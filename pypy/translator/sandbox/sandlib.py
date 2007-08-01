"""
A Python library to execute and communicate with a subprocess that
was translated from RPython code with --sandbox.  This library is
for the outer process, which can run CPython or PyPy.
"""

from py.compat import subprocess
from pypy.translator.sandbox.sandboxmsg import Message, encode_message
from pypy.translator.sandbox.sandboxmsg import read_message

class SandboxedProc(object):
    """Base class to control a sandboxed subprocess.
    Inherit from this class and implement all the do_xxx() methods
    for the external functions xxx that you want to support.
    """
    def __init__(self, args):
        """'args' should a sequence of argument for the subprocess,
        starting with the full path of the executable.
        """
        self.popen = subprocess.Popen(args,
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE)

    def poll(self):
        return self.popen.poll()

    def wait(self):
        return self.popen.wait()

    def handle_forever(self):
        while True:
            try:
                msg = read_message(self.popen.stdout)
            except EOFError, e:
                break
            answer = self.handle_message(msg)
            self.popen.stdin.write(answer)
        returncode = self.popen.wait()
        if returncode != 0:
            raise OSError("the sandboxed subprocess exited with code %d" % (
                returncode,))

    def handle_message(self, msg):
        fn = msg.nextstring()
        try:
            argtypes, restypes = self.TYPES[fn]
        except KeyError:
            raise IOError("trying to invoke unknown external function %r" % (
                fn,))
        handler = getattr(self, 'do_' + fn)
        answers = handler(*msg.decode(argtypes))
        if len(restypes) == 0:
            assert answers is None
            answers = (0,)
        elif len(restypes) == 1:
            answers = (0, answers)
        else:
            answers = (0,) + answers
        return encode_message("i" + restypes, answers)

    TYPES = {
        "open": ("sii", "i"),
        "read": ("iI", "s"),
        "write": ("is", "I"),
        "close": ("i", "i"),
        }


class SimpleIOSandboxedProc(SandboxedProc):
    """Control a sandboxed subprocess which is only allowed to read from
    its stdin and write to its stdout and stderr.
    """
    _input = None
    _output = None
    _error = None

    def communicate(self, input=None):
        """Send data to stdin. Read data from stdout and stderr,
        until end-of-file is reached. Wait for process to terminate.
        """
        import cStringIO
        if input:
            if isinstance(input, str):
                input = cStringIO.StringIO(input)
            self._input = input
        self._output = cStringIO.StringIO()
        self._error = cStringIO.StringIO()
        self.handle_forever()
        output = self._output.getvalue()
        self._output = None
        error = self._error.getvalue()
        self._error = None
        return (output, error)

    def do_read(self, fd, size):
        if fd == 0:
            if self._input is None:
                return ""
            else:
                return self._input.read(size)
        raise OSError("trying to read from fd %d" % (fd,))

    def do_write(self, fd, data):
        if fd == 1:
            self._output.write(data)
            return len(data)
        if fd == 2:
            self._error.write(data)
            return len(data)
        raise OSError("trying to write to fd %d" % (fd,))
