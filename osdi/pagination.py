from drf_hal_json.pagination import HalPageNumberPagination
from rest_framework.response import Response
from rest_framework.settings import api_settings
from drf_hal_json import LINKS_FIELD_NAME, EMBEDDED_FIELD_NAME

class OsdiPagination(HalPageNumberPagination):

    max_page_size = 100 # something sane
    page_query_param = 'page'
    page_size_query_param = 'per_page'
    osdi_schema = None # e.g. 'osdi:events'

    def get_paginated_response(self, data):
        if self.osdi_schema:
            data = {self.osdi_schema: data}
        response = super(OsdiPagination, self).get_paginated_response(data)
        result = response.data
        result['total_pages'] = int(result['count'] / result['page_size']) + 1
        result['page'] =  self.request.query_params.get(self.page_query_param, 1)
        result['total_records'] = result.get('count')
        response.data = result
        return response
