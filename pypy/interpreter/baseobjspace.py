from executioncontext import ExecutionContext, OperationError, NoValue
import pyframe, threadlocals
import pypy.module.builtin

__all__ = ['ObjSpace', 'OperationError', 'NoValue', 'PyPyError']

class PyPyError(Exception):
    "Raise this when you encounter an exceptional situation in PyPy itself."
    def __init__(self, space, operationerr):
        self.space = space
        self.operationerr = operationerr


class ObjSpace:
    """Base class for the interpreter-level implementations of object spaces.
    XXX describe here in more details what the object spaces are."""

    def __init__(self):
        "Basic initialization of objects."
        self.w_modules = self.newdict([])
        self.appfile_helpers = {}
        self.initialize()

    def make_builtins(self):
        self.builtin = pypy.module.builtin.Builtin(self)
        self.w_builtin = self.builtin.wrap_base()
        self.w_builtins = self.getattr(self.w_builtin, self.wrap("__dict__"))
        self.builtin.wrap_appfile(self.w_builtin)

    def make_sys(self):
        import pypy.module.sysmodule
        self.sys = pypy.module.sysmodule.Sys(self)
        self.w_sys = self.sys.wrap_me()
        self.setattr(self.w_sys, self.wrap("modules"), self.w_modules)

    # XXX use a dictionary in the future
    def get_builtin_module(self, w_name):
        name = self.unwrap(w_name)
        if name == '__builtin__':
            return self.w_builtin
        elif name == 'sys':
            return self.w_sys
        return None

    def initialize(self):
        """Abstract method that should put some minimal content into the
        w_builtins."""

    def getexecutioncontext(self):
        "Return what we consider to be the active execution context."
        ec = threadlocals.getlocals().executioncontext
        if ec is None:
            ec = self.createexecutioncontext()
        return ec

    def createexecutioncontext(self):
        "Factory function for execution contexts."
        return ExecutionContext(self)

    def gethelper(self, applicationfile):
        try:
            helper = self.appfile_helpers[applicationfile]
        except KeyError:
            from appfile import AppHelper
            helper = AppHelper(self, applicationfile)
            self.appfile_helpers[applicationfile] = helper
        return helper

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones.  Subclasses
    # may also override specific functions for performance.

    def is_(self, w_x, w_y):
        "'x is y'."
        w_id_x = self.id(w_x)
        w_id_y = self.id(w_y)
        return self.eq(w_id_x, w_id_y)

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
            except NoValue:
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
        items = []
        for i in range(tuple_length):
            w_i = self.wrap(i)
            w_item = self.getitem(w_tuple, w_i)
            items.append(w_item)
        return items

    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        check_list = [w_check_class]
        while check_list:
            w_item = check_list.pop()
            #Test within iterables (i.e. tuples)
            try:
                exclst = self.unpackiterable(w_item)
                check_list.extend(exclst)
            except KeyboardInterrupt:
                raise
            except:
                #w_check_class is not iterable
                pass
            #w_item should now be an Exception (or string?)
            #Match identical items.
            w_rv = self.is_(w_exc_type, w_item)
            if self.is_true(w_rv):
                return w_rv
            #Match subclasses.
            try:
                w_rv = self.issubtype(w_exc_type, w_item)
            except KeyboardInterrupt:
                raise
            except:
                pass
            else:
                if self.is_true(w_rv):
                    return w_rv
        return self.w_False

    def call_function(self, w_func, *args_w, **kw_w):
        w_kw = self.newdict([(self.wrap(k), w_v) for k, w_v in kw_w.iteritems()])
        return self.call(w_func, self.newtuple(list(args_w)), w_kw)
            
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
    ('not_',            'not',       1, []),
    ('abs' ,            'abs',       1, ['__abs__']),
    ('hex',             'hex',       1, ['__hex__']),
    ('oct',             'oct',       1, ['__oct__']),
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
    ('call',            'call',      3, ['__call__']),
    ('get',             'get',       3, ['__get__']),
    ('set',             'set',       2, ['__set__']),
    ('delete',          'delete',    2, ['__delete__']),
    ('new',             'new',       3, ['__new__']),
    ('init',            'init',      3, ['__init__']),
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
# newslice(w_start,w_stop,w_end) -> w_slice     (w_end may be a real None)
#               newfunction(...) -> w_function
#              newmodule(w_name) -> w_module
#                   next(w_iter) -> w_value or raise NoValue
#
