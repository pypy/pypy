secondary_entrypoints = {}

import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.objectmodel import we_are_translated


def entrypoint_lowlevel(key, argtypes, c_name=None, relax=False):
    """ Note: entrypoint should call llop.gc_stack_bottom on it's own.
    That's necessary for making it work with asmgcc and hence JIT

    If in doubt, use entrypoint().

    if key == 'main' than it's included by default
    """
    from rpython.translator.tool.cbuild import ExternalCompilationInfo

    def deco(func):
        secondary_entrypoints.setdefault(key, []).append((func, argtypes))
        if c_name is not None:
            func.c_name = c_name
        if relax:
            func.relax_sig_check = True
        func._compilation_info = ExternalCompilationInfo(
            export_symbols=[c_name or func.func_name])
        return func
    return deco


pypy_debug_catch_fatal_exception = rffi.llexternal('pypy_debug_catch_fatal_exception', [], lltype.Void)

def entrypoint(key, argtypes, c_name=None):
    """if key == 'main' than it's included by default
    """
    from rpython.translator.tool.cbuild import ExternalCompilationInfo

    def deco(func):
        source = py.code.Source("""
        def wrapper(%(args)s):
            # the tuple has to be killed, but it's fine because this is
            # called from C
            rffi.stackcounter.stacks_counter += 1
            llop.gc_stack_bottom(lltype.Void)   # marker for trackgcroot.py
            # this should not raise
            try:
                res = func(%(args)s)
            except Exception, e:
                if not we_are_translated():
                    import traceback
                    traceback.print_exc()
                    raise
                else:
                    print str(e)
                    pypy_debug_catch_fatal_exception()
                    llop.debug_fatalerror(lltype.Void, "error in c callback")
                    assert 0 # dead code
            rffi.stackcounter.stacks_counter -= 1
            return res
        """ % {'args': ', '.join(['arg%d' % i for i in range(len(argtypes))])})
        d = {'rffi': rffi, 'lltype': lltype,
         'pypy_debug_catch_fatal_exception': pypy_debug_catch_fatal_exception,
         'llop': llop, 'func': func, 'we_are_translated': we_are_translated}
        exec source.compile() in d
        wrapper = d['wrapper']
        secondary_entrypoints.setdefault(key, []).append((wrapper, argtypes))
        wrapper.func_name = func.func_name
        if c_name is not None:
            wrapper.c_name = c_name
        wrapper._compilation_info = ExternalCompilationInfo(
            export_symbols=[c_name or func.func_name])
        return wrapper
    return deco

# the point of dance below is so the call to rpython_startup_code actually
# does call asm_stack_bottom. It's here because there is no other good place.
# This thing is imported by any target which has any API, so it'll get
# registered

RPython_StartupCode = rffi.llexternal('RPython_StartupCode', [], lltype.Void,
                                      _nowrapper=True,
                                      random_effects_on_gcobjs=True)

@entrypoint('main', [], c_name='rpython_startup_code')
def rpython_startup_code():
    return RPython_StartupCode()
