
"""Python's standard exception class hierarchy.

Before Python 1.5, the standard exceptions were all simple string objects.
In Python 1.5, the standard exceptions were converted to classes organized
into a relatively flat hierarchy.  String-based standard exceptions were
optional, or used as a fallback if some problem occurred while importing
the exception module.  With Python 1.6, optional string-based standard
exceptions were removed (along with the -X command line flag).

The class exceptions were implemented in such a way as to be almost
completely backward compatible.  Some tricky uses of IOError could
potentially have broken, but by Python 1.6, all of these should have
been fixed.  As of Python 1.6, the class-based standard exceptions are
now implemented in C, and are guaranteed to exist in the Python
interpreter.

Here is a rundown of the class hierarchy.  The classes found here are
inserted into both the exceptions module and the `built-in' module.  It is
recommended that user defined class based exceptions be derived from the
`Exception' class, although this is currently not enforced.

BaseException
 +-- SystemExit
 +-- KeyboardInterrupt
 +-- GeneratorExit
 +-- Exception
      +-- StopIteration
      +-- StandardError
      |    +-- BufferError
      |    +-- ArithmeticError
      |    |    +-- FloatingPointError
      |    |    +-- OverflowError
      |    |    +-- ZeroDivisionError
      |    +-- AssertionError
      |    +-- AttributeError
      |    +-- EnvironmentError
      |    |    +-- IOError
      |    |    +-- OSError
      |    |         +-- WindowsError (Windows)
      |    |         +-- VMSError (VMS)
      |    +-- EOFError
      |    +-- ImportError
      |    +-- LookupError
      |    |    +-- IndexError
      |    |    +-- KeyError
      |    +-- MemoryError
      |    +-- NameError
      |    |    +-- UnboundLocalError
      |    +-- ReferenceError
      |    +-- RuntimeError
      |    |    +-- NotImplementedError
      |    +-- SyntaxError
      |    |    +-- IndentationError
      |    |         +-- TabError
      |    +-- SystemError
      |    +-- TypeError
      |    +-- ValueError
      |         +-- UnicodeError
      |              +-- UnicodeDecodeError
      |              +-- UnicodeEncodeError
      |              +-- UnicodeTranslateError
      +-- Warning
           +-- DeprecationWarning
           +-- PendingDeprecationWarning
           +-- RuntimeWarning
           +-- SyntaxWarning
           +-- UserWarning
           +-- FutureWarning
           +-- ImportWarning
           +-- UnicodeWarning
           +-- BytesWarning
"""

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty_w,\
     GetSetProperty, interp_attrproperty, descr_get_dict, descr_set_dict,\
     descr_del_dict
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.rlib import rwin32

def readwrite_attrproperty_w(name, cls):
    def fget(space, obj):
        return getattr(obj, name)
    def fset(space, obj, w_val):
        setattr(obj, name, w_val)
    return GetSetProperty(fget, fset, cls=cls)

