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

Exception
 |
 +-- SystemExit
 +-- StopIteration
 +-- StandardError
 |    |
 |    +-- KeyboardInterrupt
 |    +-- ImportError
 |    +-- EnvironmentError
 |    |    |
 |    |    +-- IOError
 |    |    +-- OSError
 |    |         |
 |    |         +-- WindowsError
 |    |         +-- VMSError
 |    |
 |    +-- EOFError
 |    +-- RuntimeError
 |    |    |
 |    |    +-- NotImplementedError
 |    |
 |    +-- NameError
 |    |    |
 |    |    +-- UnboundLocalError
 |    |
 |    +-- AttributeError
 |    +-- SyntaxError
 |    |    |
 |    |    +-- IndentationError
 |    |         |
 |    |         +-- TabError
 |    |
 |    +-- TypeError
 |    +-- AssertionError
 |    +-- LookupError
 |    |    |
 |    |    +-- IndexError
 |    |    +-- KeyError
 |    |
 |    +-- ArithmeticError
 |    |    |
 |    |    +-- OverflowError
 |    |    +-- ZeroDivisionError
 |    |    +-- FloatingPointError
 |    |
 |    +-- ValueError
 |    |    |
 |    |    +-- UnicodeError
 |    |        |
 |    |        +-- UnicodeEncodeError
 |    |        +-- UnicodeDecodeError
 |    |        +-- UnicodeTranslateError
 |    |
 |    +-- ReferenceError
 |    +-- SystemError
 |    +-- MemoryError
 |
 +---Warning
      |
      +-- UserWarning
      +-- DeprecationWarning
      +-- PendingDeprecationWarning
      +-- SyntaxWarning
      +-- OverflowWarning
      +-- RuntimeWarning
      +-- FutureWarning"""

class Exception:
    """Common base class for all exceptions."""

    def __getitem__(self, idx):
        return self.args[idx]

    def __init__(self, *args):
        self.args = args

    def __str__(self):
        args = self.args
        argc = len(args)
        if argc == 0:
            return ''
        elif argc == 1:
            return str(args[0])
        else:
            return str(args)

class StandardError(Exception):
    """Base class for all standard Python exceptions."""

class ValueError(StandardError):
    """Inappropriate argument value (of correct type)."""

class ImportError(StandardError):
    """Import can't find module, or can't find name in module."""

class RuntimeError(StandardError):
    """Unspecified run-time error."""

class UnicodeError(ValueError):
    """Unicode related error."""

class UnicodeTranslateError(UnicodeError):
    """Unicode translation error."""

    def __init__(self, *args):
        argc = len(args)
        self.args = args # modified: always assign args, no error check
        if argc == 4:
            if type(args[0]) == unicode:
                self.object = args[0]
            else:
                raise TypeError('argument 0 must be unicode, not %s'%type(args[0]))
            if type(args[1]) == int:
                self.start = args[1]
            else:
                raise TypeError('argument 1 must be int, not %s'%type(args[1]))
            if type(args[2]) == int:
                self.end = args[2]
            else:
                raise TypeError('argument 2 must be int, not %s'%type(args[2]))
            if type(args[3]) == str:
                self.reason = args[3]
            else:
                raise TypeError('argument 3 must be str, not %s'%type(args[3]))
        else:
            raise TypeError('function takes exactly 4 arguments (%d given)'%argc)

    def __str__(self):
        if self.end == self.start + 1:
            badchar = ord(self.object[self.start])
            if badchar <= 0xff:
                return "can't translate character u'\\x%02x' in position %d: %s" % (badchar, self.start, self.reason)
            if badchar <= 0xffff:
                return "can't translate character u'\\u%04x' in position %d: %s"%(badchar, self.start, self.reason)
            return "can't translate character u'\\U%08x' in position %d: %s"%(badchar, self.start, self.reason)
        return "can't translate characters in position %d-%d: %s" % (self.start, self.end - 1, self.reason)

class LookupError(StandardError):
    """Base class for lookup errors."""

class KeyError(LookupError):
    """Mapping key not found."""

    def __str__(self):
        args = self.args
        argc = len(args)
        if argc == 0:
            return ''
        elif argc == 1:
            return repr(args[0])
        else:
            return str(args)

class StopIteration(Exception):
    """Signal the end from iterator.next()."""

class Warning(Exception):
    """Base class for warning categories."""

class PendingDeprecationWarning(Warning):
    """Base class for warnings about features which will be deprecated in the future."""

class EnvironmentError(StandardError):
    """Base class for I/O related errors."""

    def __init__(self, *args):
        argc = len(args)
        self.args = args
        self.errno = None
        self.strerror = None
        self.filename = None
        if 2 <= argc <= 3:
            self.errno = args[0]
            self.strerror = args[1]
        if argc == 3:
            self.filename = args[2]
            self.args = (args[0], args[1])

    def __str__(self): 
        if self.filename is not None: 
            return  "[Errno %s] %s: %s" % (self.errno, 
                                           self.strerror,   
                                           self.filename)
        if self.errno and self.strerror: 
            return "[Errno %s] %s" % (self.errno, self.strerror)
        return StandardError.__str__(self) 
    

class OSError(EnvironmentError):
    """OS system call failed."""

try:
    WindowsError
    class WindowsError(OSError):
        """MS-Windows OS system call failed."""
except NameError:pass

class DeprecationWarning(Warning):
    """Base class for warnings about deprecated features."""

class ArithmeticError(StandardError):
    """Base class for arithmetic errors."""

class FloatingPointError(ArithmeticError):
    """Floating point operation failed."""

class ReferenceError(StandardError):
    """Weak ref proxy used after referent went away."""

class NameError(StandardError):
    """Name not found globally."""

class OverflowWarning(Warning):
    """Base class for warnings about numeric overflow.  Won't exist in Python 2.5."""

