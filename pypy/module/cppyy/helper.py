from pypy.rlib import rstring


#- type name manipulations --------------------------------------------------
def compound(name):
    name = "".join(rstring.split(name, "const")) # poor man's replace
    if name.endswith("]"):                       # array type?
        return "[]"
    i = _find_qualifier_index(name)
    return "".join(name[i:].split(" "))

def array_size(name):
    name = "".join(rstring.split(name, "const")) # poor man's replace
    if name.endswith("]"):                       # array type?
        idx = name.rfind("[")
        if 0 < idx:
            end = len(name)-1                    # len rather than -1 for rpython
            if 0 < end and (idx+1) < end:        # guarantee non-neg for rpython
                return int(name[idx+1:end])
    return -1

def _find_qualifier_index(name):
    i = len(name)
    # search from the back; note len(name) > 0 (so rtyper can use uint)
    for i in range(len(name) - 1, 0, -1):
        c = name[i]
        if c.isalnum() or c == ">" or c == "]":
            break
    return i + 1

def clean_type(name):
    # can't strip const early b/c name could be a template ...
    i = _find_qualifier_index(name)
    name = name[:i].strip(' ')

    idx = -1
    if name.endswith("]"):                       # array type?
        idx = name.rfind("[")
        if 0 < idx:
             name = name[:idx]
    elif name.endswith(">"):                     # template type?
        idx = name.find("<")
        n1 = "".join(rstring.split(name[:idx], "const")) # poor man's replace
        name = "".join((n1, name[idx:]))
    else:
        name = "".join(rstring.split(name, "const")) # poor man's replace
        name = name[:_find_qualifier_index(name)]
    return name.strip(' ')


#- operator mappings --------------------------------------------------------
_operator_mappings = {}

def map_operator_name(cppname, nargs):
    from pypy.module.cppyy import capi

    if cppname[0:8] == "operator":
        op = cppname[8:].strip(' ')

        # operator could be a conversion using a typedef
        handle = capi.c_get_typehandle(op)
        if handle:
            op = capi.charp2str_free(capi.c_final_name(handle))

        # look for known mapping
        try:
            return _operator_mappings[op]
        except KeyError:
            pass

        # a couple more cases that depend on whether args were given

        if op == "*":   # dereference (not python) vs. multiplication
            return nargs and "__mul__" or "__deref__"

        if op == "+":   # unary positive vs. binary addition
            return nargs and  "__add__" or "__pos__"

        if op == "-":   # unary negative vs. binary subtraction
            return nargs and "__sub__" or "__neg__"

        if op == "++":  # prefix v.s. postfix increment (not python)
            return nargs and "__postinc__" or "__preinc__";

        if op == "--":  # prefix v.s. postfix decrement (not python)
            return nargs and "__postdec__" or "__predec__";

    # might get here, as not all operator methods handled (new, delete,etc.)
    # TODO: perhaps absorb or "pythonify" these operators?
    return cppname

# _operator_mappings["[]"]  = "__setitem__"      # depends on return type
# _operator_mappings["+"]   = "__add__"          # depends on # of args (see __pos__)
# _operator_mappings["-"]   = "__sub__"          # id. (eq. __neg__)
# _operator_mappings["*"]   = "__mul__"          # double meaning in C++

_operator_mappings["[]"]  = "__getitem__"
_operator_mappings["()"]  = "__call__"
_operator_mappings["/"]   = "__div__"            # __truediv__ in p3
_operator_mappings["%"]   = "__mod__"
_operator_mappings["**"]  = "__pow__"            # not C++
_operator_mappings["<<"]  = "__lshift__"
_operator_mappings[">>"]  = "__rshift__"
_operator_mappings["&"]   = "__and__"
_operator_mappings["|"]   = "__or__"
_operator_mappings["^"]   = "__xor__"
_operator_mappings["~"]   = "__inv__"
_operator_mappings["+="]  = "__iadd__"
_operator_mappings["-="]  = "__isub__"
_operator_mappings["*="]  = "__imul__"
_operator_mappings["/="]  = "__idiv__"           # __itruediv__ in p3
_operator_mappings["%="]  = "__imod__"
_operator_mappings["**="] = "__ipow__"
_operator_mappings["<<="] = "__ilshift__"
_operator_mappings[">>="] = "__irshift__"
_operator_mappings["&="]  = "__iand__"
_operator_mappings["|="]  = "__ior__"
_operator_mappings["^="]  = "__ixor__"
_operator_mappings["=="]  = "__eq__"
_operator_mappings["!="]  = "__ne__"
_operator_mappings[">"]   = "__gt__"
_operator_mappings["<"]   = "__lt__"
_operator_mappings[">="]  = "__ge__"
_operator_mappings["<="]  = "__le__"

# the following type mappings are "exact"
_operator_mappings["const char*"] = "__str__"
_operator_mappings["int"]         = "__int__"
_operator_mappings["long"]        = "__long__"   # __int__ in p3
_operator_mappings["double"]      = "__float__"

# the following type mappings are "okay"; the assumption is that they
# are not mixed up with the ones above or between themselves (and if
# they are, that it is done consistently)
_operator_mappings["char*"]              = "__str__"
_operator_mappings["short"]              = "__int__"
_operator_mappings["unsigned short"]     = "__int__"
_operator_mappings["unsigned int"]       = "__long__"      # __int__ in p3
_operator_mappings["unsigned long"]      = "__long__"      # id.
_operator_mappings["long long"]          = "__long__"      # id.
_operator_mappings["unsigned long long"] = "__long__"      # id.
_operator_mappings["float"]              = "__float__"

_operator_mappings["bool"] = "__nonzero__"       # __bool__ in p3

# the following are not python, but useful to expose
_operator_mappings["->"]  = "__follow__"
_operator_mappings["="]   = "__assign__"
