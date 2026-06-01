"""Unit tests for tolerant LLM JSON repair."""
import pytest

from app.lib.llm_json import repair_llm_json


class TestRepairLlmJson:
    def test_strict_json(self):
        assert repair_llm_json('{"full_name": "Jane"}') == {"full_name": "Jane"}

    def test_markdown_fence(self):
        raw = '```json\n{"skills": ["python"]}\n```'
        assert repair_llm_json(raw) == {"skills": ["python"]}

    def test_trailing_comma_object(self):
        raw = '{"full_name": "Jane",}'
        assert repair_llm_json(raw) == {"full_name": "Jane"}

    def test_trailing_comma_array(self):
        raw = '{"skills": ["a", "b",], "full_name": "x"}'
        assert repair_llm_json(raw) == {"skills": ["a", "b"], "full_name": "x"}

    def test_greedy_outer_brace_extraction(self):
        raw = 'Here is the JSON:\n{"confidence": 0.9, "skills": []}\nThanks!'
        assert repair_llm_json(raw) == {"confidence": 0.9, "skills": []}

    def test_returns_none_on_garbage(self):
        assert repair_llm_json("not json at all") is None
