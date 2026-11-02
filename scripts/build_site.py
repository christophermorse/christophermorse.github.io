"""Build the website from cv.yaml into _site/."""

import json
import shutil

from cv_common import ROOT, load_cv, strip_markdown, timeline_position, timeline_span

OUTPUT = ROOT / "_site"
STATIC_FILES = ("style.css", "app.js")

# Short names used in timeline labels.
INSTITUTION_LABELS = {
    "Harvard University": "Harvard",
    "University of Massachusetts Amherst": "UMass Amherst",
    "Kwansei Gakuin University": "Kwansei Gakuin",
    "International Christian University": "ICU",
}
HARVARD = "Harvard University"
BANDS = [
    ["work", "Work and education"],
    ["writing", "Writing"],
    ["speaking", "Speaking and radio"],
    ["teaching", "Teaching and convening"],
    ["press", "In the press"],
    ["service", "Service"],
]


def short_label(text, limit=38):
    """Shorten a title for the timeline, cutting at a colon or a word boundary."""
    text = strip_markdown(text).strip().rstrip(".")
    if ":" in text[: limit + 6]:
        text = text.split(":")[0]
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;–-") + "…"
    return text


def linked(text, url):
    return f"[{text}]({url})" if url else text


def as_list(text):
    return [text] if text else []


def role_prefix(entry):
    return f'{entry["role"]}. ' if entry.get("role") else ""


def make_item(
    band, kind, item_id, title, meta, when, start, end, themes, items=None, label=None, **extra
):
    item = {
        "id": item_id,
        "band": band,
        "kind": kind,
        "title": title,
        "meta": meta,
        "when": when,
        "start": start,
        "end": end,
        "span": bool(end - start > 0.3),
        "themes": themes or ["community"],
        "items": items or [],
        "label": label or short_label(title),
    }
    item.update({key: value for key, value in extra.items() if value})
    return item


def experience_items(cv):
    for i, job in enumerate(cv["experience"]):
        start, end, when = timeline_span(job.get("start"), job.get("end"))
        employer = job.get("short_org") or job["organization"].split(",")[0]
        yield make_item(
            "work",
            "Position",
            f"exp{i}",
            job["title"],
            f'{job["organization"]}, {job["location"]}',
            when,
            start,
            end,
            job.get("themes"),
            job.get("items"),
            label=f'{job["title"]}, {employer}',
            image=job.get("image"),
            credits=job.get("credits"),
        )


def grant_items(cv):
    for i, grant in enumerate(cv["grants"]):
        start, end, when = timeline_span(grant["start"], grant["end"])
        press = [m for url in grant.get("press", []) for m in cv["media"] if m.get("url") == url]
        quote = next((m["pull_quote"] for m in press if m.get("pull_quote")), None)
        meta = f'{grant["funder"]}, with {grant["partner"]}. {grant["amount"]}'
        if grant.get("co_lead"):
            meta += f'. Co-led with {grant["co_lead"]}'
        yield make_item(
            "work",
            "Grant",
            f"grt{i}",
            linked(grant["title"], grant.get("url")),
            meta,
            when,
            start,
            end,
            grant["themes"],
            [grant["description"]],
            label=f'{grant["amount"]} R&D project: multilingual, explainable NLP',
            quote=quote,
        )


def education_items(cv):
    for i, entry in enumerate(cv["education"]):
        start, end, when = timeline_span(entry.get("start"), entry.get("end"))
        school = entry["institution"].split(",")[0]
        degree = strip_markdown(entry["degree"]).split(":")[0]
        yield make_item(
            "work",
            entry.get("kind", "Degree"),
            f"edu{i}",
            entry["degree"],
            f'{entry["institution"]}, {entry["location"]}',
            when,
            start,
            end,
            entry.get("themes"),
            entry.get("items"),
            label=f"{degree}, {INSTITUTION_LABELS.get(school, school)}",
        )


def publication_items(cv):
    publications = cv["publications"]
    groups = (
        ("Publication", publications["refereed"] + publications["thesis"]),
        ("Essay", publications["other"]),
    )
    for kind, entries in groups:
        for i, entry in enumerate(entries):
            start, _ = timeline_position(entry["year"])
            yield make_item(
                "writing",
                kind,
                f"{kind[:3]}{i}",
                linked(entry["title"].rstrip("."), entry.get("url")),
                f'{entry["authors"]}. *{entry["venue"]}*',
                str(entry["year"]),
                start,
                start,
                entry.get("themes"),
                image=entry.get("image"),
            )


