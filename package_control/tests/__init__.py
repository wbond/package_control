from sys import modules

if "sublime" not in modules:
    import importlib.machinery
    import os

    PACKAGE_ROOT = os.path.dirname(__file__)

    # Mock the sublime module for CLI usage
    sublime = importlib.machinery.SourceFileLoader(
        "sublime",
        os.path.join(PACKAGE_ROOT, "mock_sublime.py")
    ).load_module()

    # Mock the sublime_plugin module for CLI usage
    sublime_plugin = importlib.machinery.SourceFileLoader(
        "sublime_plugin",
        os.path.join(PACKAGE_ROOT, "mock_sublime_plugin.py")
    ).load_module()
