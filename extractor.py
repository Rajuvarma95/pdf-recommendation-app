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
        if ch in ("\t", "\n", "\r") or ord(ch) >= 32
    )


def normalize_extracted_line(text: str) -> str:
    """
    Clean common PDF extraction artifacts.
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
