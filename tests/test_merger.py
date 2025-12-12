from tempfile import NamedTemporaryFile
from pathlib import Path
from polib import POFile, POEntry, pofile
from django_po_merge.merger import merge_po_files, MergeConfig


def create_po_file(entries, metadata=None):
    po = POFile()

    if metadata:
        po.metadata = metadata
    else:
        po.metadata = {
            'Content-Type': 'text/plain; charset=UTF-8',
            'Language': 'sv',
        }

    for entry in entries:
        po.append(entry)

    return po


def save_po_to_temp(po_file):
    with NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
        temp_path = Path(tmp.name)
    po_file.save(str(temp_path))
    return temp_path


def run_merge_test(base_entries, ours_entries, theirs_entries, config=None):
    base_po = create_po_file(base_entries)
    ours_po = create_po_file(ours_entries)
    theirs_po = create_po_file(theirs_entries)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    if config is None:
        config = MergeConfig()

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path), config)
        assert result == 0, "Merge should succeed"

        merged_po = pofile(str(ours_path))
        return merged_po
    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_new_entries_added_in_different_branches():
    base = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='goodbye', msgstr='hejdå'),
    ]

    ours = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='goodbye', msgstr='hejdå'),
        POEntry(msgid='welcome', msgstr='välkommen'),
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='goodbye', msgstr='hejdå'),
        POEntry(msgid='thank you', msgstr='tack'),
    ]

    expected = {
        'hello': 'hej',
        'goodbye': 'hejdå',
        'welcome': 'välkommen',
        'thank you': 'tack',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected


def create_conflict_scenario():
    base = [
        POEntry(msgid='modified', msgstr='original'),
        POEntry(msgid='one file', msgid_plural='%d files', msgstr_plural={0: 'en fil', 1: '%d filer'}),
    ]

    ours = [
        POEntry(msgid='modified', msgstr='ours version'),
        POEntry(msgid='new', msgstr='ny'),
        POEntry(msgid='one file', msgid_plural='%d files', msgstr_plural={0: 'ett dokument', 1: '%d filer'}),
    ]

    theirs = [
        POEntry(msgid='modified', msgstr='theirs version'),
        POEntry(msgid='new', msgstr='nytt'),
        POEntry(msgid='one file', msgid_plural='%d files', msgstr_plural={0: 'en fil', 1: '%d dokument'}),
    ]

    return base, ours, theirs


def test_strategy_ours_resolves_conflicts():
    base, ours, theirs = create_conflict_scenario()

    expected = {
        'modified': 'ours version',
        'new': 'ny',
    }

    config = MergeConfig()
    config.strategy = 'ours'
    merged_po = run_merge_test(base, ours, theirs, config)

    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid and entry.msgstr}
    assert merged_entries == expected

    plural_entry = [e for e in merged_po if e.msgid == 'one file'][0]
    assert plural_entry.msgstr_plural[0] == 'ett dokument'
    assert plural_entry.msgstr_plural[1] == '%d filer'


def test_strategy_theirs_resolves_conflicts():
    base, ours, theirs = create_conflict_scenario()

    expected = {
        'modified': 'theirs version',
        'new': 'nytt',
    }

    config = MergeConfig()
    config.strategy = 'theirs'
    merged_po = run_merge_test(base, ours, theirs, config)

    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid and entry.msgstr}
    assert merged_entries == expected

    plural_entry = [e for e in merged_po if e.msgid == 'one file'][0]
    assert plural_entry.msgstr_plural[0] == 'en fil'
    assert plural_entry.msgstr_plural[1] == '%d dokument'


