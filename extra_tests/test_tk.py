import subprocess
import sys
import pytest

# Everything touching _tkinter runs in a subprocess: importing it loads
# libtcl, which installs pthread_atfork handlers and starts a notifier
# thread.  On macOS that makes any later test in this process which forks
# and then forks again (e.g. test_zdistutils) trap in Tcl's atfork handler.

def run_in_subprocess(code):
    prologue = ("import sys\n"
                "try:\n    import _tkinter\n"
                "except ImportError:\n    sys.exit(77)\n")
    proc = subprocess.run([sys.executable, '-c', prologue + code],
                          capture_output=True, text=True)
    if proc.returncode == 77:
        pytest.skip("_tkinter not available")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_encoding_mess_from_tcl_string():
    run_in_subprocess(r'''
from _tkinter.tclobj import FromTclString
# cesu-8 mess
assert FromTclString(b'string\xed\xa0\xbd\xed\xb2\xbb') == 'string\U0001f4bb'
''')


@pytest.mark.pypy_only
def test_image_adds_memory_pressure():
    run_in_subprocess(r'''
import tkinter

class FakeTk:
    # Supply image dimensions without requiring a display server.
    def call(self, *args):
        if args == ('image', 'width', 'test_image'):
            return '23'
        if args == ('image', 'height', 'test_image'):
            return '17'
        return ''

    getint = staticmethod(int)

pressures = []
tkinter.add_memory_pressure = pressures.append
image = tkinter.PhotoImage(name='test_image', master=FakeTk())
assert pressures == [23 * 17 * 3]
''')
