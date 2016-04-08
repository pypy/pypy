from rpython.rlib.rvmprof.rvmprof import cintf
from rpython.jit.metainterp import resoperation as resoperations
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import ConstInt, ConstFloat
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.objectmodel import compute_unique_id, always_inline
import sys
import weakref

MARK_INPUT_ARGS = 0x10
MARK_RESOP_META = 0x11
MARK_RESOP = 0x12
MARK_RESOP_DESCR = 0x13
MARK_ASM_ADDR = 0x14
MARK_ASM = 0x15

# which type of trace is logged after this
# the trace as it is recorded by the tracer
MARK_TRACE = 0x16
# the trace that has passed the optimizer
MARK_TRACE_OPT = 0x17
# the trace assembled to machine code (after rewritten)
MARK_TRACE_ASM = 0x18

# the machine code was patched (e.g. guard)
MARK_STITCH_BRIDGE = 0x19

MARK_JIT_LOOP_COUNTER = 0x20
MARK_JIT_BRIDGE_COUNTER = 0x21
MARK_JIT_ENTRY_COUNTER = 0x22

MARK_JITLOG_HEADER = 0x23
MARK_JITLOG_DEBUG_MERGE_POINT = 0x24

IS_32_BIT = sys.maxint == 2**31-1

@always_inline
def encode_str(string):
    return encode_le_32bit(len(string)) + string

@always_inline
def encode_le_16bit(val):
    return chr((val >> 0) & 0xff) + chr((val >> 8) & 0xff)

@always_inline
def encode_le_32bit(val):
    return ''.join([chr((val >> 0) & 0xff),
                    chr((val >> 8) & 0xff),
                    chr((val >> 16) & 0xff),
                    chr((val >> 24) & 0xff)])

@always_inline
def encode_le_addr(val):
    if IS_32_BIT:
        return encode_be_32bit(val)
    else:
        return ''.join([chr((val >> 0) & 0xff),
                        chr((val >> 8) & 0xff),
                        chr((val >> 16) & 0xff),
                        chr((val >> 24) & 0xff),
                        chr((val >> 32) & 0xff),
                        chr((val >> 40) & 0xff),
                        chr((val >> 48) & 0xff),
                        chr((val >> 56)& 0xff)])


class VMProfJitLogger(object):

    def __init__(self):
        self.cintf = cintf.setup()
        self.memo = {}

    def setup_once(self):
        if self.cintf.jitlog_enabled():
            return
        self.cintf.jitlog_try_init_using_env()
        if not self.cintf.jitlog_enabled():
            return
        VMProfJitLogger._write_header(self.cintf)

    @staticmethod
    @always_inline
    def _write_header(cintf):
        header = encode_le_16bit(0xaffe)
        cintf.jitlog_write_marked(MARK_JITLOG_HEADER,
                        header, len(header))

        count = len(resoperations.opname)
        mark = MARK_RESOP_META
        for opnum, opname in resoperations.opname.items():
            line = encode_le_16bit(opnum) + encode_str(opname.lower())
            cintf.jitlog_write_marked(mark, line, len(line))

    def finish(self):
        self.cintf.jitlog_teardown()

    def _write_marked(self, mark, line):
        if not we_are_translated():
            assert self.cintf.jitlog_enabled()
        self.cintf.jitlog_write_marked(mark, line, len(line))

    def log_jit_counter(self, struct):
        if not self.cintf.jitlog_enabled():
            return
        le_addr = encode_le_addr(struct.number)
        # not an address (but a number) but it is a machine word
        le_count = encode_le_addr(struct.i)
        if struct.type == 'l':
            tag = MARK_JIT_LOOP_COUNTER
        elif struct.type == 'b':
            tag = MARK_JIT_BRIDGE_COUNTER
        else:
            tag = MARK_JIT_ENTRY_COUNTER
        self._write_marked(tag, le_addr + le_count)

    def log_trace(self, tag, metainterp_sd, mc, memo=None):
        if not self.cintf.jitlog_enabled():
            return EMPTY_TRACE_LOG
        assert isinstance(tag, int)
        if memo is None:
            memo = {}
        return LogTrace(tag, memo, metainterp_sd, mc, self)

    def log_patch_guard(self, descr_number, addr):
        if not self.cintf.jitlog_enabled():
            return
        le_descr_number = encode_le_addr(descr_number)
        le_addr = encode_le_addr(addr)
        lst = [le_descr_number, le_addr]
        self._write_marked(MARK_STITCH_BRIDGE, ''.join(lst))

class BaseLogTrace(object):
    def write(self, args, ops, faildescr=None, ops_offset={}, name=None, unique_id=0):
        return None

EMPTY_TRACE_LOG = BaseLogTrace()

