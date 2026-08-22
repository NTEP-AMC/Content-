import io
import textwrap
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import requests
import streamlit as st
import google.generativeai as genai

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
    "Upload any topic or news screenshot. The AI will analyze the core issue, brainstorm a visual metaphor, generate a brand-new custom artwork, and build the post."
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

if uploaded_file and api_key and st.button("Generate Original Editorial Post"):
  with st.spinner(
      "Step 1: AI is analyzing the topic and creating a satirical visual"
      " concept..."
  ):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Load uploaded image for Gemini Vision
    input_image = Image.open(uploaded_file)

    # Prompt Gemini to extract topic, write a sarcastic headline, and create an image prompt
    analysis_prompt = f"""
        You are a top editorial cartoonist and political satirist (like The Tatva or R.K. Laxman).
        Analyze this image and the context note: '{extra_prompt}'.
        
        Provide the response in EXACTLY this format:
        HEADLINE: [Write a sharp, punchy, sarcastic editorial headline of 10-15 words in English/Hinglish]
        IMAGE_PROMPT: [Write a detailed visual prompt describing a metaphorical, satirical editorial cartoon or dramatic 2D illustration capturing the essence of the debate. Do not put text in the image. Style: high contrast editorial cartoon, dramatic lighting, detailed, dark theme.]
        """

    response = model.generate_content([analysis_prompt, input_image])
    output_text = response.text

    # Parse headline and image prompt
    headline = "Editorial Analysis"
    image_prompt = "satirical political cartoon editorial illustration"

    for line in output_text.split("\n"):
      if line.startswith("HEADLINE:"):
        headline = line.replace("HEADLINE:", "").strip()
      elif line.startswith("IMAGE_PROMPT:"):
        image_prompt = line.replace("IMAGE_PROMPT:", "").strip()

    st.info(f"**Generated Headline:** {headline}")
    st.caption(f"**Visual Concept Created by AI:** {image_prompt}")

  with st.spinner(
      "Step 2: Generating brand-new original artwork from scratch..."
  ):
    # Call free text-to-image API (Pollinations)
    encoded_prompt = urllib.parse.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1000&nologo=true"

    img_response = requests.get(image_url)
    if img_response.status_code == 200:
      ai_generated_artwork = Image.open(io.BytesIO(img_response.content))
    else:
      st.error("Failed to generate image. Please try again.")
      st.stop()

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

    # Paste Newly Generated AI Artwork
    resized_art = ai_generated_artwork.resize(
        (980, 980), Image.Resampling.LANCZOS
    )
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
    st.image(
        canvas, caption="Final Branded Editorial Post", use_container_width=True
    )

    # Download Button
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=95)
    st.download_button(
        label="Download High-Res Post",
        data=buf.getvalue(),
        file_name="editorial_post.jpg",
        mime="image/jpeg",
    )
