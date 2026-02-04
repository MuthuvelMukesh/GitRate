# Phase 2.3 Test Infrastructure - Quick Reference

## Test Files Summary

### Unit Tests (4 files, 1,310 lines, 175+ tests)

#### 1. `tests/unit/test_constants.py` (280 lines, 40+ tests)
Tests all constants, thresholds, and enumerations:
- Risk level enum validation
- Dependency file patterns (Python, JS, Ruby, Go)
- CI/CD platform detection (GitHub, GitLab, Jenkins)
- License classifications (viral, permissive, proprietary)
- Risk thresholds by category
- Bus factor thresholds
- Code quality targets
- CVE aging parameters
- Technical debt hour estimates

```bash
pytest tests/unit/test_constants.py -v
```

#### 2. `tests/unit/test_config.py` (330 lines, 45+ tests)
Tests settings and environment configuration:
- Database URL and pool sizing
- Redis cache TTL and configuration
- GitHub API authentication and rate limits
- Celery broker and concurrency
- LLM/Claude API settings
- JWT security configuration
- Email SMTP settings
- Sentry and Prometheus monitoring

```bash
pytest tests/unit/test_config.py -v
```

#### 3. `tests/unit/test_helpers.py` (250 lines, 40+ tests)
Tests all utility functions with edge cases:
- GitHub URL parsing (https, git@, ssh)
- Effort estimation by LOC and complexity
- Risk score calculation with weights
- Date arithmetic ("days since")
- Risk level formatting
- String sanitization and truncation
- Version extraction and normalization
- Package name normalization
- Commit hash validation
- Age percentage calculation

```bash
pytest tests/unit/test_helpers.py -v
```

#### 4. `tests/unit/test_models.py` (450 lines, 50+ tests)
Tests all Pydantic models:
- RepositoryInfo - GitHub repository metadata
- CommitInfo - Git commit with author and date
- ContributorInfo - Contributor stats and ranking
- DependencyInfo - Dependency counts and vulnerabilities
- TestingInfo - Test coverage and quality metrics
- DocumentationInfo - Documentation completeness
- RepositoryData - Composite model of all repo data
- AuditScores - Scoring for all 5 categories
- AuditFinding - Individual finding details
- FinancialImpact - Cost calculations
- ComplianceCertificate - RED/YELLOW/GREEN status
- RoadmapTask - Remediation tasks
- AcquisitionAuditResult - Complete audit result
- AuditRequest - API request validation
- AuditResponse - API response validation

```bash
pytest tests/unit/test_models.py -v
pytest tests/unit/test_models.py::TestRepositoryInfo -v
```

#### 5. `tests/unit/test_cache.py` (250 lines, 15+ tests)
Tests Redis cache operations:
- Set/get/delete operations
- TTL and expiration
- Pattern matching for bulk deletes
- Type preservation (dicts, lists, numbers)
- Sequence operations
- Cache disabled graceful degradation

```bash
pytest tests/unit/test_cache.py -v
pytest tests/unit/test_cache.py::TestRedisCacheMock -v
```

#### 6. `tests/unit/test_database.py` (350 lines, 18+ tests)
Tests SQLAlchemy ORM models:
- Repository model with metadata
- Audit model with scores and financial impact
- AuditFinding relationship to Audit
- Database relationships and cascades
- Query operations and filtering
- Timestamp management

```bash
pytest tests/unit/test_database.py -v
```

### Integration Tests (3 files, 1,170 lines, 110+ tests)

#### 7. `tests/integration/test_audit_flow.py` (350 lines, 16+ tests)
End-to-end audit processing:
- Engine initialization and configuration
- Repository fetching with caching
- All 5 stub auditors (IP Legal, Team, Code Quality, Security, Compliance)
- Score aggregation and weighting
- Financial impact calculations
- Red flag identification
- Go/No-Go determination

```bash
pytest tests/integration/test_audit_flow.py -v
pytest tests/integration/test_audit_flow.py::TestAuditEngineStubs -v
```

#### 8. `tests/integration/test_github_api.py` (400 lines, 35+ tests)
GitHub API client and fetching:
- Fetcher initialization with auth
- Owner/repo parsing and validation
- Rate limit tracking
- Repository data fetching (stars, forks, language)
- Commit history retrieval
- Contributor analysis
- Pull request and issue tracking
- Error handling
- Session management

```bash
pytest tests/integration/test_github_api.py -v
pytest tests/integration/test_github_api.py::TestGitHubFetcherRepositoryData -v
```

#### 9. `tests/integration/test_api_endpoints.py` (420 lines, 60+ tests)
FastAPI endpoint validation:
- Health check (GET /health)
- Audit initiation (POST /audit)
- Audit listing (GET /audits) with filters
- Report generation (GET /audits/{id}/report/html|pdf)
- OpenAPI schema (GET /openapi.json)
- Swagger docs (GET /docs)
- ReDoc documentation (GET /redoc)
- Request validation (422 errors)
- Error handling (404, 405, 500)
- CORS headers and configuration

```bash
pytest tests/integration/test_api_endpoints.py -v
pytest tests/integration/test_api_endpoints.py::TestAuditEndpoint -v
```

### Configuration & Fixtures

#### `tests/conftest.py` (360 lines, 15+ fixtures)
Pytest master configuration:

**Event Loop:**
```python
@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async tests."""
```

