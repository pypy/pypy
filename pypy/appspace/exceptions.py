class Exception:
    """Common base class for all exceptions."""

    # auto-generated code, please check carefully!
    def __getitem__(self, idx):
        return self.args[idx]

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        pass

    # auto-generated code, please check carefully!
    # please implement Exception.__str__
    # instantiation of Exception works with 13119 solutions

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
        pass

    # auto-generated code, please check carefully!
    # please implement UnicodeTranslateError.__str__
    # instantiation of UnicodeTranslateError works with 1 solutions

class LookupError(StandardError):
    """Base class for lookup errors."""

class KeyError(LookupError):
    """Mapping key not found."""

    # auto-generated code, please check carefully!
    # please implement KeyError.__str__
    # instantiation of KeyError works with 13119 solutions

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
        pass

    # auto-generated code, please check carefully!
    # please implement EnvironmentError.__str__
    # instantiation of EnvironmentError works with 13119 solutions

class OSError(EnvironmentError):
    """OS system call failed."""

class DeprecationWarning(Warning):
    """Base class for warnings about deprecated features."""

class UnicodeEncodeError(UnicodeError):
    """Unicode encoding error."""

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        pass

    # auto-generated code, please check carefully!
    # please implement UnicodeEncodeError.__str__
    # instantiation of UnicodeEncodeError works with 1 solutions

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
        pass

    # auto-generated code, please check carefully!
    # please implement SyntaxError.__str__
    # instantiation of SyntaxError works with 13116 solutions

class FutureWarning(Warning):
    """Base class for warnings about constructs that will change semantically in the future."""

class SystemExit(Exception):
    """Request to exit from the interpreter."""

    # auto-generated code, please check carefully!
    def __init__(self, *args):
        pass

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
        pass

    # auto-generated code, please check carefully!
    # please implement UnicodeDecodeError.__str__
    # instantiation of UnicodeDecodeError works with 1 solutions

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

