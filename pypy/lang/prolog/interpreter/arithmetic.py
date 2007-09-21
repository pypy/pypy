import py
import math
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.jit import we_are_jitted, hint
from pypy.rlib.unroll import unrolling_iterable

arithmetic_functions = {}
arithmetic_functions_list = []


class CodeCollector(object):
    def __init__(self):
        self.code = []
        self.blocks = []

    def emit(self, line):
        for line in line.split("\n"):
            self.code.append(" " * (4 * len(self.blocks)) + line)

    def start_block(self, blockstarter):
        assert blockstarter.endswith(":")
        self.emit(blockstarter)
        self.blocks.append(blockstarter)

    def end_block(self, starterpart=""):
        block = self.blocks.pop()
        assert starterpart in block, "ended wrong block %s with %s" % (
            block, starterpart)

    def tostring(self):
        assert not self.blocks
        return "\n".join(self.code)

def wrap_builtin_operation(name, pattern, unwrap_spec, can_overflow, intversion):
    code = CodeCollector()
    code.start_block("def prolog_%s(engine, query):" % name)
    for i, spec in enumerate(unwrap_spec):
        varname = "var%s" % (i, )
        code.emit("%s = eval_arithmetic(engine, query.args[%s])" %
                  (varname, i))
    for i, spec in enumerate(unwrap_spec):
        varname = "var%s" % (i, )
        if spec == "int":
            code.start_block(
                "if not isinstance(%s, term.Number):" % (varname, ))
            code.emit("error.throw_type_error('int', %s)" % (varname, ))
            code.end_block("if")
    if "expr" in unwrap_spec and intversion:
        # check whether all arguments are ints
        for i, spec in enumerate(unwrap_spec):
            varname = "var%s" % (i, )
            if spec == "int":
                continue
            code.start_block(
                "if isinstance(%s, term.Number):" % (varname, ))
            code.emit("v%s = var%s.num" % (i, i))
        code.emit("return term.Number(int(%s))" % (pattern, ))
        for i, spec in enumerate(unwrap_spec):
            if spec == "int":
                continue
            code.end_block("if")
    
    #general case in an extra function
    args = ", ".join(["var%s" % i for i in range(len(unwrap_spec))])
    code.emit("return general_%s(%s)" % (name, args))
    code.end_block("def")
    code.start_block("def general_%s(%s):" % (name, args))
    for i, spec in enumerate(unwrap_spec):
        varname = "var%s" % (i, )
        code.emit("v%s = 0" % (i, ))
        code.start_block("if isinstance(%s, term.Number):" % (varname, ))
        code.emit("v%s = %s.num" % (i, varname))
        code.end_block("if")
        expected = 'int'
        if spec == "expr":
            code.start_block("elif isinstance(%s, term.Float):" % (varname, ))
            code.emit("v%s = %s.floatval" % (i, varname))
            code.end_block("elif")
            expected = 'float'
        code.start_block("else:")
        code.emit("error.throw_type_error('%s', %s)" % (expected, varname, ))
        code.end_block("else")
    code.emit("return norm_float(term.Float(%s))" % pattern)
    code.end_block("def")
    miniglobals = globals().copy()
    exec py.code.Source(code.tostring()).compile() in miniglobals
    result = miniglobals["prolog_" + name]
    result._look_inside_me_ = True
    return result

wrap_builtin_operation._annspecialcase_ = 'specialize:memo'

def eval_arithmetic(engine, query):
    return query.eval_arithmetic(engine)
eval_arithmetic._look_inside_me_ = True

def norm_float(obj):
    v = obj.floatval
    if v == int(v):
        return term.Number(int(v))
    else:
        return obj

simple_functions = [
    ("+",                     ["expr", "expr"], "v0 + v1", True, True),
    ("-",                     ["expr", "expr"], "v0 - v1", True, True),
    ("*",                     ["expr", "expr"], "v0 * v1", True, True),
    ("//",                    ["int",  "int"],  "v0 / v1", True, False),
    ("**",                    ["expr", "expr"], "math.pow(float(v0), float(v1))", True, False),
    (">>",                    ["int", "int"],   "v0 >> v1", False, False),
    ("<<",                    ["int", "int"],   "intmask(v0 << v1)", False,
                                                                     False),
    ("\\/",                   ["int", "int"],   "v0 | v1", False, False),
    ("/\\",                   ["int", "int"],   "v0 & v1", False, False),
    ("xor",                   ["int", "int"],   "v0 ^ v1", False, False),
    ("mod",                   ["int", "int"],   "v0 % v1", False, False),
    ("\\",                    ["int"],          "~v0", False, False),
    ("abs",                   ["expr"],         "abs(v0)", True, True),
    ("max",                   ["expr", "expr"], "max(v0, v1)", False, True),
    ("min",                   ["expr", "expr"], "min(v0, v1)", False, True),
    ("round",                 ["expr"],         "int(v0 + 0.5)", False, False),
    ("floor",                 ["expr"],         "math.floor(v0)", False, False), #XXX
    ("ceiling",               ["expr"],         "math.ceil(v0)", False, False), #XXX
    ("float_fractional_part", ["expr"],         "v0 - int(v0)", False, False), #XXX
    ("float_integer_part",    ["expr"],         "int(v0)", False, True),
]

for prolog_name, unwrap_spec, pattern, overflow, intversion in simple_functions:
    # the name is purely for flowgraph viewing reasons
    if prolog_name.replace("_", "").isalnum():
        name = prolog_name
    else:
        import unicodedata
        name = "".join([unicodedata.name(unicode(c)).replace(" ", "_").replace("-", "").lower() for c in prolog_name])
    f = wrap_builtin_operation(name, pattern, unwrap_spec, overflow,
                               intversion)
    signature = "%s/%s" % (prolog_name, len(unwrap_spec))
    arithmetic_functions[signature] = f
    arithmetic_functions_list.append((signature, f))

arithmetic_functions_list = unrolling_iterable(arithmetic_functions_list)
