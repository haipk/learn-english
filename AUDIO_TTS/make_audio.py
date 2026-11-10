# -*- coding: utf-8 -*-
"""
make_audio.py — Tạo file MP3 luyện nghe từ vựng bằng Microsoft Edge TTS (giọng Anh Mỹ).

Cách dùng:
    python make_audio.py --input data/book2_unit06.txt --book 2 --unit 6
    python make_audio.py --input data/book2_unit06.txt --book 2 --unit 6 --voice en-US-GuyNeural
    python make_audio.py --input data.xlsx --book 2 --unit 6          # đọc từ Excel
    python make_audio.py --input data.xlsx --all                       # chạy toàn bộ unit trong Excel

Tuỳ chọn:
    --voice   Tên giọng Edge TTS (mặc định en-US-JennyNeural - nữ Mỹ)
              Xem danh sách: edge-tts --list-voices | findstr en-US
    --rate    Tốc độ đọc, vd "-10%" (mặc định -5% cho trẻ em)
    --out     Thư mục gốc xuất audio (mặc định ./AUDIO)
"""

import argparse
import asyncio
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from pydub import AudioSegment

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# pydub dùng ffmpeg đi kèm imageio-ffmpeg -> không cần cài FFmpeg riêng
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

# ---- Khoảng nghỉ mặc định (ms) — đã chốt với người dùng ---------------------
PAUSE_AFTER_WORD = 1000      # sau phần "word. word."
PAUSE_AFTER_MEANING = 1500   # sau phần Meaning
PAUSE_AFTER_EXAMPLE = 2000   # sau Example, trước từ tiếp theo

DEFAULT_VOICE = "en-US-GuyNeural"    # nam Mỹ; giọng nữ: en-US-JennyNeural


@dataclass
class WordEntry:
    no: int
    word: str
    meaning: str
    example: str


# ---- Tiền xử lý văn bản -----------------------------------------------------
def clean(text: str) -> str:
    """Bỏ [Pause], thay ' / ' bằng dấu chấm (TTS hay đọc '/' thành 'slash'),
    gom khoảng trắng."""
    t = re.sub(r"\[\s*Pause\s*\]", " ", text, flags=re.IGNORECASE)
    t = re.sub(r"<br\s*/?>", ". ", t, flags=re.IGNORECASE)
    t = t.replace(" / ", ". ").replace("/", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---- Đọc dữ liệu ------------------------------------------------------------
def parse_txt(path: Path) -> list[WordEntry]:
    """Parse định dạng:  N. word - word [Pause] -> Meaning: ... -> Example: ..."""
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("->")]
        head = clean(re.sub(r"^\d+\s*[.)]\s*", "", parts[0]))
        word = head.split(" - ")[0].strip()

        meaning = example = ""
        for p in parts[1:]:
            if re.match(r"(?i)^meaning\s*:", p):
                meaning = clean(re.sub(r"(?i)^meaning\s*:\s*", "", p))
            elif re.match(r"(?i)^example\s*:", p):
                example = clean(re.sub(r"(?i)^example\s*:\s*", "", p))

        no = len(entries) + 1
        m = re.match(r"^(\d+)\s*[.)]", line)
        if m:
            no = int(m.group(1))
        entries.append(WordEntry(no, word, meaning, example))
    return entries


def parse_xlsx(path: Path, book: int | None, unit: int | None) -> dict[tuple[int, int], list[WordEntry]]:
    """Đọc Excel: cột book | unit | no | word | meaning | example.
    Trả về {(book, unit): [WordEntry,...]} — lọc theo book/unit nếu có."""
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = [str(c).strip().lower() if c else "" for c in next(rows)]
    idx = {name: header.index(name) for name in ("book", "unit", "word")}

    def col(row, name):
        i = idx.get(name)
        return row[i] if i is not None and i < len(row) else None

    groups: dict[tuple[int, int], list[WordEntry]] = {}
    for row in rows:
        if row is None or col(row, "word") in (None, ""):
            continue
        b, u = int(col(row, "book")), int(col(row, "unit"))
        if book is not None and b != book:
            continue
        if unit is not None and u != unit:
            continue
        e = WordEntry(
            no=int(col(row, "no") or 0),
            word=clean(str(col(row, "word"))),
            meaning=clean(str(col(row, "meaning") or "")),
            example=clean(str(col(row, "example") or "")),
        )
        groups.setdefault((b, u), []).append(e)
    for es in groups.values():
        es.sort(key=lambda e: e.no)
        for i, e in enumerate(es, 1):
            e.no = i
    return groups


