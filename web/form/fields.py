# Copyright (c) 2026 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import annotations
from textwrap import dedent

import json
from datetime import date, datetime
import typing as t

from markupsafe import escape, Markup
from wtforms import Field
from wtforms_widgets.widgets import BootstrapStandardDecorator


DEFAULT_SENTINEL = "__default__"


@BootstrapStandardDecorator
def render_date_or_default(field: DateOrDefaultField, **kwargs: t.Any) -> Markup:
    """Toggle between a caller-defined default and an explicit date.

    Requires Datastar on the page for the toggle reactivity.
    """
    s = field.label.field_id

    if field.raw_data is not None:
        # error recovery
        raw = field.raw_data[0] if field.raw_data else ""
        use_default = raw == "__default__"
        date_iso = "" if use_default else raw
    else:
        # Initial rendering
        use_default = field.data is None
        date_iso = field.data.isoformat() if field.data else ""

    # date_iso = field.data.isoformat() if field.data else ""
    # use_default = field.data is None
    signals = escape(json.dumps({s: {"default": use_default, "date": date_iso}}))
    default_label = escape(field.default_label)
    date_label = escape(field.date_label)
    name = escape(field.name)
    field_id = escape(kwargs.get("id", field.id))
    posted = "" if use_default else date_iso

    return Markup(
        dedent(f"""
            <div data-signals="{signals}">
              <div class="d-flex align-items-center gap-1"
                   role="group"
                   aria-label="{escape(field.label.text) if field.label else ""}"
              >
                <button type="button"
                        class="btn border border-secondary-subtle rounded-1
                               flex-shrink-0 focus-ring focus-ring-primary"
                        data-class:bg-secondary-subtle="${s}.default"
                        data-class:text-body-emphasis="${s}.default"
                        data-class:text-body-secondary="!${s}.default"
                        data-on:click="${s}.default = true"
                        data-attr:aria-pressed="${s}.default">
                  {default_label}
                </button>

                <button type="button"
                        class="btn border border-secondary-subtle rounded-1
                               flex-shrink-0 focus-ring focus-ring-primary"
                        data-class:bg-secondary-subtle="!${s}.default"
                        data-class:text-body-emphasis="!${s}.default"
                        data-class:text-body-secondary="${s}.default"
                        data-on:click="${s}.default = false"
                        data-attr:aria-pressed="!${s}.default">
                  {date_label}
                </button>
                <input type="text" class="form-control" id="{field_id}"
                       value="{escape(date_iso)}"
                       data-date-format="yyyy-mm-dd"
                       data-date-language="de"
                       data-provide="datepicker"
                       data-show="!${s}.default"
                       data-bind:{s}.date
                       data-on:change="${s}.date = evt.target.value"
                       data-on:input="${s}.date = evt.target.value"
                       />

                <input type="hidden" name="{name}"
                       value="{escape(posted)}"
                       data-attr:value="${s}.default ? '{DEFAULT_SENTINEL}' : ${s}.date" />
              </div>
            </div>
        """)
    )


class DateOrDefaultField(Field):
    """A date field with a toggle for a caller-defined default."""

    data: date | None
    default_label: Markup | str
    date_label: Markup | str

    widget = render_date_or_default

    def __init__(
        self,
        label: t.Any = None,
        validators: t.Any = None,
        *,
        default_label: t.Any,
        date_label: t.Any,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(str(label) if label else None, validators, **kwargs)
        self.default_label = default_label
        self.date_label = date_label

    @t.override
    def process_data(self, value: t.Any) -> None:
        if value is None:
            self.data = None
        elif isinstance(value, datetime):
            self.data = value.date()
        elif isinstance(value, date):
            self.data = value
        else:
            raise TypeError(f"Expected date | datetime | None, got {type(value)!r}")

    @t.override
    def process_formdata(self, valuelist: list[str]) -> None:
        if not valuelist or not valuelist[0]:
            raise ValueError("Date must be set.")
        if valuelist[0] == DEFAULT_SENTINEL:
            self.data = None
            return
        try:
            self.data = date.fromisoformat(valuelist[0])
        except ValueError as e:
            raise ValueError("Not a valid date.") from e
