"""Moduł domenowy: cała logika biznesowa aplikacji.

Zasada: ten pakiet NIE importuje FastAPI, SQLAlchemy ani niczego z ``app.api``, ``app.db``,
``app.services``. Dzięki temu da się go testować jednostkowo i mutacyjnie bez bazy i sieci.
"""
