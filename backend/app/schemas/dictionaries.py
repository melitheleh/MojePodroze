from app.schemas.common import ApiModel, EnumOption


class DictionaryEntryOut(ApiModel):
    id: int
    code: str
    name: str


class DictionariesOut(ApiModel):
    """Wszystkie listy wyboru potrzebne w formularzach GUI, w jednym zapytaniu."""

    trip_characters: list[DictionaryEntryOut]
    transport_means: list[DictionaryEntryOut]
    expense_categories: list[DictionaryEntryOut]
    trip_statuses: list[EnumOption]
    trip_types: list[EnumOption]
    place_kinds: list[EnumOption]
    sections: list[EnumOption]
    currencies: list[EnumOption]
