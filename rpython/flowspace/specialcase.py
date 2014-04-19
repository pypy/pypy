import os
from rpython.flowspace.model import Constant, const

SPECIAL_CASES = {}

def register_flow_sc(func):
    """Decorator triggering special-case handling of ``func``.

    When the flow graph builder sees ``func``, it calls the decorated function
    with ``decorated_func(ctx, *args_w)``, where ``args_w`` is a sequence of
    flow objects (Constants or Variables).
    """
    def decorate(sc_func):
        SPECIAL_CASES[func] = sc_func
    return decorate

@register_flow_sc(__import__)
def sc_import(ctx, *args_w):
    assert all(isinstance(arg, Constant) for arg in args_w)
    args = [arg.value for arg in args_w]
    return ctx.import_name(*args)

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
def sc_isinstance(ctx, w_instance, w_type):
    if w_instance.foldable() and w_type.foldable():
        return const(isinstance(w_instance.value, w_type.value))
    return ctx.appcall(isinstance, w_instance, w_type)

@register_flow_sc(getattr)
def sc_getattr(ctx, w_obj, w_index, w_default=None):
    if w_default is not None:
        return ctx.appcall(getattr, w_obj, w_index, w_default)
    else:
        from rpython.flowspace.operation import op
        return op.getattr(w_obj, w_index).eval(ctx)

@register_flow_sc(open)
def sc_open(ctx, *args_w):
    from rpython.rlib.rfile import create_file
    return ctx.appcall(create_file, *args_w)

@register_flow_sc(os.fdopen)
def sc_os_fdopen(ctx, *args_w):
    from rpython.rlib.rfile import create_fdopen_rfile
    return ctx.appcall(create_fdopen_rfile, *args_w)

@register_flow_sc(os.tmpfile)
def sc_os_tmpfile(ctx):
    from rpython.rlib.rfile import create_temp_rfile
    return ctx.appcall(create_temp_rfile)

@register_flow_sc(os.remove)
def sc_os_remove(ctx, *args_w):
    # on top of PyPy only: 'os.remove != os.unlink'
    # (on CPython they are '==', but not identical either)
    return ctx.appcall(os.unlink, *args_w)

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
