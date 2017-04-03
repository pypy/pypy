import os

from pypy.interpreter.gateway import unwrap_spec


@unwrap_spec(name='text0')
def real_getenv(space, name):
    """Get an OS environment value skipping Python cache"""
    return space.newtext_or_none(os.environ.get(name))
