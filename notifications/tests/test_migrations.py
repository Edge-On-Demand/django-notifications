from unittest import skipIf

from django.contrib.auth.models import User
from django.db import connection, migrations
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from swapper import load_model

from notifications.signals import notify

Notification = load_model('notifications', 'Notification')


@skipIf(Notification._meta.app_label != 'notifications', 'Tests the default notification model migrations')
class MigrationCompatibilityTests(TransactionTestCase):
    latest = ('notifications', '0010_rename_notification_recipient_unread_notificatio_recipie_8bedf2_idx')

    def migrate_latest(self):
        MigrationExecutor(connection).migrate([self.latest])

    def test_upgrade_when_old_fork_already_renamed_the_index(self):
        self.addCleanup(self.migrate_latest)
        MigrationExecutor(connection).migrate([('notifications', '0008_index_together_recipient_unread')])

        executor = MigrationExecutor(connection)
        previous = ('notifications', '0009_alter_notification_options_and_more')
        migration = executor.loader.disk_migrations[previous]
        # The Edge fork's former 0009 performed the rename that upstream moved into 0010.
        migration.operations.insert(1, migrations.RenameIndex(
            model_name='notification', new_name='notificatio_recipie_8bedf2_idx',
            old_fields=('recipient', 'unread'),
        ))
        executor.migrate([previous])
        user = User.objects.create_user(username='recipient')
        notification = notify.send(user, recipient=user, verb='Preserve this notification')[0][1][0]

        self.migrate_latest()

        notification.refresh_from_db()
        self.assertEqual(notification.verb, 'Preserve this notification')
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_constraints(cursor, Notification._meta.db_table)
        self.assertIn('notificatio_recipie_8bedf2_idx', indexes)
        self.assertEqual(indexes['notificatio_recipie_8bedf2_idx']['columns'], ['recipient_id', 'unread'])
