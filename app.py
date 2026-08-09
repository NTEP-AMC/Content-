
import base64
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from openai import OpenAI

st.set_page_config(page_title="Content Lab AI", page_icon="🔥", layout="wide")

# ----------------------------
# Helpers
# ----------------------------
def get_api_key():
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return os.getenv("OPENAI_API_KEY", "")

def extract_instagram_metadata(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0 Mobile Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    r.raise_for_status()
    html = r.text

    def meta(prop):
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(prop)}["\']',
            rf'<meta[^>]+name=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        ]
        for p in patterns:
            m = re.search(p, html, re.I)
            if m:
                return m.group(1).replace("&amp;", "&")
        return ""

    return {
        "title": meta("og:title") or meta("twitter:title"),
        "description": meta("og:description") or meta("description"),
        "image": meta("og:image") or meta("twitter:image"),
        "canonical": meta("og:url") or url,
    }

def download_image(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def image_to_data_url(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def ask_ai(client, reference_image_url, reference_text, custom_topic):
    topic_instruction = (
        f"Use this new topic instead of copying the reference topic: {custom_topic}"
        if custom_topic.strip()
        else "Use the reference's subject/topic as the starting point."
    )

    prompt = f"""
You are the creative director of an Indian Instagram current-events/meme page.

Analyze the reference post/reel ONLY for its creative DNA. Do NOT copy its exact
wording, watermark, username, logo, characters, or composition. Create a new,
original content concept inspired by the useful structural qualities.

Reference metadata:
TITLE: {reference_text.get('title','')}
DESCRIPTION: {reference_text.get('description','')}

{topic_instruction}

Return ONLY valid JSON with these keys:
{{
  "content_type": "news_reel|meme_reel|culture_reel|carousel|image_post",
  "hook": "short scroll-stopping hook",
  "headline": "main on-screen headline",
  "body": "2-4 short sentences of context",
  "cta": "short engagement CTA",
  "topic": "topic",
  "visual_style": "describe visual style",
  "layout": "describe text/layout",
  "motion": "describe simple motion/pacing",
  "music_mood": "describe music mood",
  "design_dna": ["5-8 concise traits"],
  "image_prompt": "original visual-generation prompt with no text/logos/watermarks",
  "reel_plan": [
     {{"time":"0-2s","text":"...","visual":"..."}},
     {{"time":"2-6s","text":"...","visual":"..."}},
     {{"time":"6-9s","text":"...","visual":"..."}},
     {{"time":"9-11s","text":"...","visual":"..."}}
  ]
}}
Keep on-screen text short and mobile readable.
"""

    content = [
        {"type": "input_text", "text": prompt},
    ]
    if reference_image_url:
        content.append({
            "type": "input_image",
            "image_url": reference_image_url,
            "detail": "high",
        })

    response = client.responses.create(
        model="gpt-5",
        input=[{"role": "user", "content": content}],
    )
    raw = response.output_text.strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

def generate_image(client, image_prompt):
    result = client.images.generate(
        model="gpt-image-1",
        prompt=(
            "Create a vertical 4:5 Instagram editorial visual. "
            "No words, no captions, no logos, no watermarks, no social-media UI. "
            + image_prompt
        ),
        size="1024x1536",
        quality="medium",
    )
    b64 = result.data[0].b64_json
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

def load_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def render_card(base, headline, body, cta, size=(1080,1350)):
    img = base.copy().resize(size)
    # dark translucent top/bottom panels
    overlay = Image.new("RGBA", size, (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0,0,size[0],360), fill=(0,0,0,155))
    od.rectangle((0,size[1]-250,size[0],size[1]), fill=(0,0,0,165))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    d = ImageDraw.Draw(img)

    hf = load_font(66)
    bf = load_font(38)
    cf = load_font(34)

    y = 55
    for line in wrap_text(d, headline.upper(), hf, 950)[:4]:
        d.text((65,y), line, font=hf, fill="white", stroke_width=2, stroke_fill="black")
        y += 78

    y = size[1]-220
    for line in wrap_text(d, body, bf, 930)[:3]:
        d.text((65,y), line, font=bf, fill="white", stroke_width=1, stroke_fill="black")
        y += 48

    d.text((65,size[1]-62), cta.upper(), font=cf, fill="white")
    return img.convert("RGB")

def make_reel(cards, durations, out_path):
    # Uses ffmpeg if available. Three/four cards create a simple fast editorial reel.
    tmp = Path(tempfile.mkdtemp(prefix="contentlab_"))
    files = []
    for i, card in enumerate(cards):
        p = tmp / f"card_{i}.jpg"
        card.save(p, quality=92)
        files.append((p, durations[i]))

    ffmpeg = "ffmpeg"
    if subprocess.run(["which", ffmpeg], capture_output=True).returncode != 0:
        raise RuntimeError("ffmpeg is not installed. Add packages.txt with 'ffmpeg' on Streamlit Cloud.")

    concat = tmp / "concat.txt"
    with concat.open("w", encoding="utf-8") as f:
        for p, dur in files:
            f.write(f"file '{p.as_posix()}'\n")
            f.write(f"duration {dur}\n")
        f.write(f"file '{files[-1][0].as_posix()}'\n")

    cmd = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_path)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:])
    return out_path

