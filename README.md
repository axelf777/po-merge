# po-merge

Git merge driver for `.po` files.

If you've worked with gettext translations in a team, you know the pain - `.po` files conflict constantly, and resolving them manually is tedious because git treats them as plain text instead of the structured format they are.

po-merge solves this by merging `.po` files entry-by-entry. Most conflicts resolve automatically. When they can't, you get clear conflict markers showing exactly which translations need attention.

## Quick start

```bash
pip install po-merge
cd your-repo
po-merge install
```

That's it. Git will now use po-merge for all `.po` files in this repo.

## How it works

Instead of line-by-line diffs, po-merge compares entries by their `msgid`. If both branches changed the same translation differently, that's a real conflict. If only one side changed it, take that change. If both made the same change, no conflict.

When there's a real conflict that can't be auto-resolved, po-merge appends conflict markers to the file and fails the merge, so you can fix it manually.

## Options

```bash
# Auto-resolve conflicts by keeping our version
po-merge install --strategy=ours

# Auto-resolve conflicts by taking their version
po-merge install --strategy=theirs

# Don't prefer non-fuzzy over fuzzy translations
po-merge install --no-fuzzy-preference

# Skip msgfmt validation
po-merge install --skip-validation
```

To remove:

```bash
po-merge uninstall
```

## GitHub bot

There's also a GitHub Actions workflow that can automatically rebase PRs with `.po` conflicts. See `.github/workflows/po-merge-bot.yml` if you want that.

## License

MIT
