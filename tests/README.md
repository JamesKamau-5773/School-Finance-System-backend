# Test Suite Documentation

## Overview

This comprehensive test suite covers:
- **Unit tests** for Models, Repositories, Services, and SMS integration
- **Integration tests** for API Controllers and complete workflows
- **Data integrity** and consistency checks
- **Error handling** and edge cases

## Test Coverage

### Unit Tests

#### `test_inventory_service.py`
Tests the core business logic for inventory management:
- Record usage (consumption) with proper validation
- Stock level updates and audit logging
- Low stock alert triggering
- Stock prediction calculations
- Database error handling and rollbacks

**17+ test cases**

#### `test_inventory_repository.py`
Tests data access layer operations:
- Get all items and get by ID
- Update stock levels (positive, negative, zero)
- Add audit log entries
- Decimal precision maintenance
- Data persistence verification

**19+ test cases**

#### `test_sms_service.py`
Tests SMS receipt functionality with Africa's Talking API:
- Message formatting
- Phone number validation
- Currency formatting
- Special character handling
- API error handling and graceful degradation
- Configuration validation

**14+ test cases**

### Model Tests

#### `test_inventory_models.py`
Tests database models and ORM functionality:
- Inventory model creation and relationships
- InventoryLog audit trail entries
- UUID auto-generation
- Timestamp management
- Foreign key constraints
- Cascade delete behavior
- Decimal precision for quantities

**22+ test cases**

### Integration Tests

#### `test_inventory_controller.py`
Tests REST API endpoints:
- `GET /api/inventory/status` - Fetch stock predictions
  - Authentication validation
  - Predictions format and accuracy
  - Multiple items handling
  
- `POST /api/inventory/consume` - Record consumption
  - Valid consumption recording
  - Insufficient stock rejection
  - Low stock alert generation
  - User authentication
  - Input validation (missing fields, invalid IDs)
  - Default values
  - Decimal quantities

- `POST /api/inventory/add-stock` - Stock-in operations
  - Endpoint existence
  - Implementation placeholder

**23+ test cases**

#### `test_inventory_workflow.py`
Tests complete end-to-end workflows:
- Full inventory cycle (create → consume → predict)
- Multiple consumption sequence tracking
- Audit trail chain completeness
- Stock prediction accuracy over time
- Low stock alert progression
- Concurrent modification handling
- Data integrity and consistency
- Timestamp monotonicity

**11+ test cases**

---

## Running the Tests

### Install test dependencies
```bash
pip install -r requirements-test.txt
```

### Run all tests
```bash
pytest tests/
```

### Run specific test module
```bash
pytest tests/unit/test_inventory_service.py
pytest tests/integration/test_inventory_controller.py
```

### Run specific test class
```bash
pytest tests/unit/test_inventory_service.py::TestInventoryServiceRecordUsage
```

### Run specific test
```bash
pytest tests/unit/test_inventory_service.py::TestInventoryServiceRecordUsage::test_record_usage_success
```

### Run with coverage report
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with markers
```bash
pytest tests/ -m unit      # Only unit tests
pytest tests/ -m integration  # Only integration tests
```

---

## Test Fixtures

The `conftest.py` provides:

### App & Database
- `app` - Flask test app with in-memory SQLite database
- `client` - Test client for making HTTP requests
- `reset_db` - Autouse fixture to reset database before each test

### Users & Auth
- `admin_user` - Admin user with full permissions
- `regular_user` - Regular user with read-only permissions
- `admin_token` - JWT token for admin user
- `user_token` - JWT token for regular user

### Inventory
- `inventory_item` - Sample item with 100 units at reorder_level=20
- `low_stock_item` - Sample item at 15 units (below reorder_level=20)
- `inventory_log` - Sample audit log entry

### Headers
- `auth_headers` - Pre-built authorization headers with JWT
- `json_headers` - Content-Type: application/json

---

## Key Testing Patterns