def talk_items(cv):
    for i, talk in enumerate(cv["talks"]):
        start, when = timeline_position(talk["date"])
        # `teaching: true` moves a session out of Speaking and in with the courses.
        if talk.get("teaching"):
            band, kind = "teaching", "Session"
        elif talk.get("type") == "workshop":
            band, kind = "speaking", "Workshop"
        else:
            band, kind = "speaking", "Talk"
        yield make_item(
            band,
            kind,
            f"tlk{i}",
            linked(talk["title"], talk.get("url")),
            f'{talk["event"]}, {talk["location"]}',
            when,
            start,
            start,
            talk.get("themes"),
            as_list(talk.get("description")),
            image=talk.get("image"),
        )


def radio_episode(show, show_index, index, episode):
    start, when = timeline_position(episode["date"])
    return {
        "id": f"brd{show_index}-{index}",
        "kind": "Radio episode",
        "title": linked(f'*{episode["title"]}*', episode.get("url")),
        "meta": f'{show["show"]}, {show["outlet"]}. With {episode["with"]}',
        "when": when,
        "start": start,
        "end": start,
        "themes": show["themes"],
        "items": as_list(episode.get("topic")),
        "label": strip_markdown(episode["title"]),
        "image": episode.get("image"),
    }


def broadcast_items(cv):
    for i, show in enumerate(cv["broadcast"]):
        title = linked(f'*{show["show"]}*', show.get("url"))
        meta = f'{show["outlet"]}. {show["role"]}'
        name = strip_markdown(show["show"])
        if "episodes" not in show:
            start, when = timeline_position(show.get("date"))
            yield make_item(
                "speaking",
                "Radio",
                f"brd{i}",
                title,
                meta,
                when,
                start,
                start,
                show.get("themes"),
                as_list(show.get("topic")),
                label=f'{name}, {show["outlet"]}',
            )
            continue

        episodes = [radio_episode(show, i, j, e) for j, e in enumerate(show["episodes"])]
        episodes.sort(key=lambda e: e["start"])
        first, last = episodes[0], episodes[-1]
        yield make_item(
            "speaking",
            "Radio series",
            f"brd{i}",
            title,
            meta,
            f'{first["when"].split()[-1]}–{last["when"].split()[-1]}',
            first["start"],
            last["start"],
            show["themes"],
            [f'{e["when"]}: {e["title"]}, with {e["meta"].split("With ")[-1]}' for e in episodes],
            label=f'{name}, {show["outlet"]} ({len(episodes)} episodes)',
            ticks=episodes,
        )


def course_items(cv):
    for i, course in enumerate(cv["teaching"]["courses"]):
        start, _ = timeline_position(course["year"])
        yield make_item(
            "teaching",
            "Course",
            f"crs{i}",
            linked(course["title"], course.get("url")),
            course["institution"],
            course["term"],
            start,
            start,
            course.get("themes"),
            [course["description"]],
        )


def series_entry(kind, prefix, index, entry):
    start, when = timeline_position(entry["date"])
    meta = role_prefix(entry) + entry["host"]
    if entry.get("location"):
        meta += f', {entry["location"]}'
    return {
        "id": f"{prefix}-{index}",
        "kind": kind,
        "title": linked(f'*{entry["title"]}*', entry.get("url")),
        "meta": meta,
        "when": when,
        "start": start,
        "end": start,
        "themes": entry.get("themes") or ["community"],
        "items": as_list(entry.get("description")),
        "label": strip_markdown(entry["title"]),
        "image": entry.get("image"),
        "credits": entry.get("credits"),
    }


def series_item(kind, prefix, entries, title, meta, label):
    """Group dated entries into one timeline item with a tick per entry."""
    ticks = [series_entry(kind, prefix, i, entry) for i, entry in enumerate(entries)]
    ticks.sort(key=lambda t: t["start"])
    themes = {theme for tick in ticks for theme in tick["themes"]}
    themes = sorted(themes, key=lambda t: (-sum(t in tick["themes"] for tick in ticks), t))
    first, last = ticks[0], ticks[-1]
    return make_item(
        "teaching",
        kind + "s",
        prefix,
        title,
        meta,
        f'{first["when"].split()[-1]}–{last["when"].split()[-1]}',
        first["start"],
        last["start"],
        themes,
        [f'{t["when"]}: {t["title"]}' for t in ticks],
        label=label,
        ticks=ticks,
    )


