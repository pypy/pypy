
from pypy.jit.tl.spli.objects import DumbObjSpace, Int, Str
from pypy.jit.tl.spli.pycode import Code
from pypy.rlib.rstruct.runpack import runpack
import struct

FMT = 'iiiii'
int_lgt = len(struct.pack('i', 0))
header_lgt = int_lgt * len(FMT)

class NotSupportedFormat(Exception):
    pass

def serialize_const(const):
    if isinstance(const, int):
        return 'd' + struct.pack('i', const)
    elif isinstance(const, str):
        return 's' + struct.pack('i', len(const)) + const
    elif const is None:
        return 'n'
    else:
        raise NotSupportedFormat(str(const))

def unserialize_const(c, start):
    if c[start] == 'd':
        end = start + int_lgt + 1
        intval, = runpack('i', c[start + 1:end])
        return Int(intval), end
    elif c[start] == 's':
        end_lgt = start + 1 + int_lgt
        lgt, = runpack('i', c[start + 1:end_lgt])
        end_str = end_lgt + lgt
        return Str(c[end_lgt:end_str]), end_str
    elif c[start] == 'n':
        return None, start + 1
    else:
        raise NotSupportedFormat(c[start])

def unserialize_consts(constrepr):
    pos = 0
    consts_w = []
    while pos < len(constrepr):
        next_const, pos = unserialize_const(constrepr, pos)
        consts_w.append(next_const)
    return consts_w

# ------------------- PUBLIC API ----------------------

def serialize(code):
    header = struct.pack(FMT, code.co_argcount, code.co_nlocals,
                         code.co_stacksize, code.co_flags, len(code.co_code))
    constsrepr = "".join([serialize_const(const) for const in code.co_consts])
    return header + code.co_code + constsrepr

def deserialize(coderepr, space=None):
    if space is None:
        space = DumbObjSpace()
    header = coderepr[:header_lgt]
    argcount, nlocals, stacksize, flags, code_len = runpack(FMT, header)
    code = coderepr[header_lgt:(code_len + header_lgt)]
    consts = unserialize_consts(coderepr[code_len + header_lgt:])
    names = []
    varnames = []
    return Code(space, argcount, nlocals, stacksize, flags, code,
                consts, names, varnames, 'file', 'code', 0,
                0, [], [])