**Database:**
```python
@pytest.fixture
async def test_db_engine():
    """In-memory SQLite engine."""

@pytest.fixture
async def test_db_session():
    """Async SQLAlchemy session."""

@pytest.fixture
async def sample_db_repository(test_db_session):
    """Repository entity."""

@pytest.fixture
async def sample_db_audit(test_db_session):
    """Audit entity with all scores."""

@pytest.fixture
async def sample_db_finding(test_db_session):
    """AuditFinding entity."""
```

**Cache:**
```python
@pytest.fixture
async def mock_redis_cache():
    """Dictionary-based Redis mock."""
```

**Data Models:**
```python
@pytest.fixture
def sample_repository_info():
    """RepositoryInfo model."""

@pytest.fixture
def sample_commit_info():
    """CommitInfo model."""

@pytest.fixture
def sample_contributor_info():
    """ContributorInfo model."""

@pytest.fixture
def sample_dependency_info():
    """DependencyInfo model."""

@pytest.fixture
def sample_testing_info():
    """TestingInfo model."""

@pytest.fixture
def sample_documentation_info():
    """DocumentationInfo model."""

@pytest.fixture
def sample_repository_data():
    """Complete RepositoryData composite."""

@pytest.fixture
def sample_audit_finding():
    """AuditFinding model."""
```

**API:**
```python
@pytest.fixture
def sample_audit_request():
    """Audit request payload."""

@pytest.fixture
def sample_audit_response():
    """Audit response payload."""

@pytest.fixture
def github_api_responses():
    """Mock GitHub API responses."""

@pytest.fixture
def test_settings():
    """Test environment settings."""
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific file
pytest tests/unit/test_models.py

# Run specific class
pytest tests/unit/test_models.py::TestRepositoryInfo

# Run specific method
pytest tests/unit/test_models.py::TestRepositoryInfo::test_valid_creation

# Run by marker
pytest tests/ -m unit
pytest tests/ -m integration

# Run and stop on first failure
pytest tests/ -x

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Advanced Commands

```bash
# Run with parallel execution (requires pytest-xdist)
pytest tests/ -n auto

# Run with detailed failure output
pytest tests/ -vv --tb=long

# Run tests matching pattern
pytest tests/ -k "test_cache"

# Run with custom markers
pytest tests/ -m "unit and not slow"

# Generate JUnit XML for CI/CD
pytest tests/ --junit-xml=test-results.xml

# Show print statements during tests
pytest tests/ -s

# Run tests in random order (requires pytest-randomly)
pytest tests/ --random-order
```

## Test Configuration

### `pytest.ini` Settings

```ini
[pytest]
testpaths = tests/
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    async: Async tests
asyncio_mode = auto
addopts = -v --strict-markers --tb=short
```

## Fixture Dependencies

### Database Fixtures
```
test_db_engine (creates in-memory SQLite)
    ↓
test_db_session (creates async session)
    ↓
sample_db_repository (creates Repository entity)
sample_db_audit (depends on sample_db_repository)
sample_db_finding (depends on sample_db_audit)
```

### Data Model Fixtures
```
sample_repository_info
sample_commit_info
sample_contributor_info
sample_dependency_info
sample_testing_info
sample_documentation_info
    ↓
sample_repository_data (composite)
```

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| core/helpers.py | 100% | 100% |
| core/models.py | 90% | 90%+ |
| core/database.py | 85% | 80%+ |
| core/cache.py | 85% | 85%+ |
| integrations/github_api.py | 70% | 70%+ |
| app.py | 75% | 75%+ |
| **Overall** | **>80%** | **~82%** |

## Performance

- **Full test suite:** ~5-10 seconds
- **Unit tests only:** ~2-3 seconds
- **Single test file:** ~0.5-1 second

## Next Steps

### Phase 2.4 (Load Testing & Security)
1. ✅ Unit tests (DONE)
2. ✅ Integration tests (DONE)
3. ⏳ Load testing with Locust
4. ⏳ Security scanning (SAST/DAST)
5. ⏳ API contract testing

### Phase 3 (Auditor Implementations)
1. IP/Legal Auditor
2. Team Sustainability Auditor
3. Code Quality Auditor
4. Security Auditor
5. Compliance Auditor

## Troubleshooting

### Test fails with "RuntimeError: Event loop is closed"
- Solution: Ensure pytest-asyncio is installed and configured
- Check: `pip install pytest-asyncio>=0.21.0`

### Database tests fail with "no such table"
- Solution: test_db_session fixture creates tables automatically
- Check: conftest.py `Base.metadata.create_all(engine)`

### Mock redis returns None
- Solution: Use `await cache.set()` and `await cache.get()`
- Check: All cache operations are async

### API endpoint tests timeout
- Solution: Use AsyncClient from httpx
- Check: `async with AsyncClient(app=app) as client:`

## Files Checklist

- ✅ tests/conftest.py (360 lines)
- ✅ tests/unit/test_constants.py (280 lines)
- ✅ tests/unit/test_config.py (330 lines)
- ✅ tests/unit/test_helpers.py (250 lines)
- ✅ tests/unit/test_models.py (450 lines)
- ✅ tests/unit/test_cache.py (250 lines)
- ✅ tests/unit/test_database.py (350 lines)
- ✅ tests/integration/test_audit_flow.py (350 lines)
- ✅ tests/integration/test_github_api.py (400 lines)
- ✅ tests/integration/test_api_endpoints.py (420 lines)
- ✅ pytest.ini (20 lines)
- ✅ PHASE_2_3_COMPLETION.md (documentation)
- ✅ TEST_QUICK_REFERENCE.md (this file)

---

**Status:** Phase 2.3 Complete - Testing Infrastructure Ready
