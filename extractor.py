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


def clean_toc_title(line: str) -> str:
    """
    Convert TOC lines like:
      5. Conclusions and Recommendations 8
      5. Conclusions and Recommendations........8
    into:
      5. Conclusions and Recommendations
    """
    clean = line.strip()
    clean = re.sub(r"\s*\.{2,}\s*\d+\s*$", "", clean)
    clean = re.sub(r"\s+\d+\s*$", "", clean)
    return clean.strip()


def is_main_section_heading(line: str) -> bool:
    """
    Matches:
      1. INTRODUCTION
      5. Conclusions and Recommendations
      6. RECOMMENDATIONS
    But not:
      6.1 Assessment Team
    """
    line = line.strip()

    if re.match(r"^\d+\.\d+", line):
        return False

    return re.match(r"^\d+\.\s+[A-Za-z]", line) is not None


def is_subsection_heading(line: str) -> bool:
    """
    Matches:
      6.1 Assessment Team
      6.2 Maintenance Team
    """
    return re.match(r"^\d+\.\d+\s+[A-Za-z]", line.strip()) is not None


def is_numbered_bullet(line: str) -> bool:
    """
    Matches:
      1. Replacement of existing repairs
      2. Fully clean and repaint...
    But avoids treating main headings as bullets.
    """
    line = line.strip()
    return re.match(r"^\d+\.\s+\S+", line) is not None and not is_main_section_heading(line)


def looks_like_date_footer(line: str) -> bool:
    """
    Catch lines like:
      June 2016
      Feb 2024
    """
    clean = line.strip().lower()
    return re.match(
        r"^(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)\s+\d{4}$",
        clean
    ) is not None


def looks_like_file_path_or_internal(line: str) -> bool:
    """
    Catch document footer/path lines like:
      \\server\folder\...
      C:\folder\...
      INTERNAL
    """
    clean = line.strip()
    low = clean.lower()

    if low == "internal":
        return True

    if clean.startswith("\\") or clean.startswith("/"):
        return True

    if re.search(r"[A-Za-z]:\\", clean):
        return True

    if "\\" in clean and len(clean) > 10:
        return True

    if "/" in clean and len(clean) > 20 and (
        "project" in low or "execution" in low or "structures" in low
    ):
        return True

    return False


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

    if looks_like_date_footer(line):
        return True

    if looks_like_file_path_or_internal(line):
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


def looks_like_appendix_or_caption_start(line: str) -> bool:
    """
    Detect appendix/caption blocks that should stop extraction.
    """
    clean = line.strip()
    low = clean.lower()

    if low.startswith("appendix") or low.startswith("appendices"):
        return True

    # A. Location Plan / B. Photographs
    if re.match(r"^[A-Z]\.\s+[A-Za-z]", clean):
        return True

    if low.startswith("figure "):
        return True
    if low.startswith("photograph "):
        return True
    if low.startswith("table "):
        return True

    caption_keywords = [
        "location plan",
        "principal inspection report",
        "general view",
        "north west wing wall",
        "south west wing wall",
        "formed from the water seepage",
        "spalled concrete",
    ]
    if any(k in low for k in caption_keywords):
        return True

    return False


def trim_line_before_noise(line: str) -> str:
    """
    If valid sentence text and caption/report/appended noise appear in the SAME line,
    trim from the first noise marker onward and keep the valid prefix.
    """
    if not line:
        return line

    markers = [
        " Atkins Newcastle Road Middle Bridge",
        " Principal Inspection Report",
        " Figure ",
        " Photograph ",
        " A. Location Plan",
        " B. Photographs",
        " C. Defect Drawings",
        " Appendix",
        " Appendices",
        " INTERNAL",
        "\\\\",
    ]

    cut_positions = []

    for marker in markers:
        pos = line.find(marker)
        if pos > 0:
            cut_positions.append(pos)

    if cut_positions:
        line = line[:min(cut_positions)].strip()

    return line


def is_plain_subheading(line: str) -> bool:
    """
    Detect plain subheadings like:
      Further Assessment
      Monitoring
      Maintenance
    """
    clean = line.strip()

    if not clean:
        return False

    if is_main_section_heading(clean) or is_subsection_heading(clean) or is_numbered_bullet(clean):
        return False

    if clean.endswith(".") or clean.endswith(":") or clean.endswith(";"):
        return False

    words = clean.split()
    if len(words) < 1 or len(words) > 4:
        return False

    if sum(ch.isdigit() for ch in clean) > 1:
        return False

    alpha_words = sum(
        1 for w in words
        if re.fullmatch(r"[A-Za-z][A-Za-z'/-]*", w)
    )
    if alpha_words < len(words):
        return False

    if looks_like_appendix_or_caption_start(clean):
        return False
    if looks_like_table_noise(clean):
        return False
    if looks_like_footer_or_noise(clean):
        return False

    return True


