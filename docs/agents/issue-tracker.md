# Issue tracker: GitHub

Issues and specs for RecipeTap live in GitHub Issues. Use `gh` from this repository.

Before the first issue write in a session, check `gh repo view --json nameWithOwner`
and confirm the target is `neusse/RecipeTap`. Never file into `mattpocock/skills`.

- Create: write multiline bodies to a UTF-8 file, then use
  `gh issue create --title "..." --body-file <path>`.
- Read: `gh issue view <number> --json number,title,body,labels,comments`.
- List: `gh issue list --state open --json number,title,labels`.
- Label: `gh issue edit <number> --add-label <label>` or `--remove-label <label>`.
- Comment and close: `gh issue comment <number> --body-file <path>`, then
  `gh issue close <number>`.
- Use GitHub sub-issues and native issue dependencies where available.
  If unavailable, record `Part of #<parent>` or `Blocked by: #<blocker>`
  in the issue body.

## Pull requests as a triage surface

**PRs as a request surface: no.**

When a skill says "publish to the issue tracker," create a GitHub issue.
When it says "fetch the relevant ticket," read that issue.
