import py
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.annlowlevel import cast_instance_to_gcref, cast_base_ptr_to_instance
from rpython.rlib.objectmodel import we_are_translated, CDefinedIntSymbolic
from rpython.rlib import jit, rgc, rposix
from rpython.tool.pairtype import extendabletype
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pycode import PyCode

FALSE_BUT_NON_CONSTANT = CDefinedIntSymbolic('0', default=0)

ROOT = py.path.local(__file__).join('..')
SRC = ROOT.join('src')

# by default, we statically link vmprof.c into pypy; however, if you set
# DYNAMIC_VMPROF to True, it will be dynamically linked to the libvmprof.so
# which is expected to be inside pypy/module/_vmprof/src: this is very useful
# during development. Note that you have to manually build libvmprof by
# running make inside the src dir
DYNAMIC_VMPROF = False

eci_kwds = dict(
    include_dirs = [SRC],
    includes = ['vmprof.h', 'trampoline.h'],
    separate_module_files = [SRC.join('trampoline.asmgcc.s')],
    libraries = ['unwind'],
    
    post_include_bits=["""
        void* pypy_vmprof_get_virtual_ip(void*);
        void pypy_vmprof_init(void);
    """],
    
    separate_module_sources=["""
        void pypy_vmprof_init(void) {
            vmprof_set_mainloop(pypy_execute_frame_trampoline, 0,
                                pypy_vmprof_get_virtual_ip);
        }
    """],
    )


if DYNAMIC_VMPROF:
    eci_kwds['libraries'] += ['vmprof']
    eci_kwds['link_extra'] = ['-Wl,-rpath,%s' % SRC, '-L%s' % SRC]
else:
    eci_kwds['separate_module_files'] += [SRC.join('vmprof.c')]

eci = ExternalCompilationInfo(**eci_kwds)


pypy_execute_frame_trampoline = rffi.llexternal(
    "pypy_execute_frame_trampoline",
    [llmemory.GCREF, llmemory.GCREF, llmemory.GCREF],
    llmemory.GCREF,
    compilation_info=eci,
    _nowrapper=True, sandboxsafe=True,
    random_effects_on_gcobjs=True)

pypy_vmprof_init = rffi.llexternal("pypy_vmprof_init", [], lltype.Void,
                                   compilation_info=eci)
vmprof_enable = rffi.llexternal("vmprof_enable",
                                [rffi.INT, rffi.INT, rffi.LONG],
                                rffi.INT, compilation_info=eci)
vmprof_disable = rffi.llexternal("vmprof_disable", [], rffi.INT,
                                 compilation_info=eci)

vmprof_register_virtual_function = rffi.llexternal(
    "vmprof_register_virtual_function",
    [rffi.CCHARP, rffi.VOIDP, rffi.VOIDP], lltype.Void,
    compilation_info=eci)

original_execute_frame = PyFrame.execute_frame.im_func
original_execute_frame.c_name = 'pypy_pyframe_execute_frame'
original_execute_frame._dont_inline_ = True

class __extend__(PyFrame):
    def execute_frame(frame, w_inputvalue=None, operr=None):
        # go through the asm trampoline ONLY if we are translated but not being JITted.
        #
        # If we are not translated, we obviously don't want to go through the
        # trampoline because there is no C function it can call.
        #
        # If we are being JITted, we want to skip the trampoline, else the JIT
        # cannot see throug it
        if we_are_translated() and not jit.we_are_jitted():
            # if we are translated, call the trampoline
            gc_frame = cast_instance_to_gcref(frame)
            gc_inputvalue = cast_instance_to_gcref(w_inputvalue)
            gc_operr = cast_instance_to_gcref(operr)
            gc_result = pypy_execute_frame_trampoline(gc_frame, gc_inputvalue, gc_operr)
            return cast_base_ptr_to_instance(W_Root, gc_result)
        else:
            return original_execute_frame(frame, w_inputvalue, operr)



class __extend__(PyCode):
    __metaclass__ = extendabletype

    def _vmprof_setup_maybe(self):
        self._vmprof_virtual_ip = _vmprof.get_next_virtual_IP()
        self._vmprof_registered = 0

