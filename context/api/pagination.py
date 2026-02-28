from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "status": "success",
                "data": data,
                "meta": {
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "success"},
                "data": schema,
                "meta": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "total_count": {"type": "integer"},
                        "total_pages": {"type": "integer"},
                    },
                },
            },
        }
