
from pypy.rlib.rsre import rsre_char
from pypy.rlib.rsre.rsre_core import match

def get_hacked_sre_compile(my_compile):
    """Return a copy of the sre_compile module for which the _sre
    module is a custom module that has _sre.compile == my_compile
    and CODESIZE == rsre_char.CODESIZE.
    """
    import sre_compile, __builtin__, new
    sre_hacked = new.module("_sre_hacked")
    sre_hacked.compile = my_compile
    sre_hacked.MAGIC = sre_compile.MAGIC
    sre_hacked.CODESIZE = rsre_char.CODESIZE
    sre_hacked.getlower = rsre_char.getlower
    def my_import(name, *args):
        if name == '_sre':
            return sre_hacked
        else:
            return default_import(name, *args)
    src = sre_compile.__file__
    if src.lower().endswith('.pyc') or src.lower().endswith('.pyo'):
        src = src[:-1]
    mod = new.module("sre_compile_hacked")
    default_import = __import__
    try:
        __builtin__.__import__ = my_import
        execfile(src, mod.__dict__)
    finally:
        __builtin__.__import__ = default_import
    return mod

class GotIt(Exception):
    pass
def my_compile(pattern, flags, code, *args):
    raise GotIt(code, flags, args)
sre_compile_hacked = get_hacked_sre_compile(my_compile)

def get_code(regexp, flags=0, allargs=False):
    try:
        sre_compile_hacked.compile(regexp, flags)
    except GotIt, e:
        pass
    else:
        raise ValueError("did not reach _sre.compile()!")
    if allargs:
        return e.args
    else:
        return e.args[0]
