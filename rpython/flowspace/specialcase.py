import os
from rpython.flowspace.model import Constant, const

SPECIAL_CASES = {}

def register_flow_sc(func):
    """Decorator triggering special-case handling of ``func``.

    When the flow graph builder sees ``func``, it calls the decorated function
    with ``decorated_func(space, *args_w)``, where ``args_w`` is a sequence of
    flow objects (Constants or Variables).
    """
    def decorate(sc_func):
        SPECIAL_CASES[func] = sc_func
    return decorate

@register_flow_sc(__import__)
def sc_import(space, *args_w):
    assert len(args_w) > 0 and len(args_w) <= 5, 'import needs 1 to 5 arguments'
    assert all(isinstance(arg, Constant) for arg in args_w)
    args = [arg.value for arg in args_w]
    return space.import_name(*args)

@register_flow_sc(locals)
def sc_locals(_, *args):
    raise Exception(
        "A function calling locals() is not RPython.  "
        "Note that if you're translating code outside the PyPy "
        "repository, a likely cause is that py.test's --assert=rewrite "
        "mode is getting in the way.  You should copy the file "
        "pytest.ini from the root of the PyPy repository into your "
        "own project.")

@register_flow_sc(isinstance)
def sc_isinstance(space, w_instance, w_type):
    if w_instance.foldable() and w_type.foldable():
        return const(isinstance(w_instance.value, w_type.value))
    return space.frame.do_operation('simple_call', const(isinstance),
            w_instance, w_type)

@register_flow_sc(open)
def sc_open(space, *args_w):
    from rpython.rlib.rfile import create_file

    return space.frame.do_operation("simple_call", const(create_file), *args_w)

@register_flow_sc(os.tmpfile)
def sc_os_tmpfile(space):
    from rpython.rlib.rfile import create_temp_rfile

    return space.frame.do_operation("simple_call", const(create_temp_rfile))

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
