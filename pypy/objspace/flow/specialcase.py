from pypy.objspace.flow.model import Constant, UnwrapException
from pypy.objspace.flow.operation import OperationName, Arity
from pypy.interpreter.gateway import ApplevelClass
from pypy.interpreter.error import OperationError
from pypy.tool.cache import Cache
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import we_are_translated
import py

def sc_import(space, fn, args):
    args_w, kwds_w = args.unpack()
    assert kwds_w == {}, "should not call %r with keyword arguments" % (fn,)
    assert len(args_w) > 0 and len(args_w) <= 5, 'import needs 1 to 5 arguments'
    args = [space.unwrap(arg) for arg in args_w]
    return space.import_name(*args)

def sc_operator(space, fn, args):
    args_w, kwds_w = args.unpack()
    assert kwds_w == {}, "should not call %r with keyword arguments" % (fn,)
    opname = OperationName[fn]
    if len(args_w) != Arity[opname]:
        if opname == 'pow' and len(args_w) == 2:
            args_w = args_w + [Constant(None)]
        elif opname == 'getattr' and len(args_w) == 3:
            return space.do_operation('simple_call', Constant(getattr), *args_w)
        else:
            raise Exception, "should call %r with exactly %d arguments" % (
                fn, Arity[opname])
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

def sc_applevel(space, app, name, args_w):
    # special case only for print_item and print_newline
    if 'pyopcode' in app.filename and name == 'print_item':
        w_s = space.do_operation('str', *args_w)
        args_w = (w_s,)
    elif 'pyopcode' in app.filename and name == 'print_newline':
        pass
    else:
        raise Exception("not RPython: calling %r from %r" % (name, app))
    func = globals()['rpython_' + name]
    return space.do_operation('simple_call', Constant(func), *args_w)

# _________________________________________________________________________

def sc_r_uint(space, r_uint, args):
    # special case to constant-fold r_uint(32-bit-constant)
    # (normally, the 32-bit constant is a long, and is not allowed to
    # show up in the flow graphs at all)
    args_w, kwds_w = args.unpack()
    assert not kwds_w
    [w_value] = args_w
    if isinstance(w_value, Constant):
        return Constant(r_uint(w_value.value))
    return space.do_operation('simple_call', space.wrap(r_uint), w_value)

def sc_we_are_translated(space, we_are_translated, args):
    return Constant(True)

SPECIAL_CASES = {__import__: sc_import, ApplevelClass: sc_applevel,
        r_uint: sc_r_uint, we_are_translated: sc_we_are_translated}
for fn in OperationName:
    SPECIAL_CASES[fn] = sc_operator

