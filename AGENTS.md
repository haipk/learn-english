# English Vocabulary Cards

Single-file web app (`vocab-cards.html`) that renders hand-drawn-style English
vocabulary flashcards, modeled after classroom whiteboard posters. No build
step, no dependencies to install — open the HTML file in any browser.

## Files

- `vocab-cards.html` — the entire app: markup, CSS, and JS in one file.
- `dinob.png` — profile photo shown on the BIO page (`#bioScreen`).
- `AGENTS.md` — this file.

## How to run

```bash
open vocab-cards.html        # macOS
# or just double-click the file in a file manager
```

Internet is required for: Google Fonts (Gochi Hand, Shantell Sans), IPA
lookup (dictionaryapi.dev), and sql.js WASM. Illustrations are **user
uploads**, not AI — everything works offline.

## Card anatomy (matches reference poster)

- `h1.word` (its own top row): word number + WORD.
- `zone-word` (row 2, left column): red bold IPA + red speaker SVG, "What does
  X mean?", meaning sign (held by hands, `<span class="hl">` marks blue
  highlights), big green keyword stack (centered in the column).
- `zone-ex` (right column, one example): big "Example" label, full-width
  sign with the example sentence (target word highlighted via `[brackets]`
  in data), illustration with a yellow tape strip and an optional speech
  bubble (`quote`). Only `examples[0]` is used anywhere — importing,
  editing and the card all handle a single example.

## Data model

Words are grouped per unit in the `UNITS` array inside the `<script>` block:

```js
const UNITS = [
  { unit: 8, topic: "Friends and relatives", words: [ /* word objects */ ] },
  // add more units here — units with empty words[] show locked in the menu
];
```

At runtime, `rebuildUnits()` merges `UNITS` (built-ins get `book: BOOK_TITLE`,
`_id: "b<index>"`) with `customUnits` (localStorage `vocab_custom_units`,
`_id: "c<index>"`) into `ALL_UNITS`. The "📚➕ Danh sách mới" screen creates a
custom unit — persisted in localStorage; to persist permanently add it to
`UNITS` in the file.

Each unit row in `#unitScreen` has ✏️/🗑 actions: custom units are edited/
deleted in `vocab_custom_units` directly; built-in units are overridden via
`vocab_unit_overrides` or hidden via `vocab_hidden_units` (file unchanged —
deleting the keys restores them). The ✏️ edit screen (`#editScreen`) also
lists every word as an editable card (`eWordHTML`/`renderEWords`): word,
IPA (blank = auto-lookup), meaning, keywords (blank = auto), and both
examples' text/image-prompt/quote, with 🗑 delete and ➕ add-word. Saving
writes the whole `words` array into the unit (or the `unitOverrides`
entry for built-ins).

## Video recording & practice flow

**Video recording** happens right on the card screen — a real screen
recording with the webcam bubble inside. The toolbar "🎥 Quay video" button
does everything in one click: starts the camera (`#camBubble` — draggable
circle with 📷/🎤 toggles via `MediaStreamTrack.enabled`), asks for
`getDisplayMedia` (user should pick "this tab"/the browser window) and
begins recording the **screen video track + mic audio track** mixed into one
`MediaStream` — no canvas compositing needed since the DOM camera bubble is
already inside the captured screen. `#recBar` (bottom-left) only shows
⏹ Dừng + ● REC while recording, plus ✖ to close the camera and a "✅ Đã
quay ngoài" fallback if the camera is unavailable. If screen share is
denied it falls back to camera-only recording; if the user ends sharing via
the browser UI (`track.onended`) the recording stops gracefully. Stop →
the webm blob is saved to IndexedDB `dinob_img` under
`vid:<learner>|unit:<id>` (or `vid:<learner>|mat:<sub>|<coll>|<item>` for
material recordings — `recCtx` set by the caller) and `#recScreen` opens as
a review screen (playback + "Quay lại" / "✅ Hoàn thành" which marks
`p.p1`); camera keeps running until ✖ or Hoàn thành. Saved videos can be
re-watched via the 🎬 button (`playSaved`) shown in the practice screen
(when `p.p1`) and on completed material items, and downloaded to the
machine as `.webm` via the 💾 Tải về máy button on the review screen.
Videos are NOT in the SQLite export.

The "📝 Luyện tập" button also lives on the toolbar (right end).

