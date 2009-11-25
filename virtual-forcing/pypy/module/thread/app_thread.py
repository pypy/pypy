class error(Exception):
    pass

def exit():
    """This is synonymous to ``raise SystemExit''.  It will cause the current
thread to exit silently unless the exception is caught."""
    raise SystemExit
