import types, operator, sys
from pypy.interpreter import pyframe, baseobjspace
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Constant, Variable
from pypy.objspace.flow.operation import OperationName, Arity
from pypy.interpreter import pyopcode
from pypy.interpreter.gateway import ApplevelClass
from pypy.tool.cache import Cache
from pypy.tool.sourcetools import NiceCompile, compile2

EAGER_IMPORTS = True

def sc_import(space, fn, args):
    w_name, w_glob, w_loc, w_frm = args.fixedunpack(4)
    try:
        mod = __import__(space.unwrap(w_name), space.unwrap(w_glob),
                         space.unwrap(w_loc), space.unwrap(w_frm))
    except UnwrapException:
        # import * in a function gives us the locals as Variable
        # we forbid it as a SyntaxError
        raise SyntaxError, "RPython: import * is not allowed in functions"
    if EAGER_IMPORTS:
        return space.wrap(mod)
    # redirect it, but avoid showing the globals
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
    if space.builtins_can_raise_exceptions:
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
        first = "\n".join(app.source.split("\n", 3)[:3])
        if "NOT_RPYTHON" in first:
            return None
        if app.filename is None:
            code = py.code.Source(app.source).compile()
        else:
            code = NiceCompile(app.filename)(app.source)
            dic['__file__'] = app.filename
        dic['__name__'] = app.modname
        exec code in dic
        return dic
    _build = staticmethod(_build)

compiled_funcs = FunctionCache()

def sc_applevel(space, app, name, args_w):
    dic = compiled_funcs.getorbuild(app)
    if not dic:
        return None # signal that this is not RPython
    func = dic[name]
    return space.do_operation('simple_call', Constant(func), *args_w)

def setup(space):
    # fn = pyframe.normalize_exception.get_function(space)
    # this is now routed through the objspace, directly.
    # space.specialcases[fn] = sc_normalize_exception
    if space.do_imports_immediately:
        space.specialcases[__import__] = sc_import
    # redirect ApplevelClass for print et al.
    space.specialcases[ApplevelClass] = sc_applevel
    # turn calls to built-in functions to the corresponding operation,
    # if possible
    for fn in OperationName:
        space.specialcases[fn] = sc_operator
