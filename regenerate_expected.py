#!/usr/bin/env python3
"""Regenerate expected output files for integration tests."""
from pathlib import Path
import tempfile
import shutil
from tests.git_helpers import GitTestRepo, setup_git_conflict_scenario


def regenerate_expected(strategy, prefer_non_fuzzy=True, validate_compiled=True):
    """Generate expected output for a given strategy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        repo = GitTestRepo(tmp_path)

        repo.set_config('merge.po-merge.strategy', strategy)

        if not prefer_non_fuzzy:
            repo.set_config('merge.po-merge.prefer-non-fuzzy', 'false')

        if not validate_compiled:
            repo.set_config('merge.po-merge.validate-compiled', 'false')

        setup_git_conflict_scenario(repo)

        success, stdout, stderr = repo.merge('branch-theirs')

        content = repo.get_file_content('locale/sv/LC_MESSAGES/django.po')

        if not prefer_non_fuzzy:
            filename = f'strategy_{strategy}_no_prefer_fuzzy.po'
        elif not validate_compiled:
            filename = f'strategy_{strategy}_skip_validation.po'
        else:
            filename = f'strategy_{strategy}.po'

        expected_path = Path('tests/fixtures/expected') / filename
        expected_path.write_text(content)

        print(f"Generated {filename}")
        print(f"  Merge {'succeeded' if success else 'failed'}")


if __name__ == '__main__':
    regenerate_expected('none')
    regenerate_expected('ours')
    regenerate_expected('theirs')
    regenerate_expected('ours', prefer_non_fuzzy=False)
    regenerate_expected('ours', validate_compiled=False)

    print("\nAll expected files regenerated!")
