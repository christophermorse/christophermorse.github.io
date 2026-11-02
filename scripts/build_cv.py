"""Build the PDF CV from cv.yaml and cv.private.yaml using headless Chrome.

The PDF contains private contact details, so it is gitignored.
"""

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from cv_common import MONTHS, ROOT, load_cv, load_yaml, month_label, sort_key, year_range

DEFAULT_OUTPUT = ROOT / "Christopher_Morse_CV.pdf"
PRIVATE_FILE = ROOT / "cv.private.yaml"
BROWSERS = ("google-chrome", "chromium", "chromium-browser")
HARVARD = "Harvard University"
BRASS = "#8F7036"
RUBRIC = "#972B1A"


def markdown(text):
    """Render cv.yaml's light markdown: *italic*, **bold** and [text](url)."""
    text = html.escape(str(text).strip(), quote=False)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m[2])}">{m[1]}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)


def linked(text, url):
    return f"[{text}]({url})" if url else text


def trimmed(text):
    return str(text).rstrip(" .")


def closing_period(text):
    """Return the period to follow a title, unless it ends in ? or !."""
    return "" if re.search(r"[?!][\"”“»]*$", trimmed(text)) else "."


def strong(text):
    return f'<span class="t">{text}</span>'


def muted(text):
    return f'<span class="m">{text}</span>'


def title_of(entry):
    """Render an entry's title, linked if it has a URL, without its final period."""
    return strong(markdown(linked(trimmed(entry["title"]), entry.get("url"))))


def printed(entries):
    return [entry for entry in entries if entry.get("print", True)]


def newest_first(entries):
    return sorted(entries, key=lambda e: sort_key(e["date"]), reverse=True)


def line_row(when, content):
    return f'<div class="row line"><div class="when">{when}</div><div>{content}</div></div>'


def entry_row(when, title, organization, items=()):
    bullets = "".join(f"<li>{markdown(item)}</li>" for item in items)
    bullets = f"<ul>{bullets}</ul>" if bullets else ""
    return (
        f'<div class="row entry"><div class="when">{when}</div><div>'
        f'<h3>{markdown(title)}</h3><p class="org">{markdown(organization)}</p>{bullets}'
        "</div></div>"
    )


def section(title, body):
    return f"<section><h2>{title}</h2>{body}</section>"


def bare_url(url):
    return url.split("//")[-1].rstrip("/")


def contact_links(person):
    email = person.get("email")
    if isinstance(email, dict):
        email = email.get("address")
    site = person["homepage"]
    linkedin = person["linkedin"]
    scholar = person["google_scholar"]["id"]

    contacts = [f'<a href="mailto:{email}">{email}</a>'] if email else []
    contacts += [person[key] for key in ("phone", "address") if person.get(key)]
    contacts += [
        f'<a href="{site}">{bare_url(site)}</a>',
        f'<a href="https://www.linkedin.com/in/{linkedin}">linkedin.com/in/{linkedin}</a>',
        f'<a href="https://scholar.google.com/citations?user={scholar}">Google Scholar</a>',
    ]
    return "".join(f"<span>{contact}</span>" for contact in contacts)


def render_header(person):
    name = f'{person["first_name"]} {person["last_name"]}'
    if person.get("suffix"):
        name += f', {person["suffix"]}'
    photo = ""
    if person.get("photo"):
        photo = f'<img id="portrait" src="file://{ROOT / person["photo"]}" alt="" />'
    paragraphs = [p for p in person["summary"].split("\n") if p.strip()]
    summary = "".join(f"<p>{markdown(p)}</p>" for p in paragraphs)
    ornament = (
        f'<svg viewBox="0 0 52 10"><path d="M26 .5L30.5 5L26 9.5L21.5 5Z" fill="{BRASS}"/>'
        f'<circle cx="15" cy="5" r="1.2" fill="{BRASS}"/>'
        f'<circle cx="37" cy="5" r="1.2" fill="{BRASS}"/></svg>'
    )
    return (
        f'<header><div class="ident">{photo}<div><h1>{html.escape(name)}</h1>'
        f'<p class="position">{markdown(person["position"])}</p>'
        f'<p class="contact">{contact_links(person)}</p></div></div>'
        f'<div class="flourish"><i></i>{ornament}<i></i></div>'
        f'<div class="summary">{summary}</div></header>'
    )


