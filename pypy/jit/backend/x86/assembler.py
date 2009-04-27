import sys, os
import ctypes
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.history import Const, ConstInt, Box, ConstPtr, BoxPtr,\
     BoxInt, ConstAddr
from pypy.rpython.lltypesystem import lltype, rffi, ll2ctypes, rstr, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.annotation import model as annmodel
from pypy.tool.uid import fixid
from pypy.jit.backend.x86.regalloc import (RegAlloc, WORD, REGS, TempBox,
                                      arg_pos, lower_byte, stack_pos)
from pypy.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from pypy.jit.backend.x86 import codebuf
from pypy.jit.backend.x86.support import gc_malloc_fnaddr
from pypy.jit.backend.x86.ri386 import *
from pypy.jit.metainterp.resoperation import rop

# our calling convention - we pass three first args as edx, ecx and eax
# and the rest stays on the stack

MAX_FAIL_BOXES = 1000

def repr_of_arg(memo, arg):
    try:
        mv = memo[arg]
    except KeyError:
        mv = len(memo)
        memo[arg] = mv
    if isinstance(arg, ConstInt):
        return "ci(%d,%d)" % (mv, arg.value)
    elif isinstance(arg, ConstPtr):
        return "cp(%d,%d)" % (mv, arg.get_())
    elif isinstance(arg, BoxInt):
        return "bi(%d,%d)" % (mv, arg.value)
    elif isinstance(arg, BoxPtr):
        return "bp(%d,%d)" % (mv, arg.get_())
    elif isinstance(arg, ConstAddr):
        return "ca(%d,%d)" % (mv, arg.get_())
    else:
        #raise NotImplementedError
        return "?%r" % (arg,)

class MachineCodeBlockWrapper(object):
    MC_SIZE = 1024*1024

    def __init__(self):
        self.old_mcs = [] # keepalive
        self._mc = codebuf.MachineCodeBlock(self.MC_SIZE)

    def tell(self):
        return self._mc.tell()

    def done(self):
        self._mc.done()

def _new_method(name):
    def method(self, *args):
        # XXX er.... pretty random number, just to be sure
        #     not to write half-instruction
        if self._mc._pos + 64 >= self._mc._size:
            new_mc = codebuf.MachineCodeBlock(self.MC_SIZE)
            self._mc.JMP(rel32(new_mc.tell()))
            self._mc.done()
            self.old_mcs.append(self._mc)
            self._mc = new_mc
        getattr(self._mc, name)(*args)    
    method.func_name = name
    return method

for name in dir(codebuf.MachineCodeBlock):
    if name.upper() == name:
        setattr(MachineCodeBlockWrapper, name, _new_method(name))

class MachineCodeStack(object):
    def __init__(self):
        self.mcstack = []
        self.counter = 0

    def next_mc(self):
        if len(self.mcstack) == self.counter:
            mc = MachineCodeBlockWrapper()
            self.mcstack.append(mc)
        else:
            mc = self.mcstack[self.counter]
        self.counter += 1
        return mc

    def give_mc_back(self, mc):
        mc.done()
        assert self.mcstack[self.counter - 1] is mc
        self.counter -= 1

