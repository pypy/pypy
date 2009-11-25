import sys
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {}
    
    interpleveldefs = {
        'ArithmeticError' : 'interp_exceptions.W_ArithmeticError',
        'AssertionError' : 'interp_exceptions.W_AssertionError',
        'AttributeError' : 'interp_exceptions.W_AttributeError',
        'BaseException' : 'interp_exceptions.W_BaseException',
        'DeprecationWarning' : 'interp_exceptions.W_DeprecationWarning',
        'EOFError' : 'interp_exceptions.W_EOFError',
        'EnvironmentError' : 'interp_exceptions.W_EnvironmentError',
        'Exception' : 'interp_exceptions.W_Exception',
        'FloatingPointError' : 'interp_exceptions.W_FloatingPointError',
        'FutureWarning' : 'interp_exceptions.W_FutureWarning',
        'GeneratorExit' : 'interp_exceptions.W_GeneratorExit',
        'IOError' : 'interp_exceptions.W_IOError',
        'ImportError' : 'interp_exceptions.W_ImportError',
        'ImportWarning' : 'interp_exceptions.W_ImportWarning',
        'IndentationError' : 'interp_exceptions.W_IndentationError',
        'IndexError' : 'interp_exceptions.W_IndexError',
        'KeyError' : 'interp_exceptions.W_KeyError',
        'KeyboardInterrupt' : 'interp_exceptions.W_KeyboardInterrupt',
        'LookupError' : 'interp_exceptions.W_LookupError',
        'MemoryError' : 'interp_exceptions.W_MemoryError',
        'NameError' : 'interp_exceptions.W_NameError',
        'NotImplementedError' : 'interp_exceptions.W_NotImplementedError',
        'OSError' : 'interp_exceptions.W_OSError',
        'OverflowError' : 'interp_exceptions.W_OverflowError',
        'PendingDeprecationWarning' : 'interp_exceptions.W_PendingDeprecationWarning',
        'ReferenceError' : 'interp_exceptions.W_ReferenceError',
        'RuntimeError' : 'interp_exceptions.W_RuntimeError',
        'RuntimeWarning' : 'interp_exceptions.W_RuntimeWarning',
        'StandardError' : 'interp_exceptions.W_StandardError',
        'StopIteration' : 'interp_exceptions.W_StopIteration',
        'SyntaxError' : 'interp_exceptions.W_SyntaxError',
        'SyntaxWarning' : 'interp_exceptions.W_SyntaxWarning',
        'SystemExit' : 'interp_exceptions.W_SystemExit',
        'SystemError' : 'interp_exceptions.W_SystemError',
        'TabError' : 'interp_exceptions.W_TabError',
        'TypeError' : 'interp_exceptions.W_TypeError',
        'UnboundLocalError' : 'interp_exceptions.W_UnboundLocalError',
        'UnicodeDecodeError' : 'interp_exceptions.W_UnicodeDecodeError',
        'UnicodeEncodeError' : 'interp_exceptions.W_UnicodeEncodeError',
        'UnicodeError' : 'interp_exceptions.W_UnicodeError',
        'UnicodeTranslateError' : 'interp_exceptions.W_UnicodeTranslateError',
        'UnicodeWarning' : 'interp_exceptions.W_UnicodeWarning',
        'UserWarning' : 'interp_exceptions.W_UserWarning',
        'ValueError' : 'interp_exceptions.W_ValueError',
        'Warning' : 'interp_exceptions.W_Warning',
        'ZeroDivisionError' : 'interp_exceptions.W_ZeroDivisionError',
        }

    if sys.platform.startswith("win"):
        interpleveldefs['WindowsError'] = 'interp_exceptions.W_WindowsError'

    def setup_after_space_initialization(self):
        from pypy.objspace.std.transparent import register_proxyable
        from pypy.module.exceptions import interp_exceptions

        for name, exc in interp_exceptions.__dict__.items():
            if isinstance(exc, type) and issubclass(exc, interp_exceptions.W_BaseException):
                register_proxyable(self.space, exc)
