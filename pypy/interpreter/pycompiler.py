"""
General classes for bytecode compilers.
Compiler instances are stored into 'space.getexecutioncontext().compiler'.
"""

import sys
from pypy.interpreter.astcompiler.consts import PyCF_DONT_IMPLY_DEDENT
from pypy.interpreter.error import OperationError

class AbstractCompiler(object):
    """Abstract base class for a bytecode compiler."""

    # The idea is to grow more methods here over the time,
    # e.g. to handle .pyc files in various ways if we have multiple compilers.

    def __init__(self, space):
        self.space = space
        self.w_compile_hook = space.w_None

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

        if space.eq_w(err1.get_w_value(space), err2.get_w_value(space)):
            raise     # twice the same error, re-raise

        return None   # two different errors, expect more


# ____________________________________________________________
# faked compiler

import warnings

## from pypy.tool import stdlib___future__
## compiler_flags = 0
## compiler_features = {}
## for fname in stdlib___future__.all_feature_names:
##     flag = getattr(stdlib___future__, fname).compiler_flag
##     compiler_flags |= flag
##     compiler_features[fname] = flag
## allowed_flags = compiler_flags | PyCF_DONT_IMPLY_DEDENT

## def get_flag_names(space, flags):
##     if flags & ~allowed_flags:
##         raise OperationError(space.w_ValueError,
##                              space.wrap("compile(): unrecognized flags"))
##     flag_names = []
##     for name, value in compiler_features.items():
##         if flags & value:
##             flag_names.append( name )
##     return flag_names


class PyCodeCompiler(AbstractCompiler):
    """Base class for compilers producing PyCode objects."""

    def getcodeflags(self, code):
        """Return the __future__ compiler flags that were used to compile
        the given code object."""
        from pypy.interpreter.pycode import PyCode
        if isinstance(code, PyCode):
            return code.co_flags & self.compiler_flags
        else:
            return 0

from pypy.interpreter.pyparser import future

class CPythonCompiler(PyCodeCompiler):
    """Faked implementation of a compiler, using the underlying compile()."""

    def __init__(self, space):
        self.space = space
        self.w_compile_hook = space.w_None
        if sys.version_info >= (2.5):
            self.compiler_flags = future.futureFlags_2_5.allowed_flags
        else:
            self.compiler_flags = future.futureFlags_2_4.allowed_flags

    def compile(self, source, filename, mode, flags):
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
        except UnicodeDecodeError, e:
            # TODO use a custom UnicodeError
            raise OperationError(space.w_UnicodeDecodeError, space.newtuple([
                                 space.wrap(e.encoding), space.wrap(e.object),
                                 space.wrap(e.start),
                                 space.wrap(e.end), space.wrap(e.reason)]))
        except ValueError, e:
            raise OperationError(space.w_ValueError, space.wrap(str(e)))
        except TypeError, e:
            raise OperationError(space.w_TypeError, space.wrap(str(e)))
        from pypy.interpreter.pycode import PyCode
        return PyCode._from_code(space, c)
    compile._annspecialcase_ = "override:cpy_compile"

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
                                          space.newdict())
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


class PythonAstCompiler(PyCodeCompiler):
    """Uses the stdlib's python implementation of compiler

    XXX: This class should override the baseclass implementation of
         compile_command() in order to optimize it, especially in case
         of incomplete inputs (e.g. we shouldn't re-compile from sracth
         the whole source after having only added a new '\n')
    """
    def __init__(self, space, override_version=None):

        from pypy.interpreter.pyparser.pyparse import PythonParser
        PyCodeCompiler.__init__(self, space)
        self.parser = PythonParser(space)
        self.additional_rules = {}
        self.future_flags = future.futureFlags_2_5
        self.compiler_flags = self.future_flags.allowed_flags

    def compile_ast(self, node, filename, mode, flags):
        from pypy.interpreter.pyparser.pyparse import CompileInfo
        from pypy.interpreter.astcompiler.misc import parse_future
        info = CompileInfo(filename, mode, flags, parse_future(node))
        return self._compile_ast(node, info)

    def _compile_ast(self, node, info):
        from pypy.interpreter.astcompiler import optimize
        from pypy.interpreter.astcompiler.codegen import compile_ast
        from pypy.interpreter.pyparser.error import SyntaxError
        space = self.space
        try:
            mod = optimize.optimize_ast(space, node, info)
            code = compile_ast(space, mod, info)
        except SyntaxError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space))
        return code

    def compile_to_ast(self, source, filename, mode, flags):
        from pypy.interpreter.pyparser.pyparse import CompileInfo
        info = CompileInfo(filename, mode, flags)
        return self._compile_to_ast(source, info)

    def _compile_to_ast(self, source, info):
        from pypy.interpreter.pyparser.future import get_futures
        from pypy.interpreter.pyparser.error import (SyntaxError,
                                                     IndentationError,
                                                     TokenIndentationError)
        from pypy.interpreter.astcompiler.astbuilder import ast_from_node
        space = self.space
        try:
            f_flags, future_info = get_futures(self.future_flags, source)
            info.last_future_import = future_info
            info.flags |= f_flags
            parse_tree = self.parser.parse_source(source, info)
            mod = ast_from_node(space, parse_tree, info)
        except IndentationError, e:
            raise OperationError(space.w_IndentationError,
                                 e.wrap_info(space))
        except TokenIndentationError, e:
            raise OperationError(space.w_IndentationError,
                                 e.wrap_info(space))
        except SyntaxError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space))
        return mod

    def compile(self, source, filename, mode, flags):
        from pypy.interpreter.pyparser.pyparse import CompileInfo
        info = CompileInfo(filename, mode, flags)
        mod = self._compile_to_ast(source, info)
        return self._compile_ast(mod, info)
