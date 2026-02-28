from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None

        # Don't wrap already-wrapped responses (e.g. from pagination)
        if isinstance(data, dict) and "status" in data:
            return super().render(data, accepted_media_type, renderer_context)

        if response and response.status_code >= 400:
            wrapped = {
                "status": "error",
                "error": data,
            }
        else:
            wrapped = {
                "status": "success",
                "data": data,
            }

        return super().render(wrapped, accepted_media_type, renderer_context)
