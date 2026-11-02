# Christopher M. Morse: curriculum vitae

An interactive CV at [christophermorse.github.io](https://christophermorse.github.io/): a year
selected on an astrolabe shows that year's work. A PDF edition is built from the same data.

## Layout

| Path                     | Purpose                                        |
| ------------------------ | ---------------------------------------------- |
| `cv.yaml`                | CV content; the single source of truth         |
| `scripts/build_site.py`  | Generates the website into `_site/`            |
| `scripts/build_cv.py`    | Generates the PDF through headless Chrome      |
| `scripts/cv_common.py`   | YAML loading and date handling shared by both  |
| `site/`                  | Website template, styles and script; PDF layout |
| `tests/`                 | Unit tests                                     |

## Building

```sh
pip install -r requirements.txt
python scripts/build_site.py   # writes _site/index.html
python scripts/build_cv.py     # writes Christopher_Morse_CV.pdf
```

The PDF build needs Chrome or Chromium, and network access for the web fonts. Contact details are
read from `cv.private.yaml`, which is not committed; the PDF that contains them is gitignored.

```yaml
# cv.private.yaml
person:
  email: name@example.com
```

Run the tests with `pip install -r requirements-dev.txt && pytest`.

## Deployment

Pushing to `master` builds the site and publishes it to GitHub Pages
(`.github/workflows/pages.yml`).
