from tempfile import NamedTemporaryFile
from pathlib import Path
from polib import POFile, POEntry, pofile
from django_po_merge import merge_po_files


def create_po_file(entries, metadata=None):
    """
    Helper to create a POFile programmatically.

    Args:
        entries: list of dicts with keys: msgid, msgstr, msgctxt (optional),
                 msgid_plural (optional), msgstr_plural (optional)
        metadata: dict of metadata key-value pairs

    Returns:
        POFile object
    """
    po = POFile()

    if metadata:
        po.metadata = metadata
    else:
        po.metadata = {
            'Content-Type': 'text/plain; charset=UTF-8',
            'Language': 'sv',
        }

    for entry_data in entries:
        entry = POEntry(
            msgid=entry_data['msgid'],
            msgstr=entry_data.get('msgstr', ''),
            msgctxt=entry_data.get('msgctxt'),
        )

        if 'msgid_plural' in entry_data:
            entry.msgid_plural = entry_data['msgid_plural']
            entry.msgstr_plural = entry_data.get('msgstr_plural', {})

        po.append(entry)

    return po


def save_po_to_temp(po_file):
    """Save a POFile to a temporary file and return the path."""
    with NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
        temp_path = Path(tmp.name)
    po_file.save(str(temp_path))
    return temp_path


def run_merge_test(base_entries, ours_entries, theirs_entries, expected_entries,
                   base_metadata=None, ours_metadata=None, theirs_metadata=None):
    """
    Helper to run a merge test with programmatically created PO files.

    Returns the merged entries as a dict for assertions.
    """
    base_po = create_po_file(base_entries, base_metadata)
    ours_po = create_po_file(ours_entries, ours_metadata)
    theirs_po = create_po_file(theirs_entries, theirs_metadata)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0, "Merge should succeed"

        merged_po = pofile(str(ours_path))
        merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}

        assert merged_entries == expected_entries, f"Expected {expected_entries}, got {merged_entries}"

        return merged_entries
    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_new_entries_added_in_different_branches():
    """
    Scenario: Both branches add different new entries.
    Expected: All entries from both branches are included.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'goodbye', 'msgstr': 'hejdå'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'goodbye', 'msgstr': 'hejdå'},
        {'msgid': 'welcome', 'msgstr': 'välkommen'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'goodbye', 'msgstr': 'hejdå'},
        {'msgid': 'thank you', 'msgstr': 'tack'},
    ]

    expected = {
        'hello': 'hej',
        'goodbye': 'hejdå',
        'welcome': 'välkommen',
        'thank you': 'tack',
    }

    run_merge_test(base, ours, theirs, expected)


def test_same_entry_modified_differently():
    """
    Scenario: Both branches modify the same entry with different translations.
    Expected: OURS wins (feature branch has newer changes).
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hallå'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'tjena'},
    ]

    expected = {
        'hello': 'hallå',
    }

    run_merge_test(base, ours, theirs, expected)


def test_entry_deleted_in_ours_modified_in_theirs():
    """
    Scenario: Entry is deleted in OURS but modified in THEIRS.
    Expected: THEIRS modification is kept.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'old', 'msgstr': 'gammal'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'old', 'msgstr': 'föråldrad'},
    ]

    expected = {
        'hello': 'hej',
        'old': 'föråldrad',
    }

    run_merge_test(base, ours, theirs, expected)


def test_entry_modified_in_ours_deleted_in_theirs():
    """
    Scenario: Entry is modified in OURS but deleted in THEIRS.
    Expected: OURS modification is kept.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'old', 'msgstr': 'gammal'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'old', 'msgstr': 'föråldrad'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    expected = {
        'hello': 'hej',
        'old': 'föråldrad',
    }

    run_merge_test(base, ours, theirs, expected)


def test_entry_deleted_in_both_branches():
    """
    Scenario: Entry is deleted in both branches.
    Expected: Entry stays deleted.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'old', 'msgstr': 'gammal'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    expected = {
        'hello': 'hej',
    }

    run_merge_test(base, ours, theirs, expected)


def test_same_entry_added_with_same_translation():
    """
    Scenario: Both branches add the same entry with identical translation.
    Expected: One copy is kept.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'new', 'msgstr': 'ny'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'new', 'msgstr': 'ny'},
    ]

    expected = {
        'hello': 'hej',
        'new': 'ny',
    }

    run_merge_test(base, ours, theirs, expected)


