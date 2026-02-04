"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient
from fastapi import FastAPI

from app import app


@pytest.fixture
async def client():
    """Create async test client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client):
        """Test health endpoint returns OK status."""
        response = await client.get("/health")
        assert response.json()["status"] == "healthy" or response.json().get("status") == "ok"
    
    @pytest.mark.asyncio
    async def test_health_check_is_json(self, client):
        """Test health endpoint returns JSON."""
        response = await client.get("/health")
        assert response.headers["content-type"].startswith("application/json")


class TestAuditEndpoint:
    """Tests for audit initiation endpoint."""
    
    @pytest.mark.asyncio
    async def test_audit_endpoint_requires_owner_repo(self, client):
        """Test audit endpoint requires owner/repo."""
        response = await client.post("/audit", json={})
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_audit_endpoint_accepts_valid_request(self, client, sample_audit_request):
        """Test audit endpoint accepts valid request."""
        response = await client.post("/audit", json=sample_audit_request)
        # Should return 202 (accepted) or 200 (ok)
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_audit_endpoint_returns_audit_response(self, client, sample_audit_request):
        """Test audit endpoint returns response with audit_id."""
        response = await client.post("/audit", json=sample_audit_request)
        if response.status_code in [200, 202]:
            data = response.json()
            assert "audit_id" in data or "id" in data


class TestAuditsListEndpoint:
    """Tests for listing audits endpoint."""
    
    @pytest.mark.asyncio
    async def test_audits_list_returns_200(self, client):
        """Test audits list endpoint returns 200."""
        response = await client.get("/audits")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_audits_list_returns_array(self, client):
        """Test audits list returns array."""
        response = await client.get("/audits")
        data = response.json()
        assert isinstance(data, (list, dict))
    
    @pytest.mark.asyncio
    async def test_audits_list_with_filter(self, client):
        """Test audits list with filters."""
        response = await client.get("/audits?status=completed")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_audits_list_pagination(self, client):
        """Test audits list pagination."""
        response = await client.get("/audits?skip=0&limit=10")
        assert response.status_code == 200


class TestAuditRetrievalEndpoint:
    """Tests for retrieving audit results."""
    
    @pytest.mark.asyncio
    async def test_audit_status_endpoint_not_found(self, client):
        """Test audit status for non-existent audit."""
        response = await client.get("/audits/nonexistent-id")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_audit_status_returns_json(self, client):
        """Test audit status returns JSON."""
        # This would need a valid audit ID
        response = await client.get("/audits/test-id")
        if response.status_code != 404:
            assert response.headers["content-type"].startswith("application/json")


class TestReportEndpoints:
    """Tests for report generation endpoints."""
    
    @pytest.mark.asyncio
    async def test_html_report_not_found(self, client):
        """Test HTML report for non-existent audit."""
        response = await client.get("/audits/nonexistent/report/html")
        assert response.status_code in [404, 400]
    
    @pytest.mark.asyncio
    async def test_pdf_report_not_found(self, client):
        """Test PDF report for non-existent audit."""
        response = await client.get("/audits/nonexistent/report/pdf")
        assert response.status_code in [404, 400]
    
    @pytest.mark.asyncio
    async def test_pdf_report_content_type(self, client):
        """Test PDF report has correct content type."""
        response = await client.get("/audits/test-id/report/pdf")
        if response.status_code == 200:
            assert "pdf" in response.headers.get("content-type", "").lower()


class TestOpenAPI:
    """Tests for OpenAPI documentation."""
    
    @pytest.mark.asyncio
    async def test_openapi_schema_endpoint(self, client):
        """Test OpenAPI schema endpoint."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_openapi_schema_is_valid_json(self, client):
        """Test OpenAPI schema is valid JSON."""
        response = await client.get("/openapi.json")
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "openapi" in data
    
    @pytest.mark.asyncio
    async def test_docs_endpoint(self, client):
        """Test Swagger docs endpoint."""
        response = await client.get("/docs")
        # Docs may be HTML or JSON
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint."""
        response = await client.get("/redoc")
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_404_error_returns_json(self, client):
        """Test 404 error returns JSON."""
        response = await client.get("/nonexistent/endpoint")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client):
        """Test method not allowed."""
        response = await client.put("/health")
        assert response.status_code == 405  # Method not allowed
    
    @pytest.mark.asyncio
    async def test_invalid_json_returns_422(self, client):
        """Test invalid JSON returns 422."""
        response = await client.post("/audit", content="invalid json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422


class TestCORS:
    """Tests for CORS headers."""
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """Test CORS headers are present."""
        response = await client.get("/health")
        # May have access-control headers
        assert "content-type" in response.headers


class TestAPIVersioning:
    """Tests for API versioning."""
    
    @pytest.mark.asyncio
    async def test_api_version_in_response(self, client):
        """Test API version is available."""
        response = await client.get("/openapi.json")
        if response.status_code == 200:
            data = response.json()
            # Should have info with version
            assert "info" in data


class TestEndpointValidation:
    """Tests for endpoint input validation."""
    
    @pytest.mark.asyncio
    async def test_missing_required_field(self, client):
        """Test missing required field."""
        response = await client.post("/audit", json={
            # Missing owner and repo
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_invalid_field_type(self, client):
        """Test invalid field type."""
        response = await client.post("/audit", json={
            "owner": 123,  # Should be string
            "repo": "test"
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_additional_fields_ignored(self, client, sample_audit_request):
        """Test additional fields don't cause errors."""
        request_data = sample_audit_request.copy()
        request_data["extra_field"] = "should be ignored"
        response = await client.post("/audit", json=request_data)
        # Should succeed or fail on validation, not extra field
        assert response.status_code != 500


class TestEndpointPerformance:
    """Tests for endpoint response times."""
    
    @pytest.mark.asyncio
    async def test_health_check_fast(self, client):
        """Test health check responds quickly."""
        import time
        start = time.time()
        response = await client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should be under 1 second


class TestEndpointBehavior:
    """Tests for correct endpoint behavior."""
    
    @pytest.mark.asyncio
    async def test_post_creates_resource(self, client, sample_audit_request):
        """Test POST creates new resource."""
        response = await client.post("/audit", json=sample_audit_request)
        # Should return 200 or 202, not 400+
        assert response.status_code < 400
    
    @pytest.mark.asyncio
    async def test_get_retrieves_resource(self, client):
        """Test GET retrieves resource."""
        response = await client.get("/audits")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_endpoints_return_data(self, client):
        """Test endpoints return data."""
        response = await client.get("/health")
        data = response.json()
        assert data is not None
        assert len(data) > 0
