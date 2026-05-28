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

        if in_toc:
            if re.match(r'^\d+\.\s+[A-Za-z]', clean):

                if re.match(r'^\d+\.\d+', clean):
                    continue

                clean = re.sub(r'\.+\s*\d+$', '', clean)

                sections.append(clean)

    return sections


# ✅ STRICT HEADING MATCH (FIX)
def is_heading_match(title, line):
    title_num = re.match(r'^(\d+)\.', title)
    title_text = title.split('.', 1)[-1].strip().lower()

    if title_num:
        num = title_num.group(1)

        # ✅ Match like "8. RECOMMENDATIONS"
        if re.match(rf'^{num}\.\s+', line):
            if title_text in line.lower():
                return True

        # ✅ Match like "8 RECOMMENDATIONS"
        if re.match(rf'^{num}\s+', line):
            if title_text in line.lower():
                return True

    return False


def extract_section(lines, title):
    content = []
    found = False

    for i in range(len(lines)):
        line = lines[i]
        clean = line.strip()

        # ✅ CORRECT START DETECTION
        if not found:
            if is_heading_match(title, clean):
                found = True
                content.append(clean)
            continue

        lower = clean.lower()

        # ✅ Stop at next main section ONLY
        if re.match(r'^\d+\.\s+[A-Za-z]', clean):
            break

        # ✅ KEEP sub-sections like 8.1
        if re.match(r'^\d+\.\d+', clean):
            content.append(clean)
            continue

        # ✅ KEEP bullet points (1., 2., etc.)
        if re.match(r'^\d+\.\s+', clean):
            content.append(clean)
            continue

        # ❌ REMOVE table noise
        if any(word in lower for word in [
            "asset details", "policy on a page", "owner",
            "territory", "railway", "data availability",
            "status", "reports"
        ]):
            continue

        # ❌ REMOVE footer
        if any(word in lower for word in [
            "assessment report", "final", "february",
            "page", "wkl"
        ]):
            continue

        # ✅ Keep remaining valid text
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