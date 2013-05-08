secondary_entrypoints = {}


def entrypoint(key, argtypes, c_name=None, relax=False):
    """ Note: entrypoint should call llop.gc_stack_bottom on it's own.
    That's necessary for making it work with asmgcc and hence JIT

    if key == 'main' than it's included by default
    """
    from rpython.translator.cbuild import ExternalCompilationInfo
    
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

