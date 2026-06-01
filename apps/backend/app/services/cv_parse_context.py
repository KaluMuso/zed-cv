"""Debug context for CV parse failures (Sentry breadcrumbs)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CVParseDebugContext:
    file_size: int | None = None
    page_count: int | None = None
    extracted_text_length: int | None = None
    llm_response_length: int | None = None

    def as_breadcrumb_data(self) -> dict[str, int]:
        out: dict[str, int] = {}
        if self.file_size is not None:
            out["file_size"] = self.file_size
        if self.page_count is not None:
            out["page_count"] = self.page_count
        if self.extracted_text_length is not None:
            out["extracted_text_length"] = self.extracted_text_length
        if self.llm_response_length is not None:
            out["llm_response_length"] = self.llm_response_length
        return out
