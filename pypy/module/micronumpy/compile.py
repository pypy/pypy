
""" This is a set of tools for standalone compiling of numpy expressions.
It should not be imported by the module itself
"""

from pypy.interpreter.baseobjspace import InternalSpaceCache, W_Root
from pypy.module.micronumpy import interp_boxes
from pypy.module.micronumpy.interp_dtype import get_dtype_cache
from pypy.module.micronumpy.interp_numarray import (Scalar, BaseArray,
     descr_new_array, scalar_w, SingleDimArray)
from pypy.module.micronumpy import interp_ufuncs
from pypy.rlib.objectmodel import specialize


class BogusBytecode(Exception):
    pass

class ArgumentMismatch(Exception):
    pass

class ArgumentNotAnArray(Exception):
    pass

class WrongFunctionName(Exception):
    pass

SINGLE_ARG_FUNCTIONS = ["sum", "prod", "max", "min", "all", "any", "unegative"]

class FakeSpace(object):
    w_ValueError = None
    w_TypeError = None
    w_None = None

    w_bool = "bool"
    w_int = "int"
    w_float = "float"
    w_list = "list"
    w_long = "long"
    w_tuple = 'tuple'

    def __init__(self):
        """NOT_RPYTHON"""
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.w_float64dtype = get_dtype_cache(self).w_float64dtype

    def issequence_w(self, w_obj):
        return isinstance(w_obj, ListObject) or isinstance(w_obj, SingleDimArray)

    def isinstance_w(self, w_obj, w_tp):
        return False

    def decode_index4(self, w_idx, size):
        return (self.int_w(self.int(w_idx)), 0, 0, 1)

    @specialize.argtype(1)
    def wrap(self, obj):
        if isinstance(obj, float):
            return FloatObject(obj)
        elif isinstance(obj, bool):
            return BoolObject(obj)
        elif isinstance(obj, int):
            return IntObject(obj)
        raise Exception

    def newlist(self, items):
        return ListObject(items)

    def listview(self, obj):
        assert isinstance(obj, ListObject)
        return obj.items

    def float(self, w_obj):
        if isinstance(w_obj, FloatObject):
            return w_obj
        assert isinstance(w_obj, interp_boxes.W_GenericBox)
        return self.float(w_obj.descr_float(self))

    def float_w(self, w_obj):
        assert isinstance(w_obj, FloatObject)
        return w_obj.floatval

    def int_w(self, w_obj):
        if isinstance(w_obj, IntObject):
            return w_obj.intval
        elif isinstance(w_obj, FloatObject):
            return int(w_obj.floatval)
        raise NotImplementedError

    def int(self, w_obj):
        if isinstance(w_obj, IntObject):
            return w_obj
        assert isinstance(w_obj, interp_boxes.W_GenericBox)
        return self.int(w_obj.descr_int(self))

    def is_true(self, w_obj):
        assert isinstance(w_obj, BoolObject)
        return w_obj.boolval

    def is_w(self, w_obj, w_what):
        return w_obj is w_what

    def type(self, w_obj):
        return w_obj.tp

    def gettypefor(self, w_obj):
        return None

    def call_function(self, tp, w_dtype):
        return w_dtype

    @specialize.arg(1)
    def interp_w(self, tp, what):
        assert isinstance(what, tp)
        return what

class FloatObject(W_Root):
    tp = FakeSpace.w_float
    def __init__(self, floatval):
        self.floatval = floatval

class BoolObject(W_Root):
    tp = FakeSpace.w_bool
    def __init__(self, boolval):
        self.boolval = boolval

class IntObject(W_Root):
    tp = FakeSpace.w_int
    def __init__(self, intval):
        self.intval = intval

class ListObject(W_Root):
    tp = FakeSpace.w_list
    def __init__(self, items):
        self.items = items

class InterpreterState(object):
    def __init__(self, code):
        self.code = code
        self.variables = {}
        self.results = []

    def run(self, space):
        self.space = space
        for stmt in self.code.statements:
            stmt.execute(self)

class Node(object):
    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other

    def wrap(self, space):
        raise NotImplementedError

    def execute(self, interp):
        raise NotImplementedError

