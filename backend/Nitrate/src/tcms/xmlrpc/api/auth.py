# -*- coding: utf-8 -*-

from django.contrib.auth import authenticate
from xmlrpc.client import Fault
from django.conf import settings
from django.core.exceptions import PermissionDenied

from tcms.xmlrpc.decorators import log_call

__all__ = ("login", "logout", "login_krbv")

__xmlrpc_namespace__ = "Auth"


def check_user_name(parameters):
    username = parameters.get("username")
    password = parameters.get("password")
    if not username or not password:
        raise PermissionDenied("Username and password is required")

    return username, password


@log_call(namespace=__xmlrpc_namespace__)
def login(request, credential):
    """Login into Nitrate

    :param dict credential: a mapping containing ``username`` and ``password``.
    :return: Session ID
    :rtype: str
    :raise PermissionDenied: if either ``username`` or ``password`` is
        incorrect.

    Example:

    >>> Auth.login({'username': 'foo', 'password': 'bar'})
    """
    from tcms.auth import get_backend

    user = None

    for backend_str in settings.AUTHENTICATION_BACKENDS:
        backend = get_backend(backend_str)
        user = backend.authenticate(request, *check_user_name(credential))

        if user:
            user.backend = "{}.{}".format(backend.__module__, backend.__class__.__name__)
            django.contrib.auth.login(request, user)
            return request.session.session_key

    if user is None:
        raise PermissionDenied("Wrong username or password")


@log_call(namespace=__xmlrpc_namespace__)
def login_krbv(request):
    """Login into the Nitrate deployed with mod_auth_kerb

    :return: Session ID.
    :rtype: str

    Example::

        $ kinit
        Password for username@example.com:

        $ python
        Auth.login_krbv()
    """
    from django.contrib.auth.middleware import RemoteUserMiddleware

    middleware = RemoteUserMiddleware()
    middleware.process_request(request)

    return request.session.session_key


@log_call(namespace=__xmlrpc_namespace__)
def logout(request):
    """Delete session information"""
    django.contrib.auth.logout(request)

@log_call(namespace=__xmlrpc_namespace__)
def legacy_login(request, username, password):
    """
    Backward-compatible login method for python-tcms-api
    """
    return login(request, {'username': username, 'password': password})
