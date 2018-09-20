from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from .exceptions import BadRequestException, ConfigurationException, ForbiddenException
from robinhood.api import ApiForbiddenException
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from .utilities import mattermost_text
import json

class HandleExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, BadRequestException):
            status = 400
        elif isinstance(exception, ConfigurationException):
            status = 401
        elif isinstance(exception, ApiForbiddenException)or isinstance(exception, ForbiddenException):
            status = 403
        else:
            raise(exception)

        if request.method == 'POST':
            # Return a JSON message for Mattermost requests
            return mattermost_text(str(exception))
        else:
            return HttpResponse(str(exception), status=status)

class DisableCSRF(MiddlewareMixin):
    def process_request(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)