def render_experience(cv):
    rows = (
        entry_row(
            year_range(job["start"], job["end"]),
            job["title"],
            f'{job["organization"]}, {job["location"]}',
            job.get("items"),
        )
        for job in printed(cv["experience"])
    )
    return section("Experience", "".join(rows))


def render_education(cv):
    # Study-abroad entries (which have a `kind`) exist for the site's timeline;
    # the B.A. entry already names them.
    rows = (
        entry_row(
            year_range(entry["start"], entry["end"]),
            entry["degree"],
            f'{entry["institution"]}, {entry["location"]}',
            entry.get("items"),
        )
        for entry in printed(cv["education"])
        if "kind" not in entry
    )
    return section("Education", "".join(rows))


def render_grants(cv):
    rows = []
    for grant in printed(cv["grants"]):
        funding = (
            f'{grant["funder"]}, with {grant["partner"]}. {grant["amount"]}. '
            f'Co-led with {grant["co_lead"]}'
        )
        row = entry_row(
            year_range(grant["start"], grant["end"]),
            linked(trimmed(grant["title"]), grant.get("url")),
            funding,
            [grant["description"]],
        )
        rows.append(f'<div class="grant">{row}</div>')
    return section("Grants", "".join(rows))


def render_skills(cv):
    rows = [
        f'<dt>{markdown(group["category"])}</dt><dd>{markdown(", ".join(group["items"]))}</dd>'
        for group in cv["skills"]
    ]
    languages = ", ".join(f'{l["language"]} ({l["level"]})' for l in cv["languages"])
    rows.append(f"<dt>Languages</dt><dd>{markdown(languages)}</dd>")
    return section("Skills &amp; Languages", f'<dl class="skills">{"".join(rows)}</dl>')


def publication_row(entry):
    authors = markdown(entry["authors"]).replace("C. Morse", '<span class="me">C. Morse</span>')
    venue = f'<i class="m">{markdown(trimmed(entry["venue"]))}</i>'
    return line_row(
        entry["year"],
        f'{authors}. {title_of(entry)}{closing_period(entry["title"])} {venue}.',
    )


def render_publications(cv):
    publications = cv["publications"]
    # The dissertation is named under Education.
    groups = (("Refereed", "refereed"), ("Essays &amp; Public Writing", "other"))
    body = "".join(
        f"<h4>{heading}</h4>" + "".join(publication_row(e) for e in printed(publications[key]))
        for heading, key in groups
    )
    return section("Publications", body)


def talk_content(talk):
    co_presenters = ""
    if talk["authors"] != "C. Morse":
        authors = markdown(talk["authors"]).replace(" (co-presenter)", ", co-presenter")
        co_presenters = " " + muted(f"({authors})")
    punctuation = "." if co_presenters else closing_period(talk["title"])
    event = muted(f'{markdown(talk["event"])}, {markdown(talk["location"])}.')
    return f"{title_of(talk)}{co_presenters}{punctuation} {event}"


def render_talks(cv):
    talks = [t for t in printed(cv["talks"]) if not t.get("teaching")]
    rows = (line_row(month_label(t["date"]), talk_content(t)) for t in talks)
    return section("Talks &amp; Workshops", "".join(rows))


def render_teaching(cv):
    teaching = cv["teaching"]
    courses = "".join(
        line_row(
            course["term"],
            f'{title_of(course)}. {muted(markdown(course["institution"]) + ".")} '
            f'{markdown(course["description"])}',
        )
        for course in printed(teaching["courses"])
    )
    sessions = [(t["date"], talk_content(t)) for t in printed(cv["talks"]) if t.get("teaching")]
    sessions += [
        (w["date"], f'{title_of(w)}. {muted(markdown(w["host"]) + ".")}')
        for w in printed(teaching["workshops"])
    ]
    sessions.sort(key=lambda s: sort_key(s[0]), reverse=True)
    session_rows = "".join(line_row(month_label(date), text) for date, text in sessions)
    return section(
        "Teaching",
        f"<h4>Courses</h4>{courses}<h4>Workshops &amp; Sessions</h4>{session_rows}",
    )


def render_organizing(cv):
    events = printed(cv["organizing"])

    def host_row(event):
        role = f'{event["role"]}, ' if event.get("role") else ""
        return line_row(
            month_label(event["date"]),
            f'{title_of(event)}. {muted(role + markdown(event["host"]) + ".")}',
        )

    def consortium_row(event):
        return line_row(
            month_label(event["date"]), f'{title_of(event)}. {muted(event["role"] + ".")}'
        )

    elsewhere = newest_first(e for e in events if e["host"] != HARVARD)
    harvard = newest_first(e for e in events if e["host"] == HARVARD)
    return section(
        "Conferences &amp; Events Organized",
        "".join(map(host_row, elsewhere))
        + f"<h4>Digital Futures Consortium, {HARVARD}</h4>"
        + "".join(map(consortium_row, harvard)),
    )


