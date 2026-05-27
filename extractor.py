import re
from pypdf import PdfReader


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


def detect_sections(lines):
    sections = []
    in_toc = False

    for line in lines:
        clean = line.strip()
        lower = clean.lower()

        if "table of contents" in lower:
            in_toc = True
            continue

        if in_toc and "appendices" in lower:
            break

        if in_toc and re.match(r'^\d+\.\s+[A-Za-z]', clean):

            if re.match(r'^\d+\.\d+', clean):
                continue

            clean = re.sub(r'\.+\s*\d+$', '', clean)

            sections.append(clean)

    return sections


def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def extract_section(lines, title):
    content = []
    found = False

    # ✅ normalize title
    norm_title = normalize(title)

    for line in lines:
        clean = line.strip()
        norm_line = normalize(clean)

        # ✅ find actual section
        if not found:
            if norm_title in norm_line:
                # skip TOC dotted lines
                if "..." not in clean:
                    found = True
                    content.append(clean)
            continue

        lower = clean.lower()

        # ✅ stop at next section
        if re.match(r'^\d+\.\s+', clean):
            break

        # ✅ stop noise
        if "appendix" in lower:
            break
        if "figure" in lower:
            break

        content.append(clean)

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