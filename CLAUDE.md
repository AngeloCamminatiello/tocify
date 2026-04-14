# CLAUDE.md

## What this project does
Tocify is a weekly RSS digest pipeline for an academic researcher. It fetches
journal table-of-contents feeds, pre-filters items by keyword, sends batches to
an OpenAI model for relevance scoring, and commits a ranked Markdown digest
(`digest.md`) back to the repository via a scheduled GitHub Actions workflow.

## Tech stack
- **Python 3.11** (pinned in the workflow)
- **feedparser** – RSS/Atom parsing
- **openai** – structured JSON responses from the LLM
- **httpx** – custom HTTP client passed to the OpenAI client
- **python-dateutil** – robust date parsing for feed entries
- **pytest** – tests live in `tests/`

## Project structure
| File | Role |
|---|---|
| `digest.py` | End-to-end pipeline: fetch → prefilter → triage → render |
| `feeds.txt` | One feed URL per line; optional `Name \| URL` format; `#` comments |
| `interests.md` | User interest profile parsed by `parse_interests_md()` (see Gotchas) |
| `prompt.txt` | LLM prompt template with `{{KEYWORDS}}`, `{{NARRATIVE}}`, `{{ITEMS}}` placeholders |
| `digest.md` | Output — auto-committed by the bot each Monday |
| `requirements.txt` | Runtime dependencies (no dev deps; install pytest separately) |
| `.github/workflows/weekly-digest.yml` | Scheduled workflow (Mondays 08:00 PT) |

## Configuration & secrets
- Runtime knobs (`MODEL`, `LOOKBACK_DAYS`, `MIN_SCORE_READ`, etc.) are read from
  environment variables with sensible defaults in `digest.py` lines 11-20.
- The workflow overrides several of these in the `env:` block of the "Run digest"
  step — that is the canonical production configuration.
- `OPENAI_API_KEY` must be set as a GitHub Actions secret; the client validates
  that it starts with `sk-`.
- No `.env` file is used; there is no local secret management convention.

## Gotchas
- **`interests.md` format is load-bearing.** `parse_interests_md()` extracts two
  Markdown sections by heading name — `## keywords` (bullet list) and
  `## narrative` (free text). If either heading is renamed or the bullet format
  changes, parsing silently returns empty strings/lists and the LLM receives no
  interest signal.
- **Keyword prefilter has a fallback.** `keyword_prefilter()` returns
  `items[:keep_top]` unfiltered when fewer than `min(50, keep_top)` items match
  any keyword — so sparse keyword lists do not accidentally discard everything.
- **`prompt.txt` must exist at runtime.** `load_prompt_template()` raises
  `RuntimeError` if the file is missing; there is no embedded fallback.
- **The workflow clears proxy env vars** (`HTTP_PROXY`, `HTTPS_PROXY`, etc.)
  before calling the OpenAI API to avoid runner-level proxy interference.
