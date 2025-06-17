import os
import sys
import importlib

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import egg.utils as utils  # noqa: E402


class DummyEP:
    def __init__(self, name, func):
        self.name = name
        self._func = func

    def load(self):
        return self._func


def _reset_utils(monkeypatch):
    module = importlib.reload(importlib.import_module("egg.utils"))
    monkeypatch.setitem(sys.modules, "egg.utils", module)
    return module


def test_load_plugins_select(monkeypatch):
    mod = _reset_utils(monkeypatch)

    runtime_called = []
    agent_called = []

    def runtime():
        runtime_called.append(True)
        return {"ruby": ["ruby"]}

    def agent():
        agent_called.append(True)

    class Container:
        def select(self, *, group):
            if group == mod.RUNTIME_PLUGIN_GROUP:
                return [DummyEP("ruby", runtime)]
            if group == mod.AGENT_PLUGIN_GROUP:
                return [DummyEP("a", agent)]
            return []

    monkeypatch.setattr(mod, "entry_points", lambda: Container())
    # call select with an unknown group to cover the fallback branch
    Container().select(group="other")
    mod.load_plugins()

    assert runtime_called == [True]
    assert agent_called == [True]
    assert mod.DEFAULT_LANG_COMMANDS["ruby"] == ["ruby"]


def test_load_plugins_legacy(monkeypatch):
    mod = _reset_utils(monkeypatch)

    runtime_called = []
    agent_called = []

    def runtime():
        runtime_called.append(True)
        return {"ruby": ["ruby"]}

    def agent():
        agent_called.append(True)

    eps = {
        mod.RUNTIME_PLUGIN_GROUP: [DummyEP("ruby", runtime)],
        mod.AGENT_PLUGIN_GROUP: [DummyEP("a", agent)],
    }

    monkeypatch.setattr(mod, "entry_points", lambda: eps)
    mod.load_plugins()

    assert runtime_called == [True]
    assert agent_called == [True]
    assert mod.DEFAULT_LANG_COMMANDS["ruby"] == ["ruby"]
