import os
import sys

from pypy.interpreter.gateway import unwrap_spec
from rpython.translator.platform import platform as compiler

_WIN32 = sys.platform == 'win32'


@unwrap_spec(name='text0')
def real_getenv(space, name):
    """Get an OS environment value skipping Python cache"""
    if _WIN32:
        # the narrow environment gives us the value in the ANSI code page,
        # which newtext() would then read as utf-8
        from rpython.rlib import rwin32
        value = rwin32._wgetenv(name)
    else:
        value = os.environ.get(name)
    return space.newtext_or_none(value)

# For annotation, pre-build this as a global
_multiarch = compiler.get_multiarch()

def _get_multiarch(space):
    """Get the platform-specific multiarch label.

    On linux, this returns something like "x86_64-linux-gnu"
    On macOS this returns "darwin" for CPython compatibility
    On windows it returns ""
    """
    return space.newtext(_multiarch)


