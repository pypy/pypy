import py
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

    def newlabel(self):
        label = 'L%d' % (self.n_labels,)
        self.n_labels += 1
        return label

count = Count()


class Var(GenVar):

    def __init__(self, type):
        self.n = count.n_vars
        self.type = type
        count.n_vars += 1

    def operand(self):
        return '%s %%v%d' % (self.type, self.n)

    def operand2(self):
        return '%%v%d' % (self.n,)


class IntConst(GenConst):
    type = 'int'

    def __init__(self, value):
        self.value = value

    def operand(self):
        return '%s %s' % (self.type, self.value)

    def operand2(self):
        return str(self.value)

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)


class AddrConst(GenConst):
    type = 'int*'

    def __init__(self, addr):
        self.addr = addr

    def operand(self):
        return '%s %s' % (self.type, llmemory.cast_adr_to_int(self.addr))

    def operand2(self):
        return str(llmemory.cast_adr_to_int(self.addr))

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
        #XXX ERIC assert sourcevartypes == targetvartypes

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
        lines.append('%s %%%s(%s){' % (
            restype,
            self.name,
            ','.join([v.operand() for v in self.inputargs])))
        lines.append(self.label + ':')
        lines.append(' br label %%%s' % (self.startblocklabel,))


class EpilogueBlock(Block):
    def writecode(self, lines):
        lines.append('}')


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

    # ----------------------------------------------------------------
    # The public Builder interface

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        #log('%s Builder.genop1' % self.block.label)
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        #log('%s Builder.genop2' % self.block.label)
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def _rgenop2_generic(self, llvm_opcode, gv_arg1, gv_arg2, restype='int'):
        log('%s Builder._rgenop2_generic %s %s,%s' % (
            self.block.label, llvm_opcode, gv_arg1.operand(), gv_arg2.operand2()))
        gv_result = Var(restype)
        self.asm.append(' %s=%s %s,%s' % (
            gv_result.operand2(), llvm_opcode, gv_arg1.operand(), gv_arg2.operand2()))
        return gv_result

    def op_int_add(self, gv_x, gv_y):       return self._rgenop2_generic('add' , gv_x, gv_y)
    def op_int_sub(self, gv_x, gv_y):       return self._rgenop2_generic('sub' , gv_x, gv_y)
    def op_int_mul(self, gv_x, gv_y):       return self._rgenop2_generic('mul' , gv_x, gv_y)
    def op_int_floordiv(self, gv_x, gv_y):  return self._rgenop2_generic('sdiv', gv_x, gv_y)
    def op_int_mod(self, gv_x, gv_y):       return self._rgenop2_generic('rem' , gv_x, gv_y)
    def op_int_and(self, gv_x, gv_y):       return self._rgenop2_generic('and' , gv_x, gv_y)
    def op_int_or(self, gv_x, gv_y):        return self._rgenop2_generic('or'  , gv_x, gv_y)
    def op_int_xor(self, gv_x, gv_y):       return self._rgenop2_generic('xor' , gv_x, gv_y)

    def op_int_lshift(self, gv_x, gv_y):
        gv_y_ubyte = Var('ubyte')
        self.asm.append(' %s=cast %s to ubyte' % (gv_y_ubyte.operand2(), gv_y.operand()))
        gv_result = Var(gv_x.type)
        self.asm.append(' %s=shl %s,%s' % (
            gv_result.operand2(), gv_x.operand(), gv_y_ubyte.operand()))
        return gv_result

    def op_int_rshift(self, gv_x, gv_y):
        gv_y_ubyte = Var('ubyte')
        self.asm.append(' %s=cast %s to ubyte' % (gv_y_ubyte.operand2(), gv_y.operand()))
        gv_result = Var(gv_x.type)
        self.asm.append(' %s=shr %s,%s' % (
            gv_result.operand2(), gv_x.operand(), gv_y_ubyte.operand()))
        return gv_result

    op_uint_add = op_float_add = op_int_add
    op_uint_sub = op_float_sub = op_int_sub
    op_uint_mul = op_float_mul = op_int_mul
    op_uint_floordiv = op_float_floordiv = op_int_floordiv
    op_uint_mod = op_int_mod
    op_uint_and = op_int_and
    op_uint_or  = op_int_or
    op_uint_xor = op_int_xor
    op_uint_lshift = op_int_lshift
    op_uint_rshift = op_int_rshift

    def op_int_lt(self, gv_x, gv_y): return self._rgenop2_generic('setlt', gv_x, gv_y, 'bool')
    def op_int_le(self, gv_x, gv_y): return self._rgenop2_generic('setle', gv_x, gv_y, 'bool')
    def op_int_eq(self, gv_x, gv_y): return self._rgenop2_generic('seteq', gv_x, gv_y, 'bool')
    def op_int_ne(self, gv_x, gv_y): return self._rgenop2_generic('setne', gv_x, gv_y, 'bool')
    def op_int_gt(self, gv_x, gv_y): return self._rgenop2_generic('setgt', gv_x, gv_y, 'bool')
    def op_int_ge(self, gv_x, gv_y): return self._rgenop2_generic('setge', gv_x, gv_y, 'bool')

    op_char_lt = op_uint_lt = op_float_lt = op_int_lt
    op_char_le = op_uint_le = op_float_le = op_int_le
    op_char_eq = op_uint_eq = op_float_eq = op_unichar_eq = op_int_eq
    op_char_ne = op_uint_ne = op_float_ne = op_unichar_ne = op_int_ne
    op_char_gt = op_uint_gt = op_float_gt = op_int_gt
    op_char_ge = op_uint_ge = op_float_ge = op_int_ge

    def _rgenop1_generic(self, llvm_opcode, gv_x, restype='int'):
        log('%s Builder._rgenop1_generic %s %s' % (
            self.block.label, llvm_opcode, gv_x.operand()))
        gv_result = Var(restype)
        self.asm.append(' %s=%s %s' % (
            gv_result.operand2(), llvm_opcode, gv_x.operand()))
        return gv_resulgv_comp.operand(), t

    def op_int_neg(self, gv_x):     return self._rgenop2_generic('sub', IntConst(0), gv_x)
    def op_int_invert(self, gv_x):  return self._rgenop2_generic('xor', gv_x, IntConst(-1))
    def op_uint_invert(self, gv_x): return self._rgenop2_generic('xor', gv_x, IntConst((1<<32)-1))

    def op_int_abs(self, gv_x):
        gv_comp    = Var('bool')
        gv_abs_pos = Var(gv_x.type)
        gv_result  = Var(gv_x.type)
        self.asm.append(' %s=setgt %s,-1' % (gv_comp.operand2(), gv_x.operand()))
        self.asm.append(' %s=sub %s 0,%s' % (gv_abs_pos.operand2(), gv_x.type, gv_x.operand2()))
        self.asm.append(' %s=select %s,%s,%s' % (
            gv_result.operand2(), gv_comp.operand(), gv_x.operand(), gv_abs_pos.operand()))
        return gv_result

    #def op_bool_not(self, gv_x): #use select, xor or sub XXXX todo: did not see a test for this

    def _cast_to(self, gv_x, restype='int'):
        gv_result = Var(restype)
        self.asm.append(' %s=cast %s to %s' % (
            gv_result.operand2(), gv_x.operand(), restype))
        return gv_result

    def _cast_to_bool(self, gv_x):      return self._cast_to(gv_x, 'bool')
    def _cast_to_char(self, gv_x):      return self._cast_to(gv_x, 'ubyte')
    def _cast_to_unichar(self, gv_x):   return self._cast_to(gv_x, 'int')
    def _cast_to_int(self, gv_x):       return self._cast_to(gv_x, 'int')
    def _cast_to_uint(self, gv_x):      return self._cast_to(gv_x, 'uint')
    def _cast_to_float(self, gv_x):     return self._cast_to(gv_x, 'float')

    op_cast_char_to_bool    = _cast_to_bool
    op_cast_unichar_to_bool = _cast_to_bool
    op_cast_int_to_bool     = _cast_to_bool
    op_cast_uint_to_bool    = _cast_to_bool
    op_cast_float_to_bool   = _cast_to_bool

    op_cast_bool_to_char    = _cast_to_char
    op_cast_unichar_to_char = _cast_to_char
    op_cast_int_to_char     = _cast_to_char
    op_cast_uint_to_char    = _cast_to_char
    op_cast_float_to_char   = _cast_to_char

    op_cast_bool_to_unichar  = _cast_to_unichar
    op_cast_char_to_unichar  = _cast_to_unichar
    op_cast_int_to_unichar   = _cast_to_unichar
    op_cast_uint_to_unichar  = _cast_to_unichar
    op_cast_float_to_unichar = _cast_to_unichar

    op_cast_bool_to_int    = _cast_to_int
    op_cast_char_to_int    = _cast_to_int
    op_cast_unichar_to_int = _cast_to_int
    op_cast_uint_to_int    = _cast_to_int
    op_cast_float_to_int   = _cast_to_int

    op_cast_bool_to_uint    = _cast_to_uint
    op_cast_char_to_uint    = _cast_to_uint
    op_cast_unichar_to_uint = _cast_to_uint
    op_cast_int_to_uint     = _cast_to_uint
    op_cast_float_to_uint   = _cast_to_uint

    op_cast_bool_to_float    = _cast_to_float
    op_cast_char_to_float    = _cast_to_float
    op_cast_unichar_to_float = _cast_to_float
    op_cast_int_to_float     = _cast_to_float
    op_cast_uint_to_float    = _cast_to_float

    def enter_next_block(self, kinds, args_gv):
        # if nextlabel is None, it means that we are currently
        # generating a block; in this case we need to put a br
        # to go to the next block
        if self.nextlabel is None:
            self.nextlabel = count.newlabel()
            self.asm.append(' br label %%%s' % (self.nextlabel,))
        coming_from = self.block
        log('%s Builder leave block %s' % (
            coming_from.label, [v.operand() for v in args_gv]))

        # prepare the next block
        nextblock = BasicBlock(self.rgenop, self.nextlabel, kinds)
        log('%s Builder enter block %s' % (
            nextblock.label, [v.operand() for v in nextblock.inputargs]))
        self.block     = nextblock
        self.asm       = nextblock.asm
        self.nextlabel = None

        # link the two blocks together and update args_gv
        nextblock.add_incoming_link(coming_from, args_gv)
        for i in range(len(args_gv)):
            args_gv[i] = nextblock.inputargs[i]

        return self.block

    def jump_if_false(self, gv_condition):
        log('%s Builder.jump_if_false %s' % (self.block.label, gv_condition.operand()))
        targetbuilder = self._fork()
        self.nextlabel = count.newlabel()
        self.asm.append(' br %s,label %%%s,label %%%s' % (
            gv_condition.operand(), self.nextlabel, targetbuilder.nextlabel))
        return targetbuilder

    def jump_if_true(self, gv_condition):
        log('%s Builder.jump_if_true %s' % (self.block.label, gv_condition.operand()))
        targetbuilder = self._fork()
        self.nextlabel = count.newlabel()
        self.asm.append(' br %s,label %%%s,label %%%s' % (
            gv_condition.operand(), targetbuilder.nextlabel, self.nextlabel))
        return targetbuilder

    def _is_true(self, gv_x, nullstr='0'):
        log('%s Builder._is_true %s' % (self.block.label, gv_x.operand()))
        gv_result = Var('bool')
        self.asm.append(' %s=setne %s,%s' % (
            gv_result.operand2(), gv_x.operand(), nullstr))
        return gv_result

    op_bool_is_true = op_char_is_true = op_unichar_is_true = op_int_is_true =\
    op_uint_is_true = _is_true

    def op_float_is_true(self, gv_x):   return self._is_true(gv_x, '0.0')

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        log('%s Builder.genop_call %s,%s,%s' % (
            self.block.label, sigtoken, gv_fnptr, [v.operand() for v in args_gv]))
        argtypes, restype = sigtoken
        gv_returnvar = Var(restype)
        #XXX we probably need to call an address directly if we can't resolve the funcname
        self.asm.append(' %s=call %s(%s)' % (
                        gv_returnvar.operand2(),
                        self.rgenop.funcname[gv_fnptr.value],
                        ','.join([v.operand() for v in args_gv])))
        return gv_returnvar
    
    def finish_and_return(self, sigtoken, gv_returnvar):
        log('%s Builder.finish_and_return %s,%s' % (
            self.block.label, sigtoken, gv_returnvar.operand()))
        self.asm.append(' ret ' + gv_returnvar.operand())
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        # 'target' is a label, which for the llvm backend is a Block
        gv = [v.operand() for v in outputargs_gv]
        log('%s Builder.finish_and_goto %s,%s' % (
            self.block.label, gv, target.label))
        self.asm.append(' br label %%%s' % (target.label,))
        target.add_incoming_link(self.block, outputargs_gv)
        self._close()

    def flexswitch(self, gv_exitswitch):
        log('%s Builder.flexswitch %s' % (self.block.label, gv_exitswitch.operand()))
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

    def end(self):
        log('RLLVMGenOp.end')
        self.blocklist.append(EpilogueBlock())
        asmlines = []
        for block in self.blocklist:
            block.writecode(asmlines)
        asmlines.append('')
        asm_string = '\n'.join(asmlines)

        self.blocklist = None
        log(asm_string)
        llvmjit.parse(asm_string)
        llvmjit.transform(3) #optimize module (should be on functions actually)
        function   = llvmjit.getNamedFunction(self.name)
        entrypoint = llvmjit.getPointerToFunctionAsInt(function)
        # XXX or directly cast the ctypes ptr to int with:
        #   ctypes.cast(ptr, c_void_p).value
        self.funcname[entrypoint] = self.funcname[self.gv_entrypoint.value]
        self.gv_entrypoint.value = entrypoint

    # ----------------------------------------------------------------
    # the public RGenOp interface

    def newgraph(self, sigtoken, name):
        if name in self.funcused:
            self.funcused[name] += 1
            name = '%s_%d' % (name, self.funcused[name])
        else:
            self.funcused[name] = 0

        log('RLLVMGenOp.newgraph %s,%s' % (sigtoken, name))

        prologueblock = PrologueBlock(sigtoken, name)
        self.blocklist = [prologueblock]
        builder = Builder(self, coming_from=prologueblock)
        prologueblock.startblocklabel = builder.nextlabel

        argtypes, restype = sigtoken
        n = len(self.funcname) * 2 + 1     #+1 so we recognize these pre compilation 'pointers'
        self.name = name
        self.funcname[n] = '%s %%%s' % (restype, name)
        self.gv_entrypoint = IntConst(n)    #note: updated by Builder.end() (i.e after compilation)
        args = list(prologueblock.inputargs)
        builder.enter_next_block(argtypes, args)
        return builder, self.gv_entrypoint, args

    @specialize.genconst(1)
    def genconst(self, llvalue):
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
    def kindToken(T):
        # turn the type T into the llvm approximation that we'll use here
        # XXX incomplete
        if isinstance(T, lltype.Ptr):
            return 'int*'
        elif T is llmemory.Address:
            return 'int*'
        if T is lltype.Bool:
            return 'bool'
        elif T is lltype.Char:
            return 'ubyte'
        elif T is lltype.Unsigned:
            return 'uint'
        elif T is lltype.Float:
            return 'float'
        else:
            return 'int'    #Signed/UniChar/Void

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return (RLLVMGenOp.kindToken(T), llmemory.offsetof(T, name))

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        XXX
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
        XXX
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

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
            assert 0, "XXX not implemented"


global_rgenop = RLLVMGenOp()
RLLVMGenOp.constPrebuiltGlobal = global_rgenop.genconst

