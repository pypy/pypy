import py, os
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.llvm import llvmjit
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.codegen.i386.rgenop import gc_malloc_fnaddr
from pypy.jit.codegen.llvm.conftest import option
from pypy.jit.codegen.llvm.genvarorconst import count, Var, BoolConst, CharConst,\
    IntConst, UIntConst, FloatConst, AddrConst
from pypy.jit.codegen.llvm.logger import logger, log
from pypy.jit.codegen.llvm.cast import cast
from pypy.jit.codegen.llvm.compatibility import icmp, scmp, ucmp, fcmp,\
    trunc, zext, bitcast, inttoptr, shr_prefix, define, globalprefix,\
    i1, i8, i16, i32, f64


pi8  = i8  + '*'
pi32 = i32 + '*'
u32  = i32

LINENO       = option.lineno
PRINT_SOURCE = option.print_source
PRINT_DEBUG  = option.print_debug


class ParseException(Exception):
    pass


class Block(GenLabel):
    def writecode(self, lines):
        raise NotImplementedError


class BasicBlock(Block):
    """An llvm basic block.
    The source text is stored in the 'asm' list of lines.
    The phinodes dict is updated by branches and is eventually
    turned into 'phi' instructions by the writecode() method.
    """
    def __init__(self, rgenop, label, inputargtypes):
        self.rgenop = rgenop
        self.label = label
        self.inputargs = [Var(type) for type in inputargtypes]
        self.phinodes = {}   # dict {source block: [source vars]}
        self.asm = []
        rgenop.blocklist.append(self)

    def getinputargtypes(self):
        return [var.type for var in self.inputargs]

    def add_incoming_link(self, sourceblock, sourcevars):
        # check the types for debugging
        sourcevartypes = [var.type for var in sourcevars]
        targetvartypes = [var.type for var in self.inputargs]
        if sourcevartypes != targetvartypes:
            logger.dump('assert fails on: sourcevartypes(%s) != targetvartypes(%s)' % (
                sourcevartypes, targetvartypes))
            self.rgenop._dump_partial_lines()
            assert sourcevartypes == targetvartypes

        # Check if the source block jumps to 'self' from multiple
        # positions: in this case we need an intermediate block...
        if sourceblock in self.phinodes:
            tmplabel = count.newlabel()
            tmpblock = BasicBlock(self.rgenop, tmplabel, targetvartypes)
            tmpblock.add_incoming_link(sourceblock, sourcevars)
            sourceblock = tmpblock
            sourcevars = tmpblock.inputargs

        # Add this source for the phi nodes
        self.phinodes[sourceblock] = list(sourcevars)

    def writecode(self, lines):
        lines.append(self.label + ':')
        for i in range(len(self.inputargs)):
            targetvar = self.inputargs[i]
            mergelist = []
            for sourceblock, sourcevars in self.phinodes.iteritems():
                mergelist.append("[%s,%%%s]" % (sourcevars[i].operand2(),
                                                sourceblock.label))
            lines.append(' %s=phi %s %s' % (targetvar.operand2(),
                                            targetvar.type,
                                            ', '.join(mergelist)))
        lines.extend(self.asm)


class PrologueBlock(Block):
    label = 'LP'

    def __init__(self, sigtoken, name):
        self.name = name
        self.sigtoken = sigtoken
        argtypes, restype = sigtoken
        self.inputargs = [Var(type) for type in argtypes]
        # self.startblocklabel set by newgraph()

    def writecode(self, lines):
        argtypes, restype = self.sigtoken
        lines.append('%s %s %s%s(%s){' % (
            define, restype, globalprefix, self.name,
            ','.join([v.operand() for v in self.inputargs])))
        lines.append(self.label + ':')
        lines.append(' br label %%%s' % (self.startblocklabel,))


class EpilogueBlock(Block):
    def writecode(self, lines):
        lines.append('}')


class FlexSwitch(Block):

    def __init__(self, rgenop, builder, gv_exitswitch):
        log('%s FlexSwitch.__init__ %s' % (builder.block.label, gv_exitswitch.operand()))
        self.rgenop = rgenop
        self.builder = builder
        self.gv_exitswitch = gv_exitswitch

        self.default_label = None
        self.cases = []

        self.rgenop.blocklist.append(self)

    def add_case(self, gv_case):
        targetbuilder = self.builder._fork()
        self.cases.append('%s,label %%%s' % (gv_case.operand(), targetbuilder.nextlabel))
        log('%s FlexSwitch.add_case %s => %s' % (
            self.builder.block.label, gv_case.operand(), targetbuilder.nextlabel))
        targetbuilder.start_writing()
        return targetbuilder

    def _add_default(self):
        targetbuilder = self.builder._fork()
        self.default_label = targetbuilder.nextlabel
        log('%s FlexSwitch.add_default => %s' % (
            self.builder.block.label, targetbuilder.nextlabel))
        targetbuilder.start_writing()
        return targetbuilder

    def writecode(self, lines):
        #note: gv_exitswitch should be an integer! (cast might be required here)
        lines.append(' switch %s,label %%%s [%s]' % (
                self.gv_exitswitch.operand(), self.default_label, ' '.join(self.cases)))


