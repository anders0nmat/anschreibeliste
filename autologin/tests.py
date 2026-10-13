from django.test import TestCase

from autologin.models import PrivilegedSession
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils.timezone import now
from unittest import mock
from django.contrib.sessions.models import Session

# Create your tests here.
class AutloginTestCase(TestCase):
    def setUp(self) -> None:
        User.objects.create_user('a', password='1234')

    def test_default_session(self):
        self.client.login(username='a', password='1234')
        self.client.get('/')

        session = Session.objects.get(session_key=self.client.session.session_key)
        self.assertIsNotNone(session)

        self.client.get('/')

        after_session = Session.objects.get(session_key=self.client.session.session_key)

        self.assertEqual(session.session_key, after_session.session_key)
        self.assertEqual(session.expire_date, after_session.expire_date)

    def test_sesssion_renewal(self):
        self.client.login(username='a', password='1234')

        PrivilegedSession.objects.create(
            name='asd',
            session_key=self.client.session.session_key
        )

        key_before = self.client.session.session_key
        expiry_before = self.client.session.get_expiry_date()
        instant = now()
        self.client.get('/')
        key_after = self.client.session.session_key
        expiry_after = self.client.session.get_expiry_date()

        self.assertEqual(key_before, key_after)
        self.assertTrue(expiry_before < expiry_after)
        self.assertTrue(instant + timedelta(days=90) <= expiry_after)

        self.client.get('/')
        expiry_after2 = self.client.session.get_expiry_date()
        self.assertTrue(expiry_after < expiry_after2)
    
    def test_session_reroll(self):
        self.client.login(username='a', password='1234')

        testtime = now() - timedelta(days=32)

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = testtime
            PrivilegedSession.objects.create(
                name='asd',
                session_key=self.client.session.session_key
            )

        key_before = self.client.session.session_key
        expire_before = self.client.session.get_expiry_date()
        instant = now()
        self.client.get('/')
        key_after = self.client.session.session_key
        expire_after = self.client.session.get_expiry_date()

        self.assertNotEqual(key_before, key_after)
        self.assertTrue(expire_before < expire_after)
        self.assertTrue(instant + timedelta(days=90) <= expire_after)



