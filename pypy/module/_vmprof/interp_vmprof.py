import py, os, sys
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.annlowlevel import cast_instance_to_gcref, cast_base_ptr_to_instance
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import jit, rposix, rgc
from rpython.rlib.rarithmetic import ovfcheck_float_to_int
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib.rstring import StringBuilder
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt, wrap_oserror, OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pycode import PyCode

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
    libraries = ['dl'],
    
    post_include_bits=["""
        int pypy_vmprof_init(void);
    """],
    
    separate_module_sources=["""
        int pypy_vmprof_init(void) {
            return vmprof_set_mainloop(pypy_execute_frame_trampoline, 0,
                                NULL);
        }
    """],
    )


if DYNAMIC_VMPROF:
    eci_kwds['libraries'] += ['vmprof']
    eci_kwds['link_extra'] = ['-Wl,-rpath,%s' % SRC, '-L%s' % SRC]
else:
    eci_kwds['separate_module_files'] += [SRC.join('vmprof.c')]

eci = ExternalCompilationInfo(**eci_kwds)

check_eci = eci.merge(ExternalCompilationInfo(separate_module_files=[
    SRC.join('fake_pypy_api.c')]))

platform.verify_eci(check_eci)

pypy_execute_frame_trampoline = rffi.llexternal(
    "pypy_execute_frame_trampoline",
    [llmemory.GCREF, llmemory.GCREF, llmemory.GCREF, lltype.Signed],
    llmemory.GCREF,
    compilation_info=eci,
    _nowrapper=True, sandboxsafe=True,
    random_effects_on_gcobjs=True)

pypy_vmprof_init = rffi.llexternal("pypy_vmprof_init", [], rffi.INT,
                                   compilation_info=eci)
vmprof_enable = rffi.llexternal("vmprof_enable",
                                [rffi.INT, rffi.LONG, rffi.INT,
                                 rffi.CCHARP, rffi.INT],
                                rffi.INT, compilation_info=eci,
                                save_err=rffi.RFFI_SAVE_ERRNO)
vmprof_disable = rffi.llexternal("vmprof_disable", [], rffi.INT,
                                 compilation_info=eci,
                                save_err=rffi.RFFI_SAVE_ERRNO)
vmprof_get_error = rffi.llexternal("vmprof_get_error", [], rffi.CCHARP,
                                   compilation_info=eci,
                                   save_err=rffi.RFFI_SAVE_ERRNO)

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
            unique_id = frame.pycode._unique_id
            gc_result = pypy_execute_frame_trampoline(gc_frame, gc_inputvalue,
                                                      gc_operr, unique_id)
            return cast_base_ptr_to_instance(W_Root, gc_result)
        else:
            return original_execute_frame(frame, w_inputvalue, operr)



def write_long_to_string_builder(l, b):
    if sys.maxint == 2147483647:
        b.append(chr(l & 0xff))
        b.append(chr((l >> 8) & 0xff))
        b.append(chr((l >> 16) & 0xff))
        b.append(chr((l >> 24) & 0xff))
    else:
        b.append(chr(l & 0xff))
        b.append(chr((l >> 8) & 0xff))
        b.append(chr((l >> 16) & 0xff))
        b.append(chr((l >> 24) & 0xff))
        b.append(chr((l >> 32) & 0xff))
        b.append(chr((l >> 40) & 0xff))
        b.append(chr((l >> 48) & 0xff))
        b.append(chr((l >> 56) & 0xff))

def try_cast_to_pycode(gcref):
    return rgc.try_cast_gcref_to_instance(PyCode, gcref)

MAX_CODES = 1000

class VMProf(object):
    def __init__(self):
        self.is_enabled = False
        self.ever_enabled = False
        self.fileno = -1
        self.current_codes = []

    def enable(self, space, fileno, period_usec):
        if self.is_enabled:
            raise oefmt(space.w_ValueError, "_vmprof already enabled")
        self.fileno = fileno
        self.is_enabled = True
        self.write_header(fileno, period_usec)
        if not self.ever_enabled:
            if we_are_translated():
                res = pypy_vmprof_init()
                if res:
                    raise OperationError(
                        space.w_IOError,
                        space.wrap(rffi.charp2str(vmprof_get_error())))
            self.ever_enabled = True
        self.gather_all_code_objs(space)
        space.register_code_callback(vmprof_register_code)
        if we_are_translated():
            # does not work untranslated
            res = vmprof_enable(fileno, period_usec, 0,
                                lltype.nullptr(rffi.CCHARP.TO), 0)
        else:
            res = 0
        if res == -1:
            raise wrap_oserror(space, OSError(rposix.get_saved_errno(),
                                              "_vmprof.enable"))

    def gather_all_code_objs(self, space):
        all_code_objs = rgc.do_get_objects(try_cast_to_pycode)
        for code in all_code_objs:
            self.register_code(space, code)

    def write_header(self, fileno, period_usec):
        assert period_usec > 0
        b = StringBuilder()
        write_long_to_string_builder(0, b)
        write_long_to_string_builder(3, b)
        write_long_to_string_builder(0, b)
        write_long_to_string_builder(period_usec, b)
        write_long_to_string_builder(0, b)
        b.append('\x04') # interp name
        b.append(chr(len('pypy')))
        b.append('pypy')
        os.write(fileno, b.build())

    def register_code(self, space, code):
        if self.fileno == -1:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("vmprof not running"))
        self.current_codes.append(code)
        if len(self.current_codes) >= MAX_CODES:
            self._flush_codes(space)

    def _flush_codes(self, space):
        b = StringBuilder()
        for code in self.current_codes:
            name = code._get_full_name()
            b.append('\x02')
            write_long_to_string_builder(code._unique_id, b)
            write_long_to_string_builder(len(name), b)
            b.append(name)
        os.write(self.fileno, b.build())
        self.current_codes = []

    def disable(self, space):
        if not self.is_enabled:
            raise oefmt(space.w_ValueError, "_vmprof not enabled")
        self.is_enabled = False
        space.register_code_callback(None)
        self._flush_codes(space)
        self.fileno = -1
        if we_are_translated():
           # does not work untranslated
            res = vmprof_disable()
        else:
            res = 0
        if res == -1:
            raise wrap_oserror(space, OSError(rposix.get_saved_errno(),
                                              "_vmprof.disable"))

def vmprof_register_code(space, code):
    from pypy.module._vmprof import Module
    mod_vmprof = space.getbuiltinmodule('_vmprof')
    assert isinstance(mod_vmprof, Module)
    mod_vmprof.vmprof.register_code(space, code)

@unwrap_spec(fileno=int, period=float)
def enable(space, fileno, period=0.01):   # default 100 Hz
    from pypy.module._vmprof import Module
    mod_vmprof = space.getbuiltinmodule('_vmprof')
    assert isinstance(mod_vmprof, Module)
    #
    try:
        period_usec = ovfcheck_float_to_int(period * 1000000.0 + 0.5)
        if period_usec <= 0 or period_usec >= 1e6:
            # we don't want seconds here at all
            raise ValueError
    except (ValueError, OverflowError):
        raise OperationError(space.w_ValueError,
                             space.wrap("'period' too large or non positive"))
    #
    mod_vmprof.vmprof.enable(space, fileno, period_usec)

def disable(space):
    from pypy.module._vmprof import Module
    mod_vmprof = space.getbuiltinmodule('_vmprof')
    assert isinstance(mod_vmprof, Module)
    mod_vmprof.vmprof.disable(space)