class Builder(GenBuilder):

    def __init__(self, rgenop, coming_from):
        self.rgenop = rgenop
        self.nextlabel = count.newlabel()   # the label of the next block
        self.block = coming_from            # the old block that jumped here

    def _fork(self):
        targetbuilder = Builder(self.rgenop, coming_from=self.block)
        log('%s Builder._fork => %s' % (self.block.label, targetbuilder.nextlabel))
        return targetbuilder

    def _close(self):
        self.block = None

    def end(self):
        self.rgenop.end()      # XXX Hack to be removed!

    def pause_writing(self, args_gv):
        log('%s Builder.pause_writing' % self.block.label)
        assert self.asm is not None
        self.nextlabel = count.newlabel()   # for the next block
        self.asm.append(' br label %%%s' % (self.nextlabel,))
        self.asm = None
        return self

    def start_writing(self):
        log('%s Builder.start_writing' % self.nextlabel)
        assert self.nextlabel is not None
        coming_from = self.block
        # prepare the next block
        nextblock = BasicBlock(self.rgenop, self.nextlabel, [])
        self.block     = nextblock
        self.asm       = nextblock.asm
        self.nextlabel = None
        nextblock.add_incoming_link(coming_from, [])

    # ----------------------------------------------------------------
    # The public Builder interface

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        log('%s Builder.genop1 %s %s' % (
            self.block.label, opname, gv_arg.operand()))
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        log('%s Builder.genop2 %s %s,%s' % (
            self.block.label, opname, gv_arg1.operand(), gv_arg2.operand()))
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def _rgenop2_generic(self, llvm_opcode, gv_arg1, gv_arg2, restype=None):
        log('%s Builder._rgenop2_generic %s %s,%s' % (
            self.block.label, llvm_opcode, gv_arg1.operand(), gv_arg2.operand2()))
        restype = restype or gv_arg1.type
        gv_result = Var(restype)
        self.asm.append(' %s=%s %s,%s' % (
            gv_result.operand2(), llvm_opcode, gv_arg1.operand(), gv_arg2.operand2()))
        return gv_result

    def op_int_add(self, gv_x, gv_y):       return self._rgenop2_generic('add' , gv_x, gv_y)
    def op_int_sub(self, gv_x, gv_y):       return self._rgenop2_generic('sub' , gv_x, gv_y)
    def op_int_mul(self, gv_x, gv_y):       return self._rgenop2_generic('mul' , gv_x, gv_y)
    def op_int_floordiv(self, gv_x, gv_y):
        return self._rgenop2_generic('us'[gv_x.signed] + 'div', gv_x, gv_y)
    def op_int_mod(self, gv_x, gv_y):
        return self._rgenop2_generic('us'[gv_x.signed] + 'rem' , gv_x, gv_y)
    def op_int_and(self, gv_x, gv_y):       return self._rgenop2_generic('and' , gv_x, gv_y)
    def op_int_or(self, gv_x, gv_y):        return self._rgenop2_generic('or'  , gv_x, gv_y)
    def op_int_xor(self, gv_x, gv_y):       return self._rgenop2_generic('xor' , gv_x, gv_y)

    def op_int_lshift(self, gv_x, gv_y):
        gv_y_i8 = Var(i8)
        self.asm.append(' %s=%s %s to %s' % (
            gv_y_i8.operand2(), trunc, gv_y.operand(), i8))
        gv_result = Var(gv_x.type)
        self.asm.append(' %s=shl %s,%s' % (
            gv_result.operand2(), gv_x.operand(), gv_y_i8.operand()))
        return gv_result

    def op_int_rshift(self, gv_x, gv_y):
        gv_y_i8 = Var(i8)
        self.asm.append(' %s=%s %s to %s' % (
            gv_y_i8.operand2(), trunc, gv_y.operand(), i8))
        gv_result = Var(gv_x.type)
        self.asm.append(' %s=%sshr %s,%s' % (
            gv_result.operand2(), shr_prefix[gv_x.signed], gv_x.operand(), gv_y_i8.operand()))
        return gv_result

    op_uint_add = op_float_add = op_int_add
    op_uint_sub = op_float_sub = op_int_sub
    op_uint_mul = op_float_mul = op_int_mul
    op_uint_floordiv = op_int_floordiv
    op_uint_mod = op_int_mod
    op_uint_and = op_int_and
    op_uint_or  = op_int_or
    op_uint_xor = op_int_xor
    op_uint_lshift = op_int_lshift
    op_uint_rshift = op_int_rshift
 
    def op_float_truediv(self, gv_x, gv_y):  return self._rgenop2_generic('fdiv', gv_x, gv_y)
    def op_float_neg(self, gv_x): return self._rgenop2_generic('sub', FloatConst(0.0), gv_x)

    def op_int_lt(self, gv_x, gv_y):
        return self._rgenop2_generic(scmp + 'lt', gv_x, gv_y, i1)

    def op_int_le(self, gv_x, gv_y):
        return self._rgenop2_generic(scmp + 'le', gv_x, gv_y, i1)

    def op_int_eq(self, gv_x, gv_y):
        return self._rgenop2_generic(icmp + 'eq' , gv_x, gv_y, i1)

    def op_int_ne(self, gv_x, gv_y):
        return self._rgenop2_generic(icmp + 'ne' , gv_x, gv_y, i1)

    def op_int_gt(self, gv_x, gv_y):
        return self._rgenop2_generic(scmp + 'gt', gv_x, gv_y, i1)

    def op_int_ge(self, gv_x, gv_y):
        return self._rgenop2_generic(scmp + 'ge', gv_x, gv_y, i1)

    def op_uint_lt(self, gv_x, gv_y):
        return self._rgenop2_generic(ucmp + 'lt', gv_x, gv_y, i1)

    def op_uint_le(self, gv_x, gv_y):
        return self._rgenop2_generic(ucmp + 'le', gv_x, gv_y, i1)

    def op_uint_gt(self, gv_x, gv_y):
        return self._rgenop2_generic(ucmp + 'gt', gv_x, gv_y, i1)

    def op_uint_ge(self, gv_x, gv_y):
        return self._rgenop2_generic(ucmp + 'ge', gv_x, gv_y, i1)

    def op_float_lt(self, gv_x, gv_y):
        return self._rgenop2_generic(fcmp + 'lt', gv_x, gv_y, i1)

    def op_float_le(self, gv_x, gv_y): 
        return self._rgenop2_generic(fcmp + 'le', gv_x, gv_y, i1)
    
    def op_float_eq(self, gv_x, gv_y): 
        return self._rgenop2_generic(fcmp + 'eq', gv_x, gv_y, i1)
    
    def op_float_ne(self, gv_x, gv_y): 
        return self._rgenop2_generic(fcmp + 'ne', gv_x, gv_y, i1)

    def op_float_gt(self, gv_x, gv_y): 
        return self._rgenop2_generic(fcmp + 'gt', gv_x, gv_y, i1)

    def op_float_ge(self, gv_x, gv_y): 
        return self._rgenop2_generic(fcmp + 'ge', gv_x, gv_y, i1)
    
    op_unichar_eq = op_ptr_eq = op_uint_eq = op_int_eq
    op_unichar_ne = op_ptr_ne = op_uint_ne = op_int_ne

    op_char_lt = op_uint_lt
    op_char_le = op_uint_le
    op_char_eq = op_uint_eq
    op_char_ne = op_uint_ne
    op_char_gt = op_uint_gt
    op_char_ge = op_uint_ge

    def _rgenop1_generic(self, llvm_opcode, gv_x, restype=None):
        log('%s Builder._rgenop1_generic %s %s' % (
            self.block.label, llvm_opcode, gv_x.operand()))
        restype = restype or gv_x.type
        gv_result = Var(restype)
        self.asm.append(' %s=%s %s' % (
            gv_result.operand2(), llvm_opcode, gv_x.operand()))
        return gv_resulgv_comp.operand(), t

    def op_int_neg(self, gv_x):     return self._rgenop2_generic('sub', IntConst(0), gv_x)
    def op_int_invert(self, gv_x):  return self._rgenop2_generic('xor', gv_x, IntConst(-1))
    def op_uint_invert(self, gv_x): return self._rgenop2_generic('xor', gv_x, UIntConst((1<<32)-1))

    def _abs(self, gv_x, nullstr='0'):
        gv_comp    = Var(i1)
        gv_abs_pos = Var(gv_x.type)
        gv_result  = Var(gv_x.type)
        if nullstr == 'null' or nullstr == '0':
            cmp = scmp
        else:
            cmp = fcmp
        self.asm.append(' %s=%sge %s,%s' % (
            gv_comp.operand2(), cmp, gv_x.operand(), nullstr))
        self.asm.append(' %s=sub %s %s,%s' % (
            gv_abs_pos.operand2(), gv_x.type, nullstr, gv_x.operand2()))
        self.asm.append(' %s=select %s,%s,%s' % (
            gv_result.operand2(), gv_comp.operand(), gv_x.operand(), gv_abs_pos.operand()))
        return gv_result

    op_int_abs = _abs
    def op_float_abs(self, gv_x):   return self._abs(gv_x, '0.0')

    def op_bool_not(self, gv_x):
        gv_result = Var(i1)
        self.asm.append(' %s=select %s,%s false,%s true' % (
            gv_result.operand2(), gv_x.operand(), i1, i1))
        return gv_result

    #XXX 'cast' has been replaced by many sext/zext/uitofp/... opcodes in the upcoming llvm 2.0.
    #The lines upto /XXX should be refactored to do the right thing
    def genop_same_as(self, kind, gv_x): #XXX why do we need a 'kind' here?
        if gv_x.is_const:    # must always return a var
            restype = gv_x.type
            gv_result = Var(restype)
            v = gv_x.operand2()
            if restype[-1] == '*':
                cst = inttoptr
                t   = i32
                if v == 'null':
                    v = '0'
            else:
                cst = bitcast
                t   = restype
            self.asm.append(' %s=%s %s %s to %s ;1' % (
                gv_result.operand2(), cst, t, v, restype))
            return gv_result
        else:
            return gv_x

    def _cast_to(self, gv_x, restype=None):
        t = gv_x.type
        restype = restype or t
        if restype is t:
            return self.genop_same_as(None, gv_x)
        gv_result = Var(restype)
        if restype[-1] == '*':
            if gv_x.is_const:
                cst = inttoptr
                t = i32
            else:
                cst = bitcast
        else:
            cst = zext
        self.asm.append(' %s=%s %s %s to %s ;2' % (
            gv_result.operand2(), cst, t, gv_x.operand2(), restype))
        return gv_result

    def _trunc_to(self, gv_x, restype=None):
        restype = restype or gv_x.type
        if restype is gv_x.type:
            return self.genop_same_as(None, gv_x)
        gv_result = Var(restype)
        self.asm.append(' %s=%s %s to %s' % (
            gv_result.operand2(), trunc, gv_x.operand(), restype))
        return gv_result

    def _cast_to_bool(self, gv_x):      return self._cast_to(gv_x, i1)
    def _cast_to_char(self, gv_x):      return self._cast_to(gv_x, i8)
    def _cast_to_unichar(self, gv_x):   return self._cast_to(gv_x, i32)
    def _cast_to_int(self, gv_x):       return self._cast_to(gv_x, i32)
    def _cast_to_uint(self, gv_x):      return self._cast_to(gv_x, u32)
    def _cast_to_float(self, gv_x):     return self._cast_to(gv_x, f64)

    def _trunc_to_bool(self, gv_x):      return self._trunc_to(gv_x, i1)
    def _trunc_to_char(self, gv_x):      return self._trunc_to(gv_x, i8)
    def _trunc_to_unichar(self, gv_x):   return self._trunc_to(gv_x, i32)
    def _trunc_to_int(self, gv_x):       return self._trunc_to(gv_x, i32)
    def _trunc_to_uint(self, gv_x):      return self._trunc_to(gv_x, u32)
    def _trunc_to_float(self, gv_x):     return self._trunc_to(gv_x, f64)

    op_cast_char_to_bool    = _trunc_to_bool
    op_cast_unichar_to_bool = _trunc_to_bool
    op_cast_int_to_bool     = _trunc_to_bool
    op_cast_uint_to_bool    = _trunc_to_bool
    op_cast_float_to_bool   = _trunc_to_bool

    op_cast_bool_to_char    = _cast_to_char
    op_cast_unichar_to_char = _trunc_to_char
    op_cast_int_to_char     = _trunc_to_char
    op_cast_uint_to_char    = _trunc_to_char
    op_cast_float_to_char   = _trunc_to_char

    op_cast_bool_to_unichar  = _cast_to_unichar
    op_cast_char_to_unichar  = _cast_to_unichar
    op_cast_int_to_unichar   = _cast_to_unichar
    op_cast_uint_to_unichar  = _cast_to_unichar
    op_cast_float_to_unichar = _trunc_to_unichar

    op_cast_bool_to_int    = _cast_to_int
    op_cast_char_to_int    = _cast_to_int
    op_cast_unichar_to_int = _cast_to_int
    op_cast_uint_to_int    = _cast_to_int
    op_cast_float_to_int   = _trunc_to_int

    op_cast_bool_to_uint    = _cast_to_uint
    op_cast_char_to_uint    = _cast_to_uint
    op_cast_unichar_to_uint = _cast_to_uint
    op_cast_int_to_uint     = _cast_to_uint
    op_cast_float_to_uint   = _trunc_to_uint

    op_cast_bool_to_float    = _cast_to_float
    op_cast_char_to_float    = _cast_to_float
    op_cast_unichar_to_float = _cast_to_float
    op_cast_int_to_float     = _cast_to_float
    op_cast_uint_to_float    = _cast_to_float
    #/XXX

    def enter_next_block(self, kinds, args_gv):
        assert self.nextlabel is None
        coming_from = self.block
        newlabel = count.newlabel()
        # we still need to properly terminate the current block
        # (with a br to go to the next block)
        # see: http://llvm.org/docs/LangRef.html#terminators
        self.asm.append(' br label %%%s' % (newlabel,))
        # prepare the next block
        nextblock = BasicBlock(self.rgenop, newlabel, kinds)
        log('%s Builder enter block %s' % (
            nextblock.label, [v.operand() for v in nextblock.inputargs]))
        self.block = nextblock
        self.asm   = nextblock.asm

        # link the two blocks together and update args_gv
        nextblock.add_incoming_link(coming_from, args_gv)
        for i in range(len(args_gv)):
            args_gv[i] = nextblock.inputargs[i]

        return self.block

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        log('%s Builder.jump_if_false %s' % (self.block.label, gv_condition.operand()))
        targetbuilder = self._fork()
        self.nextlabel = count.newlabel()
        self.asm.append(' br %s,label %%%s,label %%%s' % (
            gv_condition.operand(), self.nextlabel, targetbuilder.nextlabel))
        self.start_writing()
        return targetbuilder

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        log('%s Builder.jump_if_true %s' % (self.block.label, gv_condition.operand()))
        targetbuilder = self._fork()
        self.nextlabel = count.newlabel()
        self.asm.append(' br %s,label %%%s,label %%%s' % (
            gv_condition.operand(), targetbuilder.nextlabel, self.nextlabel))
        self.start_writing()
        return targetbuilder

    def _is_false(self, gv_x, nullstr='0'):
        log('%s Builder._is_false %s' % (self.block.label, gv_x.operand()))
        gv_result = Var(i1)
        if nullstr == 'null' or nullstr == '0':
            cmp = icmp
        else:
            cmp = fcmp
        self.asm.append(' %s=%seq %s,%s' % (
            gv_result.operand2(), cmp, gv_x.operand(), nullstr))
        return gv_result

    def _is_true(self, gv_x, nullstr='0'):
        log('%s Builder._is_true %s' % (self.block.label, gv_x.operand()))
        gv_result = Var(i1)
        if nullstr == 'null' or nullstr == '0':
            cmp = icmp
        else:
            cmp = fcmp
        self.asm.append(' %s=%sne %s,%s' % (
            gv_result.operand2(), cmp, gv_x.operand(), nullstr))
        return gv_result

    op_bool_is_true = op_char_is_true = op_unichar_is_true = op_int_is_true =\
    op_uint_is_true = _is_true
    
    def op_ptr_nonzero(self, gv_x):     return self._is_true(gv_x, 'null')
    def op_ptr_iszero(self, gv_x):      return self._is_false(gv_x, 'null')

    def genop_ptr_iszero(self, kind, gv_ptr):
        return self.op_ptr_iszero(gv_ptr)

    def genop_ptr_nonzero(self, kind, gv_ptr):
        return self.op_ptr_nonzero(gv_ptr)

    def genop_ptr_eq(self, kind, gv_ptr1, gv_ptr2):
        return self.op_ptr_eq(gv_ptr1, gv_ptr2)

    def genop_ptr_ne(self, kind, gv_ptr1, gv_ptr2):
        return self.op_ptr_ne(gv_ptr1, gv_ptr2)

    def op_float_is_true(self, gv_x):   return self._is_true(gv_x, '0.0') #XXX fails for doubles

    def genop_getfield(self, fieldtoken, gv_ptr):
        offset, fieldtype = fieldtoken
        log('%s Builder.genop_getfield (%d,%s) %s' % (
            self.block.label, offset, fieldtype, gv_ptr.operand()))
        gv_ptr_var = self._as_var(gv_ptr)
        gv_p = Var(gv_ptr.type)
        self.asm.append(' %s=getelementptr %s,%s %s' % (
            gv_p.operand2(), gv_ptr_var.operand(), i32, offset))
        gv_p2 = self._cast_to(gv_p, fieldtype + '*')
        gv_result = Var(fieldtype)
        self.asm.append(' %s=load %s' % (
            gv_result.operand2(), gv_p2.operand()))
        return gv_result

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        offset, fieldtype = fieldtoken
        log('%s Builder.genop_setfield (%d,%s) %s=%s' % (
            self.block.label, offset, fieldtype, gv_ptr.operand(), gv_value.operand()))
        gv_ptr_var = self._as_var(gv_ptr)
        gv_p = Var(gv_ptr.type)
        self.asm.append(' %s=getelementptr %s,%s %s' % (
            gv_p.operand2(), gv_ptr_var.operand(), i32, offset))
        gv_p2 = self._cast_to(gv_p, fieldtype + '*')
        self.asm.append(' store %s,%s' % (
            gv_value.operand(), gv_p2.operand()))

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        offset, fieldtype = fieldtoken
        log('%s Builder.genop_getsubstruct (%d,%s) %s' % (
            self.block.label, offset, fieldtype, gv_ptr.operand()))
        gv_ptr_var = self._as_var(gv_ptr)
        gv_sub = Var(gv_ptr.type)
        self.asm.append(' %s=getelementptr %s,%s %d' % (
            gv_sub.operand2(), gv_ptr_var.operand(), i32, offset))
        return gv_sub

    def genop_getarraysubstruct(self, arraytoken, gv_ptr, gv_index):
        '''
        self.mc.MOV(edx, gv_ptr.operand(self))
        op = self.itemaddr(edx, arraytoken, gv_index)
        self.mc.LEA(eax, op)
        return self.returnvar(eax)
        '''
        #XXX WIP
        log('%s Builder.genop_getarraysubstruct %s,%s,%s' % (
            self.block.label, arraytoken, gv_ptr.operand(), gv_index.operand()))

        array_length_offset, array_items_offset, item_size, item_type = arraytoken

        op_size = self._itemaddr(arraytoken, gv_index)

        gv_ptr_var = self._as_var(gv_ptr)

        gv_result = Var(pi8)
        self.asm.append(' %s=getelementptr %s,%s' % (
            gv_result.operand2(), gv_ptr_var.operand(), op_size.operand()))

        return gv_result

    def genop_getarraysize(self, arraytoken, gv_ptr):
        log('%s Builder.genop_getarraysize %s,%s' % (
            self.block.label, arraytoken, gv_ptr.operand()))

        array_length_offset, array_items_offset, item_size, item_type = arraytoken
        gv_ptr_var = self._as_var(gv_ptr)

        gv_p = Var(gv_ptr_var.type)
        self.asm.append(' %s=getelementptr %s,%s %s' % (
            gv_p.operand2(), gv_ptr_var.operand(), i32, array_length_offset))

        gv_p2 = self._cast_to(gv_p, pi32)

        gv_result = Var(i32)
        self.asm.append(' %s=load %s' % (
            gv_result.operand2(), gv_p2.operand()))

        return gv_result

    def _as_var(self, gv):
        if gv.is_const:
            gv_var = Var(gv.type)
            #XXX provide correct cast here
            self.asm.append(' %s=%s %s %s to %s' % (
                gv_var.operand2(), inttoptr, i32, gv.operand2(), gv_var.type))
            return gv_var
        return gv
 
    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        array_length_offset, array_items_offset, item_size, item_type = arraytoken
        log('%s Builder.genop_getarrayitem %s,%s[%s]' % (
            self.block.label, arraytoken, gv_ptr.operand(), gv_index.operand()))

        gv_ptr_var = self._as_var(gv_ptr)

        gv_p = Var(gv_ptr_var.type)
        self.asm.append(' %s=getelementptr %s,%s %s' % (
            gv_p.operand2(), gv_ptr_var.operand(), i32, array_items_offset))

        gv_p2 = self._cast_to(gv_p, item_type + '*')

        gv_p3 = Var(gv_p2.type)
        self.asm.append(' %s=getelementptr %s,%s' % (
            gv_p3.operand2(), gv_p2.operand(), gv_index.operand()))

        gv_result = Var(item_type)
        self.asm.append(' %s=load %s' % (
            gv_result.operand2(), gv_p3.operand()))

        return gv_result

    def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
        array_length_offset, array_items_offset, item_size, item_type = arraytoken
        log('%s Builder.genop_setarrayitem %s,%s[%s]=%s' % (
            self.block.label, arraytoken, gv_ptr.operand(), gv_index.operand(), gv_value.operand()))

        gv_ptr_var = self._as_var(gv_ptr)

        gv_p = Var(gv_ptr_var.type)
        self.asm.append(' %s=getelementptr %s,%s %s' % (
            gv_p.operand2(), gv_ptr_var.operand(), i32, array_items_offset))

        gv_p2 = self._cast_to(gv_p, item_type + '*')

        gv_p3 = Var(gv_p2.type)
        self.asm.append(' %s=getelementptr %s,%s' % (
            gv_p3.operand2(), gv_p2.operand(), gv_index.operand()))

        self.asm.append(' store %s,%s' % (
            gv_value.operand(), gv_p3.operand()))

    def genop_malloc_fixedsize(self, size):
        log('%s Builder.genop_malloc_fixedsize %s' % (
            self.block.label, str(size)))
        gv_gc_malloc_fnaddr = Var('%s (%s)*' % (pi8, i32))
        gv_result = Var(pi8)
        #or use addGlobalFunctionMapping in libllvmjit.restart()
        self.asm.append(' %s=%s %s %d to %s ;gc_malloc_fnaddr' % (
            gv_gc_malloc_fnaddr.operand2(), inttoptr, i32,
            gc_malloc_fnaddr(), gv_gc_malloc_fnaddr.type))
        self.asm.append(' %s=call %s(%s %d)' % (
            gv_result.operand2(), gv_gc_malloc_fnaddr.operand(), i32, size))
        return gv_result

    def _itemaddr(self, arraytoken, gv_index):
        length_offset, items_offset, item_size, item_type = arraytoken

        gv_size2 = Var(i32) #i386 uses self.itemaddr here
        self.asm.append(' %s=mul %s,%d' % (
            gv_size2.operand2(), gv_index.operand(), item_size))

        gv_size3 = Var(i32)
        self.asm.append(' %s=add %s,%d' % (
            gv_size3.operand2(), gv_size2.operand(), items_offset))

        return gv_size3

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        log('%s Builder.genop_malloc_varsize %s,%s' % (
            self.block.label, varsizealloctoken, gv_size.operand()))

        length_offset, items_offset, item_size, item_type = varsizealloctoken

        gv_gc_malloc_fnaddr = Var('%s (%s)*' % (pi8, i32))
        #or use addGlobalFunctionMapping in libllvmjit.restart()
        self.asm.append(' %s=%s %s %d to %s ;gc_malloc_fnaddr (varsize)' % (
            gv_gc_malloc_fnaddr.operand2(), inttoptr, i32,
            gc_malloc_fnaddr(), gv_gc_malloc_fnaddr.type))

        op_size = self._itemaddr(varsizealloctoken, gv_size)

        gv_result = Var(pi8)
        self.asm.append(' %s=call %s(%s)' % (
            gv_result.operand2(), gv_gc_malloc_fnaddr.operand(), op_size.operand()))

        gv_p = Var(gv_result.type)
        self.asm.append(' %s=getelementptr %s,%s %s' % (
            gv_p.operand2(), gv_result.operand(), i32, length_offset))

        gv_p2 = self._cast_to(gv_p, pi32) #warning: length field hardcoded as int here
        self.asm.append(' store %s, %s' % (gv_size.operand(), gv_p2.operand()))

        return gv_result

    def _funcsig_type(self, args_gv, restype):
        return '%s (%s)' % (restype, ','.join([a.type for a in args_gv]))

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        log('%s Builder.genop_call %s,%s,%s' % (
            self.block.label, sigtoken, gv_fnptr, [v.operand() for v in args_gv]))
        argtypes, restype = sigtoken
        if isinstance(gv_fnptr, AddrConst):
            gv_fn = Var(self._funcsig_type(args_gv, restype) + '*')
            self.asm.append(' %s=%s %s %s to %s' % (
                gv_fn.operand2(), inttoptr, i32, gv_fnptr.operand2(), gv_fn.type))
            funcsig = gv_fn.operand()
        else:
            try:
                funcsig = self.rgenop.funcsig[gv_fnptr.get_integer_value()]
            except KeyError:
                funcsig = 'TODO: funcsig here'
                py.test.skip('call an address directly not supported yet')
        args_gv2 = []
        for v in args_gv:
            if v.is_const and v.type[-1] == '*': #or use some kind of 'inline' cast (see LangRef)
                t = Var(v.type)
                self.asm.append(' %s=%s %s %s to %s' % (
                    t.operand2(), inttoptr, i32, v.operand2(), v.type))
                v = t
            args_gv2.append(v)
        gv_returnvar = Var(restype)
        self.asm.append(' %s=call %s(%s)' % (
                        gv_returnvar.operand2(),
                        funcsig,
                        ','.join([v.operand() for v in args_gv2])))
        return gv_returnvar
    
    def finish_and_return(self, sigtoken, gv_returnvar):
        log('%s Builder.finish_and_return %s,%s' % (
            self.block.label, sigtoken, gv_returnvar.operand()))
        self.asm.append(' ret ' + gv_returnvar.operand())
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        # 'target' is a label, which for the llvm backend is a Block
        log('%s Builder.finish_and_goto' % self.block.label)
        gv = [v.operand() for v in outputargs_gv]
        log('%s Builder.finish_and_goto %s,%s' % (
            self.block.label, gv, target.label))
        self.asm.append(' br label %%%s' % (target.label,))
        target.add_incoming_link(self.block, outputargs_gv)
        self._close()

    def flexswitch(self, gv_exitswitch, args_gv):
        log('%s Builder.flexswitch %s' % (self.block.label, gv_exitswitch.operand()))
        flexswitch = FlexSwitch(self.rgenop, self, gv_exitswitch)
        return flexswitch, flexswitch._add_default()


