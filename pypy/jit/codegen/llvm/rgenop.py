from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.llvm import llvmjit
from pypy.rlib.objectmodel import we_are_translated


def log(s):
    if not we_are_translated():
        print str(s)


class Count(object):
    n_vars = 0
    n_labels = 0

count = Count()


class Var(GenVar):

    def __init__(self):
        self.name = '%v' + str(count.n_vars)
        count.n_vars += 1

    def operand(self):
        return self.type() + ' ' + self.name

    def operand2(self):
        return self.name

    def type(self):
        return 'int'


class VarAddr(Var):

    def __init__(self, v, asm):
        self.name = '%p' + v.name[2:]
        asm.append(' %s=alloca %s' % (self.operand2(), v.type())) #note: sideeffect!

    def type(self):
        return 'int*'


class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def operand(self):
        return self.type() + ' ' + str(self.value)

    def operand2(self):
        return str(self.value)

    def type(self):
        return 'int'

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)


class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

    def operand(self):
        return self.type() + ' ' + str(llmemory.cast_adr_to_int(self.addr))

    def operand2(self):
        return str(llmemory.cast_adr_to_int(self.addr))

    def type(self):
        return 'int*'

    @specialize.arg(1)
    def revealconst(self, T):
        if T is llmemory.Address:
            return self.addr
        elif isinstance(T, lltype.Ptr):
            return llmemory.cast_adr_to_ptr(self.addr, T)
        elif T is lltype.Signed:
            return llmemory.cast_adr_to_int(self.addr)
        else:
            assert 0, "XXX not implemented"


class Label(GenLabel):

    def __init__(self):
        self.label = 'L' + str(count.n_labels)
        count.n_labels += 1

    def operand(self):
        return self.type() + ' %' + self.label

    def operand2(self):
        return self.label + ':'

    def type(self):
        return 'label'


class EntryLabel(Label):

    def __init(self):
        self.label = 'L_' #Block-label for alloca's. The label is never put in the source!


class FlexSwitch(CodeGenSwitch):

    def __init__(self, rgenop):
        log('FlexSwitch.__init__')
        self.rgenop = rgenop
        #self.default_case_addr = 0

    def initialize(self, builder, gv_exitswitch):
        log('FlexSwitch.initialize TODO')
        #mc = builder.mc
        #mc.MOV(eax, gv_exitswitch.operand(builder))
        #self.saved_state = builder._save_state()
        #self._reserve(mc)

    def _reserve(self, mc):
        log('FlexSwitch._reserve TODO')
        #RESERVED = 11*4+5      # XXX quite a lot for now :-/
        #pos = mc.tell()
        #mc.UD2()
        #mc.write('\x00' * (RESERVED-1))
        #self.nextfreepos = pos
        #self.endfreepos = pos + RESERVED

    def _reserve_more(self):
        log('FlexSwitch._reserve_more TODO')
        #start = self.nextfreepos
        #end   = self.endfreepos
        #newmc = self.rgenop.open_mc()
        #self._reserve(newmc)
        #self.rgenop.close_mc(newmc)
        #fullmc = InMemoryCodeBuilder(start, end)
        #fullmc.JMP(rel32(self.nextfreepos))
        #fullmc.done()

    def add_case(self, gv_case):
        log('FlexSwitch.add_case TODO')
        #rgenop = self.rgenop
        #targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        #target_addr = targetbuilder.mc.tell()
        #try:
        #    self._add_case(gv_case, target_addr)
        #except CodeBlockOverflow:
        #    self._reserve_more()
        #    self._add_case(gv_case, target_addr)
        #return targetbuilder

    def _add_case(self, gv_case, target_addr):
        log('FlexSwitch._add_case TODO')
        #start = self.nextfreepos
        #end   = self.endfreepos
        #mc = InMemoryCodeBuilder(start, end)
        #mc.CMP(eax, gv_case.operand(None))
        #mc.JE(rel32(target_addr))
        #pos = mc.tell()
        #if self.default_case_addr:
        #    mc.JMP(rel32(self.default_case_addr))
        #else:
        #    illegal_start = mc.tell()
        #    mc.JMP(rel32(0))
        #    ud2_addr = mc.tell()
        #    mc.UD2()
        #    illegal_mc = InMemoryCodeBuilder(illegal_start, end)
        #    illegal_mc.JMP(rel32(ud2_addr))
        #mc.done()
        #self.nextfreepos = pos

    def add_default(self):
        log('FlexSwitch.add_default TODO')
        #rgenop = self.rgenop
        #targetbuilder = Builder._new_from_state(rgenop, self.saved_state)
        #self.default_case_addr = targetbuilder.mc.tell()
        #start = self.nextfreepos
        #end   = self.endfreepos
        #mc = InMemoryCodeBuilder(start, end)
        #mc.JMP(rel32(self.default_case_addr))
        #mc.done()
        #return targetbuilder


