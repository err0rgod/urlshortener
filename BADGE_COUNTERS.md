# Persistent GitHub Badges

This adds standalone persistent counters without changing the core FlexURL application code.

## What It Counts

- `links_created`: increments whenever a row is inserted into `urldata`.
- `visitors`: increments whenever a row is inserted into `clicklog`.

The counters are stored in `badge_counters`, so deleting links or click logs does not reduce the displayed totals.

## Install Database Counters

Run this once against the production database:

```powershell
python backend/install_badge_counters.py
```

The installer backfills from the existing `urldata` and `clicklog` row counts, then adds PostgreSQL insert triggers for future increments.

## Run The Badge Service

Run this as a separate service:

```powershell
uvicorn backend.badge_counter_app:app --host 0.0.0.0 --port 8010
```

## Markdown

Replace `https://badges.flexurl.app` with the public URL where the badge service is hosted.

```markdown
[![FlexURL Visitors](https://badges.flexurl.app/badge/visitors.svg?left_text=visitors&left_color=BLACK&right_color=GREEN)](https://flexurl.app)

[![FlexURL Links Created](https://badges.flexurl.app/badge/links-created.svg?left_text=links%20created&left_color=BLACK&right_color=GREEN)](https://flexurl.app)
```

Use `units=raw` if you do not want compact values like `1.2K`.
