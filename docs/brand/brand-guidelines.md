# Brand guidelines - Cairn

> Cairn is an open source GRC (Governance, Risk, Compliance) platform built
> for CISOs, DPOs, auditors and compliance officers. This document defines
> the visual system of the product. It is meant for developers shipping CSS
> classes as much as for designers iterating on screens.

---

## Table of contents

1. [About the name](#about-the-name)
2. [Logo](#logo)
3. [Colors](#colors)
4. [Typography](#typography)
5. [Spacing, radii, shadows](#spacing-radii-shadows)
6. [Iconography](#iconography)
7. [Components](#components)
8. [Forms](#forms)
9. [Motion and transitions](#motion-and-transitions)
10. [Accessibility](#accessibility)
11. [Voice and tone](#voice-and-tone)
12. [Assets and files](#assets-and-files)

---

## About the name

**Cairn**, from Gaelic _càrn_: a deliberate stack of stones built to mark a
safe path through the mountains. Where the trail becomes uncertain, the
cairn reassures: someone has been here before you, you are on the right
path.

The metaphor fits compliance. A CISO facing NIS 2, a DPO facing GDPR, an
auditor facing ISO 27001 - all of them look for the cairns that mark an
otherwise complex path. Cairn (the product) is that marking.

**Positioning**

- Audit-grade: gravitas, rigour, traceability. No mascot, no marketing
  gradient, no superlative.
- Open source by choice: readable code, paid-down design debt, no
  proprietary magic.
- Bilingual by construction: every label is translatable; the name reads
  the same in French and English (`/kɛʁn/` ~ `/kɛərn/`).

**Pronunciation**

- FR: _kèrn_, like the typography term "kern".
- EN: _cairn_, single syllable, silent `i`.

---

## Logo

The Cairn logo is a **responsive two-variant system** sharing a common bowl
(the cup opening upward) but with an inner element that changes based on
render size. Like a real cairn seen from far away (silhouette) and then up
close (distinct stones).

### The two variants

| Variant | When | File |
| --- | --- | --- |
| **Primary** - Stepped cairn | ≥ 24 px: sidebar brand, header, splash, high-res app icon | [`mark.svg`](./mark.svg) |
| **Small** - Peak silhouette | ≤ 22 px: favicon, browser tab, low-res OS icon, dense lists | [`mark-sm.svg`](./mark-sm.svg) |

> Rule: under 24 px, switch to `mark-sm`. Above, stay on `mark`.
> 32 px belongs to the primary (where it starts to shine).

### Wordmark

`CAIRN` in Inter 700, tight tracking at `-0.04em`, followed by a small navy
dot baseline-aligned - the silent signature of a validated stamp.

File: [`wordmark.svg`](./wordmark.svg).

### Lock-up

Mark on the left, wordmark on the right, gap between them: `1.5x` the
mark height.

```text
  ╭───╮
  │ ▲ │   CAIRN.
  ╰───╯
```

### Clear space

No graphic element shall enter a zone equivalent to **50% of the mark
height** around the logo. At a 32 px mark, that means 16 px of minimum
margin all around.

### Don'ts

- ❌ Do not reduce the primary variant under 24 px. Use `mark-sm` instead.
- ❌ Do not place the mark on a background that makes it unreadable (e.g.
  navy on navy). Prefer white, cream, or sufficiently contrasted ink.
- ❌ Do not invert the colours (the bowl stays white on navy, never the
  other way around).
- ❌ Do not change the internal proportions, do not stretch, do not rotate.
- ❌ Do not fill the bowl with another colour that would clash with the
  navy primary.

---

## Colors

A single identity colour (navy), monochrome neutrals for everything else,
and three semantic colours **reserved for status only**.

### Identity palette

| Token | Hex | Usage |
| --- | --- | --- |
| `--accent` | `#1E3A8A` | Navy. The identity colour. Logo, active link, focus ring, primary CTA. |
| `--accent-hover` | `#1E2E5E` | Deeper navy. `hover` / `active` state of primary. |
| `--accent-soft` | `#EEF2FF` | Pale lavender. Active chip backgrounds, info alerts, subtle hovers. |
| `--accent-glow` | `rgba(99,102,241,.18)` | Focus ring outline. |

### Neutrals (canvas and surfaces)

| Token | Hex | Usage |
| --- | --- | --- |
| `--bg-page` | `#FAFAFA` | Application page background. |
| `--surface` / `--surface-raised` | `#FFFFFF` | Background of cards, modals, drawer, dropdowns. |
| `--surface-muted` | `#FAFAFA` | Table row hover, secondary zone background. |
| `--surface-subtle` | `#F5F5F5` | Disabled state, visual separators. |
| `--text-primary` | `#18181B` | Titles, values, main table text. |
| `--text-secondary` | `#52525B` | Secondary labels, meta information. |
| `--text-muted` | `#A1A1AA` | Placeholders, eyebrows, counters, ancillary info. |
| `--border-light` | `rgba(0,0,0,.08)` | Card, input, sidebar borders. |
| `--border-subtle` | `rgba(0,0,0,.05)` | Separators inside lists. |
| `--border-hairline` | `rgba(0,0,0,.03)` | Intra-table lines. |

### Semantic (status only)

| Token | Hex | Usage |
| --- | --- | --- |
| `--success` | `#16A34A` | Approved, compliant, complete. Badge, alert, status icon. |
| `--success-soft` | `#F0FDF4` | Success alert / chip background. |
| `--warning` | `#D97706` | Pending, to review, partially compliant. |
| `--warning-soft` | `#FFFBEB` | Warning alert / chip background. |
| `--danger` | `#DC2626` | Critical, non-compliant, expired, rejected. |
| `--danger-soft` | `#FEF2F2` | Danger alert / chip background. |
| `--info` | `#0891B2` | Neutral information. |
| `--info-soft` | `#ECFEFF` | Info alert / chip background. |

> Rule: no semantic colour is used as decoration. If an element is not a
> status, it takes navy or a neutral.

### Dark mode (warm-charcoal)

Dark mode flips automatically via `[data-bs-theme="dark"]`. The rule:
warm-charcoal, never true black (#000), off-white text never pure white.

| Token | Hex |
| --- | --- |
| `--bg-page` | `#0F1011` |
| `--surface` | `#16181B` |
| `--surface-raised` | `#1C1F23` |
| `--text-primary` | `#E4E4E7` |
| `--text-secondary` | `#A1A1AA` |
| `--accent` | `#818CF8` (lighter indigo to carry on dark backgrounds) |

### WCAG 2.2 contrast

| Combination | Ratio | Compliance |
| --- | --- | --- |
| `text-primary #18181B` on `bg-page #FAFAFA` | 16.6:1 | AAA |
| `text-secondary #52525B` on `surface #FFFFFF` | 7.9:1 | AAA |
| `text-muted #A1A1AA` on `surface #FFFFFF` | 2.85:1 | AA for large text only |
| `accent #1E3A8A` on `surface #FFFFFF` | 10.2:1 | AAA |
| `#FFFFFF` on `accent #1E3A8A` (primary CTA) | 10.2:1 | AAA |
| `success #16A34A` on `surface #FFFFFF` | 3.4:1 | AA (UI), AA large text |

> `text-muted` must never carry running text - it is reserved for labels,
> eyebrows and small annotations where the lightness is intentional.

---

## Typography

**One family only**: [Inter](https://rsms.me/inter/). Loaded via Google
Fonts (`Inter:wght@400;500;600;700`). Plan a self-host eventually for
GDPR concerns and perf.

No display font. Large size and tight tracking carry the visual
differentiation.

### Scale

| Element | Size | Weight | Tracking | Line-height |
| --- | --- | --- | --- | --- |
| `h1` | 1.75rem (28 px) | 600 | -0.022em | 1.2 |
| `h2` | 1.375rem (22 px) | 600 | -0.018em | 1.25 |
| `h3` | 1.125rem (18 px) | 600 | -0.012em | 1.35 |
| `h4` | 1rem (16 px) | 600 | normal | 1.4 |
| `h5` | 0.9375rem (15 px) | 600 | normal | 1.4 |
| `h6` (eyebrow) | 0.75rem (12 px) | 600 | +0.04em uppercase | 1.4 |
| `.display-4` | 2.25rem (36 px) | 600 | -0.028em | 1.1 |
| `body` | 0.9375rem (15 px) | 400 | normal | 1.6 |
| `.small` | 0.8125rem (13 px) | 400 | normal | 1.6 |
| `.text-xs` | 0.75rem (12 px) | 400 | normal | 1.6 |

### Rules

- **No UPPERCASE on titles.** Reserved for eyebrows (h6 and `.form-label`)
  as a discreet hierarchy cue.
- **Tight tracking on large titles.** -0.022em on h1, never positive.
- **Wide tracking on eyebrows.** +0.04em to +0.08em, that's what creates
  the "small caps" effect.
- **Tabular numbers everywhere** numbers align vertically (numeric table
  columns, KPIs). Utility class `.tabular-nums`.

---

## Spacing, radii, shadows

### Radii

| Token | Value | Usage |
| --- | --- | --- |
| `--radius-xs` | 0.375rem (6 px) | Badges, small pills, ref pills. |
| `--radius-sm` | 0.5rem (8 px) | Small buttons. |
| `--radius-md` | 0.625rem (10 px) | Buttons, dropdowns. |
| `--radius-lg` | 0.875rem (14 px) | Cards, sidebar, modals, drawer. |
| `--radius-xl` | 1.125rem (18 px) | Hero, large-surface sections. |
| `--radius-2xl` | 1.5rem (24 px) | Very rare, feature blocks. |

### Shadows

Soft depth, never hard offset-block shadows. Hierarchy comes from shadows
AND spacing, not from thick borders.

| Token | Usage |
| --- | --- |
| `--shadow-xs` | Card at rest (very subtle). |
| `--shadow-sm` | Button bubble, light raised element. |
| `--shadow-md` | Card on hover, stat-card hover, dropdown menu. |
| `--shadow-lg` | Drawer, modal, command palette. |
| `--shadow-xl` | Element floating above everything. |

### Spacing

The app uses Bootstrap classes (`mb-3`, `gap-2`, `g-4`, ...) with the
adjustments defined in `templates/base.html`. In direct CSS, prefer `rem`
values consistent with the Bootstrap scale:

`0.25rem` / `0.5rem` / `0.75rem` / `1rem` / `1.25rem` / `1.5rem` / `2rem` / `2.5rem` / `3rem`

---

## Iconography

**[Bootstrap Icons](https://icons.getbootstrap.com/) 1.11.3** is the
single library. No FontAwesome, no Lucide, no mixing.

### Rules

- Always `<i class="bi bi-...">`, and always `aria-hidden="true"` when the
  icon is decorative (next to a text label).
- Default size in em (the icon follows the parent text size). Explicit
  size when the icon is isolated: 1rem for a button, 1.25rem for a header
  button, 1.5rem for an empty state.
- Colour via `color: currentColor` by default. Icons must never force an
  arbitrary colour.

### Recurring system icons

| Concept | Icon | Code |
| --- | --- | --- |
| Approved | check-circle | `bi-check-circle` |
| Pending | clock | `bi-clock` |
| Rejected | x-circle | `bi-x-circle` |
| Risk | exclamation-triangle | `bi-exclamation-triangle` |
| Essential asset | gem | `bi-gem` |
| Framework | journal-check | `bi-journal-check` |
| Search | search | `bi-search` |
| Plus / new | plus-lg | `bi-plus-lg` |
| Edit | pencil | `bi-pencil` |
| Delete | trash | `bi-trash` |

---

## Components

Shared primitives live in `core/templatetags/ui.py` and are documented
live on the `/styleguide` page (visit after login).

### Cards

- `1px` border `--border-light`, radius `--radius-lg`, no shadow by default.
- Clickable cards: add `.card--linked`. Hover lifts the card (-1px
  translateY + `--shadow-md`).
- Padding `1.5rem 1.75rem`.

### Buttons

- Pill shape (`border-radius: 0.625rem`), `1px` border.
- **Primary**: solid navy, white text. Reserved for the principal action
  per context.
- **Outline**: surface background, subtle border, secondary text. Hover:
  cream background.
- **Danger / Success / Warning**: solid semantic background, white text.
  Strictly for actions with that impact (delete, approve, etc.).

### Page header

```django
{% page_header _("Risk register")
   eyebrow=_("Risks")
   icon="exclamation-triangle"
   accent="risks" %}
  <a href="..." class="btn btn-outline-secondary">...</a>
  <a href="..." class="btn btn-primary">
    <i class="bi bi-plus-lg me-1" aria-hidden="true"></i>{% trans "New risk" %}
  </a>
{% endpage_header %}
```

- Without `accent`: plain header, normal h1.
- With `accent="<module>"`: a 2 px coloured line appears under the eyebrow.
  Available modules: `risks`, `compliance`, `assets`, `context`, `reports`,
  `accounts`, `helpers`, `dashboard`.

### Form inputs (token-level)

Inputs use a `1px` border, radius `0.75rem`, padding `0.5625rem 0.875rem`.
Focus draws an accent ring (`0 0 0 3px var(--accent-glow)`) and switches
the border to `--accent`. Labels are 13 px, weight 600, in
`--text-secondary`.

For anatomy, layouts, validation, deletion, accessibility, and copy, see
the dedicated [Forms](#forms) section below — it is the operational
reference when building any create / edit / delete screen.

### Tables

- Header transparent, weight 700, uppercase tracking `0.08em`,
  bottom border `1.5px subtle`.
- Row hover: `--surface-muted` (very light).
- Cell padding `0.75rem 1rem`.

### Badges, pills, refs

- `.badge-dot`: pill with a small coloured dot prefix. Semantics via
  Bootstrap classes (`text-bg-success`, etc.).
- `.ref`: mono uppercase pill for reference codes (`RISK-001`).
  Background `--surface-muted`, border `--border-light`.

---

## Forms

Forms are where audit-grade rigour meets day-to-day data entry. Every
field reads like a contractual statement: the label is precise, the
helper removes ambiguity, the error tells the user what to fix. Forms
default to server-side validation and always preserve the user's input on
error.

### Patterns at a glance

Pick the lightest pattern that fits the task. Don't open a full page when
a drawer will do; don't cram twelve fields into a drawer.

| Pattern | Use when | Reference |
| --- | --- | --- |
| **Drawer form** | Quick create / edit triggered from a list or detail page. HTMX-driven, never navigates away. ≤ 12 fields. | [`templates/includes/modal_form.html`](../../templates/includes/modal_form.html) |
| **Single-column page form** | Simple object with ≤ 8 fields, no metadata to surface. Wrap in a `.card`. | [`risks/templates/risks/risk_form.html`](../../risks/templates/risks/risk_form.html) |
| **Two-column page form** | Rich object with logical groups. `col-lg-8` for primary fields, `col-lg-4` for status / dates / tags. | [`context/templates/context/issue_form.html`](../../context/templates/context/issue_form.html) |
| **Confirmation form** | Single destructive action (delete, archive). One sentence + danger / cancel buttons. | [`reports/templates/reports/decision_confirm_delete.html`](../../reports/templates/reports/decision_confirm_delete.html) |

### Anatomy of a field

The four parts of any field, always in this order: label, control,
helper, error.

```django
<div class="mb-3">
  <label for="{{ field.id_for_label }}" class="form-label">
    {{ field.label }}{% if field.field.required %} *{% endif %}
  </label>
  {{ field }}
  {% if field.help_text %}<div class="form-text">{{ field.help_text }}</div>{% endif %}
  {% for error in field.errors %}<div class="invalid-feedback d-block">{{ error }}</div>{% endfor %}
</div>
```

| Slot | Class | Spec |
| --- | --- | --- |
| Label | `.form-label` | 13 px / 600 / `--text-secondary`. Trailing `*` on required (with a space before it). Never hidden, never replaced by a placeholder. |
| Control | `.form-control` / `.form-select` / `.form-check-input` | 15 px / 500 / `--text-primary`. 1 px border, radius `0.75rem`, padding `.5625rem .875rem`. |
| Helper | `.form-text` | 13 px / 400 / `--text-muted`. Short, concrete. No terminal punctuation unless it's a full sentence. |
| Error | `.invalid-feedback.d-block` | 13 px / 400 / `--danger`. Says what to fix, not just "invalid". Use `.d-block` so it appears unconditionally below the control. |

### Visual states

| State | Treatment |
| --- | --- |
| Default | Border `--border-light`, surface background. |
| Hover | Border darkens to `rgba(22,19,18,.22)` (subtle, not aggressive). |
| Focus | Border `--accent`, glow ring `0 0 0 3px var(--accent-glow)`. |
| Filled | No special styling: a value is its own signal. |
| Placeholder | `--text-muted` at 70 % opacity, weight 400 (lighter than the typed value). |
| Disabled / readonly | Background `--surface-muted`, text `--text-secondary`. |
| Invalid | Add Bootstrap `.is-invalid` (red border). Error appears below as `.invalid-feedback.d-block`. |

### Layouts

#### Single column

The canonical pattern for objects with ≤ 8 fields and no metadata
sidebar. Wrap the form in a single `.card`, iterate fields, end with a
sticky action bar.

#### Two columns

For rich objects: `col-lg-8` for primary fields grouped in cards,
`col-lg-4` for the status / dates / tags sidebar. Each column hosts
one or more `.card` blocks, each card carrying one logical group.

```django
<form method="post">
  {% csrf_token %}
  <div class="row">
    <div class="col-lg-8">
      <div class="card mb-4">
        <div class="card-header">
          <h6 class="mb-0">
            <i class="bi bi-flag me-2" style="color:var(--accent)"></i>
            {% trans "Identity" %}
          </h6>
        </div>
        <div class="card-body">… fields …</div>
      </div>
      {# more cards: analysis, relations, etc. #}
    </div>
    <div class="col-lg-4">
      {# status, dates, tags #}
    </div>
  </div>
  <div class="d-flex gap-2 form-actions-sticky">
    <button type="submit" class="btn btn-primary">
      <i class="bi bi-check-lg me-1" aria-hidden="true"></i>{% trans "Save" %}
    </button>
    <a href="..." class="btn btn-outline-secondary">{% trans "Cancel" %}</a>
  </div>
</form>
```

#### Drawer

Extends [`templates/includes/modal_form.html`](../../templates/includes/modal_form.html)
and fills the `{% block modal_form_fields %}` block. The drawer renders
inputs at a tighter scale (13 px, radius `--radius-xs`, min-height
36 px) so ~12 fields fit without scrolling on a 13-inch laptop. Form
submission is HTMX (`hx-post` on the form, target `#drawer-form-content`);
the drawer never closes on validation failure - the partial returns with
errors re-rendered.

#### Grid inside a card

Bootstrap rows + columns are encouraged when two fields are short and
related (e.g., `type` + `category`). Don't split a long textarea; let it
take the full width.

### Field grouping

Group fields by **meaning**, not by widget type. A card carries one
concept; its header names that concept with an icon + section title:

| Group | Typical fields |
| --- | --- |
| **Identity** | name, reference, type, category, scopes, owner |
| **Analysis** | levels, scores, descriptions, rationale |
| **Status** | workflow status, planned dates, assignees |
| **Relations** | linked assets, risks, frameworks, suppliers |
| **Tags** | free-form classification only |

Rules:

- A card with more than ~6 fields usually splits into two.
- Don't create a card for a single field unless it's a rich-text area.
- Card titles use the action-oriented voice of [Voice and tone](#voice-and-tone)
  ("Analysis", not "Step 2"; "Identity", not "Basic info").

### Required vs. optional

- Required fields carry a trailing `*` next to the label (separated by a
  space). No extra helper text saying "Required" - the asterisk is the
  signal.
- Don't mark optional fields ("optional" label, parentheses, etc.). If
  most of the form is optional, mark only the few required fields. If
  most fields are required, that's already the default expectation.
- The asterisk inherits the label's grey - it's a marker, not an alarm.
  Avoid `<span class="text-danger">*</span>`.

### Actions

#### Order, style, hierarchy

| Position | Style | Action |
| --- | --- | --- |
| Left | `btn btn-primary` | **Save** (primary CTA). Carries `<i class="bi bi-check-lg me-1"></i>`. |
| Right | `btn btn-outline-secondary` | **Cancel** (escape hatch). Always present. |

Drawer footer mirrors the same order: Cancel on the far left of the
footer cluster (dismisses the drawer), Save on the right (primary CTA).
The asymmetry is intentional - it follows the platform convention
established by the offcanvas component.

#### Destructive actions

Never put a destructive button beside Save. Delete, archive, reject and
similar actions live on their own page or in a confirmation modal. They
use `btn btn-danger`.

#### Sticky action bar

For any form longer than one viewport, wrap the actions in
`.form-actions-sticky`. The bar pins to the bottom of the viewport with a
soft gradient mask so the form content fades into it rather than
colliding.

### Create vs. edit

Same template, conditional title - the form structure stays identical so
the user's mental model carries over from one mode to the other.

```django
{% if form.instance.pk %}
  {% trans "Edit risk" as page_title %}
{% else %}
  {% trans "New risk" as page_title %}
{% endif %}
{% page_header page_title %}{% endpage_header %}
```

- Pre-filled values come from `ModelForm` - never repeat them in
  placeholder or help text. The user already sees the value in the field.
- The page title says **Edit \<object\>** or **New \<object\>**, never
  "Edit form" or "Create".
- In edit mode, audit-relevant fields (status, approval, history) stay
  visible but may be readonly. Never silently strip them.

### Delete

Deletion is a separate page (or HTMX-driven modal for trivial in-list
objects). The canonical pattern:

```django
{% page_header _("Delete decision") %}{% endpage_header %}
<div class="card"><div class="card-body">
  <p>
    {% blocktrans with ref=object.reference title=object.title %}
    Delete decision <strong>{{ ref }} - {{ title }}</strong>?
    {% endblocktrans %}
  </p>
  <p class="text-muted">
    {% trans "This action cannot be undone. The 4 linked actions will become orphaned." %}
  </p>
  <form method="post">
    {% csrf_token %}
    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-danger">
        <i class="bi bi-trash me-1" aria-hidden="true"></i>{% trans "Delete permanently" %}
      </button>
      <a href="..." class="btn btn-outline-secondary">{% trans "Cancel" %}</a>
    </div>
  </form>
</div></div>
```

Rules:

- Always name the object in the confirmation sentence (`Delete framework
  "ISO 27001"?`), never a generic "this item".
- Spell out the consequence: "This action cannot be undone", "12 linked
  risks will be unassigned", "The 3 child sites will move to no parent".
- Verb on the button: **Delete**, **Archive**, **Remove**, **Reject**.
  Never "OK", "Yes", "Confirm".
- Destructive primary button on the **left**, Cancel on the right - same
  order as Save / Cancel; muscle memory wins.

### Widgets

| Need | Widget | Notes |
| --- | --- | --- |
| Short text | `<input type="text">` (`.form-control`) | Default. |
| Long text | `<textarea>` (`.form-control`) | Auto-upgraded to **Jodit** rich text on page load. Opt out with `.no-jodit`. |
| Enumerated value | `<select>` (`.form-select`) | Auto-upgraded to **TomSelect** for searchable single-select where appropriate. |
| Tags | `<select multiple name="tags">` | Always **TomSelect** with the create plugin, initialised by `base.html`. |
| Date | `<input type="date">` (`.form-control`) | Native picker; format `YYYY-MM-DD`. |
| Datetime | `<input type="datetime-local">` | Same conventions; UTC stored, local shown. |
| Boolean | `<input type="checkbox">` (`.form-check-input`) | Wrap in `.form-check` with the label on the right. |
| Scope tree | Custom radio / checkbox tree | See `templates/includes/scope_tree.html`. |
| File upload | `<input type="file">` | The parent `<form>` must set `enctype="multipart/form-data"`. |

Widget enhancements (TomSelect, Jodit) are wired centrally in
[`templates/base.html`](../../templates/base.html). Never load them
manually inside a template.

### Validation

- **Server-side is the source of truth.** Always validate in the view,
  even when client-side hints exist. Browser `required` / `pattern`
  attributes are nice-to-have, not load-bearing.
- Field-level errors are rendered as `.invalid-feedback.d-block` directly
  under the control.
- Form-level errors (`form.non_field_errors`) render as a single
  `<div class="alert alert-danger">` at the top of the form, before the
  first field.
- HTMX submissions return the same partial with errors re-rendered; the
  drawer stays open and the user keeps their input.
- The ARIA polite region `#hx-live` announces the error count after each
  HTMX submit. Screen readers hear "3 fields need attention" without
  having to re-scan the form.

### Accessibility in forms

- Every control has an associated `<label>` via `for` / `id_for_label`.
  Never use a placeholder as a label.
- Errors are programmatically associated with the field via Bootstrap's
  `.invalid-feedback` adjacency. When the field carries `.is-invalid`,
  the message is announced.
- Tab order follows visual order. No `tabindex` overrides.
- The first input of a fresh form receives focus on render (`autofocus`
  on the first non-disabled field).
- Date inputs use `type="date"` so screen readers and mobile keyboards
  pick the right affordance.
- Touch targets ≥ 36 px (current input height range is 36 to 42 px).
- Required state is conveyed both visually (trailing `*`) and
  semantically (`required` attribute carried by the widget).
- Disabled inputs stay reachable in the tab order; truly hidden inputs
  use `display: none` and `aria-hidden="true"`.

### Copy

Form labels and helpers follow the [Voice and tone](#voice-and-tone)
section. Concrete rules for forms specifically:

| Bad | Good |
| --- | --- |
| `Name` (label on a risk form) | `Risk name` |
| `Required` (help text) | (just the trailing `*`) |
| `Invalid input` (error) | `Use a date later than the start date.` |
| `Please fill out this field.` (browser default) | `Enter a name.` |
| `Saving...` (button while submitting) | The button stays "Save"; the form-wide spinner via `hx-disabled-elt` carries the loading signal. |
| `Are you sure?` (delete) | `Delete framework "ISO 27001"? 12 requirements and 4 assessments will become orphaned.` |
| `OK` (button) | `Save`, `Create the risk`, `Approve`, `Delete permanently` |

---

## Motion and transitions

Intentional motion, never decorative. Always honours
`prefers-reduced-motion` (global guard in `base.html`).

### Easing

| Token | Cubic-bezier | Usage |
| --- | --- | --- |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | Appearances, hovers, scrolls. The default. |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | Theme / mode transitions. |
| `--transition-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Light attention pop-ins, very rare. |

### Durations

| Token | Value | Usage |
| --- | --- | --- |
| `--transition-fast` | 150 ms | Colour on hover, focus rings. |
| `--transition-normal` | 220 ms | Surface transitions, opacity. |
| `--transition-slow` | 320 ms | Content slides (drawer, page fade-in). |

### Reusable animations

Defined in `base.html`, applied via utility classes.

| Class | Effect | Duration |
| --- | --- | --- |
| `.fw-fade-in` | Opacity 0→1 | 220 ms |
| `.fw-slide-up` | Opacity 0→1 + 8 px translateY | 320 ms |
| `.fw-pop` | Opacity 0→1 + scale 0.96→1 | 350 ms (spring) |
| `.fw-stagger > *` | Slide-up with cascading delay (40 ms per child via `--i`) | 320 ms |

### Automatic behaviour

On page load, major elements (`page-header`, `h1`, `h2`, `card`, `alert`,
`row`, `table-responsive`, `stat-card`) automatically play `fw-slide-up`
with a slight stagger (40 / 80 / 120 / 160 ms) to give the impression of
"page being built" rather than abrupt appearance.

### Motion rules

- No animation longer than 400 ms outside page transitions.
- No perpetual decorative animation (rotating loaders OK, but no ambient
  pulses running continuously).
- `prefers-reduced-motion: reduce` collapses all animations and
  transitions to 0.001 ms (global guard in place).

---

## Accessibility

The app targets WCAG 2.2 AA. See also `/styleguide` which documents the
criteria covered.

### Criteria covered by default

| Criterion | How | Level |
| --- | --- | --- |
| 1.4.3 Minimum contrast | All palette text/bg pairs are AA, most AAA | AA |
| 2.4.7 Focus visible | Global `:focus-visible` rule, 2 px accent outline at min 3:1 | AA |
| 2.3.3 Reduced motion | Global guard `prefers-reduced-motion: reduce` | AAA |
| 4.1.3 Status messages | ARIA polite region `#hx-live` announces every HTMX mutation | AA |
| 4.1.2 Name, Role, Value | Command palette in combobox pattern (role, aria-controls, aria-activedescendant) | A |
| 2.4.4 Link purpose | Descriptive `aria-label` on every icon-only button | A |
| 2.5.8 Target size | Icon-only buttons at 36×36 px, above the 24×24 minimum | AA |

### Commitments

- All labels are translatable (never hard-coded without `_()` or
  `{% trans %}`).
- Decorative icons carry `aria-hidden="true"`.
- Icon-only buttons carry a descriptive `aria-label`.
- Interactive elements have a target size ≥ 24×24 px.
- Transitions vanish when the user requests
  `prefers-reduced-motion: reduce`.
- The app is fully usable from the keyboard (tab, shift+tab, escape,
  enter, cmd+k for the command palette).

---

## Voice and tone

Cairn speaks to professionals who know their craft. The tone is:

- **Sober**: no superlative ("awesome", "great", "best"), no emoji in
  the interface (they are fine in release notes and docs).
- **Precise**: "Risk assessment" rather than "assessment"; "approved by
  X on DD/MM/YYYY" rather than "validated".
- **Action-oriented**: buttons describe the action, not the state
  ("Create a risk" rather than "New").
- **Bilingual by default**: every string is translated to French and
  English. When in doubt, the French follows the ANSSI / CNIL / ISO
  vocabulary ("exigence", "périmètre", "partie intéressée").

### To avoid

- ❌ "Click here"
- ❌ "You have X errors" (prefer "X requirements non-compliant")
- ❌ Unnecessary anglicisms in French strings ("checker", "splitter",
  "ownership").

### Concrete examples

| Bad | Good |
| --- | --- |
| "Oops, something went wrong" | "The record failed to save. Check the highlighted fields." |
| "Validated ✓" | "Approved by Alice Dupont on 2026-05-30" |
| "Empty" | "No risk recorded yet. Open an assessment to create one." |
| "New" | "Create a requirement" |

---

## Assets and files

### Logos

- [`mark.svg`](./mark.svg) - primary mark (≥ 24 px)
- [`mark-sm.svg`](./mark-sm.svg) - small mark / favicon (≤ 22 px)
- [`wordmark.svg`](./wordmark.svg) - CAIRN wordmark with signature dot

### Live styleguide page

- `/styleguide` (accessible after login) - renders all shared
  components in their variants. The runtime reference, updated
  automatically as components evolve.

### Design sources

- Palette, shadows, radii and transitions are defined in
  `templates/base.html` (`:root` block and `[data-bs-theme="dark"]`).
- Shared components (badge, page_header, empty_state, etc.):
  `core/templatetags/ui.py` + `templates/components/`.
- This guide: `docs/brand/brand-guidelines.md`.

### Evolution

Any change to the palette, motion tokens or core components must:

1. Be discussed and approved before execution (transverse impact).
2. Update both this guide AND the `/styleguide` page.
3. Be entered in the `CHANGELOG.md`.

---

_Last updated: 2026-05-30. Cairn (formerly Fairway)._
