from polib import pofile, POFile
from subprocess import run, CalledProcessError
from .parser import parse_po_resilient, format_parse_error_conflict
import sys
import os
import re

class UnresolvedConflict(Exception):
    def __init__(self, ours_entry, theirs_entry):
        self.ours_entry = ours_entry
        self.theirs_entry = theirs_entry
        super().__init__(f"Conflict for msgid '{ours_entry.msgid}'")


class MergeConfig:
    def __init__(self):
        self.strategy = self._get_config('merge.po-merge.strategy', 'none')
        prefer_non_fuzzy_str = self._get_config('merge.po-merge.prefer-non-fuzzy', 'true')
        self.prefer_non_fuzzy = prefer_non_fuzzy_str.lower() == 'true'
        validate_compiled_str = self._get_config('merge.po-merge.validate-compiled', 'true')
        self.validate_compiled = validate_compiled_str.lower() == 'true'

    def _get_config(self, key, default):
        try:
            result = run(
                ['git', 'config', '--get', key],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except CalledProcessError:
            return default


def get_unique_entry_key(entry):
    return (entry.msgctxt, entry.msgid)


def entry_to_text(entry):
    return str(entry)


def format_merge_conflicts(merge_conflicts):
    if not merge_conflicts:
        return ""

    conflicts = []
    for ours_entry, theirs_entry in merge_conflicts:
        conflict = f"""<<<<<<< MERGE CONFLICT
{entry_to_text(ours_entry)}
=======
{entry_to_text(theirs_entry)}
>>>>>>> THEIRS
"""
        conflicts.append(conflict)

    return '\n\n'.join(conflicts)


def validate_po_compilation(po_file_path):
    try:
        result = run(
            ['msgfmt', '-c', '-o', os.devnull, po_file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            error_output = result.stderr or result.stdout
            # Remove temp file references, keep just line numbers and messages
            error_output = re.sub(r'\.merge_file_\w+:', '', error_output)
            return False, error_output.strip()
        return True, None
    except FileNotFoundError:
        # msgfmt not available, print warning once and skip validation
        print("Warning: msgfmt not found. Skipping PO file compilation validation.", file=sys.stderr)
        print("Install GNU gettext tools to enable validation.", file=sys.stderr)
        return True, None
    except Exception as e:
        return False, str(e)


def format_compilation_error(error_message):
    return f"""<<<<<<< COMPILATION ERROR
{error_message}
=======
# The merged PO file failed compilation validation with msgfmt.
# Please fix the errors above manually.
>>>>>>> COMPILATION ERROR
    """


def merge_po_files(base_path, ours_path, theirs_path, config):
    base_result = parse_po_resilient(base_path)
    ours_result = parse_po_resilient(ours_path)
    theirs_result = parse_po_resilient(theirs_path)

    base_dict = {get_unique_entry_key(entry): entry for entry in base_result['valid_entries']}
    ours_dict = {get_unique_entry_key(entry): entry for entry in ours_result['valid_entries']}
    theirs_dict = {get_unique_entry_key(entry): entry for entry in theirs_result['valid_entries']}

    all_keys = set(base_dict.keys()) | set(ours_dict.keys()) | set(theirs_dict.keys())

    merge_conflicts = []
    merged_entries = []

    for key in all_keys:
        base_entry = base_dict.get(key)
        ours_entry = ours_dict.get(key)
        theirs_entry = theirs_dict.get(key)

        try:
            merged_entry = decide_entry(base_entry, ours_entry, theirs_entry, config)

            if merged_entry is not None:
                merged_entries.append(merged_entry)
        except UnresolvedConflict as e:
            merge_conflicts.append((e.ours_entry, e.theirs_entry))

    active_entries = [e for e in merged_entries if not e.obsolete]
    obsolete_entries = [e for e in merged_entries if e.obsolete]

    active_entries.sort(key=lambda e: (e.msgid, e.msgctxt or ''))
    obsolete_entries.sort(key=lambda e: (e.msgid, e.msgctxt or ''))

    merged_po = POFile()
    if config.strategy == 'theirs':
        merged_po.metadata = theirs_result['metadata'] if theirs_result['metadata'] else {}
    else:
        merged_po.metadata = ours_result['metadata'] if ours_result['metadata'] else {}

    merged_po.extend(active_entries + obsolete_entries)

    try:
        merged_po.save(ours_path)
    except Exception as e:
        print(f"Failed to save merged file: {e}")
        return 1

    compilation_error = None
    if config.validate_compiled:
        success, error_msg = validate_po_compilation(ours_path)
        if not success:
            compilation_error = error_msg

    all_conflict_markers = []

    has_parse_failures = (
        len(base_result['failed_entries']) > 0 or
        len(ours_result['failed_entries']) > 0 or
        len(theirs_result['failed_entries']) > 0
    )

    if has_parse_failures:
        parse_markers = format_parse_error_conflict(
            base_result['failed_entries'],
            ours_result['failed_entries'],
            theirs_result['failed_entries']
        )
        if parse_markers:
            all_conflict_markers.append(parse_markers)

    if merge_conflicts:
        merge_conflicts.sort(key=lambda x: (x[0].msgid, x[0].msgctxt or ''))
        merge_markers = format_merge_conflicts(merge_conflicts)
        if merge_markers:
            all_conflict_markers.append(merge_markers)

    if compilation_error:
        compilation_marker = format_compilation_error(compilation_error)
        all_conflict_markers.append(compilation_marker)

    if all_conflict_markers:
        try:
            with open(ours_path, 'a', encoding='utf-8') as f:
                f.write('\n\n' + '\n\n'.join(all_conflict_markers))
        except Exception as e:
            print(f"Failed to write conflict markers: {e}")

    if merge_conflicts or has_parse_failures:
        return 1
    else:
        return 0


def decide_entry(base_entry, ours_entry, theirs_entry, config):
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
                return resolve_conflict(ours_entry, theirs_entry, config)

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
                    return resolve_conflict(ours_entry, theirs_entry, config)


def resolve_conflict(ours_entry, theirs_entry, config):
    if ours_entry.obsolete and not theirs_entry.obsolete:
        return theirs_entry
    elif theirs_entry.obsolete and not ours_entry.obsolete:
        return ours_entry

    if config.prefer_non_fuzzy:
        if ours_entry.fuzzy and not theirs_entry.fuzzy:
            return theirs_entry
        elif theirs_entry.fuzzy and not ours_entry.fuzzy:
            return ours_entry

    if config.strategy == 'ours':
        return ours_entry
    elif config.strategy == 'theirs':
        return theirs_entry
    elif config.strategy == 'none':
        raise UnresolvedConflict(ours_entry, theirs_entry)
    else:
        raise Exception(f"Unknown strategy: {config.strategy}")


def entries_equal(entry1, entry2):
    return (
        entry1.msgstr == entry2.msgstr
        and entry1.msgstr_plural == entry2.msgstr_plural
        and entry1.fuzzy == entry2.fuzzy
    )
