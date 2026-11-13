# Art iteration: preserve original evidence, scope the next capture

These commands maintain tooling only. They do not execute a game, manufacture a
passed quality result, or authorize an upload. The first complete analysis runs
once; later analyses keep the original failed rows open and rerun their owners
plus changed-rule dependents. A valid old screenshot may contain a quality defect.
Capture authenticity and quality acceptance are separate facts.

## Decide before performing work

`art_change_plan.py` is read-only. It reads actual capture status and existing
reports; it does not run pixels, build, start a round, capture, or write a ledger.
Pass every relevant parent/subreport to get the complete batch of blockers.

```sh
python3 -B <skills>/remake-core/scripts/art_change_plan.py \
  --project PROJECT --build WEB \
  --report PREVIOUS_FULL_REPORT --report PREVIOUS_PAGE_REPORT \
  --changed-rule audit_page_richness.py
```

With identical source/export/matrix/collector hashes, `build.required=false` and
`capture.required=false`. Tool/report-only changes use the original files and
round. Without before/after rule hashes, analysis currency is unknown, not passed.
If source changed but export did not, finish the repair batch and build once. If
both changed, verify their actual binding; do not reflexively build again.

## Same-version evidence

`art_round_check.run('verify', project, build, dumps)` validates every original
proof, snapshot, dump, PNG pair, case, viewport and environment. A proof from an
older round with the exact same version remains usable without a full-art pass or
a second identical PNG. The producer file and its full collector hash are unchanged.
No equality is inferred for a changed collector; unknown producer transitions fail.

The result is capture integrity only: `quality_promoted=false`. It does not make a
previous failed page pass. Existing quality results remain bound to their original
report bytes and must be resolved by the owning analysis.

## Forward-only local dependency contract

A contract must exist before the original browser arrival. Do not retrofit it to
legacy screenshots. `init` binds exact source/export snapshots, archives owned raw
bytes, and records static method projections. The game JavaScript is parsed with
the vendored Acorn; it is never executed by the dependency tools.

A minimal schema example (replace every synthetic path/owner with reviewed real
consumers):

```json
{
  "schema": "art-case-dependencies.v1",
  "cases": ["home-phone", "gift-phone"],
  "case_inputs": {
    "home-phone": {
      "mode": "origin_bound",
      "external_inputs": [],
      "basis": "Reviewed state represented by the original captured input and UI"
    },
    "gift-phone": {
      "mode": "fresh",
      "external_inputs": ["time-dependent availability"],
      "basis": "Its external availability is not proven unchanged"
    }
  },
  "files": [
    {
      "unit": "ui",
      "domain": "source",
      "path": "assets/scripts/UI.js",
      "kind": "methods",
      "methods": [
        {"name":"openHome","cases":["home-phone"],"basis":"Exact Home constructor"},
        {"name":"openGift","cases":["gift-phone"],"basis":"Exact Gift constructor"}
      ]
    },
    {
      "unit": "ui",
      "domain": "export",
      "path": "src/UI.js",
      "kind": "methods",
      "methods": [
        {"name":"openHome","cases":["home-phone"],"basis":"Same exported owner"},
        {"name":"openGift","cases":["gift-phone"],"basis":"Same exported owner"}
      ]
    }
  ]
}
```

Each unit needs exactly one source and export owner with identical case ownership.
An `asset` entry instead has `kind:"asset"`, `cases`, and `basis`; source/export
asset bytes must correspond exactly. Named methods must resolve uniquely. Method
references expand their transitive consumer cases; undeclared consumers and bytes
outside the owned methods are shared. Every unlisted file is shared. Shared edits
expand once to the whole declared consumer set; this is an explicit dependency
result, not a default rule that every JavaScript edit invalidates all evidence.

Dynamic method closure, ambiguous selectors, source/export deltas that do not
correspond, unsupported compilation, and changed producers cannot authorize
inheritance. `fresh` cases and cases with external inputs stay fresh. The tool
cannot prove a developer's consumer declaration is correct; the declaration needs
an explicit reviewed basis before capture. An unknown consumer must not be
labelled local to save work.

After the real export is ready and its actual round has been initialized, but
before the initial browser arrival:

```sh
python3 -B <skills>/remake-core/scripts/art_capture_history.py init \
  --project PROJECT --build WEB --contract CASE_DEPENDENCIES_JSON \
  --out BASELINE_A_JSON
```

Run the existing official collector and one complete analysis. No quality-pass
prerequisite exists for retaining those authentic captures.

## One merged repair batch

After the source repair batch and one verified export, initialize the real new
round through the existing producer, then plan without capturing:

```sh
python3 -B <skills>/remake-core/scripts/art_capture_history.py plan-transition \
  --project PROJECT --build WEB --baseline BASELINE_A_JSON --base-dumps CAPTURES_A
```

The JSON gives the full source/export diff, affected case set, necessary viewport
anchors, reuse set, and a `manifest` template. Feed only `fresh_cases` to the
existing collector. The source/matrix/collector identity is still global and
verified; the new transition proves exactly why each old case remains applicable.
If closure is unknown, the plan explicitly reports it and permits no inheritance;
use the stated expanded plain-current capture scope once.

The outer production planner can consume the same real contract directly:

```sh
python3 -B <skills>/remake-core/scripts/art_change_plan.py \
  --project PROJECT --build WEB --baseline BASELINE_A_JSON --base-dumps CAPTURES_A \
  --report PREVIOUS_FULL_REPORT
```

It calls the owning history planner on the actual round; an `--impact` declaration
alone never authorizes reuse. Before new capture it reports candidate reuse and
`verified_current_ready=false`. After capture add `--dumps CAPTURES_B`: only real
proof verification can change that to true and `capture.required=false`. Altered
old PNGs, missing anchors and invalid baselines remain blocked.

After the collector creates its fresh output directory, place the exact template
in `CAPTURES_B/capture-inheritance.json`. Do not precreate the collector's fresh
output directory. Optional `quality_refs` entries are absolute original report
paths with exact `sha256`; failed quality stays failed. No dump/PNG is copied,
renamed, patched, wrapped, or assigned a replacement proof.

```sh
python3 -B <skills>/remake-core/scripts/art_capture_history.py verify \
  --project PROJECT --build WEB --dumps CAPTURES_B
```

The result exposes `resolved_dumps`: the exact original files selected from new
and historical directories. Inventory and subcheckers consume that list through
`resolve_input_files`; they must never recursively import an entire old directory.
Required current captures must be fresh in the current round, one anchor per
viewport is mandatory, and mixed environments, unexpected competing files,
modified originals, symlinks, or changed quality reports are rejected.

## Keep subsequent repairs local too

After verifying B, checkpoint its exact origin chain before the next source edit:

```sh
python3 -B <skills>/remake-core/scripts/art_capture_history.py init \
  --project PROJECT --build WEB --contract CASE_DEPENDENCIES_JSON \
  --inherit-evidence CAPTURES_B --out BASELINE_B_JSON
```

Plan C against B, not against the oldest A. The checkpoint preserves each raw
origin (possibly from A), original report references, and archived bytes bound to
B's actual snapshot. Verification replays the chain from the pre-capture contract.
Thus a Gift repair in B is not recaptured again when C changes only Settings.
Changing the ownership declaration mid-chain is rejected; establish a new forward
baseline for an actually expanded contract.

The complete original producer remains unchanged, so no collector hash is faked or
silently mapped. The explicit chain records the same real collector fingerprint.
A future producer change needs a separately reviewed equivalence/migration; this
implementation deliberately does not guess one.
