import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.annlowlevel import cast_instance_to_gcref
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rlib.jit_hooks import LOOP_RUN_CONTAINER
from pypy.jit.codewriter import longlong
from pypy.jit.metainterp import history, compile
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.x86.arch import IS_X86_32, JITFRAME_FIXED_SIZE
from pypy.jit.backend.x86.profagent import ProfileAgent
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.llsupport import jitframe
from pypy.jit.backend.x86 import regloc
from pypy.jit.backend.llsupport.symbolic import WORD
from pypy.jit.backend.llsupport.descr import ArrayDescr, FLAG_POINTER,\
     FLAG_FLOAT
        
import sys

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitbackend')
py.log.setconsumer('jitbackend', ansi_log)


class AbstractX86CPU(AbstractLLCPU):
    debug = True
    supports_floats = True
    supports_singlefloats = True

    dont_keepalive_stuff = False # for tests
    with_threads = False

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        profile_agent = ProfileAgent()
        if rtyper is not None:
            config = rtyper.annotator.translator.config
            if config.translation.jit_profiler == "oprofile":
                from pypy.jit.backend.x86 import oprofile
                if not oprofile.OPROFILE_AVAILABLE:
                    log.WARNING('oprofile support was explicitly enabled, but oprofile headers seem not to be available')
                profile_agent = oprofile.OProfileAgent()
            self.with_threads = config.translation.thread

        self.profile_agent = profile_agent

    def set_debug(self, flag):
        return self.assembler.set_debug(flag)

    def get_failargs_limit(self):
        if self.opts is not None:
            return self.opts.failargs_limit
        else:
            return 1000

    def setup(self):
        self.assembler = Assembler386(self, self.translate_support_code)

    def setup_once(self):
        self.profile_agent.startup()
        self.assembler.setup_once()

    def finish_once(self):
        self.assembler.finish_once()
        self.profile_agent.shutdown()

    def dump_loop_token(self, looptoken):
        """
        NOT_RPYTHON
        """
        from pypy.jit.backend.x86.tool.viewcode import machine_code_dump
        data = []
        label_list = [(offset, name) for name, offset in
                      looptoken._x86_ops_offset.iteritems()]
        label_list.sort()
        addr = looptoken._x86_rawstart
        src = rffi.cast(rffi.CCHARP, addr)
        for p in range(looptoken._x86_fullsize):
            data.append(src[p])
        data = ''.join(data)
        lines = machine_code_dump(data, addr, self.backend_name, label_list)
        print ''.join(lines)

    def compile_loop(self, inputargs, operations, looptoken, log=True, name=''):
        return self.assembler.assemble_loop(name, inputargs, operations,
                                            looptoken, log=log)

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(faildescr, inputargs, operations,
                                              original_loop_token, log=log)

    def clear_latest_values(self, count):
        setitem = self.assembler.fail_boxes_ptr.setitem
        null = lltype.nullptr(llmemory.GCREF.TO)
        for index in range(count):
            setitem(index, null)

    def make_execute_token(self, *ARGS):
        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF],
                                             lltype.Signed))
        #
        def execute_token(executable_token, *args):
            clt = executable_token.compiled_loop_token
            assert len(args) == clt._debug_nbargs
            #
            addr = executable_token._x86_function_addr
            func = rffi.cast(FUNCPTR, addr)
            #llop.debug_print(lltype.Void, ">>>> Entering", addr)
            frame_info = clt.frame_info
            frame = lltype.malloc(jitframe.JITFRAME, frame_info.jfi_frame_depth,
                                  zero=True)
            frame.jf_frame_info = frame_info
            ll_frame = lltype.cast_opaque_ptr(llmemory.GCREF, frame)
            prev_interpreter = None   # help flow space
            if not self.translate_support_code:
                prev_interpreter = LLInterpreter.current_interpreter
                LLInterpreter.current_interpreter = self.debug_ll_interpreter
            try:
                # XXX RPythonize
                num = JITFRAME_FIXED_SIZE * WORD
                for arg in args:
                    if isinstance(arg, int):
                        self.set_int_value(frame, num, arg)
                    elif isinstance(arg, float):
                        self.set_float_value(frame, num, arg)
                        if IS_X86_32:
                            num += WORD
                    else:
                        self.set_ref_value(frame, num, arg)
                    num += WORD
                descr_no = func(ll_frame)
            finally:
                if not self.translate_support_code:
                    LLInterpreter.current_interpreter = prev_interpreter
            #llop.debug_print(lltype.Void, "<<<< Back")
            descr = self.get_fail_descr_from_number(descr_no)
            frame.jf_descr = cast_instance_to_gcref(descr)
            return frame
        return execute_token

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return CPU386.cast_adr_to_int(adr)
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)

    all_null_registers = lltype.malloc(rffi.LONGP.TO,
                                       IS_X86_32 and (16+8)  # 16 + 8 regs
                                                 or (16+16), # 16 + 16 regs
                                       flavor='raw', zero=True,
                                       immortal=True)

    def force(self, addr_of_force_token):
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        frame = rffi.cast(jitframe.JITFRAMEPTR, addr_of_force_token - ofs)
        fail_index = frame.jf_force_index
        faildescr = self.get_fail_descr_from_number(fail_index)
        frame.jf_descr = cast_instance_to_gcref(faildescr)
        return frame

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        self.assembler.redirect_call_assembler(oldlooptoken, newlooptoken)

    def invalidate_loop(self, looptoken):
        from pypy.jit.backend.x86 import codebuf
        
        for addr, tgt in looptoken.compiled_loop_token.invalidate_positions:
            mc = codebuf.MachineCodeBlockWrapper()
            mc.JMP_l(tgt)
            assert mc.get_relative_pos() == 5      # [JMP] [tgt 4 bytes]
            mc.copy_to_raw_memory(addr - 1)
        # positions invalidated
        looptoken.compiled_loop_token.invalidate_positions = []

    def get_all_loop_runs(self):
        l = lltype.malloc(LOOP_RUN_CONTAINER,
                          len(self.assembler.loop_run_counters))
        for i, ll_s in enumerate(self.assembler.loop_run_counters):
            l[i].type = ll_s.type
            l[i].number = ll_s.number
            l[i].counter = ll_s.i
        return l

    def set_int_value(self, newframe, index, value):
        """ Note that we keep index multiplied by WORD here mostly
        for completeness with get_int_value and friends
        """
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        self.write_int_at_mem(newframe, ofs + index, WORD, 1, value)

    def set_ref_value(self, newframe, index, value):
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        self.write_ref_at_mem(newframe, ofs + index, value)

    def set_float_value(self, newframe, index, value):
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        self.write_float_at_mem(newframe, ofs + index, value)

    @specialize.arg(1)
    def get_ofs_of_frame_field(self, name):
        descrs = self.gc_ll_descr.getframedescrs(self)
        base_ofs = self.unpack_arraydescr(descrs.arraydescr)
        ofs = self.unpack_fielddescr(getattr(descrs, name))
        return ofs - base_ofs

    def get_baseofs_of_frame_field(self):
        descrs = self.gc_ll_descr.getframedescrs(self)
        base_ofs = self.unpack_arraydescr(descrs.arraydescr)
        return base_ofs

