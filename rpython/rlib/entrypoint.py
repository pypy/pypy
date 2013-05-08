secondary_entrypoints = {}


def entrypoint(key, argtypes, c_name=None, relax=False):
    """ Note: entrypoint should call llop.gc_stack_bottom on it's own.
    That's necessary for making it work with asmgcc and hence JIT

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

# the point of dance below is so the call to rpython_startup_code actually
# does call asm_stack_bottom. It's here because there is no other good place.
# This thing is imported by any target which has any API, so it'll get
# registered

from rpython.rtyper.lltypesystem import lltype, rffi

RPython_StartupCode = rffi.llexternal('RPython_StartupCode', [], lltype.Void)

@entrypoint('main', [], c_name='rpython_startup_code')
def rpython_startup_code():
    return RPython_StartupCode()
