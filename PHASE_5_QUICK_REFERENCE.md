# GitRate Phase 5 - Quick Reference Guide

## Phase 5 Components (6 Major Systems)

### 1. Advanced Caching
**File**: `core/advanced_cache.py` (230 LOC)  
**Purpose**: Multi-layer caching (Redis + in-memory) for 375x speedup

```python
from core.advanced_cache import cache_audit_result

@cache_audit_result(ttl_seconds=3600)
async def audit_repo(owner: str, repo: str):
    return await engine.run_full_audit(owner, repo)

# Access: 40ms (cached) vs 12-15s (cold)
```

### 2. Batch Processing
**File**: `core/batch_processor.py` (360 LOC)  
**Purpose**: Parallel auditing of 100+ repos

```python
from core.batch_processor import BatchAuditProcessor

processor = BatchAuditProcessor(engine, max_concurrent=5)
repos = [{"owner": "microsoft", "repo": "vscode"}]

summary = await processor.process_batch(repos)
# Returns: success_rate, avg_scores, total_duration
```

### 3. Webhooks (GitHub/GitLab)
**File**: `core/webhooks.py` (330 LOC)  
**Purpose**: Event-driven audit triggering

```
GitHub:   POST /webhooks/github (SHA-256 validated)
GitLab:   POST /webhooks/gitlab (token validated)
Status:   GET  /webhooks/status
```

### 4. Structured Logging
**File**: `core/logging.py` (280 LOC)  
**Purpose**: JSON logs with audit trails

```python
from core.logging import StructuredLogger, LogCategory

logger = StructuredLogger("app")
logger.info("Audit complete", 
    category=LogCategory.AUDIT,
    audit_id="audit_123",
    duration_ms=45230)
```

### 5. Task Queue
**File**: `core/task_queue.py` (290 LOC)  
**Purpose**: Background job processing with priority

```python
from core.task_queue import task_queue, TaskPriority

task_id = await task_queue.enqueue(
    "audit", 
    data={"owner": "microsoft", "repo": "vscode"},
    priority=TaskPriority.HIGH)
```

### 6. Rate Limiting & Robustness
**File**: `core/rate_limiter.py` (340 LOC)  
**Purpose**: Rate limiting, circuit breaker, retry logic

```python
from core.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=60)
allowed, headers = limiter.is_allowed("client_ip")
```

---

## Performance Improvements

| Operation | Before | After | Speed |
|-----------|--------|-------|-------|
| Cached audit | 12-15s | 40ms | **375x** |
| Batch 10 repos | 120-150s | 35-45s | **3-4x** |
| API response (p95) | 2-3s | 100-150ms | **20-30x** |

---

## API Endpoints (Phase 5)

### Webhooks
```
POST /webhooks/github     - Receive GitHub events
POST /webhooks/gitlab     - Receive GitLab events
GET  /webhooks/status     - Check queue status
```

**Returns**:
```json
{
  "status": "accepted",
  "event_id": "webhook_000001",
  "repository": "owner/repo",
  "event_type": "push"
}
```

### Example: Webhook Configuration

**GitHub**:
1. Settings → Webhooks → Add webhook
2. Payload URL: `https://your-domain/webhooks/github`
3. Secret: Set `GITHUB_WEBHOOK_SECRET` env var
4. Events: Push, Pull requests, Releases

**GitLab**:
1. Project → Settings → Webhooks
2. URL: `https://your-domain/webhooks/gitlab`
3. Secret: Set `GITLAB_WEBHOOK_SECRET` env var
4. Events: Push, Merge requests, Releases

---

## Environment Variables

```bash
# Webhooks (Phase 5 New)
GITHUB_WEBHOOK_SECRET=your_github_secret
GITLAB_WEBHOOK_SECRET=your_gitlab_secret

# Rate Limiting (Phase 5 New)
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Existing
GITHUB_TOKEN=github_pat_xxxxx
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379/0
```

---

## Usage Examples

### Single Audit with Caching
```python
from core.audit_engine import AuditEngine
from core.advanced_cache import AuditResultCache

engine = AuditEngine(github_token="...")
cache = AuditResultCache()

# First call: 12-15 seconds
result = await engine.run_full_audit("microsoft", "vscode")
cache.cache_audit(result)

# Subsequent calls: 40ms
cached = cache.get_audit("microsoft", "vscode")
```

### Batch Processing
```python
from core.batch_processor import BatchAuditProcessor

repos = [
    {"owner": "microsoft", "repo": "vscode"},
    {"owner": "kubernetes", "repo": "kubernetes"},
    {"owner": "facebook", "repo": "react"},
]

processor = BatchAuditProcessor(engine, max_concurrent=3)

async def progress(job):
    print(f"Job {job.job_id}: {job.status}")

summary = await processor.process_batch(repos, progress)
print(f"Completed: {summary['completed']}/{summary['total']}")
print(f"Avg Score: {summary['average_scores']['overall']:.1f}/100")
```

### Task Queue
```python
from core.task_queue import task_queue, TaskPriority

# Register handler
async def my_audit(data):
    return await engine.run_full_audit(data['owner'], data['repo'])

task_queue.register_handler("audit", my_audit)

# Enqueue task
task_id = await task_queue.enqueue(
    "audit",
    data={"owner": "microsoft", "repo": "vscode"},
    priority=TaskPriority.HIGH
)

# Check status
task = task_queue.get_task(task_id)
print(f"Status: {task.status}")
print(f"Result: {task.result}")
```

