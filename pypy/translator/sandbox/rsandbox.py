"""Generation of sandboxing stand-alone executable from RPython code.
In place of real calls to any external function, this code builds
trampolines that marshal their input arguments, dump them to STDOUT,
and wait for an answer on STDIN.  Enable with 'translate.py --sandbox'.
"""
from pypy.translator.sandbox.sandboxmsg import MessageBuilder, LLMessage

# ____________________________________________________________
#
# Sandboxing code generator for external functions
#

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.annotation import model as annmodel
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("sandbox")
py.log.setconsumer("sandbox", ansi_log)


# a version of os.read() and os.write() that are not mangled
# by the sandboxing mechanism
ll_read_not_sandboxed = rffi.llexternal('read',
                                        [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                                        rffi.SIZE_T)
ll_read_not_sandboxed._obj._safe_not_sandboxed = True

ll_write_not_sandboxed = rffi.llexternal('write',
                                         [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                                         rffi.SIZE_T)
ll_write_not_sandboxed._obj._safe_not_sandboxed = True

def writeall_not_sandboxed(fd, buf, length):
    while length > 0:
        size = rffi.cast(rffi.SIZE_T, length)
        count = rffi.cast(lltype.Signed, ll_write_not_sandboxed(fd, buf, size))
        if count < 0:
            raise IOError
        if count == 0:
            raise EOFError
        length -= count
        buf = lltype.direct_ptradd(lltype.direct_arrayitems(buf), count)
        buf = rffi.cast(rffi.CCHARP, buf)

def readall_not_sandboxed(fd, length):
    buf = lltype.malloc(rffi.CCHARP.TO, length, flavor='raw')
    p = buf
    got = 0
    while got < length:
        size1 = rffi.cast(rffi.SIZE_T, length - got)
        count = rffi.cast(lltype.Signed, ll_read_not_sandboxed(fd, p, size1))
        if count < 0:
            raise IOError
        if count == 0:
            raise EOFError
        got += count
        p = lltype.direct_ptradd(lltype.direct_arrayitems(p), count)
        p = rffi.cast(rffi.CCHARP, p)
    return buf

def buf2num(buf, index=0):
    c0 = ord(buf[index  ])
    c1 = ord(buf[index+1])
    c2 = ord(buf[index+2])
    c3 = ord(buf[index+3])
    if c0 >= 0x80:
        c0 -= 0x100
    return (c0 << 24) | (c1 << 16) | (c2 << 8) | c3

def build_default_marshal_input(FUNCTYPE, namehint, cache={}):
    # return a default 'marshal_input' function
    try:
        return cache[FUNCTYPE]
    except KeyError:
        pass
    unroll_args = []
    for i, ARG in enumerate(FUNCTYPE.ARGS):
        if ARG == rffi.INT:       # 'int' argument
            methodname = "packnum"
        elif ARG == rffi.SIZE_T:  # 'size_t' argument
            methodname = "packsize_t"
        elif ARG == rffi.CCHARP:  # 'char*' argument, assumed zero-terminated
            methodname = "packccharp"
        else:
            raise NotImplementedError("external function %r argument type %s" %
                                      (namehint, ARG))
        unroll_args.append((i, methodname))
    unroll_args = unrolling_iterable(unroll_args)

    def marshal_input(msg, *args):
        assert len(args) == len(FUNCTYPE.ARGS)
        for index, methodname in unroll_args:
            getattr(msg, methodname)(args[index])

    cache[FUNCTYPE] = marshal_input
    return marshal_input

def unmarshal_int(msg, *args):    return msg.nextnum()
def unmarshal_size_t(msg, *args): return msg.nextsize_t()
def unmarshal_void(msg, *args):   pass

def build_default_unmarshal_output(FUNCTYPE, namehint,
                                   cache={rffi.INT   : unmarshal_int,
                                          rffi.SIZE_T: unmarshal_size_t,
                                          lltype.Void: unmarshal_void}):
    try:
        return cache[FUNCTYPE.RESULT]
    except KeyError:
        raise NotImplementedError("exernal function %r return type %s" % (
            namehint, FUNCTYPE.RESULT))

CFalse = CDefinedIntSymbolic('0')    # hack hack

def sandboxed_io(msg):
    STDIN = 0
    STDOUT = 1
    buf = msg.as_rffi_buf()
    if CFalse:  # hack hack to force a method to be properly annotated/rtyped
        msg.packstring(chr(CFalse) + chr(CFalse))
        msg.packsize_t(rffi.cast(rffi.SIZE_T, CFalse))
        msg.packbuf(buf, CFalse * 5, CFalse * 6)
    try:
        writeall_not_sandboxed(STDOUT, buf, msg.getlength())
    finally:
        lltype.free(buf, flavor='raw')
    # wait for the answer
    buf = readall_not_sandboxed(STDIN, 4)
    try:
        length = buf2num(buf)
    finally:
        lltype.free(buf, flavor='raw')
    length -= 4     # the original length includes the header
    if length < 0:
        raise IOError
    buf = readall_not_sandboxed(STDIN, length)
    msg = LLMessage(buf, 0, length)
    if CFalse:  # hack hack to force a method to be properly annotated/rtyped
        msg.nextstring()
        msg.nextsize_t()
    return msg

def not_implemented_stub(msg):
    STDERR = 2
    buf = rffi.str2charp(msg + '\n')
    writeall_not_sandboxed(STDERR, buf, len(msg) + 1)
    rffi.free_charp(buf)
    raise RuntimeError(msg)  # XXX in RPython, the msg is ignored at the moment
not_implemented_stub._annenforceargs_ = [str]

def get_external_function_sandbox_graph(fnobj, db):
    """Build the graph of a helper trampoline function to be used
    in place of real calls to the external function 'fnobj'.  The
    trampoline marshals its input arguments, dumps them to STDOUT,
    and waits for an answer on STDIN.
    """
    # XXX for now, only supports function with int and string arguments
    # and returning an int or void.  Other cases need a custom
    # _marshal_input and/or _unmarshal_output function on fnobj.
    FUNCTYPE = lltype.typeOf(fnobj)
    fnname = fnobj._name
    try:
        if hasattr(fnobj, '_marshal_input'):
            marshal_input = fnobj._marshal_input
        else:
            marshal_input = build_default_marshal_input(FUNCTYPE, fnname)
        if hasattr(fnobj, '_unmarshal_output'):
            unmarshal_output = fnobj._unmarshal_output
        else:
            unmarshal_output = build_default_unmarshal_output(FUNCTYPE, fnname)
    except NotImplementedError, e:
        msg = 'Not Implemented: %s' % (e,)
        log.WARNING(msg)
        def execute(*args):
            not_implemented_stub(msg)

    else:
        def execute(*args):
            # marshal the input arguments
            msg = MessageBuilder()
            msg.packstring(fnname)
            marshal_input(msg, *args)
            # send the buffer and wait for the answer
            msg = sandboxed_io(msg)
            try:
                # decode the answer
                errcode = msg.nextnum()
                if errcode != 0:
                    raise IOError
                result = unmarshal_output(msg, *args)
            finally:
                lltype.free(msg.value, flavor='raw')
            return result
    execute = func_with_new_name(execute, 'sandboxed_' + fnname)

    ann = MixLevelHelperAnnotator(db.translator.rtyper)
    args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNCTYPE.ARGS]
    s_result = annmodel.lltype_to_annotation(FUNCTYPE.RESULT)
    graph = ann.getgraph(execute, args_s, s_result)
    ann.finish()
    return graph
