import re
from pypdf import PdfReader


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def clean_for_word(text: str) -> str:
    """
    Remove invalid XML/control chars that can break python-docx.
    Keep tabs/newlines/carriage returns.
    """
    if not text:
        return ""
    return "".join(
        ch for ch in text
        if ch in ("\t", "\n", "\r") or ord(ch) >= 32
    )


def normalize_extracted_line(text: str) -> str:
    """
    Clean common extraction artifacts.
    """
    if not text:
        return ""
    text = clean_for_word(text)
    text = text.replace("¶", "")
    text = text.replace("•", "")
    text = text.replace("", "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
    line = line.strip()
    if re.match(r"^\d+\.\d+", line):
        return False
    return re.match(r"^\d+\.\s+[A-Za-z]", line) is not None


def is_subsection_heading(line: str) -> bool:
    return re.match(r"^\d+\.\d+\s+[A-Za-z]", line.strip()) is not None


def is_numbered_bullet(line: str) -> bool:
    line = line.strip()
    return re.match(r"^\d+\.\s+\S+", line) is not None and not is_main_section_heading(line)


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


def looks_like_date_footer(line: str) -> bool:
    clean = line.strip().lower()
    return re.match(
        r"^(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?)\s+\d{4}$",
        clean
    ) is not None


def looks_like_file_path_or_internal(line: str) -> bool:
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
    clean = line.strip()
    low = clean.lower()

    if low.startswith("appendix") or low.startswith("appendices"):
        return True

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


def is_continuation_start(text: str) -> bool:
    if not text:
        return False

    low = text.strip().lower()
    continuation_words = (
        "and ", "or ", "but ", "with ", "to ", "of ", "for ",
        "in ", "on ", "at ", "from ", "by ", "during "
    )

    if low.startswith(continuation_words):
