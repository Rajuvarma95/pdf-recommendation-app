import re
from pypdf import PdfReader


# ✅ Extract text lines
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


# ✅ Detect only TOC sections (main sections only)
def detect_sections(lines):
    sections = []
    in_toc = False

    for line in lines:
        clean = line.strip()
        lower = clean.lower()

        # ✅ start TOC
        if "table of contents" in lower:
            in_toc = True
            continue

        # ✅ stop TOC
        if in_toc and "appendices" in lower:
            break

        if in_toc:
            if re.match(r'^\d+\.\s+[A-Za-z]', clean):

                # ❌ skip sub-sections
                if re.match(r'^\d+\.\d+', clean):
                    continue

                # ✅ remove dotted page numbers
                clean = re.sub(r'\.+\s*\d+$', '', clean)

                sections.append(clean)

    return sections


# ✅ Extract REAL section content (NOT TOC)
def extract_section(lines, title):
    content = []
    found = False

    for line in lines:
        clean = line.strip()

        # ✅ find actual section location
        if not found:
            if title.lower() in clean.lower():
                if "..." not in clean:  # skip TOC
                    found = True
                    content.append(clean)
            continue

        # ✅ once found
        if found:
            lower = clean.lower()

            # ✅ stop at next main section
            if re.match(r'^\d+\.\s+', clean):
                break

            # ✅ stop appendix
            if "appendix" in lower:
                break

            # ✅ stop figures/tables
            if "figure" in lower:
                break

            content.append(clean)

    return format_output(content)


# ✅ Format output cleanly
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