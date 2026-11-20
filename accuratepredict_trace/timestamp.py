"""T: Timestamped.

Every prediction is written to an append-only log before the event starts.
A later update (new odds, a confirmed line up) is a new version, never an
edit. Each record carries the SHA-256 hash of the record before it, so any
change to history breaks the chain and `verify()` reports where.

The prediction that counts for settlement is the last version published
before kick off. Anything published after kick off stays visible in the
history but can never change the settled record.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional

GENESIS = "0" * 64


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps must carry a UTC offset: %r" % ts)
    return dt


@dataclass
class PredictionRecord:
    fixture_id: str
    kickoff: str                      # ISO 8601 with offset
    published_at: str                 # ISO 8601 with offset
    market: str                       # e.g. "1X2", "OU2.5"
    selection: str                    # e.g. "home", "over"
    probability: float
    model_version: str
    inputs_fetched_at: Dict[str, str] = field(default_factory=dict)
    version: int = 0
    prev_hash: str = GENESIS
    hash: str = ""

    def payload(self) -> str:
        d = asdict(self)
        d.pop("hash")
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        return hashlib.sha256(self.payload().encode("utf-8")).hexdigest()


class PredictionLog:
    """Append-only JSON Lines log of prediction versions."""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.records: List[PredictionRecord] = []
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.records.append(PredictionRecord(**json.loads(line)))

    def publish(self, rec: PredictionRecord) -> PredictionRecord:
        if not 0.0 < rec.probability < 1.0:
            raise ValueError("probability must be strictly between 0 and 1")
        for ts in [rec.kickoff, rec.published_at] + list(rec.inputs_fetched_at.values()):
            _parse(ts)
        for name, ts in rec.inputs_fetched_at.items():
            if _parse(ts) > _parse(rec.published_at):
                raise ValueError("input %r was fetched after publication" % name)
        rec.version = 1 + sum(1 for r in self.records if r.fixture_id == rec.fixture_id)
        rec.prev_hash = self.records[-1].hash if self.records else GENESIS
        rec.hash = rec.compute_hash()
        self.records.append(rec)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(rec), sort_keys=True) + "\n")
        return rec

    def history(self, fixture_id: str) -> List[PredictionRecord]:
        return [r for r in self.records if r.fixture_id == fixture_id]

    def version_at(self, fixture_id: str, when: str) -> Optional[PredictionRecord]:
        """The version that was public at `when`."""
        t = _parse(when)
        live = [r for r in self.history(fixture_id) if _parse(r.published_at) <= t]
        return live[-1] if live else None

    def settled_version(self, fixture_id: str) -> Optional[PredictionRecord]:
        """The last version published before kick off: the one that counts."""
        hist = self.history(fixture_id)
        return self.version_at(fixture_id, hist[0].kickoff) if hist else None

    def verify(self) -> List[str]:
        """Return a list of problems; an empty list means the chain is intact."""
        problems, prev = [], GENESIS
        for i, r in enumerate(self.records):
            if r.prev_hash != prev:
                problems.append("record %d: chain broken (prev_hash mismatch)" % i)
            if r.compute_hash() != r.hash:
                problems.append("record %d: contents changed after publication" % i)
            prev = r.hash
        return problems
