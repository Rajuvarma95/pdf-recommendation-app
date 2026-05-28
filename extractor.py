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
    found_candidates = []

    # ✅ FIRST: find all possible section matches
    for i, line in enumerate(lines):
        clean = line.strip()

        if is_heading_line(clean, title):
            if "..." not in clean:  # skip TOC
                found_candidates.append(i)

    # ✅ If no match → return empty safely
    if not found_candidates:
        return ""

    # ✅ Take FIRST VALID real content (not TOC)
    start_index = found_candidates[0]

    # ✅ Extract content
    for i in range(start_index, len(lines)):
        line = lines[i].strip()
        lower = line.lower()

        if i != start_index:
            # stop at next major section
            if re.match(r'^\d+\.\s+[A-Za-z]', line):
                break

        # ✅ CLEAN unwanted stuff
        if "...." in line:
            continue

        if any(word in lower for word in [
            "asset details", "policy", "owner",
            "territory", "railway", "status", "reports"
        ]):
            continue

        if any(word in lower for word in [
            "assessment report", "final", "february", "page"
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