class W_BaseException(Wrappable):
    """Superclass representing the base of the exception hierarchy.

    The __getitem__ method is provided for backwards-compatibility
    and will be deprecated at some point.
    """
    w_dict = None
    args_w = []

    def __init__(self, space):
        self.w_message = space.w_None

    def descr_init(self, space, args_w):
        self.args_w = args_w
        if len(args_w) == 1:
            self.w_message = args_w[0]
        else:
            self.w_message = space.wrap("")

    def descr_str(self, space):
        lgt = len(self.args_w)
        if lgt == 0:
            return space.wrap('')
        elif lgt == 1:
            return space.str(self.args_w[0])
        else:
            return space.str(space.newtuple(self.args_w))

    def descr_unicode(self, space):
        w_str = space.lookup(self, "__str__")
        w_base_type = space.gettypeobject(W_BaseException.typedef)
        w_base_str = w_base_type.dict_w["__str__"]
        if not space.is_w(w_str, w_base_str):
            w_as_str = space.get_and_call_function(w_str, space.wrap(self))
            return space.call_function(space.w_unicode, w_as_str)
        lgt = len(self.args_w)
        if lgt == 0:
            return space.wrap(u"")
        if lgt == 1:
            return space.call_function(space.w_unicode, self.args_w[0])
        else:
            w_tup = space.newtuple(self.args_w)
            return space.call_function(space.w_unicode, w_tup)

    def descr_repr(self, space):
        if self.args_w:
            args_repr = space.str_w(space.repr(space.newtuple(self.args_w)))
        else:
            args_repr = "()"
        clsname = self.getclass(space).getname(space, '?')
        return space.wrap(clsname + args_repr)

    def descr_getargs(self, space):
        return space.newtuple(self.args_w)

    def descr_setargs(self, space, w_newargs):
        self.args_w = space.fixedview(w_newargs)

    def descr_getitem(self, space, w_index):
        return space.getitem(space.newtuple(self.args_w), w_index)

    def getdict(self, space):
        if self.w_dict is None:
            self.w_dict = space.newdict(instance=True)
        return self.w_dict

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance( w_dict, space.w_dict )):
            raise OperationError( space.w_TypeError, space.wrap("setting exceptions's dictionary to a non-dict") )
        self.w_dict = w_dict

    def descr_reduce(self, space):
        lst = [self.getclass(space), space.newtuple(self.args_w)]
        if self.w_dict is not None and space.is_true(self.w_dict):
            lst = lst + [self.w_dict]
        return space.newtuple(lst)

    def descr_setstate(self, space, w_dict):
        w_olddict = self.getdict(space)
        space.call_method(w_olddict, 'update', w_dict)

    def descr_message_get(self, space):
        w_dict = self.w_dict
        if w_dict is not None:
            w_msg = space.finditem(w_dict, space.wrap("message"))
            if w_msg is not None:
                return w_msg
        if self.w_message is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("message was deleted"))
        space.warn("BaseException.message has been deprecated as of Python 2.6",
                   space.w_DeprecationWarning)
        return self.w_message

    def descr_message_set(self, space, w_new):
        space.setitem(self.getdict(space), space.wrap("message"), w_new)

    def descr_message_del(self, space):
        w_dict = self.w_dict
        if w_dict is not None:
            try:
                space.delitem(w_dict, space.wrap("message"))
            except OperationError, e:
                if not e.match(space, space.w_KeyError):
                    raise
        self.w_message = None

def _new(cls, basecls=None):
    if basecls is None:
        basecls = cls
    def descr_new_base_exception(space, w_subtype, __args__):
        exc = space.allocate_instance(cls, w_subtype)
        basecls.__init__(exc, space)
        return space.wrap(exc)
    descr_new_base_exception.func_name = 'descr_new_' + cls.__name__
    return interp2app(descr_new_base_exception)

W_BaseException.typedef = TypeDef(
    'BaseException',
    __doc__ = W_BaseException.__doc__,
    __module__ = 'exceptions',
    __new__ = _new(W_BaseException),
    __init__ = interp2app(W_BaseException.descr_init),
    __str__ = interp2app(W_BaseException.descr_str),
    __unicode__ = interp2app(W_BaseException.descr_unicode),
    __repr__ = interp2app(W_BaseException.descr_repr),
    __dict__ = GetSetProperty(descr_get_dict, descr_set_dict, descr_del_dict,
                              cls=W_BaseException),
    __getitem__ = interp2app(W_BaseException.descr_getitem),
    __reduce__ = interp2app(W_BaseException.descr_reduce),
    __setstate__ = interp2app(W_BaseException.descr_setstate),
    message = GetSetProperty(W_BaseException.descr_message_get,
                            W_BaseException.descr_message_set,
                            W_BaseException.descr_message_del),
    args = GetSetProperty(W_BaseException.descr_getargs,
                          W_BaseException.descr_setargs),
)

def _new_exception(name, base, docstring, **kwargs):
    # Create a subclass W_Exc of the class 'base'.  Note that there is
    # hackery going on on the typedef of W_Exc: when we make further
    # app-level subclasses, they inherit at interp-level from 'realbase'
    # instead of W_Exc.  This allows multiple inheritance to work (see
    # test_multiple_inheritance in test_exc.py).

    class W_Exc(base):
        __doc__ = docstring

    W_Exc.__name__ = 'W_' + name

    realbase = base.typedef.applevel_subclasses_base or base

    for k, v in kwargs.items():
        kwargs[k] = interp2app(v.__get__(None, realbase))
    W_Exc.typedef = TypeDef(
        name,
        base.typedef,
        __doc__ = W_Exc.__doc__,
        __module__ = 'exceptions',
        **kwargs
    )
    W_Exc.typedef.applevel_subclasses_base = realbase
    return W_Exc

