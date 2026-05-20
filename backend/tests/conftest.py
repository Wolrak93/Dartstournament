"""Shared test utilities for the DartsTournament backend test suite.

These are plain helper functions (not pytest fixtures) so that test modules
can import them directly:

    from conftest import _miss, make_visit
"""

from __future__ import annotations

from app.services.match import Dart, DartBand


def _miss() -> Dart:
    """Return a dart that missed the board entirely."""
    return Dart(score=0, band=DartBand.MISS, number=0)


def make_visit(d1: Dart, d2: Dart, d3: Dart) -> list[Dart]:
    """Build a three-dart list for use with process_visit / detect_events."""
    return [d1, d2, d3]
