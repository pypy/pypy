from _decimal import getcontext, setcontext

class _ContextManager(object):
    """Context manager class to support localcontext()."""
    def __init__(self, new_context):
        self.new_context = new_context.copy()
    def __enter__(self):
        self.saved_context = getcontext()
        setcontext(self.new_context)
        return self.new_context
    def __exit__(self, t, v, tb):
        setcontext(self.saved_context)

def localcontext(ctx=None):
    if ctx is None:
        ctx = getcontext()
    return _ContextManager(ctx)