class Builder(object):  #changed baseclass from (GenBuilder) for better error messages

    def __init__(self, rgenop, asm, prev_block_closed=False):
        self.label = EntryLabel()
        log('%s Builder.__init__' % self.label.operand2())
        self.rgenop = rgenop
        self.asm = asm  #list of llvm assembly source code lines
        self.prev_block_closed = prev_block_closed #XXX might be a problem with empty blocks

    # ----------------------------------------------------------------
    # The public Builder interface

    def end(self):
        log('%s Builder.end' % self.label.operand2())
        self.rgenop.asms.append(['}'])
        #log(self.rgenop.asms)
        asm_string = ''
        for asm in self.rgenop.asms:
            asm_string += '\n'.join(asm) + '\n'
        self.rgenop.asms = None #XXX or [] ?
        log(asm_string)
        llvmjit.parse(asm_string)
        llvmjit.transform(3) #optimize module (should be on functions actually)
        function   = llvmjit.getNamedFunction(self.rgenop.name)
        entrypoint = llvmjit.getPointerToFunctionAsInt(function) #how to cast a ctypes ptr to int?
        self.rgenop.funcname[entrypoint] = self.rgenop.funcname[self.rgenop.gv_entrypoint.value]
        self.rgenop.gv_entrypoint.value = entrypoint

    def _write_prologue(self, sigtoken):
        numargs = sigtoken     # for now
        inputargs_gv = [Var() for i in range(numargs)]
        self.asm.append('int %%%s(%s){' % (
            self.rgenop.name, ','.join([v.operand() for v in inputargs_gv])))

        inputargs_gv_ = []
        for v in inputargs_gv:
            v_ = VarAddr(v, self.asm)
            self.asm.append(' store %s,%s %s' % (v.operand(), v_.type(), v_.operand2()))
            inputargs_gv_.append(v_)

        #self.asm.append(self.label.operand2())
        #note: alloca's should be appended to self.rgenop.asms[0]
        self.asm = self.rgenop.open_asm() #note: previous self.asm already appended to self.asms
        return inputargs_gv_ #XXX make this inputargs_gv_

    def _close(self):
        log('%s Builder._close' % self.label.operand2())
        #self.rgenop.close_asm(self.asm)
        self.asm = None
        self.prev_block_closed = True
        #self.mc.done()
        #self.rgenop.close_mc(self.mc)
        #self.mc = None

    def _fork(self):
        log('%s Builder._fork' % self.label.operand2())
        self.prev_block_closed = True
        targetbuilder = self.rgenop.openbuilder(False)
        targetbuilder.asm.append(targetbuilder.label.operand2()) #another HACK
        return targetbuilder

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        #log('%s Builder.genop1' % self.label.operand2())
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        #log('%s Builder.genop2' % self.label.operand2())
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def _rgenop2_generic(self, llvm_opcode, gv_arg1, gv_arg2):
        log('%s Builder._rgenop2_generic %s %s,%s' % (
            self.label.operand2(), llvm_opcode, gv_arg1.operand(), gv_arg2.operand2()))

        #XXX can't this be shorter?
        if gv_arg1.is_const or isinstance(gv_arg1, VarAddr):
            gv_arg1_ = gv_arg1
        else:
            gv_arg1_ = VarAddr(gv_arg1, self.rgenop.asms[0])
        if isinstance(gv_arg1_, VarAddr):
            gv_arg1_tmp = Var()
            self.asm.append(' %s=load %s' % (gv_arg1_tmp.operand2(), gv_arg1_.operand()))
        else:
            gv_arg1_tmp = gv_arg1_

        if gv_arg2.is_const or isinstance(gv_arg2, VarAddr):
            gv_arg2_ = gv_arg2
        else:
            gv_arg2_ = VarAddr(gv_arg2, self.rgenop.asms[0])
        if isinstance(gv_arg2_, VarAddr):
            gv_arg2_tmp = Var()
            self.asm.append(' %s=load %s' % (gv_arg2_tmp.operand2(), gv_arg2_.operand()))
        else:
            gv_arg2_tmp = gv_arg2_

        gv_result = Var()
        self.asm.append(' %s=%s %s,%s' % (
            gv_result.operand2(), llvm_opcode, gv_arg1_tmp.operand(), gv_arg2_tmp.operand2()))

        if llvm_opcode[:3] == 'set': #HACK
            #XXX We assume there will always be a jump_if_true/false right after an op_int_eq/etc.
            #    Because we don't yet keep track of non-ints it will be difficult to do the
            #    right thing in jump_if_true/false. So this is a hack we want to fix later!
            return gv_result

        gv_result_ = VarAddr(gv_result, self.rgenop.asms[0])
        self.asm.append(' store %s,%s' % (gv_result.operand(), gv_result_.operand()))

        return gv_result_

    def op_int_add(self, gv_x, gv_y):       return self._rgenop2_generic('add'  , gv_x, gv_y)
    def op_int_sub(self, gv_x, gv_y):       return self._rgenop2_generic('sub'  , gv_x, gv_y)
    def op_int_mul(self, gv_x, gv_y):       return self._rgenop2_generic('mul'  , gv_x, gv_y)
    def op_int_floordiv(self, gv_x, gv_y):  return self._rgenop2_generic('sdiv' , gv_x, gv_y)
    def op_int_mod(self, gv_x, gv_y):       return self._rgenop2_generic('rem'  , gv_x, gv_y)
    def op_int_and(self, gv_x, gv_y):       return self._rgenop2_generic('and'  , gv_x, gv_y)
    def op_int_or(self, gv_x, gv_y):        return self._rgenop2_generic('or'   , gv_x, gv_y)
    def op_int_xor(self, gv_x, gv_y):       return self._rgenop2_generic('xor'  , gv_x, gv_y)
    def op_int_lt(self, gv_x, gv_y):        return self._rgenop2_generic('setlt', gv_x, gv_y)
    def op_int_le(self, gv_x, gv_y):        return self._rgenop2_generic('setle', gv_x, gv_y)
    def op_int_eq(self, gv_x, gv_y):        return self._rgenop2_generic('seteq', gv_x, gv_y)
    def op_int_ne(self, gv_x, gv_y):        return self._rgenop2_generic('setne', gv_x, gv_y)
    def op_int_gt(self, gv_x, gv_y):        return self._rgenop2_generic('setgt', gv_x, gv_y)
    def op_int_ge(self, gv_x, gv_y):        return self._rgenop2_generic('setge', gv_x, gv_y)

    #def op_int_neg(self, gv_x):
    #def op_int_abs(self, gv_x):
    #def op_int_invert(self, gv_x):
    #def op_int_lshift(self, gv_x, gv_y):
    #def op_int_rshift(self, gv_x, gv_y):
    #def op_bool_not(self, gv_x):
    #def op_cast_bool_to_int(self, gv_x):

    def enter_next_block(self, kinds, args_gv):
        label = Label()
        log('%s Builder.enter_next_block (was %s), prev_block_closed=%s, %s' % (
            label.operand2(), self.label.operand2(), str(self.prev_block_closed),
            [v.operand() for v in args_gv]))
        self.label = label
        if not self.prev_block_closed: #there are not always explicit branches to blocks
            self.asm.append(' br ' + self.label.operand() + ' ;fixup')
        self.asm.append(self.label.operand2())
        #XXX These phi nodes seems to get really messy especially with the 'fixup' branches.
        #XXX Perhaps using alloca's and omitting the phi nodes does make some sense.
        self.asm.append(' ;phi %s' % [v.operand() for v in args_gv])
        self.prev_block_closed = False #easiest, but might be a problem with empty blocks
        return self.label
        #arg_positions = []
        #seen = {}
        #for i in range(len(args_gv)):
        #    gv = args_gv[i]
        #    # turn constants into variables; also make copies of vars that
        #    # are duplicate in args_gv
        #    if not isinstance(gv, Var) or gv.stackpos in seen:
        #        gv = args_gv[i] = self.returnvar(gv.operand(self))
        #    # remember the var's position in the stack
        #    arg_positions.append(gv.stackpos)
        #    seen[gv.stackpos] = None
        #return Label(self.mc.tell(), arg_positions, self.stackdepth)

    def jump_if_false(self, gv_condition):
        log('%s Builder.jump_if_false %s' % (self.label.operand2(), gv_condition.operand()))
        targetbuilder = self._fork()
        
        #XXX the next couple of lines are incorrect! Should we make this a two-pass algorithm?
        no_branch = Label() #XXX should be this Builder's next 'enter_next_block' label
        count.n_labels -= 1 #HACK HACK HACK
        #XXX will need to keep type of Vars to get rid of the hardcoded 'bool' in the next line
        targetlabel = targetbuilder.label

        self.asm.append(' br bool %s,%s,%s' % (
            gv_condition.operand2(), no_branch.operand(), targetlabel.operand()))
        #XXX self.asm.append(no_branch.operand2())
        #self.mc.CMP(gv_condition.operand(self), imm8(0))
        #self.mc.JNE(rel32(targetbuilder.mc.tell()))
        return targetbuilder

    def jump_if_true(self, gv_condition):
        log('%s Builder.jump_if_true %s' % (self.label.operand2(), gv_condition.operand()))
        targetbuilder = self._fork()

        #XXX the next couple of lines are incorrect! Should we make this a two-pass algorithm?
        no_branch = Label() #XXX should be this Builder's next 'enter_next_block' label
        count.n_labels -= 1 #HACK HACK HACK
        #XXX will need to keep type (bool/int/float/...) of Vars
        targetlabel = targetbuilder.label

        self.asm.append(' br bool %s,%s,%s' % (
            gv_condition.operand2(), targetlabel.operand(), no_branch.operand()))
        #XXX self.asm.append(no_branch.operand2())
        #self.mc.CMP(gv_condition.operand(self), imm8(0))
        #self.mc.JNE(rel32(targetbuilder.mc.tell()))
        return targetbuilder

    def op_int_is_true(self, gv_x_):
        log('%s Build.op_int_is_true %s' % (self.label.operand2(), gv_x_.operand()))
        if isinstance(gv_x_, VarAddr):
            gv_x = Var()
            self.asm.append(' %s=load %s' % (gv_x.operand2(), gv_x_.operand()))
        else:
            gv_x = gv_x_
        gv_result = Var() #XXX need to mark it a 'bool' somehow
        self.asm.append(' %s=trunc %s to bool' % (gv_result.operand2(), gv_x.operand()))
        return gv_result

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        log('%s Builder.genop_call %s,%s,%s' % (
            self.label.operand2(), sigtoken, gv_fnptr, [v.operand() for v in args_gv]))
        numargs = sigtoken #for now
        gv_returnvar = Var()
        #XXX we probably need to call an address directly if we can't resolve the funcname
        self.asm.append(' %s=call %s(%s)' % (
                        gv_returnvar.operand2(),
                        self.rgenop.funcname[gv_fnptr.value],
                        ','.join([v.operand() for v in args_gv])))
        return gv_returnvar
    
    def finish_and_return(self, sigtoken, gv_returnvar_):
        log('%s Builder.finish_and_return %s,%s' % (
            self.label.operand2(), sigtoken, gv_returnvar_.operand()))

        if isinstance(gv_returnvar_, VarAddr):
            gv_returnvar = Var()
            self.asm.append(' %s=load %s' % (gv_returnvar.operand2(), gv_returnvar_.operand()))
        else:
            gv_returnvar = gv_returnvar_
        self.asm.append(' ret ' + gv_returnvar.operand())
        #numargs = sigtoken      # for now
        #initialstackdepth = numargs + 1
        #self.mc.MOV(eax, gv_returnvar.operand(self))
        #self.mc.ADD(esp, imm(WORD * (self.stackdepth - initialstackdepth)))
        #self.mc.RET()
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        gv = [v.operand() for v in outputargs_gv]
        log('%s Builder.finish_and_goto %s,%s' % (
            self.label.operand2(), gv, target.operand()))
        self.asm.append(' br %s ;%s' % (target.operand(), gv))
        #remap_stack_layout(self, outputargs_gv, target)
        #self.mc.JMP(rel32(target.startaddr))
        self._close()

    def flexswitch(self, gv_exitswitch):
        log('%s Builder.flexswitch %s' % (self.label.operand2(), gv_exitswitch.operand()))
        self.asm.append(' ;flexswitch ' + gv_exitswitch.operand())
        result = FlexSwitch(self.rgenop)
        result.initialize(self, gv_exitswitch)
        self._close()
        return result

    def show_incremental_progress(self):
        log('%s Builder.show_incremental_progress' % self.label.operand())
        pass


