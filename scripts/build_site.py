"""Builds the website from cv.yaml into _site/. Runs in the GitHub Action on every push.
   Locally: pip install pyyaml && python scripts/build_site.py
   --inline-images embeds local images as data URIs (used for single-file previews)."""
import yaml, json, datetime, re, sys, base64, os
args = [a for a in sys.argv[1:] if not a.startswith("--")]
INLINE = "--inline-images" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = args[0] if args else os.path.join(ROOT, "cv.yaml")
cv = yaml.safe_load(open(SRC))
NOW = 2026.75
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

def parse(d):
    if d is None: return None, ""
    if d == "present": return NOW, "present"
    if isinstance(d, datetime.date): y, m, dd = d.year, d.month, d.day
    else:
        p = str(d).split("-"); y = int(p[0]); m = int(p[1]) if len(p) > 1 else None; dd = int(p[2]) if len(p) > 2 else None
        if m is None: return y + .5, str(y)
    if dd is None: return y + (m - .5) / 12, f"{MON[m-1]} {y}"
    return y + (m - 1 + dd / 31) / 12, f"{dd} {MON[m-1]} {y}"

def span(a, b):
    s, sd = parse(a); e, ed = parse(b)
    if s is None: return e, e, ed
    if e is None: return s, s, sd
    sy = sd.split()[-1]; ey = ed if ed == "present" else ed.split()[-1]
    if sy != ey: return s, e, f"{sy}–{ey}"
    # same year, different months: "Jun–Aug 2006"
    return s, e, (f'{sd.rsplit(" ", 1)[0]}–{ed}' if sd != ed else sd)

def plain(t): return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(t)).replace("*", "")
def short(t, n=38):
    t = plain(t).strip().rstrip(".")
    if ":" in t[:n+6]: t = t.split(":")[0]
    if len(t) > n: t = t[:n].rsplit(" ", 1)[0].rstrip(",;–-") + "…"
    return t
def link(t, u): return f"[{t}]({u})" if u else t
def img(path):
    if not path: return None
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if INLINE and os.path.exists(full):
        return "data:image/jpeg;base64," + base64.b64encode(open(full, "rb").read()).decode()
    return path

INST = {"Harvard University": "Harvard", "University of Massachusetts Amherst": "UMass Amherst",
        "Kwansei Gakuin University": "Kwansei Gakuin", "International Christian University": "ICU"}
items = []
def add(band, kind, iid, title, meta, when, s, e, themes, bullets=None, label=None, **kw):
    it = dict(id=iid, band=band, kind=kind, title=title, meta=meta, when=when, start=s, end=e,
              span=bool(e - s > .3), themes=themes or ["community"], items=bullets or [], label=label or short(title))
    it.update({k: v for k, v in kw.items() if v}); items.append(it); return it

for i, x in enumerate(cv["experience"]):
    s, e, w = span(x.get("start"), x.get("end"))
    add("work", "Position", f"exp{i}", x["title"], f'{x["organization"]}, {x["location"]}', w, s, e, x.get("themes"), x.get("items"),
        label=f'{x["title"]}, {x.get("short_org") or x["organization"].split(",")[0]}', image=img(x.get("image")), credits=x.get("credits"))
for i, x in enumerate(cv["grants"]):
    s, e, w = span(x["start"], x["end"])
    press = [m for u in x.get("press", []) for m in cv["media"] if m.get("url") == u]
    quote = next((m["pull_quote"] for m in press if m.get("pull_quote")), None)
    add("work", "Grant", f"grt{i}", link(x["title"], x.get("url")),
        f'{x["funder"]}, with {x["partner"]}. {x["amount"]}' + (f'. Co-led with {x["co_lead"]}' if x.get("co_lead") else ""), w, s, e, x["themes"],
        [x["description"]] + [f'In the press: {link(m["title"], m["url"])}, *{m["outlet"]}*, {parse(m["date"])[1]}' for m in press],
        label=f'{x["amount"]} R&D project: multilingual, explainable NLP', quote=quote)
