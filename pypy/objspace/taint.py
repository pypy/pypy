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
    def __init__(self, space, operr):
        if get_debug_level(space) > 0:
            debug_bomb(space, operr)
        self.space = space
        self.operr = operr

    def explode(self):
        #msg = self.operr.errorstr(space)
        raise OperationError(self.space.w_TaintError, self.space.w_None)


def taint(w_obj):
    if w_obj is None or isinstance(w_obj, W_Tainted):
        return w_obj
    else:
        return W_Tainted(w_obj)
taint.unwrap_spec = [gateway.W_Root]
app_taint = gateway.interp2app(taint)

def is_tainted(space, w_obj):
    res = isinstance(w_obj, W_Tainted) or isinstance(w_obj, W_TaintBomb)
    return space.wrap(res)
app_is_tainted = gateway.interp2app(is_tainted)

def untaint(space, w_expectedtype, w_obj):
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

executioncontext.ExecutionContext.is_taint_mode = False

def taint_mode_function(space, w_func, __args__):
    ec = space.getexecutioncontext()
    old_auth = ec.is_taint_mode
    try:
        ec.is_taint_mode = True
        try:
            w_res = space.call_args(w_func, __args__)
        except OperationError, operr:
            if old_auth:
                raise
            w_res = W_TaintBomb(space, operr)
        else:
            if not old_auth:
                w_res = taint(w_res)
    finally:
        ec.is_taint_mode = old_auth
    return w_res

app_taint_mode_function = gateway.interp2app(
    taint_mode_function,
    unwrap_spec=[gateway.ObjSpace, gateway.W_Root, gateway.Arguments])

def taint_mode(space, w_callable):
    meth = Method(space, space.wrap(app_taint_mode_function),
                  w_callable, space.type(w_callable))
    return space.wrap(meth)
app_taint_mode = gateway.interp2app(taint_mode)

def have_taint_mode(space):
    return space.getexecutioncontext().is_taint_mode

# ____________________________________________________________

executioncontext.ExecutionContext.taint_debug = 0

def taint_debug(space, level):
    space.getexecutioncontext().taint_debug = level
app_taint_debug = gateway.interp2app(taint_debug,
                                     unwrap_spec=[gateway.ObjSpace, int])

def get_debug_level(space):
    return space.getexecutioncontext().taint_debug

def debug_bomb(space, operr):
    from pypy.interpreter.pyframe import PyFrame
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
        self.w_TaintError = self.call_function(
            self.w_type,
            self.wrap("TaintError"),
            self.newtuple([self.w_Exception]),
            self.newdict())
        w_pypymagic = self.getbuiltinmodule("pypymagic")
        self.setattr(w_pypymagic, self.wrap('taint'),
                     self.wrap(app_taint))
        self.setattr(w_pypymagic, self.wrap('is_tainted'),
                     self.wrap(app_is_tainted))
        self.setattr(w_pypymagic, self.wrap('untaint'),
                     self.wrap(app_untaint))
        self.setattr(w_pypymagic, self.wrap('taint_mode'),
                     self.wrap(app_taint_mode))
        self.setattr(w_pypymagic, self.wrap('TaintError'),
                     self.w_TaintError)
        self.setattr(w_pypymagic, self.wrap('taint_debug'),
                     self.wrap(app_taint_debug))
        patch_space_in_place(self, 'taint', proxymaker)


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
                    if have_taint_mode(space):
                        raise OperationError, w_arg.operr
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
                if name == 'type' and have_taint_mode(space):
                    pass
                else:
                    w_res = taint(w_res)
            return w_res

    elif arity == 0:
        return None

    else:

        def proxy(*args_w):
            newargs_w = ()
            for i in indices:
                w_arg = args_w[i]
                if isinstance(w_arg, W_Tainted):
                    if have_taint_mode(space):
                        w_arg = w_arg.w_obj
                    else:
                        tainted_error(space, name)
                elif isinstance(w_arg, W_TaintBomb):
                    if have_taint_mode(space):
                        raise OperationError, w_arg.operr
                    else:
                        w_arg.explode()
                newargs_w += (w_arg,)
            newargs_w += args_w[arity:]
            return parentfn(*newargs_w)

    proxy = func_with_new_name(proxy, '%s_proxy' % name)
    return proxy
