import os
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from algo_trading.settings import database_from_url

from .models import (
    UserBNFuturesRelation,
    UserBNOptionsRelation,
    UserFyersAppRelation,
)


class DatabaseConfigurationTests(SimpleTestCase):
    def test_postgres_url_is_parsed_without_exposing_credentials_in_source(self):
        with patch.dict(os.environ, {"DB_CONN_MAX_AGE": "17"}):
            config = database_from_url(
                "postgresql://trade_user:p%40ss@database.example:5544/trading"
            )

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "trading")
        self.assertEqual(config["USER"], "trade_user")
        self.assertEqual(config["PASSWORD"], "p@ss")
        self.assertEqual(config["HOST"], "database.example")
        self.assertEqual(config["PORT"], 5544)
        self.assertEqual(config["CONN_MAX_AGE"], 17)

    def test_non_postgres_database_url_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            database_from_url("mysql://localhost/autodub")


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("trader", password="password")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('home')}",
            fetch_redirect_response=False,
        )

    def test_authenticated_dashboard_renders_both_bot_forms(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("bn_futures_bot_url"))
        self.assertContains(response, reverse("bn_options_bot_url"))
        self.assertContains(response, reverse("fyers_authentication"))


class BotConfigurationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("trader", password="password")
        self.client.force_login(self.user)

    def set_access_token(self, value="broker-token"):
        session = self.client.session
        session["fyers_access_token"] = value
        session.save()

    def test_configuration_routes_only_accept_posts(self):
        self.assertEqual(self.client.get(reverse("bn_futures_bot_url")).status_code, 405)
        self.assertEqual(self.client.get(reverse("bn_options_bot_url")).status_code, 405)

    def test_bot_configuration_requires_a_broker_token(self):
        response = self.client.post(
            reverse("bn_futures_bot_url"), {"number_of_lots": 2}, follow=True
        )

        self.assertContains(response, "Authenticate with Fyers")
        self.assertFalse(UserBNFuturesRelation.objects.exists())

    def test_number_of_lots_must_be_positive(self):
        self.set_access_token()

        response = self.client.post(
            reverse("bn_futures_bot_url"), {"number_of_lots": 0}, follow=True
        )

        self.assertContains(response, "positive number of lots")
        self.assertFalse(UserBNFuturesRelation.objects.exists())

    def test_repeated_futures_configuration_updates_one_record(self):
        self.set_access_token("first-token")
        self.client.post(reverse("bn_futures_bot_url"), {"number_of_lots": 2})
        self.set_access_token("updated-token")

        response = self.client.post(
            reverse("bn_futures_bot_url"), {"number_of_lots": 4}, follow=True
        )

        self.assertContains(response, "configuration saved")
        self.assertEqual(UserBNFuturesRelation.objects.count(), 1)
        configuration = UserBNFuturesRelation.objects.get()
        self.assertEqual(configuration.user_id, self.user)
        self.assertEqual(configuration.number_of_lots, 4)
        self.assertEqual(configuration.fyers_access_token, "updated-token")

    def test_options_configuration_is_saved_for_authenticated_user(self):
        self.set_access_token()

        response = self.client.post(
            reverse("bn_options_bot_url"), {"number_of_lots": 3}, follow=True
        )

        self.assertContains(response, "configuration saved")
        configuration = UserBNOptionsRelation.objects.get()
        self.assertEqual(configuration.user_id, self.user)
        self.assertEqual(configuration.number_of_lots, 3)


class FyersAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("trader", password="password")
        self.client.force_login(self.user)

    def configure_app(self):
        return UserFyersAppRelation.objects.create(
            user=self.user,
            fyers_app_id="app-id",
            fyers_app_secretkey="app-secret",
        )

    def test_authentication_requires_configured_credentials(self):
        response = self.client.get(reverse("fyers_authentication"), follow=True)

        self.assertContains(response, "Add your Fyers application credentials")

    @patch("home.views._fyers_session")
    def test_authentication_redirects_to_broker(self, session_factory):
        self.configure_app()
        broker_session = Mock()
        broker_session.generate_authcode.return_value = "https://broker.example/oauth"
        session_factory.return_value = broker_session

        response = self.client.get(reverse("fyers_authentication"))

        self.assertRedirects(
            response, "https://broker.example/oauth", fetch_redirect_response=False
        )

    def test_callback_rejects_missing_authorization_code(self):
        self.configure_app()

        response = self.client.get(
            reverse("fyers_authentication_callback"), follow=True
        )

        self.assertContains(response, "could not be completed")
        self.assertNotIn("fyers_access_token", self.client.session)

    @patch("home.views._fyers_session")
    def test_callback_saves_valid_access_token_without_rendering_it(
        self, session_factory
    ):
        self.configure_app()
        broker_session = Mock()
        broker_session.generate_token.return_value = {"access_token": " secret-token "}
        session_factory.return_value = broker_session

        response = self.client.get(
            reverse("fyers_authentication_callback") + "?auth_code=code-123",
            follow=True,
        )

        broker_session.set_token.assert_called_once_with("code-123")
        self.assertEqual(self.client.session["fyers_access_token"], "secret-token")
        self.assertContains(response, "authentication completed")
        self.assertNotContains(response, "secret-token")

    @patch("home.views._fyers_session")
    def test_callback_rejects_malformed_broker_response(self, session_factory):
        self.configure_app()
        broker_session = Mock()
        broker_session.generate_token.return_value = {"message": "denied"}
        session_factory.return_value = broker_session

        response = self.client.get(
            reverse("fyers_authentication_callback") + "?auth_code=code-123",
            follow=True,
        )

        self.assertContains(response, "could not be completed")
        self.assertNotIn("fyers_access_token", self.client.session)