W_Exception = _new_exception('Exception', W_BaseException,
                         """Common base class for all non-exit exceptions.""")

W_GeneratorExit = _new_exception('GeneratorExit', W_BaseException,
                          """Request that a generator exit.""")

W_StandardError = _new_exception('StandardError', W_Exception,
                         """Base class for all standard Python exceptions.""")

W_BufferError = _new_exception('BufferError', W_StandardError,
                         """Buffer error.""")

W_ValueError = _new_exception('ValueError', W_StandardError,
                         """Inappropriate argument value (of correct type).""")

W_ImportError = _new_exception('ImportError', W_StandardError,
                  """Import can't find module, or can't find name in module.""")

W_RuntimeError = _new_exception('RuntimeError', W_StandardError,
                     """Unspecified run-time error.""")

W_UnicodeError = _new_exception('UnicodeError', W_ValueError,
                          """Unicode related error.""")


class W_UnicodeTranslateError(W_UnicodeError):
    """Unicode translation error."""
    object = None
    start = None
    end = None
    reason = None

    def descr_init(self, space, w_object, w_start, w_end, w_reason):
        # typechecking
        space.realunicode_w(w_object)
        space.int_w(w_start)
        space.int_w(w_end)
        space.realstr_w(w_reason)
        # assign attributes
        self.w_object = w_object
        self.w_start = w_start
        self.w_end = w_end
        self.w_reason = w_reason
        W_BaseException.descr_init(self, space, [w_object, w_start,
                                                 w_end, w_reason])

    def descr_str(self, space):
        return space.appexec([space.wrap(self)], r"""(self):
            if self.end == self.start + 1:
                badchar = ord(self.object[self.start])
                if badchar <= 0xff:
                    return "can't translate character u'\\x%02x' in position %d: %s" % (badchar, self.start, self.reason)
                if badchar <= 0xffff:
                    return "can't translate character u'\\u%04x' in position %d: %s"%(badchar, self.start, self.reason)
                return "can't translate character u'\\U%08x' in position %d: %s"%(badchar, self.start, self.reason)
            return "can't translate characters in position %d-%d: %s" % (self.start, self.end - 1, self.reason)
        """)

W_UnicodeTranslateError.typedef = TypeDef(
    'UnicodeTranslateError',
    W_UnicodeError.typedef,
    __doc__ = W_UnicodeTranslateError.__doc__,
    __module__ = 'exceptions',
    __new__ = _new(W_UnicodeTranslateError),
    __init__ = interp2app(W_UnicodeTranslateError.descr_init),
    __str__ = interp2app(W_UnicodeTranslateError.descr_str),
    object = readwrite_attrproperty_w('w_object', W_UnicodeTranslateError),
    start  = readwrite_attrproperty_w('w_start', W_UnicodeTranslateError),
    end    = readwrite_attrproperty_w('w_end', W_UnicodeTranslateError),
    reason = readwrite_attrproperty_w('w_reason', W_UnicodeTranslateError),
)

W_LookupError = _new_exception('LookupError', W_StandardError,
                               """Base class for lookup errors.""")

def key_error_str(self, space):
    if len(self.args_w) == 0:
        return space.wrap('')
    elif len(self.args_w) == 1:
        return space.repr(self.args_w[0])
    else:
        return space.str(space.newtuple(self.args_w))

W_KeyError = _new_exception('KeyError', W_LookupError,
                            """Mapping key not found.""",
                            __str__ = key_error_str)

W_StopIteration = _new_exception('StopIteration', W_Exception,
                                 """Signal the end from iterator.next().""")

W_Warning = _new_exception('Warning', W_Exception,
                           """Base class for warning categories.""")

W_PendingDeprecationWarning = _new_exception('PendingDeprecationWarning',
                                             W_Warning,
       """Base class for warnings about features which will be deprecated in the future.""")