class IOError(EnvironmentError):
    """I/O operation failed."""

class SyntaxError(StandardError):
    """Invalid syntax."""
    filename = None
    lineno = None
    msg = ''
    offset = None
    print_file_and_line = None
    text = None

    def __init__(self, *args):
        argc = len(args)
        self.args = args
        if argc >= 1:
            self.msg = args[0]
        if argc == 2:
            if args[1][0] is None or type(args[1][0]) == str:
                self.filename = args[1][0]
            else:
                raise TypeError('argument 1 must be str, not %s'%type(args[1][0]))
            if args[1][1] is None or type(args[1][1]) == int:
                self.lineno = args[1][1]
            else:
                raise TypeError('argument 2 must be str, not %s'%type(args[1][1]))
            if args[1][2] is None or type(args[1][2]) == int:
                self.offset = args[1][2]
            else:
                raise TypeError('argument 3 must be str, not %s'%type(args[1][2]))
            if args[1][3] is None or type(args[1][3]) == str:
                self.text = args[1][3]
            else:
                raise TypeError('argument 4 must be str, not %s'%type(args[1][3]))

    def __str__(self):
        if type(self.msg) is not str:
            return self.msg
    
        buffer = self.msg
        have_filename = type(self.filename) is str
        have_lineno = type(self.lineno) is int
        if have_filename or have_lineno:
            import os
            fname = os.path.basename(self.filename or "???")
            if have_filename and have_lineno:
                buffer = "%s (%s, line %ld)" % (self.msg, fname, self.lineno)
            elif have_filename:
                buffer ="%s (%s)" % (self.msg, fname)
            elif have_lineno:
                buffer = "%s (line %ld)" % (self.msg, self.lineno)
        return buffer
    

class FutureWarning(Warning):
    """Base class for warnings about constructs that will change semantically in the future."""

class SystemExit(Exception):
    """Request to exit from the interpreter."""

    def __init__(self, *args):
        argc = len(args)
        if argc == 0:
            self.code = None
        self.args = args
        if argc == 1:
            self.code = args[0]
        if argc >= 2:
            if type(args) == tuple:
                self.code = args
            else:
                raise TypeError('argument 0 must be tuple, not %s'%type(args))

class EOFError(StandardError):
    """Read beyond end of file."""

class IndentationError(SyntaxError):
    """Improper indentation."""

class TabError(IndentationError):
    """Improper mixture of spaces and tabs."""

class ZeroDivisionError(ArithmeticError):
    """Second argument to a division or modulo operation was zero."""

