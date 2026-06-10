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


class Step:
    """One group of fields in a modal form.

    ``title``  : translatable label shown in the stepper / section header.
    ``icon``   : Bootstrap icon name without the ``bi-`` prefix.
    ``fields`` : ordered field names that belong to this step.
    """

    __slots__ = ("title", "icon", "fields")

    def __init__(self, title, icon, fields):
        self.title = title
        self.icon = icon
        self.fields = tuple(fields)

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
            for name in step.fields:
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
    def required_field_count(self):
        """Number of visible required fields, for the completion meter."""
        return sum(
            1
            for name, f in self.fields.items()
            if f.required and not f.widget.is_hidden
        )

    def iter_steps(self):
        """Yield one dict per step with its bound fields and metadata."""
        total = len(self.steps)
        for index, step in enumerate(self.steps):
            bound = [self[name] for name in step.fields]
            yield {
                "index": index,
                "number": index + 1,
                "title": step.title,
                "icon": step.icon,
                "fields": bound,
                "required_count": sum(1 for bf in bound if bf.field.required),
                "is_first": index == 0,
                "is_last": index == total - 1,
            }