for i, x in enumerate(cv["education"]):
    s, e, w = span(x.get("start"), x.get("end"))
    add("work", x.get("kind", "Degree"), f"edu{i}", x["degree"], f'{x["institution"]}, {x["location"]}', w, s, e, x.get("themes"), x.get("items"),
        label=f'{plain(x["degree"]).split(":")[0]}, {INST.get(x["institution"].split(",")[0], x["institution"].split(",")[0])}')

P = cv["publications"]
for kind, lst in (("Publication", P["refereed"] + P["thesis"]), ("Essay", P["other"])):
    for i, x in enumerate(lst):
        s, _ = parse(x["year"])
        add("writing", kind, f"{kind[:3]}{i}", link(x["title"].rstrip("."), x.get("url")), f'{x["authors"]}. *{x["venue"]}*', str(x["year"]), s, s, x.get("themes"), image=img(x.get("image")))

for i, x in enumerate(cv["talks"]):
    s, w = parse(x["date"])
    add("speaking", "Workshop" if x.get("type") == "workshop" else "Talk", f"tlk{i}", link(x["title"], x.get("url")), f'{x["event"]}, {x["location"]}',
        w, s, s, x.get("themes"), [x["description"]] if x.get("description") else [], image=img(x.get("image")))

for i, x in enumerate(cv["broadcast"]):
    if "episodes" in x:
        kids = []
        for j, ep in enumerate(x["episodes"]):
            es, ew = parse(ep["date"])
            kids.append(dict(id=f"brd{i}-{j}", kind="Radio episode", title=link(f'*{ep["title"]}*', ep.get("url")),
                             meta=f'{x["show"]}, {x["outlet"]}. With {ep["with"]}', when=ew, start=es, end=es,
                             themes=x["themes"], items=[ep["topic"]] if ep.get("topic") else [], label=plain(ep["title"]), image=img(ep.get("image"))))
        kids.sort(key=lambda k: k["start"])
        s, e = kids[0]["start"], kids[-1]["start"]
        add("speaking", "Radio series", f"brd{i}", link(f'*{x["show"]}*', x.get("url")), f'{x["outlet"]}. {x["role"]}',
            f'{kids[0]["when"].split()[-1]}–{kids[-1]["when"].split()[-1]}', s, e, x["themes"],
            [f'{k["when"]}: {k["title"]}, with {k["meta"].split("With ")[-1]}' for k in kids],
            label=f'{plain(x["show"])}, {x["outlet"]} ({len(kids)} episodes)', ticks=kids)
    else:
        s, w = parse(x.get("date"))
        add("speaking", "Radio", f"brd{i}", link(f'*{x["show"]}*', x.get("url")), f'{x["outlet"]}. {x["role"]}', w, s, s, x.get("themes"),
            [x["topic"]] if x.get("topic") else [], label=f'{plain(x["show"])}, {x["outlet"]}')

for i, x in enumerate(cv["teaching"]["courses"]):
    s, _ = parse(x["year"])
    add("teaching", "Course", f"crs{i}", link(x["title"], x.get("url")), x["institution"], x["term"], s, s, x.get("themes"), [x["description"]])
def series(band, kind, prefix, lst, title, meta, label):
    kids = []
    for j, x in enumerate(lst):
        es, ew = parse(x["date"])
        kids.append(dict(id=f"{prefix}-{j}", kind=kind, title=link(f'*{x["title"]}*', x.get("url")),
                         meta=(f'{x["role"]}. ' if x.get("role") else "") + f'{x["host"]}' + (f', {x["location"]}' if x.get("location") else ""),
                         when=ew, start=es, end=es, themes=x.get("themes") or ["community"],
                         items=[x["description"]] if x.get("description") else [], label=plain(x["title"]),
                         image=img(x.get("image")), credits=x.get("credits")))
    kids.sort(key=lambda k: k["start"]); th = sorted({t for k in kids for t in k["themes"]}, key=lambda t: (-sum(t in k["themes"] for k in kids), t))
    add(band, kind + "s", prefix, title, meta, f'{kids[0]["when"].split()[-1]}–{kids[-1]["when"].split()[-1]}',
        kids[0]["start"], kids[-1]["start"], th, [f'{k["when"]}: {k["title"]}' for k in kids], label=label, ticks=kids)
