import io
import math
import random
import textwrap
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import streamlit as st

# --- PAGE CONFIG & STYLING ---
st.set_page_config(page_title="AI Editorial Studio", layout="centered")
st.markdown(
    """
    <style>
    .main {background-color: #121212; color: #E0E0E0;}
    h1 {color: #FF3B30;}
    .stButton>button {background-color: #FF3B30; color: white; border-radius: 8px; font-weight: bold;}
    </style>
""",
    unsafe_allow_html=True,
)

st.title("⚡ AI Satirical Editorial Studio")
st.write(
    "Upload any topic or news screenshot. The AI writes the headline and visual concept, "
    "and the app renders a brand-new, original artwork itself (no external image API), "
    "then builds the final branded post."
)

# Configure Gemini API Key
api_key = st.text_input(
    "Enter your Google Gemini API Key:",
    type="password",
    help="Get a free key from Google AI Studio",
)
uploaded_file = st.file_uploader(
    "Upload news screenshot or topic reference...", type=["jpg", "png", "jpeg"]
)
extra_prompt = st.text_input(
    "Specific angle or topic note (Optional):",
    placeholder="e.g., Reservation system debate, cutoffs, merit vs opportunity",
)

# ---------------------------------------------------------------------------
# SELF-MADE ARTWORK ENGINE (pure PIL, no external image generation service)
# ---------------------------------------------------------------------------

# A handful of high-contrast "editorial" palettes. One is picked deterministically
# from the prompt text so the same topic gets a consistent look, but different
# topics vary.
PALETTES = [
    {"bg1": (10, 10, 14), "bg2": (40, 6, 10), "accent": (255, 59, 48), "accent2": (255, 180, 60)},
    {"bg1": (8, 12, 18), "bg2": (10, 30, 46), "accent": (0, 200, 255), "accent2": (255, 255, 255)},
    {"bg1": (14, 10, 4), "bg2": (46, 26, 4), "accent": (255, 170, 0), "accent2": (255, 59, 48)},
    {"bg1": (12, 8, 16), "bg2": (36, 8, 44), "accent": (200, 60, 255), "accent2": (255, 59, 48)},
    {"bg1": (6, 14, 10), "bg2": (10, 40, 26), "accent": (60, 255, 140), "accent2": (255, 255, 255)},
]


def pick_palette(seed_text: str) -> dict:
    rnd = random.Random(seed_text)
    return rnd.choice(PALETTES)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def diagonal_gradient(w, h, color1, color2):
    """Fast diagonal gradient using numpy-free pixel math via row scaling."""
    base = Image.new("RGB", (w, h))
    px = base.load()
    max_d = w + h
    # Precompute per-diagonal-step colors, then fill (much faster than per-pixel loop calls)
    steps = 256
    ramp = [lerp(color1, color2, i / (steps - 1)) for i in range(steps)]
    for y in range(h):
        for_x_base = y
        for x in range(w):
            t = (x + y) / max_d
            idx = min(steps - 1, int(t * (steps - 1)))
            px[x, y] = ramp[idx]
    return base


