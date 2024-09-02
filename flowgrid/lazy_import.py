from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import types
import importlib.util


__all__ = [
    'lazy',
    'LazyLoader',
]


def lazy(fullname: str) -> importlib.util._LazyModule:
    return LazyLoader(fullname, globals(), fullname)


"""A LazyLoader class."""


class LazyLoader(types.ModuleType):
    """Lazily import a module, mainly to avoid pulling in large dependencies.

    `contrib`, and `ffmpeg` are examples of modules that are large and
    not always needed, and this allows them to only be loaded when
    they are used.
    """

    # The lint error here is incorrect.
    def __init__(self, local_name, parent_module_globals, name):
        self._local_name = local_name
        self._parent_module_globals = parent_module_globals

        super(LazyLoader, self).__init__(name)

    def _load(self):
        # Import the target module and insert it into the parent's namespace
        module = importlib.import_module(self.__name__)
        self._parent_module_globals[self._local_name] = module

        # Update this object's dict so that if someone keeps a reference to the
        #   LazyLoader, lookups are efficient (__getattr__ is only
        #   called on lookups that fail).
        self.__dict__.update(module.__dict__)

        return module

    def __getattr__(self, item):
        module = self._load()
        return getattr(module, item)

    def __dir__(self):
        module = self._load()
        return dir(module)