class LogTrace(BaseLogTrace):
    def __init__(self, tag, memo, metainterp_sd, mc, logger):
        self.memo = memo
        self.metainterp_sd = metainterp_sd
        self.ts = None
        if self.metainterp_sd is not None:
            self.ts = metainterp_sd.cpu.ts
        self.tag = tag
        self.mc = mc
        self.logger = logger

    def write(self, args, ops, faildescr=None, ops_offset={},
              name=None, unique_id=0):
        log = self.logger

        if name is None:
            name = ''
        # write the initial tag
        if faildescr is None:
            string = encode_str('loop') + \
                     encode_le_addr(unique_id) + \
                     encode_str(name or '')
            log._write_marked(self.tag, string)
        else:
            descr_number = compute_unique_id(faildescr)
            string = encode_str('bridge') + \
                     encode_le_addr(descr_number) + \
                     encode_le_addr(unique_id) + \
                     encode_str(name or '')
            log._write_marked(self.tag, string)

        # input args
        str_args = [self.var_to_str(arg) for arg in args]
        string = encode_str(','.join(str_args))
        log._write_marked(MARK_INPUT_ARGS, string)

        # assembler address (to not duplicate it in write_code_dump)
        if self.mc is not None:
            absaddr = self.mc.absolute_addr()
            rel = self.mc.get_relative_pos()
            # packs <start addr> <end addr> as two unsigend longs
            le_addr1 = encode_le_addr(absaddr)
            le_addr2 = encode_le_addr(absaddr + rel)
            log._write_marked(MARK_ASM_ADDR, le_addr1 + le_addr2)
        for i,op in enumerate(ops):
            if rop.DEBUG_MERGE_POINT == op.getopnum():
                self.encode_debug_info(op)
                continue
            mark, line = self.encode_op(op)
            log._write_marked(mark, line)
            self.write_core_dump(ops, i, op, ops_offset)

        self.memo = {}

    def encode_debug_info(self, op):
        log = self.logger
        jd_sd = self.metainterp_sd.jitdrivers_sd[op.getarg(0).getint()]
        file_name, bytecode, line_number  = jd_sd.warmstate.get_location_str(op.getarg(2))
        line = []
        line.append(encode_str(file_name))
        line.append(encode_str(bytecode))
        line.append(encode_str(line_number))
        log._write_marked(MARK_JITLOG_DEBUG_MERGE_POINT, ''.join(line))


    def encode_op(self, op):
        """ an operation is written as follows:
            <marker> <opid (16 bit)> \
                     <len (32 bit)> \
                     <res_val>,<arg_0>,...,<arg_n>,<descr>
            The marker indicates if the last argument is
            a descr or a normal argument.
        """
        str_args = [self.var_to_str(arg) for arg in op.getarglist()]
        descr = op.getdescr()
        le_opnum = encode_le_16bit(op.getopnum())
        str_res = self.var_to_str(op)
        line = ','.join([str_res] + str_args)
        if descr:
            descr_str = descr.repr_of_descr()
            line = line + ',' + descr_str
            string = encode_str(line)
            descr_number = compute_unique_id(descr)
            le_descr_number = encode_le_addr(descr_number)
            return MARK_RESOP_DESCR, le_opnum + string + le_descr_number
        else:
            string = encode_str(line)
            return MARK_RESOP, le_opnum + string


    def write_core_dump(self, operations, i, op, ops_offset):
        if self.mc is None:
            return

        op2 = None
        j = i+1
        # find the next op that is in the offset hash
        while j < len(operations):
            op2 = operations[j]
            if op in ops_offset:
                break
            j += 1

        # this op has no known offset in the machine code (it might be
        # a debug operation)
        if op not in ops_offset:
            return
        # there is no well defined boundary for the end of the
        # next op in the assembler
        if op2 is not None and op2 not in ops_offset:
            return
        dump = []

        start_offset = ops_offset[op]
        # end offset is either the last pos in the assembler
        # or the offset of op2
        if op2 is None:
            end_offset = self.mc.get_relative_pos()
        else:
            end_offset = ops_offset[op2]

        count = end_offset - start_offset
        dump = self.mc.copy_core_dump(self.mc.absolute_addr(), start_offset, count)
        offset = encode_le_16bit(start_offset)
        edump = encode_str(dump)
        self.logger._write_marked(MARK_ASM, offset + edump)

    def var_to_str(self, arg):
        try:
            mv = self.memo[arg]
        except KeyError:
            mv = len(self.memo)
            self.memo[arg] = mv
        if isinstance(arg, ConstInt):
            if self.metainterp_sd and int_could_be_an_address(arg.value):
                addr = arg.getaddr()
                name = self.metainterp_sd.get_name_from_address(addr)
                if name:
                    return 'ConstClass(' + name + ')'
            return str(arg.value)
        elif self.ts is not None and isinstance(arg, self.ts.ConstRef):
            if arg.value:
                return 'ConstPtr(ptr' + str(mv) + ')'
            return 'ConstPtr(null)'
        if isinstance(arg, ConstFloat):
            return str(arg.getfloat())
        elif arg is None:
            return 'None'
        elif arg.is_vector():
            return 'v' + str(mv)
        elif arg.type == 'i':
            return 'i' + str(mv)
        elif arg.type == 'r':
            return 'p' + str(mv)
        elif arg.type == 'f':
            return 'f' + str(mv)
        else:
            return '?'

def int_could_be_an_address(x):
    if we_are_translated():
        x = rffi.cast(lltype.Signed, x)       # force it
        return not (-32768 <= x <= 32767)
    else:
        return isinstance(x, llmemory.AddressAsInt)