**App shell — DinoB Lab**: after login the app lands on `#homeScreen`, a
home page with a top nav bar (`🦕 DinoB Lab | BIO | MATH | ENGLISH▾ |
learner name + Đăng nhập`). ENGLISH drops down to SHADOWING / VOCABULARY;
BIO opens `#bioScreen` (DinoB profile — 3-column full-screen grid; the photo
top-right is clickable to upload a per-learner replacement stored as
`user.photo` dataURL, default `dinob.png`). Nav order: BIO, MY PROGRESS,
MATH, ENGLISH▾. "MY PROGRESS"
opens `#reportScreen`: a weekly plan card (styled like a handwritten
planner — week date range, sections numbered ①②③, checkbox items). The plan
is edited as plain text (`user.plans[<Monday ISO>] = {text, checks}`): plain
lines = section titles, `- ` lines = tickable tasks; ticking persists per
week per learner. Progress bar = ticked/total plan items, plus per-unit
activity detail and a weekly summary (units/videos/words this week) —
week = since Monday 00:00, tracked via timestamps `p1At`, `q1At`, `q2At`,
`doneAt`, `hwAt` written into each unit's progress. MATH alerts
"sắp ra mắt". ENGLISH drops down to LISTENING - SPEAKING / READING /
WRITING / GRAMMAR / VOCABULARY. The first four open `#matScreen` →
`#matItemScreen`: a two-level material library stored in
`localStorage["dinob_materials"]` (`{subject: [{name, items:[{t, link}]}]}`,
shared across learners; seeded with samples on first run). Each item row
has 🎥 Quay video (same screen+mic recorder — generalized via `onRecDone`
callback + `recReturn` screen id, `z-index` of `#recScreen` is 55) and
📝 Bài tập (opens `link` if set + toggles done); per-learner flags live in
`user.mat["sub|coll|item"]`. All `.screen`s carry class `full` → their card
fills the viewport; `loginScreen` stays a centered card.
VOCABULARY → `#booksScreen` (book collections grouped from `ALL_UNITS`,
e.g. *Essential Vocabulary In Context 1*) → `#unitScreen` filtered to that
book (`buildUnitScreenList(book)`) → card screen. On `#booksScreen`, admin
also gets "📚➕ Thêm bộ sách mới" (asks for a name, then opens the new-list
form to create that book's first unit — a book only exists while a unit
references it) and a ✏️ per book row (`renameBook` rewrites `book` on all
its units — custom units directly, built-ins via `unitOverrides`). The card
toolbar's 🏠 returns home; a floating `#homeFloat` 🏠 (top-right, z-70)
appears on every `.screen` except `homeScreen`/`loginScreen` via a
MutationObserver and closes all screens back to home; the fixed `#userBox`
(top-right: name + Đăng nhập) sits under screens at z-45.

**Learner login**: a full-screen `#loginScreen` asks for the learner's name
on first use (existing profiles appear as clickable chips). All user data
lives in `localStorage["vocab_users"]` =
`{current, users: {name: {progress: {unitId: {...}}}}}` — each learner has
independent progress. The `#userBox` chip shows the current learner and
"Đăng nhập" reopens the login screen to switch. The legacy `vocab_progress` key is
migrated into the first user who logs in.

**Admin account**: logging in as `admin` prompts for `ADMIN_PASS` (const
`ADMIN_PASS = "dinob123"` in the script — change it there). `isAdmin()`
checks `store.current === "admin"` + `sessionStorage["dinob_admin"]`
(session-scoped — reopening the app requires the password again). Admin
bypasses all locks (`unitUnlocked`, Practice-2 gate, `submitHomework`
guard), sees the 💾/📥 SQLite tools on the home screen (hidden otherwise),
and in MY PROGRESS gets a 👑 learner selector (`repUser`/`reportUser`) to
view and edit any learner's report/plan.

Only admin can edit entered data — all mutating surfaces are both hidden in
the UI and guarded by `isAdmin()`: unit ✏️/🗑 buttons and "📚➕ Danh sách
mới" in `#unitScreen` (`openEdit`/`saveEdit`/`deleteUnit`/`saveList`),
material add/delete rows in `#matScreen`/`#matItemScreen`, and the 🗑
delete-learner buttons on the login screen. Learners keep their own
non-admin actions: quiz/homework flow, weekly-plan ticks, bio photo.

