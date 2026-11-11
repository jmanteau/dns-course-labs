# DNS Fundamentals – Quarto slide deck

Quarto (reveal.js) version of *Domain Name System (DNS) Fundamentals – IUT Blagnac*
(`Domain Name System (DNS) Fundamentals - IUT Blagnac.pptx`, the original deck kept as reference).
The Quarto deck has since been reordered and corrected, so the two no longer match slide for slide.

## Layout

| Path | Purpose |
|---|---|
| `dns-fundamentals.qmd` | The whole deck (slides and speaker notes) |
| `_quarto.yml` | reveal.js options (1280×720 canvas, no margins, slide numbers) |
| `theme/dns.scss` | Theme: colour tokens, type scale, title bar, terminal windows, tables and cards (pillars, features, records, vendor cards…) |
| `theme/fonts.html` | Source Sans 3 (text) and JetBrains Mono (terminals, code) from Google Fonts |
| `theme/part-footer.lua` | Adds the "PART n · NAME" footer to every slide, taken from the last chapter divider |
| `theme/link-icons.lua` | Turns external links into text plus a clickable icon |
| `images/` | Media extracted from the pptx (+ a few crops, see below) |
| `diagrams/` | Editable draw.io sources, exported to `images/` under the same name (`make figures`). They use Source Sans 3, which must be installed locally for the export (`brew install --cask font-source-sans-3`); otherwise draw.io falls back to a serif font |

## Build

```sh
quarto render dns-fundamentals.qmd            # -> _site/dns-fundamentals.html
quarto preview dns-fundamentals.qmd           # live reload
quarto render dns-fundamentals.qmd --to revealjs -M embed-resources:true --metadata-file theme/single.yml   # single self-contained file (turns off the chalkboard, which can't be embedded)
```

PDF: open `_site/dns-fundamentals.html?print-pdf` in Chrome and print to PDF
(or `quarto render … --to revealjs` then `decktape`).

## Authoring notes

- Every slide is a 1280×720 canvas. Free-form slides place elements with
  `{.absolute left=… top=… width=…}` (coordinates come straight from the pptx).
  If a div needs its own `style=`, use `.a` and put `left/top/width` in the style
  (an explicit `style` overrides `.absolute`'s generated position).
- Terminal output uses `<pre class="a terminal">` – Pandoc turns soft line breaks
  into spaces, so a plain `<div>` would collapse the lines.
- Speaker notes are in `::: notes` blocks (press `S` in the browser).
- Chalkboard: press `B` for a blank board, `C` to draw on the current slide (`Del` clears it).
- Cropped image variants (`*-c.png`) reproduce the crops applied in the pptx;
  `feature-N.png` and `question-mockups.png` were cut from a render of the original
  where the pptx used vector shapes.
