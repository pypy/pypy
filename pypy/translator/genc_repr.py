"""
High-level types and how variables of that type are represented by a
series of low-level variables.
"""

import types, __builtin__
from pypy.translator.typer import CannotConvert, LLConst
from pypy.translator import genc_op


class CRepr:
    "A possible representation of a flow-graph variable as C-level variables."
    parse_code = None    # character(s) for PyArg_ParseTuple()

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ' + '.join(self.impl))

    def convert_to(self, target, typeset):
        raise CannotConvert


class CAtomicRepr(CRepr):
    "A simple C type."

    def __init__(self, impl, parse_code=None):
        self.impl = impl
        self.parse_code = parse_code


class CUndefined(CRepr):
    "An undefined value. (singleton class)"
    impl = []
    
    def convert_to(self, target, typeset):
        return genc_op.LoDummyResult


class CConstant(CRepr):
    "A constant value."
    impl = []

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'CConstant(%r)' % (self.value,)

    def convert_to_pyobj(self, initexpr, globalname):
        # helper for subclasses
        return genc_op.LoKnownAnswer.With(
            known_answer = [LLConst('PyObject*', globalname, initexpr,
                                    to_declare = bool(initexpr))],
            )

class CConstantInt(CConstant):
    def convert_to(self, target, typeset):
        if target == R_INT:
            # can convert the constant to a C int
            return genc_op.LoKnownAnswer.With(
                known_answer = [LLConst('int', '%d' % self.value)],
                )
        elif target == R_OBJECT:
            # can convert the constant to a PyObject*
            if self.value >= 0:
                name = 'g_IntObj_%d' % self.value
            else:
                name = 'g_IntObj_minus%d' % abs(self.value)
            return self.convert_to_pyobj(
                'PyInt_FromLong(%d)' % self.value,
                name)
        else:
            raise CannotConvert

class CConstantStr(CConstant):
    def convert_to(self, target, typeset):
        if target == R_OBJECT:
            # can convert the constant to a PyObject*
            return self.convert_to_pyobj(
                'PyString_FromStringAndSize(%s, %d)' % (c_str(self.value),
                                                        len(self.value)),
                'g_StrObj_%s' % manglestr(self.value))
        else:
            raise CannotConvert

class CConstantNone(CConstant):
    def convert_to(self, target, typeset):
        if target == R_OBJECT:
            # can convert the constant to a PyObject*
            return self.convert_to_pyobj(None, 'Py_None')
        else:
            raise CannotConvert

class CConstantBuiltin(CConstant):   # a constant from the __builtin__ module
    def convert_to(self, target, typeset):
        if target == R_OBJECT:
            # can load the constant as a PyObject* from the builtins
            fn = self.value
            if getattr(__builtin__, fn.__name__, None) is not fn:
                raise CannotConvert   # unless it doesn't appear to be there
            return self.convert_to_pyobj(
                'PyMapping_GetItemString(PyEval_GetBuiltins(), %s)' % (
                    c_str(fn.__name__)),
                'g_Builtin_%s' % manglestr(fn.__name__))
        else:
            raise CannotConvert

class CConstantFunction(CConstant):
    def convert_to(self, target, typeset):
        if isinstance(target, CFunction):
            fn = self.value
            if fn not in typeset.genc.llfunctions:
                raise CannotConvert
            llfunc = typeset.genc.llfunctions[fn]
            my_header_r = typeset.getfunctionsig(llfunc)
            if my_header_r != target.header_r:
                raise CannotConvert(self, my_header_r, target)
            cfunctype, = target.impl
            return genc_op.LoKnownAnswer.With(
                known_answer = [LLConst(cfunctype, llfunc.name)],
                )
        else:
            raise CannotConvert


class CTuple(CRepr):
    "An unpacked tuple.  Represents all its items independently."

    def __init__(self, items_r):
        self.items_r = tuple(items_r)
        self.impl = []
        for r in items_r:
            self.impl += r.impl

    def __repr__(self):
        return 'CTuple(%s)' % ', '.join([repr(r) for r in self.items_r])

    def convert_to(self, target, typeset):
        if isinstance(target, CTuple):
            if len(self.items_r) != len(target.items_r):
                raise CannotConvert
            # convert each tuple item that needs to be converted
            cost = 0
            for r1, r2 in zip(self.items_r, target.items_r):
                if r1 != r2:
                    cost += typeset.getconversion(r1, r2).cost
            return genc_op.LoConvertTupleItem.With(
                source_r = self.items_r,
                target_r = target.items_r,
                cost     = cost,
                )
        elif target == R_OBJECT:
            # to convert a tuple to a PyTupleObject* we first need to
            # make sure that all items are PyObject*.
            intermediate_r = (R_OBJECT,) * len(self.items_r)
            if self.items_r == intermediate_r:
                return genc_op.LoNewTuple   # already the case
            else:
                r_middle = tuple_representation(intermediate_r)
                cost1 = typeset.getconversion(self, r_middle).cost
                return genc_op.LoConvertChain.With(
                    r_from   = self,
                    r_middle = r_middle,
                    r_to     = target,
                    cost     = cost1 + genc_op.LoNewTuple.cost,
                    )
        else:
            raise CannotConvert


class CInstance(CRepr):
    "An instance of some class (or a subclass of it)."
    impl = ['PyObject*']

    def __init__(self, llclass):
        self.llclass = llclass     # instance of classtyper.LLClass or None
        # R_INSTANCE is CInstance(None): a match-all, any-type instance.

    def __repr__(self):
        if self.llclass is None:
            return 'CInstance(*)'
        else:
            cls = self.llclass.cdef.cls
            return 'CInstance(%s.%s)' % (cls.__module__, cls.__name__)

    def convert_to(self, target, typeset):
        if isinstance(target, CInstance):
            if not (self.llclass is None or target.llclass is None):
                # can only convert to an instance of a parent class
                if target.llclass.cdef not in self.llclass.cdef.getmro():
                    raise CannotConvert
            return genc_op.LoCopy
        elif target == R_OBJECT:
            # can convert to a generic PyObject*
            return genc_op.LoCopy
        else:
            raise CannotConvert


