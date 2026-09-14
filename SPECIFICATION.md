# ZMDC-1G v1.0 specification

Status: v1.0 implementation specification. Freeze by SHA-256 before compression comparisons. A publication must preserve this document, generator sources, configuration, and manifest. Material schema/distribution changes require a new version; this is not a promise of compatibility with future Python implementations.

## Benchmark Independence

ZMDC is a deterministic synthetic corpus for contemporary structured and machine-generated data. It is independent of any compression engine. No compression executable is invoked by this project. No workload, size, distribution, encoding, or parameter is selected using compression results. The specification and generator must be complete and frozen before comparisons. It does not represent every kind of data generated in 2026. It contains no real personal messages or copyrighted source content.

## Logical world and time

Defaults: 50,000 users, 500 organizations, 5,000 devices, 240 instances, 20 services, 8 regions, 30 days from 2026-01-01T00:00:00Z. User organization is `(user_id-1) mod organization_count + 1`. Devices and instances have stable regions and device-specific baselines. Identifier namespaces are synthetic. Numeric entity IDs are validated against the world bounds.

Generation is streaming. Each family first yields logical dictionaries/events; independent encoders then serialize them. The API is the causal anchor stream. Other families consult a bounded rolling window of prior API requests at the current logical time. They retain request/trace/user/organization references from those real generated anchors. Their own record IDs are distinct. This is an explicitly sampled infrastructure, not an exhaustive reconstruction of all events that 50,000 people would produce in a month.

Each primary family spans the same 30-day clock. Logical progress is derived from emitted bytes relative to its byte budget. Within-day clock progression follows a fixed cumulative traffic profile: quiet overnight and more business-hour events. Region selection follows the region's local time. Days 6, 12, 19 and 25 contain scheduled incidents, product bursts, outages or deployments. Observation time and event time are separate; delayed delivery and bounded clock drift can put event timestamps out of order.

## Composition and stopping rule

Decimal sizes: 1GB = 1,000,000,000 bytes; 100MB = 100,000,000; 10MB = 10,000,000. Primary weights:

| Family | Weight | Primary files |
| --- | ---: | --- |
| API | 15% | api/events.jsonl |
| Telemetry | 15% | telemetry/telemetry.jsonl |
| Observability | 15% | observability/{traces,metrics,logs}.jsonl |
| Logs | 12.5% | logs/{application,system}.log; logs/audit.jsonl |
| Database | 12.5% | database/cdc.jsonl |
| Transactions | 10% | transactions/transactions.jsonl |
| Collaboration | 7.5% | collaboration/events.jsonl |
| Binary | 7.5% | binary/records.bin |
| Entropy control | 5% | entropy-control/control.bin |

Generate complete records, or complete trace/metric/log bundles, until each budget is reached. Overshoot is at most the final emission unit. There is no byte padding or truncation inside records. Metadata is additional. `--workload` selects a family's proportional share of `--size`; an API support stream is also generated for causal references, separately labelled and excluded from primary bytes.

## Randomness

Seed 20260914. Each named workload receives a `random.Random` instance seeded with SHA-256 of a versioned domain separator, the decimal seed, and stream name. No global RNG, current time, filesystem enumeration order, process hash randomization or thread scheduling affects data. Cryptographic hash-derived identifiers and SHAKE-256 control blobs are deterministic synthetic values, not security tokens. Float output is rounded before canonical serialization. Reproducibility is promised for the recorded implementation/runtime; cross-runtime changes to distribution functions require validation.

## Distributions and relationships

API: weighted endpoints, truncated Pareto heavy users, session reuse, high-cardinality hash request/trace IDs, log-normal latency and response size. Request rate, scheduled incidents, errors and latency are correlated. Endpoints map to services; instances belong to services. Region popularity varies by local hour.

Telemetry: bounded per-device state; baseline plus daily sinusoid, small Gaussian innovations, drift, bounded values, correlated power/current and temperature/fan speed. Failure windows, outage-related reporting gaps, delayed delivery, duplicates and staggered firmware upgrades. Binary telemetry represents separate device samples, not a second copy of the telemetry family.

Observability: variable-depth complete trees with gateway roots, service and database children, optional storage calls and retries. Children share trace and request identity; parent IDs exist in the same emitted trace. Durations and errors inherit request conditions. Each bundle includes a related metric and structured log. CPU and queue depth depend on the same load used for latency.

Logs: application, system, container, network, security and audit types; templated and compositional synthetic prose, generated paths, reserved documentation IP addresses, variable identifiers, occasional multiline stack traces. Text logs use an escaped one-line header plus canonical JSON logical record, allowing lossless parsing without guessing free-text boundaries.

