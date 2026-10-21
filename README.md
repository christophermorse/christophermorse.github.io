# Christopher M. Morse — curriculum vitae

An interactive CV: an astrolabe of years beside a page that shows each year's work.

## Updating the CV

Everything lives in **`cv.yaml`**. Edit it (on GitHub: open the file, click the pencil, commit),
and the site rebuilds and republishes itself within a minute or two.

- Images: put them in `assets/` and add `image: assets/your-file.jpg` to an entry.
- `public: false` keeps a field (phone, address, references) off the website.
- Your email, phone, address and references live in `cv.private.yaml`, which stays on your
  computer and is never pushed. **This repository is public**: anything in `cv.yaml` is served
  in plain text at `raw.githubusercontent.com`, so never put contact details there. The website
  links LinkedIn and Google Scholar instead of an address.
- Lines marked `CONFIRM` or `TODO` are still waiting for a check.

## How it works

- `cv.yaml` – the single source of truth
- `scripts/build_site.py` – turns it into `_site/index.html`
- `site/template.html` – the design (astrolabe, star chart, layout)
- `.github/workflows/pages.yml` – builds and publishes to GitHub Pages on every push

To preview locally: `pip install pyyaml`, `python scripts/build_site.py`, then open `_site/index.html`.

The printed LaTeX edition will be generated from the same `cv.yaml` (coming next).
