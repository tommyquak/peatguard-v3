"""SBAS interferometric pair selection.

Constructs an optimal network of interferogram pairs from a temporal
stack of SAR acquisitions. The SBAS (Small BAseline Subset) approach
connects acquisitions with short temporal and perpendicular baselines
to maximize coherence while maintaining network redundancy for
time-series inversion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class InSARPair:
    """An interferometric pair definition."""

    reference_date: str
    secondary_date: str
    temporal_baseline_days: int
    perpendicular_baseline_m: Optional[float] = None

    @property
    def pair_id(self) -> str:
        return f"{self.reference_date}_{self.secondary_date}"


def select_sbas_pairs(
    dates: list[str],
    max_temporal_baseline_days: int = 48,
    max_connections: int = 4,
) -> list[InSARPair]:
    """Select interferogram pairs using the SBAS connection strategy.

    For each acquisition, connects to up to max_connections forward-looking
    acquisitions within the temporal baseline limit. This produces a
    well-connected network suitable for MintPy SBAS inversion.

    Args:
        dates: List of acquisition dates in YYYY-MM-DD format, sorted.
        max_temporal_baseline_days: Maximum temporal gap between pairs.
        max_connections: Maximum number of forward connections per date.

    Returns:
        List of InSARPair objects defining the interferogram network.
    """
    sorted_dates = sorted(dates)
    parsed = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_dates]
    pairs = []

    for i, ref_date in enumerate(parsed):
        connections = 0
        for j in range(i + 1, len(parsed)):
            sec_date = parsed[j]
            baseline = (sec_date - ref_date).days

            if baseline > max_temporal_baseline_days:
                break

            pairs.append(
                InSARPair(
                    reference_date=sorted_dates[i],
                    secondary_date=sorted_dates[j],
                    temporal_baseline_days=baseline,
                )
            )
            connections += 1
            if connections >= max_connections:
                break

    logger.info(
        "Selected %d SBAS pairs from %d acquisitions (max baseline: %d days)",
        len(pairs),
        len(dates),
        max_temporal_baseline_days,
    )
    return pairs


def select_sequential_pairs(dates: list[str]) -> list[InSARPair]:
    """Select consecutive-only pairs (simpler but less redundant).

    Each acquisition is paired only with its immediate temporal neighbor.
    This matches the original PeatGuard pipeline behavior but produces
    a minimal network without redundancy for error correction.

    Args:
        dates: List of acquisition dates in YYYY-MM-DD format, sorted.

    Returns:
        List of consecutive InSARPair objects.
    """
    sorted_dates = sorted(dates)
    parsed = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_dates]
    pairs = []

    for i in range(len(sorted_dates) - 1):
        baseline = (parsed[i + 1] - parsed[i]).days
        pairs.append(
            InSARPair(
                reference_date=sorted_dates[i],
                secondary_date=sorted_dates[i + 1],
                temporal_baseline_days=baseline,
            )
        )

    logger.info("Selected %d sequential pairs from %d acquisitions", len(pairs), len(sorted_dates))
    return pairs


def network_summary(pairs: list[InSARPair]) -> dict:
    """Compute summary statistics for an interferogram network.

    Args:
        pairs: List of InSARPair objects.

    Returns:
        Dict with network statistics.
    """
    if not pairs:
        return {"num_pairs": 0}

    baselines = [p.temporal_baseline_days for p in pairs]
    all_dates = set()
    for p in pairs:
        all_dates.add(p.reference_date)
        all_dates.add(p.secondary_date)

    return {
        "num_pairs": len(pairs),
        "num_dates": len(all_dates),
        "min_baseline_days": min(baselines),
        "max_baseline_days": max(baselines),
        "mean_baseline_days": sum(baselines) / len(baselines),
        "redundancy": len(pairs) / max(len(all_dates) - 1, 1),
    }
