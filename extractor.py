import re
from pypdf import PdfReader


# ✅ Extract text lines from PDF
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
        lower = line.strip().lower()

        if "table of contents" in lower:
            in_toc = True
            continue

        if in_toc and "appendices" in lower:
            break

        if in_toc:
            if re.match(r'^\d+\.\s+[A-Za-z]', line):

                # skip sub-sections
                if re.match(r'^\d+\.\d+', line):
                    continue

                clean = re.sub(r'\.+\s*\d+$', '', line.strip())
                sections.append(clean)

    return sections


# ✅ Simple heading match
def is_heading(title, line):
    num_match = re.match(r'^(\d+)', title)
    if not num_match:
        return False

    num = num_match.group(1)

    if re.match(rf'^{num}[\.\s]', line):
        if title.lower().split(".", 1)[-1].strip() in line.lower():
            return True

    return False


# ✅ FINAL SECTION EXTRACTOR (STABLE VERSION)
def extract_section(lines, title):

    content = []
    found = False

    for i, line in enumerate(lines):
        clean = line.strip()
        lower = clean.lower()

        # ✅ Find section (skip TOC)
        if not found:
            if is_heading(title, clean):

                # skip TOC version
                if "..." in clean:
                    continue

                # check next lines (avoid TOC)
                next_block = " ".join(lines[i+1:i+5])
                if "..." in next_block:
                    continue

                found = True
                content.append(clean)
                continue

        # ✅ Once found → extract content
        if found:

            # ✅ stop at next section
            if re.match(r'^\d+\.\s+[A-Za-z]', clean):
                break

            # ✅ keep sub-sections
            if re.match(r'^\d+\.\d+', clean):
                content.append(clean)
                continue

            # ✅ keep bullet points
            if re.match(r'^\d+\.\s+', clean):
                content.append(clean)
                continue

            # ❌ remove dotted TOC garbage
            if "...." in clean:
                continue

            # ❌ remove table / structured content
            if any(w in lower for w in [
                "asset", "railway", "owner", "territory",
                "status", "reports", "policy"
            ]):
                continue

            # ❌ remove footer/meta
            if any(w in lower for w in [
                "version", "contract", "page", "february",
                "report", "final"
            ]):
                continue

            # ❌ remove pure numeric junk
            if re.match(r'^\d+(\.\d+)?$', clean):
                continue

            content.append(clean)

    return format_output(content)


# ✅ Clean formatting
def format_output(lines):
    result = ""
    paragraph = ""

    for line in lines:
        if len(line.split()) <= 3:
            if paragraph:
                result += paragraph.strip() + "\n\n"
                paragraph = ""
            result += line + "\n"
        else:
            paragraph += line + " "

    if paragraph:
        result += paragraph.strip()

    return result.strip()
