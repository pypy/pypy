"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.error import OperationError 
from pypy.interpreter.gateway import NoneNotWrapped
import __builtin__ as cpy_builtin

def compile(space, w_str_, filename, startstr,
            supplied_flags=0, dont_inherit=0):
    if space.is_true(space.isinstance(w_str_, space.w_unicode)):
        str_ = space.unwrap(w_str_) # xxx generic unwrap
    else:
        str_ = space.str_w(w_str_)
    #print (str_, filename, startstr, supplied_flags, dont_inherit)
    # XXX we additionally allow GENERATORS because compiling some builtins
    #     requires it. doesn't feel quite right to do that here.
    supplied_flags |= 4096 
    if not dont_inherit:
        try:
            frame = space.sys.call('_getframe') 
        except OperationError, e: 
            if not e.match(space, space.w_ValueError): 
                raise 
            pass
        else:
            supplied_flags |= frame.get_compile_flags()
    try:
        c = cpy_builtin.compile(str_, filename, startstr, supplied_flags, 1)
    # It would be nice to propagate all exceptions to app level,
    # but here we only propagate the 'usual' ones, until we figure
    # out how to do it generically.
    except SyntaxError,e:
        raise OperationError(space.w_SyntaxError,space.wrap(str(e)))
    except ValueError,e:
        raise OperationError(space.w_ValueError,space.wrap(str(e)))
    except TypeError,e:
        raise OperationError(space.w_TypeError,space.wrap(str(e)))
    return space.wrap(PyCode(space)._from_code(c))
#
compile.unwrap_spec = [ObjSpace,W_Root,str,str,int,int]


def eval(space, w_source, w_globals=NoneNotWrapped, w_locals=NoneNotWrapped):
    w = space.wrap

    if (space.is_true(space.isinstance(w_source, space.w_str)) or
        space.is_true(space.isinstance(w_source, space.w_unicode))):
        w_codeobj = compile(space,
                            space.call_method(w_source, 'lstrip',
                                              space.wrap(' \t')),
                            "<string>", "eval")
    elif isinstance(space.interpclass_w(w_source), PyCode):
        w_codeobj = w_source
    else:
        raise OperationError(space.w_TypeError,
              w('eval() arg 1 must be a string or code object'))

    try:
        caller = space.getexecutioncontext().framestack.top()
    except IndexError:
        caller = None

    if w_globals is None:
        if caller is None:
            w_globals = w_locals = space.newdict([])
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

    return space.interpclass_w(w_codeobj).exec_code(space, w_globals, w_locals)
