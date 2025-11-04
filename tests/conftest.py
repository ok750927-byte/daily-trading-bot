import os
import builtins

# Replace builtin print on import (pytest imports conftest early), so that
# module-level prints in the project don't flood pytest output. This is
# test-only and controlled by SHOW_PRINTS env var.
_ORIGINAL_PRINT = builtins.print
if os.environ.get("SHOW_PRINTS") != "1":
    def _silent_print(*args, **kwargs):
        return

    builtins.print = _silent_print


def pytest_sessionfinish(session, exitstatus):
    # restore print at the end of the session to avoid side effects
    try:
        builtins.print = _ORIGINAL_PRINT
    except Exception:
        pass


def pytest_ignore_collect(path, config):
    """Ignore GUI-related test modules if PyQt6 is not installed.

    Some tests require PyQt6 (GUI integration). In CI or headless test
    environments PyQt6 may not be available; rather than causing an
    ImportError during collection we ignore those test modules so the test
    suite can run in typical CI environments. If you want to run GUI tests
    locally, install PyQt6 or set an env var to force collection.
    """
    try:
        # Only apply this rule to likely GUI test files
        name = path.basename.lower()
        if 'gui' in name or 'pyqt' in name:
            import importlib
            importlib.import_module('PyQt6')
    except ImportError:
        return True
    return False


import json
import requests
import pytest


class _SimpleRequestsMock:
    def __init__(self):
        # mapping: (METHOD, url) -> dict(status_code, text, json)
        self._map = {}

    def _register(self, method, url, **kwargs):
        self._map[(method.upper(), url)] = kwargs

    def post(self, url, **kwargs):
        return self._register('POST', url, **kwargs)

    def get(self, url, **kwargs):
        return self._register('GET', url, **kwargs)

    def _request(self, method, url, *args, **kwargs):
        key = (method.upper(), url)
        info = self._map.get(key)
        # default behavior: 404
        resp = requests.Response()
        if info is None:
            resp.status_code = 404
            resp._content = b''
            return resp

        resp.status_code = info.get('status_code', 200)
        if 'json' in info and info['json'] is not None:
            resp._content = json.dumps(info['json']).encode('utf-8')
            resp.headers['Content-Type'] = 'application/json'
        else:
            text = info.get('text', '')
            resp._content = (text or '').encode('utf-8')
        return resp


@pytest.fixture
def requests_mock(monkeypatch):
    """A tiny replacement for the requests-mock pytest fixture.

    Tests in this repo use a simple pattern: call requests_mock.post/get(url, ...)
    and then the code under test issues requests to that URL. This fixture
    monkeypatches requests.sessions.Session.request to return a prepared
    Response based on registrations.
    """
    mock = _SimpleRequestsMock()
    # Patch the Session.request method to call our mock's _request
    def _session_request(session_self, method, url, *args, **kwargs):
        return mock._request(method, url, *args, **kwargs)

    monkeypatch.setattr(requests.sessions.Session, 'request', _session_request)
    return mock
