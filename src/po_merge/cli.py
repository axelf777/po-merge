from argparse import ArgumentParser
from subprocess import run, CalledProcessError
from sys import exit
from pathlib import Path


def get_git_root():
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


def install_merge_driver(strategy='none', prefer_non_fuzzy=True, validate_compiled=True):
    git_root = get_git_root()

    try:
        run(
            ['git', 'config', 'merge.po-merge.name', 'PO file merge driver'],
            check=True
        )

        run(
            ['git', 'config', 'merge.po-merge.driver', 'po-merge-driver %O %A %B'],
            check=True
        )

        run(
            ['git', 'config', 'merge.po-merge.strategy', strategy],
            check=True
        )

        run(
            ['git', 'config', 'merge.po-merge.prefer-non-fuzzy', str(prefer_non_fuzzy).lower()],
            check=True
        )

        run(
            ['git', 'config', 'merge.po-merge.validate-compiled', str(validate_compiled).lower()],
            check=True
        )

        print("Configured git merge driver")
        print(f"  Strategy: {strategy}")
        print(f"  Prefer non-fuzzy: {prefer_non_fuzzy}")
        print(f"  Validate compiled: {validate_compiled}")
    except CalledProcessError as e:
        print(f"Error configuring git: {e}")
        exit(1)

    gitattributes_path = git_root / '.gitattributes'
    pattern = '*.po merge=po-merge\n'

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

    print("\nSuccessfully installed po-merge")


def uninstall_merge_driver():
    git_root = get_git_root()

    try:
        run(
            ['git', 'config', '--unset', 'merge.po-merge.name'],
            check=True
        )
        run(
            ['git', 'config', '--unset', 'merge.po-merge.driver'],
            check=True
        )
        print("Removed git merge driver configuration")
    except CalledProcessError:
        print("Git merge driver configuration not found")

    gitattributes_path = git_root / '.gitattributes'
    pattern = '*.po merge=po-merge'

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

    print("\nSuccessfully uninstalled po-merge")


def main():
    parser = ArgumentParser(
        description='PO file merge driver',
        prog='po-merge'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    install_parser = subparsers.add_parser('install', help='Configure git to use po-merge for .po files')
    install_parser.add_argument(
        '--strategy',
        choices=['ours', 'theirs', 'none'],
        default='none',
        help='Conflict resolution strategy: ours (prefer our changes), theirs (prefer their changes), none (fail on conflicts, default)'
    )
    install_parser.add_argument(
        '--no-fuzzy-preference',
        action='store_true',
        help='Disable automatic preference for non-fuzzy translations over fuzzy ones'
    )
    install_parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip msgfmt validation of merged PO file'
    )

    subparsers.add_parser('uninstall', help='Remove po-merge configuration from git')

    args = parser.parse_args()

    if args.command == 'install':
        prefer_non_fuzzy = not args.no_fuzzy_preference
        validate_compiled = not args.skip_validation
        install_merge_driver(strategy=args.strategy, prefer_non_fuzzy=prefer_non_fuzzy, validate_compiled=validate_compiled)
    elif args.command == 'uninstall':
        uninstall_merge_driver()
    else:
        parser.print_help()
        exit(1)


if __name__ == '__main__':
    main()
