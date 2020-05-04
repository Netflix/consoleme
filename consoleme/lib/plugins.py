import pkgutil
from typing import Any

import pkg_resources


def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def get_plugin_by_name(plugin_name: str) -> Any:
    plugins = []
    for ep in pkg_resources.iter_entry_points("consoleme.plugins"):
        plugins.append(ep.name)
        if ep.name == plugin_name:
            return ep.load()
    initial_exception_message = f"Could not find the specified plugin: {plugin_name}. "
    if plugin_name == "default_config":
        initial_exception_message = (
            f"Could not find the specified plugin: {plugin_name}. "
            "Please install it with `pip install -e default_plugins` "
            "from the ConsoleMe directory. "
        )

    exception_message = (
        initial_exception_message + f"Plugins found: {', '.join(plugins)}. "
        f"Make sure you've set the environment variable CONSOLEME_CONFIG_ENTRYPOINT to the name of your configuration "
        f"entrypoint, otherwise it will default to `default_config`."
    )

    raise Exception(exception_message)
