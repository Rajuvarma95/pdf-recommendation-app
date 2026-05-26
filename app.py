import streamlit as st
import re
from pypdf import PdfReader
from docx import Document
import tempfile
import zipfile
import io

# ✅ Page config
st.set_page_config(page_title="AI PDF Recommendation Extractor", layout="wide")

# ✅ LOGO + HEADER
col1, col2 = st.columns([1, 6])

with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Atkins_logo.svg/2560px-Atkins_logo.svg.png", width=120)

with col2:
    st.title("AI PDF Recommendation Extractor")

st.markdown("---")

st.write("📂 Upload one or more PDF files to extract recommendation sections and preview them before download.")

# ✅ Upload PDFs
uploaded_files = st.file_uploader(
    "Upload PDF files",
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


# ✅ Detect recommendation/conclusion section
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
        return "❌ No recommendation section found"

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

    if st.button("🚀 Process PDFs"):

        zip_buffer = io.BytesIO()

        st.subheader("📊 Preview of Extracted Recommendations")

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zipf:

            for file in uploaded_files:

                lines = extract_lines(file)
                content = find_recommendation_section(lines)

                # ✅ Preview (nice formatting)
                st.markdown(f"### 📄 {file.name}")
                st.text_area("Extracted Content", content, height=200)

                # ✅ Create Word doc
                doc = Document()
                doc.add_heading(f"Recommendations - {file.name}", level=1)
                doc.add_paragraph(content)

                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                doc.save(temp.name)

                zipf.write(temp.name, file.name.replace(".pdf", "_recommendations.docx"))

        st.success("✅ Processing Complete!")

        st.download_button(
            label="⬇ Download ALL Word files (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="all_recommendations.zip",
            mime="application/zip"
        )
``