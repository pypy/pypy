
""" This is a set of tools for standalone compiling of numpy expressions.
It should not be imported by the module itself
"""

from pypy.interpreter.baseobjspace import InternalSpaceCache, W_Root
from pypy.module.micronumpy.interp_dtype import W_Float64Dtype, W_Int32Dtype
from pypy.module.micronumpy.interp_numarray import Scalar, BaseArray, descr_new_array
from pypy.rlib.objectmodel import specialize


class BogusBytecode(Exception):
    pass

def create_array(dtype, size):
    a = SingleDimArray(size, dtype=dtype)
    for i in range(size):
        dtype.setitem(a.storage, i, dtype.box(float(i % 10)))
    return a

class FakeSpace(object):
    w_ValueError = None
    w_TypeError = None
    w_None = None

    w_bool = "bool"
    w_int = "int"
    w_float = "float"
    w_list = "list"
    w_long = "long"

    def __init__(self):
        """NOT_RPYTHON"""
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.w_float64dtype = W_Float64Dtype(self)

    def issequence_w(self, w_obj):
        return w_obj.seq

    def isinstance_w(self, w_obj, w_tp):
        return False

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
        assert isinstance(w_obj, FloatObject)
        return w_obj

    def float_w(self, w_obj):
        assert isinstance(w_obj, FloatObject)        
        return w_obj.floatval

    def int_w(self, w_obj):
        assert isinstance(w_obj, IntObject)
        return w_obj.intval

    def int(self, w_obj):
        return w_obj

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
    seq = False
    tp = FakeSpace.w_float
    def __init__(self, floatval):
        self.floatval = floatval

class BoolObject(W_Root):
    seq = False
    tp = FakeSpace.w_bool
    def __init__(self, boolval):
        self.boolval = boolval

class IntObject(W_Root):
    seq = False
    tp = FakeSpace.w_int
    def __init__(self, intval):
        self.intval = intval

class ListObject(W_Root):
    seq = True
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
    def __init__(self, id, expr):
        self.id = id
        self.expr = expr

    def execute(self, interp):
        interp.variables[self.id.name] = self.expr.execute(interp)

    def __repr__(self):
        return "%r = %r" % (self.id, self.expr)

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
        w_rhs = self.rhs.execute(interp)
        assert isinstance(w_lhs, BaseArray)
        if self.name == '+':
            return w_lhs.descr_add(interp.space, w_rhs)
        elif self.name == '->':
            if isinstance(w_rhs, Scalar):
                index = int(interp.space.float_w(
                    w_rhs.value.wrap(interp.space)))
                dtype = interp.space.fromcache(W_Float64Dtype)
                return Scalar(dtype, w_lhs.get_concrete().eval(index))
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

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
        dtype = interp.space.fromcache(W_Float64Dtype)
        assert isinstance(dtype, W_Float64Dtype)
        return Scalar(dtype, dtype.box(self.v))

class RangeConstant(Node):
    def __init__(self, v):
        self.v = int(v)

    def execute(self, interp):
        w_list = interp.space.newlist(
            [interp.space.wrap(float(i)) for i in range(self.v)])
        dtype = interp.space.fromcache(W_Float64Dtype)
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
        dtype = interp.space.fromcache(W_Float64Dtype)
        return descr_new_array(interp.space, None, w_list, w_dtype=dtype)

    def __repr__(self):
        return "[" + ", ".join([repr(item) for item in self.items]) + "]"

class Execute(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return repr(self.expr)

    def execute(self, interp):
        interp.results.append(self.expr.execute(interp))

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
        if v[0] == '[':
            return ArrayConstant([self.parse_constant(elem)
                                  for elem in v[1:-1].split(",")])
        if v[0] == '|':
            return RangeConstant(v[1:-1])
        return FloatConstant(v)

    def is_identifier_or_const(self, v):
        c = v[0]
        if ((c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') or
            (c >= '0' and c <= '9') or c in '-.['):
            if v == '-' or v == "->":
                return False
            return True
        return False

    def parse_constant_or_identifier(self, v):
        c = v[0]
        if (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z'):
            return self.parse_identifier(v)
        return self.parse_constant(v)
        
    def parse_statement(self, line):
        if '=' in line:
            lhs, rhs = line.split("=")
            return Assignment(self.parse_identifier(lhs),
                              self.parse_expression(rhs))
        else:
            return Execute(self.parse_expression(line))

    def parse(self, code):
        statements = []
        for line in code.split("\n"):
            line = line.strip(" ")
            if line:
                statements.append(self.parse_statement(line))
        return Code(statements)

def numpy_compile(code):
    parser = Parser()
    return InterpreterState(parser.parse(code))

def xxx_numpy_compile(bytecode, array_size):
    stack = []
    i = 0
    dtype = space.fromcache(W_Float64Dtype)
    for b in bytecode:
        if b == 'a':
            stack.append(create_array(dtype, array_size))
            i += 1
        elif b == 'f':
            stack.append(Scalar(dtype, dtype.box(1.2)))
        elif b == '+':
            right = stack.pop()
            res = stack.pop().descr_add(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '-':
            right = stack.pop()
            res = stack.pop().descr_sub(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '*':
            right = stack.pop()
            res = stack.pop().descr_mul(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '/':
            right = stack.pop()
            res = stack.pop().descr_div(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '%':
            right = stack.pop()
            res = stack.pop().descr_mod(space, right)
            assert isinstance(res, BaseArray)
            stack.append(res)
        elif b == '|':
            res = stack.pop().descr_abs(space)
            assert isinstance(res, BaseArray)
            stack.append(res)
        else:
            print "Unknown opcode: %s" % b
            raise BogusBytecode()
    if len(stack) != 1:
        print "Bogus bytecode, uneven stack length"
        raise BogusBytecode()
    return stack[0]
