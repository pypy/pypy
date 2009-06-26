
""" Usage:
serialize.py python_file func_name output_file
"""

import autopath
import py
import sys
import types
from pypy.jit.tl.spli.objects import Int, Str, spli_None
from pypy.jit.tl.spli.pycode import Code
from pypy.rlib.rstruct.runpack import runpack
import struct

FMT = 'iiii'
int_lgt = len(struct.pack('i', 0))
header_lgt = int_lgt * len(FMT)

class NotSupportedFormat(Exception):
    pass

def serialize_str(value):
    return struct.pack('i', len(value)) + value

def unserialize_str(data, start):
    end_lgt = start + int_lgt
    lgt = runpack('i', data[start:end_lgt])
    assert lgt >= 0
    end_str = end_lgt + lgt
    return data[end_lgt:end_str], end_str

def serialize_const(const):
    if isinstance(const, int):
        return 'd' + struct.pack('i', const)
    elif isinstance(const, str):
        return 's' + serialize_str(const)
    elif const is None:
        return 'n'
    elif isinstance(const, types.CodeType):
        return 'c' + serialize(const)
    else:
        raise NotSupportedFormat(str(const))

def unserialize_const(c, start):
    assert start >= 0
    if c[start] == 'd':
        end = start + int_lgt + 1
        intval = runpack('i', c[start + 1:end])
        return Int(intval), end
    elif c[start] == 's':
        value, end = unserialize_str(c, start + 1)
        return Str(value), end
    elif c[start] == 'n':
        return spli_None, start + 1
    elif c[start] == 'c':
        return unserialize_code(c, start + 1)
    else:
        raise NotSupportedFormat(c[start])

def unserialize_consts(constrepr):
    pos = int_lgt
    consts_w = []
    num = runpack('i', constrepr[:int_lgt])
    for i in range(num):
        next_const, pos = unserialize_const(constrepr, pos)
        consts_w.append(next_const)
    return consts_w, pos

def unserialize_names(namesrepr, num):
    pos = 0
    names = []
    for i in range(num):
        name, pos = unserialize_str(namesrepr, pos)
        names.append(name)
    return names, pos

def unserialize_code(coderepr, start=0):
    coderepr = coderepr[start:]
    header = coderepr[:header_lgt]
    argcount, nlocals, stacksize, code_len = runpack(FMT, header)
    assert code_len >= 0
    names_pos = code_len + header_lgt
    code = coderepr[header_lgt:names_pos]
    num = runpack('i', coderepr[names_pos:names_pos + int_lgt])
    names, end_names = unserialize_names(coderepr[names_pos + int_lgt:], num)
    const_start = names_pos + int_lgt + end_names
    consts, pos = unserialize_consts(coderepr[const_start:])
    pos = start + const_start + pos
    return Code(argcount, nlocals, stacksize, code, consts, names), pos

# ------------------- PUBLIC API ----------------------

def serialize(code):
    header = struct.pack(FMT, code.co_argcount, code.co_nlocals,
                         code.co_stacksize, len(code.co_code))
    namesrepr = (struct.pack('i', len(code.co_names)) +
                 "".join(serialize_str(name) for name in code.co_names))
    constsrepr = (struct.pack('i', len(code.co_consts)) +
                  "".join([serialize_const(const) for const in code.co_consts]))
    return header + code.co_code + namesrepr + constsrepr

def deserialize(data, start=0):
    return unserialize_code(data)[0]

def main(argv):
    if len(argv) != 3:
        print __doc__
        sys.exit(1)
    code_file = argv[1]
    mod = py.path.local(code_file).read()
    r = serialize(compile(mod, code_file, "exec"))
    outfile = py.path.local(argv[2])
    outfile.write(r)

if __name__ == '__main__':
    import sys
    main(sys.argv)