# avoid rtyper warnings
PyCode._vmprof_virtual_ip = 0
PyCode._vmprof_registered = 0



def get_virtual_ip(gc_frame):
    frame = cast_base_ptr_to_instance(PyFrame, gc_frame)
    if jit._get_virtualizable_token(frame):
        return rffi.cast(rffi.VOIDP, 0)
    virtual_ip = do_get_virtual_ip(frame)
    return rffi.cast(rffi.VOIDP, virtual_ip)
get_virtual_ip.c_name = 'pypy_vmprof_get_virtual_ip'
get_virtual_ip._dont_inline_ = True

def strncpy(src, tgt, tgt_ofs, count):
    if len(src) < count:
        count = len(src)
    i = 0
    while i < count:
        tgt[i + tgt_ofs] = src[i]
        i += 1
    return i

def int2str(num, s, ofs):
    if num == 0:
        s[ofs] = '0'
        return 1
    count = 0
    c = num
    while c != 0:
        count += 1
        c /= 10
    pos = ofs + count - 1
    c = num
    while c != 0:
        s[pos] = chr(ord('0') + c % 10)
        c /= 10
        pos -= 1
    return count

@rgc.no_collect
def do_get_virtual_ip(frame):
    virtual_ip = frame.pycode._vmprof_virtual_ip
    if not frame.pycode._vmprof_registered:
        # we need to register this code object
        name = frame.pycode.co_name
        filename = frame.pycode.co_filename
        firstlineno = frame.pycode.co_firstlineno
        start = rffi.cast(rffi.VOIDP, virtual_ip)
        end = start # ignored for now
        #
        # manually fill the C buffer; we cannot use str2charp because we
        # cannot call malloc from a signal handler
        strbuf = _vmprof.strbuf
        ofs = strncpy("py:", _vmprof.strbuf, 0, len("py:"))
        ofs += strncpy(filename, _vmprof.strbuf, ofs, 128)
        _vmprof.strbuf[ofs] = ':'
        ofs += 1
        ofs += int2str(firstlineno, _vmprof.strbuf, ofs)
        _vmprof.strbuf[ofs] = ':'
        ofs += 1
        ofs += strncpy(name, _vmprof.strbuf, ofs, 1024 - 1 - ofs)
        _vmprof.strbuf[ofs] = '\x00'
        vmprof_register_virtual_function(strbuf, start, end)
        frame.pycode._vmprof_registered = 1
    #
    return virtual_ip



class VMProf(object):
    def __init__(self):
        self.virtual_ip = 0
        self.is_enabled = False
        self.ever_enabled = False
        self.strbuf = lltype.malloc(rffi.CCHARP.TO, 1024, flavor='raw', immortal=True, zero=True)

    def get_next_virtual_IP(self):
        self.virtual_ip -= 1
        return self.virtual_ip

    @jit.dont_look_inside
    def _annotate_get_virtual_ip(self):
        if FALSE_BUT_NON_CONSTANT:
            # make sure it's annotated
            gcref = rffi.cast(llmemory.GCREF, self.virtual_ip) # just a random non-constant value
            get_virtual_ip(gcref)            

    def enable(self, space, fileno, symno, period):
        self._annotate_get_virtual_ip()
        if self.is_enabled:
            raise oefmt(space.w_ValueError, "_vmprof already enabled")
        self.is_enabled = True
        if not self.ever_enabled:
            pypy_vmprof_init()
            self.ever_enabled = True
        res = vmprof_enable(fileno, symno, period)
        if res == -1:
            raise wrap_oserror(space, OSError(rposix.get_errno(),
                                              "_vmprof.enable"))

    def disable(self, space):
        if not self.is_enabled:
            raise oefmt(space.w_ValueError, "_vmprof not enabled")
        self.is_enabled = False
        res = vmprof_disable()
        if res == -1:
            raise wrap_oserror(space, OSError(rposix.get_errno(),
                                              "_vmprof.disable"))

_vmprof = VMProf()

@unwrap_spec(filename=str, period=int)
def enable(space, filename, period=-1):
    _vmprof.enable(space, filename, period)

def disable(space):
    _vmprof.disable(space)

