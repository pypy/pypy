from rpython.rlib.rvmprof.rvmprof import cintf
from rpython.jit.metainterp import resoperation as resoperations
from rpython.jit.metainterp.history import ConstInt, ConstFloat
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
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
MARK_ASM_PATCH = 0x19

IS_32_BIT = sys.maxint == 2**31-1

class VMProfJitLogger(object):

    def __init__(self):
        self.cintf = cintf.setup()
        self.memo = {}

    def setup_once(self):
        self.cintf.jitlog_try_init_using_env()
        if self.cintf.jitlog_filter(0x0):
            return
        count = len(resoperations.opname)
        mark = MARK_RESOP_META
        for opnum, opname in resoperations.opname.items():
            line = self.encode_le_16bit(opnum) + opname.lower()
            self.write_marked(mark, line)

    def teardown(self):
        self.cintf.jitlog_teardown()

    def write_marked(self, mark, line):
        self.cintf.jitlog_write_marked(mark, line, len(line))

    def log_trace(self, tag, metainterp_sd, mc, memo=None):
        if self.cintf.jitlog_filter(tag):
            return
        assert isinstance(tag, int)
        if memo is None:
            memo = {}
        return LogTrace(tag, memo, metainterp_sd, mc, self)

    def log_patch_guard(self, addr, target_addr):
        if self.cintf.jitlog_filter(tag):
            return
        le_addr_write = self.encode_le_addr(addr)
        le_len = self.encode_le_32bit(8)
        le_addr = self.encode_le_addr(target_addr)
        lst = [le_addr, le_len, le_addr]
        self.cintf.jitlog_filter(MARK_ASM_PATCH, ''.join(lst))

    def encode_le_16bit(self, val):
        return chr((val >> 0) & 0xff) + chr((val >> 8) & 0xff)

    def encode_le_32bit(self, val):
        return ''.join([chr((val >> 0) & 0xff),
                        chr((val >> 8) & 0xff),
                        chr((val >> 16) & 0xff),
                        chr((val >> 24) & 0xff)])

    def encode_le_addr(self,val):
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


class LogTrace(object):
    def __init__(self, tag, memo, metainterp_sd, mc, logger):
        self.memo = memo
        self.metainterp_sd = metainterp_sd
        if self.metainterp_sd is not None:
            self.ts = metainterp_sd.cpu.ts
        self.tag = tag
        self.mc = mc
        self.logger = logger

    def write(self, args, ops, faildescr=None, ops_offset={}):
        log = self.logger

        # write the initial tag
        if faildescr is None:
            log.write_marked(self.tag, 'loop')
        else:
            log.write_marked(self.tag, 'bridge')

        # input args
        str_args = [self.var_to_str(arg) for arg in args]
        log.write_marked(MARK_INPUT_ARGS, ','.join(str_args))

        # assembler address (to not duplicate it in write_code_dump)
        if self.mc is not None:
            absaddr = self.mc.absolute_addr()
            rel = self.mc.get_relative_pos()
            # packs <start addr> <end addr> as two unsigend longs
            le_addr1 = self.encode_le_addr(absaddr)
            le_addr2 = self.encode_le_addr(absaddr + rel)
            log.write_marked(MARK_ASM_ADDR, le_addr1 + le_addr2)
        for i,op in enumerate(ops):
            mark, line = self.encode_op(op)
            log.write_marked(mark, line)
            self.write_core_dump(ops, i, op, ops_offset)

        self.memo = {}

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
        le_opnum = self.logger.encode_le_16bit(op.getopnum())
        str_res = self.var_to_str(op)
        line = le_opnum + ','.join([str_res] + str_args)
        if descr:
            descr_str = descr.repr_of_descr()
            return MARK_RESOP_DESCR, line + ',' + descr_str
        else:
            return MARK_RESOP, line


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

        dump = self.mc.copy_core_dump(self.mc.absolute_addr(), start_offset)
        offset = self.logger.encode_le_16bit(start_offset)
        self.logger.write_marked(MARK_ASM, offset + dump)

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
