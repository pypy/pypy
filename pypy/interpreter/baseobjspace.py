
__all__ = ['ObjSpace', 'OperationError', 'NoValue']

class OperationError(Exception):
    """Interpreter-level exception that signals an exception that should be
    sent to the application level.

    OperationError instances have three public attributes (and no .args),
    w_type, w_value and w_traceback, which contain the wrapped type, value
    and traceback describing the exception."""

    def __init__(self, w_type, w_value, w_traceback=None):
        self.w_type = w_type
        self.w_value = w_value
        self.w_traceback = w_traceback
        ### DEBUG DUMP ###
        #self.nicetraceback(None)
    
    def __str__(self):
        "Convenience for tracebacks."
        return '[%s: %s]' % (self.w_type, self.w_value)
    def nicetraceback(self, space):
        "Dump a nice custom traceback to sys.stderr."
        import sys, traceback
        tb = sys.exc_info()[2]
        if space is not None:
            exc = space.unwrap(self.w_type)
            value = space.unwrap(self.w_value)
            msg = traceback.format_exception_only(exc, value)
        else:
            msg = '%r: %r' % (self.w_type, self.w_value)
        print >> sys.stderr, "*"*10, " OperationError ", "*"*10
        traceback.print_tb(tb)
##         if self.w_traceback:
##             traceback.print_tb(space.unwrap(self.w_traceback))
        print >> sys.stderr, "[Application-level]", ''.join(msg).strip()
        print >> sys.stderr, "*"*10

class NoValue(Exception):
    """Raised to signal absence of value, e.g. in the iterator accessing
    method 'iternext()' of object spaces."""


##################################################################

import executioncontext, pyframe


class ObjSpace:
    """Base class for the interpreter-level implementations of object spaces.
    XXX describe here in more details what the object spaces are."""

    def __init__(self):
        "Basic initialization of objects.  Override me."
        self.w_builtins = self.newdict([])
        self.w_modules  = self.newdict([])
        self.appfile_helpers = {}
        self.initialize()
        #import builtins
        #builtins.init(self)

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
        return executioncontext.ExecutionContext(self)

    def gethelper(self, applicationfile):
        try:
            helper = self.appfile_helpers[applicationfile]
        except KeyError:
            from appfile import AppHelper
            helper = AppHelper(self, applicationfile.bytecode)
            self.appfile_helpers[applicationfile] = helper
        return helper

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones

    def unpackiterable(self, w_iterable, expected_length=None):
        """Unpack an iterable object into a real (interpreter-level) list.
        Raise a real ValueError if the length is wrong."""
        w_iterator = self.getiter(w_iterable)
        items = []
        while True:
            try:
                w_item = self.iternext(w_iterator)
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


## Table describing the regular part of the interface of object spaces,
## namely all methods which only take w_ arguments and return a w_ result.

ObjSpace.MethodTable = [
# method name # symbol # number of arguments
    ('type',            'type',     1),
    ('checktype',       'type?',    2),
    ('repr',            'repr',     1),
    ('str',             'str',      1),
    ('getattr',         'getattr',  2),
    ('setattr',         'setattr',  3),
    ('delattr',         'delattr',  2),
    ('getitem',         'getitem',  2),
    ('setitem',         'setitem',  3),
    ('delitem',         'delitem',  2),
    ('pos',             'unary+',   1),
    ('neg',             'unary-',   1),
    ('not_',            'not',      1),
    ('abs' ,            'abs',      1),
    ('invert',          '~',        1),
    ('add',             '+',        2),
    ('sub',             '-',        2),
    ('mul',             '*',        2),
    ('truediv',         '/',        2),
    ('floordiv',        '//',       2),
    ('div',             'div',      2),
    ('mod',             '%',        2),
    ('divmod',          'divmod',   2),
    ('pow',             '**',       3),
    ('lshift',          '<<',       2),
    ('rshift',          '>>',       2),
    ('and_',            '&',        2),
    ('or_',             '|',        2),
    ('xor',             '^',        2),
    ('inplace_add',     '+=',       2),
    ('inplace_sub',     '-=',       2),
    ('inplace_mul',     '*=',       2),
    ('inplace_truediv', '/=',       2),
    ('inplace_floordiv','//=',      2),
    ('inplace_div',     'div=',     2),
    ('inplace_mod',     '%=',       2),
    ('inplace_pow',     '**=',      2),
    ('inplace_lshift',  '<<=',      2),
    ('inplace_rshift',  '>>=',      2),
    ('inplace_and',     '&=',       2),
    ('inplace_or',      '|=',       2),
    ('inplace_xor',     '^=',       2),
    ('getiter',         'iter',     1),
    ('iternext',        'next',     1),
    ('call',            'call',     3),
    ]

## Irregular part of the interface:
#
#                        wrap(x) -> w_x
#                    unwrap(w_x) -> x
#                   is_true(w_x) -> True or False
#                      hash(w_x) -> int
#          compare(w_x, w_y, op) -> w_result
#       newtuple([w_1, w_2,...]) -> w_tuple
#        newlist([w_1, w_2,...]) -> w_list
# newdict([(w_key,w_value),...]) -> w_dict
# newslice(w_start,w_stop,w_end) -> w_slice     (w_end may be a real None)
#               newfunction(...) -> w_function
#
