import sys
import weakref
import struct
import os

from rpython.rlib.rvmprof import cintf
from rpython.jit.metainterp import resoperation as resoperations
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import ConstInt, ConstFloat
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.objectmodel import compute_unique_id, always_inline
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.unroll import unrolling_iterable

def commonprefix(a,b):
    "Given a list of pathnames, returns the longest common leading component"
    assert a is not None
    assert b is not None
    la = len(a)
    lb = len(b)
    c = min(la,lb)
    if c == 0:
        return ""
    for i in range(c):
        if a[i] != b[i]:
            return a[:i] # partly matching
    return a # full match

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
def encode_le_64bit(val):
    return ''.join([chr((val >> 0) & 0xff),
                    chr((val >> 8) & 0xff),
                    chr((val >> 16) & 0xff),
                    chr((val >> 24) & 0xff),
                    chr((val >> 32) & 0xff),
                    chr((val >> 40) & 0xff),
                    chr((val >> 48) & 0xff),
                    chr((val >> 56)& 0xff)])

@always_inline
def encode_le_addr(val):
    if IS_32_BIT:
        return encode_le_32bit(val)
    else:
        return encode_le_64bit(val)

def encode_type(type, value):
    if type == "s":
        return encode_str(value)
    elif type == "q":
        return encode_le_64bit(value)
    elif type == "i":
        return encode_le_32bit(value)
    elif type == "h":
        return encode_le_32bit(value)
    else:
        raise NotImplementedError


# more variable parameters
MP_STR = (0x0, "s")
MP_INT = (0x0, "i")

# concrete parameters
MP_FILENAME = (0x1, "s")
MP_LINENO = (0x2, "i")
MP_INDEX = (0x4, "i")
MP_SCOPE = (0x8, "s")
MP_OPCODE = (0x10, "s")

class WrappedValue(object):
    def encode(self, log, i, prefixes):
        raise NotImplementedError

class StringValue(WrappedValue):
    def __init__(self, sem_type, gen_type, value):
        self.value = value

    def encode(self, log, i, prefixes):
        str_value = self.value
        if len(str_value) < 5:
            enc_value = encode_str(chr(0xff) + str_value)
        else:
            cp = commonprefix([prefixes[i], str_value])
            if cp != prefixes[i]:
                if len(cp) == 0:
                    # they are fully different!
                    prefixes[i] = str_value
                    enc_value = encode_str(chr(0xff) + str_value)
                else:
                    # the prefix changed
                    prefixes[i] = cp
                    # common prefix of field i
                    assert i != 0xff
                    log._write_marked(MARK_COMMON_PREFIX, chr(i) \
                                                      + encode_str(cp))
                    enc_value = encode_str(chr(i) + str_value)
            else:
                enc_value = encode_str(chr(i) + str_value)
        #
        if prefixes[i] is None:
            prefixes[i] = str_value
        return enc_value

class IntValue(WrappedValue):
    def __init__(self, sem_type, gen_type, value):
        self.value = value

    def encode(self, log, i, prefixes):
        return encode_le_64bit(self.value)

# note that a ...
# "semantic_type" is an integer denoting which meaning does a type at a merge point have
#                 there are very common ones that are predefined. E.g. MP_FILENAME
# "generic_type" is one of the primitive types supported (string,int)

@specialize.argtype(2)
def wrap(sem_type, gen_type, value):
    if isinstance(value, int):
        return IntValue(sem_type, gen_type, value)
    elif isinstance(value, str):
        return StringValue(sem_type, gen_type, value)
    raise NotImplementedError

def returns(*args):
    """ Decorate your get_location function to specify the types.
        Use MP_* constant as parameters. An example impl for get_location
        would return the following:

        @returns(MP_FILENAME, MP_LINENO)
        def get_location(...):
            return ("a.py", 0)
    """
    def decor(method):
        method._loc_types = args
        return method
    return decor