class CPU386(AbstractX86CPU):
    backend_name = 'x86'
    WORD = 4
    NUM_REGS = 8
    CALLEE_SAVE_REGISTERS = [regloc.ebx, regloc.esi, regloc.edi]

    supports_longlong = True

    def __init__(self, *args, **kwargs):
        assert sys.maxint == (2**31 - 1)
        super(CPU386, self).__init__(*args, **kwargs)

class CPU386_NO_SSE2(CPU386):
    supports_floats = False
    supports_longlong = False

class CPU_X86_64(AbstractX86CPU):
    backend_name = 'x86_64'
    WORD = 8
    NUM_REGS = 16
    CALLEE_SAVE_REGISTERS = [regloc.ebx, regloc.r12, regloc.r13, regloc.r14, regloc.r15]

    def __init__(self, *args, **kwargs):
        assert sys.maxint == (2**63 - 1)
        super(CPU_X86_64, self).__init__(*args, **kwargs)
        descrs = self.gc_ll_descr.getframedescrs(self)
        ad = descrs.arraydescr
        # the same as normal JITFRAME, however with an array of pointers
        self.refarraydescr = ArrayDescr(ad.basesize, ad.itemsize, ad.lendescr,
                                        FLAG_POINTER)
        self.floatarraydescr = ArrayDescr(ad.basesize, ad.itemsize, ad.lendescr,
                                          FLAG_FLOAT)

    def getarraydescr_for_frame(self, type, index):
        if type == history.FLOAT:
            descr = self.floatarraydescr
        elif type == history.REF:
            descr = self.refarraydescr
        else:
            descrs = self.gc_ll_descr.getframedescrs(self)
            descr = descrs.arraydescr
        return JITFRAME_FIXED_SIZE + index, descr

CPU = CPU386
