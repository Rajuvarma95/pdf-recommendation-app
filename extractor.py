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


# ✅ SIMPLE MATCH FUNCTION (NOT strict)
def is_match(title, line):
    num_match = re.match(r'^(\d+)', title)
    if not num_match:
        return False

    num = num_match.group(1)

    return re.match(rf'^{num}[\.\s]', line)


# ✅ FINAL EXTRACTION FUNCTION (STABLE)
def extract_section(lines, title):

    content = []
    found = False

    for i, line in enumerate(lines):
        clean = line.strip()
        lower = clean.lower()

        # ✅ find section start
        if not found:
            if is_match(title, clean):

                # ❌ skip TOC dotted entries
                if "..." in clean:
                    continue

                found = True
                content.append(clean)
                continue

        # ✅ extract until next section
        if found:

            if re.match(r'^\d+\.\s+[A-Za-z]', clean):
                break

            # ✅ keep subsections
            if re.match(r'^\d+\.\d+', clean):
                content.append(clean)
                continue

            # ✅ keep bullet points
            if re.match(r'^\d+\.', clean):
                content.append(clean)
                continue

            # ❌ remove noise
            if "...." in clean:
                continue

            if any(w in lower for w in [
                "asset", "railway", "owner", "territory",
                "status", "report", "policy"
            ]):
                continue

            if any(w in lower for w in [
                "page", "version", "contract", "february"
            ]):
                continue

            # ❌ remove pure numeric junk
            if re.match(r'^\d+(\.\d+)?$', clean):
                continue

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