import re
from pypdf import PdfReader


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def is_main_section_heading(line: str) -> bool:
    """
    Matches main headings like:
    1. INTRODUCTION
    8. RECOMMENDATIONS
    but not:
    1.1 Scope of Work
    8.2 Maintenance Team
    """
    line = line.strip()
    if re.match(r"^\d+\.\d+", line):
        return False
    return re.match(r"^\d+\.\s+[A-Za-z]", line) is not None


def is_subsection_heading(line: str) -> bool:
    """
    Matches subsections like:
    8.1 Assessment Team
    8.2 Maintenance Team
    """
    return re.match(r"^\d+\.\d+\s+[A-Za-z]", line.strip()) is not None


def is_numbered_bullet(line: str) -> bool:
    """
    Matches numbered bullets like:
    1. Replace...
    2. Repair...
    """
    line = line.strip()
    return re.match(r"^\d+\.\s+\S+", line) is not None and not is_main_section_heading(line)


def looks_like_footer_or_noise(line: str) -> bool:
    low = line.lower().strip()

    if not low:
        return True

    # dotted TOC style line
    if re.search(r"\.{4,}", line):
        return True

    # page/footer-like patterns
    footer_keywords = [
        "page ",
        "assessment report",
        "re-review assessment report",
        "version ",
        "contract mileage",
        "struc. ref",
        "struc ref",
        "wkl",
        "february",
        "final",
    ]
    if any(k in low for k in footer_keywords):
        return True

    # isolated numeric junk like 9.73 / 30 / 0214
    if re.fullmatch(r"\d+(\.\d+)?", low):
        return True

    # short metadata fragments
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

    # many separated short tokens / numeric columns
    parts = line.split()
    if len(parts) >= 5:
        short_count = sum(1 for p in parts if len(p) <= 3)
        digit_count = sum(1 for p in parts if any(ch.isdigit() for ch in p))
        if short_count >= 4 and digit_count >= 2:
            return True

    return False


# ---------------------------------------------------
# PDF structure extraction
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


# ---------------------------------------------------
# TOC detection
# ---------------------------------------------------

def detect_sections(doc):
    """
    Detect main sections ONLY from TOC.
    Returns list of dicts:
    [
      {"num": 1, "title": "1. INTRODUCTION", "toc_page": 1, "toc_target_page": 4},
      ...
    ]
    """
    sections = []
    pages = doc["pages"]

    in_toc = False
    toc_started = False
    toc_page_index = None

    # common TOC line formats:
    # 8. RECOMMENDATIONS................20
    # 8. RECOMMENDATIONS .......... 20
    toc_regex = re.compile(r"^(\d+)\.\s+(.+?)\s*\.{2,}\s*(\d+)\s*$")

    for page_index, page_lines in enumerate(pages):
        for line in page_lines:
            low = line.lower().strip()

            if "table of contents" in low or low == "contents":
                in_toc = True
                toc_started = True
                toc_page_index = page_index
                continue

            if not in_toc:
                continue

            # Appendix/end of TOC
            if "appendices" in low or low.startswith("appendix"):
                in_toc = False
                break

            m = toc_regex.match(line.strip())
            if not m:
                continue

            sec_num = m.group(1)
            sec_title = m.group(2).strip()
            sec_page = int(m.group(3))

            # skip subsections like 8.1
            if re.match(r"^\d+\.\d+", f"{sec_num}. {sec_title}"):
                continue

            display = f"{sec_num}. {sec_title}"
            sections.append({
                "num": int(sec_num),
                "title": display,
                "toc_page": page_index,
                "toc_target_page": sec_page,
            })

        if toc_started and not in_toc:
            break

    # remove duplicates by title
    unique = []
    seen = set()
    for sec in sections:
        if sec["title"] not in seen:
            seen.add(sec["title"])
            unique.append(sec)

    return unique


# ---------------------------------------------------
# Actual section extraction
# ---------------------------------------------------

def find_section_start(doc, section):
    """
    Find the real section heading in the body, not the TOC.
    Strategy:
    1. Search only AFTER TOC pages.
    2. Match exact main heading number.
    3. Require heading text overlap.
    4. Skip dotted TOC-like lines.
    """
    flat_lines = doc["flat_lines"]
    title = section["title"]
    section_num = section["num"]

    # heading text after number
    heading_text = title.split(".", 1)[1].strip() if "." in title else title
    heading_norm = normalize_text(heading_text)

    best_idx = None

    # Find last TOC page
    start_search_page = section.get("toc_page", 0) + 1

    for idx, (page_index, line) in enumerate(flat_lines):
        if page_index < start_search_page:
            continue

        clean = line.strip()

        # skip dotted TOC lines
        if re.search(r"\.{4,}", clean):
            continue

        # must be a main heading with the same main section number
        if not re.match(rf"^{section_num}\.\s+[A-Za-z]", clean):
            continue

        line_after_num = clean.split(".", 1)[1].strip()
        line_norm = normalize_text(line_after_num)

        # flexible overlap
        if heading_norm and (heading_norm in line_norm or line_norm in heading_norm):
            best_idx = idx
            break

    return best_idx


def extract_section(doc, section):
    """
    Extract from real section heading until next main section heading.
    Keeps subsection headings and numbered bullets.
    Removes noise/footer/table fragments.
    """
    flat_lines = doc["flat_lines"]
    start_idx = find_section_start(doc, section)

    if start_idx is None:
        return ""

    collected = []
    section_num = section["num"]

    for idx in range(start_idx, len(flat_lines)):
        _, line = flat_lines[idx]
        clean = line.strip()

        if idx > start_idx:
            # stop at next MAIN section number
            if is_main_section_heading(clean):
                next_num_match = re.match(r"^(\d+)\.", clean)
                if next_num_match:
                    next_num = int(next_num_match.group(1))
                    if next_num != section_num:
                        break

        # drop noise
        if looks_like_footer_or_noise(clean):
            continue
        if looks_like_table_noise(clean):
            continue

        collected.append(clean)

    return format_output(collected)


# ---------------------------------------------------
# Output formatting
# ---------------------------------------------------

def format_output(lines):
    """
    Keeps:
    - main heading
    - subsection headings
    - numbered bullets
    - paragraph flow
    """
    out = []
    paragraph = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            out.append(" ".join(paragraph).strip())
            paragraph = []

    for line in lines:
        clean = line.strip()
        if not clean:
            continue

        # main/sub headings on separate lines
        if is_main_section_heading(clean) or is_subsection_heading(clean):
            flush_paragraph()
            out.append(clean)
            continue

        # numbered bullets on separate lines
        if is_numbered_bullet(clean):
            flush_paragraph()
            out.append(clean)
            continue

        # normal paragraph text
        paragraph.append(clean)

    flush_paragraph()

    return "\n\n".join(out).strip()