import py, os, struct
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.annlowlevel import cast_instance_to_gcref, cast_base_ptr_to_instance
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import jit, rposix, entrypoint
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt, wrap_oserror, OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pyframe import PyFrame

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
                                [rffi.INT, rffi.INT, rffi.LONG, rffi.INT],
                                rffi.INT, compilation_info=eci)
vmprof_disable = rffi.llexternal("vmprof_disable", [], rffi.INT,
                                 compilation_info=eci)

vmprof_register_virtual_function = rffi.llexternal(
    "vmprof_register_virtual_function",
    [rffi.CCHARP, rffi.VOIDP, rffi.VOIDP], lltype.Void,
    compilation_info=eci, _nowrapper=True)

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


@entrypoint.entrypoint_lowlevel('main', [llmemory.GCREF],
                                'pypy_vmprof_get_virtual_ip', True)
def get_virtual_ip(gc_frame):
    frame = cast_base_ptr_to_instance(PyFrame, gc_frame)
    if jit._get_virtualizable_token(frame):
        return rffi.cast(rffi.VOIDP, 0)
    virtual_ip = do_get_virtual_ip(frame)
    return rffi.cast(rffi.VOIDP, virtual_ip)

def do_get_virtual_ip(frame):
    return frame.pycode._unique_id



class VMProf(object):
    def __init__(self):
        self.is_enabled = False
        self.ever_enabled = False
        self.mapping_so_far = [] # stored mapping in between runs
        self.fileno = -1

    def enable(self, space, fileno, period):
        if self.is_enabled:
            raise oefmt(space.w_ValueError, "_vmprof already enabled")
        self.fileno = fileno
        self.is_enabled = True
        self.write_header(fileno, period)
        if not self.ever_enabled:
            if we_are_translated():
                pypy_vmprof_init()
            self.ever_enabled = True
        for weakcode in space.all_code_objs.get_all_handles():
            code = weakcode()
            if code:
                self.register_code(space, code)
        space.set_code_callback(self.register_code)
        if we_are_translated():
            # does not work untranslated
            res = vmprof_enable(fileno, -1, period, 0)
        else:
            res = 0
        if res == -1:
            raise wrap_oserror(space, OSError(rposix.get_errno(),
                                              "_vmprof.enable"))

    def write_header(self, fileno, period):
        if period == -1:
            period_usec = 1000000 / 100 #  100hz
        else:
            period_usec = period
        os.write(fileno, struct.pack("lllll", 0, 3, 0, period_usec, 0))

    def register_code(self, space, code):
        if self.fileno == -1:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("vmprof not running"))
        name = code._get_full_name()
        s = '\x02' + struct.pack("ll", code._unique_id, len(name)) + name
        os.write(self.fileno, s)

    def disable(self, space):
        if not self.is_enabled:
            raise oefmt(space.w_ValueError, "_vmprof not enabled")
        self.is_enabled = False
        self.fileno = -1
        if we_are_translated():
           # does not work untranslated
            res = vmprof_disable()
        else:
            res = 0
        space.set_code_callback(None)
        if res == -1:
            raise wrap_oserror(space, OSError(rposix.get_errno(),
                                              "_vmprof.disable"))

@unwrap_spec(fileno=int, period=int)
def enable(space, fileno, period=-1):
    space.getbuiltinmodule('_vmprof').vmprof.enable(space, fileno, period)

def disable(space):
    space.getbuiltinmodule('_vmprof').vmprof.disable(space)

