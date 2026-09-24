"""Draft-era schema URLs alias to surviving revisions.

Between the specs' first drafts (December 2025) and their v0.1 releases
(June 2026), the spec READMEs published example declarations carrying
`refs/tags/v1` schema URLs that were never released. Deployed writers --
rioxarray, topozarr, xpublish-tiles -- copied those examples, so documents
declaring the dead URLs exist in the wild. Each fixture here reproduces a
deployed writer's declaration verbatim.

The aliases are enumerated, not a fallback: a URL outside the recognized
set still fails validation (`test_contracts` pins that separately).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jsonschema
import pytest

import zarr_cm
from zarr_cm import multiscales, proj, spatial

if TYPE_CHECKING:
    from zarr_metadata import ZarrV3GroupMetadataJSON

SCHEMAS = Path(__file__).parent / "schemas"

# As written by rioxarray (rioxarray/_convention/zarr.py): the geo-proj
# spelling predates the repo's rename to proj.
RIOXARRAY_PROJ_CMO: dict[str, Any] = {
    "schema_url": "https://raw.githubusercontent.com/zarr-conventions/geo-proj/refs/tags/v1/schema.json",
    "uuid": "f17cb550-5864-4468-aeb7-f3180cfb622f",
    "name": "proj:",
}
RIOXARRAY_SPATIAL_CMO: dict[str, Any] = {
    "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json",
    "uuid": "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4",
    "name": "spatial:",
}
# As written by topozarr (src/topozarr/metadata.py).
TOPOZARR_MULTISCALES_CMO: dict[str, Any] = {
    "schema_url": "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v1/schema.json",
    "spec_url": "https://github.com/zarr-conventions/multiscales/blob/v1/README.md",
    "uuid": "d35379db-88df-4056-af3a-620245f8e347",
    "name": "multiscales",
}


def wild_geozarr_attrs() -> dict[str, Any]:
    """A rioxarray-style attributes dict: proj + spatial, draft-era URLs."""
    return {
        "zarr_conventions": [RIOXARRAY_PROJ_CMO, RIOXARRAY_SPATIAL_CMO],
        "proj:code": "EPSG:4326",
        "spatial:dimensions": ["y", "x"],
        "spatial:transform": [30.0, 0.0, 323400.0, 0.0, -30.0, 4268400.0],
    }


def test_legacy_urls_detect_as_their_alias() -> None:
    attrs = wild_geozarr_attrs()
    assert spatial.detect(attrs) == "r2"
    assert proj.detect(attrs) == "r2"
    ms_attrs: dict[str, Any] = {
        "zarr_conventions": [TOPOZARR_MULTISCALES_CMO],
        "multiscales": {"layout": [{"asset": "0"}]},
    }
    assert multiscales.detect(ms_attrs) == "r2"


def test_legacy_documents_validate_and_extract() -> None:
    attrs = wild_geozarr_attrs()
    assert spatial.validate(attrs).get("spatial:dimensions") == ["y", "x"]
    remaining, data = spatial.extract(attrs)
    assert data.get("spatial:transform") is not None
    assert "proj:code" in remaining
    assert zarr_cm.validate_all(attrs) is not None


def test_legacy_documents_validate_at_node_level() -> None:
    node: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": wild_geozarr_attrs(),
    }
    spatial.validate_group_metadata(node)
    proj.validate_group_metadata(node)


def test_legacy_url_satisfies_a_matching_revision_pin() -> None:
    attrs = wild_geozarr_attrs()
    node: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": attrs,
    }
    # Pinning the revision the legacy URL aliases to is consistent...
    spatial.validate_group_metadata(node, revision="r2")
    # ...pinning a different revision is still a declaration mismatch.
    with pytest.raises(ValueError, match="does not match revision 'r3'"):
        spatial.validate_group_metadata(node, revision="r3")


def test_aliases_are_additive_and_disjoint_from_canonical() -> None:
    """Aliases are the *other* URLs: the canonical one is never listed among them.

    The recognized set is derived as `{SCHEMA_URL} | ALIAS_SCHEMA_URLS`, so
    canonical membership holds by construction; what a revision must not do
    is repeat its own canonical URL as an alias.
    """
    for module in (spatial.r2, spatial.r3, proj.r2, proj.r3, multiscales.r2):
        assert module.SCHEMA_URL not in module.ALIAS_SCHEMA_URLS
    # And every alias reaches the package map alongside the canonical url.
    for module, pkg in (
        (spatial.r2, spatial),
        (proj.r2, proj),
        (multiscales.r2, multiscales),
    ):
        for url in module.ALIAS_SCHEMA_URLS:
            assert pkg.REVISION_BY_SCHEMA_URL[url] == "r2"


def test_written_documents_use_the_narrow_url() -> None:
    """The output type is a single URL: new documents never carry an alias."""
    attrs = spatial.create_convention_attrs(dimensions=["y", "x"])
    (declaration,) = attrs["zarr_conventions"]
    assert declaration.get("schema_url") == spatial.SCHEMA_URL
    assert declaration.get("schema_url") != RIOXARRAY_SPATIAL_CMO["schema_url"]


def test_input_map_is_published_per_package() -> None:
    """The wide input type is public data: every recognized url -> its revision."""
    assert spatial.REVISION_BY_SCHEMA_URL[RIOXARRAY_SPATIAL_CMO["schema_url"]] == "r2"
    assert proj.REVISION_BY_SCHEMA_URL[RIOXARRAY_PROJ_CMO["schema_url"]] == "r2"
    assert (
        multiscales.REVISION_BY_SCHEMA_URL[TOPOZARR_MULTISCALES_CMO["schema_url"]]
        == "r2"
    )
    # Both proj spellings are covered: the repo was renamed geo-proj -> proj.
    assert (
        "https://raw.githubusercontent.com/zarr-conventions/proj/refs/tags/v1/schema.json"
        in proj.REVISION_BY_SCHEMA_URL
    )
    # And the canonical urls are members too -- one map, one lookup.
    assert spatial.REVISION_BY_SCHEMA_URL[spatial.r3.SCHEMA_URL] == "r3"
    assert spatial.REVISION_BY_SCHEMA_URL[spatial.r2.SCHEMA_URL] == "r2"


def test_no_url_is_claimed_by_two_revisions() -> None:
    """No shared URLs across the whole map: across a convention, every URL names one revision.

    `detect` and validation both look the declared URL up in
    `REVISION_BY_SCHEMA_URL`, so a URL two revisions both claimed would resolve
    to whichever was inserted last. The per-revision test above only checks a
    revision against itself; this checks the map as a whole.
    """
    for pkg in (spatial, proj, multiscales):
        claimed: dict[str, str] = {}
        for label, module in pkg._REVISIONS.items():
            for url in (module.SCHEMA_URL, *module.ALIAS_SCHEMA_URLS):
                assert url not in claimed, (
                    f"{pkg.__name__}: {url} claimed by {claimed[url]} and {label}"
                )
                claimed[url] = label
        assert claimed == pkg.REVISION_BY_SCHEMA_URL


def test_map_construction_refuses_a_shared_url() -> None:
    """The map cannot even be built with an ambiguous URL -- it fails at import.

    A future alias that shadowed another revision's canonical URL would raise
    when the convention package is imported, not silently win the lookup.
    """
    from zarr_cm._core import build_revision_by_schema_url  # noqa: PLC0415

    with pytest.raises(ValueError, match="claimed by revisions 'r2' and 'r3'"):
        build_revision_by_schema_url(
            {
                "r2": ("https://example/r2.json", frozenset()),
                "r3": (
                    "https://example/r3.json",
                    frozenset({"https://example/r2.json"}),
                ),
            }
        )
    # The same URL listed twice *within* one revision is not a conflict.
    assert build_revision_by_schema_url(
        {"r2": ("https://example/r2.json", frozenset({"https://example/r2.json"}))}
    ) == {"https://example/r2.json": "r2"}


# The URLs upstream *tells* writers to declare for the v0.1 releases: the
# `$id` of each published schema and the `schema_url` in every README example.
# Each tag points at the very commit the r3 snapshots pin, so a document
# declaring the tag URL must read as r3.
PROJ_V01_TAG_URL = (
    "https://raw.githubusercontent.com/zarr-conventions/proj/refs/tags/v0.1/schema.json"
)
SPATIAL_V01_TAG_URL = "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v0.1/schema.json"


def upstream_readme_attrs() -> dict[str, Any]:
    """Attributes exactly as the upstream proj/spatial READMEs show them."""
    return {
        "zarr_conventions": [
            {"uuid": proj.UUID, "schema_url": PROJ_V01_TAG_URL, "name": "proj"},
            {
                "uuid": spatial.UUID,
                "schema_url": SPATIAL_V01_TAG_URL,
                "name": "spatial",
            },
        ],
        "proj:code": "EPSG:4326",
        "spatial:dimensions": ["y", "x"],
        "spatial:bbox": [-180.0, -90.0, 180.0, 90.0],
    }


def test_v01_tag_urls_match_the_published_schema_ids() -> None:
    """The alias is the schema's own `$id`: the vendored snapshots agree."""
    for path, url in (
        ("proj-r3.json", PROJ_V01_TAG_URL),
        ("spatial-r3.json", SPATIAL_V01_TAG_URL),
    ):
        schema = json.loads((SCHEMAS / path).read_text())
        assert schema["$id"] == url


