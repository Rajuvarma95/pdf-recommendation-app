import streamlit as st
from docx import Document
import tempfile
import zipfile
import io

from extractor import extract_document, detect_sections, extract_section, clean_for_word, is_main_section_heading, is_subsection_heading, is_plain_subheading, is_numbered_bullet

st.set_page_config(page_title="AI PDF Content Extractor", layout="wide")

st.title("AI PDF Content Extractor")
st.divider()

st.write(
    "Upload one or more PDFs, select main sections, preview extracted content, and download the results."
)

uploaded_files = st.file_uploader(
    "Upload PDF file(s)",
    type=["pdf"],
    accept_multiple_files=True
)


def render_preview_block(title: str, content: str):
    """
    Richer preview to preserve headings, subheadings and bullets visually.
    """
    st.markdown(f"### {title}")

    if not content.strip():
        st.info("No content extracted.")
        return

    for block in content.split("\n\n"):
        line = block.strip()
        if not line:
            continue

        if is_main_section_heading(line):
            st.markdown(f"#### {line}")
        elif is_subsection_heading(line):
            st.markdown(f"**{line}**")
        elif is_plain_subheading(line):
            st.markdown(f"**{line}**")
        elif is_numbered_bullet(line):
            st.markdown(line)
        else:
            st.write(line)


if uploaded_files:

    all_results = []

    for file_index, uploaded_file in enumerate(uploaded_files):
        st.markdown("---")
        st.subheader(f"📄 {uploaded_file.name}")

        with st.spinner(f"Processing {uploaded_file.name}..."):
            doc = extract_document(uploaded_file)
            detected_sections = detect_sections(doc)

        if detected_sections:
            st.markdown("**Select Sections**")

            selected_sections = []

            for sec_index, sec in enumerate(detected_sections):
                label = sec["title"]
                if st.checkbox(
                    label,
                    key=f"sec_{file_index}_{sec_index}_{sec['num']}"
                ):
                    selected_sections.append(sec)

            all_results.append({
                "file_name": uploaded_file.name,
                "doc": doc,
                "sections": detected_sections,
                "selected_sections": selected_sections
            })
        else:
            st.warning(
                f"No valid sections were detected in {uploaded_file.name}."
            )

    if st.button("🚀 Extract Selected Sections From All PDFs"):

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

            for result_index, result in enumerate(all_results):
                file_name = result["file_name"]
