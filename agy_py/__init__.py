"""agy-py: a thin Python wrapper around Google Antigravity's `agy` CLI binary.

The public surface lives in :mod:`agy_py.core` (the binary runner and config
helpers) and :mod:`agy_py.cli` (the Click command-line interface).
"""

from .core import AgyError, AgyRunner, Result, find_binary

__version__ = "0.1.0"

__all__ = ["AgyError", "AgyRunner", "Result", "find_binary", "__version__"]
