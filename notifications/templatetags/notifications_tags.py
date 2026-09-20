''' Django notifications template tags file '''
# -*- coding: utf-8 -*-
import re

from django import get_version
from django.core.cache import cache
from django.template import Library
from django.utils.html import escapejs, format_html, format_html_join
from packaging.version import (
    parse as parse_version,  # pylint: disable=no-name-in-module,import-error
)

from notifications import settings
from notifications.settings import get_config

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import (
        reverse,  # pylint: disable=no-name-in-module,import-error
    )

register = Library()


def get_cached_notification_unread_count(user):

    return cache.get_or_set(
        'cache_notification_unread_count',
        user.notifications.unread().count,
        settings.get_config()['CACHE_TIMEOUT']
    )

def notifications_unread(context):
    user = user_context(context)
    if not user:
        return ''
    return get_cached_notification_unread_count(user)


if parse_version(get_version()) >= parse_version('2.0'):
    notifications_unread = register.simple_tag(takes_context=True)(notifications_unread)  # pylint: disable=invalid-name
else:
    notifications_unread = register.assignment_tag(takes_context=True)(notifications_unread)  # noqa


@register.filter
def has_notification(user):
    if user:
        return user.notifications.unread().exists()
    return False


# Requires vanilla-js framework - http://vanilla-js.com/
@register.simple_tag
def register_notify_callbacks(badge_class='live_notify_badge',  # pylint: disable=too-many-arguments,missing-docstring
                              menu_class='live_notify_list',
                              refresh_period=15,
                              callbacks='',
                              api_name='list',
                              fetch=5,
                              nonce=None,
                              mark_as_read=False
                              ):
    refresh_period = int(refresh_period) * 1000

    if api_name == 'list':
        api_url = reverse('notifications:live_unread_notification_list')
    elif api_name == 'count':
        api_url = reverse('notifications:live_unread_notification_count')
    else:
        return ""
    definitions = format_html("""
        notify_badge_class='{badge_class}';
        notify_menu_class='{menu_class}';
        notify_api_url='{api_url}';
        notify_fetch_count='{fetch_count}';
        notify_unread_url='{unread_url}';
        notify_mark_all_unread_url='{mark_all_unread_url}';
        notify_refresh_period={refresh};
        notify_mark_as_read={mark_as_read};
    """,
        badge_class=escapejs(badge_class),
        menu_class=escapejs(menu_class),
        refresh=refresh_period,
        api_url=escapejs(api_url),
        unread_url=escapejs(reverse('notifications:unread')),
        mark_all_unread_url=escapejs(reverse('notifications:mark_all_as_read')),
        fetch_count=escapejs(str(fetch)),
        mark_as_read=str(mark_as_read).lower()
    )

    # add a nonce value to the script tag if one is provided
    nonce_str = format_html(' nonce="{}"', nonce) if nonce else ""

    callback_names = [name.strip() for name in callbacks.split(',') if name.strip()]
    for name in callback_names:
        if not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*', name):
            raise ValueError('Notification callbacks must be JavaScript function names.')
    registrations = format_html_join('', 'register_notifier({});', ((name,) for name in callback_names))
    return format_html('<script type="text/javascript"{}>{}{}</script>', nonce_str, definitions, registrations)


@register.simple_tag(takes_context=True)
def live_notify_badge(context, badge_class='live_notify_badge'):
    user = user_context(context)
    if not user:
        return ''

    return format_html("<span class='{badge_class}'>{unread}</span>",
        badge_class=badge_class, unread=get_cached_notification_unread_count(user)
    )


@register.simple_tag
def live_notify_list(list_class='live_notify_list'):
    return format_html("<ul class='{list_class}'></ul>", list_class=list_class)


def user_context(context):
    if 'user' not in context:
        return None

    request = context['request']
    user = request.user
    try:
        user_is_anonymous = user.is_anonymous()
    except TypeError:  # Django >= 1.11
        user_is_anonymous = user.is_anonymous

    if user_is_anonymous:
        return None
    return user