**SQLite storage (sql.js, CDN)**: every `localStorage.setItem/removeItem`
call is write-through mirrored into a real SQLite database — table
`kv(k TEXT PRIMARY KEY, v TEXT)` — created in WASM via `initDB()`. The DB
binary is base64-dumped to `localStorage["dinob_sqlite"]` on every write;
on load, `kv` rows are hydrated back into localStorage (auto-reload once if
they differ, e.g. after an import). Home screen has 💾 Xuất .sqlite /
📥 Nhập .sqlite buttons to back up or move data — the file opens in DB
Browser for SQLite / sqlite3 CLI. First load needs internet for the WASM.

**Practice screen** (`#quizScreen`, via the toolbar "📝 Luyện tập") has 2
steps; per-user progress is keyed by unit `_id`
(`{p1, q1, q2, q1Wrong, q2Wrong, hw, done}`):

1. **Practice 1 — Quiz từ vựng** (always open): Quiz 1 — hear the word (TTS)
   & pick its meaning from a 2×2 pastel grid; Quiz 2 — read the meaning and
   type the word. BOTH must reach ≥80%. Each quiz tracks missed words in
   `q1Wrong`/`q2Wrong`; the score = % of the whole unit's words NOT in the
   wrong set, so redoing only the wrong words can raise the score. One
   "🔁 Làm lại quiz N từ vựng chưa thuộc" button re-quizzes all wrong words:
   Quiz 1's misses first, then automatically chains into Quiz 2's misses
   (`quiz.chain`). "📖 Ôn tập từ vựng chưa thuộc" browses cards of just the
   union of wrong words on the main screen (floating `#reviewBadge` exits).
2. **Practice 2 — Bài tập ứng dụng** (locked until both quizzes ≥80% —
   enforced both in the UI and in `submitHomework()`): the learner enters
   correct-count / total-count (the app computes the %), lists the
   vocabulary words they got wrong (`p.hwWrong`) and — required whenever
   wrong words exist — writes their own sentences with those words
   (`p.hwWork`) before submitting. `unit.pdf` URL / a local-PDF picker is
   available for viewing the exercise. `done` (which unlocks the NEXT unit
   via `unitUnlocked(i)`; locked units show 🔒 and are disabled in the unit
   dropdown and unit list) requires ≥80% AND no remaining wrong words —
   i.e. Practice 3 must also be cleared when it exists.
3. **Practice 3 — Bài tập phụ đạo** unlocks while `p.hwWrong` is non-empty:
   the teacher assigns a new exercise on the wrong words (outside the app),
   the learner again reports correct/total + remaining wrong words +
   self-made sentences (`p.p3`, `p.p3Wrong`, `p.p3Work`); `p.p3done` when
   no wrong words remain, which also marks `done` and unlocks the next
   unit.

`loadUnit(i)` loads a unit: updates the banner, merges its `words` with
custom words, rebuilds the word picker, resets to card 1. Empty units render
a "Danh sách trống" placeholder card. Word schema:

```js
{
  word: "encourage",
  ipa: "/ɪnˈkʌrɪdʒ/",
  meaning: 'To <span class="hl">MOTIVATE</span> and <span class="hl">SUPPORT</span> someone to do something!',
  keywords: ["SUPPORT!", "and", "MOTIVATE!"],   // rendered stacked, each on its own line
  examples: [
    {
      text: "The mother [encourages] her son to study in London!",  // [x] -> blue highlight
      img: "aunt1.png",                                           // image path/URL or "idb:<key>" — or leave "" and upload via 📷 in the unit editor
      quote: "You're very good at English! ...",                    // optional speech bubble
      emoji: "📞"                                                   // fallback if image fails
    }
  ]   // card shows ONE example — keep a single entry
}
```

Word details are edited only from the unit list — the ✏️ button on each
unit row in `#unitScreen` opens `#editScreen` where every word's fields can
be edited/added/deleted. Legacy `localStorage["vocab_custom_words"]` is
still merged into `ALL_WORDS` at load.
The new-list screen also accepts a pasted AI-style list, parsed by
`parseWordList()` — either one line per word `word | [ipa] | meaning |
example`, or `**word**` blocks followed by optional IPA line, meaning +
1 example line. An IPA column is auto-detected via `looksIpa()` (leading
`/` or IPA chars). `autoBracket()`
auto-highlights the target word inside each example sentence.

