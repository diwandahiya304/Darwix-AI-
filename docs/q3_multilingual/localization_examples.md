# Localization Examples: Literal Translation vs. Localized Adaptation

Three examples per market, drawn from the actual content in
`multilingual/{philippines,indonesia}/`, showing what a literal
translation would have produced vs. what was actually written, and why
the difference matters. **Linguistic review needed** on all Tagalog/
Bahasa Indonesia content here — see `docs/q3_multilingual/gaps.md`.

## Philippines

### 1. Premium reminder opener

- **Literal translation** (of a generic English reminder script): "You
  have a premium due on the 15th." → *"Mayroon kang premium na dapat
  bayaran sa ika-15."*
- **Localized** (actual system prompt example,
  `multilingual/philippines/config/system_prompt.md`): *"Ma'am/Sir, may
  premium po kayong due sa 15th, gusto niyo po bang i-auto-debit para
  hindi ma-lapse ang policy?"*
- **Why**: the literal version drops "po" entirely (sounds abrupt,
  almost rude in a business call — Filipino register strongly expects
  "po/opo" toward customers regardless of age), states a fact instead of
  offering help, and translates "premium"/"due"/"auto-debit" into
  invented Tagalog equivalents nobody actually says. The localized
  version keeps those as natural Taglish loanwords (real call center
  Tagalog code-switches finance vocabulary constantly), uses "po", and
  frames the message as a caring question ("gusto niyo po bang...")
  rather than a bare statement — matching the brief's "warm, indirect,
  relationship-first" requirement.

### 2. Scam-suspicion objection

- **Literal translation** (of a typical Western "we're legitimate"
  script): "We are a legitimate company, please trust us." → *"Kami ay
  lehitimong kompanya, pakiusap magtiwala kayo."*
- **Localized** (`multilingual/philippines/kb_seed/web/
  objection_handling_premium_reminder.html`): *"Naiintindihan po namin
  ang alalahanin ninyo, tama pong mag-ingat. Opisyal po kaming tumatawag
  ... makikita ninyo ang aming opisyal na numero sa likod ng inyong
  policy card ... Maaari po kayong tumawag gamit ang numerong iyon para
  makumpirma ang tawag na ito."*
- **Why**: the literal version just asserts trustworthiness — which
  reads as defensive and doesn't actually address the customer's doubt.
  The localized version first **validates the suspicion as reasonable**
  ("tama pong mag-ingat" = "you're right to be careful"), then offers a
  concrete **independent verification path** instead of asking for blind
  trust. This matches Filipino indirect communication norms: you earn
  trust by enabling the other person to verify for themselves, not by
  insisting.

### 3. "I already have work insurance" objection

- **Literal translation**: "Your work insurance is not enough, you need
  more." → *"Hindi sapat ang insurance mo sa trabaho, kailangan mo pa ng
  karagdagan."*
- **Localized** (same file): *"Maganda po iyon! Karamihan po ng group
  insurance sa trabaho ay tumatagal lamang habang kayo ay empleyado
  roon. Ang inyong individual policy po ay nagpapatuloy nang
  independiyente kahit magpalit kayo ng trabaho."*
- **Why**: the literal version opens by contradicting/correcting the
  customer ("hindi sapat" = "not enough"), which is confrontational. The
  localized version opens with a **compliment/validation** ("Maganda po
  iyon!" = "That's great!") before introducing the counterpoint — this
  is a standard Filipino politeness pattern (soften disagreement with
  affirmation first) and avoids the pushy, argumentative tone the brief
  explicitly says to avoid.

## Indonesia

### 1. Penalty objection ("Dendanya kok besar?")

- **Literal translation** (of a direct collections script): "Your
  payment is late, you must pay the penalty now." → *"Pembayaran Anda
  terlambat, Anda harus membayar denda sekarang."*
- **Localized** (`multilingual/indonesia/kb_seed/web/
  objection_handling_collections.html`): *"Kami mengerti kekhawatiran
  Bapak/Ibu. Denda dihitung sesuai perjanjian pembiayaan di awal, dan
  kami bisa bantu jelaskan rinciannya atau bantu ajukan keringanan denda
  jika Bapak/Ibu memenuhi syarat."*
- **Why**: the literal version is a demand ("Anda harus..." = "you
  must...") with no acknowledgment of the customer's concern — this
  reads as exactly the threatening tone OJK-style conduct rules
  prohibit. The localized version opens with empathy, reframes the
  penalty as something **explainable and potentially negotiable**
  (offers to help apply for relief), and never issues a command.

### 2. Missed-payment follow-up ("Gajian belum masuk")

- **Literal translation**: "Why haven't you paid?" → *"Kenapa Anda
  belum bayar?"*
- **Localized** (same file): *"Baik Pak/Bu, kami mengerti. Boleh kami
  tahu perkiraan tanggal gajian Bapak/Ibu supaya kami bisa catat janji
  bayarnya?"*
- **Why**: the literal version is accusatory ("kenapa" = "why" framed as
  a challenge). The localized version reframes the same information
  need as a **collaborative scheduling question** ("boleh kami tahu..."
  = "may we know...") — a much softer, less confrontational framing
  appropriate for a collections call where the customer hasn't done
  anything wrong yet (they're just late), and consistently uses "Bapak/
  Ibu" honorifics even in this harder conversational context.

### 3. Register-blind script vs. formal/colloquial pair

- **Literal translation approach**: a single fixed-register script
  translated once, used identically regardless of how the customer
  speaks — e.g. always *"Mohon maaf, Bapak/Ibu, saya belum memiliki
  informasi tersebut saat ini."* even if the customer opened with *"Halo
  Kak, ada apa nih?"*
- **Localized** (`multilingual/indonesia/config/fallback_messages.yaml`):
  two variants — formal (*"Mohon maaf, Bapak/Ibu, saya belum memiliki
  informasi tersebut saat ini. Saya bisa menghubungkan Bapak/Ibu dengan
  tim spesialis..."*) and colloquial (*"Maaf ya Kak, aku belum ada info
  soal itu sekarang. Aku bisa sambungin ke tim khusus..."*), selected per
  turn by `multilingual/common/register.py`'s keyword heuristic.
- **Why**: Indonesian has a much stronger formal/informal register split
  than English (different pronouns — "Anda/Bapak-Ibu" vs. "kamu/Kak" —
  different sentence particles, different politeness markers). A single-
  register translation either sounds stiff and distant to a customer who
  opened casually, or too familiar/unprofessional to one who opened
  formally. This is exactly the kind of thing literal translation
  structurally cannot capture, since the source (usually English)
  script doesn't encode a formal/informal axis this way at all.
