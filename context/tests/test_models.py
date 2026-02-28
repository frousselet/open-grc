import pytest
from django.core.exceptions import ValidationError

from context.constants import (
    IssueCategory,
    IssueType,
    ObjectiveStatus,
)
from context.tests.factories import IssueFactory, ObjectiveFactory, ScopeFactory

pytestmark = pytest.mark.django_db


class TestScopeHierarchy:
    """P1: scope tree traversal and circular reference detection."""

    def test_level_root(self):
        scope = ScopeFactory()
        assert scope.level == 0

    def test_level_nested(self):
        root = ScopeFactory()
        child = ScopeFactory(parent_scope=root)
        grandchild = ScopeFactory(parent_scope=child)
        assert child.level == 1
        assert grandchild.level == 2

    def test_full_path(self):
        root = ScopeFactory(name="Group")
        child = ScopeFactory(name="BU", parent_scope=root)
        grandchild = ScopeFactory(name="Site", parent_scope=child)
        assert grandchild.full_path == "Group / BU / Site"

    def test_get_ancestors(self):
        root = ScopeFactory(name="A")
        child = ScopeFactory(name="B", parent_scope=root)
        grandchild = ScopeFactory(name="C", parent_scope=child)
        ancestors = grandchild.get_ancestors()
        assert [a.name for a in ancestors] == ["A", "B"]

    def test_circular_reference_rejected(self):
        a = ScopeFactory()
        b = ScopeFactory(parent_scope=a)
        a.parent_scope = b
        with pytest.raises(ValidationError, match="circulaire"):
            a.clean()


class TestIssueValidation:
    """P1: type/category coherence."""

    def test_internal_with_internal_category_ok(self):
        issue = IssueFactory(type=IssueType.INTERNAL, category=IssueCategory.STRATEGIC)
        issue.clean()  # no error

    def test_internal_with_external_category_rejected(self):
        issue = IssueFactory.build(type=IssueType.INTERNAL, category=IssueCategory.POLITICAL)
        with pytest.raises(ValidationError, match="catégorie interne"):
            issue.clean()

    def test_external_with_external_category_ok(self):
        scope = ScopeFactory()
        issue = IssueFactory(scope=scope, type=IssueType.EXTERNAL, category=IssueCategory.ECONOMIC)
        issue.clean()

    def test_external_with_internal_category_rejected(self):
        issue = IssueFactory.build(type=IssueType.EXTERNAL, category=IssueCategory.TECHNICAL)
        with pytest.raises(ValidationError, match="catégorie externe"):
            issue.clean()


class TestObjectiveValidation:
    """P1: achieved status and scope rules."""

    def test_achieved_requires_100_percent(self):
        obj = ObjectiveFactory.build(
            status=ObjectiveStatus.ACHIEVED,
            progress_percentage=80,
        )
        with pytest.raises(ValidationError, match="100"):
            obj.clean()

    def test_achieved_with_100_percent_ok(self):
        obj = ObjectiveFactory(
            status=ObjectiveStatus.ACHIEVED,
            progress_percentage=100,
        )
        obj.clean()  # no error

    def test_parent_must_share_scope(self):
        scope_a = ScopeFactory()
        scope_b = ScopeFactory()
        parent = ObjectiveFactory(scope=scope_a)
        child = ObjectiveFactory.build(scope=scope_b, parent_objective=parent)
        with pytest.raises(ValidationError, match="même périmètre"):
            child.clean()

    def test_parent_same_scope_ok(self):
        scope = ScopeFactory()
        parent = ObjectiveFactory(scope=scope)
        child = ObjectiveFactory(scope=scope, parent_objective=parent)
        child.clean()  # no error
