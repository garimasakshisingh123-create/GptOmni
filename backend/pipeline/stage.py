"""
backend/pipeline/stage.py
BaseStage abstract class that all 9 pipeline stages inherit from.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from backend.models.pipeline_state import PipelineState, StageLog

logger = logging.getLogger(__name__)


class BaseStage(ABC):
    stage_number: int
    stage_name: str

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """Execute this stage. Reads from state, writes results back to state."""
        ...

    def log(
        self,
        state: PipelineState,
        status: str,
        summary: str,
        detail: Optional[dict] = None,
        started_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ) -> StageLog:
        """Append a StageLog entry to state.stage_logs and return it."""
        completed_at = datetime.utcnow()
        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        log_entry = StageLog(
            stage_number=self.stage_number,
            stage_name=self.stage_name,
            status=status,
            started_at=started_at or completed_at,
            completed_at=completed_at,
            summary=summary,
            detail=detail or {},
            error=error,
            duration_ms=duration_ms,
        )
        state.stage_logs.append(log_entry)
        logger.info(f"[Stage {self.stage_number}] {self.stage_name}: {summary}")
        return log_entry

    def load_prompt(self, path: str) -> str:
        """Load a prompt file from the prompts/ directory."""
        import os
        # Resolve relative to project root (two levels up from pipeline/)
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_path = os.path.join(base, path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
