"""Reusable declarative step model for modal forms.

A form mixes in :class:`SteppedFormMixin` and declares ``steps`` as an
ordered list of :class:`Step` (title, icon, field names). The modal shell
reads this metadata to render the stepper (multi-step) or the completion
meter (single-step) and to lay out the fields, so entity templates carry
no field markup. This is the single source of truth for a form's grouping
and ordering.

See ``docs/brand/brand-guidelines.md`` (Forms section) for the doctrine.
"""

from django.core.exceptions import ImproperlyConfigured


def _col_class(width):
    """Bootstrap column class for a field placed in a multi-column row."""
    if width is None:
        return "col-sm"
    if width == "auto":
        return "col-auto"
    return f"col-sm-{width}"


def _row_cells(item):
    """Normalize one ``Step.fields`` entry into a list of (name, width) cells.

    A plain field name renders full width (a one-cell row). A list / tuple
    renders its members side by side on one row; each member is either a
    field name (equal-width column) or a ``(name, width)`` pair, where width
    is ``"auto"`` or a Bootstrap span (1-12).
    """
    if isinstance(item, str):
        return [(item, None)]
    cells = []
    for sub in item:
        if isinstance(sub, str):
            cells.append((sub, None))
        else:
            cells.append((sub[0], sub[1]))
    return cells


class Step:
    """One group of fields in a modal form.

    ``title``  : translatable label shown in the stepper / section header.
    ``icon``   : Bootstrap icon name without the ``bi-`` prefix.
    ``fields`` : ordered layout entries. Each entry is either a field name
        (rendered full width) or a list of cells rendered side by side on
        one row, where a cell is a field name or a ``(name, width)`` pair
        (width = ``"auto"`` or a Bootstrap span 1-12). Example::

            Step(_("Identity"), "diagram-3", [
                [("icon", "auto"), "name"],   # icon + name on one row
                "parent_scope",
                "description",
            ])
    """

    __slots__ = ("title", "icon", "fields")

    def __init__(self, title, icon, fields):
        self.title = title
        self.icon = icon
        self.fields = tuple(fields)

    def field_names(self):
        """Flat list of every field name in the step, row layout aside."""
        names = []
        for item in self.fields:
            names.extend(name for name, _ in _row_cells(item))
        return names

    def __repr__(self):
        return f"Step({self.title!r}, {self.icon!r}, {self.fields!r})"


class SteppedFormMixin:
    """Declarative grouping / stepping for a Django form.

    Set ``steps`` to a list of :class:`Step`. One step renders single-step
    (with a completion meter); two or more render as a multi-step wizard.
    The declared steps must cover every visible field exactly once; this is
    validated at instantiation so a missing or duplicated field fails loud
    rather than silently dropping from the form.
    """

    steps = []

    #: A step should stay short enough to fit one viewport without scrolling.
    #: Each layout row (a full-width field or one column row) counts as one;
    #: exceeding this raises, forcing the step to be split.
    max_rows_per_step = 7

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.steps:
            self._validate_steps()

    # -- internals ---------------------------------------------------------

    def _visible_field_names(self):
        return [name for name, f in self.fields.items() if not f.widget.is_hidden]

    def _validate_steps(self):
        seen = []
        for step in self.steps:
            for name in step.field_names():
                if name not in self.fields:
                    raise ImproperlyConfigured(
                        f"{type(self).__name__}: step '{step.title}' references "
                        f"unknown field '{name}'."
                    )
                if name in seen:
                    raise ImproperlyConfigured(
                        f"{type(self).__name__}: field '{name}' appears in more "
                        f"than one step."
                    )
                seen.append(name)
            if len(step.fields) > self.max_rows_per_step:
                raise ImproperlyConfigured(
                    f"{type(self).__name__}: step '{step.title}' has "
                    f"{len(step.fields)} layout rows (max {self.max_rows_per_step}); "
                    f"split it so the step fits one viewport without scrolling."
                )
        uncovered = [n for n in self._visible_field_names() if n not in seen]
        if uncovered:
            raise ImproperlyConfigured(
                f"{type(self).__name__}: these visible fields are not assigned to "
                f"any step: {', '.join(uncovered)}."
            )

    # -- public API consumed by the template -------------------------------

    @property
    def is_stepped(self):
        return bool(self.steps)

    @property
    def is_multistep(self):
        return len(self.steps) > 1

    @property
    def modal_size(self):
        """Bootstrap-ish modal width hint consumed by the shell / JS.

        Single-step forms stay compact (``md``); multi-step wizards get a
        wider dialog (``lg``). Non-stepped forms return ``""`` (the default
        width).
        """
        if not self.steps:
            return ""
        return "lg" if self.is_multistep else "md"

    @property
    def required_field_count(self):
        """Number of visible required fields, for the completion meter."""
        return sum(
            1
            for name, f in self.fields.items()
            if f.required and not f.widget.is_hidden
        )

    def iter_steps(self):
        """Yield one dict per step with its rows of bound fields and metadata.

        ``rows`` is a list of rows; each row is a list of cells, and each
        cell is ``{"field": BoundField, "col_class": "col-sm"|...}``. A
        full-width field is simply a one-cell row.
        """
        total = len(self.steps)
        for index, step in enumerate(self.steps):
            rows = []
            bound = []
            for item in step.fields:
                row = []
                for name, width in _row_cells(item):
                    bf = self[name]
                    bound.append(bf)
                    row.append({"field": bf, "col_class": _col_class(width)})
                rows.append(row)
            yield {
                "index": index,
                "number": index + 1,
                "title": step.title,
                "icon": step.icon,
                "rows": rows,
                "fields": bound,
                "required_count": sum(1 for bf in bound if bf.field.required),
                "is_first": index == 0,
                "is_last": index == total - 1,
            }
