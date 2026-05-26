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


# ✅ Detect ONLY MAIN SECTIONS (no TOC, no sub-sections, no appendix)
def detect_sections(lines):
    sections = []

    for i, line in enumerate(lines):
        clean_line = line.strip()

        # ✅ Match main sections like "1. SYNOPSIS"
        if re.match(r"^\d+\.\s+[A-Za-z]", clean_line):

            lower_line = clean_line.lower()

            # ❌ Skip TOC entries (ending with page numbers like ..... 5)
            if re.search(r"\d+$", clean_line):
                continue

            # ❌ Skip sub-sections (1.1, 2.3, etc.)
            if re.match(r"^\d+\.\d+", clean_line):
                continue

            # ❌ Skip appendix (APPENDICES)
            if "appendix" in lower_line:
                continue

            # ❌ Skip A., B., C. type items
            if re.match(r"^[A-Z]\.", clean_line):
                continue

            sections.append((clean_line, i))

    return sections


# ✅ Extract section content CLEANLY
def extract_section(lines, start_index):
    content = []

    for i in range(start_index, len(lines)):
        line = lines[i]
        line_lower = line.lower()

        if i > start_index:

            # ✅ Stop at next main section
            if re.match(r"^\d+\.\s+", line):
                break

            # ✅ Stop at appendix sections
            if line_lower.startswith("appendix"):
                break

            # ✅ Stop at A., B., C. appendix headings
            if re.match(r"^[A-Z]\.", line):
                break

            # ✅ Stop at figure/caption content
            if "figure" in line_lower:
                break

            # ✅ Stop at report footer/header noise
            if "inspection report" in line_lower:
                break

            # ✅ Stop abnormal short uppercase lines
            if len(line.split()) < 3 and line.isupper():
                break

        content.append(line)

    return format_output(content)


# ✅ Format content into readable paragraph structure
def format_output(lines):
    output = ""
    paragraph = ""

    for line in lines:

        # ✅ Treat short lines as headings
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
``