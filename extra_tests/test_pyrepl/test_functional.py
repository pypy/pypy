#   Copyright 2000-2007 Michael Hudson-Doyle <micahel@gmail.com>
#                       Maciek Fijalkowski
# License: MIT
# some functional tests, to see if this is really working

from contextlib import contextmanager
import sys, os


@contextmanager
def start_repl():
    try:
        import pexpect
    except ImportError:
        pytest.skip("no pexpect module")
    except SyntaxError:
        pytest.skip('pexpect wont work on py3k')
    child = pexpect.spawn(
        sys.executable,
        ['-S', '-c', "from pyrepl.main import interactive_console as __pyrepl_interactive_console; __pyrepl_interactive_console()"],
        env=os.environ | {"PYTHON_COLORS": "0"},
        timeout=10, encoding="utf-8")
    child.logfile = sys.stdout
    yield child
    child.close()


def test_basic():
    with start_repl() as child:
        child.sendline('a = 120202012012')
        child.sendline('a')
        child.expect('120202012012')

def test_error():
    with start_repl() as child:
        child.sendline('1/0')
        child.expect('Traceback.*File.*1/0.*ZeroDivisionError: division by zero')

def test_ctrl_left_ctrl_right():
    with start_repl() as child:
        child.send('abc 123456789')
        child.send('\033[1;5D') # ctrl-left
        child.send('=')
        child.send('\033[1;5C') # ctrl-right
        child.sendline('88888')
        child.sendline('abc')
        child.expect('12345678988888')