class W_EnvironmentError(W_StandardError):
    """Base class for I/O related errors."""

    def __init__(self, space):
        self.w_errno = space.w_None
        self.w_strerror = space.w_None
        self.w_filename = space.w_None
        W_BaseException.__init__(self, space)

    def descr_init(self, space, args_w):
        W_BaseException.descr_init(self, space, args_w)
        if 2 <= len(args_w) <= 3:
            self.w_errno = args_w[0]
            self.w_strerror = args_w[1]
        if len(args_w) == 3:
            self.w_filename = args_w[2]
            self.args_w = [args_w[0], args_w[1]]

    # since we rebind args_w, we need special reduce, grump
    def descr_reduce(self, space):
        if not space.is_w(self.w_filename, space.w_None):
            lst = [self.getclass(space), space.newtuple(
                self.args_w + [self.w_filename])]
        else:
            lst = [self.getclass(space), space.newtuple(self.args_w)]
        if self.w_dict is not None and space.is_true(self.w_dict):
            lst = lst + [self.w_dict]
        return space.newtuple(lst)

    def descr_str(self, space):
        if (not space.is_w(self.w_errno, space.w_None) and
            not space.is_w(self.w_strerror, space.w_None)):
            errno = space.str_w(space.str(self.w_errno))
            strerror = space.str_w(space.str(self.w_strerror))
            if not space.is_w(self.w_filename, space.w_None):
                return space.wrap("[Errno %s] %s: %s" % (
                    errno,
                    strerror,
                    space.str_w(space.repr(self.w_filename))))
            return space.wrap("[Errno %s] %s" % (
                errno,
                strerror,
            ))
        return W_BaseException.descr_str(self, space)

W_EnvironmentError.typedef = TypeDef(
    'EnvironmentError',
    W_StandardError.typedef,
    __doc__ = W_EnvironmentError.__doc__,
    __module__ = 'exceptions',
    __new__ = _new(W_EnvironmentError),
    __reduce__ = interp2app(W_EnvironmentError.descr_reduce),
    __init__ = interp2app(W_EnvironmentError.descr_init),
    __str__ = interp2app(W_EnvironmentError.descr_str),
    errno    = readwrite_attrproperty_w('w_errno',    W_EnvironmentError),
    strerror = readwrite_attrproperty_w('w_strerror', W_EnvironmentError),
    filename = readwrite_attrproperty_w('w_filename', W_EnvironmentError),
    )

W_OSError = _new_exception('OSError', W_EnvironmentError,
                           """OS system call failed.""")

class W_WindowsError(W_OSError):
    """MS-Windows OS system call failed."""

    def __init__(self, space):
        self.w_winerror = space.w_None
        W_OSError.__init__(self, space)

    def descr_init(self, space, args_w):
        # Set errno to the POSIX errno, and winerror to the Win32
        # error code.
        W_OSError.descr_init(self, space, args_w)
        try:
            errno = space.int_w(self.w_errno)
        except OperationError:
            errno = self._default_errno
        else:
            errno = self._winerror_to_errno.get(errno, self._default_errno)
        self.w_winerror = self.w_errno
        self.w_errno = space.wrap(errno)

    def descr_str(self, space):
        if (not space.is_w(self.w_winerror, space.w_None) and
            not space.is_w(self.w_strerror, space.w_None)):
            if not space.is_w(self.w_filename, space.w_None):
                return space.wrap("[Error %d] %s: %s" % (
                    space.int_w(self.w_winerror),
                    space.str_w(self.w_strerror),
                    space.str_w(self.w_filename)))
            return space.wrap("[Error %d] %s" % (space.int_w(self.w_winerror),
                                                 space.str_w(self.w_strerror)))
        return W_BaseException.descr_str(self, space)

    if hasattr(rwin32, 'build_winerror_to_errno'):
        _winerror_to_errno, _default_errno = rwin32.build_winerror_to_errno()
    else:
        _winerror_to_errno, _default_errno = {}, 22 # EINVAL

W_WindowsError.typedef = TypeDef(
    "WindowsError",
    W_OSError.typedef,
    __doc__  = W_WindowsError.__doc__,
    __module__ = 'exceptions',
    __new__  = _new(W_WindowsError),
    __init__ = interp2app(W_WindowsError.descr_init),
    __str__  = interp2app(W_WindowsError.descr_str),
    winerror = readwrite_attrproperty_w('w_winerror', W_WindowsError),
    )

