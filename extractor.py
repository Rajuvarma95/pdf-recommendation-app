import re
from pypdf import PdfReader


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def clean_for_word(text: str) -> str:
    """
    Remove invalid XML/control chars that can break python-docx.
    Keeps tabs/newlines/carriage returns.
    """
    if not text:
        return ""
    return "".join(
        ch for ch in text
        if ch == "\t" or ch == "\n" or ch == "\r" or ord(ch) >= 32
    )


def is_main_section_heading(line: str) -> bool:
    """
    Main section examples:
      1. INTRODUCTION
      6. RECOMMENDATIONS
      7. APPENDICES
    Not:
      6.1 Assessment Team
    """
    line = line.strip()
    if re.match(r"^\d+\.\d+", line):
        return False
    return re.match(r"^\d+\.\s+[A-Za-z]", line) is not None


def is_subsection_heading(line: str) -> bool:
    """
    Examples:
      6.1 Assessment Team
      6.2 Maintenance Team
    """
    return re.match(r"^\d+\.\d+\s+[A-Za-z]", line.strip()) is not None


def is_numbered_bullet(line: str) -> bool:
    """
    Examples:
      1. Replacement of existing repairs
      2. Fully clean and repaint...
    """
    line = line.strip()
    return re.match(r"^\d+\.\s+\S+", line) is not None and not is_main_section_heading(line)


def looks_like_footer_or_noise(line: str) -> bool:
    low = line.lower().strip()

    if not low:
        return True

    # dotted leader TOC lines
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

    # pure numeric junk
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

    # table/grid-ish line heuristic
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
                clean = clean_for_word(clean)
                page_lines.append(clean)
                flat_lines.append((page_index, clean))

        pages.append(page_lines)

    return {
        "pages": pages,
        "flat_lines": flat_lines,
    }


# ---------------------------------------------------
# TOC detection
# ---------------------------------------------------

def detect_sections(doc):
    """
    Detect ONLY main sections from the TOC.
    Returns a list like:
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

            # stop TOC once appendices section starts
            if "appendices" in low or low.startswith("appendix"):
                in_toc = False
                break

            match = toc_line_re.match(clean)
            if not match:
                continue

            sec_num = int(match.group(1))
            sec_title = match.group(2).strip()
            target_page = int(match.group(3))

            display_title = f"{sec_num}. {sec_title}"

            # skip subsection-like TOC entries
            if re.match(r"^\d+\.\d+", display_title):
                continue

            sections.append({
                "num": sec_num,
                "title": clean_for_word(display_title),
                "toc_page": page_index,
                "target_page": target_page,
            })

        if toc_started and not in_toc:
            break

    # remove duplicates while preserving order
    unique = []
    seen = set()
    for sec in sections:
        if sec["title"] not in seen:
            seen.add(sec["title"])
            unique.append(sec)

    return unique


# ---------------------------------------------------
# Actual heading matching
# ---------------------------------------------------

def heading_matches_section(line: str, section: dict) -> bool:
    """
    Match body headings like:
      6. RECOMMENDATIONS
      6 RECOMMENDATIONS
    """
    clean = line.strip()
    num = section["num"]

    # correct section number at start
    if not re.match(rf"^{num}[\.\s]", clean):
        return False

    # reject subsection-like lines
    if re.match(r"^\d+\.\d+", clean):
        return False

    # heading text comparison
    expected_text = section["title"].split(".", 1)[1].strip() if "." in section["title"] else section["title"]
    expected_norm = normalize_text(expected_text)

    candidate = re.sub(rf"^{num}[\.\s]+", "", clean).strip()
    candidate_norm = normalize_text(candidate)

    if not candidate_norm:
        return False

    return expected_norm in candidate_norm or candidate_norm in expected_norm


def locate_section_starts(doc, sections):
    """
    Locate the real body start line for each TOC section in order.
    """
    flat_lines = doc["flat_lines"]
    located = []

    toc_end_page = max((sec["toc_page"] for sec in sections), default=0)
    search_from_idx = 0

    for idx, (page_index, _) in enumerate(flat_lines):
        if page_index > toc_end_page:
            search_from_idx = idx
            break

    for sec in sections:
        found_idx = None

        for idx in range(search_from_idx, len(flat_lines)):
            _, line = flat_lines[idx]
            clean = line.strip()

            # skip dotted TOC lines
            if re.search(r"\.{4,}", clean):
                continue

            if heading_matches_section(clean, sec):
                found_idx = idx
                break

        if found_idx is not None:
            sec_copy = sec.copy()
            sec_copy["start_idx"] = found_idx
            located.append(sec_copy)
            search_from_idx = found_idx + 1

    return located


# ---------------------------------------------------
# Section extraction
# ---------------------------------------------------

def extract_section(doc, located_sections, section):
    """
    Extract from this section's body start to the next located main section start.
    Stops before APPENDICES / next main section.
    """
    if "start_idx" not in section:
        return ""

    flat_lines = doc["flat_lines"]

    current_pos = None
    for i, sec in enumerate(located_sections):
        if sec["title"] == section["title"] and sec.get("start_idx") == section.get("start_idx"):
            current_pos = i
            break

    if current_pos is None:
        return ""

    start_idx = section["start_idx"]

    if current_pos < len(located_sections) - 1:
        end_idx = located_sections[current_pos + 1]["start_idx"]
    else:
        end_idx = len(flat_lines)

    collected = []

    for idx in range(start_idx, end_idx):
        _, line = flat_lines[idx]
        clean = line.strip()
        low = clean.lower()

        if idx > start_idx:
            if re.match(r"^\d+\.\s+[A-Za-z]", clean):
                line_num_match = re.match(r"^(\d+)\.", clean)
                if line_num_match:
                    line_num = int(line_num_match.group(1))
                    if line_num != section["num"]:
                        break

            if "appendices" in low or low.startswith("appendix"):
                break

        if looks_like_footer_or_noise(clean):
            continue

        if looks_like_table_noise(clean):
            continue

        collected.append(clean_for_word(clean))

    return format_output(collected)


# ---------------------------------------------------
# Formatting
# ---------------------------------------------------

def format_output(lines):
    """
    Preserve:
    - main headings
    - subsection headings
    - numbered bullets
    - paragraph text
    """
    output = []
    paragraph = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = " ".join(paragraph).strip()
            if text:
                output.append(clean_for_word(text))
            paragraph = []

    for line in lines:
        clean = clean_for_word(line.strip())
        if not clean:
            continue

        if is_main_section_heading(clean) or is_subsection_heading(clean):
            flush_paragraph()
            output.append(clean)
            continue

        if is_numbered_bullet(clean):
            flush_paragraph()
            output.append(clean)
            continue

        paragraph.append(clean)

    flush_paragraph()

    return "\n\n".join(output).strip()