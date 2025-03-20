"""Run all integration tests."""
import unittest
import sys
import os

def create_integration_test_suite():
    """Create a test suite with all integration tests."""
    # Use file system path to find tests instead of module path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(current_dir, pattern="test_*.py")
    return test_suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(create_integration_test_suite())
    sys.exit(0 if result.wasSuccessful() else 1)