import logging
from datetime import datetime, timezone
from email.utils import format_datetime
from functools import wraps

from flask import jsonify, make_response, request


log = logging.getLogger("sunset")


def deprecate_at(sunset_date, replacement=None):
    sunset_date = sunset_date.astimezone(timezone.utc)
    sunset = format_datetime(sunset_date, usegmt=True)

    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            log.warning("deprecated_call %s %s", request.path, request.remote_addr)

            if datetime.now(timezone.utc) >= sunset_date:
                response = jsonify(error="gone", sunset=sunset, use_instead=replacement)
                response.status_code = 410
            else:
                response = make_response(fn(*args, **kwargs))
                response.headers["Sunset"] = sunset
                response.headers["Deprecation"] = "true"

            if replacement:
                response.headers["Link"] = f'<{replacement}>; rel="successor-version"'
            return response

        return wrapper

    return decorate
