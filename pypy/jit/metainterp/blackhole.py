from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rtimer import read_timestamp
from pypy.rlib.rarithmetic import intmask, LONG_BIT, r_uint, ovfcheck
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import debug_start, debug_stop
from pypy.rlib.debug import make_sure_not_resized
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLException
from pypy.jit.codewriter.jitcode import JitCode, SwitchDictDescr
from pypy.jit.codewriter import heaptracker, longlong
from pypy.jit.metainterp.jitexc import JitException, get_llexception, reraise
from pypy.jit.metainterp.compile import ResumeAtPositionDescr

def arguments(*argtypes, **kwds):
    resulttype = kwds.pop('returns', None)
    assert not kwds
    def decorate(function):
        function.argtypes = argtypes
        function.resulttype = resulttype
        return function
    return decorate

class LeaveFrame(JitException):
    pass

class MissingValue(object):
    "NOT_RPYTHON"

def signedord(c):
    value = ord(c)
    value = intmask(value << (LONG_BIT-8)) >> (LONG_BIT-8)
    return value

NULL = lltype.nullptr(llmemory.GCREF.TO)

# ____________________________________________________________


class BlackholeInterpBuilder(object):
    verbose = True

    def __init__(self, codewriter, metainterp_sd=None):
        self.cpu = codewriter.cpu
        asm = codewriter.assembler
        self.setup_insns(asm.insns)
        self.setup_descrs(asm.descrs)
        self.metainterp_sd = metainterp_sd
        self.num_interpreters = 0
        self._freeze_()

    def _freeze_(self):
        self.blackholeinterps = []
        return False

    def setup_insns(self, insns):
        assert len(insns) <= 256, "too many instructions!"
        self._insns = [None] * len(insns)
        for key, value in insns.items():
            assert self._insns[value] is None
            self._insns[value] = key
        self.op_catch_exception = insns.get('catch_exception/L', -1)
        #
        all_funcs = []
        for key in self._insns:
            assert key.count('/') == 1, "bad key: %r" % (key,)
            name, argcodes = key.split('/')
            all_funcs.append(self._get_method(name, argcodes))
        all_funcs = unrolling_iterable(enumerate(all_funcs))
        #
        def dispatch_loop(self, code, position):
            assert position >= 0
            while True:
                if (not we_are_translated()
                    and self.jitcode._startpoints is not None):
                    assert position in self.jitcode._startpoints, (
                        "the current position %d is in the middle of "
                        "an instruction!" % position)
                opcode = ord(code[position])
                position += 1
                for i, func in all_funcs:
                    if opcode == i:
                        position = func(self, code, position)
                        break
                else:
                    raise AssertionError("bad opcode")
        dispatch_loop._dont_inline_ = True
        self.dispatch_loop = dispatch_loop

    def setup_descrs(self, descrs):
        self.descrs = descrs

    def _get_method(self, name, argcodes):
        #
        def handler(self, code, position):
            assert position >= 0
            args = ()
            next_argcode = 0
            for argtype in argtypes:
                if argtype == 'i' or argtype == 'r' or argtype == 'f':
                    # if argtype is 'i', then argcode can be 'i' or 'c';
                    # 'c' stands for a single signed byte that gives the
                    # value of a small constant.
                    argcode = argcodes[next_argcode]
                    next_argcode = next_argcode + 1
                    if argcode == 'i':
                        assert argtype == 'i'
                        value = self.registers_i[ord(code[position])]
                    elif argcode == 'c':
                        assert argtype == 'i'
                        value = signedord(code[position])
                    elif argcode == 'r':
                        assert argtype == 'r'
                        value = self.registers_r[ord(code[position])]
                    elif argcode == 'f':
                        assert argtype == 'f'
                        value = self.registers_f[ord(code[position])]
                    else:
                        raise AssertionError("bad argcode")
                    position += 1
                elif argtype == 'L':
                    # argcode should be 'L' too
                    assert argcodes[next_argcode] == 'L'
                    next_argcode = next_argcode + 1
                    value = ord(code[position]) | (ord(code[position+1])<<8)
                    position += 2
                elif argtype == 'I' or argtype == 'R' or argtype == 'F':
                    assert argcodes[next_argcode] == argtype
                    next_argcode = next_argcode + 1
                    length = ord(code[position])
                    position += 1
                    value = []
                    for i in range(length):
                        index = ord(code[position+i])
                        if   argtype == 'I': reg = self.registers_i[index]
                        elif argtype == 'R': reg = self.registers_r[index]
                        elif argtype == 'F': reg = self.registers_f[index]
                        if not we_are_translated():
                            assert not isinstance(reg, MissingValue), (
                                name, self.jitcode, position)
                        value.append(reg)
                    make_sure_not_resized(value)
                    position += length
                elif argtype == 'self':
                    value = self
                elif argtype == 'cpu':
                    value = self.cpu
                elif argtype == 'pc':
                    value = position
                elif argtype == 'd' or argtype == 'j':
                    assert argcodes[next_argcode] == 'd'
                    next_argcode = next_argcode + 1
                    index = ord(code[position]) | (ord(code[position+1])<<8)
                    value = self.descrs[index]
                    if argtype == 'j':
                        assert isinstance(value, JitCode)
                    position += 2
                else:
                    raise AssertionError("bad argtype: %r" % (argtype,))
                if not we_are_translated():
                    assert not isinstance(value, MissingValue), (
                        name, self.jitcode, position)
                args = args + (value,)

            if verbose and not we_are_translated():
                print '\tbh:', name, list(args),

            # call the method bhimpl_xxx()
            try:
                result = unboundmethod(*args)
            except Exception, e:
                if verbose and not we_are_translated():
                    print '-> %s!' % (e.__class__.__name__,)
                if resulttype == 'i' or resulttype == 'r' or resulttype == 'f':
                    position += 1
                self.position = position
                raise

            if verbose and not we_are_translated():
                if result is None:
                    print
                else:
                    print '->', result

            if resulttype == 'i':
                # argcode should be 'i' too
                assert argcodes[next_argcode] == '>'
                assert argcodes[next_argcode + 1] == 'i'
                next_argcode = next_argcode + 2
                if lltype.typeOf(result) is lltype.Bool:
                    result = int(result)
                assert lltype.typeOf(result) is lltype.Signed
                self.registers_i[ord(code[position])] = result
                position += 1
            elif resulttype == 'r':
                # argcode should be 'r' too
                assert argcodes[next_argcode] == '>'
                assert argcodes[next_argcode + 1] == 'r'
                next_argcode = next_argcode + 2
                assert lltype.typeOf(result) == llmemory.GCREF
                self.registers_r[ord(code[position])] = result
                position += 1
            elif resulttype == 'f':
                # argcode should be 'f' too
                assert argcodes[next_argcode] == '>'
                assert argcodes[next_argcode + 1] == 'f'
                next_argcode = next_argcode + 2
                assert lltype.typeOf(result) is longlong.FLOATSTORAGE
                self.registers_f[ord(code[position])] = result
                position += 1
            elif resulttype == 'L':
                assert result >= 0
                position = result
            else:
                assert resulttype is None
                assert result is None
            assert next_argcode == len(argcodes)
            return position
        #
        # Get the bhimpl_xxx method.  If we get an AttributeError here,
        # it means that either the implementation is missing, or that it
        # should not appear here at all but instead be transformed away
        # by codewriter/jtransform.py.
        unboundmethod = getattr(BlackholeInterpreter, 'bhimpl_' + name).im_func
        verbose = self.verbose
        argtypes = unrolling_iterable(unboundmethod.argtypes)
        resulttype = unboundmethod.resulttype
        handler.func_name = 'handler_' + name
        return handler

    def acquire_interp(self):
        if len(self.blackholeinterps) > 0:
            return self.blackholeinterps.pop()
        else:
            self.num_interpreters += 1
            return BlackholeInterpreter(self, self.num_interpreters)

    def release_interp(self, interp):
        interp.cleanup_registers()
        self.blackholeinterps.append(interp)