class SystemError(StandardError):
    """Internal error in the Python interpreter.

Please report this to the Python maintainer, along with the traceback,
the Python version, and the hardware/OS platform and version."""

class AssertionError(StandardError):
    """Assertion failed."""

class UnicodeDecodeError(UnicodeError):
    """Unicode decoding error."""

    def __init__(self, *args):
        argc = len(args)
        self.args = args # modified: always assign args, no error check
        if argc == 5:
            if type(args[0]) == str:
                self.encoding = args[0]
            else:
                raise TypeError('argument 0 must be str, not %s'%type(args[0]))
            if type(args[1]) == str:
                self.object = args[1]
            else:
                raise TypeError('argument 1 must be str, not %s'%type(args[1]))
            if type(args[2]) == int:
                self.start = args[2]
            else:
                raise TypeError('argument 2 must be int, not %s'%type(args[2]))
            if type(args[3]) == int:
                self.end = args[3]
            else:
                raise TypeError('argument 3 must be int, not %s'%type(args[3]))
            if type(args[4]) == str:
                self.reason = args[4]
            else:
                raise TypeError('argument 4 must be str, not %s'%type(args[4]))
        else:
            raise TypeError('function takes exactly 5 arguments (%d given)'%argc)

    def __str__(self):
        if self.end == self.start + 1:
            return "%r codec can't decode byte 0x%02x in position %d: %s"%(self.encoding, 
                         ord(self.object[self.start]), self.start, self.reason)
        return "%r codec can't decode bytes in position %d-%d: %s" % (
            self.encoding, self.start, self.end - 1, self.reason)

class TypeError(StandardError):
    """Inappropriate argument type."""

class IndexError(LookupError):
    """Sequence index out of range."""

class RuntimeWarning(Warning):
    """Base class for warnings about dubious runtime behavior."""

class KeyboardInterrupt(StandardError):
    """Program interrupted by user."""

class UserWarning(Warning):
    """Base class for warnings generated by user code."""

class SyntaxWarning(Warning):
    """Base class for warnings about dubious syntax."""

class MemoryError(StandardError):
    """Out of memory."""

class UnboundLocalError(NameError):
    """Local name referenced but not bound to a value."""

class NotImplementedError(RuntimeError):
    """Method or function hasn't been implemented yet."""

class AttributeError(StandardError):
    """Attribute not found."""

class OverflowError(ArithmeticError):
    """Result too large to be represented."""

class UnicodeEncodeError(UnicodeError):
    """Unicode encoding error."""

    def __init__(self, *args):
        argc = len(args)
        self.args = args # modified: always assign args, no error check
        if argc == 5:
            if type(args[0]) == str:
                self.encoding = args[0]
            else:
                raise TypeError('argument 0 must be str, not %s'%type(args[0]))
            if type(args[1]) == unicode:
                self.object = args[1]
            else:
                raise TypeError('argument 1 must be unicode, not %s'%type(args[1]))
            if type(args[2]) == int:
                self.start = args[2]
            else:
                raise TypeError('argument 2 must be int, not %s'%type(args[2]))
            if type(args[3]) == int:
                self.end = args[3]
            else:
                raise TypeError('argument 3 must be int, not %s'%type(args[3]))
            if type(args[4]) == str:
                self.reason = args[4]
            else:
                raise TypeError('argument 4 must be str, not %s'%type(args[4]))
        else:
            raise TypeError('function takes exactly 5 arguments (%d given)'%argc)

    def __str__(self):
        if self.end == self.start + 1:
            badchar = ord(self.object[self.start])
            if badchar <= 0xff:
                return "%r codec can't encode character u'\\x%02x' in position %d: %s"%(self.encoding, 
                     badchar, self.start, self.reason)
            if badchar <= 0xffff:
                return "%r codec can't encode character u'\\u%04x' in position %d: %s"%(self.encoding, 
                     badchar, self.start, self.reason)
          
            return "%r codec can't encode character u'\\U%08x' in position %d: %s"%(self.encoding, 
                     badchar, self.start, self.reason)
        return "%r codec can't encode characters in position %d-%d: %s" % (
            self.encoding, self.start, self.end - 1, self.reason)



