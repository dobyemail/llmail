from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol


@dataclass
class Message:
    body: Any
    headers: Dict[str, Any] = field(default_factory=dict)


class Processor(Protocol):
    def __call__(self, msg: Message) -> Message:  # noqa: D401
        """Transform or handle a message and return it (or a new one)."""
        ...


class Endpoint(Protocol):
    def send(self, msg: Message) -> None:
        ...


@dataclass
class Route:
    source: Callable[[], Message]
    processors: List[Processor]
    sink: Endpoint

    def run_once(self) -> None:
        msg = self.source()
        for p in self.processors:
            msg = p(msg)
        self.sink.send(msg)


class Router:
    def __init__(self):
        self._routes: List[Route] = []
        self._endpoints: Dict[str, Endpoint] = {}

    def register_endpoint(self, name: str, ep: Endpoint) -> None:
        self._endpoints[name] = ep

    def endpoint(self, name: str) -> Optional[Endpoint]:
        return self._endpoints.get(name)

    def add_route(self, route: Route) -> None:
        self._routes.append(route)

    def run(self, once: bool = True) -> None:
        # Simple synchronous runner for now
        for r in self._routes:
            r.run_once()
