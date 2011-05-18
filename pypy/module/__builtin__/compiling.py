"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.interpreter.astcompiler import consts, ast
from pypy.interpreter.gateway import NoneNotWrapped, unwrap_spec

@unwrap_spec(filename=str, mode=str, flags=int, dont_inherit=int)
def compile(space, w_source, filename, mode, flags=0, dont_inherit=0):
    """Compile the source string (a Python module, statement or expression)
into a code object that can be executed by the exec statement or eval().
The filename will be used for run-time error messages.
The mode must be 'exec' to compile a module, 'single' to compile a
single (interactive) statement, or 'eval' to compile an expression.
The flags argument, if present, controls which future statements influence
the compilation of the code.
The dont_inherit argument, if non-zero, stops the compilation inheriting
the effects of any future statements in effect in the code calling
compile; if absent or zero these statements do influence the compilation,
in addition to any features explicitly specified.
"""

    ast_node = None
    w_ast_type = space.gettypeobject(ast.AST.typedef)
    str_ = None
    if space.is_true(space.isinstance(w_source, w_ast_type)):
        ast_node = space.interp_w(ast.mod, w_source)
        ast_node.sync_app_attrs(space)
    elif space.is_true(space.isinstance(w_source, space.w_unicode)):
        w_utf_8_source = space.call_method(w_source, "encode",
                                           space.wrap("utf-8"))
        str_ = space.str_w(w_utf_8_source)
        # This flag tells the parser to reject any coding cookies it sees.
        flags |= consts.PyCF_SOURCE_IS_UTF8
    else:
        str_ = space.str_w(w_source)

    ec = space.getexecutioncontext()
    if flags & ~(ec.compiler.compiler_flags | consts.PyCF_ONLY_AST |
                 consts.PyCF_DONT_IMPLY_DEDENT | consts.PyCF_SOURCE_IS_UTF8):
        raise OperationError(space.w_ValueError,
                             space.wrap("compile() unrecognized flags"))
    if not dont_inherit:
        caller = ec.gettopframe_nohidden()
        if caller:
            flags |= ec.compiler.getcodeflags(caller.getcode())

    if mode not in ('exec', 'eval', 'single'):
        raise OperationError(space.w_ValueError,
                             space.wrap("compile() arg 3 must be 'exec' "
                                        "or 'eval' or 'single'"))

    if ast_node is None:
        if flags & consts.PyCF_ONLY_AST:
            mod = ec.compiler.compile_to_ast(str_, filename, mode, flags)
            return space.wrap(mod)
        else:
            code = ec.compiler.compile(str_, filename, mode, flags)
    else:
        code = ec.compiler.compile_ast(ast_node, filename, mode, flags)
    return space.wrap(code)


def eval(space, w_code, w_globals=None, w_locals=None):
    """Evaluate the source in the context of globals and locals.
The source may be a string representing a Python expression
or a code object as returned by compile().  The globals and locals
are dictionaries, defaulting to the current current globals and locals.
If only globals is given, locals defaults to it.
"""
    w = space.wrap

    if (space.is_true(space.isinstance(w_code, space.w_str)) or
        space.is_true(space.isinstance(w_code, space.w_unicode))):
        w_code = compile(space,
                         space.call_method(w_code, 'lstrip',
                                           space.wrap(' \t')),
                         "<string>", "eval")

    codeobj = space.interpclass_w(w_code)
    if not isinstance(codeobj, PyCode):
        raise OperationError(space.w_TypeError,
              w('eval() arg 1 must be a string or code object'))

    caller = space.getexecutioncontext().gettopframe_nohidden()
    if space.is_w(w_globals, space.w_None):
        if caller is None:
            w_globals = space.newdict()
            if space.is_w(w_locals, space.w_None):
                w_locals = w_globals
        else:
            w_globals = caller.w_globals
            if space.is_w(w_locals, space.w_None):
                w_locals = caller.getdictscope()
    elif space.is_w(w_locals, space.w_None):
        w_locals = w_globals

    try:
        space.getitem(w_globals, space.wrap('__builtins__'))
    except OperationError, e:
        if not e.match(space, space.w_KeyError):
            raise
        if caller is not None:
            w_builtin = space.builtin.pick_builtin(caller.w_globals)
            space.setitem(w_globals, space.wrap('__builtins__'), w_builtin)

    return codeobj.exec_code(space, w_globals, w_locals)
