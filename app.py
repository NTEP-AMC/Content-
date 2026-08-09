
import io, os, re, html, json, math, subprocess, textwrap, zipfile
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import streamlit as st

st.set_page_config(page_title="Content Lab Free", page_icon="🔥", layout="wide")

W, H = 1080, 1920
UA = {"User-Agent":"Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"}

# ---------------- fonts ----------------
def F(size, bold=False, serif=False):
    paths = []
    if serif:
        paths += ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
    paths += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(draw, text, fnt, width):
    text = re.sub(r"\s+", " ", text).strip()
    out, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if draw.textbbox((0,0), t, font=fnt)[2] <= width:
            line = t
        else:
            if line: out.append(line)
            line = word
    if line: out.append(line)
    return out

def dominant_palette(img):
    im = img.copy().convert("RGB").resize((60,60))
    # average 3 broad zones, then choose a warm accent
    px = list(im.getdata())
    r = sum(p[0] for p in px)//len(px); g = sum(p[1] for p in px)//len(px); b = sum(p[2] for p in px)//len(px)
    bg = (max(8,r//5), max(8,g//5), max(10,b//5))
    # high-contrast accent derived from complementary-ish value
    accent = (min(255, 255-r), min(210, 210-g), min(210, 210-b))
    if sum(accent) < 240: accent = (238, 75, 58)
    return bg, accent

# ---------------- instagram metadata ----------------
def meta_content(soup, prop):
    tag = soup.find("meta", attrs={"property":prop}) or soup.find("meta", attrs={"name":prop})
    return tag.get("content","").strip() if tag else ""

def fetch_reference(url):
    r = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = meta_content(soup, "og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    desc = meta_content(soup, "og:description") or meta_content(soup, "description")
    image_url = meta_content(soup, "og:image")
    canonical = meta_content(soup, "og:url") or url
    img = None
    if image_url:
        ir = requests.get(image_url, headers=UA, timeout=15)
        ir.raise_for_status()
        img = Image.open(io.BytesIO(ir.content)).convert("RGB")
    # clean Instagram boilerplate from description
    desc = re.sub(r"\s+", " ", html.unescape(desc)).strip()
    desc = re.sub(r"^\d[\d,.KMB]*\s+(?:likes?|views?)\s*,?\s*", "", desc, flags=re.I)
    return {"title":title, "description":desc, "image_url":image_url, "canonical":canonical, "image":img}

# ---------------- free content extraction ----------------
STOP = {"instagram","reel","video","watch","follow","india","the","and","for","with","this","that","from"}

def make_headline(meta, topic):
    if topic.strip():
        base = topic.strip()
    else:
        base = meta.get("description") or meta.get("title") or "The story everyone is talking about"
        # keep first useful sentence, remove handle-ish boilerplate
        base = re.split(r"[|•]\s*", base)[0]
        base = re.sub(r"@\w+", "", base).strip()
    base = re.sub(r"\s+", " ", base).strip(" .")
    # short, punchy editorial headline
    if len(base) > 82:
        base = base[:79].rsplit(" ",1)[0] + "…"
    return base

def make_support(meta, headline):
    d = meta.get("description","")
    d = re.sub(r"https?://\S+","",d)
    d = re.sub(r"\s+"," ",d).strip()
    if d and d.lower() != headline.lower():
        if len(d) > 150: d = d[:147].rsplit(" ",1)[0] + "…"
        return d
    return "Here’s the context, the key detail and why people are talking about it."

def split_points(headline, support):
    # 5 editorial scenes; not a factual rewrite
    return [
        ("THE HOOK", headline),
        ("WHAT'S GOING ON", support[:120] if support else headline),
        ("THE KEY DETAIL", "Look at the detail people are missing."),
        ("WHY IT MATTERS", "A small detail can change the whole story."),
        ("YOUR TAKE", "What do you think? Tell us below.")
    ]

# ---------------- image treatment ----------------
def cover_crop(img, size=(W,H), zoom=1.0, x=0.5, y=0.5):
    iw, ih = img.size
    tw, th = size
    scale = max(tw/iw, th/ih) * zoom
    nw, nh = int(iw*scale), int(ih*scale)
    im = img.resize((nw,nh), Image.Resampling.LANCZOS)
    left = max(0, min(nw-tw, int((nw-tw)*x)))
    top = max(0, min(nh-th, int((nh-th)*y)))
    return im.crop((left,top,left+tw,top+th))

def draw_text_block(d, text, x, y, width, size, fill="white", bold=True, serif=False, max_lines=5, spacing=8):
    f = F(size,bold,serif)
    lines = wrap(d,text,f,width)
    lines = lines[:max_lines]
    yy=y
    for line in lines:
        d.text((x,yy),line,font=f,fill=fill,stroke_width=2,stroke_fill=(0,0,0))
        yy += size + spacing
    return yy

# ---------------- reel rendering ----------------
def render_reel(meta, headline, support, style):
    ref = meta.get("image")
    if ref is None:
        ref = Image.new("RGB",(900,1200),(32,32,38))
        rd=ImageDraw.Draw(ref)
        rd.text((70,500),"CONTENT LAB",font=F(70,True),fill="white")

    bg, accent = dominant_palette(ref)
    scenes = split_points(headline,support)
    fps, sec_per = 24, 2.35
    total = int(len(scenes)*sec_per*fps)
    frame_dir = Path("/tmp/content_lab_frames_v2")
    frame_dir.mkdir(exist_ok=True)
    for p in frame_dir.glob("*.jpg"): p.unlink()

    for i in range(total):
        t=i/fps
        scene=min(len(scenes)-1,int(t/sec_per))
        local=(t-scene*sec_per)/sec_per
        label, text=scenes[scene]

        # reference image fills canvas with motion + dark editorial treatment
        zoom=1.03+0.07*local
        x=0.42+0.16*local
        y=0.48+0.04*math.sin(local*math.pi)
        base=cover_crop(ref,(W,H),zoom,x,y)
        base=ImageEnhance.Color(base).enhance(0.82)
        base=ImageEnhance.Contrast(base).enhance(1.08)
        # dark overlay, stronger toward bottom
        ov=Image.new("RGBA",(W,H),(0,0,0,92))
        od=ImageDraw.Draw(ov)
        od.rectangle((0,0,W,430),fill=(0,0,0,150))
        od.rectangle((0,1150,W,H),fill=(0,0,0,165))
        img=Image.alpha_composite(base.convert("RGBA"),ov)
        d=ImageDraw.Draw(img)

        # top brand strip
        d.rectangle((0,0,W,18),fill=accent+(255,))
        d.text((58,62),"CONTENT LAB",font=F(32,True),fill="white")
        d.text((760,66),f"{scene+1:02d}/05",font=F(30,True),fill=(225,225,225))

        # small label
        label_y=205
        d.rounded_rectangle((55,label_y,55+max(210, len(label)*20),label_y+62),radius=18,fill=accent+(245,))
        d.text((78,label_y+12),label,font=F(28,True),fill="white")

        # main headline / support
        if scene==0:
            draw_text_block(d,text,55,330,950,92,fill="white",bold=True,serif=True,max_lines=4,spacing=10)
        elif scene==1:
            draw_text_block(d,text,55,400,930,62,fill="white",bold=True,max_lines=5,spacing=12)
        else:
            draw_text_block(d,text,55,430,930,72,fill="white",bold=True,serif=(style=="Editorial"),max_lines=5,spacing=12)

        # bottom editorial card
        d.rounded_rectangle((45,1575,1035,1805),radius=28,fill=(8,8,12,210))
        d.text((75,1615),"SAVE • SHARE • DISCUSS",font=F(28,True),fill=accent+(255,))
        d.text((75,1680),"Original edit generated from the reference format",font=F(29),fill=(235,235,235))
        d.text((75,1730),"No original Reel footage is copied into this render.",font=F(25),fill=(180,180,180))

        # progress
        progress=(i+1)/total
        d.rounded_rectangle((55,1850,1025,1862),radius=6,fill=(80,80,80,220))
        d.rounded_rectangle((55,1850,55+970*progress,1862),radius=6,fill=accent+(255,))

        # quick scene transition bar
        if local < 0.18:
            alpha=int(255*(1-local/0.18))
            d.rectangle((0,0,W,H),fill=(0,0,0,alpha))

        img.convert("RGB").save(frame_dir/f"frame_{i:05d}.jpg",quality=88)

    out="/tmp/content_lab_reel_v2.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(fps),
                    "-i",str(frame_dir/"frame_%05d.jpg"),
                    "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
                    "-movflags","+faststart",out],check=True)
    return out

# ---------------- post ----------------
def render_post(meta, headline, support, style):
    ref=meta.get("image")
    if ref is None:
        ref=Image.new("RGB",(900,1200),(35,35,42))
    bg,accent=dominant_palette(ref)
    Wp,Hp=1080,1350
    img=cover_crop(ref,(Wp,Hp),1.02,0.5,0.48)
    img=ImageEnhance.Color(img).enhance(0.78)
    img=ImageEnhance.Contrast(img).enhance(1.1)
    ov=Image.new("RGBA",(Wp,Hp),(0,0,0,65))
    od=ImageDraw.Draw(ov)
    od.rectangle((0,0,Wp,360),fill=(0,0,0,185))
    od.rectangle((0,910,Wp,Hp),fill=(0,0,0,170))
    img=Image.alpha_composite(img.convert("RGBA"),ov)
    d=ImageDraw.Draw(img)

    d.rectangle((0,0,Wp,14),fill=accent+(255,))
    d.text((55,48),"CONTENT LAB",font=F(32,True),fill="white")
    d.rounded_rectangle((55,130,300,195),radius=18,fill=accent+(245,))
    d.text((78,144),style.upper(),font=F(26,True),fill="white")
    draw_text_block(d,headline,55,245,950,72,fill="white",bold=True,serif=True,max_lines=4,spacing=8)

    d.rounded_rectangle((45,930,1035,1260),radius=28,fill=(7,7,10,220))
    draw_text_block(d,support,75,985,900,42,fill=(235,235,235),bold=False,max_lines=5,spacing=9)
    d.text((75,1190),"SAVE • SHARE • COMMENT",font=F(28,True),fill=accent+(255,))
    d.text((75,1230),"Original design • Content Lab",font=F(24),fill=(180,180,180))
    return img.convert("RGB")

# ---------------- UI ----------------
st.title("🔥 Content Lab — FREE V2")
st.caption("One link → extract public reference metadata → create an original, editorial-style Post or Reel. No OpenAI API.")

url=st.text_input("Paste ONE public Instagram post / Reel URL",placeholder="https://www.instagram.com/reel/...")
topic=st.text_input("Topic (optional — leave blank to use the public caption/title)",placeholder="e.g. Cabinet reshuffle rumours")

c1,c2,c3=st.columns(3)
with c1: kind=st.selectbox("Output",["Reel (9:16)","Post (4:5)"])
with c2: style=st.selectbox("Design DNA",["Editorial","News","Meme","Political","Archive"])
with c3: source_mode=st.selectbox("Visual treatment",["Reference thumbnail + new layout","Text-led editorial"])

if st.button("🚀 ANALYZE + GENERATE",type="primary",use_container_width=True):
    if not url.strip():
        st.error("Paste an Instagram URL.")
        st.stop()

    with st.spinner("Reading public Instagram metadata…"):
        try:
            meta=fetch_reference(url.strip())
        except Exception as e:
            st.error("Instagram did not expose enough public metadata from this URL.")
            st.info("For the completely free version, use a public post/Reel URL that exposes a preview. If Instagram blocks it, upload the screenshot/video in the next step.")
            st.stop()

    headline=make_headline(meta,topic)
    support=make_support(meta,headline)

    st.success("Reference found. Creating a new original design.")
    with st.expander("Reference analysis"):
        st.write("**Title:**",meta.get("title") or "Not exposed")
        st.write("**Public description:**",meta.get("description") or "Not exposed")
        st.write("**Reference image:**", "Found" if meta.get("image") else "Not exposed")

    if meta.get("image"):
        st.image(meta["image"],caption="Public reference thumbnail used only as a visual input.",width=260)

    if "Reel" in kind:
        with st.spinner("Rendering 5-scene 9:16 Reel…"):
            out=render_reel(meta,headline,support,style)
        data=Path(out).read_bytes()
        st.video(data)
        st.download_button("⬇️ DOWNLOAD REEL (MP4)",data,"content_lab_reel.mp4","video/mp4",use_container_width=True)
    else:
        img=render_post(meta,headline,support,style)
        b=io.BytesIO(); img.save(b,"PNG"); b.seek(0)
        st.image(b.getvalue(),caption="Original 4:5 Instagram post",use_container_width=True)
        st.download_button("⬇️ DOWNLOAD POST (PNG)",b.getvalue(),"content_lab_post.png","image/png",use_container_width=True)

st.divider()
st.markdown("### What this FREE V2 actually does")
st.markdown("""
- **One URL** is enough when Instagram exposes public `og:title`, `og:description` and `og:image`.
- The app creates a **new layout** with 5 animated Reel scenes or a 4:5 post.
- It uses the reference thumbnail as a visual input, with new typography, overlays, motion and composition.
- **No OpenAI key, paid API, or subscription is required.**
- It does **not** claim that a URL gives access to every Instagram Reel. Instagram can block automated access.
""")
