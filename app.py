import streamlit as st
import re
from pypdf import PdfReader
from docx import Document
import tempfile
import zipfile
import io

# Page config
st.set_page_config(page_title="AI PDF Recommendation Extractor", layout="wide")

# Simple Header (no logo)
st.title("AI PDF Recommendation Extractor")

st.divider()

st.write("Upload PDF files to extract recommendation sections and preview them before downloading.")

# Upload
uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

# Extract text lines
def extract_lines(uploaded_file):
    reader = PdfReader(uploaded_file)
    lines = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            for line in text.split("\n"):
                clean = line.strip()
                if clean:
                    lines.append(clean)

    return lines


# Extract recommendation section
def find_recommendation_section(lines):

    candidates = []

    for i, line in enumerate(lines):
        if re.match(r"^\d+\.\s+", line):
            if "recommend" in line.lower() or "conclusion" in line.lower():

                score = 0

                if re.search(r"\d+$", line):
                    score -= 5

                next_block = " ".join(lines[i+1:i+10])

                if len(next_block.split()) > 20:
                    score += 5

                if "." in next_block:
                    score += 3

                candidates.append((i, score))

    if not candidates:
        return "No recommendation section found"

    start_index = max(candidates, key=lambda x: x[1])[0]

    section_lines = lines[start_index:start_index + 300]
    clean_lines = []

    for line in section_lines:
        l = line.lower()

        if "appendix" in l:
            break
        if re.match(r"^[A-Z]\.", line):
            break
        if re.match(r"^\d+\.\s+", line) and len(clean_lines) > 0:
            break

        clean_lines.append(line)

    return format_output(clean_lines)


# Format output
def format_output(lines):
    output = ""
    paragraph = ""

    for line in lines:
        if len(line.split()) <= 3:
            if paragraph:
                output += paragraph.strip() + "\n\n"
                paragraph = ""
            output += line + "\n"
        else:
            paragraph += line + " "

    if paragraph:
        output += paragraph.strip()

    return output.strip()


# Processing
if uploaded_files:

    if st.button("🚀 Extract Recommendations"):

        zip_buffer = io.BytesIO()

        st.subheader("📄 Preview")

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

            for file in uploaded_files:

                lines = extract_lines(file)
                content = find_recommendation_section(lines)

                # Preview
                st.markdown(f"### {file.name}")
                st.text_area("Extracted Content", content, height=200)

                # Word file
                doc = Document()
                doc.add_heading(f"Recommendations - {file.name}", level=1)
                doc.add_paragraph(content)

                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(temp.name)

                zipf.write(temp.name, file.name.replace(".pdf", "_recommendations.docx"))

        st.success("✅ Done")

        st.download_button(
            "⬇ Download All Files",
            zip_buffer.getvalue(),
            file_name="recommendations.zip",
            mime="application/zip"
        )