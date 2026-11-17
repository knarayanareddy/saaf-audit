"""Strict amount parsing.

Fails closed: anything ambiguous or non-finite raises instead of guessing.
This addresses findings such as "1,234.56" being read as 1.23456, and
float("nan") slipping through comparisons of the form ``abs(a - b) > tol``.
"""
from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

__all__ = ["NumberError", "AmbiguousNumber", "NonFiniteNumber", "parse_amount"]


class NumberError(ValueError):
    """The value is not a usable number."""


class AmbiguousNumber(NumberError):
    """The value could be read in more than one way (e.g. '1,000')."""


class NonFiniteNumber(NumberError):
    """NaN or infinity."""


_NON_FINITE = {"nan", "inf", "infinity"}
_ALLOWED = re.compile(r"^[0-9.,]+$")
_CURRENCY = "€$£"


def parse_amount(value: Any, decimal: Optional[str] = None) -> Decimal:
    """Parse ``value`` into a finite :class:`~decimal.Decimal`.

    ``decimal`` may be ``"."`` or ``","`` to state the locale explicitly. Without it,
    the format is inferred only when that is unambiguous; otherwise
    :class:`AmbiguousNumber` is raised.
    """
    if decimal not in (None, ".", ","):
        raise ValueError("decimal must be '.', ',' or None")
    if isinstance(value, bool) or value is None:
        raise NumberError(f"not a number: {value!r}")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise NonFiniteNumber(str(value))
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise NonFiniteNumber(repr(value))
        return Decimal(repr(value))

    s = str(value).strip()
    for ch in _CURRENCY + "  ":
        s = s.replace(ch, "")
    if not s:
        raise NumberError("empty value")
    if s.lstrip("+-").lower() in _NON_FINITE:
        raise NonFiniteNumber(s)

    sign = ""
    if s[0] in "+-":
        sign, s = s[0], s[1:]
    if not _ALLOWED.match(s):
        raise NumberError(f"unreadable number: {value!r}")

    if decimal is not None:
        thousands = "," if decimal == "." else "."
        if s.count(decimal) > 1:
            raise NumberError(f"more than one decimal separator: {value!r}")
        normalized = s.replace(thousands, "").replace(decimal, ".")
    else:
        normalized = _infer(s, value)

    try:
        out = Decimal(sign + normalized)
    except InvalidOperation as e:
        raise NumberError(f"unreadable number: {value!r}") from e
    if not out.is_finite():
        raise NonFiniteNumber(str(value))
    return out


def _infer(s: str, original: Any) -> str:
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        last = max(s.rfind("."), s.rfind(","))
        dec = s[last]
        thou = "," if dec == "." else "."
        if s.count(dec) != 1 or s.find(thou) > last or s.rfind(thou) > last:
            raise AmbiguousNumber(f"mixed separators in odd order: {original!r}")
        return s.replace(thou, "").replace(dec, ".")
    if has_dot or has_comma:
        sep = "." if has_dot else ","
        if s.count(sep) > 1:
            groups = s.split(sep)[1:]
            if all(len(g) == 3 for g in groups):
                return s.replace(sep, "")  # repeated separator can only be thousands
            raise AmbiguousNumber(f"irregular grouping: {original!r}")
        before, after = s.split(sep)
        if len(after) == 3 and 1 <= len(before) <= 3 and before != "0":
            raise AmbiguousNumber(
                f"{original!r} is either a thousands group or a decimal; "
                "state the locale explicitly"
            )
        return before + "." + after
    return s
