"""
A simple object space wrapping real CPython objects to PyPy,
and wrapping back PyPy W_Xxx objects to CPython.
"""
# XXX proof of concept, not fully working.

import sys, __builtin__
from pypy.interpreter import baseobjspace
from pypy.interpreter import typedef    # force the 'typedef' attributes
from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Function
from pypy.interpreter.argument import Arguments
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.rarithmetic import r_uint

class W_Box(W_Root):

    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return 'W_Box(%r)' % (self.obj,)

    def getclass(self, space):
        return space.wrap(type(self.obj))

# ____________________________________________________________

class CPyFacade(object):
    __slots__ = ('obj', '__weakref__')

facade_obj = CPyFacade.obj
facade_new = CPyFacade.__new__
del CPyFacade.obj

# ____________________________________________________________

class TrivialObjSpace(baseobjspace.ObjSpace):

    def initialize(self):
        self.facadetypes = {}

        for key, value in __builtin__.__dict__.items():
            name = 'w_' + key
            if not hasattr(self, name):
                setattr(self, name, W_Box(value))
        self.make_builtins()

        from pypy.interpreter.module import Module
        import exceptions
        mod = Module(self, self.wrap('exceptions'),
                     self.wrap(exceptions.__dict__))
        self.setitem(self.sys.get('modules'), self.wrap('exceptions'),
                     self.wrap(mod))

        self.setup_builtin_modules()

    def setoptions(self, **ignore):
        pass

    def getfacadetype(self, typedef):
        try:
            return self.facadetypes[typedef]
        except KeyError:

            basedef = typedef.base
            if basedef is None:
                base = CPyFacade
            else:
                base = self.getfacadetype(basedef)

            d = {'__slots__': ()}
            fixup_classes = []
            for key, value in typedef.rawdict.items():
                if key == '__repr__':
                    continue   # for easier debugging
                w_obj = self.wrap(value)
                if isinstance(w_obj, Wrappable):
                    x = facade_new(CPyFacade)
                    facade_obj.__set__(x, w_obj)
                    fixup_classes.append((x, w_obj.typedef))
                else:
                    x = w_obj
                d[key] = x

            if typedef is Function.typedef:
                # a special case to avoid infinite recursion
                def function_call(func, *args, **kwds):
                    w_func = self.wrap(func)
                    args_w = [self.wrap(x) for x in args]
                    kwds_w = dict([(key, self.wrap(value))
                                   for key, value in kwds.items()])
                    a = Arguments(self, args_w, kwds_w)
                    res = w_func.call_args(a)
                    return self.expose(res)
                d['__call__'] = function_call

            T = type(typedef.name, (base,), d)

            if '__slots__' not in typedef.rawdict:
                del T.__slots__

            self.facadetypes[typedef] = T

            for x, typedef in fixup_classes:
                x.__class__ = self.getfacadetype(typedef)

            return T

    def wrap(self, x):
        if isinstance(x, Wrappable):
            return x.__spacebind__(self)
        elif isinstance(x, CPyFacade):
            return facade_obj.__get__(x)
        else:
            return W_Box(x)

    newint = wrap

    def unwrap(self, w_obj):
        if isinstance(w_obj, Wrappable):
            return w_obj
        else:
            return w_obj.obj

    def expose(self, w_obj):
        """Turn a W_Root instance into an interp-level object that behaves
        on top of CPython in the same way as w_obj behaves on top of PyPy.
        """
        if isinstance(w_obj, Wrappable):
            try:
                return w_obj.__trivialfacade
            except AttributeError:
                T = self.getfacadetype(w_obj.typedef)
                f = facade_new(T)
                facade_obj.__set__(f, w_obj)
                w_obj.__trivialfacade = f
                return f
        else:
            return w_obj.obj

    def type(self, w_obj):
        return w_obj.getclass(self)

    def is_true(self, w_obj):
        return bool(self.expose(w_obj))

    def check_type(self, x, classes):
        if not isinstance(x, classes):
            msg = '%s expected, got %r object instead' % (classes,
                                                          type(x).__name__)
            raise OperationError(self.w_TypeError, self.wrap(msg))

    def str_w(self, w_obj):
        x = self.expose(w_obj)
        self.check_type(x, (str, unicode))
        return str(x)

    def int_w(self, w_obj):
        x = self.expose(w_obj)
        self.check_type(x, (int, long))
        return int(x)

    def uint_w(self, w_obj):
        x = self.expose(w_obj)
        self.check_type(x, (r_uint, int, long))
        return r_uint(x)

    def float_w(self, w_obj):
        x = self.expose(w_obj)
        self.check_type(x, (float, int, long))
        return float(x)

    def is_w(self, w_x, w_y):
        return self.expose(w_x) is self.expose(w_y)

    def newtuple(self, items_w):
        items = [self.expose(w_item) for w_item in items_w]
        return W_Box(tuple(items))

    def newlist(self, items_w):
        items = [self.expose(w_item) for w_item in items_w]
        return W_Box(items)

    def newdict(self, items_w):
        items = [(self.expose(w_key), self.expose(w_value))
                 for w_key, w_value in items_w]
        return W_Box(dict(items))

    def newstring(self, chars):
        s = ''.join([chr(n) for n in chars])
        return W_Box(s)

    def newunicode(self, chars):
        u = u''.join([unichr(n) for n in chars])
        return W_Box(u)

    def newslice(self, w_start, w_stop, w_step):
        sl = slice(self.expose(w_start),
                   self.expose(w_stop),
                   self.expose(w_step))
        return W_Box(sl)

    def call_args(self, w_callable, args):
        callable = self.expose(w_callable)
        args_w, kwds_w = args.unpack()
        args = [self.expose(w_value) for w_value in args_w]
        kwds = dict([(key, self.expose(w_value)) for key, w_value in kwds_w])
        try:
            res = callable(*args, **kwds)
        except:
            self.wrap_exception()
        return self.wrap(res)

    def wrap_exception(self):
        # real-to-wrapped exceptions
        exc, value, tb = sys.exc_info()
        if exc is OperationError:
            raise exc, value, tb   # just re-raise it
        w_exc = self.wrap(exc)
        w_value = self.wrap(value)
        raise OperationError, OperationError(w_exc, w_value), tb


def setup():
    from pypy.objspace.flow.operation import FunctionByName
    for name, symbol, arity, specialnames in baseobjspace.ObjSpace.MethodTable:
        if hasattr(TrivialObjSpace, name):
            continue
        def make_function():
            operator = FunctionByName[name]
            def do(self, *args_w):
                args = [self.expose(a) for a in args_w]
                try:
                    res = operator(*args)
                except:
                    self.wrap_exception()
                return self.wrap(res)
            return func_with_new_name(do, name)
        setattr(TrivialObjSpace, name, make_function())
setup()
del setup

Space = TrivialObjSpace