class Assembler386(object):
    log_fd = -1
    mc = None
    mc2 = None
    debug_markers = True

    def __init__(self, cpu, translate_support_code=False):
        self.cpu = cpu
        self.verbose = False
        self.rtyper = cpu.rtyper
        self.malloc_func_addr = 0
        self._exception_data = lltype.nullptr(rffi.CArray(lltype.Signed))
        self._exception_addr = 0
        self.mcstack = MachineCodeStack()
        
    def _get_log(self):
        s = os.environ.get('PYPYJITLOG')
        if not s:
            return -1
        s += '.ops'
        try:
            flags = os.O_WRONLY|os.O_CREAT|os.O_TRUNC
            log_fd = os.open(s, flags, 0666)
        except OSError:
            os.write(2, "could not create log file\n")
            return -1
        return log_fd

    def make_sure_mc_exists(self):
        if self.mc is None:
            self.fail_boxes = lltype.malloc(rffi.CArray(lltype.Signed),
                                            MAX_FAIL_BOXES, flavor='raw')
            self.fail_box_addr = self.cpu.cast_ptr_to_int(self.fail_boxes)

            self._log_fd = self._get_log()
            # we generate the loop body in 'mc'
            # 'mc2' is for guard recovery code
            if we_are_translated():
                addr = llop.get_exception_addr(llmemory.Address)
                self._exception_data = llmemory.cast_adr_to_ptr(addr, rffi.CArrayPtr(lltype.Signed))
            else:
                self._exception_data = lltype.malloc(rffi.CArray(lltype.Signed), 2,
                                                     zero=True, flavor='raw')
            self._exception_addr = self.cpu.cast_ptr_to_int(
                self._exception_data)
            # a backup, in case our exception can be somehow mangled,
            # by a handling code
            self._exception_bck = lltype.malloc(rffi.CArray(lltype.Signed), 2,
                                                zero=True, flavor='raw')
            self._exception_bck_addr = self.cpu.cast_ptr_to_int(
                self._exception_bck)
            self.mc = self.mcstack.next_mc()
            self.mc2 = self.mcstack.next_mc()
            # the address of the function called by 'new': directly use
            # Boehm's GC_malloc function.
            if self.malloc_func_addr == 0:
                self.malloc_func_addr = gc_malloc_fnaddr()

    def eventually_log_operations(self, inputargs, operations, memo=None,
                                  myid=0):
        from pypy.jit.backend.x86.runner import ConstDescr3
        
        if self._log_fd == -1:
            return
        if memo is None:
            memo = {}
        if inputargs is None:
            os.write(self._log_fd, "BEGIN(%s)\n" % myid)
        else:
            args = ",".join([repr_of_arg(memo, arg) for arg in inputargs])
            os.write(self._log_fd, "LOOP %s\n" % args)
        for i in range(len(operations)):
            op = operations[i]
            args = ",".join([repr_of_arg(memo, arg) for arg in op.args])
            if op.descr is not None and isinstance(op.descr, ConstDescr3):
                descr = (str(op.descr.v[0]) + "," + str(op.descr.v[1]) +
                         "," + str(op.descr.v[2]))
                os.write(self._log_fd, "%d:%s %s[%s]\n" % (i, op.getopname(),
                                                           args, descr))
            else:
                os.write(self._log_fd, "%d:%s %s\n" % (i, op.getopname(), args))
            if op.result is not None:
                os.write(self._log_fd, "  => %s\n" % repr_of_arg(memo,
                                                                 op.result))
            if op.is_guard():
                self.eventually_log_operations(None, op.suboperations, memo)
        if operations[-1].opnum == rop.JUMP:
            jump_target = compute_unique_id(operations[-1].jump_target)
            os.write(self._log_fd, 'JUMPTO:%s\n' % jump_target)
        if inputargs is None:
            os.write(self._log_fd, "END\n")
        else:
            os.write(self._log_fd, "LOOP END\n")

    def log_failure_recovery(self, gf, guard_index):
        if self._log_fd == -1:
            return
        return # XXX
        os.write(self._log_fd, 'xxxxxxxxxx\n')
        memo = {}
        reprs = []
        for j in range(len(gf.guard_op.liveboxes)):
            valuebox = gf.cpu.getvaluebox(gf.frame, gf.guard_op, j)
            reprs.append(repr_of_arg(memo, valuebox))
        jmp = gf.guard_op._jmp_from
        os.write(self._log_fd, "%d %d %s\n" % (guard_index, jmp,
                                               ",".join(reprs)))
        os.write(self._log_fd, 'xxxxxxxxxx\n')

    def log_call(self, valueboxes):
        if self._log_fd == -1:
            return
        return # XXX
        memo = {}
        args_s = ','.join([repr_of_arg(memo, box) for box in valueboxes])
        os.write(self._log_fd, "CALL\n")
        os.write(self._log_fd, "%s %s\n" % (name, args_s))

    def _compute_longest_fail_op(self, ops):
        max_so_far = 0
        for op in ops:
            if op.opnum == rop.FAIL:
                max_so_far = max(max_so_far, len(op.args))
            if op.is_guard():
                max_so_far = max(max_so_far, self._compute_longest_fail_op(
                    op.suboperations))
        assert max_so_far < MAX_FAIL_BOXES
        return max_so_far

    def assemble(self, tree):
        self.places_to_patch_framesize = []
        self.jumps_to_look_at = []
        # the last operation can be 'jump', 'return' or 'guard_pause';
        # a 'jump' can either close a loop, or end a bridge to some
        # previously-compiled code.
        self._compute_longest_fail_op(tree.operations)
        self.tree = tree
        self.make_sure_mc_exists()
        inputargs = tree.inputargs
        self.eventually_log_operations(tree.inputargs, tree.operations, None,
                                       compute_unique_id(tree))
        regalloc = RegAlloc(self, tree, self.cpu.translate_support_code)
        if not we_are_translated():
            self._regalloc = regalloc # for debugging
        regalloc.walk_operations(tree)
        self.sanitize_tree(tree.operations)
        self.mc.done()
        self.mc2.done()
        tree._x86_stack_depth = regalloc.max_stack_depth
        for place in self.places_to_patch_framesize:
            mc = codebuf.InMemoryCodeBuilder(place, place + 128)
            mc.ADD(esp, imm32(tree._x86_stack_depth * WORD))
            mc.done()
        for op, pos in self.jumps_to_look_at:
            if op.jump_target._x86_stack_depth < tree._x86_stack_depth:
                # XXX do a dumb thing
                tl = op.jump_target
                self.patch_jump(pos, tl._x86_compiled, tl.arglocs, tl.arglocs,
                                tree._x86_stack_depth, tl._x86_stack_depth)

    def sanitize_tree(self, operations):
        """ Cleans up all attributes attached by regalloc and backend
        """
        for op in operations:
            if op.is_guard():
                op.inputargs = None
                op.longevity = None
                self.sanitize_tree(op.suboperations)

    def assemble_bootstrap_code(self, jumpaddr, arglocs, framesize):
        self.make_sure_mc_exists()
        addr = self.mc.tell()
        self.mc.SUB(esp, imm(framesize * WORD))
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if not isinstance(loc, REG):
                self.mc.MOV(ecx,
                            addr_add(imm(self.fail_box_addr), imm(i*WORD)))
                self.mc.MOV(loc, ecx)
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if isinstance(loc, REG):
                self.mc.MOV(loc,
                            addr_add(imm(self.fail_box_addr), imm(i*WORD)))
        self.mc.JMP(rel32(jumpaddr))
        self.mc.done()
        return addr

    def dump(self, text):
        if not self.verbose:
            return
        _prev = Box._extended_display
        try:
            Box._extended_display = False
            print >> sys.stderr, ' 0x%x  %s' % (fixid(self.mc.tell()), text)
        finally:
            Box._extended_display = _prev

