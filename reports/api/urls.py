from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"reports", views.ReportViewSet)

app_name = "reports-api"

urlpatterns = [
    path("", include(router.urls)),
]