# ----------------------------
# UI
# ----------------------------
st.title("🔥 Content Lab AI")
st.caption("Paste a public Instagram post/reel URL → analyze its creative DNA → generate an original post or reel.")

if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "meta" not in st.session_state:
    st.session_state.meta = None
if "ref_image" not in st.session_state:
    st.session_state.ref_image = None

with st.sidebar:
    st.header("Settings")
    api_key = get_api_key()
    if api_key:
        st.success("OpenAI API key detected")
    else:
        st.warning("Add OPENAI_API_KEY in Streamlit Secrets.")

    output_type = st.selectbox("Output", ["Both: Post + Reel", "Post only", "Reel only"])
    custom_topic = st.text_input(
        "New topic (optional)",
        placeholder="Leave blank to make a new version of the reference topic",
    )

st.markdown("### 1️⃣ Reference")
url = st.text_input(
    "Instagram post/reel URL",
    placeholder="https://www.instagram.com/reel/...",
)

analyze = st.button("🔍 Analyze + Generate", type="primary", use_container_width=True)

if analyze:
    if not api_key:
        st.error("Open Streamlit Settings → Secrets and add OPENAI_API_KEY.")
        st.stop()
    if not url or "instagram.com" not in url:
        st.error("Please paste a valid Instagram URL.")
        st.stop()

    client = OpenAI(api_key=api_key)

    with st.spinner("Reading the reference..."):
        try:
            meta = extract_instagram_metadata(url)
            st.session_state.meta = meta
        except Exception as e:
            st.error(
                "Instagram did not expose the post data to the server. "
                "This can happen because of Instagram access restrictions. "
                "Try a public post/reel URL or use the upload fallback in the next version."
            )
            st.exception(e)
            st.stop()

    ref_img = None
    if meta.get("image"):
        try:
            ref_img = download_image(meta["image"])
            st.session_state.ref_image = ref_img
        except Exception:
            ref_img = None

    with st.spinner("AI is analysing the design, hook, layout and content pattern..."):
        try:
            analysis = ask_ai(
                client,
                meta.get("image",""),
                meta,
                custom_topic,
            )
            st.session_state.analysis = analysis
        except Exception as e:
            st.error("AI analysis failed.")
            st.exception(e)
            st.stop()

    st.success("Reference analysed.")

    if ref_img:
        st.image(ref_img, caption="Reference thumbnail", width=260)

    analysis = st.session_state.analysis

    st.markdown("### 🧠 Creative DNA")
    a,b,c,d = st.columns(4)
    a.metric("Format", analysis.get("content_type",""))
    b.metric("Hook", analysis.get("hook","")[:24])
    c.metric("Visual", analysis.get("visual_style","")[:24])
    d.metric("CTA", analysis.get("cta","")[:24])

    st.write("**Design DNA:**", " • ".join(analysis.get("design_dna", [])))
    st.write("**Headline:**", analysis.get("headline",""))
    st.write("**Body:**", analysis.get("body",""))

    with st.spinner("Creating an original visual..."):
        try:
            generated = generate_image(client, analysis["image_prompt"])
        except Exception as e:
            st.error("Image generation failed. Check your OpenAI API access/billing.")
            st.exception(e)
            st.stop()

    post = render_card(
        generated,
        analysis["headline"],
        analysis["body"],
        analysis["cta"],
    )

    st.markdown("### 🎨 Generated Post")
    st.image(post, use_container_width=True)

    post_path = Path(tempfile.gettempdir()) / "content_lab_post.jpg"
    post.save(post_path, quality=94)

    if output_type in ["Both: Post + Reel", "Post only"]:
        with open(post_path, "rb") as f:
            st.download_button(
                "⬇️ Download Post",
                f,
                file_name="instagram_post.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )

    if output_type in ["Both: Post + Reel", "Reel only"]:
        st.markdown("### 🎬 Generated Reel")
        # Make four editorial cards from one original visual.
        plan = analysis.get("reel_plan", [])
        cards = []
        if not plan:
            plan = [
                {"text": analysis["hook"]},
                {"text": analysis["headline"]},
                {"text": analysis["body"]},
                {"text": analysis["cta"]},
            ]
        for item in plan[:4]:
            cards.append(render_card(
                generated,
                item.get("text", analysis["headline"]),
                "",
                analysis["cta"],
                size=(1080,1920),
            ))

        reel_path = Path(tempfile.gettempdir()) / "content_lab_reel.mp4"
        try:
            make_reel(cards, [2.0, 3.0, 3.0, 2.0], reel_path)
            st.video(str(reel_path))
            with open(reel_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Reel",
                    f,
                    file_name="instagram_reel.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
        except Exception as e:
            st.warning("The post was generated, but Reel rendering failed.")
            st.exception(e)

st.divider()
st.caption(
    "Important: the generator uses the reference as inspiration for creative structure. "
    "It creates new copy and a new visual; it does not intentionally reproduce the reference's watermark or exact artwork."
)
