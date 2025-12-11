from polib import pofile, POFile
from subprocess import run, CalledProcessError


class MergeConfig:
    """Configuration for merge behavior."""

    def __init__(self):
        self.strategy = self._get_config('merge.django-po-merge.strategy', 'none')
        prefer_non_fuzzy_str = self._get_config('merge.django-po-merge.prefer-non-fuzzy', 'true')
        self.prefer_non_fuzzy = prefer_non_fuzzy_str.lower() == 'true'

    def _get_config(self, key, default):
        """Read a git config value with a default fallback."""
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


def get_entry_key(entry):
    """
    Create a unique key for a PO entry.

    The key includes msgctxt (context), msgid (message), and obsolete flag
    to ensure entries are uniquely identified even if they have the same
    msgid but different contexts or obsolete status.
    """
    return (entry.msgctxt, entry.msgid, entry.obsolete)


def merge_po_files(base_path, ours_path, theirs_path, config):
    try:
        base_po = pofile(base_path)
        ours_po = pofile(ours_path)
        theirs_po = pofile(theirs_path)

        base_dict = {get_entry_key(entry): entry for entry in base_po if entry.msgid}
        ours_dict = {get_entry_key(entry): entry for entry in ours_po if entry.msgid}
        theirs_dict = {get_entry_key(entry): entry for entry in theirs_po if entry.msgid}

        all_keys = set(base_dict.keys()) | set(ours_dict.keys()) | set(theirs_dict.keys())

        merged_po = POFile()
        merged_po.metadata = ours_po.metadata

        for key in sorted(all_keys, key=lambda x: (x[2], x[1], x[0] or '')):
            base_entry = base_dict.get(key)
            ours_entry = ours_dict.get(key)
            theirs_entry = theirs_dict.get(key)

            merged_entry = decide_entry(base_entry, ours_entry, theirs_entry, config)

            if merged_entry is not None:
                merged_po.append(merged_entry)

        merged_po.save(ours_path)

        return 0

    except Exception as e:
        print(f"Merge failed: {e}")
        return 1


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
    """
    Resolve a conflict between two entries based on strategy and fuzzy preference.

    If prefer_non_fuzzy is True and one entry is fuzzy while the other isn't,
    always prefer the non-fuzzy entry.

    Otherwise, apply the strategy:
    - 'ours': prefer our changes
    - 'theirs': prefer their changes
    - 'none': raise an exception (fail the merge)
    """
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
        raise Exception(
            f"Merge conflict for msgid '{ours_entry.msgid}': "
            f"both sides modified differently. "
            f"Run 'django-po-merge install --strategy=ours' or '--strategy=theirs' to resolve automatically."
        )
    else:
        raise Exception(f"Unknown strategy: {config.strategy}")


def entries_equal(entry1, entry2):
    """
    Check if two entries have the same translation content.

    Compares:
    - msgstr: regular translations
    - msgstr_plural: plural form translations
    - fuzzy: whether translation is uncertain/needs review

    Ignores:
    - occurrences: change with every makemessages run
    - comments: metadata only
    - other flags: not semantically important for merge
    """
    return (
        entry1.msgstr == entry2.msgstr
        and entry1.msgstr_plural == entry2.msgstr_plural
        and entry1.fuzzy == entry2.fuzzy
    )
