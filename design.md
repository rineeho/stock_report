# Stock Research Agent - Design Reference

## Design Direction

다크 모드 기반, 블랙 + 옐로우 컬러 스킴. 프리미엄 금융 터미널 느낌.

- dark background (#0a0a0a)
- golden yellow accent (#ffd60a)
- generous whitespace
- simple card layout on dark surfaces
- subtle borders (#2a2a2a)
- clean typography with high contrast
- structured dashboard layout

---

## Visual Keywords

- dark premium
- minimal
- high contrast
- editorial
- data-friendly
- financial terminal aesthetic
- bold accent on dark

---

## Typography

Typography instantly signals quality. Avoid using boring, generic fonts.

**Never use**: Inter, Roboto, Open Sans, Lato, default system fonts

Good, impactful choices:
- Code aesthetic: JetBrains Mono, Fira Code, Space Grotesk
- Editorial: Playfair Display, Crimson Pro
- Technical: IBM Plex family, Source Sans 3
- Distinctive: Bricolage Grotesque, Newsreader

### Font Pairing

High contrast = interesting. Display + monospace, serif + geometric sans, variable font across weights.

Use extremes: 100/200 weight vs 800/900, not 400 vs 600. Size jumps of 3x+, not 1.5x.

Pick one distinctive font, use it decisively. Load from Google Fonts.

### Current Font Stack

- Display/Headings: **Playfair Display** (700, 900) — editorial serif
- Body/UI: **Space Grotesk** (300, 400, 500, 700) — geometric sans
- Data/Numbers: **JetBrains Mono** (400, 700) — monospace

```html
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Space+Grotesk:wght@300;400;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
```

---

## Color Palette

| Token       | Value     | Usage                |
|-------------|-----------|----------------------|
| --bg        | #0a0a0a   | Page background      |
| --card-bg   | #141414   | Card background      |
| --border    | #2a2a2a   | Borders              |
| --accent    | #ffd60a   | Primary accent (yellow) |
| --accent-dim| #b89a00   | Dimmed accent        |
| --text      | #e8e8e8   | Body text            |
| --muted     | #777      | Secondary text       |
| --success   | #4ade80   | Positive indicators  |
| --danger    | #ef4444   | Negative indicators  |
| --tag-bg    | #1e1e1e   | Tag backgrounds      |

---

## Page Layout

기본 구조는 아래 3단 또는 2단 레이아웃을 사용한다.

```html
<div class="app">
  <header class="header"></header>
  <div class="layout">
    <aside class="sidebar"></aside>
    <main class="main"></main>
    <aside class="panel"></aside>
  </div>
</div>
```

- Max width: 1040px, centered
- Card-based layout with subtle dark borders
- Responsive grid for stat cards and info boxes
- Chip/pill components for category navigation

---

## Interaction

- Cards: hover로 golden glow shadow + accent border
- Chips: hover로 accent 배경 + 블랙 텍스트
- Links: accent yellow, underline on hover → white
- Transitions: 0.15s ease