class Assignment(Node):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def execute(self, interp):
        interp.variables[self.name] = self.expr.execute(interp)

    def __repr__(self):
        return "%% = %r" % (self.name, self.expr)

class ArrayAssignment(Node):
    def __init__(self, name, index, expr):
        self.name = name
        self.index = index
        self.expr = expr

    def execute(self, interp):
        arr = interp.variables[self.name]
        w_index = self.index.execute(interp).eval(0)
        w_val = self.expr.execute(interp).eval(0)
        assert isinstance(arr, BaseArray)
        arr.descr_setitem(interp.space, w_index, w_val)

    def __repr__(self):
        return "%s[%r] = %r" % (self.name, self.index, self.expr)

class Variable(Node):
    def __init__(self, name):
        self.name = name

    def execute(self, interp):
        return interp.variables[self.name]

    def __repr__(self):
        return 'v(%s)' % self.name

class Operator(Node):
    def __init__(self, lhs, name, rhs):
        self.name = name
        self.lhs = lhs
        self.rhs = rhs

    def execute(self, interp):
        w_lhs = self.lhs.execute(interp)
        assert isinstance(w_lhs, BaseArray)
        if isinstance(self.rhs, SliceConstant):
            # XXX interface has changed on multidim branch
            raise NotImplementedError
        w_rhs = self.rhs.execute(interp)
        if self.name == '+':
            w_res = w_lhs.descr_add(interp.space, w_rhs)
        elif self.name == '*':
            w_res = w_lhs.descr_mul(interp.space, w_rhs)
        elif self.name == '-':
            w_res = w_lhs.descr_sub(interp.space, w_rhs)
        elif self.name == '->':
            if isinstance(w_rhs, Scalar):
                index = int(interp.space.float_w(interp.space.float(w_rhs.value)))
                dtype = get_dtype_cache(interp.space).w_float64dtype
                return Scalar(dtype, w_lhs.get_concrete().eval(index))
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
        if (not isinstance(w_res, BaseArray) and
            not isinstance(w_res, interp_boxes.W_GenericBox)):
            dtype = get_dtype_cache(interp.space).w_float64dtype
            w_res = scalar_w(interp.space, dtype, w_res)
        return w_res

    def __repr__(self):
        return '(%r %s %r)' % (self.lhs, self.name, self.rhs)

class FloatConstant(Node):
    def __init__(self, v):
        self.v = float(v)

    def __repr__(self):
        return "Const(%s)" % self.v

    def wrap(self, space):
        return space.wrap(self.v)

    def execute(self, interp):
        dtype = get_dtype_cache(interp.space).w_float64dtype
        return Scalar(dtype, dtype.box(self.v))

class RangeConstant(Node):
    def __init__(self, v):
        self.v = int(v)

    def execute(self, interp):
        w_list = interp.space.newlist(
            [interp.space.wrap(float(i)) for i in range(self.v)]
        )
        dtype = get_dtype_cache(interp.space).w_float64dtype
        return descr_new_array(interp.space, None, w_list, w_dtype=dtype)

    def __repr__(self):
        return 'Range(%s)' % self.v

class Code(Node):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return "\n".join([repr(i) for i in self.statements])

class ArrayConstant(Node):
    def __init__(self, items):
        self.items = items

    def wrap(self, space):
        return space.newlist([item.wrap(space) for item in self.items])

    def execute(self, interp):
        w_list = self.wrap(interp.space)
        dtype = get_dtype_cache(interp.space).w_float64dtype
        return descr_new_array(interp.space, None, w_list, w_dtype=dtype)

    def __repr__(self):
        return "[" + ", ".join([repr(item) for item in self.items]) + "]"

class SliceConstant(Node):
    def __init__(self):
        pass

    def __repr__(self):
        return 'slice()'

