#   Copyright 2000-2007 Michael Hudson-Doyle <micahel@gmail.com>
#                       Maciek Fijalkowski
# License: MIT
# some functional tests, to see if this is really working

from contextlib import contextmanager
import sys, os


@contextmanager
def start_repl(extra_env=dict(), explicit_pyrepl=True):
    try:
        import pexpect
    except ImportError:
        pytest.skip("no pexpect module")
    except SyntaxError:
        pytest.skip('pexpect wont work on py3k')
    args = []
    if explicit_pyrepl:
        args = ['-S', '-c', "from pyrepl.main import interactive_console as __pyrepl_interactive_console; __pyrepl_interactive_console()"],
    child = pexpect.spawn(
        sys.executable,
        env=os.environ | {"PYTHON_COLORS": "0"} | extra_env,
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

def test_sys_excepthook_is_broken():
    with start_repl() as child:
        child.sendline("import sys")
        child.sendline("sys.excepthook = 1")
        child.sendline("1/0")
        child.expect('Error in sys.excepthook.*object is not callable.*Traceback(.*)ZeroDivisionError: division by zero')
        child.sendline('a = 10000000000')
        child.sendline('a * 5')
        child.expect('50000000000')

def test_sys_tracebacklimit_is_correct():
    with start_repl() as child:
        child.sendline("def x1(): 1/0")
        child.sendline("def x2(): x1()")
        child.sendline("def x3(): x2()")
        child.sendline("x3()")
        child.expect('Traceback.*File.*in x3.*File.*in x2.*File.*in x1.*1/0.*ZeroDivisionError: division by zero')
        child.sendline("import sys")
        child.sendline("sys.tracebacklimit=1")
        child.sendline("x3()")
        child.expect('Traceback(.*)ZeroDivisionError: division by zero')
        assert "x3" not in child.match.group(1)

def test_dumb_terminal():
    with start_repl(extra_env=dict(TERM="dumb"), explicit_pyrepl=False) as child:
        child.sendline('a = 10000000000')
        child.sendline('a * 5')
        child.expect('50000000000')
        assert "InvalidTerminal" not in child.match.string