def organizing_items(cv):
    workshops = cv["teaching"]["workshops"]
    yield series_item(
        "Workshop",
        "wks",
        workshops,
        "Workshops in digital scholarship",
        HARVARD,
        f"Digital-scholarship workshops, Harvard ({len(workshops)})",
    )
    harvard = [e for e in cv["organizing"] if e["host"] == HARVARD]
    others = [e for e in cv["organizing"] if e["host"] != HARVARD]
    yield series_item(
        "Symposium",
        "sym",
        harvard,
        "Art-and-technology events",
        f"{HARVARD}, Cambridge, MA",
        f"ArtTechPsyche, sIGHTLines and other events, Harvard ({len(harvard)})",
    )
    for i, event in enumerate(others):
        start, when = timeline_position(event["date"])
        yield make_item(
            "teaching",
            "Symposium",
            f"org{i}",
            linked(f'*{event["title"]}*', event.get("url")),
            role_prefix(event) + f'{event["host"]}, {event["location"]}',
            when,
            start,
            start,
            event.get("themes"),
            as_list(event.get("description")),
            label=short_label(event["title"]) + f' ({event.get("role", "organizer").lower()})',
            image=event.get("image"),
            credits=event.get("credits"),
        )


def press_items(cv):
    for i, article in enumerate(cv["media"]):
        start, when = timeline_position(article["date"])
        meta = article["outlet"]
        if article.get("mentions"):
            meta += f'. {article["mentions"]}'
        outlet = article["outlet"].split(" (")[0].split(" —")[0]
        yield make_item(
            "press",
            "Press",
            f"prs{i}",
            linked(article["title"], article.get("url")),
            meta,
            when,
            start,
            start,
            article.get("themes"),
            label=f'{outlet}: {short_label(article["title"], 30)}',
            quote=article.get("pull_quote"),
            credits=article.get("credits"),
            image=article.get("image"),
        )


def service_items(cv):
    for i, entry in enumerate(cv["editorial"]):
        start, end, when = timeline_span(
            entry.get("start", entry.get("year")), entry.get("end", entry.get("year"))
        )
        venue = short_label(entry["venue"].split(":")[0].split(" (")[0], 26)
        yield make_item(
            "service",
            "Editorial",
            f"edt{i}",
            entry["role"],
            linked(entry["venue"], entry.get("url")),
            when,
            start,
            end,
            entry["themes"],
            label=f'{entry["role"]}, {venue}',
        )
    for i, entry in enumerate(cv["activities"]):
        start, end, when = timeline_span(entry["start"], entry["end"])
        yield make_item(
            "service",
            "Activity",
            f"act{i}",
            entry["role"],
            f'{entry["organization"]}, {entry["location"]}',
            when,
            start,
            end,
            entry.get("themes"),
            entry["items"],
            label=f'{entry["role"]}, {entry["organization"]}',
        )


def place_spans(cv):
    spans = []
    for place in cv.get("places", []):
        start, end, _ = timeline_span(place["start"], place["end"])
        spans.append({"place": place["place"], "start": start, "end": end})
    return spans


def site_data(cv):
    person = cv["person"]
    sections = (
        experience_items,
        grant_items,
        education_items,
        publication_items,
        talk_items,
        broadcast_items,
        course_items,
        organizing_items,
        press_items,
        service_items,
    )
    name = f'{person["first_name"]} {person["last_name"]}'
    if person.get("suffix"):
        name += f', {person["suffix"]}'
    return {
        "person": {
            "name": name,
            "position": person["position"],
            "summary": person["summary"],
            "linkedin": person["linkedin"],
            "scholar": person["google_scholar"]["id"],
            "photo": person.get("photo"),
        },
        "themes": cv["themes"],
        "items": [item for section in sections for item in section(cv)],
        "places": place_spans(cv),
        "updated": str(cv["meta"]["last_updated"]),
        "bands": BANDS,
    }


def write_site(data):
    shutil.rmtree(OUTPUT, ignore_errors=True)
    OUTPUT.mkdir()
    shutil.copytree(ROOT / "assets", OUTPUT / "assets")
    for name in STATIC_FILES:
        shutil.copy(ROOT / "site" / name, OUTPUT / name)

    template = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (OUTPUT / "index.html").write_text(template.replace("/*DATA*/ null", payload), encoding="utf-8")
    (OUTPUT / ".nojekyll").touch()


def main():
    data = site_data(load_cv())
    write_site(data)
    print(f'Built {OUTPUT / "index.html"} with {len(data["items"])} entries')


if __name__ == "__main__":
    main()
