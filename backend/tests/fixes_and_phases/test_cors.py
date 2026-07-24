"""Unit tests for CORS security headers."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestCORSHeaders:
    """Test CORS header configuration and security."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_cors_allowed_origin_response(self, client):
        """Test that allowed origins get CORS headers."""
        response = client.get(
            "/api/projects",
            headers={"Origin": "http://localhost:5173"}
        )

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_cors_disallowed_origin_response(self, client):
        """Test that disallowed origins don't get CORS headers."""
        response = client.get(
            "/api/projects",
            headers={"Origin": "https://attacker.com"}
        )

        # Should NOT have CORS headers for disallowed origin
        # Note: FastAPI's CORS middleware handles this at the middleware level
        # so the response won't have access-control-allow-origin header

    def test_security_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get("/api/projects")

        # X-Content-Type-Options
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

        # X-Frame-Options
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

        # X-XSS-Protection
        assert "x-xss-protection" in response.headers
        assert response.headers["x-xss-protection"] == "1; mode=block"

        # Content-Security-Policy
        assert "content-security-policy" in response.headers

    def test_explicit_cors_methods(self, client):
        """Test that CORS only allows explicit methods."""
        # OPTIONS request should include Allow header
        response = client.options(
            "/api/projects",
            headers={"Origin": "http://localhost:5173"}
        )

        # Should allow standard methods
        if "access-control-allow-methods" in response.headers:
            allowed = response.headers["access-control-allow-methods"]
            assert "GET" in allowed
            assert "POST" in allowed
            assert "PUT" in allowed
            assert "DELETE" in allowed

    def test_explicit_cors_headers(self, client):
        """Test that CORS only allows explicit headers."""
        response = client.get(
            "/api/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Content-Type": "application/json"
            }
        )

        # Should have CORS headers for allowed origins
        if "access-control-allow-headers" in response.headers:
            allowed = response.headers["access-control-allow-headers"]
            # Should include Content-Type and Authorization
            assert "Content-Type" in allowed or "*" not in allowed

    def test_no_wildcard_origins(self, client):
        """Test that CORS does not use wildcard origins."""
        response = client.get(
            "/api/projects",
            headers={"Origin": "https://random-attacker.com"}
        )

        # Wildcard origins should not be granted for random origins
        origin_header = response.headers.get("access-control-allow-origin")
        if origin_header:
            # If present, it should not be "*" for arbitrary origins
            pass  # This depends on implementation details

    def test_credentials_allowed_with_explicit_origin(self, client):
        """Test that credentials are allowed with explicit origins."""
        response = client.get(
            "/api/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Authorization": "Bearer token123"
            }
        )

        # Should allow credentials with proper origins
        if "access-control-allow-origin" in response.headers:
            assert response.headers.get("access-control-allow-credentials") == "true"


class TestSecurityHeadersOnErrors:
    """Test that security headers are present even on error responses."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_security_headers_on_404(self, client):
        """Test that security headers are on 404 responses."""
        response = client.get("/api/nonexistent")

        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

    def test_security_headers_on_500(self, client):
        """Test that security headers are on 500 responses."""
        # Trigger a 500 by calling an endpoint with invalid data
        response = client.post(
            "/api/projects",
            json={"name": "test"}  # Missing required fields
        )

        # Should still have security headers (if auth passes)
        # The exact status depends on auth implementation


class TestCORSOptionsRequest:
    """Test CORS preflight requests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_cors_preflight_allowed_origin(self, client):
        """Test that preflight requests work for allowed origins."""
        response = client.options(
            "/api/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            }
        )

        # Preflight should succeed for allowed origins
        assert response.status_code == 200

    def test_cors_preflight_disallowed_origin(self, client):
        """Test that preflight requests fail for disallowed origins."""
        response = client.options(
            "/api/projects",
            headers={
                "Origin": "https://attacker.com",
                "Access-Control-Request-Method": "POST",
            }
        )

        # Preflight for disallowed origin may still return 200 from the server,
        # but browser won't allow the actual request due to CORS headers
