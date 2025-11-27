# pull-request-statistics

A Python CLI tool for gathering and summarizing GitHub pull request statistics for users within an organization. This tool helps track authored and reviewed pull requests over customizable date ranges.

## Features

- **Authored PRs**: Count and list pull requests created by a specific author
- **Reviewed PRs**: Count and list pull requests reviewed by a specific user
- **Flexible Date Ranges**: Filter by year, quarter, half-year, month, or a specific date
- **Filtering Options**: Limit to merged-only PRs or exclude self-authored reviews
- **Pagination Support**: Configurable page sizes for efficient API usage

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

Create a `.env` file in the project root with your GitHub access token:

```env
GITHUB_ACCESS_TOKEN=your_github_token_here
```

The token must have permissions to run search queries against the target organization.

## Usage

Run the tool using uv with your environment file:

```bash
uv run --env-file=.env src/main.py --author <username> --organisation <org>
```

### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--author` | Yes | GitHub login of the author to analyze |
| `--organisation` | Yes | GitHub organization to search within |
| `--reviewer` | No | GitHub login of the reviewer (defaults to author) |
| `--merged-only` | No | Limit authored results to merged pull requests |
| `--exclude-self-reviews` | No | Exclude self-authored PRs when counting reviews |
| `--quarter` | No | Quarter to search (e.g., Q1, Q2, Q3, Q4) |
| `--half` | No | Half-year to search (e.g., H1, H2) |
| `--month` | No | Month name or number (e.g., March or 3) |
| `--year` | No | Year to search |
| `--date` | No | Specific date to search (YYYY-MM-DD) |
| `--page-size` | No | Page size for GitHub API pagination (default: 50) |
| `--counts-only` | No | Only fetch counts, skip fetching full PR lists |

### Examples

Get PR statistics for the current quarter:
```bash
uv run --env-file=.env src/main.py --author octocat --organisation github
```

Get merged PRs only for Q1 2024:
```bash
uv run --env-file=.env src/main.py --author octocat --organisation github --merged-only --quarter Q1 --year 2024
```

Get review counts for a specific month:
```bash
uv run --env-file=.env src/main.py --author octocat --organisation github --month March --year 2024
```

Get stats for a specific date:
```bash
uv run --env-file=.env src/main.py --author octocat --organisation github --date 2024-03-15
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
