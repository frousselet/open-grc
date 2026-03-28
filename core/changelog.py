"""Parse CHANGELOG.md and extract entries between two versions."""

import re
from pathlib import Path

from django.conf import settings

# Match version headers like: ## [0.21.3] - 2026-03-26
_VERSION_RE = re.compile(r"^## \[([^\]]+)\]")

# Category headers like: ### Added
_CATEGORY_RE = re.compile(r"^### (.+)")


def _parse_changelog():
    """Return an ordered list of (version, sections) from CHANGELOG.md.

    Each *sections* value is a dict mapping category names (Added, Changed, ...)
    to lists of bullet strings.
    """
    path = Path(settings.BASE_DIR) / "CHANGELOG.md"
    if not path.exists():
        return []

    entries = []
    current_version = None
    current_sections = {}
    current_category = None

    for line in path.read_text(encoding="utf-8").splitlines():
        vm = _VERSION_RE.match(line)
        if vm:
            if current_version and current_version != "Unreleased":
                entries.append((current_version, current_sections))
            current_version = vm.group(1)
            current_sections = {}
            current_category = None
            continue

        cm = _CATEGORY_RE.match(line)
        if cm:
            current_category = cm.group(1).strip()
            current_sections.setdefault(current_category, [])
            continue

        if current_category and line.startswith("- "):
            current_sections[current_category].append(line[2:].strip())

    # Flush last entry
    if current_version and current_version != "Unreleased":
        entries.append((current_version, current_sections))

    return entries


def _normalise_version(v):
    """Strip leading 'v' and return a tuple of ints for comparison."""
    v = v.strip().lstrip("v")
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def get_changelog_between(old_version, current_version):
    """Return changelog entries for versions > old_version and <= current_version.

    Returns a list of (version_str, sections_dict) newest-first.
    If *old_version* is empty/None, returns all entries up to *current_version*.
    """
    entries = _parse_changelog()
    if not entries:
        return []

    cur = _normalise_version(current_version)
    old = _normalise_version(old_version) if old_version else (0,)

    result = []
    for version_str, sections in entries:
        # Handle range headers like "0.14.0 - 0.14.2" - use highest version
        parts = version_str.split(" - ")
        v = _normalise_version(parts[-1].strip())
        if v > old and v <= cur:
            result.append((version_str, sections))

    return result
