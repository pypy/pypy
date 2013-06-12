import py
import math
from prolog.interpreter.parsing import parse_file, TermBuilder
from prolog.interpreter import helper, term, error
from prolog.interpreter.signature import Signature
from prolog.interpreter.error import UnificationFailed
from rpython.rlib.rarithmetic import intmask, ovfcheck_float_to_int
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib import jit, rarithmetic
from rpython.rlib.rbigint import rbigint

Signature.register_extr_attr("arithmetic")

def eval_arithmetic(engine, obj):
    result = obj.eval_arithmetic(engine)
    return make_int(result)

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


def wrap_builtin_operation(name, num_args):
    fcode = CodeCollector()
    fcode.start_block('def prolog_%s(engine, query):' % name)
    for i in range(num_args):
        fcode.emit('var%s = query.argument_at(%s).eval_arithmetic(engine)' % (i, i))
    if num_args == 1:
        fcode.emit('return var0.arith_%s()' % name)
    elif num_args == 2:
        fcode.emit('return var0.arith_%s(var1)' % name)
    fcode.end_block('def')
    miniglobals = globals().copy()
    exec py.code.Source(fcode.tostring()).compile() in miniglobals
    result = miniglobals['prolog_' + name]
    return result

# remove unneeded parts, use sane names for operations
simple_functions = [
    ("+", 2, "add"),
    ("-", 2, "sub"),
    ("*", 2, "mul"),
    ("/", 2, "div"),
    ("//", 2, "floordiv"),
    ("**", 2, "pow"),
    (">>", 2, "shr"),
    ("<<", 2, "shl"),
    ("\\/", 2, "or"),
    ("/\\", 2, "and"),
    ("xor", 2, "xor"),
    ("mod", 2, "mod"),
    ("\\", 1, "not"),
    ("abs", 1, "abs"),
    ("max", 2, "max"),
    ("min", 2, "min"),
    ("round", 1, "round"),
    ("floor", 1, "floor"), #XXX
    ("ceiling", 1, "ceiling"), #XXX
    ("float_fractional_part", 1, "float_fractional_part"), #XXX
    ("float_integer_part", 1, "float_integer_part")
]

for prolog_name, num_args, name in simple_functions:
    f = wrap_builtin_operation(name, num_args)
    
    signature = Signature.getsignature(prolog_name, num_args)
    signature.set_extra("arithmetic", f)

    for suffix in ["", "_number", "_bigint", "_float"]:
        def not_implemented_func(*args):
            raise NotImplementedError("abstract base class")
        setattr(term.Numeric, "arith_%s%s" % (name, suffix), not_implemented_func)

@jit.elidable_promote('all')
def get_arithmetic_function(signature):
    return signature.get_extra("arithmetic")

def make_int(w_value):
    if isinstance(w_value, term.BigInt):
        try:
            num = w_value.value.toint()
        except OverflowError:
            pass
        else:
            return term.Number(num)
    return w_value


