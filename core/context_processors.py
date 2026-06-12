from django.conf import settings


def app_version(request):
    return {"APP_VERSION": settings.APP_VERSION}


def assistant_enabled(request):
    return {"AI_ASSISTANT_ENABLED": settings.AI_ASSISTANT_ENABLED}
