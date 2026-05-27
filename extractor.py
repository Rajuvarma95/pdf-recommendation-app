def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def extract_section(lines, title):
    content = []
    found = False

    # ✅ normalize title
    norm_title = normalize(title)

    for line in lines:
        clean = line.strip()
        norm_line = normalize(clean)

        # ✅ find actual section
        if not found:
            if norm_title in norm_line:
                # skip TOC dotted lines
                if "..." not in clean:
                    found = True
                    content.append(clean)
            continue

        lower = clean.lower()

        # ✅ stop at next section
        if re.match(r'^\d+\.\s+', clean):
            break

        # ✅ stop noise
        if "appendix" in lower:
            break
        if "figure" in lower:
            break

        content.append(clean)

    return format_output(content)