def looks_like_body_heading_candidate(line: str) -> bool:
    """
    Fallback heading detection when TOC mapping fails.
    """
    clean = line.strip()

    if not is_main_section_heading(clean):
        return False

    if re.search(r"\.{4,}", clean):
        return False

    # reject TOC-like trailing page number
    if re.search(r"\s+\d+\s*$", clean):
        return False

    text_part = re.sub(r"^\d+\.\s+", "", clean).strip()

    if text_part.endswith("."):
        return False

    word_count = len(text_part.split())
    if word_count > 10:
        return False

    return True


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

def detect_toc_sections(doc):
    """
    Detect main sections from TOC only.
    Supports:
      5. Conclusions and Recommendations 8
      5. Conclusions and Recommendations........8
    """
    pages = doc["pages"]
    sections = []

    in_toc = False
    toc_started = False

    toc_line_re = re.compile(r"^(\d+)\.\s+(.+?)(?:\s*\.{2,}\s*|\s+)(\d+)\s*$")

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

            if re.match(r"^\d+\.\d+", display_title):
                continue

            display_title = clean_toc_title(display_title)

            sections.append({
                "num": sec_num,
                "title": clean_for_word(display_title),
                "toc_page": page_index,
                "target_page": target_page,
            })

        if toc_started and not in_toc:
            break

    unique = []
    seen = set()
    for sec in sections:
        if sec["title"] not in seen:
            seen.add(sec["title"])
            unique.append(sec)

    return unique


# ---------------------------------------------------
# Section heading matching
# ---------------------------------------------------

def heading_matches_section(line: str, section: dict) -> bool:
    clean = clean_toc_title(line.strip())
    num = section["num"]

    if not re.match(rf"^{num}[\.\s]", clean):
        return False

    if re.match(r"^\d+\.\d+", clean):
        return False

    expected_text = section["title"].split(".", 1)[1].strip() if "." in section["title"] else section["title"]
    expected_norm = normalize_text(expected_text)

    candidate = re.sub(rf"^{num}[\.\s]+", "", clean).strip()
    candidate_norm = normalize_text(candidate)

    if not candidate_norm:
        return False

    return expected_norm in candidate_norm or candidate_norm in expected_norm


def locate_section_starts_from_toc(doc, sections):
    """
    Map TOC sections to body headings in order.
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
            clean = clean_toc_title(line.strip())

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
# Fallback: detect headings from body directly
# ---------------------------------------------------

def detect_body_sections(doc):
    """
    Fallback when TOC detection / mapping fails.
    """
    flat_lines = doc["flat_lines"]
    sections = []

    for idx, (page_index, line) in enumerate(flat_lines):
        clean = clean_toc_title(line.strip())

        if looks_like_footer_or_noise(clean):
            continue

        if looks_like_table_noise(clean):
            continue

        if looks_like_appendix_or_caption_start(clean):
            continue

        if looks_like_body_heading_candidate(clean):
            num_match = re.match(r"^(\d+)\.", clean)
            if not num_match:
                continue

            sec_num = int(num_match.group(1))

            sections.append({
                "num": sec_num,
                "title": clean_for_word(clean),
                "toc_page": -1,
                "target_page": page_index + 1,
                "start_idx": idx
            })

    unique = []
    seen = set()
    for sec in sections:
        if sec["title"] not in seen:
            seen.add(sec["title"])
            unique.append(sec)

    return unique


# ---------------------------------------------------
# Public detection API
# ---------------------------------------------------

def detect_sections(doc):
    """
    Final section detection used by app.

    Strategy:
    1. Try TOC detection + body mapping
    2. If that fails, fallback to body heading detection
    """
    toc_sections = detect_toc_sections(doc)
    if toc_sections:
        located = locate_section_starts_from_toc(doc, toc_sections)
        if located:
            return located

    return detect_body_sections(doc)


# ---------------------------------------------------
# Section extraction
# ---------------------------------------------------

def extract_section(doc, all_sections, section):
    """
    Extract from this section start to the next section start.
    Also stops before appendix/caption content.
    """
    if "start_idx" not in section:
        return ""

    flat_lines = doc["flat_lines"]

    current_pos = None
    for i, sec in enumerate(all_sections):
        if sec["title"] == section["title"] and sec.get("start_idx") == section.get("start_idx"):
            current_pos = i
            break

    if current_pos is None:
        return ""

    start_idx = section["start_idx"]

    if current_pos < len(all_sections) - 1:
        end_idx = all_sections[current_pos + 1]["start_idx"]
    else:
        end_idx = len(flat_lines)

    collected = []

    for idx in range(start_idx, end_idx):
        _, line = flat_lines[idx]
        clean = line.strip()

        if idx > start_idx:
            if looks_like_appendix_or_caption_start(clean):
                break

        if looks_like_footer_or_noise(clean):
            continue

        if looks_like_table_noise(clean):
            continue

        trimmed = trim_line_before_noise(clean)
        if not trimmed:
            break

        collected.append(clean_for_word(trimmed))

    return format_output(collected)


# ---------------------------------------------------
# Formatting
# ---------------------------------------------------

def format_output(lines):
    """
    Preserve:
    - main headings
    - subsection headings
    - plain subheadings
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

        if is_main_section_heading(clean) or is_subsection_heading(clean) or is_plain_subheading(clean):
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