### 1. Database Isolation
Each test runs in its own transaction. The `reset_db` fixture automatically rolls back between tests.

```python
def test_something(self, app, inventory_item):
    with app.app_context():
        # Test code here
        item = Inventory.query.get(inventory_item.id)
```

### 2. Authentication Testing
Use JWT tokens for authenticated endpoints:

```python
def test_authenticated_endpoint(self, client, admin_token, json_headers):
    headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
    response = client.get('/api/inventory/status', headers=headers)
```

### 3. Error Cases
Verify both success and failure paths:

```python
def test_success_case(self, app, inventory_item, admin_user):
    # Test happy path

def test_error_case(self, app, admin_user):
    # Test with invalid input
    result, status_code = InventoryService.record_usage(
        item_id=uuid.uuid4(),  # Invalid ID
        ...
    )
    assert status_code == 400
```

### 4. Mocking External Services
Mock Africa's Talking API calls:

```python
@patch('app.services.sms_service.africastalking.SMS')
def test_sms_service(self, mock_sms, app):
    # Mock implementation
```

---

## Test Statistics

- **Total Test Cases**: 106+
- **Modules Tested**: 5 (Models, Repository, Service, Controller, Workflows)
- **Lines of Test Code**: 2000+
- **Coverage Target**: 85%+ for core inventory functionality

---

## Continuous Integration

Run tests in CI/CD pipeline:

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-test.txt

# Run tests with coverage
pytest tests/ --cov=app --cov-report=xml --cov-report=term

# Generate HTML report
pytest tests/ --cov=app --cov-report=html
```

---

## Debugging Tests

### Run with pdb on failure
```bash
pytest tests/ --pdb
```

### Show print statements
```bash
pytest tests/ -s
```

### Show full tracebacks
```bash
pytest tests/ --tb=long
```

### Run single test with debug
```bash
pytest tests/unit/test_inventory_service.py::TestInventoryServiceRecordUsage::test_record_usage_success -vv -s
```

---

## Best Practices

1. **Use fixtures** for common setup (users, items, tokens)
2. **Test one thing per test** - clear test names describe what's tested
3. **Use app context** for database operations
4. **Mock external APIs** (SMS, payments, etc.)
5. **Test both success and failure paths**
6. **Verify audit trails** and side effects
7. **Check response formats** and HTTP status codes
8. **Test edge cases** (zero values, large amounts, special characters)

---

## Adding New Tests

1. Create test file in appropriate directory:
   - `tests/unit/test_*.py` - Unit tests
   - `tests/integration/test_*.py` - Integration tests
   - `tests/models/test_*.py` - Model tests

2. Use existing fixtures from `conftest.py`

3. Follow naming convention: `test_<what_you_test>_<expected_outcome>`

4. Example:
```python
def test_record_consumption_triggers_low_stock_alert(self, app, low_stock_item, admin_user):
    """Should trigger alert when stock below reorder level."""
    with app.app_context():
        result, status = InventoryService.record_usage(
            item_id=low_stock_item.id,
            quantity_used=1.0,
            user_id=admin_user.id,
            remarks='Test'
        )
        
        assert status == 201
        assert result['alert'] is not None
```

---

## Troubleshooting

### Tests fail with "No module named 'app'"
Ensure you're running from the backend directory:
```bash
cd /path/to/backend
pytest tests/
```

### Database locked errors
Tests are using in-memory SQLite which is thread-safe. If issues persist, ensure `-n0` (no parallel execution):
```bash
pytest tests/ -n0
```

### ImportError for models
Models must be imported before creating tables. Check `conftest.py` app fixture.

### JWT token issues
Ensure `JWT_SECRET_KEY` is set in `TestConfig` and matches across fixtures.

---

## Next Steps

1. Run test suite: `pytest tests/ -v`
2. Review coverage: `pytest tests/ --cov=app --cov-report=html`
3. Add missing tests for app features
4. Integrate into CI/CD pipeline
5. Monitor and improve coverage over time
