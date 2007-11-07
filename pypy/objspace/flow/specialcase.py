from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Constant
from pypy.objspace.flow.operation import OperationName, Arity
from pypy.interpreter.gateway import ApplevelClass
from pypy.interpreter.error import OperationError
from pypy.tool.cache import Cache

def sc_import(space, fn, args):
    args_w, kwds_w = args.unpack()
    assert kwds_w == {}, "should not call %r with keyword arguments" % (fn,)
    assert len(args_w) > 0 and len(args_w) <= 4, 'import needs 1 to 4 arguments'
    w_name = args_w[0]
    w_None = space.wrap(None)
    w_glob, w_loc, w_frm = w_None, w_None, w_None
    if len(args_w) > 1:
        w_glob = args_w[1]
    if len(args_w) > 2:
        w_loc = args_w[2]
    if len(args_w) > 3:
        w_frm = args_w[3]   
    if not isinstance(w_loc, Constant):
        # import * in a function gives us the locals as Variable
        # we always forbid it as a SyntaxError
        raise SyntaxError, "RPython: import * is not allowed in functions"
    if space.do_imports_immediately:
        name, glob, loc, frm = (space.unwrap(w_name), space.unwrap(w_glob),
                                space.unwrap(w_loc), space.unwrap(w_frm))
        try:
            mod = __import__(name, glob, loc, frm)
        except ImportError, e:
            raise OperationError(space.w_ImportError, space.wrap(str(e)))
        return space.wrap(mod)
    # redirect it, but avoid exposing the globals
    w_glob = Constant({})
    return space.do_operation('simple_call', Constant(__import__),
                               w_name, w_glob, w_loc, w_frm)

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
    if space.config.translation.builtins_can_raise_exceptions:
        # in this mode, avoid constant folding and raise an implicit Exception
        w_result = space.do_operation(opname, *args_w)
        space.handle_implicit_exceptions([Exception])
        return w_result
    else:
        # in normal mode, completely replace the call with the underlying
        # operation and its limited implicit exceptions semantic
        return getattr(space, opname)(*args_w)


# This is not a space cache.
# It is just collecting the compiled functions from all the source snippets.

class FunctionCache(Cache):
    """A cache mapping applevel instances to dicts with simple functions"""

    def _build(app):
        """NOT_RPYTHON.
        Called indirectly by ApplevelClass.interphook().appcaller()."""
        dic = {}
        if not app.can_use_geninterp:
            return None
        if app.filename is not None:
            dic['__file__'] = app.filename
        dic['__name__'] = app.modname
        exec app.code in dic
        return dic
    _build = staticmethod(_build)

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

compiled_funcs = FunctionCache()

def sc_applevel(space, app, name, args_w):
    dic = compiled_funcs.getorbuild(app)
    if not dic:
        return None # signal that this is not RPython
    func = dic[name]
    if getattr(func, '_annspecialcase_', '').startswith('flowspace:'):
        # a hack to replace specific app-level helpers with simplified
        # RPython versions
        name = func._annspecialcase_[len('flowspace:'):]
        if name == 'print_item':    # more special cases...
            w_s = space.do_operation('str', *args_w)
            args_w = (w_s,)
        func = globals()['rpython_' + name]
    else:
        # otherwise, just call the app-level helper and hope that it
        # is RPython enough
        pass
    return space.do_operation('simple_call', Constant(func), *args_w)

def setup(space):
    # fn = pyframe.normalize_exception.get_function(space)
    # this is now routed through the objspace, directly.
    # space.specialcases[fn] = sc_normalize_exception
    space.specialcases[__import__] = sc_import
    # redirect ApplevelClass for print et al.
    space.specialcases[ApplevelClass] = sc_applevel
    # turn calls to built-in functions to the corresponding operation,
    # if possible
    for fn in OperationName:
        space.specialcases[fn] = sc_operator
