from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from .exceptions import BadRequestException, ForbiddenException
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
import json

def json_error_response(text):
    return HttpResponse(json.dumps({"text": text}), content_type="application/json")

class HandleExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if request.method == 'POST':
            # Return a JSON message for Mattermost requests
            return json_error_response(str(exception))
        else:
            if isinstance(exception, BadRequestException):
                status = 400
            elif isinstance(exception, ForbiddenException):
                status = 403
            return HttpResponse(str(exception), status=status)
