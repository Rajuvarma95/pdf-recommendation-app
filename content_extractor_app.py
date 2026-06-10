import streamlit as st
from docx import Document
import tempfile
import zipfile
import io

from extractor import extract_document, detect_sections, extract_section, clean_for_word, is_main_section_heading, is_subsection_heading, is_plain_subheading, is_numbered_bullet

st.set_page_config(page_title="AI PDF Content Extractor - DEBUG", layout="wide")

st.title("AI PDF Content Extractor - DEBUG")
st.divider()

st.write(
    "Upload one or more PDFs, select sections, run extraction, and inspect debug output."
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
        st.warning("No content extracted for this section.")
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


if "debug_results" not in st.session_state:
    st.session_state["debug_results"] = None

if uploaded_files:

    all_results = []

    for file_index, uploaded_file in enumerate(uploaded_files):
        st.markdown("---")
        st.subheader(f"📄 {uploaded_file.name}")

        with st.spinner(f"Processing {uploaded_file.name}..."):
            doc = extract_document(uploaded_file)
            detected_sections = detect_sections(doc)

        # DEBUG: show total extracted lines
        st.caption(f"Total extracted lines: {len(doc['flat_lines'])}")

        if detected_sections:
            st.markdown("**Detected Sections**")
            for sec in detected_sections:
                st.write(f"- {sec['title']}")

            st.markdown("**Select Sections**")
            selected_sections = []

            for sec_index, sec in enumerate(detected_sections):
                label = sec["title"]
                if st.checkbox(
                    label,
                    key=f"sec_{file_index}_{sec_index}_{sec['num']}"
                ):
                    selected_sections.append(sec)

            st.caption(f"Selected sections count: {len(selected_sections)}")

            all_results.append({
                "file_name": uploaded_file.name,
                "doc": doc,
                "sections": detected_sections,
                "selected_sections": selected_sections
            })
        else:
            st.warning(f"No valid sections were detected in {uploaded_file.name}.")

    if st.button("🚀 Extract Selected Sections From All PDFs"):

        total_selected = sum(len(r["selected_sections"]) for r in all_results)

        if total_selected == 0:
            st.warning("Please select at least one section before extracting.")
        else:
            extracted_payload = []
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

                for result_index, result in enumerate(all_results):
                    file_name = result["file_name"]
                    doc = result["doc"]
                    sections = result["sections"]
                    selected_sections = result["selected_sections"]

                    if not selected_sections:
                        continue

                    file_result = {
                        "file_name": file_name,
                        "items": []
                    }

                    word_doc = Document()
                    word_doc.add_heading(f"Extracted PDF Sections - {file_name}", level=1)

                    for sec in selected_sections:
                        content = extract_section(doc, sections, sec)
                        safe_content = clean_for_word(content)

                        file_result["items"].append({
                            "title": sec["title"],
                            "content": safe_content,
                            "raw_length": len(safe_content)
                        })

                        word_doc.add_heading(sec["title"], level=2)

                        if safe_content:
                            for para in safe_content.split("\n\n"):
                                para = clean_for_word(para).strip()
                                if not para:
                                    continue

                                if is_main_section_heading(para):
                                    word_doc.add_heading(para, level=2)
                                elif is_subsection_heading(para) or is_plain_subheading(para):
                                    word_doc.add_heading(para, level=3)
                                else:
                                    word_doc.add_paragraph(para)
                        else:
                            word_doc.add_paragraph("[No content extracted]")

                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                    word_doc.save(tmp.name)

                    output_name = file_name.rsplit(".", 1)[0] + "_sections.docx"
                    zipf.write(tmp.name, output_name)

                    extracted_payload.append(file_result)

            st.session_state["debug_results"] = {
                "payload": extracted_payload,
                "zip_bytes": zip_buffer.getvalue()
            }

# Always show debug results if available
if st.session_state["debug_results"] is not None:
    st.markdown("---")
    st.subheader("🔍 Debug Preview Results")

    payload = st.session_state["debug_results"]["payload"]

    if not payload:
        st.warning("No extracted results available.")
    else:
        for file_result in payload:
            st.markdown(f"## 📄 {file_result['file_name']}")

            for item in file_result["items"]:
                st.markdown(f"### Section: {item['title']}")
                st.write(f"**Extracted text length:** {item['raw_length']} characters")

                with st.expander("Show raw extracted text"):
                    if item["content"]:
                        st.text(item["content"][:3000])
                    else:
                        st.write("[Empty content]")

                render_preview_block(item["title"], item["content"])

    st.download_button(
        label="⬇ Download All Word Files (ZIP)",
        data=st.session_state["debug_results"]["zip_bytes"],
        file_name="all_extracted_sections.zip",
        mime="application/zip"
    )