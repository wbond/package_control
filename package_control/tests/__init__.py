# flake8: noqa: F401
try:
    import sublime
except ImportError:
    # Mock the sublime API modules for CLI usage
    from sys import modules
    from . import mock_sublime
    from . import mock_sublime_plugin
    modules["sublime"] = mock_sublime
    modules["sublime_plugin"] = mock_sublime_plugin
