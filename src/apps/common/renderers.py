import datetime
import logging
import re

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import renderers
from rest_framework.utils.encoders import JSONEncoder

logger = logging.getLogger(__name__)


class CustomTimeJSONRenderer(renderers.JSONRenderer):
    format = "json"

    def render(self, data, media_type=None, renderer_context=None):
        request = renderer_context["request"]
        if t_format := request.META.get("HTTP_TIME_FORMAT"):
            # Change the format of all DateTime fields in the response data
            data = self.adjust_datetime_format(data, t_format)
        return super().render(data, media_type, renderer_context)

    def adjust_datetime_format(self, data, time_format):
        datetime_pattern = r"^\d{4}-\d{2}"
        if isinstance(data, list):
            return [self.adjust_datetime_format(item, time_format) for item in data]
        elif isinstance(data, dict):
            return {
                key: self.adjust_datetime_format(value, time_format) for key, value in data.items()
            }
        elif isinstance(data, str):
            if re.match(datetime_pattern, data) is not None:
                try:
                    datetime_obj = parse_datetime(data)
                    current_timezone = timezone.get_current_timezone()
                    if timezone.is_naive(datetime_obj):
                        datetime_obj = timezone.make_aware(datetime_obj, current_timezone)
                    utc_datetime = datetime_obj.astimezone(timezone.utc)
                    return utc_datetime.strftime(time_format)
                except ValueError as e:
                    logger.error(e)
                    return data
            else:
                return data
        else:
            return data
