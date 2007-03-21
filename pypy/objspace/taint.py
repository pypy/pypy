"""
Just an experiment.
"""
import os
from pypy.objspace.std.objspace import StdObjSpace
from pypy.objspace.proxy import patch_space_in_place
from pypy.objspace.thunk import nb_forcing_args
from pypy.interpreter.error import OperationError
from pypy.interpreter import baseobjspace, gateway, executioncontext
from pypy.interpreter.function import Method
from pypy.interpreter.pyframe import PyFrame
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.unroll import unrolling_iterable


class W_Tainted(baseobjspace.W_Root):
    def __init__(self, w_obj):
        self.w_obj = w_obj

##    def getdict(self):
##        return taint(self.w_obj.getdict())

##    def getdictvalue_w(self, space, attr):
##        return taint(self.w_obj.getdictvalue_w(space, attr))

##    def getdictvalue(self, space, w_attr):
##        return taint(self.w_obj.getdictvalue(space, w_attr))

##    def setdictvalue(self, space, w_attr, w_value):
##        return self.w_obj.setdictvalue(space, w_attr, w_value)

##    ...

class W_TaintBomb(baseobjspace.W_Root):
    filename = '?'
    codename = '?'
    codeline = 0

    def __init__(self, space, operr):
        self.space = space
        self.operr = operr
        self.record_debug_info()

    def record_debug_info(self):
        ec = self.space.getexecutioncontext()
        try:
            frame = ec.framestack.top()
        except IndexError:
            pass
        else:
            if isinstance(frame, PyFrame):
                self.filename = frame.pycode.co_filename
                self.codename = frame.pycode.co_name
                self.codeline = frame.get_last_lineno()
        if get_debug_level(self.space) > 0:
            self.debug_dump()

    def debug_dump(self):
        os.write(2, 'Taint Bomb from file "%s", line %d, in %s\n    %s\n' % (
            self.filename, self.codeline, self.codename,
            self.operr.errorstr(self.space)))

    def explode(self):
        #msg = self.operr.errorstr(space)
        raise OperationError(self.space.w_TaintError, self.space.w_None)


def taint(w_obj):
    """Return a tainted version of the argument."""
    if w_obj is None or isinstance(w_obj, W_Tainted):
        return w_obj
    else:
        return W_Tainted(w_obj)
taint.unwrap_spec = [gateway.W_Root]
app_taint = gateway.interp2app(taint)

def is_tainted(space, w_obj):
    """Return whether the argument is tainted."""
    res = isinstance(w_obj, W_Tainted) or isinstance(w_obj, W_TaintBomb)
    return space.wrap(res)
app_is_tainted = gateway.interp2app(is_tainted)

def untaint(space, w_expectedtype, w_obj):
    """untaint(expectedtype, tainted_obj) -> obj
Untaint untainted_obj and return it. If the result is not of expectedtype,
raise a type error."""
    if (isinstance(w_expectedtype, W_Tainted) or
        isinstance(w_expectedtype, W_TaintBomb)):
        raise OperationError(space.w_TypeError,
                  space.wrap("untaint() arg 1 must be an untainted type"))
    if not space.is_true(space.isinstance(w_expectedtype, space.w_type)):
        raise OperationError(space.w_TypeError,
                             space.wrap("untaint() arg 1 must be a type"))
    if isinstance(w_obj, W_Tainted):
        w_obj = w_obj.w_obj
    elif isinstance(w_obj, W_TaintBomb):
        w_obj.explode()
    #if isinstance(w_expectedtype, W_Tainted):
    #    w_expectedtype = w_expectedtype.w_obj
    w_realtype = space.type(w_obj)
    if not space.is_w(w_realtype, w_expectedtype):
        #msg = "expected an object of type '%s'" % (
        #    w_expectedtype.getname(space, '?'),)
        #    #w_realtype.getname(space, '?'))
        raise OperationError(space.w_TaintError, space.w_None)
    return w_obj
app_untaint = gateway.interp2app(untaint)

# ____________________________________________________________

def taint_atomic_function(space, w_func, args_w):
    newargs_w = []
    tainted = False
    for w_arg in args_w:
        if isinstance(w_arg, W_Tainted):
            tainted = True
            w_arg = w_arg.w_obj
        elif isinstance(w_arg, W_TaintBomb):
            return w_arg
        newargs_w.append(w_arg)
    w_newargs = space.newtuple(newargs_w)
    try:
        w_res = space.call(w_func, w_newargs)
    except OperationError, operr:
        if not tainted:
            raise
        return W_TaintBomb(space, operr)
    if tainted:
        w_res = taint(w_res)
    return w_res

app_taint_atomic_function = gateway.interp2app(
    taint_atomic_function,
    unwrap_spec=[gateway.ObjSpace, gateway.W_Root, 'args_w'])

def taint_atomic(space, w_callable):
    """decorator to make a callable "taint-atomic": if the function is called
with tainted arguments, those are untainted. The result of the function is
tainted again.  All exceptions that the callable raises are turned into
taint bombs."""
    meth = Method(space, space.w_fn_taint_atomic_function,
                  w_callable, space.type(w_callable))
    return space.wrap(meth)
app_taint_atomic = gateway.interp2app(taint_atomic)

# ____________________________________________________________

executioncontext.ExecutionContext.taint_debug = 0

