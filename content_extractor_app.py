import streamlit as st
from docx import Document
import tempfile
import zipfile
import io

# ✅ Import logic from extractor file
from extractor import extract_lines, detect_sections, extract_section

st.set_page_config(page_title="AI PDF Content Extractor", layout="wide")

st.title("AI PDF Content Extractor")

st.divider()

st.write("📂 Upload a PDF, select sections, preview content, and download results.")

# ✅ Upload PDF
uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])

if uploaded_file:

    lines = extract_lines(uploaded_file)
    sections = detect_sections(lines)

    if sections:

        st.subheader("📑 Select Sections")

        selected_sections = []

        for title, index in sections:
            if st.checkbox(title):
                selected_sections.append((title, index))

        if st.button("🚀 Extract Selected Sections"):

            zip_buffer = io.BytesIO()
            combined_text = ""

            st.subheader("📄 Preview")

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

                for title, index in selected_sections:

                    content = extract_section(lines, index)

                    # ✅ Preview
                    st.markdown(f"### {title}")
                    st.text_area("Content", content, height=200)

                    combined_text += f"{title}\n\n{content}\n\n"

                # ✅ Create Word file
                doc = Document()
                doc.add_heading("Extracted PDF Sections", level=1)
                doc.add_paragraph(combined_text)

                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(temp.name)

                zipf.write(temp.name, "extracted_sections.docx")

            st.success("✅ Extraction Completed!")

            st.download_button(
                "⬇ Download Word File",
                zip_buffer.getvalue(),
                file_name="sections.zip",
                mime="application/zip"
            )

    else:
        st.warning("⚠ No sections detected in this PDF")