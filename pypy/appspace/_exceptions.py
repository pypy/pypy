class Exception:
    """Common base class for all exceptions."""

    # auto-generated code, please check carefully!
    def __getitem__(self, idx):
        return self.args[idx]

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        self.args = args

    # auto-generated code, please check carefully!
    def __str__(self):
        argc = len(self.args)
        if argc == 0:
            return ''
        elif argc == 1:
            return str(self.args[0])
        else:
            return str(self.args)

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

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        argc = len(args)
        self.args = args # modified: always assign args, no error check
        if argc == 4:
            self.object = args[0]
            self.start = args[1]
            self.end = args[2]
            self.reason = args[3]

    # auto-generated code, please check carefully!
    def __str__(self):
        # this is a bad hack, please supply an implementation
        res = ' '.join([
           'start=' + str(self.start),
           'reason=' + str(self.reason),
           'args=' + str(self.args),
           'end=' + str(self.end),
           'object=' + str(self.object),
        ])
        return res

class LookupError(StandardError):
    """Base class for lookup errors."""

class KeyError(LookupError):
    """Mapping key not found."""

    # auto-generated code, please check carefully!
    def __str__(self):
        argc = len(self.args)
        if argc == 0:
            return ''
        elif argc == 1:
            return repr(self.args[0])
        else:
            return str(self.args)

class Warning(Exception):
    """Base class for warning categories."""

class SyntaxWarning(Warning):
    """Base class for warnings about dubious syntax."""

class StopIteration(Exception):
    """Signal the end from iterator.next()."""

class PendingDeprecationWarning(Warning):
    """Base class for warnings about features which will be deprecated in the future."""

class EnvironmentError(StandardError):
    """Base class for I/O related errors."""

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        argc = len(args)
        self.args = args
        self.errno = None # default, hopefully
        self.strerror = None # default, hopefully
        self.filename = None # default, hopefully
        if 2 <= argc <= 3:
            self.errno = args[0]
            self.strerror = args[1]
        if argc == 3:
            self.filename = args[2]
            self.args = (args[0], args[1])

    # auto-generated code, please check carefully!
    def __str__(self):
        # this is a bad hack, please supply an implementation
        res = ' '.join([
           'errno=' + str(self.errno),
           'args=' + str(self.args),
           'strerror=' + str(self.strerror),
           'filename=' + str(self.filename),
        ])
        return res

class OSError(EnvironmentError):
    """OS system call failed."""

class DeprecationWarning(Warning):
    """Base class for warnings about deprecated features."""

class UnicodeEncodeError(UnicodeError):
    """Unicode encoding error."""

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        argc = len(args)
        self.args = args # modified: always assign args, no error check
        if argc == 5:
            self.encoding = args[0]
            self.object = args[1]
            self.start = args[2]
            self.end = args[3]
            self.reason = args[4]

    # auto-generated code, please check carefully!
    def __str__(self):
        # this is a bad hack, please supply an implementation
        res = ' '.join([
           'object=' + str(self.object),
           'end=' + str(self.end),
           'encoding=' + str(self.encoding),
           'args=' + str(self.args),
           'start=' + str(self.start),
           'reason=' + str(self.reason),
        ])
        return res

class ArithmeticError(StandardError):
    """Base class for arithmetic errors."""

class FloatingPointError(ArithmeticError):
    """Floating point operation failed."""

class ReferenceError(StandardError):
    """Weak ref proxy used after referent went away."""

class NameError(StandardError):
    """Name not found globally."""

class OverflowWarning(Warning):
    """Base class for warnings about numeric overflow."""

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

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        argc = len(args)
        self.args = args
        if argc >= 1:
            self.msg = args[0]
        if argc == 2:
            self.filename = args[1][0]
            self.lineno = args[1][1]
            self.offset = args[1][2]
            self.text = args[1][3]

    # auto-generated code, please check carefully!
    def __str__(self):
        # this is a bad hack, please supply an implementation
        res = ' '.join([
           'args=' + str(self.args),
        ])
        return res

class FutureWarning(Warning):
    """Base class for warnings about constructs that will change semantically in the future."""

class SystemExit(Exception):
    """Request to exit from the interpreter."""

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        argc = len(args)
        if argc == 0:
            self.code = None # default, hopefully
        self.args = args
        if argc == 1:
            self.code = args[0]
        if argc >= 2:
            self.code = args

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

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        argc = len(args)
        self.args = args # modified: always assign args, no error check
        if argc == 5:
            self.encoding = args[0]
            self.object = args[1]
            self.start = args[2]
            self.end = args[3]
            self.reason = args[4]

    # auto-generated code, please check carefully!
    def __str__(self):
        # this is a bad hack, please supply an implementation
        res = ' '.join([
           'object=' + str(self.object),
           'end=' + str(self.end),
           'encoding=' + str(self.encoding),
           'args=' + str(self.args),
           'start=' + str(self.start),
           'reason=' + str(self.reason),
        ])
        return res

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

class TaskletExit(SystemExit):
    """Request to exit from a tasklet."""

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

class WindowsError(OSError):
    """MS-Windows OS system call failed."""

