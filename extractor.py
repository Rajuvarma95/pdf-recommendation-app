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
                if re.match(r'^\d+\.\d+', line):
                    continue

                clean_line = re.sub(r'\.+\s*\d+$', '', line.strip())
                sections.append(clean_line)

    return sections


def is_heading_line(line, title):
    title_num = re.match(r'^(\d+)', title)
    if not title_num:
        return False

    num = title_num.group(1)

    # matches "8." OR "8 "
    if re.match(rf'^{num}[\.\s]', line):
        if title.lower().split('.', 1)[-1].strip() in line.lower():
            return True

    return False


def extract_section(lines, title):
    content = []
    start_index = None

    # ✅ get section number (like 8 from "8. RECOMMENDATIONS")
    match = re.match(r'^(\d+)', title)
    if not match:
        return ""

    section_num = match.group(1)

    # ✅ find last occurrence (skip TOC automatically)
    for i, line in enumerate(lines):
        clean = line.strip()

        if re.match(rf'^{section_num}[\.\s]', clean):
            if "..." not in clean:  # skip TOC
                start_index = i

    if start_index is None:
        return ""

    # ✅ extract content forward
    for i in range(start_index, len(lines)):
        line = lines[i].strip()
        lower = line.lower()

        if i != start_index:
            # ✅ stop at next section
            if re.match(r'^\d+\.\s+[A-Za-z]', line):
                break

        # ❌ remove dotted TOC lines
        if "..." in line:
            continue

        # ❌ remove table content
        if any(word in lower for word in [
            "asset", "policy", "owner", "territory",
            "railway", "status", "reports"
        ]):
            continue

        # ❌ remove footer
        if any(word in lower for word in [
            "assessment report", "page", "february", "final"
        ]):
            continue

        content.append(line)

    return format_output(content)


def format_output(lines):
    text = ""
    para = ""

    for line in lines:
        if len(line.split()) <= 3:
            if para:
                text += para.strip() + "\n\n"
                para = ""
            text += line + "\n"
        else:
            para += line + " "

    if para:
        text += para.strip()

    return text.strip()