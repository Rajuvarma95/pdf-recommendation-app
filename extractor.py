
import re
from pypdf import PdfReader


# ---------------------------------------------------
# Basic helpers
# ---------------------------------------------------

def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def is_main_section_heading(line: str) -> bool:
    """
    Matches:
      1. INTRODUCTION
      6. RECOMMENDATIONS
    But NOT:
      1.1 Scope of Work
      8.2 Maintenance Team
    """
    line = line.strip()
    if re.match(r"^\d+\.\d+", line):
        return False
    return re.match(r"^\d+\.\s+[A-Za-z]", line) is not None


def is_subsection_heading(line: str) -> bool:
    """
    Matches:
      8.1 Assessment Team
      8.2 Maintenance Team
    """
    return re.match(r"^\d+\.\d+\s+[A-Za-z]", line.strip()) is not None


def is_numbered_bullet(line: str) -> bool:
    """
    Matches numbered bullets like:
      1. Replace...
      2. Repair...
    but avoids treating major headings as bullets
    """
    line = line.strip()
    return re.match(r"^\d+\.\s+\S+", line) is not None and not is_main_section_heading(line)


def looks_like_footer_or_noise(line: str) -> bool:
    low = line.lower().strip()

    if not low:
        return True

    # Dotted TOC style junk
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

    # isolated numeric junk
    if re.fullmatch(r"\d+(\.\d+)?", low):
        return True

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

    parts = line.split()
    if len(parts) >= 6:
        short_count = sum(1 for p in parts if len(p) <= 3)
        digit_count = sum(1 for p in parts if any(ch.isdigit() for ch in p))
        if short_count >= 4 and digit_count >= 2:
            return True

    return False


# ---------------------------------------------------
# Document extraction
# ---------------------------------------------------

def extract_document(file):
    """
    Returns:
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


# backward-compatible helper if needed
def extract_lines(file):
    """
    Kept only for compatibility.
    Returns flat list of lines.
    """
    doc = extract_document(file)
    return [line for _, line in doc["flat_lines"]]


# ---------------------------------------------------
# TOC parsing
# ---------------------------------------------------

def detect_sections(doc):
    """
    Detect ONLY main sections from the TOC.

    Returns:
    [
      {"num": 1, "title": "1. SYNOPSIS", "toc_page": 0, "target_page": 1},
      ...
    ]
    """
    pages = doc["pages"]
    sections = []

    in_toc = False
    toc_started = False

    # Example:
    # 6. RECOMMENDATIONS................20
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
            toc_target_page = int(m.group(3))

            display_title = f"{sec_num}. {sec_title}"

            # skip subsection-like entries just in case
            if re.match(r"^\d+\.\d+", display_title):
                continue

            sections.append({
                "num": int(sec_num),
                "title": display_title,
                "toc_page": page_index,
                "target_page": toc_target_page
            })

        if toc_started and not in_toc:
            break

    # remove duplicates while preserving order
    unique_sections = []
    seen = set()
    for sec in sections:
        if sec["title"] not in seen:
            seen.add(sec["title"])
            unique_sections.append(sec)

    return unique_sections


# ---------------------------------------------------
# Actual section finding
# ---------------------------------------------------

def heading_matches_section(line: str, section: dict) -> bool:
    """
    Match actual body heading for a TOC section.
    Handles:
      8. RECOMMENDATIONS
      8 RECOMMENDATIONS
    """
    clean = line.strip()

    # must start with section number
    num = section["num"]