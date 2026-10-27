"""Assemble the two project pages and a landing page from site/*.html plus the shared CSS and JS.

docs/                        GitHub Pages: index.html (landing), connectivity/, measures/; data in docs/data,
                             images in docs/img, shared by both pages
site/dist/<page>/page.html   claude.ai previews; docs/data and docs/img are published next to each page

Cross-links in the previews point to the other preview, whose URL is read from site/previews.json
({"connectivity": url, "measures": url}); a page without a known URL links to "#".
"""
import json
import shutil

from bgreen.config import ROOT

SITE = ROOT / "site"
DOCS = ROOT / "docs"
GITHUB = "https://github.com/m-erts/belgrade-green"
PAGES = {"connectivity": "measures", "measures": "connectivity"}
NEW_TAB = ' target="_blank" rel="noopener"'


def fill(name: str, base: str, other: str, other_target: str) -> str:
    s = (SITE / f"{name}.html").read_text()
    parts = {"{{LEAFLET_CSS}}": (SITE / "leaflet.css").read_text(), "{{COMMON_CSS}}": (SITE / "common.css").read_text(),
             "{{COMMON_JS}}": (SITE / "common.js").read_text(), "{{BASE}}": base, "{{OTHER}}": other,
             "{{OTHER_TARGET}}": other_target, "{{GITHUB}}": GITHUB}
    for k, v in parts.items():
        s = s.replace(k, v)
    assert "{{" not in s, f"unfilled placeholder in {name}"
    return s


def document(body: str) -> str:
    """Head (title, meta, styles) goes before the first markup; the claude.ai preview adds this wrapper itself."""
    cut = body.index('<div class="bar">')
    return ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + body[:cut] + "</head>\n<body>\n" + body[cut:] + "\n</body>\n</html>\n")


if __name__ == "__main__":
    f = SITE / "previews.json"
    previews = json.loads(f.read_text()) if f.exists() else {}
    for page, other in PAGES.items():
        out = DOCS / page
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(document(fill(page, "../", f"../{other}/", "")))
        dist = SITE / "dist" / page
        dist.mkdir(parents=True, exist_ok=True)
        body = fill(page, "", previews.get(other) or "#", NEW_TAB if previews.get(other) else "")
        (dist / "page.html").write_text(body)
        print(f"docs/{page}/index.html; site/dist/{page}/page.html", len(body), "chars")
    (DOCS / "img").mkdir(exist_ok=True)
    for png in (SITE / "img").glob("*.png"):
        shutil.copy(png, DOCS / "img" / png.name)
    (DOCS / "index.html").write_text(document(fill("landing", "", "", "")))
    print("docs/index.html")
