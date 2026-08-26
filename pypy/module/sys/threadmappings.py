def _current_frames(space):
    """_current_frames() -> dictionary

    Return a dictionary mapping each current thread T's thread id to T's
    current stack frame.  Functions in the traceback module can build the
    call stack given such a frame.

    Note that in PyPy with the JIT, calling this function causes a runtime
    penalty in all threads, depending on the internal JIT state.  In each
    thread, the penalty should only be noticeable if this call was done
    while in the middle of a long-running function.

    This function should be used for specialized purposes only."""
    w_result = space.newdict()
    ecs = space.threadlocals.getallvalues()
    for thread_ident, ec in ecs.items():
        w_topframe = ec.gettopframe_nohidden()
        if w_topframe is None:
            continue
        space.setitem(w_result,
                      space.newint_from_size_t(thread_ident),
                      w_topframe)
    return w_result


def _current_exceptions(space):
    """_current_exceptions() -> dictionary

    Return a dict mapping each thread's identifier to its current raised
    exception.

    Note that in PyPy with the JIT, calling this function causes a runtime
    penalty in all threads, depending on the internal JIT state.  In each
    thread, the penalty should only be noticeable if this call was done
    while in the middle of a long-running function.

    This function should be used for specialized purposes only."""
    w_result = space.newdict()
    ecs = space.threadlocals.getallvalues()
    for thread_ident, ec in ecs.items():
        operror = ec.sys_exc_info()
        if not operror:
            w_exc = space.w_None
        else:
            w_exc = operror.get_w_value(space)
        space.setitem(w_result,
                      space.newint_from_size_t(thread_ident),
                      w_exc)
    return w_result


