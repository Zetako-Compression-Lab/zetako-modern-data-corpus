# ZMDC — Zetako Modern Data Corpus

**A deterministic synthetic corpus for benchmarking compression on contemporary structured and machine-generated data.**

ZMDC generates a coherent, synthetic organization and its operational data: API traffic, device telemetry, observability, logs, CDC, transactions, collaboration, typed binary samples and opaque high-entropy controls. It generates meaning first and serializes second. Its users, organizations, services, instances and request references are shared across workloads.

ZMDC is synthetic. It aims for plausible statistical mechanisms, not a claim that it represents every category of data generated in 2026, nor a calibrated model of a particular company. No personal data, real messages or copied external prose is used.

## Benchmark Independence

ZMDC was not designed using feedback from a particular compression algorithm. Parameters must not depend on compression results. No compression engine is executed during development or generation, and this project contains no compression or random-access benchmark. Freeze the specification and generator before starting any such comparison. Published versions must be preserved; material distribution/schema changes require a new version.

## Reference corpus and distribution

The reference corpus contains 13 primary files (1,000,037,807 bytes), plus README and manifest. Its complete [file manifest](manifests/ZMDC-1G-v1.json) is included here. Bulk data will be hosted separately; a download URL will be added when that server is available. For now, generate it locally using the commands below.

The corpus was frozen before external compression comparisons. Those later experiments did not change the generator, configuration or reference data. This repository publishes the corpus project independently of codec rankings.

Reproduction: the reference was generated with CPython 3.12.10, seed 20260914, before a Git repository existed. Generation from this checkout records a non-null `git_commit` in its manifest, so the manifest's own bytes may differ; compare per-file hashes, `global_sha256`, implementation/specification fingerprints and configuration. The original reference manifest remains unchanged.

## Quick start

Python 3.11 or later, standard library only at runtime. The current reference runtime is CPython 3.12.10. From the standalone project directory:

```sh
python3 -m zmdc generate --version 1.0 --seed 20260914 --size 10MB --output outputs/dev-10MB
python3 -m zmdc validate outputs/dev-10MB
python3 -m zmdc stats outputs/dev-10MB
python3 -m zmdc inspect outputs/dev-10MB --limit 1
python3 -m zmdc manifest outputs/dev-10MB
```

