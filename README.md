# tgs-epg

A cloud-hosted **XMLTV EPG for the Sicilian channel _TGS_ (Telegiornale di Sicilia)**.

TGS only publishes its schedule as HTML at <https://tgs.gds.it/guida-tv/> (one day per `?giorno=N`
tab). [`generate.py`](generate.py) scrapes the next 7 days, derives stop times by chaining, and writes
[`tgs.xml`](tgs.xml). A GitHub Action re-runs it every 6 hours and commits the file, so any IPTV app
can attach the guide with a plain URL.

The channel id is **`tgs.gds.it`** — the same id an existing TGS EPG used, so this is a drop-in swap.

## Deploy (once)

1. Public repo `tgs-epg` with: `generate.py`, `tgs.xml`, `.github/workflows/epg.yml`, `README.md`.
2. Actions tab → run **“Generate TGS EPG”** (also runs every 6 hours).
3. Live at `https://raw.githubusercontent.com/<your-username>/tgs-epg/main/tgs.xml`.

## Add it to the app (Movie4All)

Settings ▸ IPTV ▸ edit the **TGS** channel:

| Field | Value |
|-------|-------|
| **EPG URL** | `https://raw.githubusercontent.com/<your-username>/tgs-epg/main/tgs.xml` |
| **EPG channel id / tvg-id** | `tgs.gds.it` |

Then **Save & reload**.

## Notes
- Times are Europe/Rome with a DST-correct offset (`+0200` summer / `+0100` winter).
- HTML-scrape: if TGS restyles `guida-tv`, update the regexes in `generate.py`. Nothing in the app
  changes.
- `?giorno=N` is day-of-week (Sunday=0 … Saturday=6); the script maps each upcoming date to its tab.
