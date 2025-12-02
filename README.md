# pull-request-statistics

A Python CLI tool for gathering and summarizing GitHub pull request statistics for users within an organization. This tool helps track authored and reviewed pull requests over customizable date ranges.

## Features

- **Authored PRs**: Count and list pull requests created by a specific author
- **Reviewed PRs**: Count and list pull requests reviewed by a specific user
- **Flexible Date Ranges**: Filter by year, quarter, half-year, month, week, or a specific date
- **Filtering Options**: Limit to merged-only PRs or exclude self-authored reviews
- **Pagination Support**: Configurable page sizes for efficient API usage
- **Team Members**: List members of a GitHub team within an organisation and gather per-member pull request counts

## Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- GitHub Personal Access Token with read permissions for the target organization

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Jack-Waller/pull-request-statistics.git
   cd pull-request-statistics
   ```

2. Install dependencies:
   ```bash
   make install
   ```
   Or using uv directly:
   ```bash
   uv sync
   ```

## Configuration

Set the `GITHUB_ACCESS_TOKEN` environment variable with your GitHub Personal Access Token:

```bash
export GITHUB_ACCESS_TOKEN=your_github_token_here
```

The token must have permissions to run search queries against the target organization.

<details>
<summary>Using a .env file instead</summary>

If you prefer to store your token in a file, create a `.env` file in the project root:

```env
GITHUB_ACCESS_TOKEN=your_github_token_here
```

Then use the `--env-file` flag when running uv:

```bash
uv run --env-file=.env src/main.py --author <username> --organisation <org>
```

</details>

## Usage

Run the tool using uv:

```bash
uv run src/main.py --user <username> --organisation <org>
```

### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--user` | Yes (unless `--team` is used) | GitHub login to analyse for authored and reviewed PRs. Repeat to include multiple users |
| `--organisation` | Yes | GitHub organization to search within |
| `--merged-only` | No | Limit authored results to merged pull requests |
| `--exclude-self-reviews` | No | Exclude self-authored PRs when counting reviews |
| `--quarter` | No | Quarter to search (e.g., Q1, Q2, Q3, Q4) |
| `--half` | No | Half-year to search (e.g., H1, H2) |
| `--month` | No | Month name or number (e.g., March or 3) |
| `--week` | No | Use the most recent seven days ending today |
| `--year` | No | Year to search |
| `--date` | No | Specific date to search (YYYY-MM-DD) |
| `--page-size` | No | Page size for GitHub API pagination (default: 50) |
| `--counts-only` | No | Only fetch counts, skip fetching full PR lists |
| `--team` | No | Team slug within the organisation to summarise. Enables counts-only output and cannot be combined with `--author` or `--reviewer` |

If no quarter, half, month, week, year, or date is provided, the tool defaults to the current quarter.

### Examples

Get PR statistics for the current quarter:
```bash
uv run src/main.py --user octocat --organisation github
```

Get merged PRs only for Q1 2024:
```bash
uv run src/main.py --user octocat --organisation github --merged-only --quarter Q1 --year 2024
```

Get review counts for a specific month:
```bash
uv run src/main.py --user octocat --organisation github --month March --year 2024
```

Get stats for a specific date:
```bash
uv run src/main.py --user octocat --organisation github --date 2024-03-15
```

List team members for a slug within an organisation:
```bash
uv run src/main.py --team mighty-llamas --organisation github
```

Get per-member counts (authored and reviewed) for a team over the most recent week:
```bash
uv run src/main.py --team mighty-llamas --organisation github --week
```

When using `--team`, the output includes per-member authored totals, reviewed totals, the percentage of the team's authored PRs each member created, and—when `--exclude-self-reviews` is set—the percentage of other team members' PRs each person reviewed.

Summarise multiple explicit users (counts-only is enabled automatically):
```bash
uv run src/main.py --user octocat --user hubot --organisation github --week
```

## Development

### Setup

```bash
make install
```

### Linting

Run linting checks using ruff:
```bash
make lint
```

Auto-fix linting issues:
```bash
make fix
```

Format code:
```bash
make format
```

### Testing

Run tests with linting:
```bash
make test
```

Run tests with coverage report:
```bash
make coverage
```

### Clean

Remove build artifacts and caches:
```bash
make clean
```

## Project Structure

```
pull-request-statistics/
├── src/
│   ├── main.py                      # CLI entry point
│   ├── require_env.py               # Environment variable helper
│   ├── github_client/               # GitHub GraphQL API client
│   │   ├── client.py
│   │   └── errors.py
│   └── pull_request_statistics/     # Core business logic
│       ├── date_ranges/             # Date range utilities
│       ├── pull_request_service.py  # PR query service
│       └── pull_request_summary.py  # PR data model
├── tests/
│   ├── unit/                        # Unit tests
│   └── integration/                 # Integration tests
├── Makefile                         # Build and development commands
├── pyproject.toml                   # Project configuration
└── README.md
```

## License

See the repository for license information.
