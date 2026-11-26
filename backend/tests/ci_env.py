"""
Database tests: skip locally when no test database is configured, but never in CI.

In CI a missing TEST_DATABASE_URL or TEST_MONGODB_URI is a broken pipeline, not an optional feature: the tests
must fail so the problem is visible, instead of skipping and letting CI pass without exercising the database.
"""
import os

import pytest

IN_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true" or os.environ.get("CI", "").lower() in ("true", "1")


def database_url(variable: str) -> str:
    return os.environ.get(variable, "").strip()


def needs_database(variable: str):
    """Skip only outside CI when `variable` is unset; in CI the test runs and the fixture fails."""
    return pytest.mark.skipif(
        not database_url(variable) and not IN_CI,
        reason=f"{variable} is not set (local run without a test database; CI always provides one)",
    )


def require_database_url(variable: str) -> str:
    """The test database URL, or a clear failure (used by fixtures, so CI cannot pass without the database)."""
    url = database_url(variable)
    if not url:
        pytest.fail(f"{variable} is not set. CI must provide a throwaway database for these tests "
                    f"(see the service containers in .github/workflows/verify.yml).")
    return url


def assert_ci_provides(variable: str) -> None:
    """In CI, fail if the database URL is missing; outside CI there is nothing to check."""
    if not IN_CI:
        pytest.skip("only meaningful in CI")
    assert database_url(variable), f"CI job is missing {variable}; the database tests would not run"
