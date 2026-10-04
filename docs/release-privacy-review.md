# Public Beta privacy review

Reviewed locally on 2026-10-04 before the final publication request.

The real-workflow test prompts, conversation packets, raw evaluator exchanges and
interactive review exports are kept under ignored `artifacts/dogfood-v1/`. They
are not release attachments. The local capture hook configuration is also excluded
from Git. No future-capture files were present at review time.

The audit checked all reachable Git history, including the public branch and tag
revisions, against the four local test packets (114 case records, with overlapping
cases/context). It inspected 1,261 historical text blobs. Complete user messages
of at least 40 characters and overlapping 80-character user-message excerpts had
no matches. JSON string values were decoded as well as checking ordinary text.
Assistant-context matches were approved README prose and an already-public
synthetic test example. No private dataset/capture paths had ever been tracked in
the inspected history.

Public research reports do contain case IDs, results and summarized descriptions
of reviewed work. These summaries are deliberately distinct from publishing the
raw prompts, conversations or review packets. Short generic phrases such as a
request to proceed are not useful identifiers for a privacy scan. This review is
not a claim that no wording from any conversation can appear in documentation.

Final archives and retained CI logs/artifacts are checked locally before approval;
no private corpus is uploaded to a scanning service. The ignored release manifest
and privacy audit record identify the exact packages and reviewed revisions.
Secret scanning supplements this content comparison; it cannot by itself prove
that private prompts are absent.

This review concerns GitHub/source-package publication. The separately authorized
Jev experiments sent inspected content through OpenRouter; keeping their local
records out of Git does not undo that earlier authorized data flow.
