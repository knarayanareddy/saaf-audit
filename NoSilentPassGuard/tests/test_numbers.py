from decimal import Decimal

import pytest

from no_silent_pass import AmbiguousNumber, NonFiniteNumber, NumberError, parse_amount


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,234.56", "1234.56"),   # US format, was read as 1.23456 in the audited parser
        ("1.234,56", "1234.56"),   # EU format
        ("€ 12,50", "12.50"),
        ("1234", "1234"),
        ("0.125", "0.125"),
        ("1,234,567", "1234567"),
        ("-3,5", "-3.5"),
        (7, "7"),
        (2.5, "2.5"),
    ],
)
def test_unambiguous_values(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["1,000", "1.000", "12,345"])
def test_ambiguous_values_are_rejected_without_locale(raw):
    with pytest.raises(AmbiguousNumber):
        parse_amount(raw)


def test_locale_resolves_ambiguity():
    assert parse_amount("1,000", decimal=".") == Decimal("1000")
    assert parse_amount("1,000", decimal=",") == Decimal("1.000")


@pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "Infinity", float("nan"), float("inf")])
def test_non_finite_is_rejected(raw):
    with pytest.raises(NonFiniteNumber):
        parse_amount(raw)


@pytest.mark.parametrize("raw", ["", "  ", None, True, "12abc", "1.2.3,4,5", ","])
def test_garbage_is_rejected(raw):
    with pytest.raises(NumberError):
        parse_amount(raw)
