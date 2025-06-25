# MCP Server for Splunk - Test Suite

This directory contains comprehensive tests for the MCP Server for Splunk functionality.

## Test Structure

```
tests/
├── __init__.py                 # Python package marker
├── conftest.py                 # Pytest configuration and fixtures
├── test_splunk_client.py       # Splunk client connection tests
├── test_splunk_tools.py        # Splunk MCP tools tests
├── test_transport.py           # Transport method tests (stdio/HTTP)
└── README.md                   # This file
```

## Test Coverage

The test suite covers:

### Splunk Client Tests (`test_splunk_client.py`)
- **Connection Testing**: Mock-based tests for Splunk service connections
- **Environment Variable Handling**: Default values and configuration validation
- **Error Handling**: Connection failures, invalid credentials, invalid ports
- **Authentication**: Username/password and token-based authentication

### Transport Tests (`test_transport.py`)
- **Configuration Testing**: Environment variables, command line arguments, defaults
- **Stdio Transport**: Local communication mode, startup, error handling
- **HTTP Transport**: Remote communication mode, custom configuration, port binding
- **Main Function**: Transport routing, argument parsing, Docker environment
- **Integration**: Transport with Splunk connections, failure handling
- **Security**: Network binding options, localhost vs all interfaces

### Splunk Tools Tests (`test_splunk_tools.py`)
- **Health Check Tool**: Service connectivity and version information
- **Index Tools**: Listing and validation of Splunk indexes
- **Metadata Tools**: Sourcetype and source discovery
- **Search Tools**: Oneshot and regular search operations with various parameters
- **App and User Tools**: Application and user management functionality
- **KV Store Tools**: Collection listing and data retrieval
- **Configuration Tools**: Configuration file and stanza management
- **Integration Tests**: End-to-end workflow testing

## Running Tests

### Quick Start
```bash
# Run all tests with coverage
./scripts/run_tests.sh

# Run tests without coverage (faster)
./scripts/run_tests.sh --no-coverage

# Run with verbose output
./scripts/run_tests.sh -v
```

### Test Filtering
```bash
# Run only unit tests
./scripts/run_tests.sh -m unit

# Run specific test by name
./scripts/run_tests.sh -k test_health_check

# Run specific test class
./scripts/run_tests.sh -k TestSplunkHealthTool

# Fail fast (stop on first failure)
./scripts/run_tests.sh -x
```

### Coverage Reports
```bash
# Generate HTML coverage report
./scripts/run_tests.sh
# View report: open htmlcov/index.html

# Terminal coverage only
./scripts/run_tests.sh --no-html
```

## Test Configuration

### Environment Variables
Tests use mock environment variables defined in `conftest.py`:
- `SPLUNK_HOST`: localhost
- `SPLUNK_PORT`: 8089
- `SPLUNK_USERNAME`: admin
- `SPLUNK_PASSWORD`: password
- `SPLUNK_VERIFY_SSL`: false

### Test Markers
Tests are organized with markers for selective execution:
- `unit`: Unit tests (isolated component testing)
- `integration`: Integration tests (component interaction)
- `slow`: Tests that may take longer
- `network`: Tests requiring network access
- `splunk`: Splunk-specific functionality tests

## Mock Structure

### `MockSplunkService`
Mimics `splunklib.client.Service` with:
- Indexes collection with 4 sample indexes
- Apps collection with 3 sample apps
- Users collection with 2 sample users
- Jobs interface for search operations
- KV Store interface
- Configuration interface

### `MockSplunkContext`
Mimics FastMCP Context structure:
- Request context with lifespan context
- Service injection for tool testing

### Sample Data
- **Search Results**: 3 sample log entries with timestamps and metadata
- **KV Store Data**: User collection with roles and status
- **ResultsReader**: Mock for Splunk search result iteration

## Coverage Statistics

Current test coverage with **52 comprehensive tests**:
- **Overall**: 53% (330 statements, 154 missing)
- **server.py**: 61% (main functionality and transport methods)
- **splunk_client.py**: 96% (connection handling)
- **__init__.py**: 100% (package setup)

### Test Breakdown:
- **Transport Tests**: 27 tests covering stdio and HTTP transports
- **Splunk Tools Tests**: 19 tests covering all 12 MCP tools
- **Client Tests**: 6 tests covering connection scenarios

## Dependencies

Testing uses the following packages (installed via `uv`):
- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `pytest-asyncio`: Async test support
- `pytest-mock`: Enhanced mocking capabilities

## Adding New Tests

### For New Tools
1. Add tool function tests to `test_splunk_tools.py`
2. Mock the required Splunk service interfaces in `conftest.py`
3. Test both success and error scenarios
4. Include parameter validation tests

### For Client Functionality
1. Add tests to `test_splunk_client.py`
2. Use `@patch('src.splunk_client.client.Service')` for mocking
3. Test different authentication methods and connection scenarios

### Test Structure Template
```python
class TestNewFeature:
    """Test new feature functionality"""
    
    def test_success_case(self, mock_context):
        """Test successful operation"""
        result = server.new_feature_function(mock_context)
        assert "expected_key" in result
        
    def test_error_case(self, mock_context):
        """Test error handling"""
        mock_context.service.method.side_effect = Exception("Test error")
        with pytest.raises(Exception, match="Test error"):
            server.new_feature_function(mock_context)
```

## Best Practices

1. **Mock External Dependencies**: Always mock Splunk service connections
2. **Test Error Paths**: Include negative test cases for error handling
3. **Use Descriptive Names**: Test function names should describe the scenario
4. **Assert Comprehensively**: Verify both structure and content of results
5. **Isolate Tests**: Each test should be independent and not rely on others
6. **Document Test Intent**: Use clear docstrings for complex test scenarios

## Continuous Integration

The test suite is designed to run in CI/CD environments:
- No external Splunk dependencies required
- All connections are mocked
- Fast execution (< 2 seconds for full suite)
- Comprehensive coverage reporting
- Clear pass/fail status 