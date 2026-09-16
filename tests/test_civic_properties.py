from __future__ import annotations

from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from suzano_aberta.content_store import ContentAddressedStore, SnapshotManifest
from suzano_aberta.entities import canonical_entity_id, normalize_name


@settings(max_examples=150, deadline=None)
@given(st.text(max_size=200))
def test_name_normalization_is_idempotent(value: str) -> None:
    normalized = normalize_name(value)
    assert normalize_name(normalized) == normalized


@settings(max_examples=100, deadline=None)
@given(st.text(min_size=1, max_size=120))
def test_canonical_entity_id_is_case_insensitive(value: str) -> None:
    assert canonical_entity_id("orgao", value) == canonical_entity_id("orgao", value.swapcase())


@settings(max_examples=80, deadline=None)
@given(st.binary(max_size=4096))
def test_content_addressed_store_is_deterministic(payload: bytes) -> None:
    with TemporaryDirectory() as temp_dir:
        store = ContentAddressedStore(temp_dir)
        first = store.put_bytes(payload)
        second = store.put_bytes(payload)

        assert first.sha256 == second.sha256
        assert first.path == second.path
        assert store.verify(first.sha256)


@settings(max_examples=80, deadline=None)
@given(
    dataset=st.text(min_size=1, max_size=80),
    records=st.integers(min_value=0, max_value=10_000_000),
    sources=st.integers(min_value=0, max_value=10_000),
)
def test_manifest_canonical_representation_is_stable(
    dataset: str,
    records: int,
    sources: int,
) -> None:
    manifest = SnapshotManifest(
        software_version="1.0.0",
        dataset_version=dataset,
        database_sha256="a" * 64,
        database_bytes=42,
        records=records,
        sources=sources,
        contract_status="pass",
        contract_sha256="b" * 64,
    )
    first = manifest.canonical_json()
    second = SnapshotManifest.model_validate_json(first).canonical_json()

    assert first == second
    assert manifest.sha256() == SnapshotManifest.model_validate_json(first).sha256()