#     def assemble_comeback_bootstrap(self, position, arglocs, stacklocs):
#         return
#         entry_point_addr = self.mc2.tell()
#         for i in range(len(arglocs)):
#             argloc = arglocs[i]
#             if isinstance(argloc, REG):
#                 self.mc2.MOV(argloc, stack_pos(stacklocs[i]))
#             elif not we_are_translated():
#                 # debug checks
#                 if not isinstance(argloc, (IMM8, IMM32)):
#                     assert repr(argloc) == repr(stack_pos(stacklocs[i]))
#         self.mc2.JMP(rel32(position))
#         self.mc2.done()
#         return entry_point_addr

#     def assemble_generic_return(self):
#         # generate a generic stub that just returns, taking the
#         # return value from *esp (i.e. stack position 0).
#         addr = self.mc.tell()
#         self.mc.MOV(eax, mem(esp, 0))
#         self.mc.ADD(esp, imm(FRAMESIZE))
#         self.mc.RET()
#         self.mc.done()
#         return addr

    def regalloc_load(self, from_loc, to_loc):
        self.mc.MOV(to_loc, from_loc)

    regalloc_store = regalloc_load

    def regalloc_perform(self, op, arglocs, resloc):
        genop_list[op.opnum](self, op, arglocs, resloc)

    def regalloc_perform_discard(self, op, arglocs):
        genop_discard_list[op.opnum](self, op, arglocs)

    def regalloc_perform_with_guard(self, op, guard_op, regalloc,
                                    arglocs, resloc, ovf):
        addr = self.implement_guard_recovery(guard_op, regalloc, ovf)
        genop_guard_list[op.opnum](self, op, guard_op, addr, arglocs,
                                   resloc)

    def regalloc_perform_guard(self, op, regalloc, arglocs, resloc):
        addr = self.implement_guard_recovery(op, regalloc)
        genop_guard_list[op.opnum](self, op, None, addr, arglocs,
                                   resloc)

    def _unaryop(asmop):
        def genop_unary(self, op, arglocs, resloc):
            getattr(self.mc, asmop)(arglocs[0])
        return genop_unary

    def _binaryop(asmop, can_swap=False):
        def genop_binary(self, op, arglocs, result_loc):
            getattr(self.mc, asmop)(arglocs[0], arglocs[1])
        return genop_binary

    def _binaryop_ovf(asmop, can_swap=False):
        def genop_binary_ovf(self, op, guard_op, addr, arglocs, result_loc):
            getattr(self.mc, asmop)(arglocs[0], arglocs[1])
            self.mc.JO(rel32(addr))
        return genop_binary_ovf

    def _cmpop(cond, rev_cond):
        def genop_cmp(self, op, arglocs, result_loc):
            if isinstance(op.args[0], Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                self.mc.MOV(result_loc, imm8(0))
                getattr(self.mc, 'SET' + rev_cond)(lower_byte(result_loc))
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                self.mc.MOV(result_loc, imm8(0))
                getattr(self.mc, 'SET' + cond)(lower_byte(result_loc))
        return genop_cmp

    def _cmpop_guard(cond, rev_cond, false_cond, false_rev_cond):
        def genop_cmp_guard(self, op, guard_op, addr, arglocs, result_loc):
            if isinstance(op.args[0], Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                if guard_op.opnum == rop.GUARD_FALSE:
                    name = 'J' + rev_cond
                    self.implement_guard(addr, guard_op, getattr(self.mc, name))
                else:
                    name = 'J' + false_rev_cond
                    self.implement_guard(addr, guard_op, getattr(self.mc, name))
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                if guard_op.opnum == rop.GUARD_FALSE:
                    self.implement_guard(addr, guard_op,
                                         getattr(self.mc, 'J' + cond))
                else:
                    name = 'J' + false_cond
                    self.implement_guard(addr, guard_op, getattr(self.mc, name))
        return genop_cmp_guard
            

    def call(self, addr, args, res):
        for i in range(len(args)):
            arg = args[i]
            assert not isinstance(arg, MODRM)
            self.mc.PUSH(arg)
        self.mc.CALL(rel32(addr))
        self.mc.ADD(esp, imm(len(args) * WORD))
        assert res is eax

    genop_int_neg = _unaryop("NEG")
    genop_int_invert = _unaryop("NOT")
    genop_int_add = _binaryop("ADD", True)
    genop_int_sub = _binaryop("SUB")
    genop_int_mul = _binaryop("IMUL", True)
    genop_int_and = _binaryop("AND", True)
    genop_int_or  = _binaryop("OR", True)
    genop_int_xor = _binaryop("XOR", True)

    genop_guard_int_mul_ovf = _binaryop_ovf("IMUL", True)
    genop_guard_int_sub_ovf = _binaryop_ovf("SUB")
    genop_guard_int_add_ovf = _binaryop_ovf("ADD", True)

    def genop_guard_int_neg_ovf(self, op, guard_op, addr, arglocs, result_loc):
        self.mc.NEG(result_loc)
        self.mc.JO(rel32(addr))

    genop_int_lt = _cmpop("L", "G")
    genop_int_le = _cmpop("LE", "GE")
    genop_int_eq = _cmpop("E", "E")
    genop_oois = genop_int_eq
    genop_int_ne = _cmpop("NE", "NE")
    genop_ooisnot = genop_int_ne
    genop_int_gt = _cmpop("G", "L")
    genop_int_ge = _cmpop("GE", "LE")

    genop_uint_gt = _cmpop("A", "B")
    genop_uint_lt = _cmpop("B", "A")
    genop_uint_le = _cmpop("BE", "AE")
    genop_uint_ge = _cmpop("AE", "BE")

    genop_guard_int_lt = _cmpop_guard("L", "G", "GE", "LE")
    genop_guard_int_le = _cmpop_guard("LE", "GE", "G", "L")
    genop_guard_int_eq = _cmpop_guard("E", "E", "NE", "NE")
    genop_guard_int_ne = _cmpop_guard("NE", "NE", "E", "E")
    genop_guard_int_gt = _cmpop_guard("G", "L", "LE", "GE")
    genop_guard_int_ge = _cmpop_guard("GE", "LE", "L", "G")

    genop_guard_uint_gt = _cmpop_guard("A", "B", "BE", "AE")
    genop_guard_uint_lt = _cmpop_guard("B", "A", "AE", "BE")
    genop_guard_uint_le = _cmpop_guard("BE", "AE", "A", "B")
    genop_guard_uint_ge = _cmpop_guard("AE", "BE", "B", "A")

    # for now all chars are being considered ints, although we should make
    # a difference at some point
    xxx_genop_char_eq = genop_int_eq

    def genop_bool_not(self, op, arglocs, resloc):
        self.mc.XOR(arglocs[0], imm8(1))

    def genop_int_lshift(self, op, arglocs, resloc):
        loc, loc2 = arglocs
        if loc2 is ecx:
            loc2 = cl
        self.mc.SHL(loc, loc2)

    def genop_int_rshift(self, op, arglocs, resloc):
        loc, loc2 = arglocs
        if loc2 is ecx:
            loc2 = cl
        self.mc.SAR(loc, loc2)

    def genop_uint_rshift(self, op, arglocs, resloc):
        loc, loc2 = arglocs
        if loc2 is ecx:
            loc2 = cl
        self.mc.SHR(loc, loc2)

    def genop_guard_int_lshift_ovf(self, op, guard_op, addr, arglocs, resloc):
        loc, loc2, tmploc = arglocs
        if loc2 is ecx:
            loc2 = cl
        # xxx a bit inefficient
        self.mc.MOV(tmploc, loc)
        self.mc.SHL(tmploc, loc2)
        self.mc.SAR(tmploc, loc2)
        self.mc.CMP(tmploc, loc)
        self.mc.JNE(rel32(addr))
        self.mc.SHL(loc, loc2)

    def genop_int_is_true(self, op, arglocs, resloc):
        argloc = arglocs[0]
        self.mc.TEST(argloc, argloc)
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNZ(lower_byte(resloc))

    def genop_int_abs(self, op, arglocs, resloc):
        argloc = arglocs[0]
        tmploc = arglocs[1]
        assert resloc != argloc and resloc != tmploc
        self.mc.MOV(resloc, argloc)
        # ABS-computing code from Psyco, found by exhaustive search
        # on *all* short sequences of operations :-)
        self.mc.ADD(resloc, resloc)
        self.mc.SBB(resloc, argloc)
        self.mc.SBB(tmploc, tmploc)
        self.mc.XOR(resloc, tmploc)
        # in case of overflow, the result is negative again (-sys.maxint-1)
        # and the L flag is set.

    def genop_guard_int_abs_ovf(self, op, guard_op, addr, arglocs, resloc):
        self.genop_int_abs(op, arglocs, resloc)
        self.mc.JL(rel32(addr))

    def genop_guard_oononnull(self, op, guard_op, addr, arglocs, resloc):
        loc = arglocs[0]
        self.mc.TEST(loc, loc)
        if guard_op.opnum == rop.GUARD_TRUE:
            self.implement_guard(addr, guard_op, self.mc.JZ)
        else:
            self.implement_guard(addr, guard_op, self.mc.JNZ)

    def genop_guard_ooisnull(self, op, guard_op, addr, arglocs, resloc):
        loc = arglocs[0]
        self.mc.TEST(loc, loc)
        if guard_op.opnum == rop.GUARD_TRUE:
            self.implement_guard(addr, guard_op, self.mc.JNZ)
        else:
            self.implement_guard(addr, guard_op, self.mc.JZ)

    def genop_oononnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETNE(lower_byte(resloc))

    def genop_ooisnull(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm8(0))
        self.mc.MOV(resloc, imm8(0))
        self.mc.SETE(lower_byte(resloc))

    def genop_int_mod(self, op, arglocs, resloc):
        self.mc.CDQ()
        self.mc.IDIV(ecx)

    def genop_guard_int_mod_ovf(self, op, guard_op, addr, arglocs, result_loc):
        # detect the combination "eax=-sys.maxint-1, ecx=-1"
        self.mc.LEA(edx, mem(eax, sys.maxint))  # edx=-1 if eax=-sys.maxint-1
        self.mc.AND(edx, ecx)                   # edx=-1 only in the case above
        self.mc.CMP(edx, imm(-1))
        self.mc.JE(rel32(addr))
        self.mc.CDQ()
        self.mc.IDIV(ecx)

    genop_int_floordiv = genop_int_mod
    genop_guard_int_floordiv_ovf = genop_guard_int_mod_ovf

    def genop_new_with_vtable(self, op, arglocs, result_loc):
        assert result_loc is eax
        loc_size, loc_vtable = arglocs
        self.mc.PUSH(loc_vtable)
        self.call(self.malloc_func_addr, [loc_size], eax)
        # xxx ignore NULL returns for now
        self.mc.POP(mem(eax, 0))

    # same as malloc varsize after all
    def genop_new(self, op, arglocs, result_loc):
        assert result_loc is eax
        loc_size = arglocs[0]
        self.call(self.malloc_func_addr, [loc_size], eax)

    def genop_getfield_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc = arglocs
        assert isinstance(size_loc, IMM32)
        size = size_loc.value
        if size == 1:
            self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc))
        elif size == WORD:
            self.mc.MOV(resloc, addr_add(base_loc, ofs_loc))
        else:
            raise NotImplementedError("getfield size = %d" % size)

    genop_getfield_gc_pure = genop_getfield_gc

    def genop_getarrayitem_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, scale, ofs = arglocs
        assert isinstance(ofs, IMM32)
        assert isinstance(scale, IMM32)
        if scale.value == 0:
            self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc, ofs.value,
                                            scale.value))
        elif scale.value == 2:
            self.mc.MOV(resloc, addr_add(base_loc, ofs_loc, ofs.value,
                                         scale.value))
        else:
            print "[asmgen]setarrayitem unsupported size: %d" % scale.value
            raise NotImplementedError()

    genop_getfield_raw = genop_getfield_gc
    genop_getarrayitem_gc_pure = genop_getarrayitem_gc

    def genop_discard_setfield_gc(self, op, arglocs):
        base_loc, ofs_loc, size_loc, value_loc = arglocs
        assert isinstance(size_loc, IMM32)
        size = size_loc.value
        if size == WORD:
            self.mc.MOV(addr_add(base_loc, ofs_loc), value_loc)
        elif size == 2:
            raise NotImplementedError("shorts and friends")
            self.mc.MOV(addr16_add(base_loc, ofs_loc), lower_2_bytes(value_loc))
        elif size == 1:
            self.mc.MOV(addr8_add(base_loc, ofs_loc), lower_byte(value_loc))
        else:
            print "[asmgen]setfield addr size %d" % size
            raise NotImplementedError("Addr size %d" % size)

    def genop_discard_setarrayitem_gc(self, op, arglocs):
        base_loc, ofs_loc, value_loc, scale_loc, baseofs = arglocs
        assert isinstance(baseofs, IMM32)
        assert isinstance(scale_loc, IMM32)
        if scale_loc.value == 2:
            self.mc.MOV(addr_add(base_loc, ofs_loc, baseofs.value,
                                 scale_loc.value), value_loc)
        elif scale_loc.value == 0:
            self.mc.MOV(addr8_add(base_loc, ofs_loc, baseofs.value,
                                 scale_loc.value), lower_byte(value_loc))
        else:
            raise NotImplementedError("scale = %d" % scale_loc.value)

    def genop_discard_strsetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                              self.cpu.translate_support_code)
        assert itemsize == 1
        self.mc.MOV(addr8_add(base_loc, ofs_loc, basesize),
                    lower_byte(val_loc))

    def genop_discard_unicodesetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                              self.cpu.translate_support_code)
        assert itemsize == 4
        self.mc.MOV(addr_add(base_loc, ofs_loc, basesize, 2), val_loc)

    genop_discard_setfield_raw = genop_discard_setfield_gc

    def genop_strlen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_unicodelen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_arraylen_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        self.mc.MOV(resloc, addr_add(base_loc, imm(0)))

    def genop_strgetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        self.mc.MOVZX(resloc, addr8_add(base_loc, ofs_loc, basesize))

    def genop_unicodegetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        assert itemsize == 4
        self.mc.MOV(resloc, addr_add(base_loc, ofs_loc, basesize, 2))

    def make_merge_point(self, tree, locs):
        pos = self.mc.tell()
        tree._x86_compiled = pos
        #tree.comeback_bootstrap_addr = self.assemble_comeback_bootstrap(pos,
        #                                                locs, stacklocs)

    def patch_jump(self, old_pos, new_pos, oldlocs, newlocs, olddepth, newdepth):
        if len(oldlocs) != len(newlocs):
            # virtualizable mess
            return
        if not we_are_translated():
            assert str(oldlocs) == str(newlocs)
        if newdepth != olddepth:
            mc2 = self.mcstack.next_mc()
            pos = mc2.tell()
            diff = olddepth - newdepth
            for loc in newlocs:
                if isinstance(loc, MODRM):
                    has_modrm = True
                    break
            else:
                has_modrm = False
            extra_place = stack_pos(olddepth - 1) # this is unused
            if diff > 0:
                if has_modrm:
                    mc2.MOV(extra_place, eax)
                    for i in range(len(newlocs)):
                        loc = newlocs[i]
                        if isinstance(loc, MODRM):
                            mc2.MOV(eax, loc)
                            # diff is negative!
                            mc2.MOV(stack_pos(loc.position + diff), eax)
                    mc2.MOV(eax, extra_place)
                mc2.ADD(esp, imm32((diff) * WORD))
            else:
                if has_modrm:
                    mc2.MOV(extra_place, eax)
                    for i in range(len(newlocs) -1, -1, -1):
                        loc = newlocs[i]
                        if isinstance(loc, MODRM):
                            mc2.MOV(eax, loc)
                            # diff is negative!
                            mc2.MOV(stack_pos(loc.position + diff), eax)
                    mc2.MOV(eax, extra_place)
                mc2.SUB(esp, imm32((-diff) * WORD))
            mc2.JMP(rel32(new_pos))
            self.mcstack.give_mc_back(mc2)
        else:
            pos = new_pos
        mc = codebuf.InMemoryCodeBuilder(old_pos, old_pos +
                                         MachineCodeBlockWrapper.MC_SIZE)
        mc.JMP(rel32(pos))
        mc.done()

