"""Run a subprocess.  Wrapper around the 'subprocess' module
with a hack to prevent bogus out-of-memory conditions in os.fork()
if the current process already grew very large.
"""

import sys, os
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
    pipe = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell, env=env, cwd=cwd)
    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout, stderr


if __name__ == '__main__':
    while True:
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
    _child_stdin, _child_stdout = os.popen2(
        "'%s' '%s'" % (sys.executable, _source))

    def _run(*args):
        _child_stdin.write('%r\n' % (args,))
        _child_stdin.flush()
        results = _child_stdout.readline()
        assert results.startswith('(')
        results = eval(results)
        if results[0] is None:
            raise OSError(results[1])
        return results
