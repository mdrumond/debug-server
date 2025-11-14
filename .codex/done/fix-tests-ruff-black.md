# Fix failing tests and linters

## Summary
- Updated `debug_server/db/models.py` to import the stdlib `UTC` constant and ensure the `utc_now()` helper always returns timezone-aware datetimes compatible with SQLModel defaults.
- Added UTC-aware timestamp handling in `debug_server/db/service.py`, including a helper to normalize stored datetimes before comparisons so authentication expiry checks no longer raise type errors.
- Kept the admin CLI (`debug_server/db/admin.py`) aligned with the UTC handling changes so manually created tokens also share the same semantics.

## Tests & Tooling
- `pytest`
- `ruff check`
- `black .`

### Test files covering this change
- `tests/db/test_models.py`
- `tests/integration/test_db_transactions.py`
