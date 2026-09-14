# ZMDC-1G v1 distribution

ZMDC-1G v1 is distributed as a frozen, pre-generated corpus in addition to the open-source generator.

## Release assets

The canonical v1.0 release publishes:

- `ZMDC-1G-v1.tar.zst` — the pre-generated corpus tree.
- `ZMDC-1G-v1.manifest.json` — the frozen reference manifest.
- `SHA256SUMS` — SHA-256 checksums for the downloadable release assets.

GitHub also provides source archives for the tagged generator source.

Release page:

`https://github.com/Zetako-Compression-Lab/zetako-modern-data-corpus/releases/tag/v1.0.0`

Direct asset locations after publication:

```text
https://github.com/Zetako-Compression-Lab/zetako-modern-data-corpus/releases/download/v1.0.0/ZMDC-1G-v1.tar.zst
https://github.com/Zetako-Compression-Lab/zetako-modern-data-corpus/releases/download/v1.0.0/ZMDC-1G-v1.manifest.json
https://github.com/Zetako-Compression-Lab/zetako-modern-data-corpus/releases/download/v1.0.0/SHA256SUMS
```

## Frozen corpus identity

- Specification: ZMDC-1G v1.0
- Seed: `20260914`
- Primary records: `951,552`
- Primary bytes: `1,000,037,807`
- Primary files: `13`
- Reference runtime: CPython `3.12.10`
- Corpus global SHA-256: `34b3479f61272231502cfa3f923d5780548b4f08d9dd733306f5d70b30589a7f`

The corpus global SHA-256 is defined by the specification as the SHA-256 of canonical sorted `{path, bytes, sha256}` descriptors. It is not the SHA-256 of the `.tar.zst` archive. The archive and manifest have their own hashes in `SHA256SUMS`.

## Download, verify, benchmark

Download all three release assets into one directory, then verify them:

```sh
sha256sum -c SHA256SUMS
```

On macOS, if `sha256sum` is unavailable, use a compatible implementation such as GNU coreutils (`gsha256sum`) or verify each value using `shasum -a 256`.

Extract the corpus:

```sh
zstd -d --stdout ZMDC-1G-v1.tar.zst | tar -xf -
```

The extracted tree is `ZMDC-1G-v1/`. Its `manifest.json` is the frozen reference manifest. Before benchmarking, verify the corpus semantically if the generator package is available:

```sh
python3 -m zmdc validate ZMDC-1G-v1
```

A compression benchmark can then consume the 13 primary files exactly as listed in the manifest. README and manifest metadata are not part of `primary_bytes`.

## Reproduce instead of download

The generator remains the scientific reference. The official corpus can be regenerated with:

```sh
python3 -m zmdc generate \
  --version 1.0 \
  --seed 20260914 \
  --size 1GB \
  --output outputs/ZMDC-1G-v1
```

The frozen reference was produced with CPython 3.12.10. A checkout generated after Git history exists records a non-null `git_commit` in its generated manifest, so the manifest file itself is not expected to be byte-identical to the historical reference manifest. Compare the corpus `global_sha256`, per-file hashes, configuration, implementation fingerprint and specification fingerprint.

## Publication invariant

ZMDC-1G v1 is immutable. The release workflow refuses to publish unless a newly generated corpus matches the frozen reference global hash, primary byte count, record count, implementation fingerprint and every frozen file hash. Any material future distribution/schema change must use a new version.
