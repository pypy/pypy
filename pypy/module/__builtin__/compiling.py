"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.interpreter.astcompiler import consts, ast
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.argument import Arguments
from pypy.interpreter.nestedscope import Cell

@unwrap_spec(filename=str, mode=str, flags=int, dont_inherit=int, optimize=int)
def compile(space, w_source, filename, mode, flags=0, dont_inherit=0,
            optimize=0):
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

    ec = space.getexecutioncontext()
    if flags & ~(ec.compiler.compiler_flags | consts.PyCF_ONLY_AST |
                 consts.PyCF_DONT_IMPLY_DEDENT | consts.PyCF_SOURCE_IS_UTF8):
        raise OperationError(space.w_ValueError,
                             space.wrap("compile() unrecognized flags"))

    flags |= consts.PyCF_SOURCE_IS_UTF8
    ast_node = None
    w_ast_type = space.gettypeobject(ast.AST.typedef)
    source_str = None
    if space.is_true(space.isinstance(w_source, w_ast_type)):
        ast_node = space.interp_w(ast.mod, w_source)
        ast_node.sync_app_attrs(space)
    elif space.isinstance_w(w_source, space.w_unicode):
        w_utf_8_source = space.call_method(w_source, "encode",
                                           space.wrap("utf-8"))
        source_str = space.bytes0_w(w_utf_8_source)
        flags |= consts.PyCF_IGNORE_COOKIE
    elif space.isinstance_w(w_source, space.w_bytes):
        source_str = space.bytes0_w(w_source)
    else:
        msg = space.wrap(
            "compile() arg 1 must be a string, bytes, AST or code object")
        raise OperationError(space.w_TypeError, msg)

    if not dont_inherit:
        caller = ec.gettopframe_nohidden()
        if caller:
            flags |= ec.compiler.getcodeflags(caller.getcode())

    if mode not in ('exec', 'eval', 'single'):
        raise OperationError(space.w_ValueError,
                             space.wrap("compile() arg 3 must be 'exec' "
                                        "or 'eval' or 'single'"))
    # XXX optimize is not used

    if ast_node is None:
        if flags & consts.PyCF_ONLY_AST:
            mod = ec.compiler.compile_to_ast(source_str, filename, mode, flags)
            return space.wrap(mod)
        else:
            code = ec.compiler.compile(source_str, filename, mode, flags)
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

    is_unicode = space.is_true(space.isinstance(w_code, space.w_unicode))
    if (is_unicode or space.is_true(space.isinstance(w_code, space.w_bytes))):
        w_strip = w(u' \t') if is_unicode else space.wrapbytes(' \t')
        w_code = compile(space, space.call_method(w_code, 'lstrip', w_strip),
                         "<string>", "eval")

    codeobj = space.interpclass_w(w_code)
    if not isinstance(codeobj, PyCode):
        raise OperationError(space.w_TypeError,
              w('eval() arg 1 must be a string or code object'))

    if space.is_none(w_globals):
        caller = space.getexecutioncontext().gettopframe_nohidden()
        if caller is None:
            w_globals = space.newdict()
            if space.is_none(w_locals):
                w_locals = w_globals
        else:
            w_globals = caller.w_globals
            if space.is_none(w_locals):
                w_locals = caller.getdictscope()
    elif space.is_none(w_locals):
        w_locals = w_globals

    # xxx removed: adding '__builtins__' to the w_globals dict, if there
    # is none.  This logic was removed as costly (it requires to get at
    # the gettopframe_nohidden()).  I bet no test fails, and it's a really
    # obscure case.

    return codeobj.exec_code(space, w_globals, w_locals)

def exec_(space, w_prog, w_globals=None, w_locals=None):
    if w_globals is None:
        w_globals = space.w_None
    if w_locals is None:
        w_locals = space.w_None
    ec = space.getexecutioncontext()
    frame = ec.gettopframe_nohidden()
    frame.exec_(w_prog, w_globals, w_locals)

def build_class(space, w_func, w_name, __args__):
    bases_w, kwds_w = __args__.unpack()
    w_bases = space.newtuple(bases_w)
    w_meta = kwds_w.pop('metaclass', None)
    if w_meta is None:
        if bases_w:
            w_meta = space.type(bases_w[0])
        else:
            w_meta = space.w_type
    
    try:
        w_prep = space.getattr(w_meta, space.wrap("__prepare__"))
    except OperationError, e:
        if not e.match(space, space.w_AttributeError):
            raise
        w_namespace = space.newdict()
    else:
        keywords = kwds_w.keys()
        args = Arguments(space, 
                         args_w=[w_name, w_bases],
                         keywords=keywords,
                         keywords_w=kwds_w.values())
        w_namespace = space.call_args(w_prep, args)
    w_cell = space.call_function(w_func, w_namespace)
    keywords = kwds_w.keys()
    args = Arguments(space,
                     args_w=[w_name, w_bases, w_namespace],
                     keywords=keywords,
                     keywords_w=kwds_w.values())
    w_class = space.call_args(w_meta, args)
    if isinstance(w_cell, Cell):
        w_cell.set(w_class)
    return w_class
