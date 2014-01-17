
from rpython.rlib.rsre import rsre_char
from rpython.rlib.rarithmetic import intmask


MAGIC = 20031017
CODESIZE = rsre_char.CODESIZE
getlower = rsre_char.getlower


class GotIt(Exception):
    pass

def compile(pattern, flags, code, *args):
    raise GotIt([intmask(i) for i in code], flags, args)


def get_code(regexp, flags=0, allargs=False):
    from . import sre_compile
    try:
        sre_compile.compile(regexp, flags)
    except GotIt, e:
        pass
    else:
        raise ValueError("did not reach _sre.compile()!")
    if allargs:
        return e.args
    else:
        return e.args[0]
