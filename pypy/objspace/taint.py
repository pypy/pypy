"""
Just an experiment.
"""
from pypy.objspace.std.objspace import StdObjSpace
from pypy.objspace.proxy import patch_space_in_place
from pypy.objspace.thunk import nb_forcing_args
from pypy.interpreter.error import OperationError
from pypy.interpreter import baseobjspace, gateway
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
    def __init__(self, operr):
        self.operr = operr

    def explode(self, space):
        msg = self.operr.errorstr(space)
        raise OperationError(space.w_TaintError, space.w_None)  # space.wrap(msg))


def taint(w_obj):
    if w_obj is None or isinstance(w_obj, W_Tainted):
        return w_obj
    else:
        return W_Tainted(w_obj)
taint.unwrap_spec = [gateway.W_Root]
app_taint = gateway.interp2app(taint)

def is_tainted(space, w_obj):
    res = isinstance(w_obj, W_Tainted)
    return space.wrap(res)
app_is_tainted = gateway.interp2app(is_tainted)

def untaint(space, w_obj, w_expectedtype):
    if isinstance(w_obj, W_Tainted):
        w_obj = w_obj.w_obj
    elif isinstance(w_obj, W_TaintBomb):
        w_obj.explode(space)
    #if isinstance(w_expectedtype, W_Tainted):
    #    w_expectedtype = w_expectedtype.w_obj
    w_realtype = space.type(w_obj)
    if not space.is_w(w_realtype, w_expectedtype):
        msg = "expected an object of type '%s', got '%s'" % (
            w_expectedtype.getname(space, '?'),
            w_realtype.getname(space, '?'))
        raise OperationError(space.w_TaintError,
                             space.wrap(msg))
    return w_obj
app_untaint = gateway.interp2app(untaint)

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
        patch_space_in_place(self, 'taint', proxymaker)


Space = TaintSpace


def tainted_error(space, name):
    msg = "operation '%s' forbidden on tainted object" % (name,)
    raise OperationError(space.w_TaintError, space.wrap(msg))


RegularMethods = dict.fromkeys(
    [name for name, _, _, _ in baseobjspace.ObjSpace.MethodTable])

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
            except OperationError, e:
                if not tainted:
                    raise
                return W_TaintBomb(e)
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
                    w_arg.explode(space)
            return parentfn(*args_w)

    proxy = func_with_new_name(proxy, '%s_proxy' % name)
    return proxy
