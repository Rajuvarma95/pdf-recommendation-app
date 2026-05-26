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


# ✅ Extract selected section
def extract_section(lines, start_index):
    content = []

    for i in range(start_index, len(lines)):
        line = lines[i]

        if i > start_index:
            if re.match(r"^\d+\.\s+", line):
                break
            if "appendix" in line.lower():
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