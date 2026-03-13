# Salem Mania!


---

## Files

```
spiderweb-blog/
├── index.html   ← Full newsletter page structure
├── style.css    ← All styles (CSS custom properties, responsive)
└── main.js      ← Web nav open/close + scroll animations + form
```

---

## Features

- **Spider-Web Nav Overlay** — full-screen radial web drawn with animated SVG strokes; 8 navigation nodes at spoke endpoints. Triggered by the web button in the header.
- **Corner Webs** — decorative SVG web corners anchoring the masthead.
- **Web Dividers** — intricate SVG section separators resembling a web anchor point.
- **Footer Web** — radiating thread pattern in the page footer.
- **Newsletter Card Grid** — editorial layout with hero + 3-column + 2-column sections.
- **Scroll-triggered fade-up** via IntersectionObserver (no library needed).
- **Subscribe form** with validation and success state.
- **Google Fonts** — Playfair Display, Libre Baskerville, Source Code Pro.
- **Fully responsive** down to 320px.

---

## Usage

### Option A — Standalone
Open `index.html` directly in a browser. No build step required.

### Option B — Import into existing project
1. Copy `style.css` and `main.js` into your project.
2. Add the Google Fonts `<link>` from `index.html` to your `<head>`.
3. Copy the `<nav class="web-nav">` block and the web trigger `<button>` from `index.html`.
4. Add `id="webNav"`, `id="webTrigger"`, and `id="webClose"` to the corresponding elements.
5. The rest of the card/section markup is standard HTML — use as needed.

### Option C — GitHub Pages
Push the folder as a repository, enable GitHub Pages from `main` / root, and it will serve instantly.

---

## Customization

All colors and fonts are CSS custom properties at the top of `style.css`:

```css
:root {
  --ink:    #1a1008;   /* primary text / dark backgrounds */
  --paper:  #f5f0e8;   /* page background */
  --web:    #c8002a;   /* Spider-Man red — accent color  */
  --thread: rgba(200,0,42,.55);  /* SVG web thread color */

  --font-display: 'Playfair Display', Georgia, serif;
  --font-body:    'Libre Baskerville', Georgia, serif;
  --font-mono:    'Source Code Pro', monospace;
}
```

Swap `--web` to any hex to recolor every web element at once.

---

## Browser Support
Chrome 90+, Firefox 88+, Safari 14+, Edge 90+.  
Gracefully degrades in older browsers (SVG animations simply skip, layout remains intact).

---

## License
MIT — use freely, attribution appreciated but not required.
