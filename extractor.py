import re
from pypdf import PdfReader


# ✅ Extract all lines from PDF
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


# ✅ Detect sections ONLY from TOC
def detect_sections(lines):
    sections = []
    in_toc = False

    for i, line in enumerate(lines):
        clean = line.strip()
        lower = clean.lower()

        # ✅ Start TOC
        if "table of contents" in lower:
            in_toc = True
            continue

        # ✅ Stop at appendix
        if in_toc and "appendices" in lower:
            break

        if in_toc:
            # ✅ Match main sections like "1. TITLE"
            if re.match(r'^\d+\.\s+[A-Za-z]', clean):

                # ❌ Skip sub-sections like 1.1
                if re.match(r'^\d+\.\d+', clean):
                    continue

                # ✅ Remove dotted page numbers
                clean = re.sub(r'\.+\s*\d+$', '', clean)

                sections.append((clean, i))

    return sections


# ✅ Extract section content

def extract_section(lines, title):
    content = []
    found = False

    for i, line in enumerate(lines):
        clean = line.strip()

        # ✅ Find actual section in document (not TOC)
        if not found:
            if title.lower() in clean.lower():
                # avoid matching TOC line containing dots
                if "..." not in clean:
                    found = True
                    start_index = i
                    content.append(clean)
            continue

        # ✅ Once found → collect content
        if found:
            lower = clean.lower()

            # ✅ Stop at next main section
            if re.match(r'^\d+\.\s+', clean):
                break

            # ✅ Stop appendix
            if "appendix" in lower:
                break

            # ✅ Stop figure/table noise
            if "figure" in lower:
                break

            content.append(clean)

    return format_output(content)


# ✅ Format text
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