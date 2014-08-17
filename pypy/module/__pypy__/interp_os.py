import os

from pypy.interpreter.gateway import unwrap_spec


@unwrap_spec(name='str0')
def real_getenv(space, name):
    """Get an OS environment value skipping Python cache"""
    return space.wrap(os.environ.get(name))
