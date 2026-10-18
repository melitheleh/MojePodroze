"""Kalkulator walut (narzędzie pomocnicze na ekranie głównym, niczego nie zapisuje)."""

from decimal import Decimal

from app.domain.common import ZERO, round_half_up


def convert_to_pln(amount: Decimal, rate: Decimal) -> Decimal:
    """Przelicza kwotę w walucie obcej na PLN po kursie średnim, z zaokrągleniem do groszy."""
    if amount < ZERO:
        raise ValueError("Kwota nie może być ujemna.")
    if rate <= ZERO:
        raise ValueError("Kurs musi być dodatni.")
    return round_half_up(amount * rate)
