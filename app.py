
import streamlit as st

st.set_page_config(
    page_title="Content Lab",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.25);
    padding: 12px;
    border-radius: 12px;
}
.small-note {opacity:.7; font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

st.title("🔥 Content Lab")
st.caption("Mobile-first dashboard for discovering, analysing and creating Instagram content.")

# Sidebar
st.sidebar.header("Content Lab")
section = st.sidebar.radio(
    "Go to",
    ["🏠 Dashboard", "🧠 Content Analyzer", "📝 Create Content", "🎨 Templates", "📊 Performance"],
)

if section == "🏠 Dashboard":
    st.subheader("Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ideas", "0")
    c2.metric("Drafts", "0")
    c3.metric("Published", "0")
    c4.metric("Avg. Views", "—")

    st.divider()

    left, right = st.columns([1.4, 1])

    with left:
        st.markdown("### 🚀 Quick Actions")
        a, b = st.columns(2)
        with a:
            if st.button("➕ Add Topic", use_container_width=True):
                st.session_state["section"] = "🧠 Content Analyzer"
        with b:
            if st.button("✍️ Create Post", use_container_width=True):
                st.session_state["section"] = "📝 Create Content"

        st.markdown("### 📌 Workflow")
        st.markdown("""
        **1. Find topic** → **2. Analyse** → **3. Choose format** →  
        **4. Generate content** → **5. Review** → **6. Publish** → **7. Track results**
        """)

    with right:
        st.markdown("### 🔥 Winning Content")
        st.info("No performance data yet. Once you start posting, this area will show your best-performing formats and topics.")

elif section == "🧠 Content Analyzer":
    st.subheader("🧠 Content Analyzer")
    st.caption("Phase 1: enter a topic. AI/content intelligence will be connected later.")

    topic = st.text_area(
        "Topic / news / idea",
        placeholder="Example: A roadways bus reaches a Rajasthan village for the first time...",
        height=120,
    )

    source = st.text_input("Source / reference URL (optional)")
    category = st.selectbox(
        "Category",
        ["Current Event", "Politics", "Meme", "Viral", "History", "Culture", "Sports", "Other"],
    )

    if st.button("Analyse Topic", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("Enter a topic first.")
        else:
            st.success("Topic saved for analysis.")
            st.markdown("### Initial content directions")
            st.write("• Curiosity Reel")
            st.write("• News Reel")
            st.write("• Meme")
            st.write("• Carousel")
            st.caption("These recommendations are placeholders in the starter version.")

elif section == "📝 Create Content":
    st.subheader("📝 Create Content")
    st.caption("Choose a format. Actual rendering/AI generation comes in the next phase.")

    format_type = st.selectbox(
        "Format",
        ["News Reel", "Curiosity Reel", "Political Meme", "Reaction Meme", "Carousel", "Breaking News"],
    )

    headline = st.text_input("Headline / Hook", placeholder="Write the main hook...")
    body = st.text_area("Body / context", height=140)
    cta = st.text_input("CTA", placeholder="What do you think?")

    st.markdown("### Preview")
    st.info(f"{headline or 'Your headline will appear here'}\n\n{body or 'Your content...'}\n\n{cta or 'Your CTA...'}")

    if st.button("Save Draft", type="primary", use_container_width=True):
        st.success("Draft saved (UI demo).")

elif section == "🎨 Templates":
    st.subheader("🎨 Templates")
    templates = [
        ("Tatva-style News Reel", "Real footage + strong headline + short context"),
        ("Curiosity Reel", "Curiosity hook + visual + reveal"),
        ("Political Meme", "Strong visual symbolism + short statement"),
        ("Breaking News", "Breaking headline + what happened + why it matters"),
        ("Reaction Meme", "Reaction image/video + punchline"),
        ("Carousel Explainer", "Hook + 3–5 information slides + CTA"),
    ]
    for name, desc in templates:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(desc)

elif section == "📊 Performance":
    st.subheader("📊 Performance")
    st.caption("This will become the learning system for your page.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Posts analysed", "0")
    c2.metric("Best format", "—")
    c3.metric("Best topic", "—")

    st.info(
        "Later we will enter Instagram metrics such as views, likes, comments, shares and saves. "
        "The dashboard will then identify which formats, topics and hooks work best for your page."
    )

st.divider()
st.caption("Content Lab — starter dashboard • Built for mobile-first use")
