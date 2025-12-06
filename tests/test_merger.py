from shutil import copy
from tempfile import NamedTemporaryFile
from pathlib import Path
from polib import pofile
from django_po_merge import merge_po_files


def test_basic_merge():
    fixtures_dir = Path(__file__).parent / "fixtures"
    base = fixtures_dir / "base.po"
    ours = fixtures_dir / "ours.po"
    theirs = fixtures_dir / "theirs.po"
    expected = fixtures_dir / "expected.po"

    with NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
        temp_ours = Path(tmp.name)
        copy(ours, temp_ours)

    try:
        base_po = pofile(str(base))
        ours_po = pofile(str(ours))
        theirs_po = pofile(str(theirs))

        base_entries = {entry.msgid: entry.msgstr for entry in base_po if entry.msgid}
        ours_entries = {entry.msgid: entry.msgstr for entry in ours_po if entry.msgid}
        theirs_entries = {entry.msgid: entry.msgstr for entry in theirs_po if entry.msgid}

        print("\nINPUTS")
        print(f"BASE:   {base_entries}")
        print(f"OURS:   {ours_entries}")
        print(f"THEIRS: {theirs_entries}")

        result = merge_po_files(str(base), str(temp_ours), str(theirs))

        assert result == 0

        merged_po = pofile(str(temp_ours))
        expected_po = pofile(str(expected))

        merged_entries = {e.msgid: e.msgstr for e in merged_po if e.msgid}
        expected_entries = {e.msgid: e.msgstr for e in expected_po if e.msgid}

        print("\nOUTPUT")
        print(f"MERGED:   {merged_entries}")
        print(f"EXPECTED: {expected_entries}")

        assert merged_entries == expected_entries

    finally:
        temp_ours.unlink()

