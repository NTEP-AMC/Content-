# Content Lab FREE V1

No OpenAI API key required.

## What it does
- Paste an Instagram post/Reel URL
- Optionally enter a topic
- Choose Post or Reel
- Choose a style
- Generate and download an original template-based post/Reel

## Deploy
Upload `app.py`, `requirements.txt`, and `packages.txt` to GitHub and deploy `app.py` on Streamlit Community Cloud.

## Important limitation
Instagram URLs are not scraped or downloaded in this free V1. The URL is used only as a reference identifier. This avoids relying on paid APIs or brittle Instagram scraping.

The next free version can add an upload box for a screenshot/Reel. That lets the app actually inspect the reference visual and reproduce its *design characteristics* without copying the original media.