class RLLVMGenOp(object):   #changed baseclass from (AbstractRGenOp) for better error messages

    funcname = {} #HACK for looking up function names given a pre/post compilation function pointer
    funcused = {} #we rename functions when encountered multiple times (for test_branching_compile)

    def open_asm(self):
        asm = []
        self.asms.append(asm)
        return asm

    #def close_asm(self, asm):
    #    self.asms.append(asm)

    # ----------------------------------------------------------------
    # the public RGenOp interface

    def openbuilder(self, prev_block_closed):
        #log('RLLVMGenOp.openbuilder %s' % (str(prev_block_closed))
        return Builder(self, self.open_asm(), prev_block_closed)

    def newgraph(self, sigtoken, name):
        if name in self.funcused:
            self.funcused[name] += 1
            name = '%s_%d' % (name, self.funcused[name])
        else:
            self.funcused[name] = 0

        log('RLLVMGenOp.newgraph %s,%s' % (sigtoken, name))
        self.asms = []
        numargs = sigtoken          # for now
        self.name = name
        builder = self.openbuilder(False) #enables initial label
        inputargs_gv = builder._write_prologue(sigtoken)
        n = len(self.funcname) * 2 + 1     #+1 so we recognize these pre compilation 'pointers'
        self.funcname[n] = 'int %' + name    #XXX 'int' hardcoded currently as in write_prologue()
        self.gv_entrypoint = IntConst(n)    #note: updated by Builder.end() (i.e after compilation)
        return builder, self.gv_entrypoint, inputargs_gv

    @specialize.genconst(1)
    def genconst(self, llvalue):    #i386 version (ppc version is slightly different)
        T = lltype.typeOf(llvalue)  
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            assert 0, "XXX not implemented"

    # attached later constPrebuiltGlobal = global_rgenop.genconst

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return llmemory.offsetof(T, name)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        if isinstance(T, lltype.Array):
            return RI386GenOp.arrayToken(T)
        else:
            # var-sized structs
            arrayfield = T._arrayfld
            ARRAYFIELD = getattr(T, arrayfield)
            arraytoken = RI386GenOp.arrayToken(ARRAYFIELD)
            length_offset, items_offset, item_size = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return (arrayfield_offset+length_offset,
                    arrayfield_offset+items_offset,
                    item_size)

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        return None     # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return len(FUNCTYPE.ARGS)     # for now

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            assert 0, "XXX not implemented"


global_rgenop = RLLVMGenOp()
RLLVMGenOp.constPrebuiltGlobal = global_rgenop.genconst