For an installed `zmdc` command:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/zmdc generate --version 1.0 --seed 20260914 --size 1GB --output outputs/ZMDC-1G-v1
```

`--size` accepts 10MB, 100MB, 1GB and explicit binary units. MB/GB are decimal. Existing nonempty output directories are refused. `--workload telemetry` selects the telemetry share (15%) of the chosen nominal corpus size. An API dependency stream is written under `_support`, hashed and accounted separately. Repeat `--workload` to select several families.

## Output and accounting

| Family | Nominal bytes at 1GB |
| --- | ---: |
| API | 150,000,000 |
| Telemetry | 150,000,000 |
| Observability | 150,000,000 |
| Application/system/audit logs | 125,000,000 |
| Database/CDC | 125,000,000 |
| Transactions | 100,000,000 |
| Collaboration | 75,000,000 |
| Structured binary | 75,000,000 |
| Entropy control | 50,000,000 |

Complete records or trace bundles are emitted until each target is reached. Exact bytes and record counts are measured, not hardcoded. Metadata is additional. Manifest `primary_bytes` is the official workload total; `total_bytes` includes listed metadata/support files, but excludes manifest.json itself. `global_sha256` hashes canonical sorted file/path/size/hash descriptors; it is not the hash of a concatenated archive.

The manifest contains world configuration, runtime, schema counts, logical ranges, source/specification digests, per-file SHA-256 and corpus hash. Generation duration and peak RSS live in an adjacent `<output>.profile.json`, outside the deterministic corpus tree.

## Synthetic mechanisms

- API: skewed endpoints and users, session reuse, weighted statuses, log-normal payloads and latency, region-local daily cycles and incidents.
- Telemetry: bounded per-device walks around physical baselines, periodic variation, correlated current/power and temperature/fan, anomalies, outage cohorts, reporting gaps and firmware rollouts.
- Observability: complete variable-depth span trees, parent checks, related metrics/logs and shared API request/trace links.
- Logs: JSON and losslessly parseable text logs, security/audit events, synthetic paths and documentation IP ranges, multiline stack traces and compositional prose.
- CDC: inserts, repeated updates and deletes over bounded live state, exact before/after images, monotonic sequences and owner references.
- Transactions: integer currency units, skewed merchants, log-normal amounts, recurring plan prices, failures, retries, high-risk outliers and refunds linked to settled charges.
- Collaboration: synthetic messages, channel activity, presence, reactions, meetings and file metadata tied to organizations and requests.
- Binary: documented uncompressed typed records and decoder, including separate compact edge samples.
- Controls: deterministic SHAKE-256 opaque blobs, nonce-like and hash-like values. These are not actual encrypted files or compressed media.

Default world: 50,000 users, 500 organizations, 5,000 devices, 240 instances, 20 services, 8 regions, 30 days. Output is a sample of such a world, not every event emitted by that population. API windows provide cross-family causal anchors. The streams are intentionally not identical representations of the same dataset.

## Configuration

World counts and imperfection rates may be supplied as JSON:

```json
{
  "users": 50000,
  "organizations": 500,
  "devices": 5000,
  "instances": 240,
  "rates": {
    "duplicate": 0.01,
    "delayed": 0.025,
    "missing": 0.025,
    "null": 0.02,
    "retry": 0.03,
    "anomaly": 0.005,
    "clock_drift": 0.03,
    "unexpected_enum": 0.003
  }
}
```

```sh
python3 -m zmdc generate --config config.json --size 100MB --output outputs/custom
```

All rate keys are required when overriding rates. Values are between 0 and .25. The CLI seed/size/version are authoritative. Custom configurations are recorded and must not be presented as the default official suite. Missing/null rates apply to optional fields; domain failures can introduce additional null sensor values. Duplicate sampling is per logical emission unit; a trace bundle may contain several records. Short corpora may not expose every rare event.

## Alternative representations

The official telemetry representation is JSONL. Export the same logical dataset separately:

```sh
python3 -m zmdc encode outputs/dev-10MB/telemetry/telemetry.jsonl --format csv --output variants/telemetry.csv
python3 -m zmdc encode outputs/dev-10MB/telemetry/telemetry.jsonl --format binary --output variants/telemetry.bin
```

Both conversions verify logical equality record by record. CSV uses sorted columns and JSON-encoded cells to preserve null versus absent fields and nested structures. Binary is ZMDCBIN v1, a documented typed encoding with framing and CRC32. It is not MessagePack or Protobuf and is not mislabeled as either. Alternatives must remain outside the official output directory, or strict validation will report unexpected files.

## Validation and statistics

`validate` and `stats` run a complete streaming integrity/semantic pass. Temporary SQLite indexes enable exact ID counts and reference checks without retaining all records in Python memory. They verify hashes, lengths, counts, JSON canonicalization, binary framing/CRC, timestamps, versions, request/user/organization links, trace parents, CDC transitions and refunds. Statistics include bounded-field and identifier cardinalities, event proportions, numeric summaries, top-level null/missing rates, duplicates, event-time reordering, byte entropy and per-device continuity. Out-of-order rates depend on sample spacing as well as configured delays; they are reported rather than forced to an arbitrary number.

```sh
python3 -m unittest discover -s tests -v
```

Tests cover deterministic trees/manifests, different-seed divergence, alternative encoding round trips, binary corruption, missing references, invalid schemas and illegal state transitions. Reports from the actual 10MB, 100MB and 1GB runs live in `reports/`. See `IMPLEMENTATION_REPORT.md` for the final measured sizes, hashes, validation results and limitations.

## Reproducibility and publication

Separate named PRNG streams derive from the seed by SHA-256. IDs and opaque fields derive from explicit domains. No uncontrolled RNG, wall time, path name or output directory enters corpus bytes. Canonical serialization fixes field order and whitespace; floats are rounded. The reference guarantee is for a given implementation, version and runtime. Cross-runtime/distribution-library equivalence is not assumed; record the manifest runtime and retain the source.

`FREEZE.json` preserves the original pre-benchmark freeze record. This repository publishes that unchanged generator and the original corpus manifest; its historical local status describes the time of freezing. Before public release, independent review and domain calibration remain appropriate. Once published, preserve that exact source/configuration, and make any material change under a new version.

## Project layout

`zmdc/config.py`, `rng.py`, `world.py`: configuration, independent randomness and shared world.
`zmdc/workloads/`: logical generators only.
`zmdc/encoders/`: JSONL, parseable logs, binary and optional CSV.
`zmdc/generation.py`, `manifest.py`: streaming output and accounting.
`zmdc/validation.py`, `statistics.py`: integrity, semantics and summaries.
`zmdc/cli.py`: CLI. `tests/`: automated checks.

The architecture can support larger byte budgets and additional families later; separate 10G/100G suites are not implemented as published specifications here.

MIT license; see LICENSE.