@pytest.mark.parametrize(
    ("module", "schema_file"),
    [
        (proj.r3, "proj-r3.json"),
        (spatial.r3, "spatial-r3.json"),
        (multiscales.r2, "multiscales-r2.json"),
    ],
)
def test_latest_cmo_satisfies_the_published_convention_metadata(
    module: Any, schema_file: str
) -> None:
    """The CMO a latest revision writes meets its schema's `conventionMetadata`.

    Checked against the subschema directly: in the proj and spatial schemas,
    `zarr_conventions` sits next to a sibling `$ref`, which draft-07 ignores,
    so validating a whole document never reaches these `const`s.
    """
    schema = json.loads((SCHEMAS / schema_file).read_text())
    subschema = {
        **schema["$defs"]["conventionMetadata"],
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
    }
    jsonschema.validate(module.CMO, subschema)


def test_zarr_cm_0_4_documents_read_as_r3_and_rewrite_canonically() -> None:
    """0.4 wrote commit-pinned URLs and colon names; they read as r3, and
    re-inserting replaces the declaration with the canonical one."""
    for pkg, key, data in (
        (proj, "proj:code", proj.create(code="EPSG:4326")),
        (spatial, "spatial:dimensions", spatial.create(dimensions=["y", "x"])),
    ):
        (commit_url,) = pkg.r3.ALIAS_SCHEMA_URLS
        old_cmo = {
            "uuid": pkg.UUID,
            "schema_url": commit_url,
            "name": f"{pkg.CMO['name']}:",
        }
        attrs = {"zarr_conventions": [old_cmo], **data}
        assert pkg.detect(attrs) == "r3"
        assert pkg.validate(attrs).get(key) == data[key]
        rewritten = pkg.insert(attrs, data, overwrite=True)
        assert rewritten["zarr_conventions"] == [pkg.CMO]


