import py
from prolog.interpreter.parsing import parse_file, TermBuilder
from prolog.interpreter import helper, term, error
from prolog.interpreter.signature import Signature
from prolog.interpreter.arithmetic import eval_arithmetic

from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import jit

import inspect

Signature.register_extr_attr("builtin")

jit_modules = ["control"]

class Builtin(object):
    _immutable_ = True
    def __init__(self, function, name, numargs, signature):
        self.function = function
        self.name = name
        self.numargs = numargs
        self.signature = signature

    def call(self, engine, query, module, scont, fcont, heap):
        return self.function(engine, query, module, scont, fcont, heap)
        
    def _freeze_(self):
        return True

def expose_builtin(*args, **kwargs):
    def really_expose(func):
        return make_wrapper(func, *args, **kwargs)
    return really_expose

def make_wrapper(func, name, unwrap_spec=[], handles_continuation=False,
                   translatable=True, needs_module=False):
    if isinstance(name, list):
        expose_as = name
        name = name[0]
    else:
        expose_as = [name]
    if not name.isalnum():
        name = func.func_name
    orig_funcargs = inspect.getargs(func.func_code)[0]
    funcname = "wrap_%s_%s" % (name, len(unwrap_spec))
    code = ["def %s(engine, query, module, scont, fcont, heap):" % (funcname, )]
    if not translatable:
        code.append("    if we_are_translated():")
        code.append("        raise error.UncatchableError('%s does not work in translated version')" % (name, ))
    subargs = ["engine", "heap"]
    assert orig_funcargs[0] == "engine"
    assert orig_funcargs[1] == "heap"
    code.append("    assert isinstance(query, term.Callable)")
    for i, spec in enumerate(unwrap_spec):
        varname = "var%s" % (i, )
        subargs.append(varname)
        if spec in ("obj", "callable", "int", "atom", "arithmetic", "instream", "outstream", "stream", "list"):
            code.append("    %s = query.argument_at(%s).dereference(heap)" %
                        (varname, i))
        if spec in ("int", "atom", "arithmetic", "list", "instream", "outstream", "stream"):
            code.append(
                "    if isinstance(%s, term.Var):" % (varname,))
            code.append(
                "        error.throw_instantiation_error()")
        if spec == "obj":
            pass
        elif spec == "callable":
            code.append(
                "    if not isinstance(%s, term.Callable):" % (varname,))
            code.append(
                "        if isinstance(%s, term.Var):" % (varname,))
            code.append(
                "           error.throw_instantiation_error()")
            code.append(
                "        error.throw_type_error('callable', %s)" % (varname,))
        elif spec == "raw":
            code.append("    %s = query.argument_at(%s)" % (varname, i))
        elif spec == "int":
            code.append("    %s = helper.unwrap_int(%s)" % (varname, varname))
        elif spec == "atom":
            code.append("    %s = helper.unwrap_atom(%s)" % (varname, varname))
        elif spec == "arithmetic":
            code.append("    %s = eval_arithmetic(engine, %s)" %
                        (varname, varname))
        elif spec == "list":
            code.append("    %s = helper.unwrap_list(%s)" % (varname, varname))
        elif spec == "stream":
            code.append("    %s = helper.unwrap_stream(engine, %s)" % (varname, varname))
        elif spec == "instream":
            code.append("    %s = helper.unwrap_instream(engine, %s)" % (varname, varname))
        elif spec == "outstream":
            code.append("    %s = helper.unwrap_outstream(engine, %s)" % (varname, varname))
        else:
            assert 0, "not implemented " + spec
    if needs_module:
        subargs.insert(2, "module")
        assert orig_funcargs[2] == "module"
    if handles_continuation:
        subargs.append("scont")
        subargs.append("fcont")
        assert orig_funcargs[subargs.index("scont")] == "scont"
        assert orig_funcargs[subargs.index("fcont")] == "fcont"
    call = "    result = %s(%s)" % (func.func_name, ", ".join(subargs))
    code.append(call)
    if not handles_continuation:
        code.append("    return scont, fcont, heap")
    else:
        code.append("    return result")
    miniglobals = globals().copy()
    miniglobals[func.func_name] = func
    #if func.__module__[len("prolog.builtin."):] not in jit_modules:
    #    jit.dont_look_inside(func)
    exec py.code.Source("\n".join(code)).compile() in miniglobals
    for name in expose_as:
        l = len(unwrap_spec)
        signature = Signature.getsignature(name, l)
        b = Builtin(miniglobals[funcname], funcname, l, signature)
        signature.set_extra("builtin", b)
    return func
