import builtins
import importlib
import sys

import pytest

import tests as tests_pkg


def test_tests_import_guard(monkeypatch):
    monkeypatch.delitem(sys.modules, "yaml", raising=False)
    orig = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "yaml":
            raise ModuleNotFoundError
        return orig(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ModuleNotFoundError):
        importlib.reload(tests_pkg)