#     def genop_discard_return(self, op, locs):
#         if op.args:
#             loc = locs[0]
#             if loc is not eax:
#                 self.mc.MOV(eax, loc)
#         self.mc.ADD(esp, imm(FRAMESIZE))
#         # copy exception to some safe place and clean the original
#         # one
#         self.mc.MOV(ecx, heap(self._exception_addr))
#         self.mc.MOV(heap(self._exception_bck_addr), ecx)
#         self.mc.MOV(ecx, addr_add(imm(self._exception_addr), imm(WORD)))
#         self.mc.MOV(addr_add(imm(self._exception_bck_addr), imm(WORD)),
#                      ecx)
#         # clean up the original exception, we don't want
#         # to enter more rpython code with exc set
#         self.mc.MOV(heap(self._exception_addr), imm(0))
#         self.mc.RET()

    def genop_discard_jump(self, op, locs):
        targetmp = op.jump_target
        self.jumps_to_look_at.append((op, self.mc.tell()))
        self.mc.JMP(rel32(targetmp._x86_compiled))

    def genop_guard_guard_true(self, op, ign_1, addr, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(addr, op, self.mc.JZ)

    def genop_guard_guard_no_exception(self, op, ign_1, addr, locs, ign_2):
        loc = locs[0]
        self.mc.MOV(loc, heap(self._exception_addr))
        self.mc.TEST(loc, loc)
        self.implement_guard(addr, op, self.mc.JNZ)

    def genop_guard_guard_exception(self, op, ign_1, addr, locs, resloc):
        loc = locs[0]
        loc1 = locs[1]
        self.mc.MOV(loc1, heap(self._exception_addr))
        self.mc.CMP(loc1, loc)
        self.implement_guard(addr, op, self.mc.JNE)
        if resloc is not None:
            self.mc.MOV(resloc, addr_add(imm(self._exception_addr), imm(WORD)))
        self.mc.MOV(heap(self._exception_addr), imm(0))

    def genop_guard_guard_false(self, op, ign_1, addr, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(addr, op, self.mc.JNZ)

    def genop_guard_guard_value(self, op, ign_1, addr, locs, ign_2):
        self.mc.CMP(locs[0], locs[1])
        self.implement_guard(addr, op, self.mc.JNE)

    def genop_guard_guard_class(self, op, ign_1, addr, locs, ign_2):
        offset = 0    # XXX for now, the vtable ptr is at the start of the obj
        self.mc.CMP(mem(locs[0], offset), locs[1])
        self.implement_guard(addr, op, self.mc.JNE)

    #def genop_discard_guard_nonvirtualized(self, op):
    #    STRUCT = op.args[0].concretetype.TO
    #    offset, size = symbolic.get_field_token(STRUCT, 'vable_rti')
    #    assert size == WORD
    #    self.load(eax, op.args[0])
    #    self.mc.CMP(mem(eax, offset), imm(0))
    #    self.implement_guard(op, self.mc.JNE)

    def implement_guard_recovery(self, guard_op, regalloc, ovf=False):
        oldmc = self.mc
        self.mc = self.mc2
        self.mc2 = self.mcstack.next_mc()
        addr = self.mc.tell()
        exc = False
        if ovf:
            regalloc.position = -1
            self.generate_ovf_set()
            exc = True
        if (guard_op.opnum == rop.GUARD_EXCEPTION or
            guard_op.opnum == rop.GUARD_NO_EXCEPTION):
            exc = True
        # XXX this is a heuristics to detect whether we're handling this
        # exception or not. We should have a bit better interface to deal
        # with that I fear
        if (exc and (guard_op.suboperations[0].opnum == rop.GUARD_EXCEPTION or
                    guard_op.suboperations[0].opnum == rop.GUARD_NO_EXCEPTION)):
            exc = False
        regalloc.walk_guard_ops(guard_op.inputargs, guard_op.suboperations, exc)
        self.mcstack.give_mc_back(self.mc2)
        self.mc2 = self.mc
        self.mc = oldmc
        return addr

    def generate_failure(self, op, locs, guard_index, exc):
        pos = self.mc.tell()
        for i in range(len(locs)):
            loc = locs[i]
            if isinstance(loc, REG):
                self.mc.MOV(addr_add(imm(self.fail_box_addr), imm(i*WORD)), loc)
        for i in range(len(locs)):
            loc = locs[i]
            if not isinstance(loc, REG):
                self.mc.MOV(eax, loc)
                self.mc.MOV(addr_add(imm(self.fail_box_addr), imm(i*WORD)), eax)
        if self.debug_markers:
            self.mc.MOV(eax, imm(pos))
            self.mc.MOV(addr_add(imm(self.fail_box_addr),
                                 imm(len(locs) * WORD)),
                                 eax)
        if exc:
            self.generate_exception_handling(eax)
        self.places_to_patch_framesize.append(self.mc.tell())
        self.mc.ADD(esp, imm32(0))
        self.mc.MOV(eax, imm(guard_index))
        self.mc.RET()

    def generate_ovf_set(self):
        ovf_error_vtable = self.cpu.cast_adr_to_int(self._ovf_error_vtable)
        self.mc.MOV(addr_add(imm(self._exception_addr), imm(0)),
                    imm(ovf_error_vtable))
        ovf_error_instance = self.cpu.cast_adr_to_int(self._ovf_error_inst)
        self.mc.MOV(addr_add(imm(self._exception_addr), imm(WORD)),
                    imm(ovf_error_instance))

    def generate_exception_handling(self, loc):
        self.mc.MOV(loc, heap(self._exception_addr))
        self.mc.MOV(heap(self._exception_bck_addr), loc)
        self.mc.MOV(loc, addr_add(imm(self._exception_addr), imm(WORD)))
        self.mc.MOV(addr_add(imm(self._exception_bck_addr), imm(WORD)), loc)
        # clean up the original exception, we don't want
        # to enter more rpython code with exc set
        self.mc.MOV(heap(self._exception_addr), imm(0))

    @specialize.arg(3)
    def implement_guard(self, addr, guard_op, emit_jump):
        emit_jump(rel32(addr))

    def genop_call(self, op, arglocs, resloc):
        sizeloc = arglocs[0]
        assert isinstance(sizeloc, IMM32)
        size = sizeloc.value
        arglocs = arglocs[1:]
        extra_on_stack = 0
        for i in range(len(op.args) - 1, 0, -1):
            v = op.args[i]
            loc = arglocs[i]
            if not isinstance(loc, MODRM):
                self.mc.PUSH(loc)
            else:
                # we need to add a bit, ble
                self.mc.PUSH(stack_pos(loc.position + extra_on_stack))
            extra_on_stack += 1
        if isinstance(op.args[0], Const):
            x = rel32(op.args[0].getint())
        else:
            x = arglocs[0]
            if isinstance(x, MODRM):
                x = stack_pos(x.position + extra_on_stack)
        self.mc.CALL(x)
        self.mc.ADD(esp, imm(WORD * extra_on_stack))
        if size == 1:
            self.mc.AND(eax, imm(0xff))
        elif size == 2:
            self.mc.AND(eax, imm(0xffff))

    genop_call_pure = genop_call

    def not_implemented_op_discard(self, op, arglocs):
        print "not implemented operation: %s" % op.getopname()
        raise NotImplementedError

    def not_implemented_op(self, op, arglocs, resloc):
        print "not implemented operation with res: %s" % op.getopname()
        raise NotImplementedError

    def not_implemented_op_guard(self, op, regalloc, arglocs, resloc, descr):
        print "not implemented operation (guard): %s" % op.getopname()
        raise NotImplementedError

    #def genop_call__1(self, op, arglocs, resloc):
    #    self.gen_call(op, arglocs, resloc)
    #    self.mc.MOVZX(eax, al)

    #def genop_call__2(self, op, arglocs, resloc):
    #    # XXX test it test it test it
    #    self.gen_call(op, arglocs, resloc)
    #    self.mc.MOVZX(eax, eax)

genop_discard_list = [Assembler386.not_implemented_op_discard] * rop._LAST
genop_list = [Assembler386.not_implemented_op] * rop._LAST
genop_guard_list = [Assembler386.not_implemented_op_guard] * rop._LAST

for name, value in Assembler386.__dict__.iteritems():
    if name.startswith('genop_discard_'):
        opname = name[len('genop_discard_'):]
        num = getattr(rop, opname.upper())
        genop_discard_list[num] = value
    elif name.startswith('genop_guard_') and name != 'genop_guard_exception': 
        opname = name[len('genop_guard_'):]
        num = getattr(rop, opname.upper())
        genop_guard_list[num] = value
    elif name.startswith('genop_'):
        opname = name[len('genop_'):]
        num = getattr(rop, opname.upper())
        genop_list[num] = value

def addr_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap(reg_or_imm1.value + offset +
                        (reg_or_imm2.value << scale))
        else:
            return memSIB(None, reg_or_imm2, scale, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem(reg_or_imm1, offset + (reg_or_imm2.value << scale))
        else:
            return memSIB(reg_or_imm1, reg_or_imm2, scale, offset)

def addr8_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap8(reg_or_imm1.value + (offset << scale) +
                         reg_or_imm2.value)
        else:
            return memSIB8(None, reg_or_imm2, scale, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem8(reg_or_imm1, (offset << scale) + reg_or_imm2.value)
        else:
            return memSIB8(reg_or_imm1, reg_or_imm2, scale, offset)

def addr16_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    if isinstance(reg_or_imm1, IMM32):
        if isinstance(reg_or_imm2, IMM32):
            return heap16(reg_or_imm1.value + (offset << scale) +
                         reg_or_imm2.value)
        else:
            return memSIB16(None, reg_or_imm2, scale, reg_or_imm1.value + offset)
    else:
        if isinstance(reg_or_imm2, IMM32):
            return mem16(reg_or_imm1, (offset << scale) + reg_or_imm2.value)
        else:
            return memSIB16(reg_or_imm1, reg_or_imm2, scale, offset)

def addr_add_const(reg_or_imm1, offset):
    if isinstance(reg_or_imm1, IMM32):
        return heap(reg_or_imm1.value + offset)
    else:
        return mem(reg_or_imm1, offset)
