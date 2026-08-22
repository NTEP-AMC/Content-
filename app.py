import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import textwrap

# 1. Inject Custom HTML & CSS for the Streamlit UI
st.set_page_config(page_title="My Meme Studio", layout="centered")
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1 {color: #FF4B4B; font-family: 'Helvetica', sans-serif;}
    .stButton>button {
        background-color: #FF4B4B; color: white; border-radius: 8px; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔥 The Sarcastic News Studio")
st.write("Upload a raw image or screenshot, and we will generate a branded editorial meme.")

# 2. File Uploader
uploaded_file = st.file_uploader("Upload raw image...", type=["jpg", "png", "jpeg"])

# 3. Simulate the LLM (AI) generating a sarcastic headline
# In production, you would pass the uploaded image to Google Gemini Vision or OpenAI here.
headline_text = st.text_input(
    "Generated Headline (Edit if needed):", 
    "When the government promises new roads but you need a boat to cross Ahmedabad traffic today."
)

if uploaded_file and st.button("Generate Branded Meme"):
    # Load the uploaded image
    raw_image = Image.open(uploaded_file)
    
    # 4. PYTHON PIL: Building your custom Theme/Design from scratch
    # We will create an Instagram Portrait canvas (1080 x 1350)
    canvas_width, canvas_height = 1080, 1350
    meme_canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
    draw = ImageDraw.Draw(meme_canvas)
    
    # Resize the raw image to fit nicely in the middle
    target_img_width = 1000
    w_percent = (target_img_width / float(raw_image.size[0]))
    h_size = int((float(raw_image.size[1]) * float(w_percent)))
    resized_raw = raw_image.resize((target_img_width, h_size), Image.Resampling.LANCZOS)
    
    # Paste the image into the center of our white canvas
    img_x = (canvas_width - target_img_width) // 2
    img_y = 400  # Leave top 400px for the headline
    meme_canvas.paste(resized_raw, (img_x, img_y))
    
    # 5. Add Custom Fonts and Text Styling
    # (Make sure to download a font like 'impact.ttf' or 'arial.ttf' to your folder)
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 60) # Bold headline font
        font_watermark = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font_large = ImageFont.load_default()
        font_watermark = ImageFont.load_default()
    
    # Wrap the text so it doesn't go off the screen
    wrapped_text = textwrap.fill(headline_text, width=35)
    
    # Draw the Text (Black text on the White background)
    draw.multiline_text((40, 80), wrapped_text, fill="black", font=font_large, spacing=15)
    
    # 6. Add Your Brand Identity / Watermark at the bottom
    brand_name = "© THE SARCASM INDIA"
    draw.rectangle([(0, 1250), (1080, 1350)], fill="#FF4B4B") # Red footer bar
    draw.text((320, 1280), brand_name, fill="white", font=font_watermark)
    
    # Display the final generated Image in Streamlit
    st.image(meme_canvas, caption="Your Automated Post is Ready", use_container_width=True)
    
    # Allow user to download
    meme_canvas.save("final_post.jpg")
    with open("final_post.jpg", "rb") as file:
        st.download_button(label="Download for Instagram", data=file, file_name="final_post.jpg", mime="image/jpeg")
