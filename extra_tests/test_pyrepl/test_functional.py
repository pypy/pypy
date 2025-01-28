#   Copyright 2000-2007 Michael Hudson-Doyle <micahel@gmail.com>
#                       Maciek Fijalkowski
# License: MIT
# some functional tests, to see if this is really working

import pytest
from contextlib import contextmanager
import sys, os
import pytest

try:
    from pexpect import spawn
except ImportError:
    pytest.skip(allow_module_level=True)

@contextmanager
def start_repl(extra_env=dict(), explicit_pyrepl=True, colors=False):
    args = []
    if explicit_pyrepl:
        args = ['-S', '-c', "from pyrepl.main import interactive_console as __pyrepl_interactive_console; __pyrepl_interactive_console()"],
    child = spawn(
        sys.executable,
        env=os.environ | {"PYTHON_COLORS": "1" if colors else "0"} | extra_env,
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

def test_hyperlinks_error():
    with start_repl(colors=True) as child:
        child.sendline("import traceback; list(traceback.walk_tb(1))")
        import socket
        import traceback
        child.expect(f"\x1b]8;;file://{traceback.__file__}\x1b.{traceback.__file__}\x1b]8;;\x1b.")

def test_dumb_terminal():
    with start_repl(extra_env=dict(TERM="dumb"), explicit_pyrepl=False) as child:
        child.sendline('a = 10000000000')
        child.sendline('a * 5')
        child.expect('50000000000')
        # assert "InvalidTerminal" not in child.match.string

def test_syntaxerror_correct_filename_and_positions():
    with start_repl(colors=False) as child:
        child.sendline('a bbbb c')
        child.expect('  File "<python-input-0>", line 1')
        child.expect('    a bbbb c')
        child.expect('^^^^')
        child.expect('SyntaxError')
    with start_repl(colors=False) as child:
        child.sendline('   124')
        child.expect('  File "<python-input-0>", line 1')
        child.expect('    124')
        child.expect('^^^^')
        child.expect('IndentationError')

def test_cmd_module_tab_completion_with_pyrepl_readline(tmpdir):
    fn = tmpdir / "cmdbug.py"
    fn.write("""
import cmd

class Console(cmd.Cmd):

    def do_abc(self, arg):
        print("ABC!!!!", arg)

    def do_exit(self, arg):
        raise SystemExit(0)

    def completedefault(self, text: str, line: str, begidx: int, endidx: int):
        return ["foo", "bar"]

if __name__ == "__main__":
    Console().cmdloop()
""")
    child = spawn(
        sys.executable,
        [str(fn)],
        env=os.environ,
        timeout=2, encoding="utf-8")
    try:
        child.sendline("a\t def")
        child.expect("ABC!!!! def")
        child.sendline("a\t f\t\t")
        child.expect("bar  foo")
    finally:
        child.close()

def test_sys_audit_called_in_pyrepl(tmpdir):
    with start_repl(colors=False) as child:
        child.sendline("import sys")
        child.sendline("sys.addaudithook(lambda name, *args: print(name, *args) if 'input' in name else None)")
        child.sendline("x = input('xyz')")
        child.sendline("abc")
        child.expect("input.*xyz")
        child.expect("input/result.*abc")

def test_input_is_not_monkeypatched(tmpdir):
    with start_repl(colors=False) as child:
        child.sendline("print(input)")
        child.expect("<built-in function input>")

def test_tab_completion_works():
    with start_repl(colors=False, explicit_pyrepl=False) as child:
        child.sendline("import io")
        child.sendline("io.Bloc\t)")
        child.expect("BlockingIOError()")
