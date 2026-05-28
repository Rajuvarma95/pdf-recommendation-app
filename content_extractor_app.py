import streamlit as st
from docx import Document
import tempfile
import zipfile
import io

from extractor import extract_lines, detect_sections, extract_section

st.set_page_config(page_title="AI PDF Content Extractor", layout="wide")

st.title("AI PDF Content Extractor")
st.divider()

uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])

if uploaded_file:

    with st.spinner("⏳ Processing PDF..."):
        lines = extract_lines(uploaded_file)

    sections = detect_sections(lines)
    unique_sections = list(dict.fromkeys(sections))

    if unique_sections:

        st.subheader("📑 Select Sections")

        selected_sections = []

        for i, title in enumerate(unique_sections):
            if st.checkbox(title, key=f"chk_{i}"):
                selected_sections.append(title)

        if st.button("🚀 Extract Selected Sections"):

            zip_buffer = io.BytesIO()
            combined_text = ""

            st.subheader("📄 Preview")

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

                for i, title in enumerate(selected_sections):

                    content = extract_section(lines, title)

                    st.markdown(f"### {title}")
                    st.text_area(
                        f"Content {i}",
                        content,
                        height=200,
                        key=f"text_{i}"
                    )

                    combined_text += f"{title}\n\n{content}\n\n"

                doc = Document()
                doc.add_heading("Extracted Sections", level=1)
                doc.add_paragraph(combined_text)

                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(temp.name)

                zipf.write(temp.name, "sections.docx")

            st.success("✅ Done")

            st.download_button(
                "⬇ Download",
                zip_buffer.getvalue(),
                "sections.zip",
                "application/zip"
            )

    else:
        st.warning("⚠ No TOC detected")