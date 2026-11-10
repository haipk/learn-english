# AUDIO_TTS — Tạo MP3 luyện nghe từ vựng (Edge TTS, giọng Anh Mỹ)

Tạo file MP3 cho từng Unit bằng Microsoft Edge TTS — miễn phí, cần Internet
khi chạy. Mỗi từ được đọc theo thứ tự:

```
word. word.   (nghỉ 1.5s)
Meaning: ...  (nghỉ 2s)
Example: ...  (nghỉ 3s, rồi sang từ tiếp theo)
```

## Cài đặt (đã làm 1 lần)

```
py -3.12 -m pip install --user edge-tts pydub imageio-ffmpeg openpyxl
```

`imageio-ffmpeg` đã kèm FFmpeg — không cần cài riêng.

## Dữ liệu đầu vào (2 cách)

**Cách 1 — file .txt** (định dạng đang dùng):

```
1. bite - bite [Pause] -> Meaning: ... [Pause] -> Example: ... [Pause]
```

**Cách 2 — Excel `data.xlsx`**, sheet `DATA`, các cột:

| book | unit | no | word   | meaning            | example                  |
|------|------|----|--------|--------------------|--------------------------|
| 2    | 6    | 1  | bite   | to use your teeth… | Take a small bite of…    |

Một file Excel chứa được toàn bộ 90 unit (điền book/unit cho từng dòng).

## Chạy

```bash
# HÀNG LOẠT — mọi file .txt trong thư mục data/ (khuyến nghị)
py -3.12 make_audio.py --input data

# HÀNG LOẠT — toàn bộ unit trong Excel
py -3.12 make_audio.py --input data.xlsx --all

# 1 unit lẻ
py -3.12 make_audio.py --input data/book2_unit09.txt --book 2 --unit 9

# Đổi giọng / tốc độ / khoảng nghỉ
py -3.12 make_audio.py --input data --voice en-US-JennyNeural --rate -10%
py -3.12 make_audio.py --input data --pause-word 800 --pause-meaning 1200 --pause-example 1500
```

Mặc định đã chốt: giọng **Guy** (nam Mỹ), nghỉ **1s / 1.5s / 2s**, tốc độ `-5%`.
File đã tồn tại sẽ được bỏ qua → chạy lại an toàn (resume).

## Giọng Anh Mỹ hay dùng

| Giọng                    | Giới tính | Ghi chú                |
|--------------------------|-----------|------------------------|
| en-US-JennyNeural        | Nữ        | Mặc định, tự nhiên     |
| en-US-GuyNeural          | Nam       | Trầm, rõ               |
| en-US-AriaNeural         | Nữ        | Sáng, rõ ràng          |
| en-US-AnaNeural          | Nữ trẻ em | Có thể hợp với bé      |
| en-US-ChristopherNeural  | Nam       | Chậm rãi, dễ nghe      |

Xem thêm: `py -3.12 -m edge_tts --list-voices | findstr en-US`

## Kết quả đầu ra

```
AUDIO/
  Book2/
    Unit06/
      Book2_Unit06_Jenny.mp3   (~8 phút, 24 từ)
      Book2_Unit06_Guy.mp3
      words/
        01_Guy.mp3             # từng từ một file — nút "▶ Tự động" của
        02_Guy.mp3             # vocab-cards.html phát file này rồi lật thẻ
        ...
    Unit07/ ...
  Book3/ ...
```

File per-word trong `words/` được app dùng cho chế độ "▶ Tự động chạy
flashcard": phát hết file của từ hiện tại (đã gồm khoảng nghỉ sau ví dụ)
thì app lật sang thẻ kế. Chạy lại `make_audio.py` sẽ bổ sung các file
per-word còn thiếu mà không đụng MP3 cả unit đã có.

## Xử lý tự động trong script

- Bỏ chữ `[Pause]`, thay ` / ` trong meaning bằng dấu chấm (tránh đọc "slash").
- Tốc độ mặc định `-5%` — chỉnh bằng `--rate` (VD `-15%` chậm hơn cho bé mới nghe).
- Khoảng nghỉ: chỉnh hằng số `PAUSE_*` đầu file `make_audio.py`.
