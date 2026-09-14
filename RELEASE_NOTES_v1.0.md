# ZMDC-1G v1.0

First frozen public release of the Zetako Modern Data Corpus.

ZMDC is a deterministic synthetic corpus for benchmarking compression on contemporary structured and machine-generated data. The corpus was frozen before external compression comparisons; the generator and specification were not tuned after observing codec results.

## Reference identity

- Seed: `20260914`
- Primary bytes: `1,000,037,807`
- Primary records: `951,552`
- Primary files: `13`
- Workload families: `9`
- Reference runtime: CPython `3.12.10`
- Generator version: `1.0.0`
- Corpus global SHA-256: `34b3479f61272231502cfa3f923d5780548b4f08d9dd733306f5d70b30589a7f`
- Implementation SHA-256: `9aa823da5b7cd3b3b1b6bf395fcddae24bf5b4ebdc95940e65c96d080c2caad1`
- Specification SHA-256: `37d8e70f7df68f989028fdf263c31f1238f97c51fc9cbe4e7e7c688ec7165700`

## Corpus composition

| Family | Primary bytes |
| --- | ---: |
| API | 150,000,836 |
| Telemetry | 150,000,551 |
| Observability | 150,000,779 |
| Logs | 125,000,639 |
| Database / CDC | 125,000,308 |
| Transactions | 100,000,058 |
| Collaboration | 75,000,577 |
| Structured binary | 75,000,449 |
| Entropy control | 50,033,610 |

Complete records or bundles are emitted until each target is reached; there is no arbitrary byte padding or truncation inside records.

## Assets

- `ZMDC-1G-v1.tar.zst` — pre-generated reference corpus.
- `ZMDC-1G-v1.manifest.json` — frozen reference manifest.
- `SHA256SUMS` — checksums for downloadable assets.
- GitHub-generated source archives — tagged open-source generator source.

See `DISTRIBUTION.md` for download, verification, extraction and reproduction instructions.

## Immutability

ZMDC-1G v1.0 is frozen. The publication workflow regenerates the corpus with CPython 3.12.10 and refuses release if the generated primary corpus differs from the frozen manifest, including the global corpus hash, file hashes, byte count, record count or implementation/specification fingerprints.

Material changes to workload distributions, schemas, serialization or generator semantics require a new corpus version rather than modification of v1.0.
