# NOT_RPYTHON

enabled = True

def isenabled():
    global enabled
    return enabled

def enable():
    global enabled
    import gc
    if not enabled:
        gc.enable_finalizers()
        enabled = True

def disable():
    global enabled
    import gc
    if enabled:
        gc.disable_finalizers()
        enabled = False
