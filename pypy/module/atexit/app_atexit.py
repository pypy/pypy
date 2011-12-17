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
    last_exc, last_tb = None, None
    for (func, args, kwargs) in atexit_callbacks:
        if func is None:
            # unregistered slot
            continue
        try:
            func(*args, **kwargs)
        except BaseException as e:
            if not isinstance(e, SystemExit):
                import traceback
                last_type, last_exc, last_tb = sys.exc_info()
                traceback.print_exception(last_type, last_exc, last_tb)

    clear()

    if last_exc is not None:
        raise last_exc.with_traceback(last_tb)

def clear():
    "Clear the list of previously registered exit functions."
    del atexit_callbacks[:]

def unregister(func):
    """Unregister a exit function which was previously registered using
    atexit.register"""
    for i, (f, _, _) in enumerate(atexit_callbacks):
        if f == func:
            atexit_callbacks[i] = (None, None, None)