class RLLVMGenOp(AbstractRGenOp):

    funcsig  = {} #HACK for looking up function signatures
    funcused = {} #we rename functions when encountered multiple times (for test_branching_compile)

    def check_no_open_mc(self):
        return True

    def _dump_partial_lines(self):  #what we've generated so far
        asmlines = []
        for block in self.blocklist:
            block.writecode(asmlines)
        asmlines = ['%s ;%d' % (asmlines[i], i+1) for i in range(len(asmlines))]
        asm_string = '\n'.join(asmlines)
        logger.dump(asm_string)

    def end(self):
        log('   RLLVMGenOp.end')
        self.blocklist.append(EpilogueBlock())
        asmlines = []
        for block in self.blocklist:
            block.writecode(asmlines)
        if LINENO:
            asmlines = ['%s ;%d' % (asmlines[i], i+1) for i in range(len(asmlines))]
        asm_string = '\n'.join(asmlines)

        self.blocklist = None
        if PRINT_SOURCE:
            print asm_string
        logger.dump(asm_string)
        parse_ok = llvmjit.parse(asm_string)
        if not parse_ok:
            raise ParseException()
        llvmjit.transform(3) #optimize module (should be on functions actually)
        function   = llvmjit.getNamedFunction(self.name)
        entrypoint = llvmjit.getPointerToFunctionAsInt(function)
        # XXX or directly cast the ctypes ptr to int with:
        #   ctypes.cast(ptr, c_void_p).value
        self.funcsig[entrypoint] = self.funcsig[self.gv_entrypoint.value]
        self.gv_entrypoint.value = entrypoint

    # ----------------------------------------------------------------
    # the public RGenOp interface

    def newgraph(self, sigtoken, name):
        if name in self.funcused:
            self.funcused[name] += 1
            name = '%s_%d' % (name, self.funcused[name])
        else:
            self.funcused[name] = 0

        log('   RLLVMGenOp.newgraph %s,%s' % (sigtoken, name))

        prologueblock = PrologueBlock(sigtoken, name)
        self.blocklist = [prologueblock]
        builder = Builder(self, coming_from=prologueblock)
        prologueblock.startblocklabel = builder.nextlabel

        argtypes, restype = sigtoken
        n = len(self.funcsig) * 2 + 1     #+1 so we recognize these pre compilation 'pointers'
        self.name = name
        self.funcsig[n] = '%s %s%s' % (restype, globalprefix, name)
        self.gv_entrypoint = IntConst(n)    #note: updated by Builder.end() (i.e after compilation)
        args = list(prologueblock.inputargs)
        return builder, self.gv_entrypoint, args

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif T is lltype.Bool:
            return BoolConst(lltype.cast_primitive(lltype.Bool, llvalue))
        elif T is lltype.Char:
            return CharConst(lltype.cast_primitive(lltype.Char, llvalue))
        elif T is lltype.Unsigned:
            return UIntConst(lltype.cast_primitive(lltype.Unsigned, llvalue))
        elif T is lltype.Float:
            return FloatConst(lltype.cast_primitive(lltype.Float, llvalue))
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            #if T.TO._gckind == 'gc':
            #    self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            msg = 'XXX not implemented'
            logger.dump(msg)
            assert 0, msg

    # attached later constPrebuiltGlobal = global_rgenop.genconst

    @staticmethod
    def genzeroconst(kind):
        return zero_consts[kind]

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        # turn the type T into the llvm approximation that we'll use here
        # XXX incomplete
        if isinstance(T, lltype.Ptr) or T is llmemory.Address:
            return pi8
        elif T is lltype.Bool:
            return i1 
        elif T is lltype.Char:
            return i8
        elif T is lltype.Unsigned:
            return u32
        elif T is lltype.Float:
            return f64
        else:
            return i32  #Signed/UniChar/Void

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        FIELD = getattr(T, name)
        if isinstance(FIELD, lltype.ContainerType):
            fieldtype = pi8 # not useful for getsubstruct
        else:
            fieldtype = RLLVMGenOp.kindToken(FIELD)
        return (llmemory.offsetof(T, name), fieldtype)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        #XXX TODO
        if isinstance(T, lltype.Array):
            return RLLVMGenOp.arrayToken(T)
        else:
            # var-sized structs
            arrayfield = T._arrayfld
            ARRAYFIELD = getattr(T, arrayfield)
            arraytoken = RLLVMGenOp.arrayToken(ARRAYFIELD)
            length_offset, items_offset, item_size, item_type = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return (arrayfield_offset+length_offset,
                    arrayfield_offset+items_offset,
                    item_size,
                    item_type)

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF),
                RLLVMGenOp.kindToken(A.OF))

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        argtypes = [RLLVMGenOp.kindToken(T) for T in FUNCTYPE.ARGS]
        restype  = RLLVMGenOp.kindToken(FUNCTYPE.RESULT)
        return (argtypes, restype)

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            msg = 'XXX not implemented'
            logger.dump(msg)
            assert 0, msg


global_rgenop = RLLVMGenOp()
RLLVMGenOp.constPrebuiltGlobal = global_rgenop.genconst

zero_consts = {
    pi8: AddrConst(llmemory.NULL),
    i1:  BoolConst(False),
    i8:  CharConst('\x00'),
    u32: UIntConst(r_uint(0)),
    f64: FloatConst(0.0),
    i32: IntConst(0),
    }
