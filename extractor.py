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


# ✅ Detect section headings
def detect_sections(lines):
    sections = []

    for i, line in enumerate(lines):
        if re.match(r"^\d+\.\s+", line):
            sections.append((line, i))

    return sections



def extract_section(lines, start_index):
    content = []

    for i in range(start_index, len(lines)):
        line = lines[i]
        line_lower = line.lower()

        if i > start_index:

            # ✅ Stop at next numbered section
            if re.match(r"^\d+\.\s+", line):
                break

            # ✅ Stop at Appendix section
            if line_lower.startswith("appendix"):
                break

            # ✅ Stop at A., B., C. headings (appendix style)
            if re.match(r"^[A-Z]\.", line):
                break

            # ✅ Stop at figures / drawings
            if "figure" in line_lower:
                break

            # ✅ Stop at typical footer/report header patterns
            if "inspection report" in line_lower:
                break

            # ✅ Stop if line is too short or looks like label
            if len(line.split()) < 3 and line.isupper():
                break

        content.append(line)

    return format_output(content)



# ✅ Format output nicely
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