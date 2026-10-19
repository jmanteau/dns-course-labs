# DNS Fundamentals – Quarto slide deck

Quarto (reveal.js) version of *Domain Name System (DNS) Fundamentals – IUT Blagnac*
(`Domain Name System (DNS) Fundamentals - IUT Blagnac.pptx`, the original deck kept as reference).

## Layout

| Path | Purpose |
|---|---|
| `dns-fundamentals.qmd` | The whole deck (59 slides incl. 2 hidden labs, speaker notes) |
| `_quarto.yml` | reveal.js options (1280×720 canvas, no margins, slide numbers) |
| `theme/dns.scss` | Theme + reusable layout classes (tiles, pillars, kill chain, vendor cards…) |
| `theme/fonts.html` | Roboto Mono (terminal blocks) from Google Fonts |
| `images/` | Media extracted from the pptx (+ a few crops, see below) |

## Build

```sh
quarto render dns-fundamentals.qmd            # -> _site/dns-fundamentals.html
quarto preview dns-fundamentals.qmd           # live reload
quarto render dns-fundamentals.qmd --to revealjs -M embed-resources:true   # single self-contained file
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
- Hidden slides (`data-visibility="hidden"`): *Lab: DNS Tunneling for bypassing filtering*
  and *Lab: DNS Reconnaissance* (hidden in the original too). Quarto keeps them in the source
  but leaves them out of the rendered deck (57 slides); delete the attribute to include them.
- Speaker notes are in `::: notes` blocks (press `S` in the browser).
- Cropped image variants (`*-c.png`) reproduce the crops applied in the pptx;
  `feature-N.png` and `question-mockups.png` were cut from a render of the original
  where the pptx used vector shapes.
