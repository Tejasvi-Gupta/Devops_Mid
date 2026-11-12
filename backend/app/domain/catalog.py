"""Trusted tool catalog shared with the Windows agent."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import Settings, find_catalog_path
from app.domain.versions import version_satisfies


class CatalogVersion(BaseModel):
    version: str
    winget_id: str
    url: str
    sha256: str = Field(min_length=64, max_length=64)
    requires_elevation: bool
    requires_reboot: bool
    acknowledgements: list[str]
    impact: str


class CatalogTool(BaseModel):
    id: str
    display_name: str
    strategy: str
    versions: list[CatalogVersion] = []
    notes: str = ""


class ToolCatalog(BaseModel):
    catalog_version: int
    integrity: str
    captured_from: str
    tools: list[CatalogTool]

    def tool(self, tool_id: str) -> CatalogTool | None:
        return next((item for item in self.tools if item.id == tool_id), None)

    def version(self, tool_id: str, version: str) -> CatalogVersion | None:
        tool = self.tool(tool_id)
        if not tool:
            return None
        return next((item for item in tool.versions if item.version == version), None)

    def matching_versions(self, tool_id: str, constraint: str) -> list[CatalogVersion]:
        tool = self.tool(tool_id)
        if not tool:
            return []
        return [item for item in tool.versions if version_satisfies(item.version, constraint)]

    def newest_match(self, tool_id: str, constraint: str) -> CatalogVersion | None:
        matches = self.matching_versions(tool_id, constraint)
        if not matches:
            return None
        return sorted(matches, key=lambda item: [int(part) for part in item.version.split(".")])[-1]


@lru_cache
def load_catalog(path: str) -> ToolCatalog:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ToolCatalog.model_validate(payload)


def get_catalog(settings: Settings) -> ToolCatalog:
    return load_catalog(str(find_catalog_path(settings)))
