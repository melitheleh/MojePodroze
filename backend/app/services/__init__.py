"""Serwisy aplikacyjne: łączą bazę danych (ORM) z regułami z ``app.domain``.

Routery FastAPI są cienkie: walidują wejście (Pydantic), wołają serwis i zwracają wynik.
Reguły biznesowe (np. archiwum tylko do odczytu) są sprawdzane w serwisach, a nie w routerach,
więc obowiązują niezależnie od tego, skąd serwis zostanie wywołany.
"""
