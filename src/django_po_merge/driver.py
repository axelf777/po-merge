from sys import argv, exit
from .merger import merge_po_files


def main():
    if len(argv) != 4:
        print("Usage: django-po-merge-driver <base> <ours> <theirs>")
        exit(1)

    base_path = argv[1]
    ours_path = argv[2]
    theirs_path = argv[3]

    exit_code = merge_po_files(base_path, ours_path, theirs_path)
    exit(exit_code)


if __name__ == '__main__':
    main()
