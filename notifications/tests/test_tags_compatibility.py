from django.contrib.auth.models import User
from django.core.cache import cache
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from notifications.signals import notify
from notifications.templatetags.notifications_tags import register_notify_callbacks


class TagCompatibilityTests(TestCase):
    def test_badge_and_list_escape_class_attributes(self):
        user = User.objects.create_user(username='recipient')
        notify.send(user, recipient=user, verb='updated')
        cache.clear()
        self.addCleanup(cache.clear)
        request = RequestFactory().get('/')
        request.user = user
        rendered = Template(
            '{% load notifications_tags %}'
            '{% live_notify_badge badge_class=css_class %}'
            '{% live_notify_list list_class=css_class %}'
        ).render(Context({'request': request, 'user': user, 'css_class': "badge' data-extra='value"}))
        self.assertEqual(
            rendered,
            "<span class='badge&#x27; data-extra=&#x27;value'>1</span>"
            "<ul class='badge&#x27; data-extra=&#x27;value'></ul>",
        )

    def test_callbacks_and_options_render_as_javascript(self):
        html = register_notify_callbacks(
            callbacks='fill_notification_badge, app.notify', nonce='nonce"&value',
            badge_class="badge'</script>", refresh_period=3, fetch=7, mark_as_read=True,
        )
        self.assertIn('nonce="nonce&quot;&amp;value"', html)
        self.assertIn(r"notify_badge_class='badge\u0027\u003C/script\u003E';", html)
        self.assertIn('notify_refresh_period=3000;', html)
        self.assertIn("notify_fetch_count='7';", html)
        self.assertIn('notify_mark_as_read=true;', html)
        self.assertIn('register_notifier(fill_notification_badge);register_notifier(app.notify);', html)
        self.assertEqual(html.count('</script>'), 1)

    def test_empty_callbacks_and_invalid_callback(self):
        self.assertNotIn('register_notifier(', register_notify_callbacks())
        with self.assertRaises(ValueError):
            register_notify_callbacks(callbacks='callback);</script>')
