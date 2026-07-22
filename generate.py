#!/usr/bin/env python3
"""Generate an XMLTV EPG for the Sicilian channel "TGS" (Telegiornale di Sicilia).

TGS publishes its schedule only as HTML at https://tgs.gds.it/guida-tv/ , one day per `?giorno=N`
tab (N = day-of-week, Sunday=0 … Saturday=6). This script scrapes the next 7 days, derives stop
times by chaining, and writes tgs.xml — a static file a GitHub Action commits and serves, so an IPTV
app can attach the guide by URL + tvg-id.

Channel id is `tgs.gds.it` to match the id the user's channel already references (drop-in EPG swap).

Stdlib only — runs on a stock GitHub Actions runner.
"""

import re
import sys
import urllib.request
from datetime import datetime, timedelta
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

CHANNEL_ID = "tgs.gds.it"                 # paste this exact string as the app's tvg-id
CHANNEL_NAME = "TGS"
DAYS_AHEAD = 7
ROME = ZoneInfo("Europe/Rome")
URL = "https://tgs.gds.it/guida-tv/?giorno={giorno}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
OUT = "tgs.xml"

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_ITEM = re.compile(r'<li class="television-listing__item.*?</li>', re.S)
_HOURS = re.compile(r'__hours[^>]*>\s*([0-2]?\d)[.:]([0-5]\d)')
_TITLE = re.compile(r'__title">(.*?)</span>', re.S)
_INFO = re.compile(r'__info[^>]*>(.*?)</span>', re.S)


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def fetch_day(giorno: int) -> list:
    """Return [(hh, mm, title, desc)] for one weekday tab, or [] on failure."""
    req = urllib.request.Request(URL.format(giorno=giorno), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            html = r.read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"  ! giorno={giorno}: {e}", file=sys.stderr)
        return []
    html = _COMMENT.sub("", html)                       # drop the commented-out template markup
    rows = []
    for block in _ITEM.findall(html):
        h = _HOURS.search(block)
        t = _TITLE.search(block)
        if not h or not t:
            continue
        title = clean(t.group(1))
        if not title:
            continue
        info = _INFO.search(block)
        rows.append((int(h.group(1)), int(h.group(2)), title, clean(info.group(1)) if info else ""))
    return rows


def xmltv_ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S %z")


def main() -> int:
    today = datetime.now(ROME).replace(hour=0, minute=0, second=0, microsecond=0)

    # Collect every programme across the next 7 days, stamped with its real date.
    events = []   # (start_datetime, title, desc)
    for offset in range(DAYS_AHEAD):
        day = today + timedelta(days=offset)
        giorno = day.isoweekday() % 7                    # Mon..Sun(1..7) → Sun=0 … Sat=6
        for hh, mm, title, desc in fetch_day(giorno):
            events.append((day.replace(hour=hh, minute=mm), title, desc))

    # De-dup identical (start, title) that can repeat, then sort chronologically.
    seen, uniq = set(), []
    for start, title, desc in sorted(events, key=lambda e: e[0]):
        key = (start, title)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((start, title, desc))

    # Stop time = next programme's start (chained). Last one gets a nominal +1h.
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE tv SYSTEM "xmltv.dtd">',
        '<tv generator-info-name="tgs-epg" source-info-name="tgs.gds.it">',
        f'  <channel id="{CHANNEL_ID}">',
        f'    <display-name>{escape(CHANNEL_NAME)}</display-name>',
        '  </channel>',
    ]
    for i, (start, title, desc) in enumerate(uniq):
        stop = uniq[i + 1][0] if i + 1 < len(uniq) else start + timedelta(hours=1)
        if stop <= start:                                 # guard against any out-of-order edge
            stop = start + timedelta(hours=1)
        lines.append(f'  <programme start="{xmltv_ts(start)}" stop="{xmltv_ts(stop)}" channel="{CHANNEL_ID}">')
        lines.append(f'    <title lang="it">{escape(title)}</title>')
        if desc:
            lines.append(f'    <desc lang="it">{escape(desc)}</desc>')
        lines.append('  </programme>')
    lines.append('</tv>')

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {OUT}: {len(uniq)} programmes over {DAYS_AHEAD} day(s) for {CHANNEL_NAME}.")
    if not uniq:
        print("WARNING: no programmes — the TGS page layout may have changed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
