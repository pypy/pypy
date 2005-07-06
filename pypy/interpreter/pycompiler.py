"""
General classes for bytecode compilers.
Compiler instances are stored into 'space.getexecutioncontext().compiler'.
"""
from codeop import PyCF_DONT_IMPLY_DEDENT
from pypy.interpreter.error import OperationError


class AbstractCompiler:
    """Abstract base class for a bytecode compiler."""

    # The idea is to grow more methods here over the time,
    # e.g. to handle .pyc files in various ways if we have multiple compilers.

    def __init__(self, space):
        self.space = space

    def compile(self, source, filename, mode, flags):
        """Compile and return an pypy.interpreter.eval.Code instance."""
        raise NotImplementedError

    def getcodeflags(self, code):
        """Return the __future__ compiler flags that were used to compile
        the given code object."""
        return 0

    def compile_command(self, source, filename, mode, flags):
        """Same as compile(), but tries to compile a possibly partial
        interactive input.  If more input is needed, it returns None.
        """
        # Hackish default implementation based on the stdlib 'codeop' module.
        # See comments over there.
        space = self.space
        flags |= PyCF_DONT_IMPLY_DEDENT
        # Check for source consisting of only blank lines and comments
        if mode != "eval":
            in_comment = False
            for c in source:
                if c in ' \t\f\v':   # spaces
                    pass
                elif c == '#':
                    in_comment = True
                elif c in '\n\r':
                    in_comment = False
                elif not in_comment:
                    break    # non-whitespace, non-comment character
            else:
                source = "pass"     # Replace it with a 'pass' statement

        try:
            code = self.compile(source, filename, mode, flags)
            return code   # success
        except OperationError, err:
            if not err.match(space, space.w_SyntaxError):
                raise

        try:
            self.compile(source + "\n", filename, mode, flags)
            return None   # expect more
        except OperationError, err1:
            if not err1.match(space, space.w_SyntaxError):
                raise

        try:
            self.compile(source + "\n\n", filename, mode, flags)
            raise     # uh? no error with \n\n.  re-raise the previous error
        except OperationError, err2:
            if not err2.match(space, space.w_SyntaxError):
                raise

        if space.eq_w(err1.w_value, err2.w_value):
            raise     # twice the same error, re-raise

        return None   # two different errors, expect more


# ____________________________________________________________
# faked compiler

import warnings
import __future__
compiler_flags = 0
compiler_features = {}
for fname in __future__.all_feature_names:
    flag = getattr(__future__, fname).compiler_flag
    compiler_flags |= flag
    compiler_features[fname] = flag


class CPythonCompiler(AbstractCompiler):
    """Faked implementation of a compiler, using the underlying compile()."""

    def compile(self, source, filename, mode, flags):
        flags |= __future__.generators.compiler_flag   # always on (2.2 compat)
        space = self.space
        try:
            old = self.setup_warn_explicit(warnings)
            try:
                c = compile(source, filename, mode, flags, True)
            finally:
                self.restore_warn_explicit(warnings, old)
        # It would be nice to propagate all exceptions to app level,
        # but here we only propagate the 'usual' ones, until we figure
        # out how to do it generically.
        except SyntaxError,e:
            w_synerr = space.newtuple([space.wrap(e.msg),
                                       space.newtuple([space.wrap(e.filename),
                                                       space.wrap(e.lineno),
                                                       space.wrap(e.offset),
                                                       space.wrap(e.text)])])
            raise OperationError(space.w_SyntaxError, w_synerr)
        except ValueError,e:
            raise OperationError(space.w_ValueError,space.wrap(str(e)))
        except TypeError,e:
            raise OperationError(space.w_TypeError,space.wrap(str(e)))
        from pypy.interpreter.pycode import PyCode
        return space.wrap(PyCode(space)._from_code(c))
    compile._annspecialcase_ = "override:cpy_compile"

    def getcodeflags(self, code):
        from pypy.interpreter.pycode import PyCode
        if isinstance(code, PyCode):
            return code.co_flags & compiler_flags
        else:
            return 0

    def _warn_explicit(self, message, category, filename, lineno,
                       module=None, registry=None):
        if hasattr(category, '__bases__') and \
           issubclass(category, SyntaxWarning): 
            assert isinstance(message, str)
            space = self.space
            w_mod = space.sys.getmodule('warnings')
            if w_mod is not None: 
                w_dict = w_mod.getdict() 
                w_reg = space.call_method(w_dict, 'setdefault', 
                                          space.wrap("__warningregistry__"),     
                                          space.newdict([]))
                try: 
                    space.call_method(w_mod, 'warn_explicit', 
                                      space.wrap(message), 
                                      space.w_SyntaxWarning, 
                                      space.wrap(filename), 
                                      space.wrap(lineno), 
                                      space.w_None, 
                                      space.w_None) 
                except OperationError, e: 
                    if e.match(space, space.w_SyntaxWarning): 
                        raise OperationError(
                                space.w_SyntaxError, 
                                space.wrap(message))
                    raise 

    def setup_warn_explicit(self, warnings):
        """
        this is a hack until we have our own parsing/compiling 
        in place: we bridge certain warnings to the applevel 
        warnings module to let it decide what to do with
        a syntax warning ... 
        """ 
        # there is a hack to make the flow space happy:
        # 'warnings' should not look like a Constant
        old_warn_explicit = warnings.warn_explicit 
        warnings.warn_explicit = self._warn_explicit
        return old_warn_explicit 

    def restore_warn_explicit(self, warnings, old_warn_explicit):
        warnings.warn_explicit = old_warn_explicit


