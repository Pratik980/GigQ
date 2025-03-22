# GigQ Tests

This directory contains tests for the GigQ library. The tests are organized into two main categories:

## Unit Tests

Located in the `unit/` directory, these tests focus on validating individual components in isolation. Each unit test file focuses on a specific component:

- `test_job.py` - Tests for the `Job` class
- `test_job_queue.py` - Tests for the `JobQueue` class
- `test_worker.py` - Tests for the `Worker` class
- `test_workflow.py` - Tests for the `Workflow` class
- `test_table_formatter.py` - Tests for the custom table formatting utilities
- `test_cli.py` - Tests for the CLI functionality

## Integration Tests

Located in the `integration/` directory, these tests validate that components work together correctly. They test end-to-end functionality and component interactions:

- `test_basic.py` - Basic integration tests
- `test_basic_workflow.py` - Simple workflow integration
- `test_cli.py` - CLI integration tests
- `test_concurrent_workers.py` - Tests for concurrent worker processing
- `test_error_handling.py` - Tests for error handling
- `test_persistence.py` - Tests for persistence between sessions
- `test_timeout_handling.py` - Tests for timeout detection and handling
- `test_workflow_dependencies.py` - Tests for complex workflow dependencies

## Running Tests

You can run all tests, only unit tests, or only integration tests:

### Run All Tests

```bash
# Using the run_all.py script
python tests/run_all.py

# Using unittest discover
python -m unittest discover

# Using pytest
pytest tests
```

### Run Only Unit Tests

```bash
# Using the run_all.py script
python tests/unit/run_all.py

# Using unittest discover
python -m unittest discover tests/unit

# Using pytest
pytest tests/unit
```

### Run Only Integration Tests

```bash
# Using the run_all.py script
python tests/integration/run_all.py

# Using unittest discover
python -m unittest discover tests/integration

# Using pytest
pytest tests/integration
```

### Run a Specific Test File

```bash
# Using unittest
python -m unittest tests/unit/test_job.py

# Using pytest
pytest tests/unit/test_job.py
```

### Run a Specific Test Method

```bash
# Using unittest
python -m unittest tests.unit.test_job.TestJob.test_job_initialization

# Using pytest
pytest tests/unit/test_job.py::TestJob::test_job_initialization
```

## Test Organization

The test directory structure follows these conventions:

```
tests/
├── __init__.py
├── run_all.py            # Runs all tests
├── README.md             # This file
├── job_functions.py      # Shared test functions
├── unit/                 # Unit tests directory
│   ├── __init__.py
│   ├── run_all.py        # Runs all unit tests
│   ├── test_job.py
│   ├── test_job_queue.py
│   ├── test_worker.py
│   ├── test_workflow.py
│   ├── test_table_formatter.py
│   └── test_cli.py
└── integration/          # Integration tests directory
    ├── __init__.py
    ├── base.py           # Base class for integration tests
    ├── run_all.py        # Runs all integration tests
    └── test_*.py files
```

## Writing New Tests

When writing new tests:

1. **Unit Tests**: Place in the `unit/` directory and focus on testing a single component in isolation
2. **Integration Tests**: Place in the `integration/` directory and extend `IntegrationTestBase` from `integration/base.py`
3. Use descriptive method names that explain what aspect is being tested
4. Follow the Arrange-Act-Assert pattern
5. Clean up resources in `tearDown` methods
6. Add the test to the appropriate test file based on the component being tested

## Code Coverage

To run tests with code coverage reporting:

```bash
# Using pytest
pytest --cov=gigq tests

# Generate an HTML report
pytest --cov=gigq --cov-report=html tests
```

The HTML coverage report will be available in the `htmlcov/` directory.
