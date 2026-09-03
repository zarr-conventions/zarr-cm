# STAC

This example demonstrates the [stac](https://github.com/zarr-conventions/stac)
convention, which attaches [STAC](https://stacspec.org/) (SpatioTemporal Asset
Catalog) Item or Collection metadata to a Zarr group.

The example shows how to:

- Embed a complete STAC Item directly with `stac.create_convention_attrs(item=...)`
- Point at a canonical STAC object hosted elsewhere with `stac:link`
- Detect the revision of a stored document with `stac.detect`
- Handle a document declaring an unrecognized `schema_url` defensively
- The convention is **group-only**: `validate_node_metadata` accepts a group
  document and rejects an array document

Exactly one of `stac:item`, `stac:collection`, `stac:key`, or `stac:link` must
be present on any given document; `stac.create`/`create_convention_attrs`
enforce that on the way out.

Like every `zarr-cm` convention, this module works on plain attributes/metadata
dicts and does no Zarr store I/O. `stac:key` only carries and validates the key
string; actually writing the JSON value it references (e.g. a `stac.json` file
next to `zarr.json`) into a real store is the caller's job, done with
`zarr-python` or another store-writing library, not with `zarr-cm`.

## Running the Example

From the repository root, [uv](https://docs.astral.sh/uv/) runs the script in
the project environment, installing zarr-cm on the way in:

```bash
uv run examples/stac/stac.py
```

Alternatively, run it with plain Python in any environment where `zarr-cm` is
installed:

```bash
python examples/stac/stac.py
```

Every example prints a trace of what it does and ends with `OK`; the test suite
runs them all and asserts exactly that (`tests/test_examples.py`).