def test_strategy_none_raises_on_conflicts():
    base, ours, theirs = create_conflict_scenario()

    base_po = create_po_file(base)
    ours_po = create_po_file(ours)
    theirs_po = create_po_file(theirs)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    config = MergeConfig()
    config.strategy = 'none'

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path), config)
        assert result == 1, "Merge should fail with conflicts when strategy='none'"
    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_entry_deleted_in_ours_modified_in_theirs():
    base = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old', msgstr='gammal'),
    ]

    ours = [
        POEntry(msgid='hello', msgstr='hej'),
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old', msgstr='föråldrad'),
    ]

    expected = {
        'hello': 'hej',
        'old': 'föråldrad',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected


def test_entry_modified_in_ours_deleted_in_theirs():
    base = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old', msgstr='gammal'),
    ]

    ours = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old', msgstr='föråldrad'),
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
    ]

    expected = {
        'hello': 'hej',
        'old': 'föråldrad',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected


def test_entry_deleted_in_both_branches():
    base = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old', msgstr='gammal'),
    ]

    ours = [
        POEntry(msgid='hello', msgstr='hej'),
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
    ]

    expected = {
        'hello': 'hej',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected


def test_same_entry_added_with_same_translation():
    base = [
        POEntry(msgid='hello', msgstr='hej'),
    ]

    ours = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='new', msgstr='ny'),
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='new', msgstr='ny'),
    ]

    expected = {
        'hello': 'hej',
        'new': 'ny',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected


def test_msgctxt_context_handling():
    base = []

    ours = [
        POEntry(msgid='File', msgstr='Arkiv', msgctxt='menu'),
    ]

    theirs = [
        POEntry(msgid='File', msgstr='Arkivera', msgctxt='verb'),
    ]

    merged_po = run_merge_test(base, ours, theirs)

    file_entries = [e for e in merged_po if e.msgid == 'File']
    assert len(file_entries) == 2, f"Expected 2 'File' entries with different contexts, got {len(file_entries)}"

    contexts = {e.msgctxt for e in file_entries}
    assert contexts == {'menu', 'verb'}, f"Expected both contexts, got {contexts}"


def test_plural_forms():
    base = [
        POEntry(msgid='one file', msgid_plural='%d files', msgstr_plural={0: 'en fil', 1: '%d filer'}),
    ]

    ours = [
        POEntry(msgid='one file', msgid_plural='%d files', msgstr_plural={0: 'en fil', 1: '%d filer'}),
        POEntry(msgid='hello', msgstr='hej'),
    ]

    theirs = [
        POEntry(msgid='one file', msgid_plural='%d files', msgstr_plural={0: 'en fil', 1: '%d filer'}),
        POEntry(msgid='goodbye', msgstr='hejdå'),
    ]

    merged_po = run_merge_test(base, ours, theirs)

    msgids = {e.msgid for e in merged_po if e.msgid}
    assert msgids == {'one file', 'hello', 'goodbye'}

    plural_entry = [e for e in merged_po if e.msgid == 'one file'][0]
    assert plural_entry.msgid_plural == '%d files'
    assert plural_entry.msgstr_plural[0] == 'en fil'
    assert plural_entry.msgstr_plural[1] == '%d filer'


def test_multiline_msgid_msgstr():
    base = []

    ours = [
        POEntry(
            msgid='This is a long message that spans multiple lines in the source code',
            msgstr='Detta är ett långt meddelande som spänner över flera rader i källkoden',
        ),
    ]

    theirs = [
        POEntry(
            msgid='Another long message',
            msgstr='Ett annat långt meddelande',
        ),
    ]

    expected = {
        'This is a long message that spans multiple lines in the source code':
            'Detta är ett långt meddelande som spänner över flera rader i källkoden',
        'Another long message': 'Ett annat långt meddelande',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected


def test_metadata_handling():
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

    base = [POEntry(msgid='hello', msgstr='hej')]
    ours = [POEntry(msgid='hello', msgstr='hej')]
    theirs = [POEntry(msgid='hello', msgstr='hej')]

    base_po = create_po_file(base, base_meta)
    ours_po = create_po_file(ours, ours_meta)
    theirs_po = create_po_file(theirs, theirs_meta)

    base_path = save_po_to_temp(base_po)
    ours_path = save_po_to_temp(ours_po)
    theirs_path = save_po_to_temp(theirs_po)

    config = MergeConfig()

    try:
        result = merge_po_files(str(base_path), str(ours_path), str(theirs_path), config)
        assert result == 0

        merged_po = pofile(str(ours_path))

        assert merged_po.metadata['POT-Creation-Date'] == '2023-05-01 10:00+0000'

    finally:
        base_path.unlink()
        ours_path.unlink()
        theirs_path.unlink()


def test_entry_order_is_normalized():
    base = [
        POEntry(msgid='zebra', msgstr='zebra'),
        POEntry(msgid='apple', msgstr='äpple'),
    ]

    ours = [
        POEntry(msgid='apple', msgstr='äpple'),
        POEntry(msgid='zebra', msgstr='zebra'),
        POEntry(msgid='banana', msgstr='banan'),
    ]

    theirs = [
        POEntry(msgid='zebra', msgstr='zebra'),
        POEntry(msgid='cherry', msgstr='körsbär'),
        POEntry(msgid='apple', msgstr='äpple'),
    ]

    merged_po = run_merge_test(base, ours, theirs)

    msgids_in_order = [e.msgid for e in merged_po if e.msgid]

    expected_order = ['apple', 'banana', 'cherry', 'zebra']
    assert msgids_in_order == expected_order, f"Expected {expected_order}, got {msgids_in_order}"


def test_obsolete_entry_preserved():
    base = [
        POEntry(msgid='hello', msgstr='hej'),
    ]

    ours = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old_ours', msgstr='gammal ours', obsolete=True),
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='old_theirs', msgstr='gammal theirs', obsolete=True),
    ]

    merged_po = run_merge_test(base, ours, theirs)

    obsolete_entries = [e for e in merged_po if e.obsolete]
    obsolete_msgids = {e.msgid for e in obsolete_entries}

    assert 'old_ours' in obsolete_msgids
    assert 'old_theirs' in obsolete_msgids