########
class PythonCompiler(CPythonCompiler):
    """Uses the stdlib's python implementation of compiler

    XXX: This class should override the baseclass implementation of
         compile_command() in order to optimize it, especially in case
         of incomplete inputs (e.g. we shouldn't re-compile from sracth
         the whole source after having only added a new '\n')
    """
    def compile(self, source, filename, mode, flags):
        from pyparser.error import ParseError
        from pyparser.pythonutil import pypy_parse
        flags |= __future__.generators.compiler_flag   # always on (2.2 compat)
        # XXX use 'flags'
        space = self.space
        try:
            tuples = pypy_parse(source, mode, True, flags)
        except ParseError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space, filename))
        c = self.compile_tuples(tuples, filename, mode)
        from pypy.interpreter.pycode import PyCode
        return space.wrap(PyCode(space)._from_code(c))

    def compile_tuples(self, tuples, filename, mode):
        # __________
        # XXX this uses the non-annotatable stablecompiler at interp-level
        from pypy.interpreter import stablecompiler
        from pypy.interpreter.stablecompiler.pycodegen import ModuleCodeGenerator
        from pypy.interpreter.stablecompiler.pycodegen import InteractiveCodeGenerator
        from pypy.interpreter.stablecompiler.pycodegen import ExpressionCodeGenerator
        from pypy.interpreter.stablecompiler.transformer import Transformer
        space = self.space
        try:
            transformer = Transformer()
            tree = transformer.compile_node(tuples)
            stablecompiler.misc.set_filename(filename, tree)
            if mode == 'exec':
                codegenerator = ModuleCodeGenerator(tree)
            elif mode == 'single':
                codegenerator = InteractiveCodeGenerator(tree)
            else: # mode == 'eval':
                codegenerator = ExpressionCodeGenerator(tree)
            c = codegenerator.getCode()
        except SyntaxError, e:
            w_synerr = space.newtuple([space.wrap(e.msg),
                                       space.newtuple([space.wrap(e.filename),
                                                       space.wrap(e.lineno),
                                                       space.wrap(e.offset),
                                                       space.wrap(e.text)])])
            raise OperationError(space.w_SyntaxError, w_synerr)
        except ValueError,e:
            raise OperationError(space.w_ValueError,space.wrap(str(e)))
        except TypeError,e:
            raise OperationError(space.w_TypeError,space.wrap(str(e)))
        # __________ end of XXX above
        return c
    compile_tuples._annspecialcase_ = 'override:cpy_stablecompiler'


class PyPyCompiler(CPythonCompiler):
    """Uses the PyPy implementation of Compiler

    XXX: WRITEME
    """
