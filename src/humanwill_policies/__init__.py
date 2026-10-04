"""Company policy bundles, evaluation, authenticated service and host connectors."""

__version__ = "0.2.0b2"

__all__ = [
    "Bundle",
    "Configuration",
    "Limits",
    "PolicyError",
    "load_bundle",
    "load_configuration",
    "preview",
]


def __getattr__(name):
    # Preserve the public Python API without loading the policy engine for hooks.
    from importlib import import_module

    modules = {
        "Bundle": "bundle",
        "Limits": "bundle",
        "load_bundle": "bundle",
        "Configuration": "config",
        "load_configuration": "config",
        "preview": "config",
        "PolicyError": "errors",
    }
    if name not in modules:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{modules[name]}", __name__), name)
    globals()[name] = value
    return value