series("teaching", "Workshop", "wks", cv["teaching"]["workshops"], "Workshops in digital scholarship", "Harvard University",
       f'Digital-scholarship workshops, Harvard ({len(cv["teaching"]["workshops"])})')
harv = [x for x in cv["organizing"] if x["host"] == "Harvard University"]
series("teaching", "Symposium", "sym", harv, "Art-and-technology events", "Harvard University, Cambridge, MA",
       f'ArtTechPsyche, sIGHTLines and other events, Harvard ({len(harv)})')
for i, x in enumerate([x for x in cv["organizing"] if x["host"] != "Harvard University"]):
    s, w = parse(x["date"])
    add("teaching", "Symposium", f"org{i}", link(f'*{x["title"]}*', x.get("url")),
        (f'{x["role"]}. ' if x.get("role") else "") + f'{x["host"]}, {x["location"]}', w, s, s, x.get("themes"),
        [x["description"]] if x.get("description") else [],
        label=short(x["title"]) + f' ({x.get("role", "organizer").lower()})', image=img(x.get("image")), credits=x.get("credits"))

for i, x in enumerate(cv["media"]):
    s, w = parse(x["date"])
    add("press", "Press", f"prs{i}", link(x["title"], x.get("url")), x["outlet"] + (f'. {x["mentions"]}' if x.get("mentions") else ""), w, s, s, x.get("themes"),
        label=f'{x["outlet"].split(" (")[0].split(" —")[0]}: {short(x["title"], 30)}', quote=x.get("pull_quote"),
        credits=x.get("credits"), image=img(x.get("image")))

for i, x in enumerate(cv["editorial"]):
    s, e, w = span(x.get("start", x.get("year")), x.get("end", x.get("year")))
    add("service", "Editorial", f"edt{i}", x["role"], link(x["venue"], x.get("url")), w, s, e, x["themes"],
        label=f'{x["role"]}, {short(x["venue"].split(":")[0].split(" (")[0], 26)}')
for i, x in enumerate(cv["activities"]):
    s, e, w = span(x["start"], x["end"])
    add("service", "Activity", f"act{i}", x["role"], f'{x["organization"]}, {x["location"]}', w, s, e, x.get("themes"), x["items"],
        label=f'{x["role"]}, {x["organization"]}')

places = []
for x in cv.get("places", []):
    s, e, _ = span(x["start"], x["end"]); places.append({"place": x["place"], "start": s, "end": e})
p = cv["person"]
# no address on the website: it lives in cv.private.yaml, which this script never reads
em = p.get("email")
EMAIL = em if not isinstance(em, dict) else (em["address"] if em.get("public", True) else None)
DATA = {
  "person": {"name": f'{p["first_name"]} {p["last_name"]}' + (f', {p["suffix"]}' if p.get("suffix") else ""),
             "position": p["position"], "summary": p["summary"],
             "email": EMAIL, "linkedin": p["linkedin"], "scholar": p["google_scholar"]["id"]},
  "themes": cv["themes"], "items": items, "places": places, "updated": str(cv["meta"]["last_updated"]),
  "bands": [["work","Work and education"],["writing","Writing"],["speaking","Speaking and radio"],["teaching","Teaching and convening"],
            ["press","In the press"],["service","Service"]],
}
import shutil
OUT = os.path.join(ROOT, "_site")
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
if os.path.isdir(os.path.join(ROOT, "assets")): shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
tpl = open(os.path.join(ROOT, "site", "template.html"), encoding="utf-8").read()
blob = json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(tpl.replace("/*DATA*/null", blob))
open(os.path.join(OUT, ".nojekyll"), "w").close()
print(f"Built _site/index.html with {len(items)} entries")