class CFunction(CRepr):
    "A C-level function or a pointer to a function."

    def __init__(self, header_r):
        self.header_r = header_r  # list of CReprs: [arg1, arg2, ..., retval]
        # C syntax is quite strange: a pointer to a function is declared
        # with a syntax like "int (*varname)(long, char*)".  We build here
        # a 'type' string like "int (*@)(long, char*)" that will be combined
        # with an actual name by cdecl() below.  Oh, and by the way, to
        # make a string like "int (*@)(long, char*)" we need to use cdecl()
        # as well, because the "int" which is the return type could itself
        # contain a "@"... for functions returning pointers to functions.
        llargs = []
        for r in  header_r[:-1]:
            llargs += [cdecl(atype, '') for atype in r.impl]
        llret = header_r[-1].impl
        # same logic as get_llfunc_header()
        if len(llret) == 0:
            retlltype = 'int' # no return value needed, returns an error flag
        elif len(llret) == 1:
            retlltype = llret[0]
        else:
            # if there is more than one C return type, only the first one is
            # returned and the other ones are returned via ptr output args
            retlltype = llret[0]
            llargs += [cdecl(atype, '*') for atype in llret[1:]]
        cfunctype = cdecl(retlltype, '(*@)(%s)' % ', '.join(llargs))
        self.impl = [cfunctype]

    def __repr__(self):
        args = [repr(r) for r in self.header_r[:-1]]
        return 'CFunction(%s -> %r)' % (', '.join(args), self.header_r[-1])


class CMethod(CRepr):
    "A CFunction or CConstantFunction with its first argument bound."

    def __init__(self, r_func):
        self.r_func = r_func
        self.impl = r_func.impl + ['PyObject*']

    def __repr__(self):
        return 'CMethod(%r)' % (self.r_func,)

    def convert_to(self, target, typeset):
        if not isinstance(target, CMethod):
            raise CannotConvert
        cost = typeset.getconversion(self.r_func, target.r_func).cost
        return genc_op.LoConvertBoundMethod.With(
            r_source = self.r_func,
            r_target = target.r_func,
            cost     = cost,
            )

# ____________________________________________________________
#
# Predefined CReprs and caches for building more

R_VOID      = CAtomicRepr([])
R_INT       = CAtomicRepr(['int'],       parse_code='i')
R_OBJECT    = CAtomicRepr(['PyObject*'], parse_code='O')
R_UNDEFINED = CUndefined()
R_INSTANCE  = CInstance(None)

R_TUPLE_CACHE    = {}
R_CONSTANT_CACHE = {}
R_INSTANCE_CACHE = {}
R_FUNCTION_CACHE = {}
R_METHOD_CACHE   = {}

def tuple_representation(items_r):
    items_r = tuple(items_r)
    try:
        return R_TUPLE_CACHE[items_r]
    except KeyError:
        rt   = R_TUPLE_CACHE[items_r] = CTuple(items_r)
        return rt

CONST_TYPES = {
    int:                       CConstantInt,
    str:                       CConstantStr,
    types.NoneType:            CConstantNone,
    types.BuiltinFunctionType: CConstantBuiltin,
    types.FunctionType:        CConstantFunction,
    }

def constant_representation(value):
    key = type(value), value   # to avoid mixing for example 0 and 0.0
    try:
        return R_CONSTANT_CACHE[key]
    except KeyError:
        if isinstance(value, tuple):
            # tuples have their own representation and
            # don't need a fully constant representation
            items_r = [constant_representation(x) for x in value]
            return tuple_representation(items_r)
        for cls in type(value).__mro__:
            if cls in CONST_TYPES:
                cls = CONST_TYPES[cls]
                break
        else:
            if isinstance(value, types.MethodType) and value.im_self is None:
                # replace unbound methods with plain funcs
                return constant_representation(value.im_func)
            cls = CConstant
        r = R_CONSTANT_CACHE[key] = cls(value)
        return r

def instance_representation(llclass):
    try:
        return R_INSTANCE_CACHE[llclass]
    except KeyError:
        r = R_INSTANCE_CACHE[llclass] = CInstance(llclass)
        return r

def function_representation(sig):
    key = tuple(sig)
    try:
        return R_FUNCTION_CACHE[key]
    except KeyError:
        r = R_FUNCTION_CACHE[key] = CFunction(sig)
        return r

def method_representation(r_func):
    key = r_func
    try:
        return R_METHOD_CACHE[key]
    except KeyError:
        r = R_METHOD_CACHE[key] = CMethod(r_func)
        return r


def c_str(s):
    "Return the C expression for the string 's'."
    s = repr(s)
    if s.startswith("'"):
        s = '"' + s[1:-1].replace('"', r'\"') + '"'
    return s

def manglestr(s):
    "Return an identifier name unique for the string 's'."
    l = []
    for c in s:
        if not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9'):
            if c == '_':
                c = '__'
            else:
                c = '_%02x' % ord(c)
        l.append(c)
    return ''.join(l)

def cdecl(type, name):
    # Utility to generate a typed name declaration in C syntax.
    # For local variables, struct fields, function declarations, etc.
    # For complex C types, the 'type' can contain a '@' character that
    # specifies where the 'name' should be inserted; for example, an
    # array of 10 ints has a type of "int @[10]".
    if '@' in type:
        return type.replace('@', name)
    else:
        return ('%s %s' % (type, name)).rstrip()
