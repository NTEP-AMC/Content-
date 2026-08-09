
import io, re, html
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps
import streamlit as st

st.set_page_config(page_title="Content Lab — Reference Clone", page_icon="🎨", layout="wide")

# ---------- fonts ----------
def get_font(size, bold=False, serif=False):
    names = []
    if serif:
        names += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
        ]
    names += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in names:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(draw, text, font, width):
    words = re.sub(r"\s+", " ", text.strip()).split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

# ---------- instagram public preview ----------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"
}

def og(soup, name):
    tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
    return tag.get("content", "").strip() if tag else ""

def get_instagram_preview(url):
    r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = og(soup, "og:title")
    desc = og(soup, "og:description")
    image_url = og(soup, "og:image")
    if not image_url:
        raise RuntimeError("Instagram did not expose a public preview image.")
    ir = requests.get(image_url, headers=HEADERS, timeout=15)
    ir.raise_for_status()
    image = Image.open(io.BytesIO(ir.content)).convert("RGB")
    return image, title, desc

# ---------- color/layout detection ----------
def analyze_reference(img):
    # This is deliberately deterministic/free: no paid AI.
    w, h = img.size
    ratio = w / h

    # Sample broad regions to estimate background/text zones.
    small = img.resize((120, 120)).convert("RGB")
    pix = list(small.getdata())
    avg = tuple(sum(p[i] for p in pix) // len(pix) for i in range(3))

    # Estimate whether top area is dark/light.
    top = img.crop((0, 0, w, int(h * .32))).resize((80, 80)).convert("L")
    top_avg = sum(top.getdata()) / (80 * 80)
    dark_top = top_avg < 105

    # Choose a high-contrast accent based on reference average.
    if avg[0] > avg[1] * 1.15 and avg[0] > avg[2] * 1.15:
        accent = (225, 68, 60)
    elif avg[1] > avg[0] * 1.12:
        accent = (52, 160, 95)
    elif avg[2] > avg[0] * 1.15:
        accent = (55, 110, 210)
    else:
        accent = (185, 45, 90)

    return {
        "ratio": ratio,
        "dark_top": dark_top,
        "accent": accent,
        "average": avg,
        "top_height": 0.30 if dark_top else 0.24,
        "image_start": 0.30 if dark_top else 0.22,
    }

# ---------- create original post using detected structure ----------
def make_clone_post(reference, analysis, headline, subheadline, brand):
    OUT_W, OUT_H = 1080, 1350

    # The reference is treated as a visual/layout reference.
    # We create a NEW composition; original reference text/logo is not copied.
    ref = ImageOps.fit(reference, (OUT_W, 950), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))
    ref = ImageEnhance.Color(ref).enhance(0.88)
    ref = ImageEnhance.Contrast(ref).enhance(1.06)

    canvas = Image.new("RGB", (OUT_W, OUT_H), (8, 8, 10))
    d = ImageDraw.Draw(canvas)

    # Top headline zone — modeled after the reference's measured top area.
    top_h = int(analysis["top_height"] * OUT_H)
    if analysis["dark_top"]:
        d.rectangle((0, 0, OUT_W, top_h), fill=(8, 8, 10))
        text_color = "white"
    else:
        d.rectangle((0, 0, OUT_W, top_h), fill=(245, 245, 242))
        text_color = (20, 20, 20)

    # Small brand
    d.text((54, 35), brand.upper(), font=get_font(27, True), fill=text_color)

    # Headline
    headline_font = get_font(60, True, serif=True)
    lines = wrap(d, headline, headline_font, 950)[:4]
    y = 105
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=headline_font)
        x = (OUT_W - (bbox[2] - bbox[0])) // 2
        d.text((x, y), line, font=headline_font, fill=text_color, stroke_width=1,
               stroke_fill=(0,0,0) if text_color == "white" else (245,245,242))
        y += 68

    # Image area
    canvas.paste(ref, (0, top_h))

    # Strong lower readability gradient
    overlay = Image.new("RGBA", (OUT_W, OUT_H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for yy in range(800, OUT_H):
        alpha = int(35 + 170 * ((yy - 800) / (OUT_H - 800)))
        od.line((0, yy, OUT_W, yy), fill=(0,0,0,min(alpha,205)))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    d = ImageDraw.Draw(canvas)

    # Editorial caption box
    box_y = 960
    accent = analysis["accent"]
    d.rounded_rectangle((48, box_y, 1032, 1245), radius=18,
                        fill=(5,5,8,225), outline=accent+(255,), width=3)

    # Small label
    d.rounded_rectangle((75, box_y+30, 300, box_y+82), radius=14, fill=accent+(255,))
    d.text((94, box_y+40), "THE STORY", font=get_font(24, True), fill="white")

    sub_font = get_font(39, False)
    sy = box_y + 112
    for line in wrap(d, subheadline, sub_font, 890)[:5]:
        d.text((78, sy), line, font=sub_font, fill=(238,238,238))
        sy += 48

    d.text((78, 1190), "SAVE • SHARE • DISCUSS", font=get_font(25, True), fill=accent+(255,))
    d.text((78, 1230), brand, font=get_font(23), fill=(170,170,170))

    return canvas.convert("RGB")

# ---------- UI ----------
st.title("🎨 Content Lab — Reference Clone")
st.caption("Reference → detect structure → create a NEW post with the same design logic. Free; no OpenAI API.")

st.info(
    "For the most reliable free workflow, upload the reference screenshot from Instagram. "
    "A URL is also supported when Instagram exposes its public preview image."
)

url = st.text_input("1. Instagram post / Reel URL", placeholder="https://www.instagram.com/reel/...")
uploaded = st.file_uploader("OR upload the reference screenshot (recommended)", type=["png","jpg","jpeg","webp"])

if "reference" not in st.session_state:
    st.session_state.reference = None

if st.button("🔎 GET REFERENCE", use_container_width=True):
    if uploaded:
        st.session_state.reference = Image.open(uploaded).convert("RGB")
        st.success("Reference screenshot loaded.")
    elif url.strip():
        try:
            with st.spinner("Getting public Instagram preview…"):
                img, title, desc = get_instagram_preview(url.strip())
            st.session_state.reference = img
            st.success("Public preview loaded.")
            if title:
                st.caption("Reference title: " + title)
        except Exception as e:
            st.error("Instagram blocked or did not expose a preview image.")
            st.warning("Upload the Instagram screenshot instead. This is the reliable FREE fallback.")
    else:
        st.error("Paste a URL or upload a screenshot.")

ref = st.session_state.reference
if ref:
    st.divider()
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Reference")
        st.image(ref, use_container_width=True)
    with right:
        analysis = analyze_reference(ref)
        st.subheader("Detected design")
        st.write("**Format ratio:**", f"{analysis['ratio']:.2f}")
        st.write("**Top zone:**", "Dark editorial" if analysis["dark_top"] else "Light editorial")
        st.write("**Estimated image zone:**", f"{int(analysis['image_start']*100)}% onward")
        st.write("**Accent:**", str(analysis["accent"]))

        st.divider()
        headline = st.text_area(
            "2. NEW headline",
            placeholder="Write the headline for your new post",
            height=100
        )
        sub = st.text_area(
            "3. NEW supporting text",
            placeholder="1–4 short lines explaining the new story",
            height=120
        )
        brand = st.text_input("Your page name", value="Content Lab")

        if st.button("✨ CREATE NEW POST", type="primary", use_container_width=True):
            if not headline.strip():
                st.error("Enter a new headline.")
                st.stop()
            if not sub.strip():
                sub = "The key details behind this story — explained simply."
            with st.spinner("Building the new creative from the reference structure…"):
                result = make_clone_post(ref, analysis, headline.strip(), sub.strip(), brand.strip() or "Content Lab")

            b = io.BytesIO()
            result.save(b, format="PNG")
            data = b.getvalue()

            st.subheader("NEW CREATIVE")
            st.image(data, use_container_width=True)
            st.download_button(
                "⬇️ DOWNLOAD POST",
                data,
                "content_lab_reference_clone.png",
                "image/png",
                use_container_width=True
            )

st.divider()
st.caption(
    "This version copies the reference's general composition/layout logic, not its original text or branding. "
    "It does not bypass Instagram login/private content or download protected media."
)