def test_active_and_obsolete_same_msgid():
    base = []

    ours = [
        POEntry(msgid='current', msgstr='nuvarande', obsolete=False),
    ]

    theirs = [
        POEntry(msgid='current', msgstr='gammal översättning', obsolete=True),
    ]

    merged_po = run_merge_test(base, ours, theirs)

    current_entries = [e for e in merged_po if e.msgid == 'current']
    assert len(current_entries) == 2

    active = [e for e in current_entries if not e.obsolete]
    obsolete = [e for e in current_entries if e.obsolete]

    assert len(active) == 1
    assert len(obsolete) == 1
    assert active[0].msgstr == 'nuvarande'
    assert obsolete[0].msgstr == 'gammal översättning'


def test_fuzzy_flag_difference_detected():
    base = [POEntry(msgid='hello', msgstr='hej')]

    ours = [POEntry(msgid='hello', msgstr='hej')]

    theirs_entry = POEntry(msgid='hello', msgstr='hej')
    theirs_entry.flags.append('fuzzy')
    theirs = [theirs_entry]

    expected = {
        'hello': 'hej',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected

    hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
    assert hello_entry.fuzzy == True


def test_fuzzy_flag_removed():
    base_entry = POEntry(msgid='hello', msgstr='hej')
    base_entry.flags.append('fuzzy')
    base = [base_entry]

    ours = [POEntry(msgid='hello', msgstr='hej')]

    theirs_entry = POEntry(msgid='hello', msgstr='hej')
    theirs_entry.flags.append('fuzzy')
    theirs = [theirs_entry]

    expected = {
        'hello': 'hej',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected

    hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
    assert hello_entry.fuzzy == False


def test_conflict_prefers_non_fuzzy_when_both_add():
    base = [POEntry(msgid='hello', msgstr='hej')]

    ours_entry = POEntry(msgid='new', msgstr='ny')
    ours_entry.flags.append('fuzzy')
    ours = [
        POEntry(msgid='hello', msgstr='hej'),
        ours_entry,
    ]

    theirs = [
        POEntry(msgid='hello', msgstr='hej'),
        POEntry(msgid='new', msgstr='nytt'),
    ]

    expected = {
        'hello': 'hej',
        'new': 'nytt',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected

    new_entry = [e for e in merged_po if e.msgid == 'new'][0]
    assert new_entry.fuzzy == False


def test_conflict_prefers_non_fuzzy_when_both_modify():
    base = [POEntry(msgid='hello', msgstr='hej')]

    ours_entry = POEntry(msgid='hello', msgstr='hallå')
    ours_entry.flags.append('fuzzy')
    ours = [ours_entry]

    theirs = [POEntry(msgid='hello', msgstr='tjena')]

    expected = {
        'hello': 'tjena',
    }

    merged_po = run_merge_test(base, ours, theirs)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected

    hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
    assert hello_entry.fuzzy == False


def test_conflict_both_fuzzy_falls_back_to_strategy():
    base = [POEntry(msgid='hello', msgstr='hej')]

    ours_entry = POEntry(msgid='hello', msgstr='hallå')
    ours_entry.flags.append('fuzzy')
    ours = [ours_entry]

    theirs_entry = POEntry(msgid='hello', msgstr='tjena')
    theirs_entry.flags.append('fuzzy')
    theirs = [theirs_entry]

    expected = {
        'hello': 'hallå',
    }

    config = MergeConfig()
    config.strategy = 'ours'
    merged_po = run_merge_test(base, ours, theirs, config)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected

    hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
    assert hello_entry.fuzzy == True


def test_prefer_non_fuzzy_disabled():
    base = [POEntry(msgid='hello', msgstr='hej')]

    ours_entry = POEntry(msgid='hello', msgstr='hallå')
    ours_entry.flags.append('fuzzy')
    ours = [ours_entry]

    theirs = [POEntry(msgid='hello', msgstr='tjena')]

    expected = {
        'hello': 'hallå',
    }

    config = MergeConfig()
    config.strategy = 'ours'
    config.prefer_non_fuzzy = False
    merged_po = run_merge_test(base, ours, theirs, config)
    merged_entries = {entry.msgid: entry.msgstr for entry in merged_po if entry.msgid}
    assert merged_entries == expected

    hello_entry = [e for e in merged_po if e.msgid == 'hello'][0]
    assert hello_entry.fuzzy == True


def test_comprehensive_sorting():
    base = []

    ours = [
        POEntry(msgid='zebra', msgstr='sebra'),
        POEntry(msgid='banana', msgstr='banan', msgctxt='fruit'),
        POEntry(msgid='banana', msgstr='banankurva', msgctxt='plantain'),
        POEntry(msgid='obsolete_one', msgstr='föråldrad ett', obsolete=True),
    ]

    theirs = [
        POEntry(msgid='apple', msgstr='äpple'),
        POEntry(msgid='banana', msgstr='banan split', msgctxt='dessert'),
        POEntry(msgid='obsolete_three', msgstr='föråldrad tre', obsolete=True),
        POEntry(msgid='obsolete_two', msgstr='föråldrad två', obsolete=True),
    ]

    merged_po = run_merge_test(base, ours, theirs)

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