W_BytesWarning = _new_exception('BytesWarning', W_Warning,
                                """Mixing bytes and unicode""")

W_DeprecationWarning = _new_exception('DeprecationWarning', W_Warning,
                        """Base class for warnings about deprecated features.""")

W_ArithmeticError = _new_exception('ArithmeticError', W_StandardError,
                         """Base class for arithmetic errors.""")

W_FloatingPointError = _new_exception('FloatingPointError', W_ArithmeticError,
                                      """Floating point operation failed.""")

W_ReferenceError = _new_exception('ReferenceError', W_StandardError,
                           """Weak ref proxy used after referent went away.""")

W_NameError = _new_exception('NameError', W_StandardError,
                             """Name not found globally.""")

W_IOError = _new_exception('IOError', W_EnvironmentError,
                           """I/O operation failed.""")


class W_SyntaxError(W_StandardError):
    """Invalid syntax."""

    def __init__(self, space):
        self.w_filename = space.w_None
        self.w_lineno   = space.w_None
        self.w_offset   = space.w_None
        self.w_text     = space.w_None
        self.w_msg      = space.w_None
        self.w_print_file_and_line = space.w_None # what's that?
        self.w_lastlineno = space.w_None          # this is a pypy extension
        W_BaseException.__init__(self, space)

    def descr_init(self, space, args_w):
        # that's not a self.w_message!!!
        if len(args_w) > 0:
            self.w_msg = args_w[0]
        if len(args_w) == 2:
            values_w = space.fixedview(args_w[1])
            if len(values_w) > 0: self.w_filename   = values_w[0]
            if len(values_w) > 1: self.w_lineno     = values_w[1]
            if len(values_w) > 2: self.w_offset     = values_w[2]
            if len(values_w) > 3: self.w_text       = values_w[3]
            if len(values_w) > 4:
                self.w_lastlineno = values_w[4]   # PyPy extension
                # kill the extra items from args_w to prevent undesired effects
                args_w = args_w[:]
                args_w[1] = space.newtuple(values_w[:4])
        W_BaseException.descr_init(self, space, args_w)

    def descr_str(self, space):
        return space.appexec([self], """(self):
            if type(self.msg) is not str:
                return str(self.msg)

            lineno = None
            buffer = self.msg
            have_filename = type(self.filename) is str
            if type(self.lineno) is int:
                if (type(self.lastlineno) is int and
                       self.lastlineno > self.lineno):
                    lineno = 'lines %d-%d' % (self.lineno, self.lastlineno)
                else:
                    lineno = 'line %d' % (self.lineno,)
            if have_filename:
                import os
                fname = os.path.basename(self.filename or "???")
                if lineno:
                    buffer = "%s (%s, %s)" % (self.msg, fname, lineno)
                else:
                    buffer ="%s (%s)" % (self.msg, fname)
            elif lineno:
                buffer = "%s (%s)" % (self.msg, lineno)
            return buffer
        """)

    def descr_repr(self, space):
        if (len(self.args_w) == 2
            and not space.is_w(self.w_lastlineno, space.w_None)
            and space.len_w(self.args_w[1]) == 4):
            # fake a 5-element tuple in the repr, suitable for calling
            # __init__ again
            values_w = space.fixedview(self.args_w[1])
            w_tuple = space.newtuple(values_w + [self.w_lastlineno])
            args_w = [self.args_w[0], w_tuple]
            args_repr = space.str_w(space.repr(space.newtuple(args_w)))
            clsname = self.getclass(space).getname(space, '?')
            return space.wrap(clsname + args_repr)
        else:
            return W_StandardError.descr_repr(self, space)

