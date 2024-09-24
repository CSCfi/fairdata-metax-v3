import contextlib
import logging
import re
from datetime import timezone as tz
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.utils.http import parse_header_parameters
from rest_framework import renderers

logger = logging.getLogger(__name__)

import msgspec


class MsgspecJSONRenderer(renderers.BaseRenderer):
    """JSON Renderer utilizing msgspec

    Msgspec is faster, uses less memory and natively supports
    more types than the standard json library.
    See: https://jcristharif.com/msgspec/
    """

    media_type = "application/json"
    format = "json"
    charset = None

    def encoder_default(self, obj: Any) -> Any:
        """Any types not recognized by msgspec should be added here.

        For examples, see rest_framework.utils.encoders.JSONEncoder.
        """
        if isinstance(obj, Promise):
            return force_str(obj)
        elif isinstance(obj, QuerySet):
            return tuple(obj)
        elif isinstance(obj, str):  # ErrorDetail is a subclass of str
            return str(obj)
        raise NotImplementedError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    def get_indent(self, accepted_media_type, renderer_context):
        if accepted_media_type:
            _base_media_type, params = parse_header_parameters(accepted_media_type)
            with contextlib.suppress(KeyError, ValueError, TypeError):
                if params.get("indent"):
                    return max(min(int(params["indent"]), 8), 0)
        # The indent may be provided in the context, e.g. in BrowsableAPIRenderer
        return renderer_context.get("indent")

    def render(self, data, media_type=None, renderer_context=None):
        if data is None:
            return b""

        request = renderer_context["request"]
        if t_format := request.META.get("HTTP_TIME_FORMAT"):
            # Change the format of all DateTime fields in the response data
            data = self.adjust_datetime_format(data, t_format)

        buf = msgspec.json.encode(data, enc_hook=self.encoder_default)
        if indent := self.get_indent(media_type, renderer_context):
            buf = msgspec.json.format(buf, indent=indent)
        return buf

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
                    utc_datetime = datetime_obj.astimezone(tz.utc)
                    return utc_datetime.strftime(time_format)
                except ValueError as e:
                    logger.error(e)
                    return data
            else:
                return data
        else:
            return data


class NoHTMLFormBrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    def get_rendered_html_form(self, *args, **kwargs):
        """
        The Browsable API HTML forms do not support lists or dictionaries which
        makes them unusable for e.g. creating a dataset so we hide the form.
        """
        return None
