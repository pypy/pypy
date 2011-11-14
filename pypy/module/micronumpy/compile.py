
""" This is a set of tools for standalone compiling of numpy expressions.
It should not be imported by the module itself
"""

from pypy.interpreter.baseobjspace import InternalSpaceCache, W_Root
from pypy.module.micronumpy.interp_dtype import W_Float64Dtype, W_BoolDtype
from pypy.module.micronumpy.interp_numarray import (Scalar, BaseArray,
     descr_new_array, scalar_w, NDimArray)
from pypy.module.micronumpy import interp_ufuncs
from pypy.rlib.objectmodel import specialize
import re

class BogusBytecode(Exception):
    pass

class ArgumentMismatch(Exception):
    pass

class ArgumentNotAnArray(Exception):
    pass

class WrongFunctionName(Exception):
    pass

class TokenizerError(Exception):
    pass

class BadToken(Exception):
    pass

SINGLE_ARG_FUNCTIONS = ["sum", "prod", "max", "min", "all", "any", "unegative"]

class FakeSpace(object):
    w_ValueError = None
    w_TypeError = None
    w_IndexError = None
    w_None = None

    w_bool = "bool"
    w_int = "int"
    w_float = "float"
    w_list = "list"
    w_long = "long"
    w_tuple = 'tuple'
    w_slice = "slice"

    def __init__(self):
        """NOT_RPYTHON"""
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.w_float64dtype = W_Float64Dtype(self)

    def issequence_w(self, w_obj):
        return isinstance(w_obj, ListObject) or isinstance(w_obj, NDimArray)

    def isinstance_w(self, w_obj, w_tp):
        if w_obj.tp == w_tp:
            return True
        return False

    def decode_index4(self, w_idx, size):
        if isinstance(w_idx, IntObject):
            return (self.int_w(w_idx), 0, 0, 1)
        else:
            assert isinstance(w_idx, SliceObject)
            start, stop, step = w_idx.start, w_idx.stop, w_idx.step
            if step == 0:
                return (0, size, 1, size)
            if start < 0:
                start += size
            if stop < 0:
                stop += size
            return (start, stop, step, size//step)

    @specialize.argtype(1)
    def wrap(self, obj):
        if isinstance(obj, float):
            return FloatObject(obj)
        elif isinstance(obj, bool):
            return BoolObject(obj)
        elif isinstance(obj, int):
            return IntObject(obj)
        elif isinstance(obj, W_Root):
            return obj
        raise NotImplementedError

    def newlist(self, items):
        return ListObject(items)

    def listview(self, obj):
        assert isinstance(obj, ListObject)
        return obj.items
    fixedview = listview

    def float(self, w_obj):
        assert isinstance(w_obj, FloatObject)
        return w_obj

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

    def len_w(self, w_obj):
        if isinstance(w_obj, ListObject):
            return len(w_obj.items)
        # XXX array probably
        assert False

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

class SliceObject(W_Root):
    tp = FakeSpace.w_slice
    def __init__(self, start, stop, step):
        self.start = start
        self.stop = stop
        self.step = step

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
        return "%r = %r" % (self.name, self.expr)

class ArrayAssignment(Node):
    def __init__(self, name, index, expr):
        self.name = name
        self.index = index
        self.expr = expr

    def execute(self, interp):
        arr = interp.variables[self.name]
        w_index = self.index.execute(interp).eval(arr.start_iter()).wrap(interp.space)
        # cast to int
        if isinstance(w_index, FloatObject):
            w_index = IntObject(int(w_index.floatval))
        w_val = self.expr.execute(interp).eval(arr.start_iter()).wrap(interp.space)
        arr.descr_setitem(interp.space, w_index, w_val)

    def __repr__(self):
        return "%s[%r] = %r" % (self.name, self.index, self.expr)

class Variable(Node):
    def __init__(self, name):
        self.name = name.strip(" ")

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
        if isinstance(self.rhs, SliceConstant):
            w_rhs = self.rhs.wrap(interp.space)
        else:
            w_rhs = self.rhs.execute(interp)
        assert isinstance(w_lhs, BaseArray)
        if self.name == '+':
            w_res = w_lhs.descr_add(interp.space, w_rhs)
        elif self.name == '*':
            w_res = w_lhs.descr_mul(interp.space, w_rhs)
        elif self.name == '-':
            w_res = w_lhs.descr_sub(interp.space, w_rhs)            
        elif self.name == '->':
            if isinstance(w_rhs, Scalar):
                w_rhs = w_rhs.eval(w_rhs.start_iter()).wrap(interp.space)
                assert isinstance(w_rhs, FloatObject)
                w_rhs = IntObject(int(w_rhs.floatval))
            w_res = w_lhs.descr_getitem(interp.space, w_rhs)
        else:
            raise NotImplementedError
        if not isinstance(w_res, BaseArray):
            dtype = interp.space.fromcache(W_Float64Dtype)
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

class SliceConstant(Node):
    def __init__(self, start, stop, step):
        # no negative support for now
        self.start = start
        self.stop = stop
        self.step = step

    def wrap(self, space):
        return SliceObject(self.start, self.stop, self.step)

    def __repr__(self):
        return 'slice(%s,%s,%s)' % (self.start, self.stop, self.step)

class Execute(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return repr(self.expr)

    def execute(self, interp):
        interp.results.append(self.expr.execute(interp))

class FunctionCall(Node):
    def __init__(self, name, args):
        self.name = name.strip(" ")
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
                dtype = interp.space.fromcache(W_Float64Dtype)
            elif isinstance(w_res, BoolObject):
                dtype = interp.space.fromcache(W_BoolDtype)
            else:
                dtype = None
            return scalar_w(interp.space, dtype, w_res)
        else:
            raise WrongFunctionName

_REGEXES = [
    ('-?[\d\.]+', 'number'),
    ('\[', 'array_left'),
    (':', 'colon'),
    ('\w+', 'identifier'),
    ('\]', 'array_right'),
    ('(->)|[\+\-\*\/]', 'operator'),
    ('=', 'assign'),
    (',', 'coma'),
    ('\|', 'pipe'),
    ('\(', 'paren_left'),
    ('\)', 'paren_right'),
]
REGEXES = []

for r, name in _REGEXES:
    REGEXES.append((re.compile(r' *(' + r + ')'), name))
del _REGEXES

class Token(object):
    def __init__(self, name, v):
        self.name = name
        self.v = v

    def __repr__(self):
        return '(%s, %s)' % (self.name, self.v)

empty = Token('', '')

class TokenStack(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.c = 0

    def pop(self):
        token = self.tokens[self.c]
        self.c += 1
        return token

    def get(self, i):
        if self.c + i >= len(self.tokens):
            return empty
        return self.tokens[self.c + i]

    def remaining(self):
        return len(self.tokens) - self.c

    def push(self):
        self.c -= 1

    def __repr__(self):
        return repr(self.tokens[self.c:])

class Parser(object):
    def tokenize(self, line):
        tokens = []
        while True:
            for r, name in REGEXES:
                m = r.match(line)
                if m is not None:
                    g = m.group(0)
                    tokens.append(Token(name, g))
                    line = line[len(g):]
                    if not line:
                        return TokenStack(tokens)
                    break
            else:
                raise TokenizerError(line)

    def parse_number_or_slice(self, tokens):
        start_tok = tokens.pop()
        if start_tok.name == 'colon':
            start = 0
        else:
            if tokens.get(0).name != 'colon':
                return FloatConstant(start_tok.v)
            start = int(start_tok.v)
            tokens.pop()
        if not tokens.get(0).name in ['colon', 'number']:
            stop = -1
            step = 1
        else:
            next = tokens.pop()
            if next.name == 'colon':
                stop = -1
                step = int(tokens.pop().v)
            else:
                stop = int(next.v)
                if tokens.get(0).name == 'colon':
                    tokens.pop()
                    step = int(tokens.pop().v)
                else:
                    step = 1
        return SliceConstant(start, stop, step)
            
        
    def parse_expression(self, tokens):
        stack = []
        while tokens.remaining():
            token = tokens.pop()
            if token.name == 'identifier':
                if tokens.remaining() and tokens.get(0).name == 'paren_left':
                    stack.append(self.parse_function_call(token.v, tokens))
                else:
                    stack.append(Variable(token.v))
            elif token.name == 'array_left':
                stack.append(ArrayConstant(self.parse_array_const(tokens)))
            elif token.name == 'operator':
                stack.append(Variable(token.v))
            elif token.name == 'number' or token.name == 'colon':
                tokens.push()
                stack.append(self.parse_number_or_slice(tokens))
            elif token.name == 'pipe':
                stack.append(RangeConstant(tokens.pop().v))
                end = tokens.pop()
                assert end.name == 'pipe'
            else:
                tokens.push()
                break
        stack.reverse()
        lhs = stack.pop()
        while stack:
            op = stack.pop()
            assert isinstance(op, Variable)
            rhs = stack.pop()
            lhs = Operator(lhs, op.name, rhs)
        return lhs

    def parse_function_call(self, name, tokens):
        args = []
        tokens.pop() # lparen
        while tokens.get(0).name != 'paren_right':
            args.append(self.parse_expression(tokens))
        return FunctionCall(name, args)

    def parse_array_const(self, tokens):
        elems = []
        while True:
            token = tokens.pop()
            if token.name == 'number':
                elems.append(FloatConstant(token.v))
            elif token.name == 'array_left':
                elems.append(ArrayConstant(self.parse_array_const(tokens)))
            else:
                raise BadToken()
            token = tokens.pop()
            if token.name == 'array_right':
                return elems
            assert token.name == 'coma'
        
    def parse_statement(self, tokens):
        if (tokens.get(0).name == 'identifier' and
            tokens.get(1).name == 'assign'):
            lhs = tokens.pop().v
            tokens.pop()
            rhs = self.parse_expression(tokens)
            return Assignment(lhs, rhs)
        elif (tokens.get(0).name == 'identifier' and
              tokens.get(1).name == 'array_left'):
            name = tokens.pop().v
            tokens.pop()
            index = self.parse_expression(tokens)
            tokens.pop()
            tokens.pop()
            return ArrayAssignment(name, index, self.parse_expression(tokens))
        return Execute(self.parse_expression(tokens))

    def parse(self, code):
        statements = []
        for line in code.split("\n"):
            if '#' in line:
                line = line.split('#', 1)[0]
            line = line.strip(" ")
            if line:
                tokens = self.tokenize(line)
                statements.append(self.parse_statement(tokens))
        return Code(statements)

def numpy_compile(code):
    parser = Parser()
    return InterpreterState(parser.parse(code))
