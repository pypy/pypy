from rpython.rtyper.module.ll_os_environ import getenv_llimpl

from pypy.interpreter.gateway import unwrap_spec


@unwrap_spec(name=str)
def real_getenv(space, name):
    """Get an OS environment value skipping Python cache"""
    return space.wrap(getenv_llimpl(name))
