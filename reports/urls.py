from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="report-list"),
    path("soa/create/", views.SoaReportCreateView.as_view(), name="soa-create"),
    path("<uuid:pk>/delete/", views.ReportDeleteView.as_view(), name="report-delete"),
]
