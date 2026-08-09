# Content Lab AI — URL → Original Post/Reel

## What it does

1. Paste a public Instagram post/reel URL.
2. Reads publicly exposed metadata/thumbnail.
3. Uses the OpenAI API to analyse creative DNA: hook, layout, visual style, CTA, pacing and content type.
4. Generates an original visual with GPT Image.
5. Creates an Instagram-ready image post.
6. Creates a simple MP4 editorial reel from generated cards.

## Required

You need an OpenAI API key. OpenAI's current API supports image generation and Sora video generation, but this starter uses GPT Image plus local FFmpeg for the reel so it does not require a Sora video job.

## Streamlit Cloud

Add this secret:

OPENAI_API_KEY = "your-key"

Then deploy `app.py`.

The `packages.txt` file installs FFmpeg.

## Important limitation

Instagram may block automated access to some posts/reels. The app first tries public page metadata. If Instagram blocks the page, use a public URL that exposes metadata. A later version can add a direct upload fallback for screenshots/video files.

## Do not copy

The system analyses the reference's creative structure but generates new copy and artwork. It intentionally does not ask the model to reproduce the original watermark, logo, username, or exact composition.
