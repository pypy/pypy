from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.error import OperationError
from pypy.interpreter.miscutils import getthreadlocals
from pypy.interpreter.argument import Arguments

__all__ = ['ObjSpace', 'OperationError', 'Wrappable', 'BaseWrappable',
           'W_Root']


class W_Root:
    """This is the abstract root class of all wrapped objects that live
    in a 'normal' object space like StdObjSpace."""
    def getdict(self):
        return None
    def getclass(self, space):
        return space.gettypeobject(self.typedef)

class BaseWrappable(W_Root):
    """A subclass of BaseWrappable is an internal, interpreter-level class
    that can nevertheless be exposed at application-level by space.wrap()."""
    def __spacebind__(self, space):
        return self

class Wrappable(BaseWrappable, object):
    """Same as BaseWrappable, just new-style instead."""

class ObjSpace:
    """Base class for the interpreter-level implementations of object spaces.
    http://codespeak.net/moin/pypy/moin.cgi/ObjectSpace"""
    
    full_exceptions = True  # full support for exceptions (normalization & more)

    def __init__(self):
        "Basic initialization of objects."
        self.generalcache = {}
        # sets all the internal descriptors
        self.initialize()

    def loadfromcache(self, key, builder):
        try:
            return self.generalcache[key]
        except KeyError:
            return self.generalcache.setdefault(key, builder(key, self))

    def make_builtins(self, for_builtins):
        # initializing builtins may require creating a frame which in
        # turn already accesses space.w_builtins, provide a dummy one ...
        self.w_builtins = self.newdict([])

        # insert stuff into the newly-made builtins
        for key, w_value in for_builtins.items():
            self.setitem(self.w_builtins, self.wrap(key), w_value)

        assert not hasattr(self, 'builtin')
        if not hasattr(self, 'sys'):
            self.make_sys()

        from pypy.interpreter.extmodule import BuiltinModule

        # the builtins are iteratively initialized
        self.builtin = BuiltinModule(self, '__builtin__', self.w_builtins)
        self.w_builtin = self.wrap(self.builtin)

        # initialize with "bootstrap types" from objspace  (e.g. w_None)
        for name, value in self.__dict__.items():
            if name.startswith('w_'):
                name = name[2:]
                if name.startswith('builtin') or name.startswith('sys'):
                    continue
                #print "setitem: space instance %-20s into builtins" % name
                self.setitem(self.w_builtins, self.wrap(name), value)

        self.sys.setbuiltinmodule(self.w_builtin, '__builtin__')

    def make_sys(self):
        from pypy.interpreter.extmodule import BuiltinModule
        assert not hasattr(self, 'sys')
        self.sys = BuiltinModule(self, 'sys')
        self.w_sys = self.wrap(self.sys)
        self.sys.setbuiltinmodule(self.w_sys, 'sys')
        
    def get_builtin_module(self, name):
        if name not in self.sys.builtin_modules:
            return None
        module = self.sys.builtin_modules[name]
        if module is None:
            from pypy.interpreter.extmodule import BuiltinModule
            module = BuiltinModule(self, name)
            self.sys.builtin_modules[name] = module
        w_module = self.wrap(module)
        self.sys.setbuiltinmodule(w_module, name)
        return w_module

    def initialize(self):
        """Abstract method that should put some minimal content into the
        w_builtins."""

    def getexecutioncontext(self):
        "Return what we consider to be the active execution context."
        ec = getthreadlocals().executioncontext
        if ec is None:
            ec = self.createexecutioncontext()
        return ec

    def createexecutioncontext(self):
        "Factory function for execution contexts."
        return ExecutionContext(self)

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones.  Subclasses
    # may also override specific functions for performance.

    def is_(self, w_x, w_y):
        "'x is y'."
        w_id_x = self.id(w_x)
        w_id_y = self.id(w_y)
        return self.eq(w_id_x, w_id_y)

    def not_(self, w_obj):
        return self.wrap(not self.is_true(w_obj))

    def unwrapdefault(self, w_value, default):
        if w_value is None or w_value == self.w_None:
            return default
        else:
            return self.unwrap(w_value)

    def newbool(self, b):
        if b:
            return self.w_True
        else:
            return self.w_False

    def unpackiterable(self, w_iterable, expected_length=None):
        """Unpack an iterable object into a real (interpreter-level) list.
        Raise a real ValueError if the length is wrong."""
        w_iterator = self.iter(w_iterable)
        items = []
        while True:
            try:
                w_item = self.next(w_iterator)
            except OperationError, e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break  # done
            if expected_length is not None and len(items) == expected_length:
                raise ValueError, "too many values to unpack"
            items.append(w_item)
        if expected_length is not None and len(items) < expected_length:
            i = len(items)
            if i == 1:
                plural = ""
            else:
                plural = "s"
            raise ValueError, "need more than %d value%s to unpack" % (i, plural)
        return items

    def unpacktuple(self, w_tuple, expected_length=None):
        """Same as unpackiterable(), but only for tuples.
        Only use for bootstrapping or performance reasons."""
        tuple_length = self.unwrap(self.len(w_tuple))
        if expected_length is not None and tuple_length != expected_length:
            raise ValueError, "got a tuple of length %d instead of %d" % (
                tuple_length, expected_length)
        items = [
            self.getitem(w_tuple, self.wrap(i)) for i in range(tuple_length)]
        return items

    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        check_list = [w_check_class]
        while check_list:
            w_item = check_list.pop()
            # Match identical items.
            if self.is_true(self.is_(w_exc_type, w_item)):
                return True
            try:
                # Match subclasses.
                if self.is_true(self.issubtype(w_exc_type, w_item)):
                    return True
            except OperationError:
                # Assume that this is a TypeError: w_item not a type,
                # and assume that w_item is then actually a tuple.
                try:
                    exclst = self.unpackiterable(w_item)
                except OperationError:
                    # hum, maybe it is not a tuple after all, and w_exc_type
                    # was not a type at all (string exceptions).  Give up.
                    continue
                check_list.extend(exclst)
        return False

    def call(self, w_callable, w_args, w_kwds=None):
        args = Arguments.frompacked(self, w_args, w_kwds)
        return self.call_args(w_callable, args)

    def call_function(self, w_func, *args_w):
        args = Arguments(self, list(args_w))
        return self.call_args(w_func, args)

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = self.getattr(w_obj, self.wrap(methname))
        return self.call_function(w_meth, *arg_w)

    def isinstance(self, w_obj, w_type):
        w_objtype = self.type(w_obj)
        return self.issubtype(w_objtype, w_type)

    def eval(self, expression, w_globals, w_locals):
        "For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(expression, str):
            expression = compile(expression, '?', 'eval')
        if isinstance(expression, types.CodeType):
            expression = PyCode()._from_code(expression)
        if not isinstance(expression, PyCode):
            raise TypeError, 'space.eval(): expected a string, code or PyCode object'
        return expression.exec_code(self, w_globals, w_locals)

    def exec_(self, statement, w_globals, w_locals):
        "For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(statement, str):
            statement = compile(statement, '?', 'exec')
        if isinstance(statement, types.CodeType):
            statement = PyCode()._from_code(statement)
        if not isinstance(statement, PyCode):
            raise TypeError, 'space.exec_(): expected a string, code or PyCode object'
        return statement.exec_code(self, w_globals, w_locals)


