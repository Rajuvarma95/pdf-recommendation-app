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


# ✅ Detect sections from TOC
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
            if re.match(r'^\d+\.\s+[A-Za-z]', line):

                # skip sub-sections
                if re.match(r'^\d+\.\d+', line):
                    continue

                clean_line = re.sub(r'\.+\s*\d+$', '', line.strip())

                sections.append(clean_line)

    return sections


# ✅ Check if line is actual section header
def is_heading_match(title, line):
    title_num = re.match(r'^(\d+)', title)

    if not title_num:
        return False

    num = title_num.group(1)

    # match "8. RECOMMENDATIONS" OR "8 RECOMMENDATIONS"
    if re.match(rf'^{num}[\.\s]', line):
        if title.split(".", 1)[-1].strip().lower() in line.lower():
            return True

    return False


# ✅ Extract correct section content
def extract_section(lines, title):
    content = []
    found = False

    for i, line in enumerate(lines):
        clean = line.strip()
        lower = clean.lower()

        # ✅ find actual section (NOT TOC)
        if not found:
            if is_heading_match(title, clean):

                # skip TOC dotted line
                if "..." in clean:
                    continue

                # check next lines (if still TOC)
                next_lines = " ".join(lines[i+1:i+5])
                if "..." in next_lines:
                    continue

                found = True
                content.append(clean)
            continue

        # ✅ stop at next main section
        if re.match(r'^\d+\.\s+[A-Za-z]', clean):
            break

        # ✅ keep sub-sections
        if re.match(r'^\d+\.\d+', clean):
            content.append(clean)
            continue

        # ✅ keep bullet points (1., 2., etc.)
        if re.match(r'^\d+\.\s+', clean):
            content.append(clean)
            continue

        # ❌ remove TOC garbage
        if "...." in clean:
            continue

        # ❌ remove table-like noise
        if any(word in lower for word in [
            "asset details", "policy", "owner",
            "territory", "railway", "status", "reports"
        ]):
            continue

        # ❌ remove footer
        if any(word in lower for word in [
            "assessment report", "final", "february", "page"
        ]):
            continue

        content.append(clean)

    return format_output(content)


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