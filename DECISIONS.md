# Architecture Decision Records

---

## ADR-001 — Process pre-filtered papers in batches of 50

**Status:** Accepted

### Context

After keyword pre-filtering, up to `PREFILTER_KEEP_TOP` items (default 200) are
queued for LLM relevance scoring. Each item carries a title, source, link,
publication date, and a truncated RSS summary (up to 500 characters). At 200
items that payload can exceed tens of thousands of tokens in a single prompt.

Two well-documented failure modes arise when large lists are stuffed into one
long-context call:

1. **Lost-in-the-middle.** LLMs attend more reliably to items near the beginning
   and end of a long input. Papers in the middle of a 200-item list receive
   systematically less attention, producing scores that reflect prompt position as
   much as genuine relevance.

2. **Attention-budget dilution.** With a fixed context window the model must
   distribute representational capacity across all items simultaneously. Smaller
   batches keep each item's share of attention higher, producing more
   discriminative scoring.

A third practical concern is **cost control**: a single failed or rate-limited
call would discard all scoring work, while batching limits the blast radius of
any one failure.

### Decision

Split the pre-filtered item list into batches of 50 (`BATCH_SIZE=50`) and call
the LLM once per batch. Results from all batches are merged by keeping the
highest score seen for each item ID. `notes` fields from each batch response are
concatenated and deduplicated. The final ranked list is sorted globally by score
before rendering.

The batch size of 50 is set via environment variable so it can be tuned per
deployment without code changes.

### Alternatives considered

| Option | Why rejected |
|---|---|
| **Single call (all 200 items)** | Worst-case attention dilution and lost-in-the-middle; a timeout or rate-limit error discards all work for the run |
| **Smaller batches (10–20 items)** | Multiplies API calls and total latency with diminishing quality returns; increases chattiness against rate limits |
| **Larger batches (100+ items)** | Pushes back toward single-call failure modes; more expensive per retry on transient errors |
| **Parallel batch calls** | Would reduce wall-clock time but increases burst token usage and risk of rate-limit errors; sequential batching is simpler and sufficient for a weekly job |

### Consequences

- **Positive:** Each batch fits comfortably within the model's effective attention
  range; scoring quality is more uniform across items; a single failed batch does
  not abort the entire run (the retry loop in `call_openai_triage` handles
  transient errors per batch).
- **Positive:** `BATCH_SIZE` is an env-var knob, so it can be lowered for
  cheaper models or raised if a future model demonstrates reliable long-context
  scoring.
- **Negative:** An item that appears in two batches (not possible today given
  deduplication before batching, but relevant if that changes) would receive two
  independent scores; the merge logic keeps only the maximum, which may not be
  the most reliable estimate.
- **Negative:** `notes` from different batches are concatenated naively; the
  model may produce overlapping observations across batches that are only
  partially deduplicated by `dict.fromkeys`.
