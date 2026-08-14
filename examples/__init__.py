"""Sample manifests, notebook cells, and plug-ins for the egg CLI.

This package exists so the ``egg.runtimes`` and ``egg.agents`` entry points
declared in ``pyproject.toml`` resolve after installation. ``egg.utils`` also
imports :mod:`examples.ruby_plugin` here as a fallback when the distribution
metadata is unavailable.
"""
