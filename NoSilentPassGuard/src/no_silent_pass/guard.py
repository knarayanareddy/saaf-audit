"""The core guard: a three-state verdict where PASS has to be earned."""
from __future__ import annotations

import enum
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .numbers import NumberError, parse_amount

__all__ = ["Verdict", "Guard"]


def _blank(value: Any) -> bool:
    """None and empty or whitespace-only text are an empty cell, not a value (``str(None)`` is "None")."""
    return value is None or str(value).strip() == ""


class Verdict(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_ASSESSED = "NOT_ASSESSED"

    @property
    def exit_code(self) -> int:
        return {"PASS": 0, "FAIL": 1, "NOT_ASSESSED": 2}[self.value]


class Guard:
    """Collects what was assessed, what was skipped and which checks actually ran.

    Rules (fail closed):
      * FAIL     - at least one executed check found a violation.
      * PASS     - no violation, at least ``min_checks`` checks ran, coverage of the
                   input items is at least ``min_coverage``, and nothing was recorded
                   as "could not assess".
      * NOT_ASSESSED - everything else, including "nothing was detected" and
                   "no input at all".
    """

    def __init__(
        self,
        name: str,
        min_coverage: float = 1.0,
        min_checks: int = 1,
        decimal: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> None:
        self.name = name
        # Stamped into the report so the gate can tell this run's report from an old one. In CI set the same
        # NO_SILENT_PASS_RUN_ID (for example the pipeline run number) for the tool and for ``gate``.
        self.run_id = run_id or os.environ.get("NO_SILENT_PASS_RUN_ID") or uuid.uuid4().hex
        self.min_coverage = min_coverage
        self.min_checks = min_checks
        self.decimal = decimal
        self._items: Dict[str, str] = {}  # item -> "assessed" | "skipped"
        self._skip_reasons: List[Tuple[str, str]] = []
        self._reasons: List[str] = []
        self._checks: List[Dict[str, Any]] = []
        self._claims_granted: List[str] = []
        self._claims_denied: List[str] = []

    # -- context manager: an unhandled error must never read as success ---------
    def __enter__(self) -> "Guard":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.not_assessed(f"unhandled {exc_type.__name__}: {exc}")
        return False  # never swallow the exception

    # -- coverage ledger ----------------------------------------------------------
    def mark_assessed(self, item: Any) -> None:
        """Record that ``item`` was fully assessed (no-op if it was already skipped)."""
        self._items.setdefault(str(item), "assessed")

    def skip(self, item: Any, reason: str) -> None:
        """Record that ``item`` could not be assessed. Lowers coverage."""
        self._items[str(item)] = "skipped"
        self._skip_reasons.append((str(item), reason))

    def not_assessed(self, reason: str, item: Any = None) -> None:
        """Record a reason the result cannot be trusted as a pass."""
        self._reasons.append(reason if item is None else f"{item}: {reason}")
        if item is not None:
            self.skip(item, reason)

    # -- checks ---------------------------------------------------------------------
    def check(self, name: str, ok: Any, item: Any = None, detail: str = "") -> bool:
        """Record an executed check. ``ok`` must be a real bool, never None."""
        if not isinstance(ok, bool):
            self.not_assessed(f"check '{name}' returned {ok!r}, not a bool", item)
            return False
        self._checks.append(
            {"name": name, "ok": ok, "item": None if item is None else str(item), "detail": detail}
        )
        return ok

    def within(self, name: str, a: Any, b: Any, tol: Any, item: Any = None) -> Optional[bool]:
        """``|a - b| <= tol`` with finite, parsed inputs. NaN/inf/ambiguous -> not assessed."""
        da = self.require_finite(a, f"{name}.a", item)
        db = self.require_finite(b, f"{name}.b", item)
        dt = self.require_finite(tol, f"{name}.tolerance", item)
        if da is None or db is None or dt is None:
            return None
        if dt < 0:
            self.not_assessed(f"{name}: negative tolerance {dt}", item)
            return None
        return self.check(name, abs(da - db) <= dt, item, f"|{da} - {db}| <= {dt}")

    # -- input sanity ---------------------------------------------------------------
    def require_finite(self, value: Any, name: str, item: Any = None) -> Optional[Decimal]:
        try:
            return parse_amount(value, decimal=self.decimal)
        except NumberError as e:
            self.not_assessed(f"{name}: {e}", item)
            return None

    def require_present(self, row: Mapping[str, Any], key: str, item: Any = None) -> Any:
        value = row.get(key)
        if _blank(value):
            self.not_assessed(f"required field '{key}' missing", item)
            return None
        return value

    def require_unique(
        self, row: Mapping[str, Any], aliases: Sequence[str], field: str, item: Any = None
    ) -> Any:
        """Return the value of ``field`` or record why it cannot be trusted.

        Fails closed when no alias is present, or when several alias columns hold
        different values (the "decoy column" pattern).
        """
        present = {k: row[k] for k in aliases if k in row and not _blank(row[k])}
        if not present:
            self.not_assessed(f"no column for '{field}' (tried {list(aliases)})", item)
            return None

        def norm(v: Any) -> Any:
            try:
                return parse_amount(v, decimal=self.decimal)
            except NumberError:
                return str(v).strip()

        if len({norm(v) for v in present.values()}) > 1:
            self.not_assessed(
                f"ambiguous '{field}': columns {sorted(present)} disagree", item
            )
            return None
        return next(iter(present.values()))

    # -- labels ---------------------------------------------------------------------
    def claim(self, label: str, requires: Iterable[str]) -> bool:
        """Grant a label such as 'verified' only if every required check ran and passed."""
        by_name: Dict[str, List[bool]] = {}
        for c in self._checks:
            by_name.setdefault(c["name"], []).append(c["ok"])
        for req in requires:
            results = by_name.get(req)
            if not results:
                self.not_assessed(f"claim '{label}' unsupported: check '{req}' never ran")
                self._claims_denied.append(label)
                return False
            if not all(results):
                self._claims_denied.append(label)
                return False
        self._claims_granted.append(label)
        return True

    # -- verdict --------------------------------------------------------------------
    @property
    def coverage(self) -> float:
        if not self._items:
            return 0.0
        assessed = sum(1 for s in self._items.values() if s == "assessed")
        return assessed / len(self._items)

    def _all_reasons(self) -> List[str]:
        reasons = list(self._reasons)
        if not self._items:
            reasons.append("no input items were assessed")
        elif self.coverage < self.min_coverage:
            reasons.append(
                f"coverage {self.coverage:.0%} is below the required {self.min_coverage:.0%}"
            )
        if len(self._checks) < self.min_checks:
            reasons.append(
                f"only {len(self._checks)} check(s) ran, at least {self.min_checks} required"
            )
        return reasons

    def verdict(self) -> Verdict:
        if any(not c["ok"] for c in self._checks):
            return Verdict.FAIL
        if self._all_reasons():
            return Verdict.NOT_ASSESSED
        return Verdict.PASS

    def report(self) -> Dict[str, Any]:
        v = self.verdict()
        return {
            "schema_version": 1,
            "guard": self.name,
            "run_id": self.run_id,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "verdict": v.value,
            "exit_code": v.exit_code,
            "coverage": round(self.coverage, 4),
            "min_coverage": self.min_coverage,
            "min_checks": self.min_checks,
            "items_total": len(self._items),
            "items_skipped": [{"item": i, "reason": r} for i, r in self._skip_reasons],
            "checks_run": len(self._checks),
            "checks_failed": [c for c in self._checks if not c["ok"]],
            "not_assessed_reasons": self._all_reasons(),
            "claims_granted": self._claims_granted,
            "claims_denied": self._claims_denied,
        }

    def write(self, path: str) -> Verdict:
        """Write the report in one step: a crash never leaves a half-written file behind."""
        tmp = f"{path}.tmp-{os.getpid()}"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.report(), fh, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return self.verdict()
