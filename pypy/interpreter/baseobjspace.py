from executioncontext import ExecutionContext, OperationError, NoValue
import pyframe
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
        import sys
        f = sys._getframe()           # !!hack!!
        while f:
            if f.f_locals.has_key('__executioncontext__'):
                result = f.f_locals['__executioncontext__']
                if result.space is self:
                    return result
            f = f.f_back
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
        #Match identical items.
        w_rv = self.is_(w_exc_type, w_check_class)
        if self.is_true(w_rv):
            return w_rv
        #Match subclasses.
        try:
            w_rv = self.issubtype(w_exc_type, w_check_class)
        except: pass
        else:
            if self.is_true(w_rv):
                return w_rv
        #Match tuples containing identical or parent classes
        try:
            exclst = self.unpackiterable(w_check_class)
        except:
            #w_check_class is not iterable
            return self.w_False
        #w_check_class is iterable
        for w_item in exclst:
            w_rv = self.is_(w_exc_type, w_item)
            if self.is_true(w_rv):
                return w_rv
            try:
                w_rv = self.issubtype(w_exc_type, w_item)
            except: pass
            else:
                if self.is_true(w_rv):
                    return w_rv
        return self.w_False

    def call_function(self, w_func, *args_w, **kw_w):
        w_kw = self.newdict([])
        for k, w_v in kw_w.iteritems():
            self.setitem(w_kw, self.wrap(k), w_v)
        return self.call(w_func, self.newtuple(list(args_w)), w_kw)
            
## Table describing the regular part of the interface of object spaces,
## namely all methods which only take w_ arguments and return a w_ result
## (if any).  XXX Maybe we should say that these methods must be accessed
## as 'space.op.xxx()' instead of directly 'space.xxx()'.

ObjSpace.MethodTable = [
# method name # symbol # number of arguments
    ('id',              'id',        1),
    ('type',            'type',      1),
    ('issubtype',       'issubtype', 2),  # not for old-style classes
    ('repr',            'repr',      1),
    ('str',             'str',       1),
    ('len',             'len',       1),
    ('hash',            'hash',      1),
    ('getattr',         'getattr',   2),
    ('setattr',         'setattr',   3),
    ('delattr',         'delattr',   2),
    ('getitem',         'getitem',   2),
    ('setitem',         'setitem',   3),
    ('delitem',         'delitem',   2),
    ('pos',             'pos',       1),
    ('neg',             'neg',       1),
    ('not_',            'not',       1),
    ('abs' ,            'abs',       1),
    ('hex',             'hex',       1),
    ('oct',             'oct',       1),
    ('ord',             'ord',       1),
    ('invert',          '~',         1),
    ('add',             '+',         2),
    ('sub',             '-',         2),
    ('mul',             '*',         2),
    ('truediv',         '/',         2),
    ('floordiv',        '//',        2),
    ('div',             'div',       2),
    ('mod',             '%',         2),
    ('divmod',          'divmod',    2),
    ('pow',             '**',        3),
    ('lshift',          '<<',        2),
    ('rshift',          '>>',        2),
    ('and_',            '&',         2),
    ('or_',             '|',         2),
    ('xor',             '^',         2),
    ('inplace_add',     '+=',        2),
    ('inplace_sub',     '-=',        2),
    ('inplace_mul',     '*=',        2),
    ('inplace_truediv', '/=',        2),
    ('inplace_floordiv','//=',       2),
    ('inplace_div',     'div=',      2),
    ('inplace_mod',     '%=',        2),
    ('inplace_pow',     '**=',       2),
    ('inplace_lshift',  '<<=',       2),
    ('inplace_rshift',  '>>=',       2),
    ('inplace_and',     '&=',        2),
    ('inplace_or',      '|=',        2),
    ('inplace_xor',     '^=',        2),
    ('lt',              '<',         2),
    ('le',              '<=',        2),
    ('eq',              '==',        2),
    ('ne',              '!=',        2),
    ('gt',              '>',         2),
    ('ge',              '>=',        2),
    ('contains',        'contains',  2),
    ('iter',            'iter',      1),
    ('next',            'next',      1),  # iterator interface
    ('call',            'call',      3),
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
#
