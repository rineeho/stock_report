# Stock Research Agent - Design Reference

## Design System

디자인 시스템: `Stock Research Design System` (Pretendard + JetBrains Mono)
레퍼런스: 토스증권 — clean modernism with Korean market conventions.

---

## Design Direction

다크 모드 기반 프리미엄 금융 터미널. Ink scale neutral palette + amber accent.

- App background: `--ink-950` (#0A0B0D)
- Surface: `--ink-900` (#111317)
- Amber accent: `--accent-500` (#F5A524)
- Generous whitespace (4px base spacing)
- Card layout with 12px radius
- Subtle borders (`--ink-800` #1E222A)
- Semantic color tokens throughout

---

## Visual Keywords

- dark premium
- minimal, editorial
- high contrast
- data-friendly
- financial terminal aesthetic
- Korean market conventions (red=up, blue=down)

---

## Typography

### Font Stack

- **Body/UI**: Pretendard Variable — 한글 최적화 sans-serif
- **Data/Numbers**: JetBrains Mono — tabular-nums monospace

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### Type Scale

| Token    | Size | Usage               |
|----------|------|---------------------|
| --fs-11  | 11px | Eyebrow, caption    |
| --fs-12  | 12px | Small text, chips   |
| --fs-13  | 13px | Body small          |
| --fs-14  | 14px | Body (base)         |
| --fs-16  | 16px | H4, body large      |
| --fs-18  | 18px | H3                  |
| --fs-22  | 22px | H2, detail title    |
| --fs-28  | 28px | H1, stat values     |

### Section Labels

Section headings use **eyebrow** style: 11px, uppercase, letter-spacing 0.08em, `--fg-muted` color.

---

## Color Palette

### Ink Scale (Dark Neutrals)

| Token      | Value   | Usage            |
|------------|---------|------------------|
| --ink-950  | #0A0B0D | App background   |
| --ink-900  | #111317 | Surface/cards    |
| --ink-850  | #171A1F | Hover row        |
| --ink-800  | #1E222A | Raised/borders   |
| --ink-700  | #2A2F38 | Divider          |
| --ink-500  | #5A6172 | Muted text       |
| --ink-400  | #7A8090 | Secondary text   |
| --ink-200  | #C4C8D2 | Body text        |
| --ink-100  | #E3E5EB | Primary text     |
| --ink-50   | #F4F5F8 | Display/headline |

### Semantic

| Token         | Value   | Usage                   |
|---------------|---------|-------------------------|
| --accent-500  | #F5A524 | Primary CTA, highlights |
| --accent-300  | #FFCB5C | Hover state             |
| --up-500      | #F23645 | 상승 (red, Korean)      |
| --down-500    | #2F63E0 | 하락 (blue, Korean)     |
| --success     | #12B76A | Buy rating              |
| --warning     | #F59E0B | Hold rating             |
| --danger      | #E5484D | Sell rating             |

---

## Components

### Cards
- Background: `--bg-surface`
- Border: 1px solid `--border-default`
- Radius: 12px (`--r-lg`)
- Hover: border-color → `--border-strong`

### Chips (pill)
- Radius: 9999px (pill)
- Background: `--bg-surface`
- Border: 1px solid `--border-default`
- Count badge: `--accent-500`, mono font

### Rating Badges
- Buy: `--success-bg` bg, `--success` text
- Hold: `--warning-bg` bg, `--warning` text
- Sell: `--danger-bg` bg, `--danger` text
- Size: 11px, font-weight 600, padding 3px 8px, radius 4px

### Report Cards
- Eyebrow: brokerage · sector (11px, uppercase)
- Title: 15px, bold, hover → `--accent-500`
- Meta: tags + rating badges in flex row
- One-line: 13px, `--fg-secondary`

### Header
- Sticky, glassmorphism (backdrop-filter: blur(16px))
- Background: rgba(10,11,13,0.8)
- Border-bottom: 1px solid `--border-default`

---

## Interaction

- Cards: hover → border-color transition (120ms)
- Report title: hover → accent color
- Chips: hover → border-strong + bg-hover
- Links: border-bottom on hover
- Transitions: 120ms ease-out `cubic-bezier(0.2, 0.8, 0.2, 1)`

---

## Responsive

- Container max-width: 1040px
- Mobile (<640px): padding 16px
- Grid: `auto-fit` + `minmax()` for stat cards, info boxes
- prefers-reduced-motion: disable animations
