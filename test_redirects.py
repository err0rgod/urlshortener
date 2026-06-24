import sys
import os
import unittest
from datetime import datetime, UTC, timedelta
from dotenv import load_dotenv
from sqlmodel import Session, select

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from models import urldata
from database import engine, get_long_url, add_to_db
from short_url_gen import redis_client
from app import app
from fastapi.testclient import TestClient

class TestRedirects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        cls.client = TestClient(app)
        # Clear redis cache for our test key to ensure fresh database lookup
        redis_client.delete("testexp")
        redis_client.delete("testvalid")
        redis_client.delete("testban")
        redis_client.delete("testaware")

    def tearDown(self):
        # Clean up database entries after each test
        from models import clicklog
        with Session(engine) as session:
            for code in ["testexp", "testvalid", "testban", "testaware"]:
                click_statement = select(clicklog).where(clicklog.short_url == code)
                clicks = session.exec(click_statement).all()
                for click in clicks:
                    session.delete(click)
                statement = select(urldata).where(urldata.short_url == code)
                res = session.exec(statement).first()
                if res:
                    session.delete(res)
            session.commit()
        # Clean up redis
        redis_client.delete("testexp")
        redis_client.delete("testvalid")
        redis_client.delete("testban")
        redis_client.delete("testaware")

    def test_expired_link_returns_410(self):
        # 1. Create a link in the DB that expired 1 hour ago (timezone naive)
        from short_url_gen import add_custom_url
        exp_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        add_custom_url(
            long_url="https://example.com/expired-target",
            custom_alias="testexp",
            exp_time=exp_time
        )

        # 2. Query get_long_url directly
        self.assertEqual(get_long_url("testexp"), "Expired")

        # 3. Test HTTP redirection endpoint
        response = self.client.get("/testexp", follow_redirects=False)
        self.assertEqual(response.status_code, 410)
        self.assertIn("Link Has Expired", response.text)

    def test_timezone_aware_expiration(self):
        # Create a link in the DB that expired 1 hour ago (timezone aware UTC)
        from short_url_gen import add_custom_url
        exp_time = datetime.now(UTC) - timedelta(hours=1)
        add_custom_url(
            long_url="https://example.com/aware-target",
            custom_alias="testaware",
            exp_time=exp_time
        )

        # Query get_long_url directly and check that it evaluates correctly without TypeError
        self.assertEqual(get_long_url("testaware"), "Expired")

        # Test HTTP redirection endpoint
        response = self.client.get("/testaware", follow_redirects=False)
        self.assertEqual(response.status_code, 410)

    def test_valid_link_redirects_302(self):
        # Create a valid link
        from short_url_gen import add_custom_url
        add_custom_url(
            long_url="https://example.com/valid-target",
            custom_alias="testvalid",
            exp_time=None
        )

        # Test HTTP redirection endpoint
        response = self.client.get("/testvalid", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://example.com/valid-target")

        # Verify that click count has incremented to 1
        with Session(engine) as session:
            statement = select(urldata).where(urldata.short_url == "testvalid")
            res = session.exec(statement).first()
            self.assertEqual(res.click_count, 1)

    def test_banned_link_returns_403(self):
        # Create a banned link
        from short_url_gen import add_custom_url, ban_in_cache
        from database import mark_url_banned
        add_custom_url(
            long_url="https://example.com/banned-target",
            custom_alias="testban",
            exp_time=None
        )
        mark_url_banned("testban")
        ban_in_cache("testban")

        # Query get_long_url directly
        self.assertEqual(get_long_url("testban"), "BANNED")

        # Test HTTP redirection endpoint
        response = self.client.get("/testban", follow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Security Warning", response.text)

if __name__ == "__main__":
    unittest.main()
