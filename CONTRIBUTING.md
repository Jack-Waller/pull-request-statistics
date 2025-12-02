# Contributing

Thank you for considering a contribution. Please keep changes small, readable, and easy to maintain.

## Before you start
- Prefer British English spelling and clear, complete words (avoid abbreviations).
- Please raise an issue or start a discussion before large or breaking changes.

## Getting set up
- Install Python 3.12 or higher and [uv](https://github.com/astral-sh/uv).
- Clone the repository and install dependencies:
  ```bash
  make install
  ```
  You can run `uv sync` directly if you prefer.
- Set `GITHUB_ACCESS_TOKEN` in your environment or `.env` file so commands that call GitHub can run locally.

## Branching and commits
- Branch from `main` using conventional names: `<topic>/<ticket>-<short-description>`. If you do not have a ticket, use `NO-JIRA` in its place.
- Keep commits focused and use conventional commit messages (for example, `feat: add filter option` or `chore: update docs`).
- Do not rewrite history on shared branches.

## Making changes
- Favour simple, readable code and straightforward control flow.
- Update documentation and examples when behaviour changes.
- Add tests alongside new or modified functionality.

## Code style and quality
- Follow existing patterns in `src/` and `tests/`.
- Run formatting and linting:
  ```bash
  make format
  make lint
  ```
- Run the test suite before opening a pull request:
  ```bash
  make test
  ```
  Use `make coverage` if you need a coverage report.

## Pull requests
- Ensure your branch is up to date with `main` before raising a pull request.
- Fill in `.github/pull_request_template.md`, covering What, Why, Changes, Testing, and References.
- Include any relevant tickets, documentation links, and discussion threads.
- Confirm:
  - Tests pass locally.
  - New or changed behaviour is documented.
  - Secrets are not committed.
- Request a review once the above is complete; keep drafts up to date if work is in progress.