# ---- TTS --------------------------------------------------------------------
async def tts_segment(text: str, voice: str, rate: str) -> AudioSegment:
    """TTS một đoạn text -> AudioSegment."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = Path(f.name)
    try:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(tmp))
        return AudioSegment.from_file(tmp, format="mp3")
    finally:
        tmp.unlink(missing_ok=True)


async def build_unit_audio(entries: list[WordEntry], voice: str, rate: str,
                           pauses: tuple[int, int, int]) -> tuple[AudioSegment, list]:
    """Trả về (audio cả unit, [(entry, segment per-word)]) — segment per-word
    đã gồm khoảng nghỉ cuối, dùng cho chế độ flashcard tự động."""
    p_word, p_meaning, p_example = pauses
    audio = AudioSegment.silent(duration=300)
    word_segs = []
    for i, e in enumerate(entries, 1):
        print(f"  [{i}/{len(entries)}] {e.word}")
        parts = [await tts_segment(f"{e.word}. {e.word}.", voice, rate),
                 AudioSegment.silent(duration=p_word)]
        if e.meaning:
            parts += [await tts_segment(f"Meaning: {e.meaning}", voice, rate),
                      AudioSegment.silent(duration=p_meaning)]
        if e.example:
            parts += [await tts_segment(f"Example: {e.example}", voice, rate),
                      AudioSegment.silent(duration=p_example)]
        full = parts[0]
        for p in parts[1:]:
            full += p
        audio += full
        word_segs.append((e, full))
    return audio, word_segs


def voice_tag(voice: str) -> str:
    # en-US-JennyNeural -> Jenny
    m = re.match(r"en-US-(\w+?)Neural", voice)
    return m.group(1) if m else voice.replace("-", "_")


async def render_unit(book: int, unit: int, entries: list[WordEntry],
                      voice: str, rate: str, out_root: Path,
                      pauses: tuple[int, int, int]) -> Path:
    out_dir = out_root / f"Book{book}" / f"Unit{unit:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = voice_tag(voice)
    out_file = out_dir / f"Book{book}_Unit{unit:02d}_{tag}.mp3"
    wdir = out_dir / "words"          # MP3 per-word cho chế độ flashcard tự động
    wdir.mkdir(exist_ok=True)
    want_words = [wdir / f"{e.no:02d}_{tag}.mp3" for e in entries]
    if out_file.exists() and all(f.exists() for f in want_words):
        print(f"  Bỏ qua (đã có): {out_file}")
        return out_file
    print(f"-> Book {book} / Unit {unit:02d} ({len(entries)} từ), giọng {voice}")
    audio, word_segs = await build_unit_audio(entries, voice, rate, pauses)
    if not out_file.exists():
        audio.export(out_file, format="mp3", bitrate="128k")
        print(f"  Đã tạo: {out_file}  ({len(audio)/1000:.0f}s)")
    for (e, seg), f in zip(word_segs, want_words):
        if not f.exists():
            seg.export(f, format="mp3", bitrate="128k")
    print(f"  Per-word: {len(word_segs)} file trong {wdir.name}/")
    return out_file


# ---- Main -------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Tạo MP3 từ vựng bằng Edge TTS")
    ap.add_argument("--input", required=True, help="File .txt hoặc .xlsx dữ liệu")
    ap.add_argument("--book", type=int, default=None)
    ap.add_argument("--unit", type=int, default=None)
    ap.add_argument("--all", action="store_true", help="Chạy mọi unit trong file Excel")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", default="-5%")
    ap.add_argument("--pause-word", type=int, default=PAUSE_AFTER_WORD,
                    help="Nghỉ sau 'word. word.' (ms)")
    ap.add_argument("--pause-meaning", type=int, default=PAUSE_AFTER_MEANING,
                    help="Nghỉ sau Meaning (ms)")
    ap.add_argument("--pause-example", type=int, default=PAUSE_AFTER_EXAMPLE,
                    help="Nghỉ sau Example / trước từ tiếp theo (ms)")
    ap.add_argument("--out", default="AUDIO")
    args = ap.parse_args()

    src = Path(args.input)
    out_root = Path(args.out)

    if src.is_dir():
        # Chạy cả thư mục: lấy book/unit từ tên file dạng book2_unit09.txt
        groups = {}
        for f in sorted(src.glob("*.txt")):
            m = re.search(r"book\s*(\d+).*unit\s*(\d+)", f.stem, re.IGNORECASE)
            if not m:
                print(f"  Bỏ qua {f.name} (tên file không đúng dạng bookX_unitYY.txt)")
                continue
            b, u = int(m.group(1)), int(m.group(2))
            if args.book is not None and b != args.book:
                continue
            if args.unit is not None and u != args.unit:
                continue
            groups[(b, u)] = parse_txt(f)
    elif src.suffix.lower() == ".xlsx":
        groups = parse_xlsx(src, None if args.all else args.book,
                            None if args.all else args.unit)
    else:
        if args.book is None or args.unit is None:
            ap.error("File .txt cần chỉ rõ --book và --unit (hoặc đặt tên bookX_unitYY.txt và truyền thư mục)")
        groups = {(args.book, args.unit): parse_txt(src)}

    if not groups:
        sys.exit("Không có dữ liệu nào khớp book/unit đã chọn.")

    pauses = (args.pause_word, args.pause_meaning, args.pause_example)

    async def run():
        for (b, u), entries in sorted(groups.items()):
            await render_unit(b, u, entries, args.voice, args.rate, out_root, pauses)

    asyncio.run(run())


if __name__ == "__main__":
    main()
