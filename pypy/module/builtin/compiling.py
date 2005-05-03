"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.error import OperationError 
from pypy.interpreter.gateway import NoneNotWrapped
import __builtin__ as cpy_builtin
import warnings

def setup_warn_explicit(space): 
    """ NOT_RPYTHON 
   
    this is a hack until we have our own parsing/compiling 
    in place: we bridge certain warnings to the applevel 
    warnings module to let it decide what to do with
    a syntax warning ... 
    """ 
    def warn_explicit(message, category, filename, lineno,
                      module=None, registry=None):
        if hasattr(category, '__bases__') and \
           issubclass(category, SyntaxWarning): 
            assert isinstance(message, str) 
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
    old_warn_explicit = warnings.warn_explicit 
    warnings.warn_explicit = warn_explicit 
    return old_warn_explicit 

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
            caller = space.getexecutioncontext().framestack.top()
        except IndexError:
            caller = None
        else:
            from pypy.interpreter import pyframe
            if isinstance(caller, pyframe.PyFrame): 
                supplied_flags |= caller.get_compile_flags()
    try:
        old = setup_warn_explicit(space)
        try: 
            c = cpy_builtin.compile(str_, filename, startstr, supplied_flags, 1)
        finally: 
            warnings.warn_explicit = old 
            
    # It would be nice to propagate all exceptions to app level,
    # but here we only propagate the 'usual' ones, until we figure
    # out how to do it generically.
    except SyntaxError,e:
        raise OperationError(space.w_SyntaxError,space.wrap(e.args))
    except ValueError,e:
        raise OperationError(space.w_ValueError,space.wrap(str(e)))
    except TypeError,e:
        raise OperationError(space.w_TypeError,space.wrap(str(e)))
    return space.wrap(PyCode(space)._from_code(c))
#
compile.unwrap_spec = [ObjSpace,W_Root,str,str,int,int]


def eval(space, w_code, w_globals=NoneNotWrapped, w_locals=NoneNotWrapped):
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
                e_value_w = space.unpacktuple(e.w_value)
                e_loc_w = space.unpacktuple(e_value_w[1])
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

    return codeobj.exec_code(space, w_globals, w_locals)
