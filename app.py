
import io
import re
import html
import subprocess
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter

st.set_page_config(page_title="Content Lab Free", page_icon="🔥", layout="wide")

# ---------- helpers ----------
def font(size, bold=False):
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap_text(draw, text, fnt, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def make_post(headline, sub, source):
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), (12, 12, 16))
    d = ImageDraw.Draw(img)

    # simple gradient-like bands
    for y in range(H):
        v = int(12 + 22 * y / H)
        d.line((0, y, W, y), fill=(v, v, min(255, v + 8)))

    # accent blocks
    d.rounded_rectangle((55, 55, 300, 125), 28, fill=(230, 55, 70))
    d.text((85, 70), "TRENDING", font=font(32, True), fill="white")

    hf = font(78, True)
    sf = font(40, False)
    lines = wrap_text(d, headline, hf, 900)
    y = 210
    for line in lines[:5]:
        d.text((70, y), line, font=hf, fill="white", stroke_width=1, stroke_fill="black")
        y += 94

    d.line((70, y + 20, 1010, y + 20), fill=(130,130,130), width=2)
    y += 65
    for line in wrap_text(d, sub, sf, 900)[:6]:
        d.text((70, y), line, font=sf, fill=(225,225,225))
        y += 55

    d.text((70, 970), source or "Content Lab", font=font(28), fill=(175,175,175))
    return img

def make_reel(headline, sub, source, seconds=8):
    W, H, fps = 1080, 1920, 24
    frames = Path("/tmp/content_lab_frames")
    frames.mkdir(exist_ok=True)
    for p in frames.glob("*.jpg"):
        p.unlink()

    hf, sf = font(92, True), font(48, False)

    total = seconds * fps
    for i in range(total):
        t = i / fps
        img = Image.new("RGB", (W, H), (8, 8, 12))
        d = ImageDraw.Draw(img)

        # animated background bars
        shift = int((t / seconds) * 700)
        d.rectangle((-400 + shift, 0, 900 + shift, H), fill=(25, 25, 35))
        d.rectangle((0, 0, W, 16), fill=(235, 55, 70))
        d.rectangle((0, H-16, W, H), fill=(235, 55, 70))

        d.rounded_rectangle((55, 80, 350, 155), 30, fill=(235, 55, 70))
        d.text((90, 95), "WATCH THIS", font=font(34, True), fill="white")

        # fade/scale-ish timing
        alpha = min(1.0, max(0.0, (t / 0.6))) if t < 0.6 else 1.0
        y = 460
        for line in wrap_text(d, headline, hf, 900)[:5]:
            d.text((70, y), line, font=hf, fill="white", stroke_width=2, stroke_fill="black")
            y += 110

        d.line((70, y+35, 1010, y+35), fill=(150,150,150), width=2)
        y += 90
        for line in wrap_text(d, sub, sf, 900)[:5]:
            d.text((70, y), line, font=sf, fill=(225,225,225))
            y += 62

        d.text((70, 1810), source or "Content Lab", font=font(30), fill=(175,175,175))
        img.save(frames / f"frame_{i:05d}.jpg", quality=88)

    out = "/tmp/content_lab_reel.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(fps), "-i", str(frames / "frame_%05d.jpg"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        out
    ], check=True)
    return out

def extract_caption_hint(url):
    # No scraping service/API is used. We only use the URL itself as the reference.
    m = re.search(r"(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else "reference"

# ---------- UI ----------
st.title("🔥 Content Lab — FREE")
st.caption("Paste a public Instagram URL → create an original post or Reel. No OpenAI API required.")

url = st.text_input("Instagram post / Reel URL", placeholder="https://www.instagram.com/reel/...")
topic = st.text_input("Topic (optional)", placeholder="Example: latest India current event")

col1, col2 = st.columns(2)
with col1:
    output_type = st.radio("Create", ["Post", "Reel"], horizontal=True)
with col2:
    style = st.selectbox("Style", ["News / Current Event", "Meme", "Curiosity", "Political Satire", "Breaking News"])

if st.button("✨ Generate", type="primary", use_container_width=True):
    if not url.strip():
        st.error("Paste an Instagram URL first.")
        st.stop()

    # This free version does not download Instagram media or call a paid AI API.
    # It creates an original template based on the URL + optional topic.
    ref_id = extract_caption_hint(url)
    chosen_topic = topic.strip() or "A current event worth talking about"

    hooks = {
        "News / Current Event": f"WHAT'S HAPPENING WITH {chosen_topic.upper()}?",
        "Meme": f"{chosen_topic.upper()} BE LIKE 💀",
        "Curiosity": f"WAIT… WHAT JUST HAPPENED WITH {chosen_topic.upper()}?",
        "Political Satire": f"POLITICS IN 2026: {chosen_topic.upper()} 💀",
        "Breaking News": f"🚨 BREAKING: {chosen_topic.upper()}",
    }
    headline = hooks[style]
    sub = "A fresh, original template inspired by the reference format — not a copy of the original post."
    source = f"Reference: {ref_id} • Content Lab"

    if output_type == "Post":
        img = make_post(headline, sub, source)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        st.subheader("🎨 Generated Post")
        st.image(buf, use_container_width=True)
        st.download_button("⬇️ Download Post", buf.getvalue(), "content_lab_post.png", "image/png", use_container_width=True)
    else:
        with st.spinner("Rendering Reel..."):
            out = make_reel(headline, sub, source)
        st.subheader("🎬 Generated Reel")
        with open(out, "rb") as f:
            data = f.read()
        st.video(data)
        st.download_button("⬇️ Download Reel", data, "content_lab_reel.mp4", "video/mp4", use_container_width=True)

st.divider()
st.info("FREE V1: template-based generation. The app does not access private Instagram data or copy/download the reference media. For true automatic reference analysis, we can add a free upload-based analyzer next.")
