def extract_section(lines, title):
    content = []
    found = False

    section_started = False

    for i in range(len(lines)):
        line = lines[i]
        clean = line.strip()

        lower = clean.lower()

        # ✅ STRICT heading match (skip TOC dotted lines)
        if not found:
            if is_heading_match(title, clean):

                # ❌ Skip TOC version
                if "..." in clean:
                    continue

                # ✅ Ensure next lines look like real content (not TOC)
                next_lines = " ".join(lines[i+1:i+5]).lower()

                if "..." in next_lines:
                    continue  # still TOC

                found = True
                section_started = True
                content.append(clean)
                continue

        # ✅ After section start
        if section_started:

            # ✅ Stop at next MAIN section
            if re.match(r'^\d+\.\s+[A-Za-z]', clean):
                break

            # ✅ KEEP sub-sections (8.1, 8.2)
            if re.match(r'^\d+\.\d+', clean):
                content.append(clean)
                continue

            # ✅ KEEP bullet points
            if re.match(r'^\d+\.\s+', clean):
                content.append(clean)
                continue

            # ❌ REMOVE dotted TOC garbage
            if "...." in clean:
                continue

            # ❌ REMOVE table noise
            if any(word in lower for word in [
                "asset details", "policy on a page",
                "owner", "territory", "railway",
                "data availability", "status", "reports"
            ]):
                continue

            # ❌ REMOVE footer
            if any(word in lower for word in [
                "assessment report", "final", "february", "page", "wkl"
            ]):
                continue

            # ✅ KEEP valid content
            content.append(clean)

    return format_output(content)