def test_v01_tag_urls_detect_as_r3() -> None:
    attrs = upstream_readme_attrs()
    assert proj.detect(attrs) == "r3"
    assert spatial.detect(attrs) == "r3"
    assert proj.REVISION_BY_SCHEMA_URL[PROJ_V01_TAG_URL] == "r3"
    assert spatial.REVISION_BY_SCHEMA_URL[SPATIAL_V01_TAG_URL] == "r3"
    assert zarr_cm.detect_revisions(attrs) == {"proj": "r3", "spatial": "r3"}


def test_v01_tag_documents_validate_and_extract() -> None:
    attrs = upstream_readme_attrs()
    assert proj.validate(attrs).get("proj:code") == "EPSG:4326"
    assert spatial.validate(attrs).get("spatial:bbox") == [-180.0, -90.0, 180.0, 90.0]
    assert zarr_cm.validate_all(attrs) is attrs
    remaining, extracted = zarr_cm.extract_all(attrs)
    assert set(extracted) == {"proj", "spatial"}
    assert remaining == {}


def test_v01_tag_documents_validate_at_node_level() -> None:
    node: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": upstream_readme_attrs(),
    }
    proj.validate_group_metadata(node)
    spatial.validate_group_metadata(node)
    proj.validate_group_metadata(node, revision="r3")
    with pytest.raises(ValueError, match="does not match revision 'r2'"):
        spatial.validate_group_metadata(node, revision="r2")
