# Tag Application Bot

Panel + dropdown + modal -> private application channel with the tag's managers.

## Local run
    pip install -r requirements.txt
    export DISCORD_TOKEN=... APPLICATION_CATEGORY_ID=...
    python bot.py

## Config
- `tags.json`: Roblox group ID + Discord manager role ID for each tag.
- Env vars: `DISCORD_TOKEN`, `APPLICATION_CATEGORY_ID` (never commit these).

## Deploy on Railway
1. Push this repo to GitHub.
2. Railway -> New Project -> Deploy from GitHub repo.
3. Variables tab: add `DISCORD_TOKEN` and `APPLICATION_CATEGORY_ID`.
4. It runs `python bot.py` as a worker (no port/domain needed).