## Table describing the regular part of the interface of object spaces,
## namely all methods which only take w_ arguments and return a w_ result
## (if any).  XXX Maybe we should say that these methods must be accessed
## as 'space.op.xxx()' instead of directly 'space.xxx()'.

ObjSpace.MethodTable = [
# method name # symbol # number of arguments # special method name(s)
    ('id',              'id',        1, []),
    ('type',            'type',      1, []),
    ('issubtype',       'issubtype', 2, []),  # not for old-style classes
    ('repr',            'repr',      1, ['__repr__']),
    ('str',             'str',       1, ['__str__']),
    ('len',             'len',       1, ['__len__']),
    ('hash',            'hash',      1, ['__hash__']),
    ('getattr',         'getattr',   2, ['__getattribute__']),
    ('setattr',         'setattr',   3, ['__setattr__']),
    ('delattr',         'delattr',   2, ['__delattr__']),
    ('getitem',         'getitem',   2, ['__getitem__']),
    ('setitem',         'setitem',   3, ['__setitem__']),
    ('delitem',         'delitem',   2, ['__delitem__']),
    ('pos',             'pos',       1, ['__pos__']),
    ('neg',             'neg',       1, ['__neg__']),
    ('nonzero',         'truth',     1, ['__nonzero__']),
    ('abs' ,            'abs',       1, ['__abs__']),
    ('hex',             'hex',       1, ['__hex__']),
    ('oct',             'oct',       1, ['__oct__']),
    ('round',           'round',     2, []),
    ('ord',             'ord',       1, []),
    ('invert',          '~',         1, ['__invert__']),
    ('add',             '+',         2, ['__add__', '__radd__']),
    ('sub',             '-',         2, ['__sub__', '__rsub__']),
    ('mul',             '*',         2, ['__mul__', '__rmul__']),
    ('truediv',         '/',         2, ['__truediv__', '__rtruediv__']),
    ('floordiv',        '//',        2, ['__floordiv__', '__rfloordiv__']),
    ('div',             'div',       2, ['__div__', '__rdiv__']),
    ('mod',             '%',         2, ['__mod__', '__rmod__']),
    ('divmod',          'divmod',    2, ['__divmod__', '__rdivmod__']),
    ('pow',             '**',        3, ['__pow__', '__rpow__']),
    ('lshift',          '<<',        2, ['__lshift__', '__rlshift__']),
    ('rshift',          '>>',        2, ['__rshift__', '__rrshift__']),
    ('and_',            '&',         2, ['__and__', '__rand__']),
    ('or_',             '|',         2, ['__or__', '__ror__']),
    ('xor',             '^',         2, ['__xor__', '__rxor__']),
    ('int',             'int',       1, ['__int__']),
    ('float',           'float',     1, ['__float__']),
    ('long',            'long',      1, ['__long__']),
    ('inplace_add',     '+=',        2, ['__iadd__']),
    ('inplace_sub',     '-=',        2, ['__isub__']),
    ('inplace_mul',     '*=',        2, ['__imul__']),
    ('inplace_truediv', '/=',        2, ['__itruediv__']),
    ('inplace_floordiv','//=',       2, ['__ifloordiv__']),
    ('inplace_div',     'div=',      2, ['__idiv__']),
    ('inplace_mod',     '%=',        2, ['__imod__']),
    ('inplace_pow',     '**=',       2, ['__ipow__']),
    ('inplace_lshift',  '<<=',       2, ['__ilshift__']),
    ('inplace_rshift',  '>>=',       2, ['__irshift__']),
    ('inplace_and',     '&=',        2, ['__iand__']),
    ('inplace_or',      '|=',        2, ['__ior__']),
    ('inplace_xor',     '^=',        2, ['__ixor__']),
    ('lt',              '<',         2, ['__lt__', '__gt__']),
    ('le',              '<=',        2, ['__le__', '__ge__']),
    ('eq',              '==',        2, ['__eq__', '__eq__']),
    ('ne',              '!=',        2, ['__ne__', '__ne__']),
    ('gt',              '>',         2, ['__gt__', '__lt__']),
    ('ge',              '>=',        2, ['__ge__', '__le__']),
    ('contains',        'contains',  2, ['__contains__']),
    ('iter',            'iter',      1, ['__iter__']),
    ('next',            'next',      1, ['next']),
#    ('call',            'call',      3, ['__call__']),
    ('get',             'get',       3, ['__get__']),
    ('set',             'set',       3, ['__set__']),
    ('delete',          'delete',    2, ['__delete__']),
    ]

