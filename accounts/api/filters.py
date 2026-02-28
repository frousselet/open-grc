import django_filters

from accounts.models import AccessLog, Permission, User


class UserFilter(django_filters.FilterSet):
    group = django_filters.UUIDFilter(field_name="custom_groups__id")
    permission = django_filters.CharFilter(method="filter_by_permission")
    department = django_filters.CharFilter(lookup_expr="icontains")
    is_active = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = User
        fields = ["is_active", "department"]

    def filter_by_permission(self, queryset, name, value):
        return queryset.filter(custom_groups__permissions__codename=value).distinct()

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            django_filters.utils.Q(email__icontains=value)
            | django_filters.utils.Q(first_name__icontains=value)
            | django_filters.utils.Q(last_name__icontains=value)
        )


class PermissionFilter(django_filters.FilterSet):
    module = django_filters.CharFilter()
    feature = django_filters.CharFilter()
    action = django_filters.CharFilter()

    class Meta:
        model = Permission
        fields = ["module", "feature", "action"]


class AccessLogFilter(django_filters.FilterSet):
    event_type = django_filters.CharFilter()
    email = django_filters.CharFilter(field_name="email_attempted", lookup_expr="icontains")
    date_from = django_filters.DateFilter(field_name="timestamp", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="timestamp", lookup_expr="date__lte")
    user_id = django_filters.UUIDFilter(field_name="user__id")

    class Meta:
        model = AccessLog
        fields = ["event_type"]
