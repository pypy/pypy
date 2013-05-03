from rpython.flowspace.model import Constant
from rpython.flowspace.operation import OperationName, op
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import we_are_translated

def sc_import(space, fn, args_w):
    assert len(args_w) > 0 and len(args_w) <= 5, 'import needs 1 to 5 arguments'
    args = [space.unwrap(arg) for arg in args_w]
    return space.import_name(*args)

def sc_operator(space, fn, args_w):
    opname = OperationName[fn]
    oper = getattr(op, opname)
    if len(args_w) != oper.arity:
        if opname == 'pow' and len(args_w) == 2:
            args_w = args_w + [Constant(None)]
        elif opname == 'getattr' and len(args_w) == 3:
            return space.frame.do_operation('simple_call', Constant(getattr), *args_w)
        else:
            raise Exception("should call %r with exactly %d arguments" % (
                fn, oper.arity))
    # completely replace the call with the underlying
    # operation and its limited implicit exceptions semantic
    return getattr(space, opname)(*args_w)

# _________________________________________________________________________
# a simplified version of the basic printing routines, for RPython programs
class StdOutBuffer:
    linebuf = []
stdoutbuffer = StdOutBuffer()

def rpython_print_item(s):
    buf = stdoutbuffer.linebuf
    for c in s:
        buf.append(c)
    buf.append(' ')

def rpython_print_newline():
    buf = stdoutbuffer.linebuf
    if buf:
        buf[-1] = '\n'
        s = ''.join(buf)
        del buf[:]
    else:
        s = '\n'
    import os
    os.write(1, s)

# _________________________________________________________________________

def sc_r_uint(space, r_uint, args_w):
    # special case to constant-fold r_uint(32-bit-constant)
    # (normally, the 32-bit constant is a long, and is not allowed to
    # show up in the flow graphs at all)
    [w_value] = args_w
    if isinstance(w_value, Constant):
        return Constant(r_uint(w_value.value))
    return space.frame.do_operation('simple_call', space.wrap(r_uint), w_value)

def sc_we_are_translated(space, we_are_translated, args_w):
    return Constant(True)

def sc_locals(space, locals, args):
    raise Exception(
        "A function calling locals() is not RPython.  "
        "Note that if you're translating code outside the PyPy "
        "repository, a likely cause is that py.test's --assert=rewrite "
        "mode is getting in the way.  You should copy the file "
        "pytest.ini from the root of the PyPy repository into your "
        "own project.")

SPECIAL_CASES = {__import__: sc_import, r_uint: sc_r_uint,
        we_are_translated: sc_we_are_translated,
        locals: sc_locals}
for fn in OperationName:
    SPECIAL_CASES[fn] = sc_operator
