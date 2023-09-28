import sys
from rpython.rlib.rarithmetic import widen
from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.error import oefmt
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.module.__builtin__ import compiling
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import llapi

@API.func("HPy HPy_EvalCode(HPyContext *ctx, HPy code, HPy globals, HPy locals)")
def HPy_EvalCode(space, handles, ctx, h_code, h_globals, h_locals):
    w_code = handles.deref(h_code)
    if not h_globals:
        w_globals = space.w_None
    else:
        w_globals = handles.deref(h_globals)
    if not h_locals:
        w_locals = space.w_None
    else:
        w_locals = handles.deref(h_locals)
    w_ret = compiling.eval(space, w_code, w_globals, w_locals)
    return handles.new(w_ret)

@API.func("HPy HPy_Compile_s(HPyContext *ctx, const char *utf8_source, const char *utf8_filename, int kind)")
def HPy_Compile_s(space, handles, ctx, source, filename, kind):
    """
    Evaluating Python statements/expressions */

   Parse and compile the Python source code.
  
   :param ctx:
       The execution context.
   :param utf8_source:
       Python source code given as UTF-8 encoded C string (must not be ``NULL``).
   :param utf8_filename:
       The filename (UTF-8 encoded C string) to use for construction of the code
       object. It may appear in tracebacks or in ``SyntaxError`` exception
       messages.
   :param kind:
       The source kind which tells the parser if a single expression, statement,
       or a whole file should be parsed (see enum :c:enum:`HPy_SourceKind`).
  
   :returns:
       A Python code object resulting from the parsed and compiled Python source
       code or ``HPy_NULL`` in case of errors.
    """
    Kinds = llapi.cts.gettype("HPy_SourceKind")
    w_source = API.ccharp2text(space, source)
    filename = rffi.constcharp2str(filename)
    kind =  widen(kind)
    if kind == Kinds.HPy_SourceKind_Expr:
        mode = "eval"
    elif kind == Kinds.HPy_SourceKind_File:
        mode = "exec"
    elif kind == Kinds.HPy_SourceKind_Single:
        mode = "single"
    else:
        raise oefmt(space.w_SystemError, "invalid source kind")
    flags = 0
    feature_version = -1
    w_result = compiling.compile(space, w_source,
                    filename, mode, flags,
                    _feature_version=feature_version)
    return handles.new(w_result)
