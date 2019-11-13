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
    raise Exception(
        f"Could not find the specified plugin: {plugin_name}. "
        f"Plugins found: {', '.join(plugins)}"
    )