JITLOG_VERSION = 1
JITLOG_VERSION_16BIT_LE = struct.pack("<H", JITLOG_VERSION)

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

MARK_JITLOG_COUNTER = 0x20
MARK_START_TRACE = 0x21
MARK_INIT_MERGE_POINT = 0x22

MARK_JITLOG_HEADER = 0x23
MARK_JITLOG_DEBUG_MERGE_POINT = 0x24
MARK_COMMON_PREFIX = 0x25

IS_32_BIT = sys.maxint == 2**31-1

def assemble_header():
    version = JITLOG_VERSION_16BIT_LE
    count = len(resoperations.opname)
    content = [version, chr(MARK_RESOP_META),
               encode_le_16bit(count)]
    for opnum, opname in resoperations.opname.items():
        content.append(encode_le_16bit(opnum))
        content.append(encode_str(opname.lower()))
    return ''.join(content)

class VMProfJitLogger(object):
    def __init__(self):
        self.cintf = cintf.setup()
        self.memo = {}
        self.trace_id = 0

    def setup_once(self):
        if self.cintf.jitlog_enabled():
            return
        self.cintf.jitlog_try_init_using_env()
        if not self.cintf.jitlog_enabled():
            return
        blob = assemble_header()
        self.cintf.jitlog_write_marked(MARK_JITLOG_HEADER, blob, len(blob))

    def finish(self):
        self.cintf.jitlog_teardown()

    def start_new_trace(self, faildescr=None, entry_bridge=False):
        if not self.cintf.jitlog_enabled():
            return
        content = [encode_le_addr(self.trace_id)]
        if faildescr:
            content.append(encode_str('bridge'))
            descrnmr = compute_unique_id(faildescr)
            content.append(encode_le_addr(descrnmr))
        else:
            content.append(encode_str('loop'))
            content.append(encode_le_addr(int(entry_bridge)))
        self._write_marked(MARK_START_TRACE, ''.join(content))
        self.trace_id += 1

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
        self._write_marked(MARK_JITLOG_COUNTER, le_addr + le_count)

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
    def write_trace(self, trace):
        return None

    def write(self, args, ops, ops_offset={}):
        return None

EMPTY_TRACE_LOG = BaseLogTrace()

def encode_merge_point(log, prefixes, values):
    line = []
    unrolled = unrolling_iterable(values)
    i = 0
    for value in unrolled:
        line.append(value.encode(log,i,prefixes))
        i += 1
    return ''.join(line)


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
        self.common_prefix = None

    def write_trace(self, trace):
        ops = []
        i = trace.get_iter()
        while not i.done():
            ops.append(i.next())
        self.write(i.inputargs, ops)

    def write(self, args, ops, ops_offset={}):
        log = self.logger
        log._write_marked(self.tag, encode_le_addr(self.logger.trace_id))

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

    def encode_once(self):
        pass

    def encode_debug_info(self, op):
        # the idea is to write the debug merge point as it's own well known
        # tag. Compression for common prefixes is implemented:

        log = self.logger
        jd_sd = self.metainterp_sd.jitdrivers_sd[op.getarg(0).getint()]
        if not jd_sd.warmstate.get_location:
            return
        values = jd_sd.warmstate.get_location(op.getarglist()[3:])
        if values is None:
            # indicates that this function is not provided to the jit driver
            return
        types = jd_sd.warmstate.get_location_types

        if self.common_prefix is None:
            # first time visiting a merge point
            # setup the common prefix
            self.common_prefix = [""] * len(types)
            encoded_types = []
            for i, (semantic_type, _) in enumerate(types):
                encoded_types.append(chr(semantic_type))
            log._write_marked(MARK_INIT_MERGE_POINT, ''.join(encoded_types))

        # the types have already been written
        encoded = encode_merge_point(log, self.common_prefix, values)
        log._write_marked(MARK_JITLOG_DEBUG_MERGE_POINT, encoded)

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
        assert start_offset >= 0
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