W_SyntaxError.typedef = TypeDef(
    'SyntaxError',
    W_StandardError.typedef,
    __new__ = _new(W_SyntaxError),
    __init__ = interp2app(W_SyntaxError.descr_init),
    __str__ = interp2app(W_SyntaxError.descr_str),
    __repr__ = interp2app(W_SyntaxError.descr_repr),
    __doc__ = W_SyntaxError.__doc__,
    __module__ = 'exceptions',
    msg      = readwrite_attrproperty_w('w_msg', W_SyntaxError),
    filename = readwrite_attrproperty_w('w_filename', W_SyntaxError),
    lineno   = readwrite_attrproperty_w('w_lineno', W_SyntaxError),
    offset   = readwrite_attrproperty_w('w_offset', W_SyntaxError),
    text     = readwrite_attrproperty_w('w_text', W_SyntaxError),
    print_file_and_line = readwrite_attrproperty_w('w_print_file_and_line',
                                                   W_SyntaxError),
    lastlineno = readwrite_attrproperty_w('w_lastlineno', W_SyntaxError),
)

W_FutureWarning = _new_exception('FutureWarning', W_Warning,
    """Base class for warnings about constructs that will change semantically in the future.""")

class W_SystemExit(W_BaseException):
    """Request to exit from the interpreter."""

    def __init__(self, space):
        self.w_code = space.w_None
        W_BaseException.__init__(self, space)

    def descr_init(self, space, args_w):
        if len(args_w) == 1:
            self.w_code = args_w[0]
        elif len(args_w) > 1:
            self.w_code = space.newtuple(args_w)
        W_BaseException.descr_init(self, space, args_w)

W_SystemExit.typedef = TypeDef(
    'SystemExit',
    W_BaseException.typedef,
    __new__ = _new(W_SystemExit),
    __init__ = interp2app(W_SystemExit.descr_init),
    __doc__ = W_SystemExit.__doc__,
    __module__ = 'exceptions',
    code    = readwrite_attrproperty_w('w_code', W_SystemExit)
)

W_EOFError = _new_exception('EOFError', W_StandardError,
                            """Read beyond end of file.""")

W_IndentationError = _new_exception('IndentationError', W_SyntaxError,
                                    """Improper indentation.""")

W_TabError = _new_exception('TabError', W_IndentationError,
                            """Improper mixture of spaces and tabs.""")

W_ZeroDivisionError = _new_exception('ZeroDivisionError', W_ArithmeticError,
            """Second argument to a division or modulo operation was zero.""")

W_SystemError = _new_exception('SystemError', W_StandardError,
            """Internal error in the Python interpreter.

Please report this to the Python maintainer, along with the traceback,
the Python version, and the hardware/OS platform and version.""")

W_AssertionError = _new_exception('AssertionError', W_StandardError,
                                  """Assertion failed.""")

class W_UnicodeDecodeError(W_UnicodeError):
    """Unicode decoding error."""
    w_encoding = None
    w_object = None
    w_start = None
    w_end = None
    w_reason = None

    def descr_init(self, space, w_encoding, w_object, w_start, w_end, w_reason):
        # typechecking
        space.realstr_w(w_encoding)
        space.realstr_w(w_object)
        space.int_w(w_start)
        space.int_w(w_end)
        space.realstr_w(w_reason)
        # assign attributes
        self.w_encoding = w_encoding
        self.w_object = w_object
        self.w_start = w_start
        self.w_end = w_end
        self.w_reason = w_reason
        W_BaseException.descr_init(self, space, [w_encoding, w_object,
                                                 w_start, w_end, w_reason])

    def descr_str(self, space):
        return space.appexec([self], """(self):
            if self.end == self.start + 1:
                return "'%s' codec can't decode byte 0x%02x in position %d: %s"%(
                    self.encoding,
                    ord(self.object[self.start]), self.start, self.reason)
            return "'%s' codec can't decode bytes in position %d-%d: %s" % (
                self.encoding, self.start, self.end - 1, self.reason)
        """)

W_UnicodeDecodeError.typedef = TypeDef(
    'UnicodeDecodeError',
    W_UnicodeError.typedef,
    __doc__ = W_UnicodeDecodeError.__doc__,
    __module__ = 'exceptions',
    __new__ = _new(W_UnicodeDecodeError),
    __init__ = interp2app(W_UnicodeDecodeError.descr_init),
    __str__ = interp2app(W_UnicodeDecodeError.descr_str),
    encoding = readwrite_attrproperty_w('w_encoding', W_UnicodeDecodeError),
    object = readwrite_attrproperty_w('w_object', W_UnicodeDecodeError),
    start  = readwrite_attrproperty_w('w_start', W_UnicodeDecodeError),
    end    = readwrite_attrproperty_w('w_end', W_UnicodeDecodeError),
    reason = readwrite_attrproperty_w('w_reason', W_UnicodeDecodeError),
)

