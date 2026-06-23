## What this project does

A Python command-line tool that queries GitHub's GraphQL API to gather and summarise pull request statistics for one or more users within a GitHub organisation. It supports filtering by authored or reviewed pull requests, flexible date ranges (quarter, half-year, month, week, specific date), and can produce per-member tables for a whole team.

## Project layout

```
pull-request-statistics/
├── src/
│   ├── main.py                                  # CLI entry point; argument parsing, orchestration, output printing
│   ├── require_env.py                           # Reads required environment variables, raises clearly on missing values
│   └── github_client/
│       ├── client.py                            # Thin GraphQL HTTP client (authentication, error translation)
│       ├── errors/                              # GitHubClientError, MalformedResponseError
│       ├── pull_request_statistics/
│       │   ├── pull_request_statistics_service.py   # Core service: count/list authored and reviewed PRs
│       │   ├── models/                              # PullRequestSummary, MemberStatistics data classes
│       │   └── date_ranges/                         # DateRange, DateRangeFactory, Quarter/Half/Month enums
│       └── team_members/
│           ├── team_member.py                   # TeamMember data class
│           └── team_members_service.py          # Resolves GitHub team member logins from a team slug
├── tests/
│   ├── unit/                                    # Unit tests — mock the HTTP layer with requests-mock
│   └── integration/                             # Integration tests — call the real GitHub API
├── Makefile                                     # Developer commands (see below)
└── pyproject.toml                               # Project metadata, dependencies, ruff and pytest config
```

## Environment

- **Python**: 3.12+
- **Package manager**: [uv](https://github.com/astral-sh/uv)

## Common commands

| Task | Command |
|---|---|
| Install dependencies | `make install` |
| Run tests (includes lint) | `make test` |
| Run linter | `make lint` |
| Auto-fix lint issues | `make fix` |
| Format code | `make format` |
| Run with coverage report | `make coverage` |
| Clean build artefacts | `make clean` |

Run the tool:

```bash
uv run src/main.py --user <github-login> --organisation <org>
```

Use `--env-file=.env` with uv if the token is stored in a `.env` file rather than the environment.

## Code conventions

- British English spelling throughout (including identifiers and comments).
- No abbreviations — use full words (`reviewer` not `rev`, `organisation` not `org` in variable names).
- Comments are rare; they explain *why*, never *what*.

## Branching and commits

Follow conventional commit format:

```
<type>: <short description>
```

Common types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`.

Branch names: `<type>/<TICKET-or-NO-JIRA>-<short-description>` (e.g. `feat/NO-JIRA-add-csv-output`).

## Before opening a pull request

1. Ensure new behaviour is covered by unit tests.
2. Update `README.md` if CLI arguments or output format changed.
