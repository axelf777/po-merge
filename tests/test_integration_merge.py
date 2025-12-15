from pathlib import Path
from .git_helpers import GitTestRepo, setup_git_conflict_scenario


def test_strategy_none(tmp_path):
    repo = GitTestRepo(tmp_path)
    repo.set_config('merge.po-merge.strategy', 'none')

    setup_git_conflict_scenario(repo)

    success, stdout, stderr = repo.merge('branch-theirs')

    assert not success, "Merge should fail with conflicts"

    status = repo.get_file_status('locale/sv/LC_MESSAGES/django.po')
    assert status == 'UU', f"Expected 'UU' status, got '{status}'"

    content = repo.get_file_content('locale/sv/LC_MESSAGES/django.po')

    expected_path = Path(__file__).parent / 'fixtures' / 'expected' / 'strategy_none.po'
    expected_content = expected_path.read_text()

    assert content == expected_content, "Merged output should match expected output for strategy=none"


def test_strategy_ours(tmp_path):
    repo = GitTestRepo(tmp_path)
    repo.set_config('merge.po-merge.strategy', 'ours')

    setup_git_conflict_scenario(repo)

    success, stdout, stderr = repo.merge('branch-theirs')

    assert not success, "Merge should fail due to parse errors"

    content = repo.get_file_content('locale/sv/LC_MESSAGES/django.po')

    expected_path = Path(__file__).parent / 'fixtures' / 'expected' / 'strategy_ours.po'
    expected_content = expected_path.read_text()

    assert content == expected_content, "Merged output should match expected output for strategy=ours"


def test_strategy_theirs(tmp_path):
    repo = GitTestRepo(tmp_path)
    repo.set_config('merge.po-merge.strategy', 'theirs')

    setup_git_conflict_scenario(repo)

    success, stdout, stderr = repo.merge('branch-theirs')

    assert not success, "Merge should fail due to parse errors"

    content = repo.get_file_content('locale/sv/LC_MESSAGES/django.po')

    expected_path = Path(__file__).parent / 'fixtures' / 'expected' / 'strategy_theirs.po'
    expected_content = expected_path.read_text()

    assert content == expected_content, "Merged output should match expected output for strategy=theirs"


def test_strategy_ours_no_fuzzy_preference(tmp_path):
    repo = GitTestRepo(tmp_path)
    repo.set_config('merge.po-merge.strategy', 'ours')
    repo.set_config('merge.po-merge.prefer-non-fuzzy', 'false')

    setup_git_conflict_scenario(repo)

    success, stdout, stderr = repo.merge('branch-theirs')

    assert not success, "Merge should fail due to parse errors"

    content = repo.get_file_content('locale/sv/LC_MESSAGES/django.po')

    expected_path = Path(__file__).parent / 'fixtures' / 'expected' / 'strategy_ours_no_prefer_fuzzy.po'
    expected_content = expected_path.read_text()

    assert content == expected_content, "Merged output should match expected output for strategy=ours with prefer-non-fuzzy=false"


def test_skip_validation(tmp_path):
    repo = GitTestRepo(tmp_path)
    repo.set_config('merge.po-merge.strategy', 'ours')
    repo.set_config('merge.po-merge.validate-compiled', 'false')

    setup_git_conflict_scenario(repo)

    success, stdout, stderr = repo.merge('branch-theirs')

    assert not success, "Merge should fail due to parse errors"

    content = repo.get_file_content('locale/sv/LC_MESSAGES/django.po')

    expected_path = Path(__file__).parent / 'fixtures' / 'expected' / 'strategy_ours_skip_validation.po'
    expected_content = expected_path.read_text()

    assert content == expected_content, "Merged output should match expected output for strategy=ours with validate-compiled=false"
