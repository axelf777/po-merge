from argparse import ArgumentParser
from subprocess import run, CalledProcessError
from sys import exit
from pathlib import Path


def get_git_root():
    """Get the root directory of the current git repository."""
    try:
        result = run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())
    except CalledProcessError:
        print("Error: Not in a git repository")
        exit(1)


def install_merge_driver():
    """Configure git to use django-po-merge as a merge driver for .po files."""
    git_root = get_git_root()

    try:
        run(
            ['git', 'config', 'merge.django-po-merge.name', 'Django PO file merge driver'],
            check=True
        )

        run(
            ['git', 'config', 'merge.django-po-merge.driver', 'django-po-merge-driver %O %A %B'],
            check=True
        )

        print("Configured git merge driver")
    except CalledProcessError as e:
        print(f"Error configuring git: {e}")
        exit(1)

    gitattributes_path = git_root / '.gitattributes'
    pattern = '*.po merge=django-po-merge\n'

    if gitattributes_path.exists():
        content = gitattributes_path.read_text()
        if pattern.strip() in content:
            print(".gitattributes already configured")
        else:
            with gitattributes_path.open('a') as f:
                f.write(f'\n{pattern}')
            print("Updated .gitattributes")
    else:
        gitattributes_path.write_text(pattern)
        print("Created .gitattributes")

    print("\nSuccessfully installed django-po-merge")


def uninstall_merge_driver():
    """Remove django-po-merge configuration from git."""
    git_root = get_git_root()

    try:
        run(
            ['git', 'config', '--unset', 'merge.django-po-merge.name'],
            check=True
        )
        run(
            ['git', 'config', '--unset', 'merge.django-po-merge.driver'],
            check=True
        )
        print("Removed git merge driver configuration")
    except CalledProcessError:
        print("Git merge driver configuration not found")

    gitattributes_path = git_root / '.gitattributes'
    pattern = '*.po merge=django-po-merge'

    if gitattributes_path.exists():
        content = gitattributes_path.read_text()
        lines = [line for line in content.split('\n') if pattern not in line]
        new_content = '\n'.join(lines).strip()

        if new_content:
            gitattributes_path.write_text(new_content + '\n')
            print("Updated .gitattributes")
        else:
            gitattributes_path.unlink()
            print("Removed .gitattributes")

    print("\nSuccessfully uninstalled django-po-merge")


def main():
    parser = ArgumentParser(
        description='Django PO file merge driver',
        prog='django-po-merge'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    subparsers.add_parser('install', help='Configure git to use django-po-merge for .po files')
    subparsers.add_parser('uninstall', help='Remove django-po-merge configuration from git')

    args = parser.parse_args()

    if args.command == 'install':
        install_merge_driver()
    elif args.command == 'uninstall':
        uninstall_merge_driver()
    else:
        parser.print_help()
        exit(1)


if __name__ == '__main__':
    main()
