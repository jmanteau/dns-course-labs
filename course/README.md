# Course slides and site: sources

How to edit, build and publish the slides of the DNS course and its home page. For teachers and maintainers. Updated November 2026.

Students: open the slides on the [course site](https://jmanteau.github.io/dns-course-labs/) instead.

## What gets built

| Source | Output | What it is |
|--------|--------|------------|
| `dns-fundamentals.qmd` | `_site/dns-fundamentals.html` | *Domain Name System Fundamentals*, the course deck |
| `dns-advanced.qmd` | `_site/dns-advanced.html` | *DNS Beyond the Basics*, read before the Dig Quest advanced missions |
| `index.qmd` | `_site/index.html` | The home page of the course site: one card per step, links to the slides and labs |

The slides are reveal.js presentations built with Quarto. The original PowerPoint deck, `Domain Name System (DNS) Fundamentals - IUT Blagnac.pptx`, is kept as a reference. The Quarto deck has since been reordered and corrected, so the two no longer match slide for slide.

## Build the slides

`make help` lists every command. The main ones:

| Command | What it does |
|---------|--------------|
| `make build` | Render the deck to `_site/dns-fundamentals.html` |
| `make preview` | Preview with live reload |
| `make serve` | Serve `_site` on http://localhost:8000 |
| `make single` | One self-contained HTML file, `_site/dns-fundamentals-single.html`, with the chalkboard turned off because it cannot be embedded |
| `make pdf` | Export a PDF through headless Chromium, `_site/dns-fundamentals.pdf` |
| `make site` | The whole course site in `_site`: home page, both decks and the PDFs |
| `make figures` | Re-export the changed draw.io diagrams to `images/` |
| `make cheatsheet` | Render the dig cheat sheet, `../dns-dig-lab/cheatsheet.pdf` |
| `make qr` | Regenerate the QR codes in `images/qr-*.svg` |

Add `DECK=dns-advanced` to build the advanced deck instead, for example `make build DECK=dns-advanced`.

Without make, the same with Quarto directly:

```sh
quarto render dns-fundamentals.qmd            # -> _site/dns-fundamentals.html
quarto preview dns-fundamentals.qmd           # live reload
quarto render dns-fundamentals.qmd --to revealjs -M embed-resources:true --metadata-file theme/single.yml   # single self-contained file (turns off the chalkboard, which can't be embedded)
```

To get a PDF by hand, open `_site/dns-fundamentals.html?print-pdf` in Chrome and print to PDF.

## Publish the course site

The workflow `.github/workflows/pages.yml` publishes the site on GitHub Pages at [jmanteau.github.io/dns-course-labs](https://jmanteau.github.io/dns-course-labs/).

- It runs on every push to `main` that changes `course/`, the course PDF or the dig cheat sheet. You can also start it by hand from the repository's Actions tab.
- It runs `make site` with Quarto only. The draw.io diagrams are not exported there, so commit the PNG files in `images/` after `make figures`.
- It does not fetch the private `secret` submodule: the slides need no game answers.

## Where things are

| Path | What it holds |
|------|---------------|
| `dns-fundamentals.qmd` | The whole course deck: slides and speaker notes |
| `dns-advanced.qmd` | The advanced deck |
| `index.qmd`, `theme/home.css` | The home page of the course site and its style |
| `_quarto.yml` | reveal.js options: 1280×720 canvas, no margins, slide numbers |
| `theme/dns.scss` | Slide theme: colour tokens, type scale, title bar, terminal windows, tables and cards (pillars, features, records, vendor cards…) |
| `theme/fonts.html` | Source Sans 3 (text) and JetBrains Mono (terminals, code) from Google Fonts |
| `theme/part-footer.lua` | Adds the "PART n · NAME" footer to every slide, taken from the last chapter divider. Slides only |
| `theme/link-icons.lua` | Turns external links into text plus a clickable icon. Slides only |
| `theme/single.yml` | Options for `make single` |
| `images/` | Images: media extracted from the pptx, a few crops, and the exported diagrams |
| `diagrams/` | Editable draw.io sources, exported to `images/` under the same name by `make figures` |
| `print-pdf.mjs` | The PDF export used by `make pdf` |

The draw.io diagrams use the Source Sans 3 font. Install it before you export them, or draw.io falls back to a serif font:

```sh
brew install --cask font-source-sans-3
```

## Rules for writing slides

- **Fixed canvas.** Every slide is a 1280×720 canvas. Free-form slides place elements with `{.absolute left=… top=… width=…}`. The coordinates come straight from the pptx.
- **Own style.** If a div needs its own `style=`, give it the class `.a` and put `left/top/width` in the style. An explicit `style` overrides the position `.absolute` generates.
- **Terminal output.** Write it in `<pre class="a terminal">`. Pandoc turns soft line breaks into spaces, so a plain `<div>` would collapse the lines.
- **Speaker notes.** They go in `::: notes` blocks. Press `S` in the browser to see them.
- **Chalkboard.** Press `B` for a blank board, or `C` to draw on the current slide. `Del` clears it.
- **Cropped images.** The `*-c.png` variants reproduce the crops applied in the pptx. `feature-N.png` and `question-mockups.png` were cut from a render of the original, where the pptx used vector shapes.
