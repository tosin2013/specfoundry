"""Runner interface (constitution VI, PRD F10). 003 adds a Kelos backend beside jobs.py."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Handle:
    kind: str        # worker | grader | publisher
    namespace: str
    name: str        # Job name
    own_namespace: bool = True  # delete() removes the whole namespace


class Runner(ABC):
    @abstractmethod
    def submit(self, kind: str, namespace: str, name: str, manifest: str, own_namespace: bool = True) -> Handle: ...

    @abstractmethod
    def wait(self, handle: Handle, timeout: int) -> str:
        """Complete | Failed | DeadlineExceeded | Timeout"""

    @abstractmethod
    def collect(self, handle: Handle) -> str:
        """Return the unit's stdout (where the result frame lives)."""

    @abstractmethod
    def status(self, handle: Handle) -> dict: ...

    @abstractmethod
    def delete(self, handle: Handle) -> None: ...