def radial_spotlight(w, h, center, radius, color, strength=140):
    """Returns an RGBA overlay with a soft radial light burst."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    cx, cy = center
    steps = 60
    for i in range(steps, 0, -1):
        r = radius * (i / steps)
        alpha = int(strength * (1 - i / steps) ** 2)
        odraw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(color[0], color[1], color[2], alpha),
        )
    return overlay.filter(ImageFilter.GaussianBlur(30))


def add_grain(img: Image.Image, intensity: int = 14) -> Image.Image:
    """Cheap film-grain texture for an editorial/print feel."""
    w, h = img.size
    noise = Image.effect_noise((w, h), intensity).convert("L")
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, noise_rgb, alpha=0.06)


def draw_crack_motif(draw, w, h, origin, color, branches=5, seed=0):
    """Jagged lightning-bolt / crack lines radiating from a point — a common
    editorial-cartoon device for 'fracture / conflict / breaking point'."""
    rnd = random.Random(seed)
    for _ in range(branches):
        x, y = origin
        angle = rnd.uniform(0, 2 * math.pi)
        length = rnd.randint(int(h * 0.25), int(h * 0.5))
        segments = rnd.randint(5, 9)
        pts = [(x, y)]
        for _ in range(segments):
            angle += rnd.uniform(-0.6, 0.6)
            seg_len = length / segments
            x += math.cos(angle) * seg_len
            y += math.sin(angle) * seg_len
            pts.append((x, y))
        width = rnd.randint(3, 7)
        draw.line(pts, fill=color, width=width, joint="curve")


def draw_silhouette_figure(draw, w, h, color, pose="fist"):
    """A simple, bold human silhouette built from primitive shapes — head,
    torso, raised arm — rendered flat/dark so it reads as a dramatic cutout
    against the gradient, à la editorial cartoon staging."""
    cx = w * 0.72
    ground_y = h * 0.92
    head_r = w * 0.045

    # Legs
    draw.polygon(
        [
            (cx - 30, ground_y), (cx - 55, h * 0.65),
            (cx - 10, h * 0.65), (cx, ground_y),
        ],
        fill=color,
    )
    draw.polygon(
        [
            (cx + 10, ground_y), (cx + 5, h * 0.65),
            (cx + 45, h * 0.65), (cx + 55, ground_y),
        ],
        fill=color,
    )
    # Torso
    draw.polygon(
        [
            (cx - 45, h * 0.65), (cx - 55, h * 0.42),
            (cx + 45, h * 0.40), (cx + 50, h * 0.65),
        ],
        fill=color,
    )
    # Raised arm
    if pose == "fist":
        draw.line([(cx - 30, h * 0.45), (cx - 70, h * 0.18)], fill=color, width=34, joint="curve")
        draw.ellipse(
            [cx - 90, h * 0.14, cx - 90 + head_r * 1.6, h * 0.14 + head_r * 1.6],
            fill=color,
        )
    # Head
    draw.ellipse(
        [cx - head_r, h * 0.34 - head_r * 2, cx + head_r, h * 0.34],
        fill=color,
    )


def draw_halftone_band(draw, w, y_top, y_bottom, color, spacing=18, max_r=6):
    """A row of halftone-style dots fading out — classic print/editorial texture."""
    y = y_top
    row = 0
    while y < y_bottom:
        x = 0
        col = 0
        while x < w:
            t = (y - y_top) / max(1, (y_bottom - y_top))
            r = max_r * (1 - t)
            if r > 0.5:
                draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
            x += spacing
            col += 1
        y += spacing
        row += 1


def generate_editorial_artwork(prompt_text: str, headline: str, size=(980, 980)) -> Image.Image:
    """
    Builds an original, self-made illustration entirely with PIL — no external
    text-to-image API involved. The look is deterministic-but-varied based on
    the AI-written prompt/headline text, so different topics get different
    palettes and crack/silhouette layouts while staying visually consistent
    with the 'dark, high-contrast editorial cartoon' brief.
    """
    w, h = size
    seed_text = (headline + "|" + prompt_text).strip() or "editorial"
    palette = pick_palette(seed_text)
    rnd = random.Random(seed_text)

    # 1. Gradient base
    art = diagonal_gradient(w, h, palette["bg1"], palette["bg2"])
    draw = ImageDraw.Draw(art, "RGBA")

    # 2. Spotlight burst behind the "action"
    spotlight_center = (int(w * rnd.uniform(0.3, 0.6)), int(h * rnd.uniform(0.3, 0.5)))
    spot = radial_spotlight(w, h, spotlight_center, radius=w * 0.55, color=palette["accent"], strength=160)
    art.paste(Image.alpha_composite(art.convert("RGBA"), spot).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(art, "RGBA")

    # 3. Crack / fracture motif for visual drama
    draw_crack_motif(draw, w, h, spotlight_center, palette["accent2"], branches=rnd.randint(4, 6), seed=hash(seed_text) % 10_000)

    # 4. Bold silhouette figure as the focal subject
    draw_silhouette_figure(draw, w, h, color=(15, 15, 15), pose="fist")
    # Rim-light edge on the silhouette for a "dramatic lighting" feel
    draw_silhouette_figure(draw, w, h, color=(*palette["accent"], 40), pose="fist")

    # 5. Halftone texture band along the bottom for a print/editorial finish
    draw_halftone_band(draw, w, int(h * 0.75), h, color=(*palette["accent2"], 60), spacing=16, max_r=5)

    # 6. Vignette
    vignette = Image.new("L", (w, h), 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse([-w * 0.2, -h * 0.2, w * 1.2, h * 1.2], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    art = Image.composite(art, dark, vignette)

    # 7. Grain for texture
    art = add_grain(art, intensity=16)

    return art


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

if uploaded_file and api_key and st.button("Generate Original Editorial Post"):
    with st.spinner("Step 1: AI is analyzing the topic and creating a satirical visual concept..."):

        # 1. Prepare the image as Base64 for the REST API
        input_image = Image.open(uploaded_file)
        buffered = io.BytesIO()
        input_image.convert("RGB").save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 2. Formulate the prompt
        analysis_prompt = f"""
            You are a top editorial cartoonist and political satirist (like The Tatva or R.K. Laxman).
            Analyze this image and the context note: '{extra_prompt}'.

            Provide the response in EXACTLY this format:
            HEADLINE: [Write a sharp, punchy, sarcastic editorial headline of 10-15 words in English/Hinglish]
            IMAGE_PROMPT: [Write a short visual concept/mood description — colors, tone, energy — for a
            dark, high-contrast editorial cartoon. Do not describe exact text/logos, just mood and theme.]
            """

        # 3. Direct REST API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [
                    {"text": analysis_prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                ]
            }]
        }

        try:
            api_response = requests.post(url, headers=headers, json=payload, timeout=60)
            api_response.raise_for_status()
            output_text = api_response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            st.error(f"API Error: {api_response.text if 'api_response' in locals() else str(e)}")
            st.stop()

        # Parse headline and image prompt
        headline = "Editorial Analysis"
        image_prompt = "dark high-contrast satirical editorial mood"

        for line in output_text.split("\n"):
            if line.startswith("HEADLINE:"):
                headline = line.replace("HEADLINE:", "").strip()
            elif line.startswith("IMAGE_PROMPT:"):
                image_prompt = line.replace("IMAGE_PROMPT:", "").strip()

        st.info(f"**Generated Headline:** {headline}")
        st.caption(f"**Visual Concept:** {image_prompt}")

    with st.spinner("Step 2: Rendering original artwork (built entirely by this app, no external image API)..."):
        ai_generated_artwork = generate_editorial_artwork(image_prompt, headline, size=(980, 980))

    with st.spinner("Step 3: Assembling the final branded post..."):
        # Create final Instagram canvas (1080 x 1440)
        canvas_w, canvas_h = 1080, 1440
        canvas = Image.new("RGB", (canvas_w, canvas_h), color="#0F0F0F")
        draw = ImageDraw.Draw(canvas)

        # Load fonts
        try:
            headline_font = ImageFont.truetype("arialbd.ttf", 46)
            tag_font = ImageFont.truetype("arialbd.ttf", 26)
            footer_font = ImageFont.truetype("arial.ttf", 32)
        except IOError:
            headline_font = ImageFont.load_default()
            tag_font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # Draw Category Tag
        draw.rectangle([(50, 45), (260, 85)], fill="#FF3B30")
        draw.text((65, 52), "OPINION / EDITORIAL", fill="white", font=tag_font)

        # Wrap and Draw Headline
        wrapped_headline = textwrap.fill(headline, width=38)
        draw.multiline_text(
            (50, 110), wrapped_headline, fill="#FFFFFF", font=headline_font, spacing=10
        )

        # Paste self-made artwork
        resized_art = ai_generated_artwork.resize((980, 980), Image.Resampling.LANCZOS)
        canvas.paste(resized_art, (50, 360))

        # Bottom Branding Bar
        draw.line([(50, 1370), (1030, 1370)], fill="#333333", width=2)
        draw.text(
            (50, 1385),
            "THE UNFILTERED TRUTH  •  SWIPE FOR MORE",
            fill="#888888",
            font=footer_font,
        )

        # Display Result
        st.success("Post Created!")
        st.image(canvas, caption="Final Branded Editorial Post", use_container_width=True)

        # Download Button
        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=95)
        st.download_button(
            label="Download High-Res Post",
            data=buf.getvalue(),
            file_name="editorial_post.jpg",
            mime="image/jpeg",
        )
