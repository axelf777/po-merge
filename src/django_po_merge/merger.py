from polib import pofile, POFile


def merge_po_files(base_path, ours_path, theirs_path):
    try:
        base_po = pofile(base_path)
        ours_po = pofile(ours_path)
        theirs_po = pofile(theirs_path)

        base_dict = {entry.msgid: entry for entry in base_po if entry.msgid}
        ours_dict = {entry.msgid: entry for entry in ours_po if entry.msgid}
        theirs_dict = {entry.msgid: entry for entry in theirs_po if entry.msgid}

        all_msgids = set(base_dict.keys()) | set(ours_dict.keys()) | set(theirs_dict.keys())

        merged_po = POFile()
        merged_po.metadata = ours_po.metadata

        for msgid in sorted(all_msgids):
            base_entry = base_dict.get(msgid)
            ours_entry = ours_dict.get(msgid)
            theirs_entry = theirs_dict.get(msgid)

            merged_entry = decide_entry(base_entry, ours_entry, theirs_entry)

            if merged_entry is not None:
                merged_po.append(merged_entry)

        merged_po.save(ours_path)

        return 0

    except Exception as e:
        print(f"Merge failed: {e}")
        return 1


def decide_entry(base_entry, ours_entry, theirs_entry):
    if base_entry is None:
        if ours_entry is None and theirs_entry is None:
            return None

        elif ours_entry is None:
            return theirs_entry

        elif theirs_entry is None:
            return ours_entry

        else:
            if entries_equal(ours_entry, theirs_entry):
                return ours_entry
            else:
                # For now, prefer THEIRS
                return theirs_entry

    else:
        if ours_entry is None and theirs_entry is None:
            return None

        elif ours_entry is None:
            return theirs_entry

        elif theirs_entry is None:
            return ours_entry

        else:
            ours_changed = not entries_equal(base_entry, ours_entry)
            theirs_changed = not entries_equal(base_entry, theirs_entry)

            if not ours_changed and not theirs_changed:
                return base_entry

            elif ours_changed and not theirs_changed:
                return ours_entry

            elif theirs_changed and not ours_changed:
                return theirs_entry

            else:
                if entries_equal(ours_entry, theirs_entry):
                    return ours_entry
                else:
                    # For now, prefer THEIRS
                    return theirs_entry


def entries_equal(entry1, entry2):
    return entry1.msgstr == entry2.msgstr
