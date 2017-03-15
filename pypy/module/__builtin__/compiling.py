"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.astcompiler import consts, ast
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.argument import Arguments
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.function import Function

@unwrap_spec(filename='fsencode', mode='text', flags=int, dont_inherit=int,
             optimize=int)
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
    from pypy.interpreter.pyopcode import source_as_str
    ec = space.getexecutioncontext()
    if flags & ~(ec.compiler.compiler_flags | consts.PyCF_ONLY_AST |
                 consts.PyCF_DONT_IMPLY_DEDENT | consts.PyCF_SOURCE_IS_UTF8 |
                 consts.PyCF_ACCEPT_NULL_BYTES):
        raise oefmt(space.w_ValueError, "compile() unrecognized flags")

    if not dont_inherit:
        caller = ec.gettopframe_nohidden()
        if caller:
            flags |= ec.compiler.getcodeflags(caller.getcode())

    if mode not in ('exec', 'eval', 'single'):
        raise oefmt(space.w_ValueError,
                    "compile() arg 3 must be 'exec', 'eval' or 'single'")

    if space.isinstance_w(w_source, space.gettypeobject(ast.W_AST.typedef)):
        ast_node = ast.mod.from_object(space, w_source)
        ec.compiler.validate_ast(ast_node)
        return ec.compiler.compile_ast(ast_node, filename, mode, flags,
                                       optimize=optimize)

    flags |= consts.PyCF_SOURCE_IS_UTF8
    source, flags = source_as_str(space, w_source, 'compile',
                                  "string, bytes or AST", flags)

    if flags & consts.PyCF_ONLY_AST:
        node = ec.compiler.compile_to_ast(source, filename, mode, flags)
        return node.to_object(space)
    else:
        return ec.compiler.compile(source, filename, mode, flags,
                                   optimize=optimize)


def eval(space, w_prog, w_globals=None, w_locals=None):
    """Evaluate the source in the context of globals and locals.
The source may be a string representing a Python expression
or a code object as returned by compile().  The globals and locals
are dictionaries, defaulting to the current current globals and locals.
If only globals is given, locals defaults to it.
"""
    from pypy.interpreter.pyopcode import ensure_ns, source_as_str
    w_globals, w_locals = ensure_ns(space, w_globals, w_locals, 'eval')

    if space.isinstance_w(w_prog, space.gettypeobject(PyCode.typedef)):
        code = space.interp_w(PyCode, w_prog)
    else:
        source, flags = source_as_str(space, w_prog, 'eval',
                                      "string, bytes or code",
                                      consts.PyCF_SOURCE_IS_UTF8)
        ec = space.getexecutioncontext()
        code = ec.compiler.compile(source.lstrip(' \t'), "<string>", 'eval',
                                   flags)

    # XXX: skip adding of __builtins__ to w_globals. it requires a
    # costly gettopframe_nohidden() here and nobody seems to miss its
    # absence

    return code.exec_code(space, w_globals, w_locals)

def exec_(space, w_prog, w_globals=None, w_locals=None):
    frame = space.getexecutioncontext().gettopframe()
    frame.exec_(w_prog, w_globals, w_locals)

def build_class(space, w_func, w_name, __args__):
    if not isinstance(w_func, Function):
        raise oefmt(space.w_TypeError, "__build_class__: func must be a function")
    bases_w, kwds_w = __args__.unpack()
    w_bases = space.newtuple(bases_w)
    w_meta = kwds_w.pop('metaclass', None)
    if w_meta is not None:
        isclass = space.isinstance_w(w_meta, space.w_type)
    else:
        if bases_w:
            w_meta = space.type(bases_w[0])
        else:
            w_meta = space.w_type
        isclass = True
    if isclass:
        # w_meta is really a class, so check for a more derived
        # metaclass, or possible metaclass conflicts
        from pypy.objspace.std.typeobject import _calculate_metaclass
        w_meta = _calculate_metaclass(space, w_meta, bases_w)

    try:
        w_prep = space.getattr(w_meta, space.newtext("__prepare__"))
    except OperationError as e:
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
    code = w_func.getcode()
    frame = space.createframe(code, w_func.w_func_globals, w_func)
    frame.setdictscope(w_namespace)
    w_cell = frame.run()
    keywords = kwds_w.keys()
    args = Arguments(space,
                     args_w=[w_name, w_bases, w_namespace],
                     keywords=keywords,
                     keywords_w=kwds_w.values())
    w_class = space.call_args(w_meta, args)
    if isinstance(w_cell, Cell):
        w_cell.set(w_class)
    return w_class
