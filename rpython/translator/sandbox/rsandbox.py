"""Generation of sandboxing stand-alone executable from RPython code.
In place of real calls to any external function, this code builds
trampolines that marshal their input arguments, dump them to STDOUT,
and wait for an answer on STDIN.  Enable with 'translate.py --sandbox'.
"""
import sys
if sys.platform == 'win32':
    raise TypeError("sandbox not supported on windows")

import py

from rpython.rlib import rmarshal, types
from rpython.rlib.signature import signature

# ____________________________________________________________
#
# Sandboxing code generator for external functions
#

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.tool.sourcetools import func_with_new_name
from rpython.rtyper.annlowlevel import MixLevelHelperAnnotator
from rpython.tool.ansi_print import ansi_log

log = py.log.Producer("sandbox")
py.log.setconsumer("sandbox", ansi_log)


# a version of os.read() and os.write() that are not mangled
# by the sandboxing mechanism
ll_read_not_sandboxed = rffi.llexternal('read',
                                        [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                                        rffi.SIZE_T,
                                        sandboxsafe=True)

ll_write_not_sandboxed = rffi.llexternal('write',
                                         [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                                         rffi.SIZE_T,
                                         sandboxsafe=True)


@signature(types.int(), types.ptr(rffi.CCHARP.TO), types.int(), returns=types.none())
def writeall_not_sandboxed(fd, buf, length):
    while length > 0:
        size = rffi.cast(rffi.SIZE_T, length)
        count = rffi.cast(lltype.Signed, ll_write_not_sandboxed(fd, buf, size))
        if count <= 0:
            raise IOError
        length -= count
        buf = lltype.direct_ptradd(lltype.direct_arrayitems(buf), count)
        buf = rffi.cast(rffi.CCHARP, buf)


class FdLoader(rmarshal.Loader):
    def __init__(self, fd):
        rmarshal.Loader.__init__(self, "")
        self.fd = fd
        self.buflen = 4096

    def need_more_data(self):
        buflen = self.buflen
        with lltype.scoped_alloc(rffi.CCHARP.TO, buflen) as buf:
            buflen = rffi.cast(rffi.SIZE_T, buflen)
            count = ll_read_not_sandboxed(self.fd, buf, buflen)
            count = rffi.cast(lltype.Signed, count)
            if count <= 0:
                raise IOError
            self.buf += ''.join([buf[i] for i in range(count)])
            self.buflen *= 2

def sandboxed_io(buf):
    STDIN = 0
    STDOUT = 1
    # send the buffer with the marshalled fnname and input arguments to STDOUT
    with lltype.scoped_alloc(rffi.CCHARP.TO, len(buf)) as p:
        for i in range(len(buf)):
            p[i] = buf[i]
        writeall_not_sandboxed(STDOUT, p, len(buf))
    # build a Loader that will get the answer from STDIN
    loader = FdLoader(STDIN)
    # check for errors
    error = load_int(loader)
    if error != 0:
        reraise_error(error, loader)
    else:
        # no exception; the caller will decode the actual result
        return loader

def reraise_error(error, loader):
    if   error == 1: raise OSError(load_int(loader), "external error")
    elif error == 2: raise IOError
    elif error == 3: raise OverflowError
    elif error == 4: raise ValueError
    elif error == 5: raise ZeroDivisionError
    elif error == 6: raise MemoryError
    elif error == 7: raise KeyError
    elif error == 8: raise IndexError
    else:            raise RuntimeError


@signature(types.str(), returns=types.impossible())
def not_implemented_stub(msg):
    STDERR = 2
    with rffi.scoped_str2charp(msg + '\n') as buf:
        writeall_not_sandboxed(STDERR, buf, len(msg) + 1)
    raise RuntimeError(msg)  # XXX in RPython, the msg is ignored at the moment

dump_string = rmarshal.get_marshaller(str)
load_int    = rmarshal.get_loader(int)

def get_external_function_sandbox_graph(fnobj, db, force_stub=False):
    """Build the graph of a helper trampoline function to be used
    in place of real calls to the external function 'fnobj'.  The
    trampoline marshals its input arguments, dumps them to STDOUT,
    and waits for an answer on STDIN.
    """
    fnname = fnobj._name
    if hasattr(fnobj, 'graph'):
        # get the annotation of the input arguments and the result
        graph = fnobj.graph
        annotator = db.translator.annotator
        args_s = [annotator.binding(v) for v in graph.getargs()]
        s_result = annotator.binding(graph.getreturnvar())
    else:
        # pure external function - fall back to the annotations
        # corresponding to the ll types
        FUNCTYPE = lltype.typeOf(fnobj)
        args_s = [lltype_to_annotation(ARG) for ARG in FUNCTYPE.ARGS]
        s_result = lltype_to_annotation(FUNCTYPE.RESULT)

    try:
        if force_stub:   # old case - don't try to support suggested_primitive
            raise NotImplementedError("sandboxing for external function '%s'"
                                      % (fnname,))

        dump_arguments = rmarshal.get_marshaller(tuple(args_s))
        load_result = rmarshal.get_loader(s_result)

    except (NotImplementedError,
            rmarshal.CannotMarshal,
            rmarshal.CannotUnmarshall), e:
        msg = 'Not Implemented: %s' % (e,)
        log.WARNING(msg)
        def execute(*args):
            not_implemented_stub(msg)

    else:
        def execute(*args):
            # marshal the function name and input arguments
            buf = []
            dump_string(buf, fnname)
            dump_arguments(buf, args)
            # send the buffer and wait for the answer
            loader = sandboxed_io(buf)
            # decode the answer
            result = load_result(loader)
            loader.check_finished()
            return result
    execute = func_with_new_name(execute, 'sandboxed_' + fnname)

    ann = MixLevelHelperAnnotator(db.translator.rtyper)
    graph = ann.getgraph(execute, args_s, s_result)
    ann.finish()
    return graph
