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
            message = json_error_response(str(exception))
        else:
            message = str(exception)

        if isinstance(exception, BadRequestException):
            return HttpResponseBadRequest(message)
        elif isinstance(exception, ForbiddenException):
            return HttpResponseForbidden(message)
        else:
            return HttpResponse(message)
