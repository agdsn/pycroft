import typing as t


class ButtonArgs(t.TypedDict):
    href: str
    title: str
    btn_class: str
    tooltip: str
    icon: list[str]
