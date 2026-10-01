"""FastAPI application for Acquisition Audit platform."""

import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from gitrate.core.audit_engine import AuditEngine, AuditStatus
from gitrate.core.models import AuditRequest, AuditResponse, HealthCheckResponse
from gitrate.core.webhooks import (
    GitHubWebhookHandler, GitLabWebhookHandler,
    GitHubWebhookPayload, GitLabWebhookPayload,
    WebhookValidator, webhook_queue
)
from gitrate.api.dashboard import router as dashboard_router
from gitrate.api.components import router as dashboard_ui_router
from gitrate.api.trends import router as trends_router
from gitrate.api.ml_analytics import router as ml_analytics_router
from gitrate.api.ml_dashboard import router as ml_dashboard_router
from gitrate.utils.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ===== LIFESPAN MANAGEMENT =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Acquisition Audit Platform...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API version: {settings.api_version}")
    
    yield
    
    logger.info("Shutting down Acquisition Audit Platform...")


# ===== CREATE APPLICATION =====

app = FastAPI(
    title="Acquisition Audit Platform",
    description="Professional technical due diligence for M&A and VC investments",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ===== MIDDLEWARE =====

# CORS middleware
if settings.environment != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ===== ROUTE REGISTRATION =====

# Include dashboard routes (Phase 6)
app.include_router(dashboard_router)
app.include_router(dashboard_ui_router, prefix="/dashboard")
app.include_router(trends_router)

# Include ML analytics routes (Phase 7)
app.include_router(ml_analytics_router)

# Include ML dashboard UI (Phase 8)
app.include_router(ml_dashboard_router, prefix="/ml-dashboard")



@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.environment != "production" else None,
        },
    )


# ===== ROUTES =====

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Acquisition Audit Platform",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"], response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={
            "api": "operational",
            "database": "operational",
            "cache": "operational",
        },
    )