def render_radio(cv):
    rows = []
    for show in printed(cv["broadcast"]):
        episodes = show.get("episodes")
        if episodes:
            when = year_range(show["start"], show["end"])
        else:
            when = month_label(show["date"])
        title = strong(f'<i>{markdown(linked(show["show"], show.get("url")))}</i>')
        details = f'{markdown(show["outlet"])}. {markdown(trimmed(show["role"]))}.'
        if episodes:
            details += f" {len(episodes)} episodes."
        rows.append(line_row(when, f'{title}{closing_period(show["show"])} {muted(details)}'))
    return section("Radio", "".join(rows))


def render_press(cv):
    rows = (
        line_row(
            month_label(article["date"]),
            f'{markdown(linked(trimmed(article["title"]), article.get("url")))}'
            f'{closing_period(article["title"])} <i class="m">{markdown(article["outlet"])}.</i>',
        )
        for article in newest_first(printed(cv["media"]))
    )
    return section("Press", "".join(rows))


def render_service(cv):
    editorial = "".join(
        line_row(
            year_range(entry["start"], entry["end"]) if entry.get("start") else entry["year"],
            f'{strong(entry["role"])}, {markdown(linked(entry["venue"], entry.get("url")))}.',
        )
        for entry in printed(cv["editorial"])
    )
    activities = "".join(
        line_row(
            year_range(entry["start"], entry["end"]),
            f'{strong(entry["role"])}, {markdown(entry["organization"])}, '
            f'{markdown(entry["location"])}.',
        )
        for entry in printed(cv["activities"])
    )
    return section("Service &amp; Memberships", editorial + activities)


def render_colophon(cv, person):
    updated = cv["meta"]["last_updated"]
    site = person["homepage"]
    star = "M20 2L22.2 17.8L38 20L22.2 22.2L20 38L17.8 22.2L2 20L17.8 17.8Z"
    points = "".join(
        f'<path d="{star}" fill="none" stroke="{BRASS}" stroke-width=".7" '
        f'transform="rotate({angle} 20 20)"/>'
        for angle in (45, 0)
    )
    return (
        '<div class="colophon"><svg viewBox="0 0 40 40">'
        f'<circle cx="20" cy="20" r="19" fill="none" stroke="{BRASS}" stroke-width=".5"/>'
        f'{points}<circle cx="20" cy="20" r="1.8" fill="{RUBRIC}"/></svg>'
        f"Updated {MONTHS[updated.month - 1]} {updated.year}. The interactive edition lives at "
        f'<a href="{site}">{bare_url(site)}</a>.</div>'
    )


def render_document(cv, person):
    body = "".join(
        (
            render_header(person),
            render_experience(cv),
            render_education(cv),
            render_grants(cv),
            render_skills(cv),
            render_publications(cv),
            render_talks(cv),
            render_teaching(cv),
            render_organizing(cv),
            render_radio(cv),
            render_press(cv),
            render_service(cv),
            render_colophon(cv, person),
        )
    )
    author = f'{person["first_name"]} {person["last_name"]}'
    template = (ROOT / "site" / "cv_print.html").read_text(encoding="utf-8")
    return (
        template.replace("/*TITLE*/", f"{author}: Curriculum Vitae")
        .replace("/*AUTHOR*/", author)
        .replace("/*BODY*/", body)
    )


def print_to_pdf(document, output):
    browser = next(filter(None, map(shutil.which, BROWSERS)), None)
    if browser is None:
        sys.exit("build_cv.py needs Chrome or Chromium on the PATH")
    # Rendered from a temporary directory because the page holds private details.
    with tempfile.TemporaryDirectory() as directory:
        page = Path(directory) / "cv.html"
        page.write_text(document, encoding="utf-8")
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                "--generate-pdf-document-outline",
                "--virtual-time-budget=8000",
                f"--print-to-pdf={output}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    cv = load_cv()
    private = load_yaml(PRIVATE_FILE) if PRIVATE_FILE.exists() else {}
    person = {**cv["person"], **(private or {}).get("person", {})}
    print_to_pdf(render_document(cv, person), args.output.resolve())
    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
