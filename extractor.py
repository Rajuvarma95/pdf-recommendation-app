import re
from pypdf import PdfReader


def extract_lines(file):
    reader = PdfReader(file)
    lines = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    lines.append(line)

    return lines


def detect_sections(lines):
    sections = []

    for i, line in enumerate(lines):
        clean_line = line.strip()

        if re.match(r'^\d+\.\s+[A-Za-z]', clean_line):

            lower_line = clean_line.lower()

            # skip TOC lines ending with numbers
            if re.search(r'\d+$', clean_line):
                continue

            # skip sub-sections like 1.1
            if re.match(r'^\d+\.\d+', clean_line):
                continue

            # skip appendix
            if "appendix" in lower_line:
                continue

            # skip A., B., C.
            if re.match(r'^[A-Z]\.', clean_line):
                continue

            sections.append((clean_line, i))

    return sections


def extract_section(lines, start_index):
    content = []

    for i in range(start_index, len(lines)):
        line = lines[i]
        line_lower = line.lower()

        if i > start_index:

            if re.match(r'^\d+\.\s+', line):
                break

            if line_lower.startswith("appendix"):
                break

            if re.match(r'^[A-Z]\.', line):
                break

            if "figure" in line_lower:
                break

            if "inspection report" in line_lower:
                break

            if len(line.split()) < 3 and line.isupper():
                break

        content.append(line)

    return format_output(content)


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