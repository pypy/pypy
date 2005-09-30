"""
General classes for bytecode compilers.
Compiler instances are stored into 'space.getexecutioncontext().compiler'.
"""
from codeop import PyCF_DONT_IMPLY_DEDENT
from pypy.interpreter.error import OperationError
from pypy.rpython.objectmodel import we_are_translated
import os

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
allowed_flags = compiler_flags | PyCF_DONT_IMPLY_DEDENT

def get_flag_names(space, flags):
    if flags & ~allowed_flags:
        raise OperationError(space.w_ValueError,
                             space.wrap("compile(): unrecognized flags"))
    flag_names = []
    for name, value in compiler_features.items():
        if flags & value:
            flag_names.append( name )
    return flag_names


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
        return PyCode(space)._from_code(c)
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
         of incomplete inputs (e.g. we shouldn't re-compile from scratch
         the whole source after having only added a new '\n')
    """
    def compile(self, source, filename, mode, flags):
        from pyparser.error import SyntaxError
        from pyparser.pythonutil import internal_pypy_parse
        flags |= __future__.generators.compiler_flag   # always on (2.2 compat)
        # XXX use 'flags'
        space = self.space
        try:
            parse_result = internal_pypy_parse(source, mode, True, flags)
        except SyntaxError, e:
            w_synerr = space.newtuple([space.wrap(e.msg),
                                       space.newtuple([space.wrap(filename),
                                                       space.wrap(e.lineno),
                                                       space.wrap(e.offset),
                                                       space.wrap("")
                                                       ])])
            raise OperationError(space.w_SyntaxError, w_synerr)            
        return self.compile_parse_result(parse_result, filename, mode, flags)

    def compile_parse_result(self, parse_result, filename, mode, flags):
        """NOT_RPYTHON"""
        from pyparser.pythonutil import parse_result_to_nested_tuples
        # the result of this conversion has no useful type in RPython
        tuples = parse_result_to_nested_tuples(parse_result, True)

        # __________
        # XXX this uses the non-annotatable stablecompiler at interp-level
        from pypy.interpreter import stablecompiler
        from pypy.interpreter.stablecompiler.pycodegen import ModuleCodeGenerator
        from pypy.interpreter.stablecompiler.pycodegen import InteractiveCodeGenerator
        from pypy.interpreter.stablecompiler.pycodegen import ExpressionCodeGenerator
        from pypy.interpreter.stablecompiler.transformer import Transformer
        space = self.space
        try:
            transformer = Transformer(filename)
            tree = transformer.compile_node(tuples)
            stablecompiler.misc.set_filename(filename, tree)
            flag_names = get_flag_names(space, flags)
            if mode == 'exec':
                codegenerator = ModuleCodeGenerator(tree, flag_names)
            elif mode == 'single':
                codegenerator = InteractiveCodeGenerator(tree, flag_names)
            else: # mode == 'eval':
                codegenerator = ExpressionCodeGenerator(tree, flag_names)
            c = codegenerator.getCode()
        except SyntaxError, e:
            w_synerr = space.newtuple([space.wrap(e.msg),
                                       space.newtuple([space.wrap(e.filename),
                                                       space.wrap(e.lineno),
                                                       space.wrap(e.offset),
                                                       space.wrap(e.text)])])
            raise OperationError(space.w_SyntaxError, w_synerr)
        except UnicodeDecodeError, e:
            raise OperationError(space.w_UnicodeDecodeError, space.newtuple([
                                 space.wrap(e.encoding), space.wrap(e.object), space.wrap(e.start),
                                 space.wrap(e.end), space.wrap(e.reason)]))
        except ValueError, e:
            if e.__class__ != ValueError:
                 extra_msg = "(Really go %s)" % e.__class__.__name__
            else:
                extra_msg = ""
            raise OperationError(space.w_ValueError, space.wrap(str(e)+extra_msg))
        except TypeError, e:
            raise OperationError(space.w_TypeError, space.wrap(str(e)))
        # __________ end of XXX above
        from pypy.interpreter.pycode import PyCode
        return PyCode(space)._from_code(c)
    compile_parse_result._annspecialcase_ = 'override:cpy_stablecompiler'


class PythonCompilerApp(PythonCompiler):
    """Temporary.  Calls the stablecompiler package at app-level."""

    def __init__(self, space):
        from pypy.interpreter.error import debug_print
        PythonCompiler.__init__(self, space)
        debug_print("importing the 'compiler' package at app-level...",
                    newline=False)
        self._load_compilers()
        debug_print(" done")

    def compile(self, source, filename, mode, flags):
        if (os.path.exists('fakecompletely') and
            os.path.exists('fakecompiler.py')):
            self.printmessage("faking all of compiler, cause"
                              " fakecompletely and fakecompiler.py"
                              " are in curdir")
            return self.fakecompile(source, filename, mode, flags)
        return PythonCompiler.compile(self, source, filename, mode, flags)

    def _load_compilers(self):
        # note: all these helpers, including the
        # remote compiler, must be initialized early,
        # or we get annotation errors. An alternative
        # would be to use applevel instances, instead.
        # But this code should anyway go away, soon.
        self.w_compileapp = self.space.appexec([], r'''():
            from _stablecompiler import apphook
            return apphook.applevelcompile
        ''')
        self.w_compilefake = self.space.appexec([], r'''():
            from _stablecompiler import apphook
            return apphook.fakeapplevelcompile
        ''')
        self.w_printmessage = self.space.appexec([], r'''():
            def printmessage(msg):
                print msg
            return printmessage
        ''')

    def printmessage(self, msg):
        space = self.space
        space.call_function(self.w_printmessage, space.wrap(msg))

    def _get_compiler(self, mode):
        import os
        if os.path.exists('fakecompiler.py') and mode != 'single':
            self.printmessage("faking compiler, because fakecompiler.py"
                              " is in the current dir")
            return self.w_compilefake
        else:
            return self.w_compileapp

    def compile_parse_result(self, parse_result, filename, mode, flags):
        space = self.space
        if space.options.translating and not we_are_translated():
            # to avoid to spend too much time in the app-level compiler
            # while translating PyPy, we can cheat here.  The annotator
            # doesn't see this because it thinks that we_are_translated()
            # returns True.
            return PythonCompiler.compile_parse_result(self, parse_result,
                                                       filename, mode, flags)
        source_encoding, stack_element = parse_result
        flag_names = get_flag_names(space, flags)
        w_flag_names = space.newlist( [ space.wrap(n) for n in flag_names ] )
        w_nested_tuples = stack_element.as_w_tuple(space, lineno=True)
        if source_encoding is not None:
            from pypy.interpreter.pyparser import pysymbol
            w_nested_tuples = space.newtuple([
                space.wrap(pysymbol.encoding_decl),
                w_nested_tuples,
                space.wrap(source_encoding)])

        w_code = space.call_function(self._get_compiler(mode),
                                     w_nested_tuples,
                                     space.wrap(filename),
                                     space.wrap(mode),
                                     w_flag_names)
        code = space.interpclass_w(w_code)
        from pypy.interpreter.pycode import PyCode
        if not isinstance(code, PyCode):
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("code object expected"))
        return code

    def fakecompile(self, source, filename, mode, flags):
        flags |= __future__.generators.compiler_flag   # always on (2.2 compat)
        flag_names = get_flag_names(self.space, flags)
        space = self.space

        w_flag_names = space.newlist( [ space.wrap(n) for n in flag_names ] )
        try:
            w_code = space.call_function(self.w_compilefake,
                                         space.wrap(source),
                                         space.wrap(filename),
                                         space.wrap(mode),
                                         w_flag_names)
        except OperationError, err:
            if not err.match(space, space.w_SyntaxError):
                raise
            # unfortunately, we need to unnormalize the wrapped SyntaxError,
            # or the w_value comparison will not work.
            w_inst = err.w_value
            w = space.wrap
            w_synerr = space.newtuple(
                [space.getattr(w_inst, w('msg')),
                 space.newtuple([space.getattr(w_inst, w('filename')),
                                 space.getattr(w_inst, w('lineno')),
                                 space.getattr(w_inst, w('offset')),
                                 space.getattr(w_inst, w('text'))])])
            raise OperationError(space.w_SyntaxError, w_synerr)
            
        code = space.interpclass_w(w_code)
        from pypy.interpreter.pycode import PyCode
        if not isinstance(code, PyCode):
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("code object expected"))
        return code


class PythonAstCompiler(CPythonCompiler):
    """Uses the stdlib's python implementation of compiler

    XXX: This class should override the baseclass implementation of
         compile_command() in order to optimize it, especially in case
         of incomplete inputs (e.g. we shouldn't re-compile from sracth
         the whole source after having only added a new '\n')
    """
    def compile(self, source, filename, mode, flags):
        from pyparser.error import SyntaxError
        from pypy.interpreter import astcompiler
        from pypy.interpreter.astcompiler.pycodegen import ModuleCodeGenerator
        from pypy.interpreter.astcompiler.pycodegen import InteractiveCodeGenerator
        from pypy.interpreter.astcompiler.pycodegen import ExpressionCodeGenerator
        from pyparser.pythonutil import AstBuilder, PYTHON_PARSER, TARGET_DICT 
        from pypy.interpreter.pycode import PyCode

        flags |= __future__.generators.compiler_flag   # always on (2.2 compat)
        space = self.space
        try:
            builder = AstBuilder(space=space)
            target_rule = TARGET_DICT[mode]
            PYTHON_PARSER.parse_source(source, target_rule, builder, flags)
            ast_tree = builder.rule_stack[-1]
            encoding = builder.source_encoding
        except SyntaxError, e:
            raise OperationError(space.w_SyntaxError,
                                 e.wrap_info(space, filename))

        try:
            astcompiler.misc.set_filename(filename, ast_tree)
            flag_names = get_flag_names(space, flags)
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
        except ValueError,e:
            raise OperationError(space.w_ValueError,space.wrap(str(e)))
        except TypeError,e:
            raise
            raise OperationError(space.w_TypeError,space.wrap(str(e)))
        assert isinstance(c,PyCode)
        return c
    #compile_parse_result._annspecialcase_ = 'override:cpy_stablecompiler'


class CPythonRemoteCompiler(AbstractCompiler):
    """Faked implementation of a compiler, using an external Python's compile()."""

    def __init__(self, space):
        AbstractCompiler.__init__(self, space)
        self.w_compilefake = self.space.appexec([], r'''():
            from _stablecompiler import apphook
            return apphook.fakeapplevelcompile
        ''')

    def compile(self, source, filename, mode, flags):
        flags |= __future__.generators.compiler_flag   # always on (2.2 compat)
        flag_names = get_flag_names(self.space, flags)
        space = self.space
        return None

        w_code = space.call_function(self.w_compilefake,
                                     space.wrap(source),
                                     space.wrap(filename),
                                     space.wrap(mode),
                                     space.wrap(flag_names))
        code = space.interpclass_w(w_code)
        return code

        try:
            w_code = space.call_function(self.w_compilefake,
                                         space.wrap(source),
                                         space.wrap(filename),
                                         space.wrap(mode),
                                         space.wrap(flag_names))
        except OperationError, err:
            if not err.match(space, space.w_SyntaxError):
                raise
            # unfortunately, we need to unnormalize the wrapped SyntaxError,
            # or the w_value comparison will not work.
            w_inst = err.w_value
            w = space.wrap
            w_synerr = space.newtuple(
                [space.getattr(w_inst, w('msg')),
                 space.newtuple([space.getattr(w_inst, w('filename')),
                                 space.getattr(w_inst, w('lineno')),
                                 space.getattr(w_inst, w('offset')),
                                 space.getattr(w_inst, w('text'))])])
            raise OperationError(space.w_SyntaxError, w_synerr)
            
        code = space.interpclass_w(w_code)
        from pypy.interpreter.pycode import PyCode
        if not isinstance(code, PyCode):
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("code object expected"))
        return code


class PyPyCompiler(CPythonCompiler):
    """Uses the PyPy implementation of Compiler

    XXX: WRITEME
    """
