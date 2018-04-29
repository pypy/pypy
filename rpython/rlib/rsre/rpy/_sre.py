from rpython.rlib.rsre import rsre_char, rsre_core
from rpython.rlib.rarithmetic import intmask

VERSION = "2.7.6"
MAGIC = 20031017
MAXREPEAT = rsre_char.MAXREPEAT
CODESIZE = rsre_char.CODESIZE
getlower = rsre_char.getlower


class GotIt(Exception):
    pass

def compile(pattern, flags, code, *args):
    raise GotIt(rsre_core.CompiledPattern([intmask(i) for i in code]), flags, args)


def get_code(regexp, flags=0, allargs=False):
    """NOT_RPYTHON: you can't compile new regexps in an RPython program,
    you can only use precompiled ones"""
    from . import sre_compile
    try:
        sre_compile.compile(regexp, flags)
    except GotIt as e:
        pass
    else:
        raise ValueError("did not reach _sre.compile()!")
    if allargs:
        return e.args
    else:
        return e.args[0]
