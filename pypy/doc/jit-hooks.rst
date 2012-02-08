JIT hooks in PyPy
=================

There are several hooks in the `pypyjit` module that may help you with
understanding what's pypy's JIT doing while running your program. There
are three functions related to that coming from the `pypyjit` module:

* `set_optimize_hook`::

    Set a compiling hook that will be called each time a loop is optimized,
    but before assembler compilation. This allows to add additional
    optimizations on Python level.
    
    The hook will be called with the following signature:
    hook(jitdriver_name, loop_type, greenkey or guard_number, operations)

    jitdriver_name is the name of this particular jitdriver, 'pypyjit' is
    the main interpreter loop

    loop_type can be either `loop` `entry_bridge` or `bridge`
    in case loop is not `bridge`, greenkey will be a tuple of constants
    or a string describing it.

    for the interpreter loop` it'll be a tuple
    (code, offset, is_being_profiled)

    Note that jit hook is not reentrant. It means that if the code
    inside the jit hook is itself jitted, it will get compiled, but the
    jit hook won't be called for that.

    Result value will be the resulting list of operations, or None

* `set_compile_hook`::

    Set a compiling hook that will be called each time a loop is compiled.
    The hook will be called with the following signature:
    hook(jitdriver_name, loop_type, greenkey or guard_number, operations,
         assembler_addr, assembler_length)

    jitdriver_name is the name of this particular jitdriver, 'pypyjit' is
    the main interpreter loop

    loop_type can be either `loop` `entry_bridge` or `bridge`
    in case loop is not `bridge`, greenkey will be a tuple of constants
    or a string describing it.

    for the interpreter loop` it'll be a tuple
    (code, offset, is_being_profiled)

    assembler_addr is an integer describing where assembler starts,
    can be accessed via ctypes, assembler_lenght is the lenght of compiled
    asm

    Note that jit hook is not reentrant. It means that if the code
    inside the jit hook is itself jitted, it will get compiled, but the
    jit hook won't be called for that.

* `set_abort_hook`::

    Set a hook (callable) that will be called each time there is tracing
    aborted due to some reason.

    The hook will be called as in: hook(jitdriver_name, greenkey, reason)

    Where reason is the reason for abort, see documentation for set_compile_hook
    for descriptions of other arguments.
