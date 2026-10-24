import pytest

from core.configuration.loader import load_catalog, resolve_experiment, validate_catalog, validate_experiment_readiness


def test_catalog_rejects_unknown_dataset_provider():
    catalog = load_catalog()
    catalog["datasets"]["bad_dataset"] = {
        "provider": "missing_provider",
        "symbol": "TEST",
        "interval": "1d",
    }
    with pytest.raises(ValueError, match="unknown provider"):
        validate_catalog(catalog)


def test_experiment_rejects_non_iso_dates():
    catalog = load_catalog()
    catalog["experiments"]["bad_dates"] = {
        "datasets": ["reliance_demo"],
        "strategies": ["ma_20_50"],
        "period": {"start": "01/01/2024", "end": "2024-12-31"},
    }
    with pytest.raises(ValueError, match="ISO format"):
        resolve_experiment(catalog, "bad_dates")


def test_unknown_experiment_fails_with_available_names():
    catalog = load_catalog()
    with pytest.raises(ValueError, match="Unknown experiment"):
        resolve_experiment(catalog, "not_a_real_experiment")