def taint_debug(space, level):
    """Set the debug level. If the debug level is greater than 0, the creation
of taint bombs will print debug information. For debugging purposes
only!"""
    space.getexecutioncontext().taint_debug = level
app_taint_debug = gateway.interp2app(taint_debug,
                                     unwrap_spec=[gateway.ObjSpace, int])

def taint_look(space, w_obj):
    """Print some info about the taintedness of an object. For debugging
purposes only!"""
    if isinstance(w_obj, W_Tainted):
        info = space.type(w_obj.w_obj).getname(space, '?')
        msg = space.str_w(w_obj.w_obj.getrepr(space, info))
        msg = 'Taint Box %s\n' % msg
        os.write(2, msg)
    elif isinstance(w_obj, W_TaintBomb):
        w_obj.debug_dump()
    else:
        os.write(2, 'not tainted\n')
app_taint_look = gateway.interp2app(taint_look)

def get_debug_level(space):
    return space.getexecutioncontext().taint_debug

def debug_bomb(space, operr):
    ec = space.getexecutioncontext()
    filename = '?'
    codename = '?'
    codeline = 0
    try:
        frame = ec.framestack.top()
    except IndexError:
        pass
    else:
        if isinstance(frame, PyFrame):
            filename = frame.pycode.co_filename
            codename = frame.pycode.co_name
            codeline = frame.get_last_lineno()
    os.write(2, 'Taint Bomb in file "%s", line %d, in %s\n    %s\n' % (
        filename, codeline, codename, operr.errorstr(space)))

# ____________________________________________________________


class TaintSpace(StdObjSpace):

    def __init__(self, *args, **kwds):
        StdObjSpace.__init__(self, *args, **kwds)
        w_dict = self.newdict()
        self.setitem(w_dict, self.wrap("__doc__"), self.wrap("""\
Exception that is raised when an operation revealing information on a tainted
object is performed."""))
        self.w_TaintError = self.call_function(
            self.w_type,
            self.wrap("TaintError"),
            self.newtuple([self.w_Exception]),
            w_dict
            )
        w___pypy__ = self.getbuiltinmodule("__pypy__")
        self.setattr(w___pypy__, self.wrap('taint'),
                     self.wrap(app_taint))
        self.setattr(w___pypy__, self.wrap('is_tainted'),
                     self.wrap(app_is_tainted))
        self.setattr(w___pypy__, self.wrap('untaint'),
                     self.wrap(app_untaint))
        self.w_fn_taint_atomic_function = self.wrap(app_taint_atomic_function)
        self.setattr(w___pypy__, self.wrap('taint_atomic'),
                     self.wrap(app_taint_atomic))
        self.setattr(w___pypy__, self.wrap('TaintError'),
                     self.w_TaintError)
        self.setattr(w___pypy__, self.wrap('_taint_debug'),
                     self.wrap(app_taint_debug))
        self.setattr(w___pypy__, self.wrap('_taint_look'),
                     self.wrap(app_taint_look))
        patch_space_in_place(self, 'taint', proxymaker)

        # XXX may leak info, perfomance hit, what about taint bombs?
        from pypy.objspace.std.typeobject import W_TypeObject

        def taint_lookup(w_obj, name):
            if isinstance(w_obj, W_Tainted):
                w_obj = w_obj.w_obj
            w_type = self.type(w_obj)
            assert isinstance(w_type, W_TypeObject)
            return w_type.lookup(name)

        def taint_lookup_in_type_where(w_obj, name):
            if isinstance(w_obj, W_Tainted):
                w_type = w_obj.w_obj
            else:
                w_type = w_obj
            assert isinstance(w_type, W_TypeObject)
            return w_type.lookup_where(name)

        self.lookup = taint_lookup
        self.lookup_in_type_where = taint_lookup_in_type_where


Space = TaintSpace


def tainted_error(space, name):
    #msg = "operation '%s' forbidden on tainted object" % (name,)
    raise OperationError(space.w_TaintError, space.w_None)# space.wrap(msg))


RegularMethods = dict.fromkeys(
    [name for name, _, _, _ in baseobjspace.ObjSpace.MethodTable])

TaintResultIrregularMethods = dict.fromkeys(
    ['wrap', 'call_args'] +
    [name for name in baseobjspace.ObjSpace.IrregularOpTable
          if name.startswith('new')])

def proxymaker(space, name, parentfn):
    arity = nb_forcing_args[name]
    indices = unrolling_iterable(range(arity))
    if name in RegularMethods:

        def proxy(*args_w):
            newargs_w = ()
            tainted = False
            for i in indices:
                w_arg = args_w[i]
                if isinstance(w_arg, W_Tainted):
                    tainted = True
                    w_arg = w_arg.w_obj
                elif isinstance(w_arg, W_TaintBomb):
                    return w_arg
                newargs_w += (w_arg,)
            newargs_w += args_w[arity:]
            try:
                w_res = parentfn(*newargs_w)
            except OperationError, operr:
                if not tainted:
                    raise
                return W_TaintBomb(space, operr)
            if tainted:
                w_res = taint(w_res)
            return w_res

    elif arity == 0:
        return None

    else:

        def proxy(*args_w):
            for i in indices:
                w_arg = args_w[i]
                if isinstance(w_arg, W_Tainted):
                    tainted_error(space, name)
                elif isinstance(w_arg, W_TaintBomb):
                    w_arg.explode()
            return parentfn(*args_w)

    proxy = func_with_new_name(proxy, '%s_proxy' % name)
    return proxy
