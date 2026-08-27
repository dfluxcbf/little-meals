"""Pytest entry-point for Bazel py_test.

Bazel's py_test runner calls this file as __main__. It locates the test
directory from __file__ so that pytest can discover all test_*.py files
that are listed in the surrounding py_test srcs.
"""

import os
import sys

import pytest


def main() -> int:
    """Run pytest against the tests directory when executed as a script."""
    # In Bazel runfiles the test files live alongside this runner file.
    test_dir = os.path.dirname(os.path.abspath(__file__))
    args = [
        test_dir,
        "-v",
        "--tb=short",
        "--no-header",
        # Disable coverage inside Bazel; use `bazel coverage` instead.
        "--no-cov",
    ] + sys.argv[1:]
    return pytest.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
