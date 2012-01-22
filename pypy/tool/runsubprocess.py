"""Run a subprocess.  Wrapper around the 'subprocess' module
with a hack to prevent bogus out-of-memory conditions in os.fork()
if the current process already grew very large.
"""

import sys, gc
import os
from subprocess import PIPE, Popen

def run_subprocess(executable, args, env=None, cwd=None):
    return _run(executable, args, env, cwd)


def _run(executable, args, env, cwd):   # unless overridden below
    if isinstance(args, str):
        args = str(executable) + ' ' + args
        shell = True
    else:
        if args is None:
            args = [str(executable)]
        else:
            args = [str(executable)] + args
        shell = False
    # Just before spawning the subprocess, do a gc.collect().  This
    # should help if we are running on top of PyPy, if the subprocess
    # is going to need a lot of RAM and we are using a lot too.
    gc.collect()
    #
    pipe = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell, env=env, cwd=cwd)
    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout, stderr


if __name__ == '__main__':
    import gc
    while True:
        gc.collect()
        operation = sys.stdin.readline()
        if not operation:
            sys.exit()
        assert operation.startswith('(')
        args = eval(operation)
        try:
            results = _run(*args)
        except EnvironmentError, e:
            results = (None, str(e))
        sys.stdout.write('%r\n' % (results,))
        sys.stdout.flush()


if sys.platform != 'win32' and hasattr(os, 'fork'):
    # do this at import-time, when the process is still tiny
    _source = os.path.dirname(os.path.abspath(__file__))
    _source = os.path.join(_source, 'runsubprocess.py')   # and not e.g. '.pyc'

    def spawn_subprocess():
        global _child
        _child = Popen([sys.executable, _source], bufsize=0,
                       stdin=PIPE, stdout=PIPE, close_fds=True)
    spawn_subprocess()

    def cleanup_subprocess():
        global _child
        _child = None
    import atexit; atexit.register(cleanup_subprocess)

    def _run(*args):
        try:
            _child.stdin.write('%r\n' % (args,))
        except (OSError, IOError):
            # lost the child.  Try again...
            spawn_subprocess()
            _child.stdin.write('%r\n' % (args,))
        results = _child.stdout.readline()
        assert results.startswith('(')
        results = eval(results)
        if results[0] is None:
            raise OSError('%s: %s\nargs=%r' % (args[0], results[1], args))
        return results
