# -*- coding: utf-8 -*-
from itsdangerous import URLSafeTimedSerializer

from h.security import derive_key

from h import util
from h.accounts import models


class Error(Exception):

    """Base class for this package's custom exception classes."""

    pass


class NoSuchUserError(Error):

    """Exception raised when asking for a user that doesn't exist."""

    pass


class JSONError(Error):

    """Exception raised when there's a problem with a request's JSON body.

    This is for pre-validation problems such as no JSON body, body cannot
    be parsed as JSON, or top-level keys missing from the JSON.

    """

    pass


def make_admin(username):
    """Make the given user an admin."""
    user = models.User.get_by_username(username)
    if user:
        user.admin = True
    else:
        raise NoSuchUserError


def make_staff(username):
    """Make the given user a staff member."""
    user = models.User.get_by_username(username)
    if user:
        user.staff = True
    else:
        raise NoSuchUserError


def get_user(userid, request):
    """Return the User object for the given userid, or None.

    This will also return None if the given userid is None, if it isn't a valid
    userid, if its domain doesn't match the site's domain, or if there's just
    no user with that userid.

    """
    if userid is None:
        return None

    try:
        parts = util.split_user(userid)
    except ValueError:
        return

    if parts['domain'] != request.auth_domain:
        return None

    return models.User.get_by_username(parts['username'])


def authenticated_user(request):
    """Return the authenticated user or None.

    :rtype: h.accounts.models.User or None

    """
    return get_user(request.authenticated_userid, request)


def includeme(config):
    """A local identity provider."""
    config.add_request_method(
        authenticated_user, name='authenticated_user', reify=True)

    config.include('.schemas')
    config.include('.subscribers')
    config.include('.views')

    secret = config.registry.settings['secret_key']
    derived = derive_key(secret, b'h.accounts')
    serializer = URLSafeTimedSerializer(derived)
    config.registry.password_reset_serializer = serializer