def check_shift_count(b):
    if not we_are_translated():
        if b < 0 or b >= LONG_BIT:
            raise ValueError("Shift count, %d,  not in valid range, 0 .. %d." % (b, LONG_BIT-1))

class BlackholeInterpreter(object):

    def __init__(self, builder, count_interpreter):
        self.builder            = builder
        self.cpu                = builder.cpu
        self.dispatch_loop      = builder.dispatch_loop
        self.descrs             = builder.descrs
        self.op_catch_exception = builder.op_catch_exception
        self.count_interpreter  = count_interpreter
        #
        if we_are_translated():
            default_i = 0
            default_r = NULL
            default_f = longlong.ZEROF
        else:
            default_i = MissingValue()
            default_r = MissingValue()
            default_f = MissingValue()
        self.registers_i = [default_i] * 256
        self.registers_r = [default_r] * 256
        self.registers_f = [default_f] * 256
        self.tmpreg_i = default_i
        self.tmpreg_r = default_r
        self.tmpreg_f = default_f
        self.jitcode = None

    def __repr__(self):
        return '<BHInterp #%d>' % self.count_interpreter

    def setposition(self, jitcode, position):
        if jitcode is not self.jitcode:
            # the real performance impact of the following code is unclear,
            # but it should be minimized by the fact that a given
            # BlackholeInterpreter instance is likely to be reused with
            # exactly the same jitcode, so we don't do the copy again.
            self.copy_constants(self.registers_i, jitcode.constants_i)
            self.copy_constants(self.registers_r, jitcode.constants_r)
            self.copy_constants(self.registers_f, jitcode.constants_f)
        self.jitcode = jitcode
        self.position = position

    def setarg_i(self, index, value):
        assert lltype.typeOf(value) is lltype.Signed
        self.registers_i[index] = value

    def setarg_r(self, index, value):
        assert lltype.typeOf(value) == llmemory.GCREF
        self.registers_r[index] = value

    def setarg_f(self, index, value):
        assert lltype.typeOf(value) is longlong.FLOATSTORAGE
        self.registers_f[index] = value

    def run(self):
        while True:
            try:
                self.dispatch_loop(self, self.jitcode.code, self.position)
            except LeaveFrame:
                break
            except JitException:
                raise     # go through
            except Exception, e:
                lle = get_llexception(self.cpu, e)
                self.handle_exception_in_frame(lle)

    def get_tmpreg_i(self):
        return self.tmpreg_i

    def get_tmpreg_r(self):
        result = self.tmpreg_r
        if we_are_translated():
            self.tmpreg_r = NULL
        else:
            del self.tmpreg_r
        return result

    def get_tmpreg_f(self):
        return self.tmpreg_f

    def _final_result_anytype(self):
        "NOT_RPYTHON"
        if self._return_type == 'i': return self.get_tmpreg_i()
        if self._return_type == 'r': return self.get_tmpreg_r()
        if self._return_type == 'f': return self.get_tmpreg_f()
        if self._return_type == 'v': return None
        raise ValueError(self._return_type)

    def cleanup_registers(self):
        # To avoid keeping references alive, this cleans up the registers_r.
        # It does not clear the references set by copy_constants(), but
        # these are all prebuilt constants anyway.
        for i in range(self.jitcode.num_regs_r()):
            self.registers_r[i] = NULL
        self.exception_last_value = lltype.nullptr(rclass.OBJECT)

    def get_current_position_info(self):
        return self.jitcode.get_live_vars_info(self.position)

    def handle_exception_in_frame(self, e):
        # This frame raises an exception.  First try to see if
        # the exception is handled in the frame itself.
        code = self.jitcode.code
        position = self.position
        if position < len(code):
            opcode = ord(code[position])
            if opcode == self.op_catch_exception:
                # store the exception on 'self', and jump to the handler
                self.exception_last_value = e
                target = ord(code[position+1]) | (ord(code[position+2])<<8)
                self.position = target
                return
        # no 'catch_exception' insn follows: just reraise
        reraise(e)

    def copy_constants(self, registers, constants):
        """Copy jitcode.constants[0] to registers[255],
                jitcode.constants[1] to registers[254],
                jitcode.constants[2] to registers[253], etc."""
        make_sure_not_resized(registers)
        make_sure_not_resized(constants)
        i = len(constants) - 1
        while i >= 0:
            j = 255 - i
            assert j >= 0
            registers[j] = constants[i]
            i -= 1
    copy_constants._annspecialcase_ = 'specialize:arglistitemtype(1)'

    # ----------

    @arguments("i", "i", returns="i")
    def bhimpl_int_add(a, b):
        return intmask(a + b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_sub(a, b):
        return intmask(a - b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_mul(a, b):
        return intmask(a * b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_add_ovf(a, b):
        return ovfcheck(a + b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_sub_ovf(a, b):
        return ovfcheck(a - b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_mul_ovf(a, b):
        return ovfcheck(a * b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_floordiv(a, b):
        return llop.int_floordiv(lltype.Signed, a, b)

    @arguments("i", "i", returns="i")
    def bhimpl_uint_floordiv(a, b):
        c = llop.uint_floordiv(lltype.Unsigned, r_uint(a), r_uint(b))
        return intmask(c)

    @arguments("i", "i", returns="i")
    def bhimpl_int_mod(a, b):
        return llop.int_mod(lltype.Signed, a, b)

    @arguments("i", "i", returns="i")
    def bhimpl_int_and(a, b):
        return a & b

    @arguments("i", "i", returns="i")
    def bhimpl_int_or(a, b):
        return a | b

    @arguments("i", "i", returns="i")
    def bhimpl_int_xor(a, b):
        return a ^ b

    @arguments("i", "i", returns="i")
    def bhimpl_int_rshift(a, b):
        check_shift_count(b)
        return a >> b

    @arguments("i", "i", returns="i")
    def bhimpl_int_lshift(a, b):
        check_shift_count(b)
        return intmask(a << b)

    @arguments("i", "i", returns="i")
    def bhimpl_uint_rshift(a, b):
        check_shift_count(b)
        c = r_uint(a) >> r_uint(b)
        return intmask(c)

    @arguments("i", returns="i")
    def bhimpl_int_neg(a):
        return intmask(-a)

    @arguments("i", returns="i")
    def bhimpl_int_invert(a):
        return intmask(~a)

    @arguments("i", "i", returns="i")
    def bhimpl_int_lt(a, b):
        return a < b
    @arguments("i", "i", returns="i")
    def bhimpl_int_le(a, b):
        return a <= b
    @arguments("i", "i", returns="i")
    def bhimpl_int_eq(a, b):
        return a == b
    @arguments("i", "i", returns="i")
    def bhimpl_int_ne(a, b):
        return a != b
    @arguments("i", "i", returns="i")
    def bhimpl_int_gt(a, b):
        return a > b
    @arguments("i", "i", returns="i")
    def bhimpl_int_ge(a, b):
        return a >= b
    @arguments("i", returns="i")
    def bhimpl_int_is_zero(a):
        return not a
    @arguments("i", returns="i")
    def bhimpl_int_is_true(a):
        return bool(a)
    @arguments("i", "i", "i", returns="i")
    def bhimpl_int_between(a, b, c):
        return a <= b < c

    @arguments("i", "i", returns="i")
    def bhimpl_uint_lt(a, b):
        return r_uint(a) < r_uint(b)
    @arguments("i", "i", returns="i")
    def bhimpl_uint_le(a, b):
        return r_uint(a) <= r_uint(b)
    @arguments("i", "i", returns="i")
    def bhimpl_uint_gt(a, b):
        return r_uint(a) > r_uint(b)
    @arguments("i", "i", returns="i")
    def bhimpl_uint_ge(a, b):
        return r_uint(a) >= r_uint(b)

    @arguments("r", "r", returns="i")
    def bhimpl_ptr_eq(a, b):
        return a == b
    @arguments("r", "r", returns="i")
    def bhimpl_ptr_ne(a, b):
        return a != b
    @arguments("r", returns="i")
    def bhimpl_ptr_iszero(a):
        return not a
    @arguments("r", returns="i")
    def bhimpl_ptr_nonzero(a):
        return bool(a)
    @arguments("r", returns="r")
    def bhimpl_cast_opaque_ptr(a):
        return a

    @arguments("i", returns="i")
    def bhimpl_int_copy(a):
        return a
    @arguments("r", returns="r")
    def bhimpl_ref_copy(a):
        return a
    @arguments("f", returns="f")
    def bhimpl_float_copy(a):
        return a

    @arguments("i")
    def bhimpl_int_guard_value(a):
        pass
    @arguments("r")
    def bhimpl_ref_guard_value(a):
        pass
    @arguments("f")
    def bhimpl_float_guard_value(a):
        pass

    @arguments("self", "i")
    def bhimpl_int_push(self, a):
        self.tmpreg_i = a
    @arguments("self", "r")
    def bhimpl_ref_push(self, a):
        self.tmpreg_r = a
    @arguments("self", "f")
    def bhimpl_float_push(self, a):
        self.tmpreg_f = a

    @arguments("self", returns="i")
    def bhimpl_int_pop(self):
        return self.get_tmpreg_i()
    @arguments("self", returns="r")
    def bhimpl_ref_pop(self):
        return self.get_tmpreg_r()
    @arguments("self", returns="f")
    def bhimpl_float_pop(self):
        return self.get_tmpreg_f()

    # ----------
    # float operations

    @arguments("f", returns="f")
    def bhimpl_float_neg(a):
        a = longlong.getrealfloat(a)
        x = -a
        return longlong.getfloatstorage(x)
    @arguments("f", returns="f")
    def bhimpl_float_abs(a):
        a = longlong.getrealfloat(a)
        x = abs(a)
        return longlong.getfloatstorage(x)

    @arguments("f", "f", returns="f")
    def bhimpl_float_add(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        x = a + b
        return longlong.getfloatstorage(x)
    @arguments("f", "f", returns="f")
    def bhimpl_float_sub(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        x = a - b
        return longlong.getfloatstorage(x)
    @arguments("f", "f", returns="f")
    def bhimpl_float_mul(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        x = a * b
        return longlong.getfloatstorage(x)
    @arguments("f", "f", returns="f")
    def bhimpl_float_truediv(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        x = a / b
        return longlong.getfloatstorage(x)

    @arguments("f", "f", returns="i")
    def bhimpl_float_lt(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        return a < b
    @arguments("f", "f", returns="i")
    def bhimpl_float_le(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        return a <= b
    @arguments("f", "f", returns="i")
    def bhimpl_float_eq(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        return a == b
    @arguments("f", "f", returns="i")
    def bhimpl_float_ne(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        return a != b
    @arguments("f", "f", returns="i")
    def bhimpl_float_gt(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        return a > b
    @arguments("f", "f", returns="i")
    def bhimpl_float_ge(a, b):
        a = longlong.getrealfloat(a)
        b = longlong.getrealfloat(b)
        return a >= b

    @arguments("f", returns="i")
    def bhimpl_cast_float_to_int(a):
        a = longlong.getrealfloat(a)
        # note: we need to call int() twice to care for the fact that
        # int(-2147483648.0) returns a long :-(
        return int(int(a))

    @arguments("i", returns="f")
    def bhimpl_cast_int_to_float(a):
        x = float(a)
        return longlong.getfloatstorage(x)

    @arguments("f", returns="i")
    def bhimpl_cast_float_to_singlefloat(a):
        from pypy.rlib.rarithmetic import r_singlefloat
        a = longlong.getrealfloat(a)
        a = r_singlefloat(a)
        return longlong.singlefloat2int(a)

    @arguments("i", returns="f")
    def bhimpl_cast_singlefloat_to_float(a):
        a = longlong.int2singlefloat(a)
        a = float(a)
        return longlong.getfloatstorage(a)

    # ----------
    # control flow operations

    @arguments("self", "i")
    def bhimpl_int_return(self, a):
        self.tmpreg_i = a
        self._return_type = 'i'
        raise LeaveFrame

    @arguments("self", "r")
    def bhimpl_ref_return(self, a):
        self.tmpreg_r = a
        self._return_type = 'r'
        raise LeaveFrame

    @arguments("self", "f")
    def bhimpl_float_return(self, a):
        self.tmpreg_f = a
        self._return_type = 'f'
        raise LeaveFrame

    @arguments("self")
    def bhimpl_void_return(self):
        self._return_type = 'v'
        raise LeaveFrame

    @arguments("i", "L", "pc", returns="L")
    def bhimpl_goto_if_not(a, target, pc):
        if a:
            return pc
        else:
            return target

    @arguments("i", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_lt(a, b, target, pc):
        if a < b:
            return pc
        else:
            return target

    @arguments("i", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_le(a, b, target, pc):
        if a <= b:
            return pc
        else:
            return target

    @arguments("i", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_eq(a, b, target, pc):
        if a == b:
            return pc
        else:
            return target

    @arguments("i", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_ne(a, b, target, pc):
        if a != b:
            return pc
        else:
            return target

    @arguments("i", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_gt(a, b, target, pc):
        if a > b:
            return pc
        else:
            return target

    @arguments("i", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_ge(a, b, target, pc):
        if a >= b:
            return pc
        else:
            return target

    bhimpl_goto_if_not_int_is_true = bhimpl_goto_if_not

    @arguments("i", "L", "pc", returns="L")
    def bhimpl_goto_if_not_int_is_zero(a, target, pc):
        if not a:
            return pc
        else:
            return target

    @arguments("r", "r", "L", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_eq(a, b, target, pc):
        if a == b:
            return pc
        else:
            return target

    @arguments("r", "r", "L", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_ne(a, b, target, pc):
        if a != b:
            return pc
        else:
            return target

    @arguments("r", "L", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_iszero(a, target, pc):
        if not a:
            return pc
        else:
            return target

    @arguments("r", "L", "pc", returns="L")
    def bhimpl_goto_if_not_ptr_nonzero(a, target, pc):
        if a:
            return pc
        else:
            return target

    @arguments("L", returns="L")
    def bhimpl_goto(target):
        return target

    @arguments("i", "d", "pc", returns="L")
    def bhimpl_switch(switchvalue, switchdict, pc):
        assert isinstance(switchdict, SwitchDictDescr)
        try:
            return switchdict.dict[switchvalue]
        except KeyError:
            return pc

    @arguments()
    def bhimpl_unreachable():
        raise AssertionError("unreachable")

    # ----------
    # exception handling operations

    @arguments("L")
    def bhimpl_catch_exception(target):
        """This is a no-op when run normally.  When an exception occurs
        and the instruction that raised is immediately followed by a
        catch_exception, then the code in handle_exception_in_frame()
        will capture the exception and jump to 'target'."""

    @arguments("self", "i", "L", "pc", returns="L")
    def bhimpl_goto_if_exception_mismatch(self, vtable, target, pc):
        adr = heaptracker.int2adr(vtable)
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        real_instance = self.exception_last_value
        assert real_instance
        if rclass.ll_issubclass(real_instance.typeptr, bounding_class):
            return pc
        else:
            return target

    @arguments("self", returns="i")
    def bhimpl_last_exception(self):
        real_instance = self.exception_last_value
        assert real_instance
        adr = llmemory.cast_ptr_to_adr(real_instance.typeptr)
        return heaptracker.adr2int(adr)

    @arguments("self", returns="r")
    def bhimpl_last_exc_value(self):
        real_instance = self.exception_last_value
        assert real_instance
        return lltype.cast_opaque_ptr(llmemory.GCREF, real_instance)

    @arguments("self", "r")
    def bhimpl_raise(self, excvalue):
        e = lltype.cast_opaque_ptr(rclass.OBJECTPTR, excvalue)
        assert e
        reraise(e)

    @arguments("self")
    def bhimpl_reraise(self):
        e = self.exception_last_value
        assert e
        reraise(e)

    @arguments("r")
    def bhimpl_debug_fatalerror(msg):
        llop.debug_fatalerror(lltype.Void, msg)

    @arguments("r", "i", "i", "i", "i")
    def bhimpl_jit_debug(string, arg1=0, arg2=0, arg3=0, arg4=0):
        pass

    @arguments("i")
    def bhimpl_int_assert_green(x):
        pass
    @arguments("r")
    def bhimpl_ref_assert_green(x):
        pass
    @arguments("f")
    def bhimpl_float_assert_green(x):
        pass

    @arguments(returns="i")
    def bhimpl_current_trace_length():
        return -1

    @arguments("i", returns="i")
    def bhimpl_int_isconstant(x):
        return False

    @arguments("r", returns="i")
    def bhimpl_ref_isconstant(x):
        return False

    # ----------
    # the main hints and recursive calls

    @arguments("i")
    def bhimpl_loop_header(jdindex):
        pass

    @arguments("self", "i", "I", "R", "F", "I", "R", "F")
    def bhimpl_jit_merge_point(self, jdindex, *args):
        if self.nextblackholeinterp is None:    # we are the last level
            CRN = self.builder.metainterp_sd.ContinueRunningNormally
            raise CRN(*args)
            # Note that the case above is an optimization: the case
            # below would work too.  But it keeps unnecessary stuff on
            # the stack; the solution above first gets rid of the blackhole
            # interpreter completely.
        else:
            # This occurs when we reach 'jit_merge_point' in the portal
            # function called by recursion.  In this case, we can directly
            # call the interpreter main loop from here, and just return its
            # result.
            sd = self.builder.metainterp_sd
            result_type = sd.jitdrivers_sd[jdindex].result_type
            if result_type == 'v':
                self.bhimpl_recursive_call_v(jdindex, *args)
                self.bhimpl_void_return()
            elif result_type == 'i':
                x = self.bhimpl_recursive_call_i(jdindex, *args)
                self.bhimpl_int_return(x)
            elif result_type == 'r':
                x = self.bhimpl_recursive_call_r(jdindex, *args)
                self.bhimpl_ref_return(x)
            elif result_type == 'f':
                x = self.bhimpl_recursive_call_f(jdindex, *args)
                self.bhimpl_float_return(x)
            assert False

    def get_portal_runner(self, jdindex):
        jitdriver_sd = self.builder.metainterp_sd.jitdrivers_sd[jdindex]
        fnptr = heaptracker.adr2int(jitdriver_sd.portal_runner_adr)
        calldescr = jitdriver_sd.mainjitcode.calldescr
        return fnptr, calldescr

    @arguments("self", "i", "I", "R", "F", "I", "R", "F", returns="i")
    def bhimpl_recursive_call_i(self, jdindex, greens_i, greens_r, greens_f,
                                               reds_i,   reds_r,   reds_f):
        fnptr, calldescr = self.get_portal_runner(jdindex)
        return self.cpu.bh_call_i(fnptr, calldescr,
                                  greens_i + reds_i,
                                  greens_r + reds_r,
                                  greens_f + reds_f)
    @arguments("self", "i", "I", "R", "F", "I", "R", "F", returns="r")
    def bhimpl_recursive_call_r(self, jdindex, greens_i, greens_r, greens_f,
                                               reds_i,   reds_r,   reds_f):
        fnptr, calldescr = self.get_portal_runner(jdindex)
        return self.cpu.bh_call_r(fnptr, calldescr,
                                  greens_i + reds_i,
                                  greens_r + reds_r,
                                  greens_f + reds_f)
    @arguments("self", "i", "I", "R", "F", "I", "R", "F", returns="f")
    def bhimpl_recursive_call_f(self, jdindex, greens_i, greens_r, greens_f,
                                               reds_i,   reds_r,   reds_f):
        fnptr, calldescr = self.get_portal_runner(jdindex)
        return self.cpu.bh_call_f(fnptr, calldescr,
                                  greens_i + reds_i,
                                  greens_r + reds_r,
                                  greens_f + reds_f)
    @arguments("self", "i", "I", "R", "F", "I", "R", "F")
    def bhimpl_recursive_call_v(self, jdindex, greens_i, greens_r, greens_f,
                                               reds_i,   reds_r,   reds_f):
        fnptr, calldescr = self.get_portal_runner(jdindex)
        return self.cpu.bh_call_v(fnptr, calldescr,
                                  greens_i + reds_i,
                                  greens_r + reds_r,
                                  greens_f + reds_f)

    # ----------
    # virtual refs

    @arguments("r", returns="r")
    def bhimpl_virtual_ref(a):
        return a

    @arguments("r")
    def bhimpl_virtual_ref_finish(a):
        pass

    # ----------
    # list operations

    @arguments("cpu", "r", "d", "i", returns="i")
    def bhimpl_check_neg_index(cpu, array, arraydescr, index):
        if index < 0:
            index += cpu.bh_arraylen_gc(arraydescr, array)
        return index

    @arguments("cpu", "r", "d", "i", returns="i")
    def bhimpl_check_resizable_neg_index(cpu, lst, lengthdescr, index):
        if index < 0:
            index += cpu.bh_getfield_gc_i(lst, lengthdescr)
        return index

    @arguments("cpu", "d", "d", "d", "d", "i", returns="r")
    def bhimpl_newlist(cpu, structdescr, lengthdescr, itemsdescr,
                       arraydescr, length):
        result = cpu.bh_new(structdescr)
        cpu.bh_setfield_gc_i(result, lengthdescr, length)
        items = cpu.bh_new_array(arraydescr, length)
        cpu.bh_setfield_gc_r(result, itemsdescr, items)
        return result

    @arguments("cpu", "r", "d", "d", "i", returns="i")
    def bhimpl_getlistitem_gc_i(cpu, lst, itemsdescr, arraydescr, index):
        items = cpu.bh_getfield_gc_r(lst, itemsdescr)
        return cpu.bh_getarrayitem_gc_i(arraydescr, items, index)
    @arguments("cpu", "r", "d", "d", "i", returns="r")
    def bhimpl_getlistitem_gc_r(cpu, lst, itemsdescr, arraydescr, index):
        items = cpu.bh_getfield_gc_r(lst, itemsdescr)
        return cpu.bh_getarrayitem_gc_r(arraydescr, items, index)
    @arguments("cpu", "r", "d", "d", "i", returns="f")
    def bhimpl_getlistitem_gc_f(cpu, lst, itemsdescr, arraydescr, index):
        items = cpu.bh_getfield_gc_r(lst, itemsdescr)
        return cpu.bh_getarrayitem_gc_f(arraydescr, items, index)

    @arguments("cpu", "r", "d", "d", "i", "i")
    def bhimpl_setlistitem_gc_i(cpu, lst, itemsdescr, arraydescr, index, nval):
        items = cpu.bh_getfield_gc_r(lst, itemsdescr)
        cpu.bh_setarrayitem_gc_i(arraydescr, items, index, nval)
    @arguments("cpu", "r", "d", "d", "i", "r")
    def bhimpl_setlistitem_gc_r(cpu, lst, itemsdescr, arraydescr, index, nval):
        items = cpu.bh_getfield_gc_r(lst, itemsdescr)
        cpu.bh_setarrayitem_gc_r(arraydescr, items, index, nval)
    @arguments("cpu", "r", "d", "d", "i", "f")
    def bhimpl_setlistitem_gc_f(cpu, lst, itemsdescr, arraydescr, index, nval):
        items = cpu.bh_getfield_gc_r(lst, itemsdescr)
        cpu.bh_setarrayitem_gc_f(arraydescr, items, index, nval)

    # ----------
    # the following operations are directly implemented by the backend

    @arguments("cpu", "i", "d", "R", returns="i")
    def bhimpl_residual_call_r_i(cpu, func, calldescr, args_r):
        return cpu.bh_call_i(func, calldescr, None, args_r, None)
    @arguments("cpu", "i", "d", "R", returns="r")
    def bhimpl_residual_call_r_r(cpu, func, calldescr, args_r):
        return cpu.bh_call_r(func, calldescr, None, args_r, None)
    @arguments("cpu", "i", "d", "R")
    def bhimpl_residual_call_r_v(cpu, func, calldescr, args_r):
        return cpu.bh_call_v(func, calldescr, None, args_r, None)

    @arguments("cpu", "i", "d", "I", "R", returns="i")
    def bhimpl_residual_call_ir_i(cpu, func, calldescr, args_i, args_r):
        return cpu.bh_call_i(func, calldescr, args_i, args_r, None)
    @arguments("cpu", "i", "d", "I", "R", returns="r")
    def bhimpl_residual_call_ir_r(cpu, func, calldescr, args_i, args_r):
        return cpu.bh_call_r(func, calldescr, args_i, args_r, None)
    @arguments("cpu", "i", "d", "I", "R")
    def bhimpl_residual_call_ir_v(cpu, func, calldescr, args_i, args_r):
        return cpu.bh_call_v(func, calldescr, args_i, args_r, None)

    @arguments("cpu", "i", "d", "I", "R", "F", returns="i")
    def bhimpl_residual_call_irf_i(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_i(func, calldescr, args_i, args_r, args_f)
    @arguments("cpu", "i", "d", "I", "R", "F", returns="r")
    def bhimpl_residual_call_irf_r(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_r(func, calldescr, args_i, args_r, args_f)
    @arguments("cpu", "i", "d", "I", "R", "F", returns="f")
    def bhimpl_residual_call_irf_f(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_f(func, calldescr, args_i, args_r, args_f)
    @arguments("cpu", "i", "d", "I", "R", "F")
    def bhimpl_residual_call_irf_v(cpu, func, calldescr,args_i,args_r,args_f):
        return cpu.bh_call_v(func, calldescr, args_i, args_r, args_f)

    @arguments("cpu", "j", "R", returns="i")
    def bhimpl_inline_call_r_i(cpu, jitcode, args_r):
        return cpu.bh_call_i(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             None, args_r, None)
    @arguments("cpu", "j", "R", returns="r")
    def bhimpl_inline_call_r_r(cpu, jitcode, args_r):
        return cpu.bh_call_r(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             None, args_r, None)
    @arguments("cpu", "j", "R")
    def bhimpl_inline_call_r_v(cpu, jitcode, args_r):
        return cpu.bh_call_v(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             None, args_r, None)

    @arguments("cpu", "j", "I", "R", returns="i")
    def bhimpl_inline_call_ir_i(cpu, jitcode, args_i, args_r):
        return cpu.bh_call_i(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, None)
    @arguments("cpu", "j", "I", "R", returns="r")
    def bhimpl_inline_call_ir_r(cpu, jitcode, args_i, args_r):
        return cpu.bh_call_r(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, None)
    @arguments("cpu", "j", "I", "R")
    def bhimpl_inline_call_ir_v(cpu, jitcode, args_i, args_r):
        return cpu.bh_call_v(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, None)

    @arguments("cpu", "j", "I", "R", "F", returns="i")
    def bhimpl_inline_call_irf_i(cpu, jitcode, args_i, args_r, args_f):
        return cpu.bh_call_i(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, args_f)
    @arguments("cpu", "j", "I", "R", "F", returns="r")
    def bhimpl_inline_call_irf_r(cpu, jitcode, args_i, args_r, args_f):
        return cpu.bh_call_r(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, args_f)
    @arguments("cpu", "j", "I", "R", "F", returns="f")
    def bhimpl_inline_call_irf_f(cpu, jitcode, args_i, args_r, args_f):
        return cpu.bh_call_f(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, args_f)
    @arguments("cpu", "j", "I", "R", "F")
    def bhimpl_inline_call_irf_v(cpu, jitcode, args_i, args_r, args_f):
        return cpu.bh_call_v(jitcode.get_fnaddr_as_int(), jitcode.calldescr,
                             args_i, args_r, args_f)

    @arguments("cpu", "d", "i", returns="r")
    def bhimpl_new_array(cpu, arraydescr, length):
        return cpu.bh_new_array(arraydescr, length)

    @arguments("cpu", "r", "d", "i", returns="i")
    def bhimpl_getarrayitem_gc_i(cpu, array, arraydescr, index):
        return cpu.bh_getarrayitem_gc_i(arraydescr, array, index)
    @arguments("cpu", "r", "d", "i", returns="r")
    def bhimpl_getarrayitem_gc_r(cpu, array, arraydescr, index):
        return cpu.bh_getarrayitem_gc_r(arraydescr, array, index)
    @arguments("cpu", "r", "d", "i", returns="f")
    def bhimpl_getarrayitem_gc_f(cpu, array, arraydescr, index):
        return cpu.bh_getarrayitem_gc_f(arraydescr, array, index)

    bhimpl_getarrayitem_gc_pure_i = bhimpl_getarrayitem_gc_i
    bhimpl_getarrayitem_gc_pure_r = bhimpl_getarrayitem_gc_r
    bhimpl_getarrayitem_gc_pure_f = bhimpl_getarrayitem_gc_f

    @arguments("cpu", "i", "d", "i", returns="i")
    def bhimpl_getarrayitem_raw_i(cpu, array, arraydescr, index):
        return cpu.bh_getarrayitem_raw_i(arraydescr, array, index)
    @arguments("cpu", "i", "d", "i", returns="f")
    def bhimpl_getarrayitem_raw_f(cpu, array, arraydescr, index):
        return cpu.bh_getarrayitem_raw_f(arraydescr, array, index)

    @arguments("cpu", "r", "d", "i", "i")
    def bhimpl_setarrayitem_gc_i(cpu, array, arraydescr, index, newvalue):
        cpu.bh_setarrayitem_gc_i(arraydescr, array, index, newvalue)
    @arguments("cpu", "r", "d", "i", "r")
    def bhimpl_setarrayitem_gc_r(cpu, array, arraydescr, index, newvalue):
        cpu.bh_setarrayitem_gc_r(arraydescr, array, index, newvalue)
    @arguments("cpu", "r", "d", "i", "f")
    def bhimpl_setarrayitem_gc_f(cpu, array, arraydescr, index, newvalue):
        cpu.bh_setarrayitem_gc_f(arraydescr, array, index, newvalue)

    @arguments("cpu", "i", "d", "i", "i")
    def bhimpl_setarrayitem_raw_i(cpu, array, arraydescr, index, newvalue):
        cpu.bh_setarrayitem_raw_i(arraydescr, array, index, newvalue)
    @arguments("cpu", "i", "d", "i", "f")
    def bhimpl_setarrayitem_raw_f(cpu, array, arraydescr, index, newvalue):
        cpu.bh_setarrayitem_raw_f(arraydescr, array, index, newvalue)

    # note, there is no 'r' here, since it can't happen

    @arguments("cpu", "r", "d", returns="i")
    def bhimpl_arraylen_gc(cpu, array, arraydescr):
        return cpu.bh_arraylen_gc(arraydescr, array)

    @arguments("cpu", "r", "d", "d", "i", returns="i")
    def bhimpl_getarrayitem_vable_i(cpu, vable, fielddescr, arraydescr, index):
        array = cpu.bh_getfield_gc_r(vable, fielddescr)
        return cpu.bh_getarrayitem_gc_i(arraydescr, array, index)
    @arguments("cpu", "r", "d", "d", "i", returns="r")
    def bhimpl_getarrayitem_vable_r(cpu, vable, fielddescr, arraydescr, index):
        array = cpu.bh_getfield_gc_r(vable, fielddescr)
        return cpu.bh_getarrayitem_gc_r(arraydescr, array, index)
    @arguments("cpu", "r", "d", "d", "i", returns="f")
    def bhimpl_getarrayitem_vable_f(cpu, vable, fielddescr, arraydescr, index):
        array = cpu.bh_getfield_gc_r(vable, fielddescr)
        return cpu.bh_getarrayitem_gc_f(arraydescr, array, index)

    @arguments("cpu", "r", "d", "d", "i", "i")
    def bhimpl_setarrayitem_vable_i(cpu, vable, fdescr, adescr, index, newval):
        array = cpu.bh_getfield_gc_r(vable, fdescr)
        cpu.bh_setarrayitem_gc_i(adescr, array, index, newval)
    @arguments("cpu", "r", "d", "d", "i", "r")
    def bhimpl_setarrayitem_vable_r(cpu, vable, fdescr, adescr, index, newval):
        array = cpu.bh_getfield_gc_r(vable, fdescr)
        cpu.bh_setarrayitem_gc_r(adescr, array, index, newval)
    @arguments("cpu", "r", "d", "d", "i", "f")
    def bhimpl_setarrayitem_vable_f(cpu, vable, fdescr, adescr, index, newval):
        array = cpu.bh_getfield_gc_r(vable, fdescr)
        cpu.bh_setarrayitem_gc_f(adescr, array, index, newval)

    @arguments("cpu", "r", "d", "d", returns="i")
    def bhimpl_arraylen_vable(cpu, vable, fdescr, adescr):
        array = cpu.bh_getfield_gc_r(vable, fdescr)
        return cpu.bh_arraylen_gc(adescr, array)

    @arguments("cpu", "r", "d", returns="i")
    def bhimpl_getfield_gc_i(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_i(struct, fielddescr)
    @arguments("cpu", "r", "d", returns="r")
    def bhimpl_getfield_gc_r(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_r(struct, fielddescr)
    @arguments("cpu", "r", "d", returns="f")
    def bhimpl_getfield_gc_f(cpu, struct, fielddescr):
        return cpu.bh_getfield_gc_f(struct, fielddescr)

    bhimpl_getfield_gc_i_pure = bhimpl_getfield_gc_i
    bhimpl_getfield_gc_r_pure = bhimpl_getfield_gc_r
    bhimpl_getfield_gc_f_pure = bhimpl_getfield_gc_f

    bhimpl_getfield_vable_i = bhimpl_getfield_gc_i
    bhimpl_getfield_vable_r = bhimpl_getfield_gc_r
    bhimpl_getfield_vable_f = bhimpl_getfield_gc_f

    bhimpl_getfield_gc_i_greenfield = bhimpl_getfield_gc_i
    bhimpl_getfield_gc_r_greenfield = bhimpl_getfield_gc_r
    bhimpl_getfield_gc_f_greenfield = bhimpl_getfield_gc_f

    @arguments("cpu", "i", "d", returns="i")
    def bhimpl_getfield_raw_i(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_i(struct, fielddescr)
    @arguments("cpu", "i", "d", returns="r")
    def bhimpl_getfield_raw_r(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_r(struct, fielddescr)
    @arguments("cpu", "i", "d", returns="f")
    def bhimpl_getfield_raw_f(cpu, struct, fielddescr):
        return cpu.bh_getfield_raw_f(struct, fielddescr)

    bhimpl_getfield_raw_i_pure = bhimpl_getfield_raw_i
    bhimpl_getfield_raw_r_pure = bhimpl_getfield_raw_r
    bhimpl_getfield_raw_f_pure = bhimpl_getfield_raw_f

    @arguments("cpu", "r", "d", "i")
    def bhimpl_setfield_gc_i(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_i(struct, fielddescr, newvalue)
    @arguments("cpu", "r", "d", "r")
    def bhimpl_setfield_gc_r(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_r(struct, fielddescr, newvalue)
    @arguments("cpu", "r", "d", "f")
    def bhimpl_setfield_gc_f(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_gc_f(struct, fielddescr, newvalue)

    bhimpl_setfield_vable_i = bhimpl_setfield_gc_i
    bhimpl_setfield_vable_r = bhimpl_setfield_gc_r
    bhimpl_setfield_vable_f = bhimpl_setfield_gc_f

    @arguments("cpu", "i", "d", "i")
    def bhimpl_setfield_raw_i(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_i(struct, fielddescr, newvalue)
    @arguments("cpu", "i", "d", "r")
    def bhimpl_setfield_raw_r(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_r(struct, fielddescr, newvalue)
    @arguments("cpu", "i", "d", "f")
    def bhimpl_setfield_raw_f(cpu, struct, fielddescr, newvalue):
        cpu.bh_setfield_raw_f(struct, fielddescr, newvalue)

    @arguments("r", "d", "d")
    def bhimpl_record_quasiimmut_field(struct, fielddescr, mutatefielddescr):
        pass

    @arguments("cpu", "r", "d")
    def bhimpl_jit_force_quasi_immutable(cpu, struct, mutatefielddescr):
        from pypy.jit.metainterp import quasiimmut
        quasiimmut.do_force_quasi_immutable(cpu, struct, mutatefielddescr)

    @arguments("cpu", "d", returns="r")
    def bhimpl_new(cpu, descr):
        return cpu.bh_new(descr)

    @arguments("cpu", "d", returns="r")
    def bhimpl_new_with_vtable(cpu, descr):
        vtable = heaptracker.descr2vtable(cpu, descr)
        return cpu.bh_new_with_vtable(descr, vtable)

    @arguments("cpu", "r", returns="i")
    def bhimpl_guard_class(cpu, struct):
        return cpu.bh_classof(struct)

    @arguments("cpu", "i", returns="r")
    def bhimpl_newstr(cpu, length):
        return cpu.bh_newstr(length)
    @arguments("cpu", "r", returns="i")
    def bhimpl_strlen(cpu, string):
        return cpu.bh_strlen(string)
    @arguments("cpu", "r", "i", returns="i")
    def bhimpl_strgetitem(cpu, string, index):
        return cpu.bh_strgetitem(string, index)
    @arguments("cpu", "r", "i", "i")
    def bhimpl_strsetitem(cpu, string, index, newchr):
        cpu.bh_strsetitem(string, index, newchr)
    @arguments("cpu", "r", "r", "i", "i", "i")
    def bhimpl_copystrcontent(cpu, src, dst, srcstart, dststart, length):
        cpu.bh_copystrcontent(src, dst, srcstart, dststart, length)

    @arguments("cpu", "i", returns="r")
    def bhimpl_newunicode(cpu, length):
        return cpu.bh_newunicode(length)
    @arguments("cpu", "r", returns="i")
    def bhimpl_unicodelen(cpu, unicode):
        return cpu.bh_unicodelen(unicode)
    @arguments("cpu", "r", "i", returns="i")
    def bhimpl_unicodegetitem(cpu, unicode, index):
        return cpu.bh_unicodegetitem(unicode, index)
    @arguments("cpu", "r", "i", "i")
    def bhimpl_unicodesetitem(cpu, unicode, index, newchr):
        cpu.bh_unicodesetitem(unicode, index, newchr)
    @arguments("cpu", "r", "r", "i", "i", "i")
    def bhimpl_copyunicodecontent(cpu, src, dst, srcstart, dststart, length):
        cpu.bh_copyunicodecontent(src, dst, srcstart, dststart, length)

    @arguments(returns=(longlong.is_64_bit and "i" or "f"))
    def bhimpl_ll_read_timestamp():
        return read_timestamp()

    # ----------
    # helpers to resume running in blackhole mode when a guard failed

    def _resume_mainloop(self, current_exc):
        assert lltype.typeOf(current_exc) == rclass.OBJECTPTR
        try:
            # if there is a current exception, raise it now
            # (it may be caught by a catch_operation in this frame)
            if current_exc:
                self.handle_exception_in_frame(current_exc)
            # unless the call above raised again the exception,
            # we now proceed to interpret the bytecode in this frame
            self.run()
        #
        except JitException, e:
            raise     # go through
        except Exception, e:
            # if we get an exception, return it to the caller frame
            current_exc = get_llexception(self.cpu, e)
            if not self.nextblackholeinterp:
                self._exit_frame_with_exception(current_exc)
            return current_exc
        #
        # pass the frame's return value to the caller
        caller = self.nextblackholeinterp
        if not caller:
            self._done_with_this_frame()
        kind = self._return_type
        if kind == 'i':
            caller._setup_return_value_i(self.get_tmpreg_i())
        elif kind == 'r':
            caller._setup_return_value_r(self.get_tmpreg_r())
        elif kind == 'f':
            caller._setup_return_value_f(self.get_tmpreg_f())
        else:
            assert kind == 'v'
        return lltype.nullptr(rclass.OBJECTPTR.TO)

    def _prepare_resume_from_failure(self, opnum, dont_change_position=False):
        from pypy.jit.metainterp.resoperation import rop
        #
        if opnum == rop.GUARD_TRUE:
            # Produced directly by some goto_if_not_xxx() opcode that did not
            # jump, but which must now jump.  The pc is just after the opcode.
            if not dont_change_position:
                self.position = self.jitcode.follow_jump(self.position)
        #
        elif opnum == rop.GUARD_FALSE:
            # Produced directly by some goto_if_not_xxx() opcode that jumped,
            # but which must no longer jump.  The pc is just after the opcode.
            pass
        #
        elif opnum == rop.GUARD_VALUE or opnum == rop.GUARD_CLASS:
            # Produced by guard_class(), xxx_guard_value(), or a few other
            # opcodes like switch().  The pc is at the start of the opcode
            # (so it will be redone).
            pass
        #
        elif (opnum == rop.GUARD_NONNULL or
              opnum == rop.GUARD_ISNULL or
              opnum == rop.GUARD_NONNULL_CLASS):
            # Produced by goto_if_not_ptr_{non,is}zero().  The pc is at the
            # start of the opcode (so it will be redone); this is needed
            # because of GUARD_NONNULL_CLASS.
            pass
        #
        elif (opnum == rop.GUARD_NO_EXCEPTION or
              opnum == rop.GUARD_EXCEPTION or
              opnum == rop.GUARD_NOT_FORCED):
            return lltype.cast_opaque_ptr(rclass.OBJECTPTR,
                                          self.cpu.grab_exc_value())
        #
        elif opnum == rop.GUARD_NO_OVERFLOW:
            # Produced by int_xxx_ovf().  The pc is just after the opcode.
            # We get here because it did not used to overflow, but now it does.
            return get_llexception(self.cpu, OverflowError())
        #
        elif opnum == rop.GUARD_OVERFLOW:
            # Produced by int_xxx_ovf().  The pc is just after the opcode.
            # We get here because it used to overflow, but now it no longer
            # does.
            pass
        elif opnum == rop.GUARD_NOT_INVALIDATED:
            pass
        else:
            from pypy.jit.metainterp.resoperation import opname
            raise NotImplementedError(opname[opnum])
        return lltype.nullptr(rclass.OBJECTPTR.TO)

    # connect the return of values from the called frame to the
    # 'xxx_call_yyy' instructions from the caller frame
    def _setup_return_value_i(self, result):
        assert lltype.typeOf(result) is lltype.Signed
        self.registers_i[ord(self.jitcode.code[self.position-1])] = result
    def _setup_return_value_r(self, result):
        assert lltype.typeOf(result) == llmemory.GCREF
        self.registers_r[ord(self.jitcode.code[self.position-1])] = result
    def _setup_return_value_f(self, result):
        assert lltype.typeOf(result) is longlong.FLOATSTORAGE
        self.registers_f[ord(self.jitcode.code[self.position-1])] = result

    def _done_with_this_frame(self):
        # rare case: we only get there if the blackhole interps all returned
        # normally (in general we get a ContinueRunningNormally exception).
        sd = self.builder.metainterp_sd
        kind = self._return_type
        if kind == 'v':
            raise sd.DoneWithThisFrameVoid()
        elif kind == 'i':
            raise sd.DoneWithThisFrameInt(self.get_tmpreg_i())
        elif kind == 'r':
            raise sd.DoneWithThisFrameRef(self.cpu, self.get_tmpreg_r())
        elif kind == 'f':
            raise sd.DoneWithThisFrameFloat(self.get_tmpreg_f())
        else:
            assert False

    def _exit_frame_with_exception(self, e):
        sd = self.builder.metainterp_sd
        e = lltype.cast_opaque_ptr(llmemory.GCREF, e)
        raise sd.ExitFrameWithExceptionRef(self.cpu, e)

    def _handle_jitexception_in_portal(self, e):
        # This case is really rare, but can occur if
        # convert_and_run_from_pyjitpl() gets called in this situation:
        #
        #     [function 1]             <---- top BlackholeInterpreter()
        #     [recursive portal jit code]
        #     ...
        #     [bottom portal jit code]   <---- bottom BlackholeInterpreter()
        #
        # and then "function 1" contains a call to "function 2", which
        # calls "can_enter_jit".  The latter can terminate by raising a
        # JitException.  In that case, the JitException is not supposed
        # to fall through the whole chain of BlackholeInterpreters, but
        # be caught and handled just below the level "recursive portal
        # jit code".  The present function is called to handle the case
        # of recursive portal jit codes.
        for jd in self.builder.metainterp_sd.jitdrivers_sd:
            if jd.mainjitcode is self.jitcode:
                break
        else:
            assert 0, "portal jitcode not found??"
        # call the helper in warmspot.py.  It might either raise a
        # regular exception (which should then be propagated outside
        # of 'self', not caught inside), or return (the return value
        # gets stored in nextblackholeinterp).
        jd.handle_jitexc_from_bh(self.nextblackholeinterp, e)

    def _copy_data_from_miframe(self, miframe):
        self.setposition(miframe.jitcode, miframe.pc)
        for i in range(self.jitcode.num_regs_i()):
            box = miframe.registers_i[i]
            if box is not None:
                self.setarg_i(i, box.getint())
        for i in range(self.jitcode.num_regs_r()):
            box = miframe.registers_r[i]
            if box is not None:
                self.setarg_r(i, box.getref_base())
        for i in range(self.jitcode.num_regs_f()):
            box = miframe.registers_f[i]
            if box is not None:
                self.setarg_f(i, box.getfloatstorage())

# ____________________________________________________________

def _run_forever(blackholeinterp, current_exc):
    while True:
        try:
            current_exc = blackholeinterp._resume_mainloop(current_exc)
        except JitException, e:
            blackholeinterp, current_exc = _handle_jitexception(
                blackholeinterp, e)
        blackholeinterp.builder.release_interp(blackholeinterp)
        blackholeinterp = blackholeinterp.nextblackholeinterp

def _handle_jitexception(blackholeinterp, jitexc):
    # See comments in _handle_jitexception_in_portal().
    while not blackholeinterp.jitcode.is_portal:
        blackholeinterp.builder.release_interp(blackholeinterp)
        blackholeinterp = blackholeinterp.nextblackholeinterp
    if blackholeinterp.nextblackholeinterp is None:
        blackholeinterp.builder.release_interp(blackholeinterp)
        raise jitexc     # bottommost entry: go through
    # We have reached a recursive portal level.
    try:
        blackholeinterp._handle_jitexception_in_portal(jitexc)
    except Exception, e:
        # It raised a general exception (it should not be a JitException here).
        lle = get_llexception(blackholeinterp.cpu, e)
    else:
        # It set up the nextblackholeinterp to contain the return value.
        lle = lltype.nullptr(rclass.OBJECTPTR.TO)
    # We will continue to loop in _run_forever() from the parent level.
    return blackholeinterp, lle

def resume_in_blackhole(metainterp_sd, jitdriver_sd, resumedescr,
                        all_virtuals=None):
    from pypy.jit.metainterp.resume import blackhole_from_resumedata
    #debug_start('jit-blackhole')
    metainterp_sd.profiler.start_blackhole()
    blackholeinterp = blackhole_from_resumedata(
        metainterp_sd.blackholeinterpbuilder,
        jitdriver_sd,
        resumedescr,
        all_virtuals)
    if isinstance(resumedescr, ResumeAtPositionDescr):
        dont_change_position = True
    else:
        dont_change_position = False

    current_exc = blackholeinterp._prepare_resume_from_failure(
        resumedescr.guard_opnum, dont_change_position)

    try:
        _run_forever(blackholeinterp, current_exc)
    finally:
        metainterp_sd.profiler.end_blackhole()
        #debug_stop('jit-blackhole')

def convert_and_run_from_pyjitpl(metainterp, raising_exception=False):
    # Get a chain of blackhole interpreters and fill them by copying
    # 'metainterp.framestack'.
    #debug_start('jit-blackhole')
    metainterp_sd = metainterp.staticdata
    metainterp_sd.profiler.start_blackhole()
    nextbh = None
    for frame in metainterp.framestack:
        curbh = metainterp_sd.blackholeinterpbuilder.acquire_interp()
        curbh._copy_data_from_miframe(frame)
        curbh.nextblackholeinterp = nextbh
        nextbh = curbh
    firstbh = nextbh
    #
    if metainterp.last_exc_value_box is not None:
        current_exc = metainterp.last_exc_value_box.getref(rclass.OBJECTPTR)
    else:
        current_exc = lltype.nullptr(rclass.OBJECTPTR.TO)
    if not raising_exception:
        firstbh.exception_last_value = current_exc
        current_exc = lltype.nullptr(rclass.OBJECTPTR.TO)
    #
    try:
        _run_forever(firstbh, current_exc)
    finally:
        metainterp_sd.profiler.end_blackhole()
        #debug_stop('jit-blackhole')
