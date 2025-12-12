from subprocess import run
from pathlib import Path
import os


class GitTestRepo:
    def __init__(self, tmp_path):
        self.repo_dir = tmp_path / "test-repo"
        self.repo_dir.mkdir()
        self._setup_repo()

    def _setup_repo(self):
        self._run_git(['init', '-b', 'main'])
        self._run_git(['config', 'user.email', 'test@example.com'])
        self._run_git(['config', 'user.name', 'Test User'])

        project_root = Path(__file__).parent.parent

        self._run_git([
            'config', 'merge.django-po-merge.driver',
            f'python -m django_po_merge.driver %O %A %B'
        ])

        src_path = project_root / 'src'
        if 'PYTHONPATH' in os.environ:
            os.environ['PYTHONPATH'] = f"{src_path}:{os.environ['PYTHONPATH']}"
        else:
            os.environ['PYTHONPATH'] = str(src_path)

        gitattributes = self.repo_dir / '.gitattributes'
        gitattributes.write_text('*.po merge=django-po-merge\n')

    def _run_git(self, args, check=True):
        result = run(
            ['git'] + args,
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            check=check
        )
        return result

    def commit_file(self, filename, content, message):
        file_path = self.repo_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

        self._run_git(['add', filename])
        self._run_git(['commit', '-m', message])

        sha_result = self._run_git(['rev-parse', 'HEAD'])
        return sha_result.stdout.strip()

    def create_branch(self, branch_name, from_branch=None):
        if from_branch:
            self._run_git(['checkout', '-b', branch_name, from_branch])
        else:
            self._run_git(['checkout', '-b', branch_name])

    def checkout(self, branch_name):
        self._run_git(['checkout', branch_name])

    def merge(self, branch_name):
        result = self._run_git(['merge', branch_name], check=False)
        success = result.returncode == 0
        return success, result.stdout, result.stderr

    def get_file_content(self, filename):
        file_path = self.repo_dir / filename
        return file_path.read_text()

    def get_file_status(self, filename):
        result = self._run_git(['status', '--porcelain', filename])
        status_line = result.stdout.strip()

        if not status_line:
            return None

        return status_line[:2].strip()

    def set_config(self, key, value):
        self._run_git(['config', key, value])

    def has_conflict_markers(self, content):
        return '<<<<<<<' in content and '=======' in content and '>>>>>>>' in content


def setup_git_conflict_scenario(repo: GitTestRepo):
    fixture_dir = Path(__file__).parent / 'fixtures'

    base_content = (fixture_dir / 'base.po').read_text()
    repo.commit_file('locale/sv/LC_MESSAGES/django.po', base_content, 'Initial commit')

    repo.create_branch('branch-ours')
    ours_content = (fixture_dir / 'ours.po').read_text()
    repo.commit_file('locale/sv/LC_MESSAGES/django.po', ours_content, 'Ours changes')

    repo.checkout('main')
    repo.create_branch('branch-theirs')
    theirs_content = (fixture_dir / 'theirs.po').read_text()
    repo.commit_file('locale/sv/LC_MESSAGES/django.po', theirs_content, 'Theirs changes')

    repo.checkout('branch-ours')
