
def remote_exec(pid, filename, wait=True):
    """
    Executes a script of Python code in a given remote Python process.

    Arguments:
         pid (int): The process ID of the target Python process.

         filename (str): A string containing the path to the file with the Python code to be executed.

         wait (bool): Whether to wait for the target process to start the debug
         script execution before remote_exec returns. True by default.
    """
    import operator
    pid = operator.index(pid)
    if isinstance(filename, bytes):
        pass
    elif isinstance(filename, unicode):
        filename = filename.encode('utf-8')
    
    from _pypy_remote_debug import start_debugger
    start_debugger(pid, filename, bool(wait))

