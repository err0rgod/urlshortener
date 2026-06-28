import sys
import os
import unittest
from datetime import datetime, UTC, timedelta
from dotenv import load_dotenv
from sqlmodel import Session, select
from unittest.mock import patch

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from models import urldata, clicklog
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
        redis_client.delete("testsched")
        redis_client.delete("testcustomsched")

        # Create testing users
        from models import User
        with Session(engine) as session:
            stmt_p = select(User).where(User.email == "testpremium@example.com")
            existing_p = session.exec(stmt_p).first()
            stmt_f = select(User).where(User.email == "testfree@example.com")
            existing_f = session.exec(stmt_f).first()
            
            user_ids = [u.id for u in [existing_p, existing_f] if u is not None]
            if user_ids:
                from models import CustomDomain
                dom_stmt = select(CustomDomain).where(CustomDomain.user_id.in_(user_ids))
                doms = session.exec(dom_stmt).all()
                for dom in doms:
                    session.delete(dom)
                session.commit()

                stmt_urls = select(urldata).where(urldata.user_id.in_(user_ids))
                urls = session.exec(stmt_urls).all()
                for url in urls:
                    click_stmt = select(clicklog).where(clicklog.short_url == url.short_url)
                    clicks = session.exec(click_stmt).all()
                    for click in clicks:
                        session.delete(click)
                    session.delete(url)
                session.commit()
            
            if existing_p:
                session.delete(existing_p)
            if existing_f:
                session.delete(existing_f)
            session.commit()

            cls.premium_user = User(
                email="testpremium@example.com",
                full_name="Test Premium",
                oauth_provider="local",
                oauth_id="testpremium",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                tier="premium"
            )
            cls.free_user = User(
                email="testfree@example.com",
                full_name="Test Free",
                oauth_provider="local",
                oauth_id="testfree",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                tier="free"
            )
            session.add(cls.premium_user)
            session.add(cls.free_user)
            session.commit()
            session.refresh(cls.premium_user)
            session.refresh(cls.free_user)

    @classmethod
    def tearDownClass(cls):
        from models import User
        with Session(engine) as session:
            stmt_p = select(User).where(User.email == "testpremium@example.com")
            existing_p = session.exec(stmt_p).first()
            stmt_f = select(User).where(User.email == "testfree@example.com")
            existing_f = session.exec(stmt_f).first()
            
            user_ids = [u.id for u in [existing_p, existing_f] if u is not None]
            if user_ids:
                from models import CustomDomain
                dom_stmt = select(CustomDomain).where(CustomDomain.user_id.in_(user_ids))
                doms = session.exec(dom_stmt).all()
                for dom in doms:
                    session.delete(dom)
                session.commit()

                stmt_urls = select(urldata).where(urldata.user_id.in_(user_ids))
                urls = session.exec(stmt_urls).all()
                for url in urls:
                    click_stmt = select(clicklog).where(clicklog.short_url == url.short_url)
                    clicks = session.exec(click_stmt).all()
                    for click in clicks:
                        session.delete(click)
                    session.delete(url)
                session.commit()
                    
            if existing_p:
                session.delete(existing_p)
            if existing_f:
                session.delete(existing_f)
            session.commit()

    def tearDown(self):
        # Clean up database entries after each test
        from models import clicklog
        with Session(engine) as session:
            stmt_urls = select(urldata).where(urldata.user_id.in_([self.premium_user.id, self.free_user.id]))
            urls = session.exec(stmt_urls).all()
            for url in urls:
                click_stmt = select(clicklog).where(clicklog.short_url == url.short_url)
                clicks = session.exec(click_stmt).all()
                for click in clicks:
                    session.delete(click)
                session.delete(url)

            for code in ["testexp", "testvalid", "testban", "testaware", "testsched", "testcustomsched"]:
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
        redis_client.delete("testsched")
        redis_client.delete("testcustomsched")
        self.client.cookies.clear()

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

    def test_scheduled_link_shows_countdown(self):
        from short_url_gen import add_custom_url
        activation_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)
        add_custom_url(
            long_url="https://example.com/sched-target",
            custom_alias="testsched",
            user_id=self.premium_user.id,
            activation_time=activation_time
        )
        
        response = self.client.get("/testsched", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Link Activating Soon", response.text)
        self.assertIn("window.__ACTIVATION_TIME__", response.text)

    def test_scheduled_link_redirects_custom_countdown_url(self):
        from short_url_gen import add_custom_url
        activation_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)
        add_custom_url(
            long_url="https://example.com/sched-target",
            custom_alias="testcustomsched",
            user_id=self.premium_user.id,
            activation_time=activation_time,
            custom_countdown_url="https://google.com"
        )
        
        response = self.client.get("/testcustomsched", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://google.com")

    def test_scheduled_link_already_active(self):
        from short_url_gen import add_custom_url
        activation_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
        add_custom_url(
            long_url="https://example.com/sched-target-past",
            custom_alias="testsched",
            user_id=self.premium_user.id,
            activation_time=activation_time
        )
        
        response = self.client.get("/testsched", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://example.com/sched-target-past")

    def test_post_shorten_premium_activation(self):
        import jwt
        from app import JWT_SECRET_KEY
        token = jwt.encode({"user_id": self.premium_user.id, "email": self.premium_user.email}, JWT_SECRET_KEY, algorithm="HS256")
        self.client.cookies.set("session_token", token)
        
        activation_str = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
        response = self.client.post("/shorten", json={
            "long_url": "https://google.com",
            "activation_time": activation_str,
            "custom_countdown_url": "https://google.com"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("short_url", response.json())
        
        # Test free user gets 400
        free_token = jwt.encode({"user_id": self.free_user.id, "email": self.free_user.email}, JWT_SECRET_KEY, algorithm="HS256")
        self.client.cookies.set("session_token", free_token)
        response = self.client.post("/shorten", json={
            "long_url": "https://google.com",
            "activation_time": activation_str
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("premium-only feature", response.json()["detail"])

    def test_premium_user_can_edit_link(self):
        import jwt
        from app import JWT_SECRET_KEY
        from short_url_gen import add_custom_url
        
        add_custom_url(
            long_url="https://google.com",
            custom_alias="testsched",
            user_id=self.premium_user.id
        )
        
        token = jwt.encode({"user_id": self.premium_user.id, "email": self.premium_user.email}, JWT_SECRET_KEY, algorithm="HS256")
        self.client.cookies.set("session_token", token)
        
        response = self.client.patch("/api/links/testsched", json={
            "long_url": "https://google.com",
            "webhook_url": "https://google.com",
            "ios_url": "https://google.com"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        
        with Session(engine) as session:
            statement = select(urldata).where(urldata.short_url == "testsched")
            res = session.exec(statement).first()
            self.assertEqual(res.long_url, "https://google.com")
            self.assertEqual(res.webhook_url, "https://google.com")
            self.assertEqual(res.ios_url, "https://google.com")

    def test_free_user_cannot_edit_link(self):
        import jwt
        from app import JWT_SECRET_KEY
        from short_url_gen import add_custom_url
        
        add_custom_url(
            long_url="https://google.com",
            custom_alias="testsched",
            user_id=self.free_user.id
        )
        
        token = jwt.encode({"user_id": self.free_user.id, "email": self.free_user.email}, JWT_SECRET_KEY, algorithm="HS256")
        self.client.cookies.set("session_token", token)
        
        response = self.client.patch("/api/links/testsched", json={
            "long_url": "https://google.com"
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn("premium-only feature", response.json()["detail"])

    def test_serves_sad_meme_video(self):
        response = self.client.get("/sad_meme.mp4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")

    def test_serves_dancing_meme_video(self):
        response = self.client.get("/dancing_meme.mp4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")

    def test_create_payment_order_unauthorized(self):
        response = self.client.post("/api/payments/create-order", json={"plan": "startup"})
        self.assertEqual(response.status_code, 401)

    @patch("app.razorpay_client")
    def test_create_payment_order_success(self, mock_rz):
        import jwt
        from app import JWT_SECRET_KEY
        
        mock_rz.order.create.return_value = {
            "id": "order_test_123",
            "amount": 159900,
            "currency": "INR"
        }
        
        token = jwt.encode({"user_id": self.free_user.id, "email": self.free_user.email}, JWT_SECRET_KEY, algorithm="HS256")
        self.client.cookies.set("session_token", token)
        
        response = self.client.post("/api/payments/create-order", json={"plan": "startup"})
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        self.assertEqual(res_json["order_id"], "order_test_123")
        self.assertEqual(res_json["amount"], 159900)
        self.assertEqual(res_json["currency"], "INR")

    @patch("app.razorpay_client")
    def test_verify_payment_success(self, mock_rz):
        import jwt
        from app import JWT_SECRET_KEY
        
        # mock signature verification and order fetch to pass
        mock_rz.utility.verify_payment_signature.return_value = True
        mock_rz.order.fetch.return_value = {"amount": 159900, "currency": "INR"}
        
        token = jwt.encode({"user_id": self.free_user.id, "email": self.free_user.email}, JWT_SECRET_KEY, algorithm="HS256")
        self.client.cookies.set("session_token", token)
        
        payload = {
            "razorpay_order_id": "order_test_123",
            "razorpay_payment_id": "pay_test_123",
            "razorpay_signature": "sig_test_123"
        }
        response = self.client.post("/api/payments/verify", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        
    def test_check_allowed_domain_endpoint(self):
        from models import CustomDomain
        from sqlmodel import Session
        from database import engine

        # Register custom domain in DB
        with Session(engine) as db_session:
            dom = CustomDomain(domain_name="test-caddy-domain.com", user_id=self.premium_user.id)
            db_session.add(dom)
            db_session.commit()
            dom_id = dom.id

        try:
            # Check allowed domain (should return 200)
            resp = self.client.get("/api/domains/check-allowed?domain=test-caddy-domain.com")
            self.assertEqual(resp.status_code, 200)

            # Check random unregistered domain (should return 400)
            resp = self.client.get("/api/domains/check-allowed?domain=not-registered.com")
            self.assertEqual(resp.status_code, 400)
        finally:
            with Session(engine) as db_session:
                to_del = db_session.get(CustomDomain, dom_id)
                if to_del:
                    db_session.delete(to_del)
                    db_session.commit()

if __name__ == "__main__":
    from unittest.mock import patch
    import unittest
    unittest.main()