@app.post("/audit", tags=["Audit"], response_model=AuditResponse)
async def create_audit(request: AuditRequest) -> AuditResponse:
    """
    Create and run a new acquisition audit.
    
    **Endpoint**: `POST /audit`
    
    **Request Body**:
    ```json
    {
        "repository_url": "https://github.com/owner/repo",
        "include_detailed_analysis": true
    }
    ```
    
    **Example Responses**:
    
    Success (202 Accepted):
    ```json
    {
        "success": true,
        "audit_id": "f3a4c2b1",
        "status": "COMPLETED",
        "message": "Audit completed successfully",
        "result": { ... }
    }
    ```
    
    Error:
    ```json
    {
        "success": false,
        "status": "FAILED",
        "message": "Failed to parse repository URL",
        "error": "Invalid URL format"
    }
    ```
    """
    
    try:
        # Parse GitHub URL
        from gitrate.utils.helpers import parse_github_url
        
        owner, repo, parse_error = parse_github_url(request.repository_url)
        if parse_error:
            logger.warning(f"Invalid repository URL: {request.repository_url}")
            return AuditResponse(
                success=False,
                status=AuditStatus.FAILED,
                message="Failed to parse repository URL",
                error=parse_error,
            )
        
        # Initialize audit engine
        audit_engine = AuditEngine(github_token=settings.github_token)
        
        # Run audit
        logger.info(f"Starting audit for {owner}/{repo}")
        result, error = await audit_engine.run_full_audit(owner, repo)
        
        if error:
            logger.error(f"Audit failed: {error}")
            return AuditResponse(
                success=False,
                status=AuditStatus.FAILED,
                message="Audit execution failed",
                error=error,
            )
        
        # Return successful result
        logger.info(f"Audit completed for {owner}/{repo}")
        return AuditResponse(
            success=True,
            audit_id=result.audit_id,
            status=AuditStatus.COMPLETED,
            message="Audit completed successfully",
            result=result,
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in audit endpoint: {str(e)}", exc_info=True)
        return AuditResponse(
            success=False,
            status=AuditStatus.FAILED,
            message="Internal server error",
            error=str(e),
        )


@app.get("/audit/{audit_id}", tags=["Audit"])
async def get_audit(audit_id: str):
    """
    Retrieve audit results by ID.
    
    Args:
        audit_id: The audit ID (first 8 chars of UUID)
    
    Returns:
        Complete audit results if found
    """
    # TODO: Implement audit result retrieval from database/cache
    return {
        "error": "Not implemented yet",
        "audit_id": audit_id,
    }


@app.get("/audits", tags=["Audit"])
async def list_audits(limit: int = 10, offset: int = 0):
    """
    List recent audits.
    
    Args:
        limit: Maximum results to return
        offset: Number of results to skip
    
    Returns:
        List of recent audits
    """
    # TODO: Implement audit listing from database
    return {
        "error": "Not implemented yet",
        "limit": limit,
        "offset": offset,
    }


@app.post("/report/{audit_id}/pdf", tags=["Reports"])
async def generate_pdf_report(audit_id: str):
    """
    Generate PDF report for audit.
    
    Args:
        audit_id: The audit ID
        
    Returns:
        PDF file download
    """
    # TODO: Implement PDF generation
    return {
        "error": "Not implemented yet",
        "audit_id": audit_id,
    }


@app.post("/report/{audit_id}/html", tags=["Reports"])
async def generate_html_report(audit_id: str):
    """
    Generate HTML executive dashboard for audit.
    
    Args:
        audit_id: The audit ID
        
    Returns:
        HTML dashboard
    """
    # TODO: Implement HTML generation
    return {
        "error": "Not implemented yet",
        "audit_id": audit_id,
    }


# ===== WEBHOOK ENDPOINTS =====

@app.post("/webhooks/github", tags=["Webhooks"])
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
):
    """
    GitHub webhook endpoint for event-driven audits.
    
    Configure in GitHub:
    1. Repository Settings → Webhooks
    2. Payload URL: https://your-domain/webhooks/github
    3. Content type: application/json
    4. Events: Push, Pull requests, Releases
    5. Set secret matching GITHUB_WEBHOOK_SECRET env var
    """
    try:
        # Get raw body for signature validation
        body = await request.body()
        
        # Validate signature if secret is configured
        if settings.github_webhook_secret:
            if not x_hub_signature_256:
                logger.warning("GitHub webhook received without signature")
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing signature"}
                )
            
            if not WebhookValidator.validate_github_signature(
                body, x_hub_signature_256, settings.github_webhook_secret
            ):
                logger.warning("GitHub webhook signature validation failed")
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid signature"}
                )
        
        # Parse payload
        import json
        payload_dict = json.loads(body)
        payload = GitHubWebhookPayload(**payload_dict)
        
        # Convert to normalized event
        event = GitHubWebhookHandler.parse_payload(payload)
        if not event:
            logger.debug("GitHub webhook event not relevant for auditing")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored"}
            )
        
        # Queue for processing
        event_id = webhook_queue.enqueue(event)
        
        logger.info(f"GitHub webhook queued: {event_id} ({event.owner}/{event.repo})")
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "event_id": event_id,
                "repository": f"{event.owner}/{event.repo}",
                "event_type": event.event_type.value,
            }
        )
        
    except Exception as e:
        logger.error(f"GitHub webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


@app.post("/webhooks/gitlab", tags=["Webhooks"])
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: str = Header(None),
):
    """
    GitLab webhook endpoint for event-driven audits.
    
    Configure in GitLab:
    1. Project Settings → Webhooks
    2. URL: https://your-domain/webhooks/gitlab
    3. Events: Push, Merge requests, Releases
    4. Set secret token matching GITLAB_WEBHOOK_SECRET env var
    """
    try:
        # Get raw body for signature validation
        body = await request.body()
        
        # Validate token if secret is configured
        if settings.gitlab_webhook_secret:
            if not x_gitlab_token:
                logger.warning("GitLab webhook received without token")
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing token"}
                )
            
            if not WebhookValidator.validate_gitlab_signature(
                body, x_gitlab_token, settings.gitlab_webhook_secret
            ):
                logger.warning("GitLab webhook token validation failed")
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid token"}
                )
        
        # Parse payload
        import json
        payload_dict = json.loads(body)
        payload = GitLabWebhookPayload(**payload_dict)
        
        # Convert to normalized event
        event = GitLabWebhookHandler.parse_payload(payload)
        if not event:
            logger.debug("GitLab webhook event not relevant for auditing")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored"}
            )
        
        # Queue for processing
        event_id = webhook_queue.enqueue(event)
        
        logger.info(f"GitLab webhook queued: {event_id} ({event.owner}/{event.repo})")
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "event_id": event_id,
                "repository": f"{event.owner}/{event.repo}",
                "event_type": event.event_type.value,
            }
        )
        
    except Exception as e:
        logger.error(f"GitLab webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


@app.get("/webhooks/status", tags=["Webhooks"])
async def webhook_status():
    """
    Get webhook queue status.
    
    Returns:
        Queue status and pending events
    """
    return webhook_queue.get_queue_status()



if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment != "production",
        log_level=settings.log_level.lower(),
    )