class Execute(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return repr(self.expr)

    def execute(self, interp):
        interp.results.append(self.expr.execute(interp))

class FunctionCall(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return "%s(%s)" % (self.name, ", ".join([repr(arg)
                                                 for arg in self.args]))

    def execute(self, interp):
        if self.name in SINGLE_ARG_FUNCTIONS:
            if len(self.args) != 1:
                raise ArgumentMismatch
            arr = self.args[0].execute(interp)
            if not isinstance(arr, BaseArray):
                raise ArgumentNotAnArray
            if self.name == "sum":
                w_res = arr.descr_sum(interp.space)
            elif self.name == "prod":
                w_res = arr.descr_prod(interp.space)
            elif self.name == "max":
                w_res = arr.descr_max(interp.space)
            elif self.name == "min":
                w_res = arr.descr_min(interp.space)
            elif self.name == "any":
                w_res = arr.descr_any(interp.space)
            elif self.name == "all":
                w_res = arr.descr_all(interp.space)
            elif self.name == "unegative":
                neg = interp_ufuncs.get(interp.space).negative
                w_res = neg.call(interp.space, [arr])
            else:
                assert False # unreachable code
            if isinstance(w_res, BaseArray):
                return w_res
            if isinstance(w_res, FloatObject):
                dtype = get_dtype_cache(interp.space).w_float64dtype
            elif isinstance(w_res, BoolObject):
                dtype = get_dtype_cache(interp.space).w_booldtype
            elif isinstance(w_res, interp_boxes.W_GenericBox):
                dtype = w_res.get_dtype(interp.space)
            else:
                dtype = None
            return scalar_w(interp.space, dtype, w_res)
        else:
            raise WrongFunctionName

class Parser(object):
    def parse_identifier(self, id):
        id = id.strip(" ")
        #assert id.isalpha()
        return Variable(id)

    def parse_expression(self, expr):
        tokens = [i for i in expr.split(" ") if i]
        if len(tokens) == 1:
            return self.parse_constant_or_identifier(tokens[0])
        stack = []
        tokens.reverse()
        while tokens:
            token = tokens.pop()
            if token == ')':
                raise NotImplementedError
            elif self.is_identifier_or_const(token):
                if stack:
                    name = stack.pop().name
                    lhs = stack.pop()
                    rhs = self.parse_constant_or_identifier(token)
                    stack.append(Operator(lhs, name, rhs))
                else:
                    stack.append(self.parse_constant_or_identifier(token))
            else:
                stack.append(Variable(token))
        assert len(stack) == 1
        return stack[-1]

    def parse_constant(self, v):
        lgt = len(v)-1
        assert lgt >= 0
        if ':' in v:
            # a slice
            assert v == ':'
            return SliceConstant()
        if v[0] == '[':
            return ArrayConstant([self.parse_constant(elem)
                                  for elem in v[1:lgt].split(",")])
        if v[0] == '|':
            return RangeConstant(v[1:lgt])
        return FloatConstant(v)

    def is_identifier_or_const(self, v):
        c = v[0]
        if ((c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') or
            (c >= '0' and c <= '9') or c in '-.[|:'):
            if v == '-' or v == "->":
                return False
            return True
        return False

    def parse_function_call(self, v):
        l = v.split('(')
        assert len(l) == 2
        name = l[0]
        cut = len(l[1]) - 1
        assert cut >= 0
        args = [self.parse_constant_or_identifier(id)
                for id in l[1][:cut].split(",")]
        return FunctionCall(name, args)

    def parse_constant_or_identifier(self, v):
        c = v[0]
        if (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z'):
            if '(' in v:
                return self.parse_function_call(v)
            return self.parse_identifier(v)
        return self.parse_constant(v)

    def parse_array_subscript(self, v):
        v = v.strip(" ")
        l = v.split("[")
        lgt = len(l[1]) - 1
        assert lgt >= 0
        rhs = self.parse_constant_or_identifier(l[1][:lgt])
        return l[0], rhs

    def parse_statement(self, line):
        if '=' in line:
            lhs, rhs = line.split("=")
            lhs = lhs.strip(" ")
            if '[' in lhs:
                name, index = self.parse_array_subscript(lhs)
                return ArrayAssignment(name, index, self.parse_expression(rhs))
            else:
                return Assignment(lhs, self.parse_expression(rhs))
        else:
            return Execute(self.parse_expression(line))

    def parse(self, code):
        statements = []
        for line in code.split("\n"):
            if '#' in line:
                line = line.split('#', 1)[0]
            line = line.strip(" ")
            if line:
                statements.append(self.parse_statement(line))
        return Code(statements)

def numpy_compile(code):
    parser = Parser()
    return InterpreterState(parser.parse(code))