The new-list screen can also import an uploaded photo or PDF of a unit page
(CDN, needs internet): images go through Tesseract.js OCR, PDFs through
pdf.js `getTextContent()` (scanned PDF pages fall back to render→OCR). Word
bounding boxes are split into left/right page halves, each half read
top-to-bottom (`wordsToLines`), and each table row is joined into
`word | meaning | example` lines that fill the paste textarea for the
user to review before saving.
To persist permanently, add to the unit's `words` array in `UNITS`.

## Book / unit banner & unit menu

A `.book-banner` above the toolbar shows the book/unit of the active list.
`BOOK_TITLE` constant sets the default book name; the unit label is generated
by `loadUnit()` as `Unit N — <b>topic</b>`. The book name is a link — clicking
it opens `#unitScreen`, a full-screen page listing all units grouped by book
(`.unit-item` buttons; click jumps to that unit, empty units are disabled).

The `#unitPicker` dropdown in the toolbar lists every entry in `ALL_UNITS`,
grouped by book via `<optgroup>` (built by `buildUnitPicker()`). Choosing a
unit calls `loadUnit(i)`; units with an empty `words` array are disabled.
`buildUnitPicker()` re-runs after a custom list is created.

## Layout

CSS grid with `grid-template-areas`, fixed 2-row arrangement — no layout
switching:

```
"wtitle wtitle"   <- "1. WORD" alone; nothing beside it
"word   ex1"      <- IPA/meaning/keywords | Example + illustration
```

- `h1.word` is a direct child of `.card` (grid-area `wtitle`), NOT inside
  `.zone-word`, so the vocabulary word gets its own row.
- Example order: sentence sign -> "Example" label -> illustration.
- Illustrations always sit at the bottom of their zone (`margin-top: auto`).
- Card frame has fixed `aspect-ratio: 16 / 9`; `fitCard()` zooms content down
  to fit (see below).
- On narrow screens (≤720px) the 16:9 ratio is dropped (`aspect-ratio: auto`)
  and zones stack vertically.
- `fitCard()` auto-shrinks overflowing content: it sets `zoom` on the three
  zones (1.0 → min 0.5, step 0.05) until `scrollHeight`/`scrollWidth` fit the
  fixed frame. Called after every `render()`, after each image load/fail, and
  on window resize — the outer frame size never changes.

## Images

Illustrations are **user uploads** — no AI generation. Uploads happen only
in the unit editor (`#editScreen`): each example has a 📷 button next to
its image field; the picked file goes into `IndexedDB["dinob_img"]` under a
random `idb:<key>` which is written into `ex.img`, so the reference travels
with the word data. Resolution order in `renderImage(wrap, ex, key)`:

1. `ex.img` starting with `idb:` → blob from IndexedDB/`imgCache`.
2. `ex.img` non-empty → used directly as a path (file next to the html,
   relative path, URL, or data: URL).
3. Legacy `unitId|word|exIdx` IndexedDB lookup.
4. Otherwise the emoji fallback shows (no upload UI on the card itself).

Uploaded images live in the browser's IndexedDB (offline-friendly, large
quota) — they are NOT included in the SQLite export. Images use
`mix-blend-mode: multiply` so white backgrounds blend into the card's
grid-paper (looks drawn on, not pasted).

## Controls

- Prev/Next buttons or ← → arrow keys; counter shows `n / total`
- 🔀 shuffle: jumps to a random card (also picks a new layout in auto mode)
- 🔊 button or Space: pronounces the word via `speechSynthesis` (en-US)
- Word picker dropdown; 📚 unit picker dropdown;
  "📚➕ Danh sách mới" button lives at the bottom of `#unitScreen` and opens
  a full-screen form (`#listScreen`)

## Style system

- Hand-drawn look: wavy `border-radius` ("255px 15px 225px 15px / ..."),
  slight `rotate()` tilts (±0.6–1.6deg) on headings, signs, images
- CSS vars in `:root`: `--ink` (near-black), `--green` (keywords), `--blue`
  (highlighted words in sentences), `--paper`, `--accent`
- Card background = `--paper` + faint 42px grid lines (graph paper)
- Signs get `::before`/`::after` ✋ emojis on both sides ("held by hands")

## Known limitations

- Emoji fallbacks and the ✋ hand signs require emoji-capable fonts
- Vietnamese UI labels; all example content should stay in English

## Testing / screenshots

Headless Chrome captures (images need time to generate — use a big
virtual-time budget):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu \
  --screenshot=/tmp/card.png --window-size=1280,900 --hide-scrollbars \
  --virtual-time-budget=30000 \
  "file:///path/to/vocab-cards.html#a"
```