class __extend__(term.Number):
    # ------------------ addition ------------------ 
    def arith_add(self, other):
        return other.arith_add_number(self.num)

    def arith_add_number(self, other_num):
        try:
            res = rarithmetic.ovfcheck(other_num + self.num)
        except OverflowError:
            return self.arith_add_bigint(rbigint.fromint(other_num))
        return term.Number(res)

    def arith_add_bigint(self, other_value):
        return make_int(term.BigInt(other_value.add(rbigint.fromint(self.num))))
    def arith_add_float(self, other_float):
        return term.Float(other_float + float(self.num))

    # ------------------ subtraction ------------------ 
    def arith_sub(self, other):
        return other.arith_sub_number(self.num)

    def arith_sub_number(self, other_num):
        try:
            res = rarithmetic.ovfcheck(other_num - self.num)
        except OverflowError:
            return self.arith_sub_bigint(rbigint.fromint(other_num))
        return term.Number(res)

    def arith_sub_bigint(self, other_value):
        return make_int(term.BigInt(other_value.sub(rbigint.fromint(self.num))))

    def arith_sub_float(self, other_float):
        return term.Float(other_float - float(self.num))

    # ------------------ multiplication ------------------ 
    def arith_mul(self, other):
        return other.arith_mul_number(self.num)

    def arith_mul_number(self, other_num):
        try:
            res = rarithmetic.ovfcheck(other_num * self.num)
        except OverflowError:
            return self.arith_mul_bigint(rbigint.fromint(other_num))
        return term.Number(res)

    def arith_mul_bigint(self, other_value):
        return make_int(term.BigInt(other_value.mul(rbigint.fromint(self.num))))

    def arith_mul_float(self, other_float):
        return term.Float(other_float * float(self.num))

    # ------------------ division ------------------ 
    def arith_div(self, other):
        return other.arith_div_number(self.num)

    def arith_div_number(self, other_num):
        try:
            res = rarithmetic.ovfcheck(other_num / self.num)
        except OverflowError:
            return self.arith_div_bigint(rbigint.fromint(other_num))
        return term.Number(res)

    def arith_div_bigint(self, other_value):
        return make_int(term.BigInt(other_value.div(rbigint.fromint(self.num))))

    def arith_div_float(self, other_float):
        return term.Float(other_float / float(self.num))

    def arith_floordiv(self, other):
        return other.arith_floordiv_number(self.num)

    def arith_floordiv_number(self, other_num):
        try:
            res = rarithmetic.ovfcheck(other_num // self.num)
        except OverflowError:
            return self.arith_floordiv_bigint(rbigint.fromint(other_num))
        return term.Number(res)

    def arith_floordiv_bigint(self, other_value):
        return make_int(term.BigInt(other_value.floordiv(rbigint.fromint(self.num))))

    def arith_floordiv_float(self, other_float):
        error.throw_type_error("integer", other_float)


    # ------------------ power ------------------ 
    def arith_pow(self, other):
        return other.arith_pow_number(self.num)

    def arith_pow_number(self, other_num):
        try:
            res = ovfcheck_float_to_int(math.pow(other_num, self.num))
        except OverflowError:
            return self.arith_pow_bigint(rbigint.fromint(other_num))
        return term.Number(res)

    def arith_pow_bigint(self, other_value):
        return make_int(term.BigInt(other_value.pow(rbigint.fromint(self.num))))

    def arith_pow_float(self, other_float):
        return term.Float(math.pow(other_float, float(self.num)))

    # ------------------ shift right ------------------ 
    def arith_shr(self, other):
        return other.arith_shr_number(self.num)

    def arith_shr_number(self, other_num):
        return term.Number(other_num >> self.num)

    def arith_shr_bigint(self, other_value):
        return make_int(term.BigInt(other_value.rshift(self.num)))

    # ------------------ shift left ------------------ 
    def arith_shl(self, other):
        return other.arith_shl_number(self.num)

    def arith_shl_number(self, other_num):
        return term.Number(intmask(other_num << self.num))

    def arith_shl_bigint(self, other_value):
        return make_int(term.BigInt(other_value.lshift(self.num)))

    # ------------------ or ------------------ 
    def arith_or(self, other):
        return other.arith_or_number(self.num)

    def arith_or_number(self, other_num):
        return term.Number(other_num | self.num)

    def arith_or_bigint(self, other_value):
        return make_int(term.BigInt(rbigint.fromint(self.num).or_(other_value)))

    # ------------------ and ------------------ 
    def arith_and(self, other):
        return other.arith_and_number(self.num)

    def arith_and_number(self, other_num):
        return term.Number(other_num & self.num)

    def arith_and_bigint(self, other_value):
        return make_int(term.BigInt(rbigint.fromint(self.num).and_(other_value)))

    # ------------------ xor ------------------ 
    def arith_xor(self, other):
        return other.arith_xor_number(self.num)

    def arith_xor_number(self, other_num):
        return term.Number(other_num ^ self.num)

    def arith_xor_bigint(self, other_value):
        return make_int(term.BigInt(rbigint.fromint(self.num).xor(other_value)))

    # ------------------ mod ------------------ 
    def arith_mod(self, other):
        return other.arith_mod_number(self.num)

    def arith_mod_number(self, other_num):
        return term.Number(other_num % self.num)

    def arith_mod_bigint(self, other_value):
        return make_int(term.BigInt(other_value.mod(rbigint.fromint(self.num))))

    # ------------------ inversion ------------------
    def arith_not(self):
        return term.Number(~self.num)


    # ------------------ abs ------------------
    def arith_abs(self):
        if self.num >= 0:
            return self
        return term.Number(0).arith_sub(self)

    # ------------------ max ------------------
    def arith_max(self, other):
        return other.arith_max_number(self.num)

    def arith_max_number(self, other_num):
        return term.Number(max(other_num, self.num))

    def arith_max_bigint(self, other_value):
        self_value = rbigint.fromint(self.num)
        if self_value.lt(other_value):
            return make_int(term.BigInt(other_value))
        return make_int(term.BigInt(self_value))

    def arith_max_float(self, other_float):
        return term.Float(max(other_float, float(self.num)))

    # ------------------ min ------------------
    def arith_min(self, other):
        return other.arith_min_number(self.num)

    def arith_min_number(self, other_num):
        return term.Number(min(other_num, self.num))

    def arith_min_bigint(self, other_value):
        self_value = rbigint.fromint(self.num)
        if self_value.lt(other_value):
            return make_int(term.BigInt(self_value))
        return make_int(term.BigInt(other_value))

    def arith_min_float(self, other_float):
        return term.Float(min(other_float, float(self.num)))

    # ------------------ miscellanous ------------------
    def arith_round(self):
        return self

    def arith_floor(self):
        return self

    def arith_ceiling(self):
        return self

    def arith_float_fractional_part(self):
        return term.Number(0)

    def arith_float_integer_part(self):
        return self


class __extend__(term.Float):    
    # ------------------ addition ------------------ 
    def arith_add(self, other):
        return other.arith_add_float(self.floatval)

    def arith_add_number(self, other_num):
        return term.Float(float(other_num) + self.floatval)

    def arith_add_bigint(self, other_value):
        return term.Float(other_value.tofloat() + self.floatval)

    def arith_add_float(self, other_float):
        return term.Float(other_float + self.floatval)

    # ------------------ subtraction ------------------ 
    def arith_sub(self, other):
        return other.arith_sub_float(self.floatval)

    def arith_sub_number(self, other_num):
        return term.Float(float(other_num) - self.floatval)

    def arith_sub_bigint(self, other_value):
        return term.Float(other_value.tofloat() - self.floatval)

    def arith_sub_float(self, other_float):
        return term.Float(other_float - self.floatval)

    # ------------------ multiplication ------------------ 
    def arith_mul(self, other):
        return other.arith_mul_float(self.floatval)

    def arith_mul_number(self, other_num):
        return term.Float(float(other_num) * self.floatval)

    def arith_mul_bigint(self, other_value):
        return term.Float(other_value.tofloat() * self.floatval)

    def arith_mul_float(self, other_float):
        return term.Float(other_float * self.floatval)

    # ------------------ division ------------------ 
    def arith_div(self, other):
        return other.arith_div_float(self.floatval)

    def arith_div_number(self, other_num):
        return term.Float(float(other_num) / self.floatval)

    def arith_div_bigint(self, other_value):
        return term.Float(other_value.tofloat() / self.floatval)

    def arith_div_float(self, other_float):
        return term.Float(other_float / self.floatval)

    def arith_floordiv(self, other_float):
        error.throw_type_error("integer", self)
    def arith_floordiv_number(self, other_num):
        error.throw_type_error("integer", self)
    def arith_floordiv_bigint(self, other_value):
        error.throw_type_error("integer", self)
    def arith_floordiv_float(self, other_float):
        error.throw_type_error("integer", other_float)

    # ------------------ power ------------------ 
    def arith_pow(self, other):
        return other.arith_pow_float(self.floatval)

    def arith_pow_number(self, other_num):
        return term.Float(math.pow(float(other_num), self.floatval))

    def arith_pow_bigint(self, other_value):
        return term.Float(math.pow(other_value.tofloat(), self.floatval))

    def arith_pow_float(self, other_float):
        return term.Float(math.pow(other_float, self.floatval))

    # ------------------ abs ------------------ 
    def arith_abs(self):
        return term.Float(abs(self.floatval))

    # ------------------ max ------------------ 
    def arith_max(self, other):
        return other.arith_max_float(self.floatval)

    def arith_max_number(self, other_num):
        return term.Float(max(float(other_num), self.floatval))

    def arith_max_bigint(self, other_value):
        return term.Float(max(other_value.tofloat(), self.floatval))

    def arith_max_float(self, other_float):
        return term.Float(max(other_float, self.floatval))
    
    # ------------------ min ------------------ 
    def arith_min(self, other):
        return other.arith_min_float(self.floatval)

    def arith_min_number(self, other_num):
        return term.Float(min(float(other_num), self.floatval))

    def arith_min_bigint(self, other_value):
        return term.Float(min(other_value.tofloat(), self.floatval))

    def arith_min_float(self, other_float):
        return term.Float(min(other_float, self.floatval))

    # ------------------ miscellanous ------------------
    def arith_round(self):
        fval = self.floatval
        if fval >= 0:
            factor = 1
        else:
            factor = -1

        fval = fval * factor
        try:
            val = ovfcheck_float_to_int(math.floor(fval + 0.5) * factor)
        except OverflowError:
            return term.BigInt(rbigint.fromfloat(math.floor(self.floatval + 0.5) * factor))
        return term.Number(val)

    def arith_floor(self):
        try:
            val = ovfcheck_float_to_int(math.floor(self.floatval))
        except OverflowError:
            return term.BigInt(rbigint.fromfloat(math.floor(self.floatval)))
        return term.Number(val)

    def arith_ceiling(self):
        try:
            val = ovfcheck_float_to_int(math.ceil(self.floatval))
        except OverflowError:
            return term.BigInt(rbigint.fromfloat(math.ceil(self.floatval)))
        return term.Number(val)

    def arith_float_fractional_part(self):
        try:
            val = ovfcheck_float_to_int(self.floatval)
        except OverflowError:
            val = rbigint.fromfloat(self.floatval).tofloat()
        return term.Float(float(self.floatval - val))

    def arith_float_integer_part(self):
        try:
            val = ovfcheck_float_to_int(self.floatval)
        except OverflowError:
            return term.BigInt(rbigint.fromfloat(self.floatval))
        return term.Number(val)


class __extend__(term.BigInt):
    # ------------------ addition ------------------ 
    def arith_add(self, other):
        return other.arith_add_bigint(self.value)

    def arith_add_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).add(self.value)))

    def arith_add_bigint(self, other_value):
        return make_int(term.BigInt(other_value.add(self.value)))

    def arith_add_float(self, other_float):
        return term.Float(other_float + self.value.tofloat())

    # ------------------ subtraction ------------------ 
    def arith_sub(self, other):
        return other.arith_sub_bigint(self.value)

    def arith_sub_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).sub(self.value)))

    def arith_sub_bigint(self, other_value):
        return make_int(term.BigInt(other_value.sub(self.value)))

    def arith_sub_float(self, other_float):
        return term.Float(other_float - self.value.tofloat())

    # ------------------ multiplication ------------------ 
    def arith_mul(self, other):
        return other.arith_mul_bigint(self.value)

    def arith_mul_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).mul(self.value)))

    def arith_mul_bigint(self, other_value):
        return make_int(term.BigInt(other_value.mul(self.value)))

    def arith_mul_float(self, other_float):
        return term.Float(other_float * self.value.tofloat())

    # ------------------ division ------------------ 
    def arith_div(self, other):
        return other.arith_div_bigint(self.value)

    def arith_div_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).div(self.value)))

    def arith_div_bigint(self, other_value):
        return make_int(term.BigInt(other_value.div(self.value)))

    def arith_div_float(self, other_float):
        return term.Float(other_float / self.value.tofloat())

    def arith_floordiv(self, other):
        return other.arith_floordiv_bigint(self.value)

    def arith_floordiv_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).div(self.value)))

    def arith_floordiv_bigint(self, other_value):
        return make_int(term.BigInt(other_value.div(self.value)))

    def arith_floordiv_float(self, other_float):
        error.throw_type_error("integer", other_float)
    # ------------------ power ------------------
    def arith_pow(self, other):
        return other.arith_pow_bigint(self.value)

    def arith_pow_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).pow(self.value)))

    def arith_pow_bigint(self, other_value):
        return make_int(term.BigInt(other_value.pow(self.value)))

    def arith_pow_float(self, other_float):
        return term.Float(math.pow(other_float, self.value.tofloat()))

    # ------------------ shift right ------------------ 
    def arith_shr(self, other):
        return other.arith_shr_bigint(self.value)

    def arith_shr_number(self, other_num):
        try:
            num = self.value.toint()
        except OverflowError:
            # XXX raise a Prolog-level error!
            raise ValueError('Right operand too big')
        return term.Number(other_num >> num)

    def arith_shr_bigint(self, other_value):
        try:
            num = self.value.toint()
        except OverflowError:
            # XXX raise a Prolog-level error!
            raise ValueError('Right operand too big')
        return make_int(term.BigInt(other_value.rshift(num)))

    # ------------------ shift left ------------------ 
    def arith_shl(self, other):
        return other.arith_shl_bigint(self.value)

    def arith_shl_number(self, other_num):
        try:
            num = self.value.toint()
        except OverflowError:
            # XXX raise a Prolog-level error!
            raise ValueError('Right operand too big')
        else:
            return make_int(term.BigInt(rbigint.fromint(other_num).lshift(num)))

    def arith_shl_bigint(self, other_value):
        try:
            num = self.value.toint()
        except OverflowError:
            # XXX raise a Prolog-level error!
            raise ValueError('Right operand too big')
        return make_int(term.BigInt(other_value.lshift(num)))

    # ------------------ or ------------------ 
    def arith_or(self, other):
        return other.arith_or_bigint(self.value)

    def arith_or_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).or_(self.value)))

    def arith_or_bigint(self, other_value):
        return make_int(term.BigInt(other_value.or_(self.value)))

    # ------------------ and ------------------ 
    def arith_and(self, other):
        return other.arith_and_bigint(self.value)

    def arith_and_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).and_(self.value)))

    def arith_and_bigint(self, other_value):
        return make_int(term.BigInt(other_value.and_(self.value)))

    # ------------------ xor ------------------ 
    def arith_xor(self, other):
        return other.arith_xor_bigint(self.value)

    def arith_xor_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).xor(self.value)))

    def arith_xor_bigint(self, other_value):
        return make_int(term.BigInt(other_value.xor(self.value)))

    # ------------------ mod ------------------ 
    def arith_mod(self, other):
        return other.arith_mod_bigint(self.value)

    def arith_mod_number(self, other_num):
        return make_int(term.BigInt(rbigint.fromint(other_num).mod(self.value)))

    def arith_mod_bigint(self, other_value):
        return make_int(term.BigInt(other_value.mod(self.value)))

    # ------------------ inversion ------------------ 
    def arith_not(self):
        return make_int(term.BigInt(self.value.invert()))


    # ------------------ abs ------------------
    def arith_abs(self):
        return make_int(term.BigInt(self.value.abs()))


    # ------------------ max ------------------
    def arith_max(self, other):
        return other.arith_max_bigint(self.value)

    def arith_max_number(self, other_num):
        other_value = rbigint.fromint(other_num)
        if other_value.lt(self.value):
            return make_int(term.BigInt(self.value))
        return make_int(term.BigInt(other_value))

    def arith_max_bigint(self, other_value):
        if other_value.lt(self.value):
            return make_int(term.BigInt(self.value))
        return make_int(term.BigInt(other_value))

    def arith_max_float(self, other_float):
        return term.Float(max(other_float, self.value.tofloat()))

    # ------------------ min ------------------
    def arith_min(self, other):
        return other.arith_min_bigint(self.value)

    def arith_min_number(self, other_num):
        other_value = rbigint.fromint(other_num)
        if other_value.lt(self.value):
            return make_int(term.BigInt(other_value))
        return make_int(term.BigInt(self.value))

    def arith_min_bigint(self, other_value):
        if other_value.lt(self.value):
            return make_int(term.BigInt(other_value))
        return make_int(term.BigInt(self.value))

    def arith_min_float(self, other_float):
        return term.Float(min(other_float, self.value.tofloat()))

    # ------------------ miscellanous ------------------
    def arith_round(self):
        return make_int(self)

    def arith_floor(self):
        return make_int(self)

    def arith_ceiling(self):
        return make_int(self)

    def arith_arith_fractional_part(self):
        return term.Number(0)

    def arith_arith_integer_part(self):
        return make_int(self)
