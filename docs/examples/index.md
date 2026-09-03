# Examples

Complete, runnable examples demonstrating each convention that zarr-cm
implements. Every script walks the same three workflows — create new data, read
data written under an unknown or older revision, and migrate data between
revisions — and prints a trace ending in `OK`. The test suite runs them all and
asserts exactly that.

Each example lives in its own subdirectory of
[`examples/`](https://github.com/zarr-conventions/zarr-cm/tree/main/examples)
with a README and its source, embedded in the pages below.

- [composition](composition.md) — several conventions on one node, GeoZarr
  group/array placement, and whole-document validation
- [reading](reading.md) — the consumer workflow: UUID-based detection, revision
  handling, and defensive reads with spec defaults
- [spatial](spatial.md) — spatial coordinate metadata, with a real
  cross-revision migration (r2 to r3)
- [proj](proj.md) — coordinate reference systems, including a migration that
  changes the document's pinned `schema_url`
- [multiscales](multiscales.md) — multiscale pyramid layout on a group (single
  revision)
- [license](license.md) — license specifiers (single revision)
- [uom](uom.md) — units of measurement as UCUM codes (single revision)
- [stac](stac.md) — STAC Item/Collection metadata on a group (single revision,
  group-only)