def test_same_entry_added_with_different_translations():
    """
    Scenario: Both branches add the same entry with different translations.
    Expected: OURS wins (feature branch has newer changes).
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'new', 'msgstr': 'ny'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
        {'msgid': 'new', 'msgstr': 'nytt'},
    ]

    expected = {
        'hello': 'hej',
        'new': 'ny',
    }

    run_merge_test(base, ours, theirs, expected)


def test_msgctxt_context_handling():
    """
    Scenario: Same msgid with different contexts (msgctxt).
    Expected: Both entries should be preserved as they are different.
    """
    base = []

    ours = [
        {'msgid': 'File', 'msgstr': 'Arkiv', 'msgctxt': 'menu'},
    ]

    theirs = [
        {'msgid': 'File', 'msgstr': 'Arkivera', 'msgctxt': 'verb'},
    ]

    base_po = create_po_file(base)
    ours_po = create_po_file(ours)
    theirs_po = create_po_file(theirs)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        file_entries = [e for e in merged_po if e.msgid == 'File']
        assert len(file_entries) == 2, f"Expected 2 'File' entries with different contexts, got {len(file_entries)}"

        contexts = {e.msgctxt for e in file_entries}
        assert contexts == {'menu', 'verb'}, f"Expected both contexts, got {contexts}"

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_plural_forms():
    """
    Scenario: Entries with plural forms (msgid_plural, msgstr_plural).
    Expected: Plural forms are correctly merged.
    """
    base = [
        {
            'msgid': 'one file',
            'msgid_plural': '%d files',
            'msgstr_plural': {0: 'en fil', 1: '%d filer'}
        },
    ]

    ours = [
        {
            'msgid': 'one file',
            'msgid_plural': '%d files',
            'msgstr_plural': {0: 'en fil', 1: '%d filer'}
        },
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    theirs = [
        {
            'msgid': 'one file',
            'msgid_plural': '%d files',
            'msgstr_plural': {0: 'en fil', 1: '%d filer'}
        },
        {'msgid': 'goodbye', 'msgstr': 'hejdå'},
    ]

    base_po = create_po_file(base)
    ours_po = create_po_file(ours)
    theirs_po = create_po_file(theirs)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        msgids = {e.msgid for e in merged_po if e.msgid}
        assert msgids == {'one file', 'hello', 'goodbye'}

        plural_entry = [e for e in merged_po if e.msgid == 'one file'][0]
        assert plural_entry.msgid_plural == '%d files'
        assert plural_entry.msgstr_plural[0] == 'en fil'
        assert plural_entry.msgstr_plural[1] == '%d filer'

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_multiline_msgid_msgstr():
    """
    Scenario: Entries with multi-line msgid and msgstr.
    Expected: Multi-line strings are correctly handled.
    """
    base = []

    ours = [
        {
            'msgid': 'This is a long message that spans multiple lines in the source code',
            'msgstr': 'Detta är ett långt meddelande som spänner över flera rader i källkoden',
        },
    ]

    theirs = [
        {
            'msgid': 'Another long message',
            'msgstr': 'Ett annat långt meddelande',
        },
    ]

    expected = {
        'This is a long message that spans multiple lines in the source code':
            'Detta är ett långt meddelande som spänner över flera rader i källkoden',
        'Another long message': 'Ett annat långt meddelande',
    }

    run_merge_test(base, ours, theirs, expected)


def test_metadata_handling():
    """
    Scenario: Different metadata in different branches.
    Expected: OURS metadata is used in the merged result.
    """
    base_meta = {
        'Content-Type': 'text/plain; charset=UTF-8',
        'Language': 'sv',
        'POT-Creation-Date': '2023-04-19 11:53+0000',
    }

    ours_meta = {
        'Content-Type': 'text/plain; charset=UTF-8',
        'Language': 'sv',
        'POT-Creation-Date': '2023-05-01 10:00+0000',
    }

    theirs_meta = {
        'Content-Type': 'text/plain; charset=UTF-8',
        'Language': 'sv',
        'POT-Creation-Date': '2023-05-02 09:00+0000',
    }

    base = [{'msgid': 'hello', 'msgstr': 'hej'}]
    ours = [{'msgid': 'hello', 'msgstr': 'hej'}]
    theirs = [{'msgid': 'hello', 'msgstr': 'hej'}]

    base_po = create_po_file(base, base_meta)
    ours_po = create_po_file(ours, ours_meta)
    theirs_po = create_po_file(theirs, theirs_meta)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        assert merged_po.metadata['POT-Creation-Date'] == '2023-05-01 10:00+0000'

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_entry_order_is_normalized():
    """
    Scenario: Entries appear in different orders in different branches.
    Expected: Merged result has entries in sorted order.
    """
    base = [
        {'msgid': 'zebra', 'msgstr': 'zebra'},
        {'msgid': 'apple', 'msgstr': 'äpple'},
    ]

    ours = [
        {'msgid': 'apple', 'msgstr': 'äpple'},
        {'msgid': 'zebra', 'msgstr': 'zebra'},
        {'msgid': 'banana', 'msgstr': 'banan'},
    ]

    theirs = [
        {'msgid': 'zebra', 'msgstr': 'zebra'},
        {'msgid': 'cherry', 'msgstr': 'körsbär'},
        {'msgid': 'apple', 'msgstr': 'äpple'},
    ]

    base_po = create_po_file(base)
    ours_po = create_po_file(ours)
    theirs_po = create_po_file(theirs)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        msgids_in_order = [e.msgid for e in merged_po if e.msgid]

        expected_order = ['apple', 'banana', 'cherry', 'zebra']
        assert msgids_in_order == expected_order, f"Expected {expected_order}, got {msgids_in_order}"

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_obsolete_entry_preserved():
    """
    Scenario: Obsolete entries are preserved during merge.
    Expected: Obsolete entries from both branches are included.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    theirs = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    base_po = create_po_file(base)
    ours_po = create_po_file(ours)
    theirs_po = create_po_file(theirs)

    obsolete_ours = POEntry(msgid='old_ours', msgstr='gammal ours', obsolete=True)
    ours_po.append(obsolete_ours)

    obsolete_theirs = POEntry(msgid='old_theirs', msgstr='gammal theirs', obsolete=True)
    theirs_po.append(obsolete_theirs)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        obsolete_entries = [e for e in merged_po if e.obsolete]
        obsolete_msgids = {e.msgid for e in obsolete_entries}

        assert 'old_ours' in obsolete_msgids
        assert 'old_theirs' in obsolete_msgids

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_active_and_obsolete_same_msgid():
    """
    Scenario: Same msgid exists as both active and obsolete entry.
    Expected: Both entries are preserved (different keys).
    """

    base = []
    ours_po = create_po_file([])
    theirs_po = create_po_file([])

    ours_po.append(POEntry(msgid='current', msgstr='nuvarande', obsolete=False))

    theirs_po.append(POEntry(msgid='current', msgstr='gammal översättning', obsolete=True))

    base_po = create_po_file(base)
    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        current_entries = [e for e in merged_po if e.msgid == 'current']
        assert len(current_entries) == 2

        active = [e for e in current_entries if not e.obsolete]
        obsolete = [e for e in current_entries if e.obsolete]

        assert len(active) == 1
        assert len(obsolete) == 1
        assert active[0].msgstr == 'nuvarande'
        assert obsolete[0].msgstr == 'gammal översättning'

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_fuzzy_flag_difference_detected():
    """
    Scenario: Same msgstr but different fuzzy flag.
    Expected: Entries are considered different.
    """

    base_po = create_po_file([])
    base_po.append(POEntry(msgid='hello', msgstr='hej'))

    ours_po = create_po_file([])
    ours_po.append(POEntry(msgid='hello', msgstr='hej'))

    theirs_po = create_po_file([])
    theirs_entry = POEntry(msgid='hello', msgstr='hej')
    theirs_entry.flags.append('fuzzy')
    theirs_po.append(theirs_entry)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
        assert hello_entry.fuzzy == True

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_fuzzy_flag_removed():
    """
    Scenario: BASE is fuzzy, one branch removes fuzzy flag.
    Expected: Non-fuzzy version wins (removing fuzzy is an improvement).
    """

    base_po = create_po_file([])
    base_entry = POEntry(msgid='hello', msgstr='hej')
    base_entry.flags.append('fuzzy')
    base_po.append(base_entry)

    ours_po = create_po_file([])
    ours_po.append(POEntry(msgid='hello', msgstr='hej'))

    theirs_po = create_po_file([])
    theirs_entry = POEntry(msgid='hello', msgstr='hej')
    theirs_entry.flags.append('fuzzy')
    theirs_po.append(theirs_entry)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        # OURS changed (removed fuzzy), THEIRS didn't, so OURS wins
        hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
        assert hello_entry.fuzzy == False

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_plural_forms_conflict():
    """
    Scenario: Both branches modify different plural forms.
    Expected: OURS wins (feature branch has newer changes).
    """
    base = [
        {
            'msgid': 'one file',
            'msgid_plural': '%d files',
            'msgstr_plural': {0: 'en fil', 1: '%d filer'}
        },
    ]

    ours = [
        {
            'msgid': 'one file',
            'msgid_plural': '%d files',
            'msgstr_plural': {0: 'ett dokument', 1: '%d filer'}
        },
    ]

    theirs = [
        {
            'msgid': 'one file',
            'msgid_plural': '%d files',
            'msgstr_plural': {0: 'en fil', 1: '%d dokument'}
        },
    ]

    base_po = create_po_file(base)
    ours_po = create_po_file(ours)
    theirs_po = create_po_file(theirs)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        entry = [e for e in merged_po if e.msgid == 'one file'][0]
        assert entry.msgstr_plural[0] == 'ett dokument'
        assert entry.msgstr_plural[1] == '%d filer'

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_conflict_prefers_non_fuzzy_when_both_add():
    """
    Scenario: Both branches add the same entry with different translations.
              One is fuzzy, one is not.
    Expected: Non-fuzzy entry wins.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours_po = create_po_file(base)
    ours_entry = POEntry(msgid='new', msgstr='ny')
    ours_entry.flags.append('fuzzy')
    ours_po.append(ours_entry)

    theirs_po = create_po_file(base)
    theirs_po.append(POEntry(msgid='new', msgstr='nytt'))

    base_po = create_po_file(base)
    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        new_entry = [e for e in merged_po if e.msgid == 'new'][0]
        assert new_entry.msgstr == 'nytt'
        assert new_entry.fuzzy == False

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_conflict_prefers_non_fuzzy_when_both_modify():
    """
    Scenario: Both branches modify the same entry with different translations.
              One is fuzzy, one is not.
    Expected: Non-fuzzy entry wins.
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours_po = create_po_file(base)
    ours_entry = POEntry(msgid='hello', msgstr='hallå')
    ours_entry.flags.append('fuzzy')
    ours_po[0] = ours_entry

    theirs_po = create_po_file(base)
    theirs_po[0].msgstr = 'tjena'

    base_po = create_po_file(base)
    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
        assert hello_entry.msgstr == 'tjena'
        assert hello_entry.fuzzy == False

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_conflict_both_fuzzy_prefers_ours():
    """
    Scenario: Both branches modify the same entry with different translations.
              Both are fuzzy.
    Expected: OURS wins (default conflict resolution).
    """
    base = [
        {'msgid': 'hello', 'msgstr': 'hej'},
    ]

    ours_po = create_po_file(base)
    ours_entry = POEntry(msgid='hello', msgstr='hallå')
    ours_entry.flags.append('fuzzy')
    ours_po[0] = ours_entry

    theirs_po = create_po_file(base)
    theirs_entry = POEntry(msgid='hello', msgstr='tjena')
    theirs_entry.flags.append('fuzzy')
    theirs_po[0] = theirs_entry

    base_po = create_po_file(base)
    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
        assert hello_entry.msgstr == 'hallå'
        assert hello_entry.fuzzy == True

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_comprehensive_sorting():
    """
    Scenario: Mix of active and obsolete entries with various msgids and msgctxts.
    Expected: Active entries sorted by msgid then msgctxt, obsolete entries at end sorted by msgid.
    """
    base = []

    ours_po = create_po_file([])
    ours_po.append(POEntry(msgid='zebra', msgstr='sebra'))
    ours_po.append(POEntry(msgid='banana', msgstr='banan', msgctxt='fruit'))
    ours_po.append(POEntry(msgid='banana', msgstr='banankurva', msgctxt='plantain'))
    ours_po.append(POEntry(msgid='obsolete_one', msgstr='föråldrad ett', obsolete=True))

    theirs_po = create_po_file([])
    theirs_po.append(POEntry(msgid='apple', msgstr='äpple'))
    theirs_po.append(POEntry(msgid='banana', msgstr='banan split', msgctxt='dessert'))
    theirs_po.append(POEntry(msgid='obsolete_three', msgstr='föråldrad tre', obsolete=True))
    theirs_po.append(POEntry(msgid='obsolete_two', msgstr='föråldrad två', obsolete=True))

    base_po = create_po_file(base)
    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path))
        assert result == 0

        merged_po = pofile(str(ours_path))

        active_entries = [e for e in merged_po if e.msgid and not e.obsolete]
        obsolete_entries = [e for e in merged_po if e.msgid and e.obsolete]

        active_order = [(e.msgid, e.msgctxt) for e in active_entries]
        expected_active_order = [
            ('apple', None),
            ('banana', 'dessert'),
            ('banana', 'fruit'),
            ('banana', 'plantain'),
            ('zebra', None),
        ]
        assert active_order == expected_active_order, f"Active order: {active_order}"

        obsolete_order = [e.msgid for e in obsolete_entries]
        expected_obsolete_order = ['obsolete_one', 'obsolete_three', 'obsolete_two']
        assert obsolete_order == expected_obsolete_order, f"Obsolete order: {obsolete_order}"

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()
