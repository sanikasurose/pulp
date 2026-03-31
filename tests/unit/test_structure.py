from __future__ import annotations

import dataclasses
import importlib
import sys
import types
from pathlib import Path

import pytest

import pulp.structure as structure_mod
from pulp.config import Settings
from pulp.models import (
    CleanedPage,
    CleaningResult,
    DocumentClassification,
    DocumentMeta,
)


def _cleaning_result(*, pages: list[CleanedPage]) -> CleaningResult:
    meta = DocumentMeta(
        source_path="in.pdf",
        page_count=max(1, len(pages)),
        file_size_bytes=0,
        classification=DocumentClassification.TEXT_LAYER,
        language=None,
    )
    return CleaningResult(meta=meta, pages=pages, warnings=[])


def test_structure_document_llm_disabled_is_deterministic_heuristic() -> None:
    cleaned = _cleaning_result(
        pages=[
            CleanedPage(page_number=1, clean_text="Hello", warnings=[]),
            CleanedPage(page_number=2, clean_text="World", warnings=[]),
        ]
    )
    doc = structure_mod.structure_document(cleaned, settings=Settings(), llm_enabled=False)
    assert doc.markdown == "Hello\n\nWorld\n"
    assert doc.warnings == []


def test_structure_document_missing_api_key_falls_back_when_not_strict() -> None:
    cleaned = _cleaning_result(pages=[CleanedPage(page_number=1, clean_text="Hi", warnings=[])])
    doc = structure_mod.structure_document(cleaned, settings=Settings(), llm_enabled=True)
    assert doc.markdown == "Hi\n"
    assert any("ANTHROPIC_API_KEY" in w for w in doc.warnings)


def test_structure_document_missing_api_key_raises_when_strict() -> None:
    cleaned = _cleaning_result(pages=[CleanedPage(page_number=1, clean_text="Hi", warnings=[])])
    with pytest.raises(structure_mod.LLMStructuringError):
        structure_mod.structure_document(
            cleaned,
            settings=Settings(strict_llm=True),
            llm_enabled=True,
        )


@dataclasses.dataclass
class _DummyBlock:
    text: str


@dataclasses.dataclass
class _DummyResponse:
    content: list[_DummyBlock]


class _DummyMessages:
    def __init__(self, response: object) -> None:
        self._response = response
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self._response


class _DummyAnthropic:
    last_instance: _DummyAnthropic | None = None

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.messages = _DummyMessages(_DummyResponse(content=[_DummyBlock(text="OUT")]))
        _DummyAnthropic.last_instance = self


def test_structure_document_calls_anthropic_and_loads_prompts(
    mocker: pytest.MockFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("pulp.structure._Anthropic", _DummyAnthropic)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("PULP_ANTHROPIC_MODEL", raising=False)

    cleaned = _cleaning_result(
        pages=[
            CleanedPage(page_number=1, clean_text="Alpha", warnings=[]),
            CleanedPage(page_number=2, clean_text="Beta", warnings=[]),
        ]
    )
    settings = Settings()
    doc = structure_mod.structure_document(cleaned, settings=settings, llm_enabled=True)
    assert doc.markdown == "OUT\n"

    used = _DummyAnthropic.last_instance
    assert used is not None
    assert used.api_key == "test-key"
    assert len(used.messages.calls) == 1
    call = used.messages.calls[0]
    assert call.get("model") == "claude-3-haiku-20240307"

    # Verify prompt templates were loaded and included.
    prompts_dir = Path(__file__).resolve().parents[2] / "src" / "pulp" / "prompts"
    heading = (prompts_dir / "heading_v1.txt").read_text(encoding="utf-8")
    structure = (prompts_dir / "structure_v1.txt").read_text(encoding="utf-8")
    assert heading.strip() in str(call.get("system", ""))
    assert structure.strip() in str(call.get("system", ""))

    # Verify page order preserved in the user text.
    messages = call.get("messages")
    assert isinstance(messages, list)
    user_content = messages[0]["content"]
    assert "--- Page 1 ---" in user_content
    assert "--- Page 2 ---" in user_content
    assert user_content.index("Alpha") < user_content.index("Beta")


def test_structure_document_anthropic_import_failure_sets_client_none_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    import anthropic as real_anthropic

    # Force `from anthropic import Anthropic` to fail during reload by providing a module
    # without the expected attribute.
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace())
    importlib.reload(structure_mod)
    assert structure_mod._Anthropic is None

    cleaned = _cleaning_result(pages=[CleanedPage(page_number=1, clean_text="Hi", warnings=[])])
    doc = structure_mod.structure_document(cleaned, settings=Settings(), llm_enabled=True)
    assert doc.markdown == "Hi\n"
    assert any("not importable" in w for w in doc.warnings)

    # Restore module state for subsequent tests.
    sys.modules["anthropic"] = real_anthropic
    importlib.reload(structure_mod)


def test_structure_document_anthropic_not_importable_raises_when_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(structure_mod, "_Anthropic", None)

    cleaned = _cleaning_result(pages=[CleanedPage(page_number=1, clean_text="Hi", warnings=[])])
    with pytest.raises(structure_mod.LLMStructuringError):
        structure_mod.structure_document(
            cleaned, settings=Settings(strict_llm=True), llm_enabled=True
        )


class _FailingMessages:
    def create(self, **kwargs: object) -> object:  # noqa: ARG002
        raise RuntimeError("boom")


class _FailingAnthropic:
    def __init__(self, *, api_key: str) -> None:  # noqa: ARG002
        self.messages = _FailingMessages()


def test_structure_document_llm_api_failure_falls_back_when_not_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(structure_mod, "_Anthropic", _FailingAnthropic)

    cleaned = _cleaning_result(pages=[CleanedPage(page_number=1, clean_text="Hi", warnings=[])])
    doc = structure_mod.structure_document(cleaned, settings=Settings(), llm_enabled=True)
    assert doc.markdown == "Hi\n"
    assert any("LLM structuring failed" in w for w in doc.warnings)


def test_structure_document_llm_api_failure_raises_when_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(structure_mod, "_Anthropic", _FailingAnthropic)

    cleaned = _cleaning_result(pages=[CleanedPage(page_number=1, clean_text="Hi", warnings=[])])
    with pytest.raises(structure_mod.LLMStructuringError):
        structure_mod.structure_document(
            cleaned, settings=Settings(strict_llm=True), llm_enabled=True
        )


def test_anthropic_response_text_handles_dict_block() -> None:
    resp = types.SimpleNamespace(content=[{"text": "from-dict"}])
    assert structure_mod._anthropic_response_text(resp) == "from-dict"


def test_anthropic_response_text_handles_text_attr() -> None:
    resp = types.SimpleNamespace(content=None, text="from-attr")
    assert structure_mod._anthropic_response_text(resp) == "from-attr"


def test_anthropic_response_text_raises_on_malformed_response() -> None:
    resp = types.SimpleNamespace(content=[], text=None)
    with pytest.raises(ValueError):
        structure_mod._anthropic_response_text(resp)