ObjSpace.BuiltinModuleTable = [
    '__builtin__',
    'sys',
    ]

ObjSpace.ConstantTable = [
    'None',
    'False',
    'True',
    'Ellipsis',
    'NotImplemented',
    ]

ObjSpace.ExceptionTable = [
    'ArithmeticError',
    'AssertionError',
    'AttributeError',
    'EOFError',
    'EnvironmentError',
    'Exception',
    'FloatingPointError',
    'IOError',
    'ImportError',
    'IndentationError',
    'IndexError',
    'KeyError',
    'KeyboardInterrupt',
    'LookupError',
    'MemoryError',
    'NameError',
    'NotImplementedError',
    'OSError',
    'OverflowError',
    'ReferenceError',
    'RuntimeError',
    'StandardError',
    'StopIteration',
    'SyntaxError',
    'SystemError',
    'SystemExit',
    'TabError',
    'TypeError',
    'UnboundLocalError',
    'UnicodeError',
    'ValueError',
    'ZeroDivisionError',
    ]

## Irregular part of the interface:
#
#                        wrap(x) -> w_x
#                    unwrap(w_x) -> x
#                   is_true(w_x) -> True or False
#       newtuple([w_1, w_2,...]) -> w_tuple
#        newlist([w_1, w_2,...]) -> w_list
#      newstring([w_1, w_2,...]) -> w_string from ascii numbers (bytes)
# newdict([(w_key,w_value),...]) -> w_dict
#newslice(w_start,w_stop,w_step) -> w_slice (any argument may be a real None)
#   call_args(w_obj,Arguments()) -> w_result
