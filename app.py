import streamlit as st
import re
from pypdf import PdfReader
from docx import Document
import tempfile
import zipfile
import io

st.title("📄 AI PDF Recommendation Extractor")

uploaded_files = st.file_uploader(
    "Drag & Drop PDF files here",
    type=["pdf"],
    accept_multiple_files=True
)

# ✅ Extract lines
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


# ✅ Detect section
def find_recommendation_section(lines):
    candidates = []

    for i, line in enumerate(lines):
        if re.match(r"^\d+\.\s+", line):
            if ("recommend" in line.lower() or
                "conclusion" in line.lower()):

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


# ✅ Format output
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


# ✅ MAIN PROCESS
if uploaded_files:

    if st.button("🚀 Extract & Download All"):

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

            for file in uploaded_files:

                lines = extract_lines(file)
                content = find_recommendation_section(lines)

                # ✅ Create Word doc
                doc = Document()
                doc.add_heading(f"Recommendations - {file.name}", level=1)
                doc.add_paragraph(content)

                # ✅ Save temp file
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(temp.name)

                # ✅ Add to ZIP
                zipf.write(temp.name, file.name.replace(".pdf", "_recommendations.docx"))

        st.success("✅ All files processed!")

        st.download_button(
            label="⬇ Download ALL Word files (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="all_recommendations.zip",
            mime="application/zip"
        )