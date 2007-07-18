"""Generation of sandboxing stand-alone executable from RPython code.
In place of real calls to any external function, this code builds
trampolines that marshal their input arguments, dump them to STDOUT,
and wait for an answer on STDIN.  Enable with 'translate.py --sandbox'.
"""
from pypy.translator.c.sandboxmsg import MessageBuilder, LLMessage

# ____________________________________________________________
#
# Sandboxing code generator for external functions
#

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.annotation import model as annmodel
from pypy.rlib.unroll import unrolling_iterable
from pypy.translator.c import funcgen
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

def getSandboxFuncCodeGen(fnobj, db):
    graph = get_external_function_sandbox_graph(fnobj, db)
    return funcgen.FunctionCodeGenerator(graph, db)

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


def get_external_function_sandbox_graph(fnobj, db):
    """Build the graph of a helper trampoline function to be used
    in place of real calls to the external function 'fnobj'.  The
    trampoline marshals its input arguments, dumps them to STDOUT,
    and waits for an answer on STDIN.
    """
    # XXX for now, only supports function with int and string arguments
    # and returning an int.
    FUNCTYPE = lltype.typeOf(fnobj)
    unroll_args = []
    for i, ARG in enumerate(FUNCTYPE.ARGS):
        if ARG == rffi.INT:       # 'int' argument
            methodname = "packnum"
        elif ARG == rffi.CCHARP:  # 'char*' argument, assumed zero-terminated
            methodname = "packccharp"
        else:
            raise NotImplementedError("external function %r argument type %s" %
                                      (fnobj, ARG))
        unroll_args.append((i, methodname))
    if FUNCTYPE.RESULT != rffi.INT:
        raise NotImplementedError("exernal function %r return type %s" % (
            fnobj, FUNCTYPE.RESULT))
    unroll_args = unrolling_iterable(unroll_args)
    fnname = fnobj._name

    def execute(*args):
        STDIN = 0
        STDOUT = 1
        assert len(args) == len(FUNCTYPE.ARGS)
        # marshal the input arguments
        msg = MessageBuilder()
        msg.packstring(fnname)
        for index, methodname in unroll_args:
            getattr(msg, methodname)(args[index])
        buf = msg.as_rffi_buf()
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
        try:
            # decode the answer
            msg = LLMessage(buf, 0, length)
            errcode = msg.nextnum()
            if errcode != 0:
                raise IOError
            result = msg.nextnum()
        finally:
            lltype.free(buf, flavor='raw')

        return result
    execute = func_with_new_name(execute, 'sandboxed_' + fnname)

    ann = MixLevelHelperAnnotator(db.translator.rtyper)
    args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNCTYPE.ARGS]
    s_result = annmodel.lltype_to_annotation(FUNCTYPE.RESULT)
    graph = ann.getgraph(execute, args_s, s_result)
    ann.finish()
    return graph
