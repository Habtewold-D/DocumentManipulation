from app.domain.compare import CompareService


class _FakeVersion:
    def __init__(self, manifest: str | None):
        self.preview_manifest = manifest


class _FakeRepo:
    def __init__(self, source_manifest: str, target_manifest: str):
        self.source = _FakeVersion(source_manifest)
        self.target = _FakeVersion(target_manifest)

    def get_for_document(self, document_id: str, version_id: str):
        if version_id == "from":
            return self.source
        if version_id == "to":
            return self.target
        return None


def test_compare_returns_changed_pages_from_preview_hashes() -> None:
    repo = _FakeRepo(
        source_manifest='{"pages":[{"page":1,"hash":"a"},{"page":2,"hash":"b"}]}',
        target_manifest='{"pages":[{"page":1,"hash":"a"},{"page":2,"hash":"x"}]}',
    )
    service = CompareService(repo)  # type: ignore[arg-type]

    result = service.compare("doc-1", "from", "to")

    assert result.changed_pages == [2]
