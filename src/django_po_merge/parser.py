from polib import pofile
import re


def split_po_entries(text):
    chunks = text.split('\n\n')
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def create_unique_entry_from_text(entry_text):
    try:
        po = pofile(entry_text)
        if len(po) > 0:
            return po[0], None
        else:
            return None, "No entry found in text"
    except Exception as e:
        return None, str(e)


def extract_entry_key_from_text(text):
    # Check if obsolete (all lines start with #~)
    lines = text.strip().split('\n')
    obsolete = all(line.strip().startswith('#~') for line in lines if line.strip())

    # Extract msgid (with or without #~ prefix)
    msgid_match = re.search(r'#?~?\s*msgid\s+"([^"]*)"', text)
    msgid = msgid_match.group(1) if msgid_match else None

    # Extract msgctxt if present
    msgctxt_match = re.search(r'#?~?\s*msgctxt\s+"([^"]*)"', text)
    msgctxt = msgctxt_match.group(1) if msgctxt_match else None

    return (msgctxt, msgid, obsolete)


def parse_po_resilient(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: Failed to read file '{file_path}': {e}")
        raise

    entry_chunks = split_po_entries(content)
    valid_entries = []
    failed_entries = []
    metadata = {}
    line_offset = 0

    for chunk in entry_chunks:
        is_metadata = 'msgid ""' in chunk and 'msgstr ""' in chunk

        if is_metadata:
            try:
                temp_po = pofile(chunk)
                metadata = temp_po.metadata
            except Exception as e:
                failed_entries.append((chunk, str(e), line_offset))
        else:
            entry, error = create_unique_entry_from_text(chunk)

            if entry is not None:
                if entry.msgid:
                    valid_entries.append(entry)
            else:
                failed_entries.append((chunk, error, line_offset))

        line_offset += chunk.count('\n') + 2

    return {
        'metadata': metadata,
        'valid_entries': valid_entries,
        'failed_entries': failed_entries,
        'parse_successful': len(failed_entries) == 0
    }


def format_parse_error_conflict(base_failed, ours_failed, theirs_failed):
    failures_by_key = {}

    for source, failures in [('BASE', base_failed), ('OURS', ours_failed), ('THEIRS', theirs_failed)]:
        for raw_text, error, line_num in failures:
            entry_key = extract_entry_key_from_text(raw_text)

            if entry_key not in failures_by_key:
                failures_by_key[entry_key] = {
                    'base': None,
                    'ours': None,
                    'theirs': None,
                    'error': error
                }

            failures_by_key[entry_key][source.lower()] = (raw_text, line_num)

    conflicts = []
    for failure_info in failures_by_key.values():
        base_info = failure_info['base']
        ours_info = failure_info['ours']
        theirs_info = failure_info['theirs']
        error = failure_info['error']

        sources = []
        if base_info:
            sources.append(f"BASE line {base_info[1]}")
        if ours_info:
            sources.append(f"OURS line {ours_info[1]}")
        if theirs_info:
            sources.append(f"THEIRS line {theirs_info[1]}")
        source_info = ', '.join(sources)

        if base_info and ours_info and theirs_info:
            conflict = f"""
                <<<<<<< PARSE ERROR ({source_info}): {error}
                {ours_info[0]}
                ||||||| BASE
                {base_info[0]}
                =======
                {theirs_info[0]}
                >>>>>>> PARSE ERROR
            """
        elif base_info and (ours_info or theirs_info):
            other_info = ours_info if ours_info else theirs_info
            other_label = "OURS" if ours_info else "THEIRS"
            conflict = f"""
                <<<<<<< PARSE ERROR ({source_info}): {error}
                {other_info[0]}
                ||||||| BASE
                {base_info[0]}
                =======
                # Failed to parse this entry. Please fix the syntax error and resolve manually.
                >>>>>>> {other_label}
            """
        else:
            info = ours_info if ours_info else theirs_info
            label = "OURS" if ours_info else "THEIRS"
            conflict = f"""
                <<<<<<< PARSE ERROR ({source_info}): {error}
                {info[0]}
                =======
                # Failed to parse this entry. Please fix the syntax error and resolve manually.
                >>>>>>> {label}
            """

        conflicts.append(conflict)

    return '\n'.join(conflicts)