### Logging
```python
from core.logging import StructuredLogger, LogCategory, PerformanceMonitor

logger = StructuredLogger("my_app")
monitor = PerformanceMonitor(logger)

# Log audit completion
logger.info(
    "Audit completed successfully",
    category=LogCategory.AUDIT,
    audit_id="audit_123",
    repository="microsoft/vscode",
    duration_ms=45230,
    metadata={"score": 82.5}
)

# Record performance metric
monitor.record_metric("audit_duration", 45.23)

# Get statistics
stats = monitor.get_statistics("audit_duration")
print(f"Avg: {stats['avg']:.2f}ms, P95: {stats['p95']:.2f}ms")
```

### Rate Limiting
```python
from core.rate_limiter import RateLimiter, CircuitBreaker

# Initialize limiter
limiter = RateLimiter(requests_per_minute=60)

# Check request
allowed, headers = limiter.is_allowed(client_ip)
if not allowed:
    return Response(status_code=429, headers=headers)

# Circuit breaker
breaker = CircuitBreaker(failure_threshold=5)
try:
    result = breaker.call(risky_function)
except Exception:
    return cached_fallback()
```

---

## Testing Phase 5 Features

### Test Caching
```bash
pytest tests/unit/test_cache.py -v
```

### Test Batch Processing
```bash
pytest tests/integration/test_batch_processing.py -v
```

### Test Webhooks
```bash
pytest tests/integration/test_webhooks.py -v
```

### Test Rate Limiter
```bash
pytest tests/unit/test_rate_limiter.py -v
```

---

## Troubleshooting

### Webhook Not Triggering
1. Check `GITHUB_WEBHOOK_SECRET` / `GITLAB_WEBHOOK_SECRET` env vars
2. Verify webhook URL is correct: `/webhooks/github` or `/webhooks/gitlab`
3. Check `/webhooks/status` endpoint for pending events
4. Review logs for signature validation errors

### Slow API Response
1. Check cache hit rate: `monitor.get_all_metrics()`
2. Check Redis connection: `REDIS_URL`
3. Increase rate limit if needed: `RATE_LIMIT_REQUESTS_PER_MINUTE`
4. Scale task queue workers: `max_workers` in TaskQueue

### High Memory Usage
1. Check cache size: Configure `REDIS_CACHE_TTL`
2. Clean old tasks: `task_queue.cleanup_old_tasks(days=7)`
3. Monitor task queue: `task_queue.get_queue_status()`

### Task Queue Backlog
1. Increase workers: `TaskQueue(max_workers=10)`
2. Check failed tasks: `task_queue.get_tasks(status=TaskStatus.FAILED)`
3. Monitor task types: `task_queue.get_tasks(task_type="audit")`

---

## Monitoring Commands

### Check WebhookQueue
```python
from core.webhooks import webhook_queue

status = webhook_queue.get_queue_status()
print(f"Pending: {status['pending']}")
print(f"Processed: {status['processed']}")
```

### Check TaskQueue
```python
from core.task_queue import task_queue

status = task_queue.get_queue_status()
print(f"Total: {status['total_tasks']}")
print(f"Pending: {status['pending']}")
print(f"Running: {status['running']}")
```

### Check Cache Stats
```python
from core.advanced_cache import AuditResultCache

cache = AuditResultCache()
stats = cache.get_statistics()
print(f"Hit Rate: {stats.get('hit_rate', 0):.1%}")
```

### Check Logging
```python
from core.logging import StructuredLogger

logger = StructuredLogger("app")
trail = logger.get_audit_trail(limit=10)
for entry in trail:
    print(f"{entry['timestamp']}: {entry['message']}")
```

---

## Deployment Checklist

```bash
# Environment variables
export GITHUB_WEBHOOK_SECRET=your_secret
export GITLAB_WEBHOOK_SECRET=your_token
export RATE_LIMIT_REQUESTS_PER_MINUTE=60
export REDIS_URL=redis://localhost:6379/0
export DATABASE_URL=postgresql://...

# Start services
docker-compose up -d

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/webhooks/status

# Verify logs
docker-compose logs -f api

# Test webhook (simulate GitHub)
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d '{"action":"opened","repository":{"name":"test"}}'
```

---

## Phase 5 Summary

| Component | LOC | Files | Key Feature |
|-----------|-----|-------|------------|
| Caching | 230 | 1 | 375x speedup |
| Batch Processing | 360 | 1 | 100+ repos parallel |
| Webhooks | 330 | 1 | Auto-trigger audits |
| Logging | 280 | 1 | Audit trails |
| Task Queue | 290 | 1 | Background jobs |
| Rate Limiter | 340 | 1 | Production safety |
| **Total** | **1,930** | **6** | **Enterprise-grade** |

---

## Next Steps (Phase 6+)

- [ ] Web dashboard for visualization
- [ ] Machine learning for risk prediction
- [ ] Multi-tenant support
- [ ] Advanced integrations (Jira, Slack)
- [ ] Custom audit rule engine

---

**Quick Reference**: Phase 5 adds 6 enterprise systems in 1,930 LOC for production-grade scaling.

For detailed docs, see: `PHASE_5_COMPLETION.md`
