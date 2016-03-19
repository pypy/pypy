

def make_sandbox_trampoline(fnname, args_s, s_result):
    """Create a trampoline function with the specified signature.

    The trampoline is meant to be used in place of real calls to the external
    function named 'fnname'.  Instead, it calls a function pointer that is
    under control of the main C program using the sandboxed library.
    """
    def execute(*args):
        raise NotImplementedError
    execute.__name__ = 'sandboxed_%s' % (fnname,)
    return execute
