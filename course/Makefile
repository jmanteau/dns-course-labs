QUARTO ?= $(shell command -v quarto 2>/dev/null || echo $(HOME)/opt/quarto/bin/quarto)
DECK   := dns-fundamentals
SRC    := $(DECK).qmd
OUT    := _site/$(DECK).html
PORT   ?= 8000
CHROME ?= /Applications/Chromium.app/Contents/MacOS/Chromium

.PHONY: all build preview serve single pdf clean help

all: build

help:
	@echo "make build    render the deck to $(OUT)"
	@echo "make preview  live-reload preview (quarto preview)"
	@echo "make serve    serve _site on http://localhost:$(PORT)"
	@echo "make single   self-contained HTML (_site/$(DECK)-single.html)"
	@echo "make pdf      export PDF via headless Chrome (_site/$(DECK).pdf)"
	@echo "make clean    remove build output"

build: $(OUT)

$(OUT): $(SRC) _quarto.yml theme/dns.scss theme/fonts.html $(wildcard images/*)
	$(QUARTO) render $(SRC)

preview:
	$(QUARTO) preview $(SRC)

serve: build
	cd _site && python3 -m http.server $(PORT)

single:
	$(QUARTO) render $(SRC) --to revealjs -M embed-resources:true --output $(DECK)-single.html

pdf: build
	$(CHROME) --headless=new --disable-gpu --no-pdf-header-footer \
		--virtual-time-budget=30000 \
		--print-to-pdf=_site/$(DECK).pdf "file://$(CURDIR)/$(OUT)?print-pdf"

clean:
	rm -rf _site .quarto $(DECK)_files
