QUARTO ?= $(shell command -v quarto 2>/dev/null || echo $(HOME)/opt/quarto/bin/quarto)
# DECK=dns-advanced builds the Dig Quest Advanced deck with the same targets
DECK   ?= dns-fundamentals
SRC    := $(DECK).qmd
OUT    := _site/$(DECK).html
PORT   ?= 8000
CHROME ?= /Applications/Chromium.app/Contents/MacOS/Chromium
DRAWIO ?= $(shell command -v drawio 2>/dev/null || echo /Applications/draw.io.app/Contents/MacOS/draw.io)

DIAGRAMS := $(wildcard diagrams/*.drawio)
FIGURES  := $(patsubst diagrams/%.drawio,images/%.png,$(DIAGRAMS))
STEPS    := $(foreach n,0 1 2 3 4 5 6 7 8,images/full-dns-sequence-step$(n).png)

REPO      := https://github.com/jmanteau/dns-course-labs
SITE      := https://jmanteau.github.io/dns-course-labs
CHEATSHEET := ../dns-dig-lab/cheatsheet

.PHONY: all build figures qr cheatsheet preview serve single pdf site clean help

.DEFAULT_GOAL := help

all: build

help:
	@echo "make figures  re-export changed diagrams/*.drawio to images/*.png"
	@echo "make qr       regenerate the QR codes in images/qr-*.svg"
	@echo "make cheatsheet  render the dig cheat sheet ($(CHEATSHEET).pdf)"
	@echo "make build    render the deck to $(OUT)"
	@echo "make preview  live-reload preview (quarto preview)"
	@echo "make serve    serve _site on http://localhost:$(PORT)"
	@echo "make single   self-contained HTML (_site/$(DECK)-single.html)"
	@echo "make pdf      export PDF via headless Chromium (_site/$(DECK).pdf)"
	@echo "make site     the published site in _site: home page, both decks, the PDFs (what GitHub Pages serves)"
	@echo "make clean    remove build output"
	@echo "add DECK=dns-advanced to build the advanced deck (default: $(DECK))"

figures: $(FIGURES) $(STEPS)

images/%.png: diagrams/%.drawio
	$(DRAWIO) -x -f png -s 2 -o $@ $<

# steps.py writes all nine PNGs at once; the last one stands for the group (make 3.81 has no grouped targets)
images/full-dns-sequence-step8.png: diagrams/full-dns-sequence.drawio diagrams/steps.py
	python3 diagrams/steps.py "$(DRAWIO)"

$(filter-out images/full-dns-sequence-step8.png,$(STEPS)): images/full-dns-sequence-step8.png

qr:
	uvx -q segno "$(SITE)/" --scale 8 --border 2 --dark "#15315b" --no-size --output images/qr-dig-lab.svg
	uvx -q segno "$(SITE)/dig-cheatsheet.pdf" --scale 8 --border 2 --dark "#15315b" --no-size --output images/qr-cheatsheet.svg
	uvx -q segno "$(SITE)/dns-cyber-lab.html" --scale 8 --border 2 --dark "#15315b" --no-size --output images/qr-cyber-lab.svg

cheatsheet: $(CHEATSHEET).pdf

$(CHEATSHEET).pdf: $(CHEATSHEET).typ
	$(QUARTO) typst compile $< $@

build: $(OUT)

$(OUT): $(FIGURES) $(STEPS) $(SRC) _quarto.yml theme/link-icons.lua theme/part-footer.lua theme/dns.scss theme/fonts.html $(wildcard images/*)
	$(QUARTO) render $(SRC)

preview:
	$(QUARTO) preview $(SRC)

serve: build
	cd _site && python3 -m http.server $(PORT)

single:
	$(QUARTO) render $(SRC) --to revealjs -M embed-resources:true --metadata-file theme/single.yml --output $(DECK)-single.html

pdf: build
	node print-pdf.mjs "$(CHROME)" $(OUT) _site/$(DECK).pdf

# the GitHub Pages site (.github/workflows/pages.yml runs this): quarto only, no draw.io
site:
	$(QUARTO) render index.qmd
	$(QUARTO) render dns-fundamentals.qmd
	$(QUARTO) render dns-advanced.qmd
	$(QUARTO) render dns-cyber-lab.qmd
	cp "../Domain Name System Fundamentals.pdf" _site/Domain-Name-System-Fundamentals.pdf
	cp "../DNS Beyond the Basics.pdf" _site/DNS-Beyond-the-Basics.pdf
	cp $(CHEATSHEET).pdf _site/dig-cheatsheet.pdf

clean:
	rm -rf _site .quarto dns-fundamentals_files dns-advanced_files dns-cyber-lab_files
