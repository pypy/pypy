"""
General classes for bytecode compilers.
Compiler instances are stored into 'space.getexecutioncontext().compiler'.
"""

import sys
from codeop import PyCF_DONT_IMPLY_DEDENT
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

        if space.eq_w(err1.w_value, err2.w_value):
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

        from pyparser.pythonparse import make_pyparser
        PyCodeCompiler.__init__(self, space)
        self.grammar_version = override_version or space.config.objspace.pyversion
        self.parser = make_pyparser(self.grammar_version)
        self.additional_rules = {}
        if self.grammar_version >= '2.5':
            self.futureFlags = future.futureFlags_2_5
        else:
            self.futureFlags = future.futureFlags_2_4
        self.compiler_flags = self.futureFlags.allowed_flags

    def compile(self, source, filename, mode, flags):
        from pypy.interpreter.pyparser.error import SyntaxError
        from pypy.interpreter import astcompiler
        from pypy.interpreter.astcompiler.pycodegen import ModuleCodeGenerator
        from pypy.interpreter.astcompiler.pycodegen import InteractiveCodeGenerator
        from pypy.interpreter.astcompiler.pycodegen import ExpressionCodeGenerator
        from pypy.interpreter.astcompiler.ast import Node
        from pypy.interpreter.astcompiler import opt
        from pyparser.astbuilder import AstBuilder
        from pypy.interpreter.pycode import PyCode
        from pypy.interpreter.function import Function

        from pypy.interpreter.pyparser.future import getFutures

##         flags |= stdlib___future__.generators.compiler_flag   # always on (2.2 compat)
        space = self.space
        space.timer.start("PythonAST compile")
        try:
            builder = AstBuilder(self.parser, self.grammar_version, space=space)
            for rulename, buildfunc in self.additional_rules.iteritems():
                assert isinstance(buildfunc, Function)
                builder.user_build_rules[rulename] = buildfunc
            flags |= getFutures(self.futureFlags, source)
            self.parser.parse_source(source, mode, builder, flags)
            ast_tree = builder.rule_stack[-1]
            encoding = builder.source_encoding
        except SyntaxError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space, filename))

        ast_tree = opt.optimize_ast_tree(space, ast_tree)

        if not space.is_w(self.w_compile_hook, space.w_None):
            try:
                w_ast_tree = space.call_function(self.w_compile_hook,
                                                 space.wrap(ast_tree),
                                                 space.wrap(encoding),
                                                 space.wrap(filename))
                ast_tree = space.interp_w(Node, w_ast_tree)
            except OperationError:
                self.w_compile_hook = space.w_None
                raise
        try:
            astcompiler.misc.set_filename(filename, ast_tree)
            flag_names = self.futureFlags.get_flag_names(space, flags)
            if mode == 'exec':
                codegenerator = ModuleCodeGenerator(space, ast_tree, flag_names)
            elif mode == 'single':
                codegenerator = InteractiveCodeGenerator(space, ast_tree, flag_names)
            else: # mode == 'eval':
                codegenerator = ExpressionCodeGenerator(space, ast_tree, flag_names)
            c = codegenerator.getCode()
        except SyntaxError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space, filename))
        except (ValueError, TypeError), e:
            raise OperationError(space.w_SystemError, space.wrap(str(e)))
        assert isinstance(c, PyCode)
        space.timer.stop("PythonAST compile")
        return c

    # interface for pypy.module.recparser
    def get_parser(self):
        return self.parser

    def source2ast(self, source, mode='exec'):
        from pypy.interpreter.pyparser.astbuilder import AstBuilder
        builder = AstBuilder(self.parser, self.grammar_version,
                             space=self.space)
        self.parser.parse_source(source, mode, builder)
        return builder.rule_stack[-1]


def install_compiler_hook(space, w_callable):
#       if not space.get( w_callable ):
#           raise OperationError( space.w_TypeError( space.wrap( "must have a callable" ) )
    space.default_compiler.w_compile_hook = w_callable

def insert_grammar_rule(space, w_rule, w_buildfuncs):
    """inserts new grammar rules to the default compiler"""
    from pypy.interpreter import function
    rule = space.str_w(w_rule)
    #buildfuncs_w = w_buildfuncs.content
    buildfuncs = {}
    #for w_name, w_func in buildfuncs_w.iteritems():
    #    buildfuncs[space.str_w(w_name)] = space.unwrap(w_func)
    w_iter = space.iter(w_buildfuncs)
    while 1:
        try:
            w_key = space.next(w_iter)
            w_func = space.getitem(w_buildfuncs, w_key)
            buildfuncs[space.str_w(w_key)] = space.interp_w(function.Function, w_func)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
    space.default_compiler.additional_rules = buildfuncs
    space.default_compiler.parser.insert_rule(rule)

# XXX cyclic import
#from pypy.interpreter.baseobjspace import ObjSpace
#insert_grammar_rule.unwrap_spec = [ObjSpace, str, dict]
