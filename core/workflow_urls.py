from django.urls import path

from .workflow_views import WorkflowTransitionView

app_name = "workflow"

urlpatterns = [
    path(
        "<str:app_label>/<str:model>/<uuid:pk>/transition/",
        WorkflowTransitionView.as_view(),
        name="transition",
    ),
]
