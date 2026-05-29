import re
from pypdf import PdfReader


# ---------------------------------------------------
# Utility helpers
# ---------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Lowercase and remove non-alphanumeric chars for flexible comparison.
    """
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def is_main_section_heading(line: str) -> bool:
    """
    Matches main headings like:
      1. INTRODUCTION
      6. RECOMMENDATIONS
    but NOT:
      1.1 Scope of Work
      8.2 Maintenance Team
    """
    line = line.strip()
    if re.match(r"^\d+\.\d+", line):
        return False
    return re.match(r"^\d+\.\s+[A-Za-z]", line) is not None


def is_subsection_heading(line: str) -> bool:
    """
    Matches subsection headings like:
      8.1 Assessment Team
      8.2 Maintenance Team
    """
    return re.match(r"^\d+\.\d+\s+[A-Za-z]", line.strip()) is not None


def is_numbered_bullet(line: str) -> bool:
    """
    Matches numbered bullet lines like:
      1. Repair...
      2. Replace...
    """
    line = line.strip()
    return re.match(r"^\d+\.\s+\S+", line) is not None and not is_main_section_heading(line)


def looks_like_footer_or_noise(line: str) -> bool:
    low = line.lower().strip()

    if not low:
        return True

    # Dotted leader lines (TOC style)
    if re.search(r"\.{4,}", line):
        return True

    footer_keywords = [
        "assessment report",
        "re-review assessment report",
        "page ",
        "page:",
        "version ",
        "contract mileage",
        "struc. ref",
        "struc ref",
        "february",
        "final",
        "wkl",
    ]
    if any(k in low for k in footer_keywords):
        return True

    # Pure numeric noise like 9.73 / 30 / 0214
    if re.fullmatch(r"\d+(\.\d+)?", low):
        return True

    # Tiny metadata fragments
    if low in {"ch", "yds", "m"}:
        return True

    return False


def looks_like_table_noise(line: str) -> bool:
    low = line.lower().strip()

    table_keywords = [
        "asset details",
        "policy on a page",
        "owner",
        "territory",
        "railway",
        "status",
        "reports",
        "data availability",
    ]
    if any(k in low for k in table_keywords):
        return True

    # Simple heuristic for table-like lines
    parts = line.split()
    if len(parts) >= 6:
        short_count = sum(1 for p in parts if len(p) <= 3)
        digit_count = sum(1 for p in parts if any(ch.isdigit() for ch in p))
        if short_count >= 4 and digit_count >= 2:
            return True

    return False


# ---------------------------------------------------
# PDF reading
# ---------------------------------------------------

def extract_document(file):
    """
    Reads the PDF and returns:
    {
        "pages": [ [line1, line2, ...], ... ],
        "flat_lines": [ (page_index, line), ... ]
    }
    """
    reader = PdfReader(file)
    pages = []
    flat_lines = []

    for page_index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        page_lines = []

        for raw in text.split("\n"):
            clean = raw.strip()
            if clean:
                page_lines.append(clean)
                flat_lines.append((page_index, clean))

        pages.append(page_lines)

    return {
        "pages": pages,
        "flat_lines": flat_lines,
    }


def extract_lines(file):
    """
    Backward-compatible helper.
    Returns just the flat list of text lines.
    """
    doc = extract_document(file)
    return [line for _, line in doc["flat_lines"]]


# ---------------------------------------------------
# TOC detection
# ---------------------------------------------------

def detect_sections(doc):
    """
    Detect ONLY main sections from the Table of Contents.

    Returns a list like:
    [
        {"num": 1, "title": "1. SYNOPSIS", "toc_page": 0, "target_page": 1},
        {"num": 2, "title": "2. STRUCTURE INFORMATION", "toc_page": 0, "target_page": 5},
        ...
    ]
    """
    pages = doc["pages"]
    sections = []

    in_toc = False
    toc_started = False

    # Matches lines like:
    # 6. RECOMMENDATIONS................20
    # 4. DETAILED EXAMINATION SUMMARY .... 12
    toc_line_re = re.compile(r"^(\d+)\.\s+(.+?)\s*\.{2,}\s*(\d+)\s*$")

    for page_index, page_lines in enumerate(pages):
        for line in page_lines:
            clean = line.strip()
            low = clean.lower()

            if "table of contents" in low or low == "contents":
                in_toc = True
                toc_started = True
                continue

            if not in_toc:
                continue

            # stop TOC at appendices
            if "appendices" in low or low.startswith("appendix"):
                in_toc = False
                break

            m = toc_line_re.match(clean)
            if not m:
                continue

            sec_num = m.group(1)
            sec_title = m.group(2).strip()
            target_page = int(m.group(3))

            display_title = f"{sec_num}. {sec_title}"

            # just in case, skip subsection-like titles
            if re.match(r"^\d+\.\d+", display_title):
                continue

            sections.append({
                "num": int(sec_num),
                "title": display_title,
                "toc_page": page_index,
                "target_page": target_page,
            })

        if toc_started and not in_toc:
            break

    # Remove duplicates while preserving order
    unique = []
    seen = set()
    for sec in sections:
        if sec["title"] not in seen:
            seen.add(sec["title"])
            unique.append(sec)

    return unique


# ---------------------------------------------------
# Actual body heading detection
# ---------------------------------------------------

def heading_matches_section(line: str, section: dict) -> bool:
    """
    Match a real body heading for the given section.
    Handles:
      8. RECOMMENDATIONS
      8 RECOMMENDATIONS
    """
    clean = line.strip()
    num = section["num"]

    # Must start with the correct main section number
    if not re.match(rf"^{num}[\.\s]", clean):
        return False

    # Compare heading text after the number
    if "." in section["title"]:
        expected_text = section["title"].split(".", 1)[1].strip()
    else:
        expected_text = section["title"].strip()

    expected_norm = normalize_text(expected_text)

    # Remove the leading section number from the candidate line
    candidate = re.sub(rf"^{num}[\.\s]+", "", clean).strip()
    candidate_norm = normalize_text(candidate)

    if not candidate_norm:
        return False

    # Flexible overlap
    return expected_norm in candidate_norm or candidate_norm in expected_norm


def find_section_start(doc, section