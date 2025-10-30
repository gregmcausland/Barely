# Tests

This directory contains all test files for the Barely project.

## Structure

Tests are organized by feature/phase:

- **CLI Tests**: Test command-line interface functionality
  - `test_comma_separated.py` - Bulk operations with comma-separated IDs
  - `test_default_repl.py` - Default REPL launch behavior

- **REPL Tests**: Test REPL functionality
  - `test_completer.py` - Command completion
  - `test_context_and_pickers.py` - Context management and pickers

- **Core/Integration Tests**: Test core functionality and integration
  - `test_flag_fixes.py` - Flag handling and filtering
  - `test_phase1.py` - Foundation (repository layer)
  - `test_phase2.py` - Core service layer
  - `test_phase3.py` - Minimal CLI
  - `test_phase4.py` - Basic REPL
  - `test_phase5.py` - Projects and organization
  - `test_phase6.py` - Pull-based workflow

## Running Tests

All tests can be run with pytest:

```bash
pytest tests/
```

Or run specific test files:

```bash
pytest tests/test_phase1.py
```

Many tests can also be run directly:

```bash
python tests/test_phase1.py
```

## Configuration

- `conftest.py` - Shared pytest configuration and fixtures
  - Handles path setup for imports
  - Fixes Windows console encoding for all tests
  - Provides common fixtures (e.g., temporary database for tests)

## Test Patterns

- Tests use pytest fixtures for isolation (e.g., temporary databases)
- CLI tests use subprocess to test actual command execution
- Service/repository tests use mocked or temporary databases
- Direct execution (`if __name__ == "__main__"`) is supported for many tests

