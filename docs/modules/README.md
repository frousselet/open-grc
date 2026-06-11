# Module specifications

This directory is the single source of truth for what each Cairn module does and how it is structured. It replaces the historical `features_spec/M0-M4` monolithic files: each entity now lives in its own file so a feature change touches a focused doc instead of grepping a 60 KB markdown.

## Layout

```
docs/modules/
├── README.md                    (this file)
├── m0-accounts/                 Users, groups, permissions, auth
├── m1-context/                  Scopes, issues, stakeholders, objectives, SWOT, roles, activities, indicators
├── m2-assets/                   Essential assets, support assets, asset groups, sites, suppliers
├── m3-compliance/               Frameworks, sections, requirements, assessments, mappings, action plans
├── m4-risks/                    Risk assessment, threats, vulnerabilities, risks, treatment, acceptance
│   └── ebios-rm/                EBIOS RM workshops (W0-W5) per ANSSI v1.5
├── management-review/           ISO 27001 §9.3 management review entities
└── governance/                  Cross-cutting platform governance (lifecycle workflow framework)
```

Each module directory contains:

- a `README.md` : module overview, business rules (`RG-*`, `RS-*`), API base path, permission codenames, cross-cutting concerns (notifications, UI principles);
- one `<entity>.md` per domain entity : model fields, validation, lifecycle, references back to the module's business rules.

## Conventions

- File names are **kebab-case** of the entity name (`essential-asset.md`, not `EssentialAsset.md`).
- Entity headers are H1; field tables follow the convention `| Champ | Type | Contraintes | Description |`.
- Cross-references between entities use relative links: `[Objective](objective.md)`.
- Business rules keep their original identifier (`RG-01`, `RS-04`, etc.) so legacy commit messages and code comments stay searchable. Rules retired by a later decision are kept as struck-through entries with a reason : see `m1-context/README.md` for an example.
- Enums and choice lists are reproduced verbatim from the model so the doc is grep-able against the code.

## Relationship with the code

The doc references models by their Django class name (e.g. `Indicator`, `ComplianceAssessment`) and points at the importable path (`context.models.indicator.Indicator`) at the top of each entity file. The doc is updated in the same commit as the model change : there is no separate "spec PR" step.

When the implementation diverges from a documented intent, the doc is updated rather than the code being rolled back, unless the divergence is a bug. Document the rationale in the doc itself or in `CHANGELOG.md`.
