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


# ✅ Detect TOC sections
def detect_sections(lines):
    sections = []
    in_toc = False

    for line in lines:
        clean = line.strip().lower()

        if "table of contents" in clean:
            in_toc = True
            continue

        if in_toc and "appendices" in clean:
            break

        if in_toc:
            if re.match(r'^\d+\.\s+[A-Za-z]', line.strip()):

                # skip sub-sections
                if re.match(r'^\d+\.\d+', line.strip()):
                    continue

                # remove dotted page numbers
                clean_line = re.sub(r'\.+\s*\d+$', '', line.strip())

                sections.append(clean_line)

    return sections


# ✅ Normalize text for matching
def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


# ✅ Extract section content (IMPROVED LOGIC)
def extract_section(lines, title):
    content = []
    found = False

    norm_title = normalize(title)

    for i, line in enumerate(lines):
        clean = line.strip()
        norm_line = normalize(clean)

        # ✅ find section start (skip TOC)
        if not found:
            if norm_title in norm_line and "..." not in clean:
                found = True
                content.append(clean)
            continue

        lower = clean.lower()

        # ✅ stop at next main section (but allow sub-sections)
        if re.match(r'^\d+\.\s+[A-Za-z]', clean):
            break

        # ✅ KEEP sub-sections like 8.1, 8.2 ✅
        if re.match(r'^\d+\.\d+', clean):
            content.append(clean)
            continue

        # ✅ KEEP bullet points ✅
        if re.match(r'^\d+\.', clean):
            content.append(clean)
            continue

        # ❌ REMOVE TABLE / GRID DATA
        if any(word in lower for word in [
            "asset details", "policy on a page", "owner", "territory",
            "railway", "data availability", "status", "reports"
        ]):
            continue

        # ❌ REMOVE FOOTER / HEADER
        if any(word in lower for word in [
            "assessment report", "final", "february", "page", "wkl"
        ]):
            continue

        # ❌ REMOVE PURE CAPITAL SHORT NOISE
        if len(clean.split()) < 3 and clean.isupper():
            continue

        # ✅ append valid text
        content.append(clean)

    return format_output(content)


# ✅ Clean formatting
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