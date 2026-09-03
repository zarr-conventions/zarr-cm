# zarr-cm Examples

This directory contains complete, runnable examples demonstrating each
convention that zarr-cm implements. Every script walks the same three workflows
-- create new data, read data written under an unknown or older revision, and
migrate data between revisions -- and prints a trace ending in `OK`.

## Directory Structure

Each example is organized in its own subdirectory:

```
examples/
├── example_name/
│   ├── README.md          # Documentation for the example
│   └── example_name.py    # Python source code
└── ...
```

## The Examples

- [composition](composition/README.md) -- several conventions on one node,
  GeoZarr group/array placement, and whole-document validation
- [reading](reading/README.md) -- the consumer workflow: UUID-based detection,
  revision handling, and defensive reads with spec defaults
- [spatial](spatial/README.md) -- spatial coordinate metadata, with a real
  cross-revision migration (r2 to r3)
- [proj](proj/README.md) -- coordinate reference systems, including a migration
  that changes the document's pinned `schema_url`
- [multiscales](multiscales/README.md) -- multiscale pyramid layout on a group
  (single revision)
- [license](license/README.md) -- license specifiers (single revision)
- [uom](uom/README.md) -- units of measurement as UCUM codes (single revision)
- [stac](stac/README.md) -- STAC Item/Collection metadata on a group (single
  revision, group-only)

## Adding New Examples

To add a new example:

1. Create a new subdirectory: `examples/my_example/`
2. Add your Python code: `examples/my_example/my_example.py` -- print a trace
   and end with `OK` on success, so `tests/test_examples.py` picks it up
3. Create documentation: `examples/my_example/README.md`
4. Create a documentation page at `docs/examples/my_example.md` that includes
   the README and the source via snippet directives (see the existing pages)
5. Add the new page to the `Examples` section of `mkdocs.yml`
