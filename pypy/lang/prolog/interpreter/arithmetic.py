import py
import math
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound
from pypy.rlib.rarithmetic import intmask

arithmetic_functions = {}

pattern_to_function = {}

def wrap_builtin_operation(pattern, unwrap_spec, can_overflow):
    code = ["def f(engine, query):"]
    for i, spec in enumerate(unwrap_spec):
        varname = "var%s" % (i, )
        code.append(
            "    %s = eval_arithmetic(engine, query.args[%s])" % (varname, i))
        code.append(
            "    v%s = 0" % (i, ))
        code.append("    if isinstance(%s, term.Number):" % (varname, ))
        code.append("        v%s = %s.num" % (i, varname))
        if spec == "expr":
            code.append("    elif isinstance(%s, term.Float):" % (varname, ))
            code.append("        v%s = %s.num" % (i, varname))
        code.append("    else:")
        code.append("        error.throw_type_error('int', %s)" % (varname, ))
    code.append("    return norm_float(%s)" % pattern)
    miniglobals = globals().copy()
    exec py.code.Source("\n".join(code)).compile() in miniglobals
    return miniglobals['f']

wrap_builtin_operation._annspecialcase_ = 'specialize:memo'

def eval_arithmetic(engine, query):
    query = query.getvalue(engine.heap)
    if isinstance(query, term.Number):
        return query
    if isinstance(query, term.Float):
        return norm_float(query.num)
    if isinstance(query, term.Atom):
        #XXX beautify that
        if query.name == "pi":
            return term.Float(math.pi)
        if query.name == "e":
            return term.Float(math.e)
        raise error.UncatchableError("not implemented")
    if isinstance(query, term.Term):
        func = arithmetic_functions.get(query.signature, None)
        if func is None:
            error.throw_type_error("evaluable", query.get_prolog_signature())
        return func(engine, query)
    raise error.UncatchableError("not implemented")

def norm_float(v):
    if v == int(v):
        return term.Number(int(v))
    else:
        return term.Float(v)

simple_functions = [
    ("+",                     ["expr", "expr"], "v0 + v1", True),
    ("-",                     ["expr", "expr"], "v0 - v1", True),
    ("*",                     ["expr", "expr"], "v0 * v1", True),
    ("//",                    ["int",  "int"],  "v0 / v1", True),
    ("**",                    ["expr", "expr"], "v0 ** v1", True),
    (">>",                    ["int", "int"],   "v0 >> v1", False),
    ("<<",                    ["int", "int"],   "intmask(v0 << v1)", False),
    ("\\/",                   ["int", "int"],   "v0 | v1", False),
    ("/\\",                   ["int", "int"],   "v0 & v1", False),
    ("xor",                   ["int", "int"],   "v0 ^ v1", False),
    ("mod",                   ["int", "int"],   "v0 % v1", False),
    ("\\",                    ["int"],          "v0 ^ 0", False),
    ("abs",                   ["expr"],         "abs(v0)", True),
#    ("max",                   ["expr", "expr"], "max(v0, v1)", False),
#    ("min",                   ["expr", "expr"], "min(v0, v1)", False),
    ("round",                 ["expr"],         "int(v0 + 0.5)", False),
    ("floor",                 ["expr"],         "math.floor(v0)", False),
    ("ceiling",               ["expr"],         "math.ceil(v0)", False),
    ("floor",                 ["expr"],         "math.floor(v0)", False),
    ("float_fractional_part", ["expr"],         "v0 - int(v0)", False),
    ("float_integer_part",    ["expr"],         "int(v0)", False),
]

for prolog_name, unwrap_spec, pattern, overflow in simple_functions:
    f = wrap_builtin_operation(pattern, unwrap_spec, overflow)
    signature = "%s/%s" % (prolog_name, len(unwrap_spec))
    arithmetic_functions[signature] = f
