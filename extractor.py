import re
from pypdf import PdfReader

# ✅ Extract lines from PDF
def extract_lines(file):
    reader = PdfReader(file)
    lines = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            for line in text.split("\n"):
                clean = line.strip()
                if clean:
                    lines.append(clean)

    return lines


# ✅ Detect ONLY main sections (NO TOC, NO appendix, NO sub-sections)
def detect_sections(lines):
    sections = []

    for i, line in enumerate(lines):
        clean_line = line.strip()

        # ✅ Match main sections like "1. SYNOPSIS"
        if re.match(r"^\d+\.\s+[A-Za-z]", clean_line):

            lower_line = clean_line.lower()

            # ❌ Skip TOC lines (end with page numbers)
            if re.search(r"\d+$", clean_line):
                continue

