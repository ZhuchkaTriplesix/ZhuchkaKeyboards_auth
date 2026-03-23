"""Smoke test: application factory loads without side effects."""
from src.configuration.app import App


def test_app_factory():
    app = App().app
    assert app.title == "Api microservice"