CDC: bounded live state per table, insert/update/delete lifecycle with exact before/after images, monotonic sequence numbers, synthetic transaction IDs. Inserts precede updates/deletes; deleted keys are not silently reused. User/session/message/file/device/subscription domains link to the same world. State limits prevent memory growth with corpus size.

Transactions: amounts in integer minor currency units drawn from bounded log-normal distributions, skewed customers and merchants, recurring identifiers, retries, failed/pending/settled outcomes, fraud-like high-value anomalies, and refunds referencing prior settled transactions with matching account/currency. This is a synthetic financial workload, not financial advice or real transaction data.

Collaboration: synthetic messages built from combinatorial subjects/actions/objects and qualifiers, channels, presence, meetings, mentions, reactions, notifications and file metadata. Stable workspace/user relationships and API references. No external prose is sampled.

## Configurable imperfections

Default probabilities per new emission unit: duplicate .01, delayed .025, missing optional metadata .025, explicit null .02, retry .03, anomaly .005, clock drift .03, unexpected enum .003. Duplicate units reuse prior logical record IDs and carry `is_duplicate=true`; validator skips reapplying their state transitions. Duplicates have the original event/observation time, so observation monotonicity excludes them. Nested trace bundles share a quality decision. Rates are independent Bernoulli draws unless a scheduled incident adds domain-specific failures. `quality` records sampling decisions; actual missing/null/duplicate/out-of-order rates are also measured separately. Rates are configurable, not silently changed for a target size.

## Schema evolution

Version is derived from observation day: days 1–7: 1.0; 8–14: 1.1 (optional deployment context); 15–19: 1.2 (client_type becomes client_family); 20–23: 1.3 (edge_proxy enum appears); 24–26: 1.4 (legacy optional metadata retires); days 27–30: 2.0 rollout, with a minority of instances still on 1.4. Required identity/reference fields remain stable. Missing and null perturbations affect optional fields only. Validators check version eligibility and renamed-field rules.

## Serialization

NDJSON: UTF-8, sorted keys, compact separators, finite numbers, one complete JSON object plus LF per record. No BOM. CSV variants: deterministic column union sorted lexicographically; cells contain canonical JSON values (empty cell means absent), preserving nested structures, numbers, null and missing distinctions. Header and LF are fixed. Variants are external to the official corpus and do not count toward its primary byte budget.

Binary (`ZMDCBIN` v1): eight magic bytes `5a 4d 44 43 42 49 4e 01`. Then repeated little-endian headers `<IBQQII`: payload length u32, kind code u8, event timestamp u64, entity ID u64, flags u32, CRC32 u32. Payload is a typed encoding: 0=null, 1=false, 2=true, 3=signed i64, 4=IEEE754 f64, 5=UTF-8 string, 6=bytes, 7=list, 8=map. Strings/bytes carry u32 byte lengths; lists/maps u32 item counts; maps have sorted string keys. Headers must match decoded records. No compression is embedded. Reader enforces length/depth limits, complete framing, CRC, kind and header agreement. The same encoder is available as an alternative representation of any JSONL dataset.

Entropy controls: independent deterministic 32KiB SHAKE-256 byte blobs with high-cardinality hashes, nonce-like values and type labels. They are not encrypted files and not actual media; no fake media or encryption claims are made. The primary binary framing makes controls decodable and counts overhead honestly.

## Manifest and accounting

Manifest contains exact payload/support/metadata bytes, per-file records, schema counts, byte sizes, SHA-256, source/specification digest, runtime, seed, configuration and logical range. No wall-clock generation timestamp is included. `total_bytes` covers all listed files, excluding manifest.json itself (self-hashing is undefined here). `primary_bytes` alone targets the nominal size. The global hash is SHA-256 of canonical JSON of sorted `{path,bytes,sha256}` entries. Runtime duration and peak RSS go into a separate sibling profile JSON, never the deterministic corpus tree. Git commit is recorded only if the standalone project itself is a Git root; otherwise null.

## Validation and statistics

Parse every record and verify file hashes/sizes/counts and global accounting. Validate world bounds, user/organization consistency, request references, trace parents, CDC transitions, refunds, version rules, observation ordering (excluding declared duplicates), delay/clock bounds, rates and binary decoding. SQLite temporary indexes bound Python memory while providing exact high-cardinality uniqueness and relationship checks. Report exact record-ID cardinality, field cardinality for bounded dimensions, per-kind counts, numeric summaries, null/missing/duplicate/out-of-order rates, byte entropy, record lengths, and telemetry continuity. Empirical entropy is zero-order byte entropy, not a bound for every possible compressor. Validation describes discrepancies rather than manufacturing ideal statistics.

Determinism tests compare two complete small output trees byte for byte and manifest contents, and verify different seeds change the corpus hash. Corruption tests modify payloads, references, schemas and binary checksums. Generation and validation are streaming; memory is bounded by world state, a small anchor/history window, buffers and disk-backed indexes.
