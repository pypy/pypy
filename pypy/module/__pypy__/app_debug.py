
def remote_exec(pid, code, wait=True):
    """
    Executes a block of Python code in a given remote Python process.

    Arguments:
         pid (int): The process ID of the target Python process.

         code (str): A string containing the Python code to be executed.

         wait (bool): Whether to wait for the target process to start the debug
         script execution before remote_exec returns. True by default.
    """
    import operator
    pid = operator.index(pid)
    if isinstance(code, bytes):
        pass
    elif isinstance(code, unicode):
        code = code.encode('utf-8')
    
    from _pypy_remote_debug import start_debugger
    start_debugger(pid, code, bool(wait))