W_TypeError = _new_exception('TypeError', W_StandardError,
                             """Inappropriate argument type.""")

W_IndexError = _new_exception('IndexError', W_LookupError,
                              """Sequence index out of range.""")

W_RuntimeWarning = _new_exception('RuntimeWarning', W_Warning,
                """Base class for warnings about dubious runtime behavior.""")

W_KeyboardInterrupt = _new_exception('KeyboardInterrupt', W_BaseException,
                                     """Program interrupted by user.""")

W_UserWarning = _new_exception('UserWarning', W_Warning,
                       """Base class for warnings generated by user code.""")

W_SyntaxWarning = _new_exception('SyntaxWarning', W_Warning,
                         """Base class for warnings about dubious syntax.""")

W_UnicodeWarning = _new_exception('UnicodeWarning', W_Warning,
            """Base class for warnings about Unicode related problems, mostly
related to conversion problems.""")

W_ImportWarning = _new_exception('ImportWarning', W_Warning,
    """Base class for warnings about probable mistakes in module imports""")

W_MemoryError = _new_exception('MemoryError', W_StandardError,
                               """Out of memory.""")

W_UnboundLocalError = _new_exception('UnboundLocalError', W_NameError,
                        """Local name referenced but not bound to a value.""")

W_NotImplementedError = _new_exception('NotImplementedError', W_RuntimeError,
                        """Method or function hasn't been implemented yet.""")

W_AttributeError = _new_exception('AttributeError', W_StandardError,
                                  """Attribute not found.""")

W_OverflowError = _new_exception('OverflowError', W_ArithmeticError,
                                 """Result too large to be represented.""")

class W_UnicodeEncodeError(W_UnicodeError):
    """Unicode encoding error."""
    w_encoding = None
    w_object = None
    w_start = None
    w_end = None
    w_reason = None

    def descr_init(self, space, w_encoding, w_object, w_start, w_end, w_reason):
        # typechecking
        space.realstr_w(w_encoding)
        space.realunicode_w(w_object)
        space.int_w(w_start)
        space.int_w(w_end)
        space.realstr_w(w_reason)
        # assign attributes
        self.w_encoding = w_encoding
        self.w_object = w_object
        self.w_start = w_start
        self.w_end = w_end
        self.w_reason = w_reason
        W_BaseException.descr_init(self, space, [w_encoding, w_object,
                                                 w_start, w_end, w_reason])

    def descr_str(self, space):
        return space.appexec([self], r"""(self):
            if self.end == self.start + 1:
                badchar = ord(self.object[self.start])
                if badchar <= 0xff:
                    return "'%s' codec can't encode character u'\\x%02x' in position %d: %s"%(
                        self.encoding, badchar, self.start, self.reason)
                if badchar <= 0xffff:
                    return "'%s' codec can't encode character u'\\u%04x' in position %d: %s"%(
                        self.encoding, badchar, self.start, self.reason)
                return "'%s' codec can't encode character u'\\U%08x' in position %d: %s"%(
                    self.encoding, badchar, self.start, self.reason)
            return "'%s' codec can't encode characters in position %d-%d: %s" % (
                self.encoding, self.start, self.end - 1, self.reason)
        """)

W_UnicodeEncodeError.typedef = TypeDef(
    'UnicodeEncodeError',
    W_UnicodeError.typedef,
    __doc__ = W_UnicodeEncodeError.__doc__,
    __module__ = 'exceptions',
    __new__ = _new(W_UnicodeEncodeError),
    __init__ = interp2app(W_UnicodeEncodeError.descr_init),
    __str__ = interp2app(W_UnicodeEncodeError.descr_str),
    encoding = readwrite_attrproperty_w('w_encoding', W_UnicodeEncodeError),
    object = readwrite_attrproperty_w('w_object', W_UnicodeEncodeError),
    start  = readwrite_attrproperty_w('w_start', W_UnicodeEncodeError),
    end    = readwrite_attrproperty_w('w_end', W_UnicodeEncodeError),
    reason = readwrite_attrproperty_w('w_reason', W_UnicodeEncodeError),
)
