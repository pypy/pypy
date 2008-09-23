"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.error import OperationError 
from pypy.interpreter.gateway import NoneNotWrapped

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
    if space.is_true(space.isinstance(w_source, space.w_unicode)):
        # hack: encode the unicode string as UTF-8 and attach
        # a BOM at the start
        w_source = space.call_method(w_source, 'encode', space.wrap('utf-8'))
        str_ = space.str_w(w_source)
        str_ = '\xEF\xBB\xBF' + str_
    else:
        str_ = space.str_w(w_source)

    ec = space.getexecutioncontext()
    if not dont_inherit:
        try:
            caller = ec.framestack.top()
        except IndexError:
            pass
        else:
            flags |= ec.compiler.getcodeflags(caller.getcode())

    if mode not in ('exec', 'eval', 'single'):
        raise OperationError(space.w_ValueError,
                             space.wrap("compile() arg 3 must be 'exec' "
                                        "or 'eval' or 'single'"))

    code = ec.compiler.compile(str_, filename, mode, flags)
    return space.wrap(code)
#
compile.unwrap_spec = [ObjSpace,W_Root,str,str,int,int]


def eval(space, w_code, w_globals=NoneNotWrapped, w_locals=NoneNotWrapped):
    """Evaluate the source in the context of globals and locals.
The source may be a string representing a Python expression
or a code object as returned by compile().  The globals and locals
are dictionaries, defaulting to the current current globals and locals.
If only globals is given, locals defaults to it.
"""
    w = space.wrap

    if (space.is_true(space.isinstance(w_code, space.w_str)) or
        space.is_true(space.isinstance(w_code, space.w_unicode))):
        try:
            w_code = compile(space,
                             space.call_method(w_code, 'lstrip',
                                               space.wrap(' \t')),
                             "<string>", "eval")
        except OperationError, e:
            if e.match(space, space.w_SyntaxError):
                e_value_w = space.viewiterable(e.w_value)
                if len(e_value_w) == 2:
                    e_loc_w = space.viewiterable(e_value_w[1])
                    e.w_value = space.newtuple([e_value_w[0],
                                                space.newtuple([space.w_None]+
                                                               e_loc_w[1:])])
                raise e
            else:
                raise

    codeobj = space.interpclass_w(w_code)
    if not isinstance(codeobj, PyCode):
        raise OperationError(space.w_TypeError,
              w('eval() arg 1 must be a string or code object'))

    try:
        caller = space.getexecutioncontext().framestack.top()
    except IndexError:
        caller = None

    if w_globals is None or space.is_w(w_globals, space.w_None): 
        if caller is None:
            w_globals = w_locals = space.newdict()
        else:
            w_globals = caller.w_globals
            w_locals = caller.getdictscope()
    elif w_locals is None:
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
