atexit_callbacks = []

def register(func, *args, **kwargs):
    """Register a function to be executed upon normal program termination.

    func - function to be called at exit
    args - optional arguments to pass to func
    kwargs - optional keyword arguments to pass to func

    func is returned to facilitate usage as a decorator."""

    if not callable(func):
        raise TypeError("func must be callable")

    atexit_callbacks.append((func, args, kwargs))
    return func

def run_exitfuncs():
    "Run all registered exit functions."
    # Maintain the last exception
    for (func, args, kwargs) in reversed(atexit_callbacks):
        if func is None:
            # unregistered slot
            continue
        try:
            func(*args, **kwargs)
        except BaseException as e:
            import __pypy__
            __pypy__.write_unraisable("in atexit callback", e, func)

    clear()

def clear():
    "Clear the list of previously registered exit functions."
    del atexit_callbacks[:]

def unregister(func):
    """Unregister a exit function which was previously registered using
    atexit.register"""
    for i, (f, _, _) in enumerate(atexit_callbacks):
        if f == func:
            atexit_callbacks[i] = (None, None, None)

def ncallbacks():
    return len(atexit_callbacks)
