"""
Tests for the entry point of pypy-c, app_main.py.
"""
from __future__ import with_statement
import py
import sys, os, re, runpy, subprocess
from rpython.tool.udir import udir
from contextlib import contextmanager
from pypy import pypydir
from pypy.conftest import PYTHON3, LOOK_FOR_PYTHON3
from pypy.interpreter.test.conftest import banner
from lib_pypy._pypy_interact import irc_header

app_main = os.path.join(os.path.realpath(os.path.dirname(__file__)), os.pardir, 'app_main.py')
app_main = os.path.abspath(app_main)

def get_python3():
    if PYTHON3:
        return PYTHON3
    py.test.skip("Test requires %r (not found in PATH) or a PYTHON3 "
                 "environment variable set" % (LOOK_FOR_PYTHON3,))

_counter = 0
def _get_next_path(ext='.py'):
    global _counter
    p = udir.join('demo_test_app_main_%d%s' % (_counter, ext))
    _counter += 1
    return p

def getscript(source):
    p = _get_next_path()
    p.write(str(py.code.Source(source)))
    return str(p)

def getscript_pyc(space, source):
    p = _get_next_path()
    p.write(str(py.code.Source(source)))
    subprocess.check_call([get_python3(), "-c", "import " + p.purebasename],
                          env={'PYTHONPATH': str(p.dirpath())})
    # the .pyc file should have been created above
    pycache = p.dirpath('__pycache__')
    pycs = pycache.listdir(p.purebasename + '*.pyc')
    assert len(pycs) == 1
    return str(pycs[0])

def getscript_in_dir(source):
    pdir = _get_next_path(ext='')
    p = pdir.ensure(dir=1).join('__main__.py')
    p.write(str(py.code.Source(source)))
    # return relative path for testing purposes
    return py.path.local().bestrelpath(pdir)

@py.test.fixture
def demo_script():
    return getscript("""
        print('hello')
        print('Name:', __name__)
        print('File:', __file__)
        print('Cached:', __cached__)
        import sys
        print('Exec:', sys.executable)
        print('Argv:', sys.argv)
        print('goodbye')
        myvalue = 6*7
    """)

@py.test.fixture
def crashing_demo_script():
    return getscript("""
        print('Hello2')
        myvalue2 = 11
        ooups
        myvalue2 = 22
        print('Goodbye2')  # should not be reached
    """)

script_with_future = getscript("""
    from __future__ import division
    from __future__ import print_function
    """)


@contextmanager
def setpythonpath():
    old_pythonpath = os.getenv('PYTHONPATH')
    rootdir = os.path.dirname(pypydir)
    os.putenv('PYTHONPATH', rootdir)
    try:
        yield
    finally:
        if old_pythonpath is None:
            os.unsetenv('PYTHONPATH')
        else:
            os.putenv('PYTHONPATH', old_pythonpath)


class TestParseCommandLine:
    def check_options(self, options, **expected):
        for key, value in expected.items():
            assert options[key] == value
        for key, value in options.items():
            if key not in expected:
                assert not value, (
                    "option %r has unexpectedly the value %r" % (key, value))

    def check(self, argv, env, **expected):
        p = subprocess.Popen([get_python3(), app_main,
                              '--argparse-only'] + list(argv),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=env)

        res = p.wait()
        outcome = p.stdout.readline()
        if outcome == 'SystemExit\n':
            output = p.stdout.read()
            assert expected['output_contains'] in output
        else:
            app_options = eval(p.stdout.readline())
            sys_argv = eval(p.stdout.readline())
            app_options['sys_argv'] = sys_argv
            self.check_options(app_options, **expected)

    def test_all_combinations_I_can_think_of(self):
        self.check([], {}, sys_argv=[''], run_stdin=True)
        self.check(['-'], {}, sys_argv=['-'], run_stdin=True)
        self.check(['-S'], {}, sys_argv=[''], run_stdin=True, no_site=1)
        self.check(['-OO'], {}, sys_argv=[''], run_stdin=True, optimize=2)
        self.check(['-O', '-O'], {}, sys_argv=[''], run_stdin=True, optimize=2)
        self.check(['-SO'], {}, sys_argv=[''], run_stdin=True,
                   no_site=1, optimize=1)
        self.check(['-i'], {}, sys_argv=[''], run_stdin=True,
                   interactive=1, inspect=1)
        self.check(['-?'], {}, output_contains='usage:')
        self.check(['-h'], {}, output_contains='usage:')
        self.check(['-S', '-O', '-h'], {}, output_contains='usage:')
        self.check(['-S', '-hO'], {}, output_contains='usage:')
        self.check(['-S', '-O', '--help'], {}, output_contains='usage:')
        self.check(['-S', '-O', '--info'], {}, output_contains='translation')
        self.check(['-S', '-O', '--version'], {}, output_contains='Python')
        self.check(['-S', '-OV'], {}, output_contains='Python')
        self.check(['--jit', 'off', '-S'], {}, sys_argv=[''],
                   run_stdin=True, no_site=1)
        self.check(['-c', 'pass'], {}, sys_argv=['-c'], run_command='pass')
        self.check(['-cpass'], {}, sys_argv=['-c'], run_command='pass')
        self.check(['-cpass','x'], {}, sys_argv=['-c','x'], run_command='pass')
        self.check(['-Sc', 'pass'], {}, sys_argv=['-c'], run_command='pass',
                   no_site=1)
        self.check(['-Scpass'], {}, sys_argv=['-c'], run_command='pass', no_site=1)
        self.check(['-c', '', ''], {}, sys_argv=['-c', ''], run_command='')
        self.check(['-mfoo', 'bar', 'baz'], {}, sys_argv=['-m', 'bar', 'baz'],
                   run_module='foo')
        self.check(['-m', 'foo', 'bar', 'baz'], {}, sys_argv=['-m', 'bar', 'baz'],
                   run_module='foo')
        self.check(['-Smfoo', 'bar', 'baz'], {}, sys_argv=['-m', 'bar', 'baz'],
                   run_module='foo', no_site=1)
        self.check(['-Sm', 'foo', 'bar', 'baz'], {}, sys_argv=['-m', 'bar', 'baz'],
                   run_module='foo', no_site=1)
        self.check(['-', 'foo', 'bar'], {}, sys_argv=['-', 'foo', 'bar'],
                   run_stdin=True)
        self.check(['foo', 'bar'], {}, sys_argv=['foo', 'bar'])
        self.check(['foo', '-i'], {}, sys_argv=['foo', '-i'])
        self.check(['-i', 'foo'], {}, sys_argv=['foo'], interactive=1, inspect=1)
        self.check(['--', 'foo'], {}, sys_argv=['foo'])
        self.check(['--', '-i', 'foo'], {}, sys_argv=['-i', 'foo'])
        self.check(['--', '-', 'foo'], {}, sys_argv=['-', 'foo'], run_stdin=True)
        self.check(['-Wbog'], {}, sys_argv=[''], warnoptions=['bog'], run_stdin=True)
        self.check(['-W', 'ab', '-SWc'], {}, sys_argv=[''], warnoptions=['ab', 'c'],
                   run_stdin=True, no_site=1)
        self.check(['-X', 'foo'], {}, sys_argv=[''], _xoptions=['foo'],
                   run_stdin=True)
        self.check(['-X', 'foo=bar', '-Xbaz'], {}, sys_argv=[''],
                   _xoptions=['foo=bar', 'baz'], run_stdin=True)

        self.check([], {'PYTHONDEBUG': '1'}, sys_argv=[''], run_stdin=True, debug=1)
        self.check([], {'PYTHONDONTWRITEBYTECODE': '1'}, sys_argv=[''], run_stdin=True, dont_write_bytecode=1)
        self.check([], {'PYTHONNOUSERSITE': '1'}, sys_argv=[''], run_stdin=True, no_user_site=1)
        self.check([], {'PYTHONUNBUFFERED': '1'}, sys_argv=[''], run_stdin=True, unbuffered=1)
        self.check([], {'PYTHONVERBOSE': '1'}, sys_argv=[''], run_stdin=True, verbose=1)
        self.check([], {'PYTHONOPTIMIZE': '1'}, sys_argv=[''], run_stdin=True, optimize=1)
        self.check([], {'PYTHONOPTIMIZE': '0'}, sys_argv=[''], run_stdin=True, optimize=1)
        self.check([], {'PYTHONOPTIMIZE': '10'}, sys_argv=[''], run_stdin=True, optimize=10)
        self.check(['-O'], {'PYTHONOPTIMIZE': '10'}, sys_argv=[''], run_stdin=True, optimize=10)
        self.check(['-OOO'], {'PYTHONOPTIMIZE': 'abc'}, sys_argv=[''], run_stdin=True, optimize=3)

    def test_sysflags(self):
        flags = (
            ("debug", "-d", "1"),
            (["inspect", "interactive"], "-i", "1"),
            ("optimize", "-O", "1"),
            ("optimize", "-OO", "2"),
            ("dont_write_bytecode", "-B", "1"),
            ("no_user_site", "-s", "1"),
            ("no_site", "-S", "1"),
            ("ignore_environment", "-E", "1"),
            ("verbose", "-v", "1"),
            ("bytes_warning", "-b", "1"),
            (["isolated", "no_user_site", "ignore_environment"], "-I", "1"),
        )
        for flag, opt, value in flags:
            if isinstance(flag, list):   # this is for inspect&interactive
                expected = {}
                for flag1 in flag:
                    expected[flag1] = int(value)
            else:
                expected = {flag: int(value)}
            self.check([opt, '-c', 'pass'], {}, sys_argv=['-c'],
                       run_command='pass', **expected)

    def test_sysflags_envvar(self, monkeypatch):
        expected = {"no_user_site": True}
        self.check(['-c', 'pass'], {'PYTHONNOUSERSITE': '1'}, sys_argv=['-c'],
                   run_command='pass', **expected)

class TestInteraction:
    """
    These tests require pexpect (UNIX-only).
    http://pexpect.sourceforge.net/
    """
    def _spawn(self, *args, **kwds):
        try:
            import pexpect
        except ImportError as e:
            py.test.skip(str(e))
        else:
            # Version is of the style "0.999" or "2.1".  Older versions of
            # pexpect try to get the fileno of stdin, which generally won't
            # work with py.test (due to sys.stdin being a DontReadFromInput
            # instance).
            version = map(int, pexpect.__version__.split('.'))

            # I only tested 0.999 and 2.1.  The former does not work, the
            # latter does.  Feel free to refine this measurement.
            # -exarkun, 17/12/2007
            if version < [2, 1]:
                py.test.skip(
                    "pexpect version too old, requires 2.1 or newer: %r" % (
                        pexpect.__version__,))

        kwds.setdefault('timeout', 10)
        print 'SPAWN:', ' '.join([args[0]] + args[1]), kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv, env=None):
        # make sure that when we do 'import pypy' we get the correct package
        with setpythonpath():
            return self._spawn(get_python3(), [app_main] + argv, env=env)

    def test_interactive(self):
        child = self.spawn([])
        child.expect('Python ')   # banner
        child.expect('>>> ')      # prompt
        child.sendline('[6*7]')
        child.expect(re.escape('[42]'))
        child.sendline('def f(x):')
        child.expect(re.escape('... '))
        child.sendline('    return x + 100')
        child.expect(re.escape('... '))
        child.sendline('')
        child.expect('>>> ')
        child.sendline('f(98)')
        child.expect('198')
        child.expect('>>> ')
        child.sendline('__name__')
        child.expect("'__main__'")
        child.expect('>>> ')
        child.sendline('import sys')
        child.expect('>>> ')
        child.sendline("'' in sys.path")
        child.expect("True")

    def test_yes_irc_topic(self, monkeypatch):
        monkeypatch.setenv('PYPY_IRC_TOPIC', '1')
        child = self.spawn([])
        child.expect(irc_header)   # banner

    def test_maybe_irc_topic(self):
        import sys
        pypy_version_info = getattr(sys, 'pypy_version_info', sys.version_info)
        irc_topic = pypy_version_info[3] != 'final'
        child = self.spawn([])
        child.expect('>>>')   # banner
        if irc_topic:
            assert irc_header in child.before
        else:
            assert irc_header not in child.before

    def test_help(self):
        # test that -h prints the usage, including the name of the executable
        # which should be /full/path/to/app_main.py in this case
        child = self.spawn(['-h'])
        child.expect(r'usage: .*app_main.py \[option\]')
        child.expect('PyPy options and arguments:')

    def test_run_script(self, demo_script):
        child = self.spawn([demo_script])
        idx = child.expect(['hello', 'Python ', '>>> '])
        assert idx == 0   # no banner or prompt
        child.expect(re.escape("Name: __main__"))
        child.expect(re.escape('File: ' + demo_script))
        child.expect(re.escape('Exec: ' + app_main))
        child.expect(re.escape('Argv: ' + repr([demo_script])))
        child.expect('goodbye')

    def test_run_script_with_args(self, demo_script):
        argv = [demo_script, 'hello', 'world']
        child = self.spawn(argv)
        child.expect(re.escape('Argv: ' + repr(argv)))
        child.expect('goodbye')

    def test_no_such_script(self):
        import errno
        msg = os.strerror(errno.ENOENT)   # 'No such file or directory'
        child = self.spawn(['xxx-no-such-file-xxx'])
        child.expect(re.escape(msg))

    def test_option_i(self, demo_script):
        argv = [demo_script, 'foo', 'bar']
        child = self.spawn(['-i'] + argv)
        idx = child.expect(['hello', re.escape(banner)])
        assert idx == 0      # no banner
        child.expect(re.escape('File: ' + demo_script))
        child.expect(re.escape('Argv: ' + repr(argv)))
        child.expect('goodbye')
        idx = child.expect(['>>> ', re.escape(banner)])
        assert idx == 0      # prompt, but still no banner
        child.sendline('myvalue * 102')
        child.expect('4284')
        child.sendline('__name__')
        child.expect('__main__')

    def test_option_i_crashing(self, crashing_demo_script):
        argv = [crashing_demo_script, 'foo', 'bar']
        child = self.spawn(['-i'] + argv)
        idx = child.expect(['Hello2', re.escape(banner)])
        assert idx == 0      # no banner
        child.expect('NameError')
        child.sendline('myvalue2 * 1001')
        child.expect('11011')
        child.sendline('import sys; sys.argv')
        child.expect(re.escape(repr(argv)))
        child.sendline('sys.last_type.__name__')
        child.expect(re.escape(repr('NameError')))

    def test_options_i_c(self):
        child = self.spawn(['-i', '-c', 'x=555'])
        idx = child.expect(['>>> ', re.escape(banner)])
        assert idx == 0      # prompt, but no banner
        child.sendline('x')
        child.expect('555')
        child.sendline('__name__')
        child.expect('__main__')
        child.sendline('import sys; sys.argv')
        child.expect(re.escape("['-c']"))

    def test_options_i_c_crashing(self, monkeypatch):
        monkeypatch.setenv('PYTHONPATH', None)
        child = self.spawn(['-i', '-c', 'x=666;foobar'])
        child.expect('NameError')
        idx = child.expect(['>>> ', re.escape(banner)])
        assert idx == 0      # prompt, but no banner
        child.sendline('x')
        child.expect('666')
        child.sendline('__name__')
        child.expect('__main__')
        child.sendline('import sys; sys.argv')
        child.expect(re.escape("['-c']"))
        child.sendline('sys.last_type.__name__')
        child.expect(re.escape(repr('NameError')))

    def test_options_i_c_sysexit(self):
        child = self.spawn(['-i', '-c', 'import sys; sys.exit(1)'])
        child.expect('SystemExit: 1')
        child.expect('>>>')

    def test_atexit(self):
        skip("Python3 atexit is a builtin module")
        child = self.spawn([])
        child.expect('>>> ')
        child.sendline('def f(): print("foobye")')
        child.sendline('')
        child.sendline('import atexit; atexit.register(f)')
        child.sendline('6*7')
        child.expect('42')
        # pexpect's sendeof() is confused by py.test capturing, though
        # I think that it is a bug of sendeof()
        old = sys.stdin
        try:
            sys.stdin = child
            child.sendeof()
        finally:
            sys.stdin = old
        child.expect('foobye')

    def test_pythonstartup(self, monkeypatch, demo_script, crashing_demo_script):
        monkeypatch.setenv('PYTHONPATH', None)
        monkeypatch.setenv('PYTHONSTARTUP', crashing_demo_script)
        child = self.spawn([])
        child.expect(re.escape(banner))
        child.expect('Traceback')
        child.expect('NameError')
        child.expect('>>> ')
        child.sendline('[myvalue2]')
        child.expect(re.escape('[11]'))
        child.expect('>>> ')

        child = self.spawn(['-i', demo_script])
        for line in ['hello', 'goodbye', '>>> ']:
            idx = child.expect([line, 'Hello2'])
            assert idx == 0    # no PYTHONSTARTUP run here
        child.sendline('myvalue2')
        child.expect('Traceback')
        child.expect('NameError')

    def test_pythonstartup_file1(self, monkeypatch, demo_script):
        monkeypatch.setenv('PYTHONPATH', None)
        monkeypatch.setenv('PYTHONSTARTUP', demo_script)
        child = self.spawn([])
        child.expect('File: [^\n]+\.py')
        child.expect('goodbye')
        child.expect('>>> ')
        child.sendline('[myvalue]')
        child.expect(re.escape('[42]'))
        child.expect('>>> ')
        child.sendline('__file__')
        child.expect('Traceback')
        child.expect('NameError')

    def test_pythonstartup_file2(self, monkeypatch, crashing_demo_script):
        monkeypatch.setenv('PYTHONPATH', None)
        monkeypatch.setenv('PYTHONSTARTUP', crashing_demo_script)
        child = self.spawn([])
        child.expect('Traceback')
        child.expect('>>> ')
        child.sendline('__file__')
        child.expect('Traceback')
        child.expect('NameError')

    def test_ignore_python_startup(self, crashing_demo_script):
        old = os.environ.get('PYTHONSTARTUP', '')
        try:
            os.environ['PYTHONSTARTUP'] = crashing_demo_script
            child = self.spawn(['-E'])
            child.expect(re.escape(banner))
            index = child.expect(['Traceback', '>>> '])
            assert index == 1      # no traceback
        finally:
            os.environ['PYTHONSTARTUP'] = old

    def test_future_in_executed_script(self):
        child = self.spawn(['-i', script_with_future])
        child.expect('>>> ')
        child.sendline('x=1; print(x/2, 3/4)')
        child.expect('0.5 0.75')

    def test_future_in_python_startup(self, monkeypatch):
        monkeypatch.setenv('PYTHONSTARTUP', script_with_future)
        child = self.spawn([])
        child.expect('>>> ')
        child.sendline('x=1; print(x/2, 3/4)')
        child.expect('0.5 0.75')

    def test_future_in_cmd(self):
        child = self.spawn(['-i', '-c', 'from __future__ import division'])
        child.expect('>>> ')
        child.sendline('x=1; x/2; 3/4')
        child.expect('0.5')
        child.expect('0.75')

    def test_cmd_co_name(self):
        child = self.spawn(['-c',
                    'import sys; print sys._getframe(0).f_code.co_name'])
        child.expect('<module>')

    def test_ignore_python_inspect(self):
        os.environ['PYTHONINSPECT_'] = '1'
        try:
            child = self.spawn(['-E', '-c', 'pass'])
            from pexpect import EOF
            index = child.expect(['>>> ', EOF])
            assert index == 1      # no prompt
        finally:
            del os.environ['PYTHONINSPECT_']

    def test_python_path_keeps_duplicates(self):
        old = os.environ.get('PYTHONPATH', '')
        try:
            child = self.spawn(['-c', 'import sys; print(sys.path)'],
                               env={'PYTHONPATH': 'foobarbaz:foobarbaz'})
            child.expect(r"\['', 'foobarbaz', 'foobarbaz', ")
        finally:
            os.environ['PYTHONPATH'] = old

    def test_ignore_python_path(self):
        old = os.environ.get('PYTHONPATH', '')
        try:
            os.environ['PYTHONPATH'] = 'foobarbaz'
            child = self.spawn(['-E', '-c', 'import sys; print(sys.path)'])
            from pexpect import EOF
            index = child.expect(['foobarbaz', EOF])
            assert index == 1      # no foobarbaz
        finally:
            os.environ['PYTHONPATH'] = old

    def test_buffered(self):
        line = 'import sys;print(type(sys.stdout.buffer).__name__)'
        child = self.spawn(['-c', line])
        child.expect('BufferedWriter')

    def test_unbuffered(self):
        # In Python3, -u affects the "binary layer" of sys.stdout.
        line = 'import os,sys;sys.stdout.buffer.write(str(789).encode());os.read(0,1)'
        child = self.spawn(['-u', '-c', line])
        child.expect('789')    # expect to see it before the timeout hits
        child.sendline('X')

    def test_file_modes(self):
        child = self.spawn(['-c', 'import sys; print(sys.stdout.mode)'])
        child.expect('w')
        child = self.spawn(['-c', 'import sys; print(sys.stderr.mode)'])
        child.expect('w')
        child = self.spawn(['-c', 'import sys; print(sys.stdin.mode)'])
        child.expect('r')

    def test_options_i_m(self, monkeypatch):
        if sys.platform == "win32":
            skip("close_fds is not supported on Windows platforms")
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'mymodule.py')
        p = os.path.abspath(p)
        monkeypatch.chdir(os.path.dirname(app_main))
        child = self.spawn(['-i',
                            '-m', 'test.mymodule',
                            'extra'])
        child.expect('mymodule running')
        child.expect('Name: __main__')
        child.expect(re.escape('File: ' + p))
        child.expect(re.escape('Argv: ' + repr([p, 'extra'])))
        child.expect('>>> ')
        child.sendline('somevalue')
        child.expect(re.escape(repr("foobar")))
        child.expect('>>> ')
        child.sendline('import sys')
        child.sendline('"test" in sys.modules')
        child.expect('True')
        child.sendline('"test.mymodule" in sys.modules')
        child.expect('False')
        child.sendline('sys.path[0]')
        child.expect("''")

    def test_option_i_noexit(self):
        child = self.spawn(['-i', '-c', 'import sys; sys.exit(1)'])
        child.expect('Traceback')
        child.expect('SystemExit: 1')

    def test_options_u_i(self):
        if sys.platform == "win32":
            skip("close_fds is not supported on Windows platforms")
        import subprocess, select, os
        pipe = subprocess.Popen([get_python3(), app_main, "-u", "-i"],
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=0, close_fds=True)
        iwtd, owtd, ewtd = select.select([pipe.stdout], [], [], 5)
        assert iwtd    # else we timed out
        data = os.read(pipe.stdout.fileno(), 1024)
        assert data.startswith('Python')

    def test_paste_several_lines_doesnt_mess_prompt(self):
        py.test.skip("this can only work if readline is enabled")
        child = self.spawn([])
        child.expect('>>> ')
        child.sendline('if 1:\n    print 42\n')
        child.expect('...     print 42')
        child.expect('... ')
        child.expect('42')
        child.expect('>>> ')

    def test_pythoninspect(self):
        os.environ['PYTHONINSPECT_'] = '1'
        try:
            path = getscript("""
                print(6*7)
                """)
            child = self.spawn([path])
            child.expect('42')
            child.expect('>>> ')
        finally:
            del os.environ['PYTHONINSPECT_']

    def test_set_pythoninspect(self):
        path = getscript("""
            import os
            os.environ['PYTHONINSPECT'] = '1'
            print(6*7)
            """)
        child = self.spawn([path])
        child.expect('42')
        child.expect('>>> ')

    def test_clear_pythoninspect(self):
        os.environ['PYTHONINSPECT_'] = '1'
        try:
            path = getscript("""
                import os
                del os.environ['PYTHONINSPECT']
                """)
            child = self.spawn([path])
            child.expect('>>> ')
        finally:
            del os.environ['PYTHONINSPECT_']

    def test_stdout_flushes_before_stdin_blocks(self):
        skip("Python3 does not implement this behavior")
        # This doesn't really test app_main.py, but a behavior that
        # can only be checked on top of py.py with pexpect.
        path = getscript("""
            import sys
            sys.stdout.write('Are you suggesting coconuts migrate? ')
            line = sys.stdin.readline()
            assert line.rstrip() == 'Not at all. They could be carried.'
            print('A five ounce bird could not carry a one pound coconut.')
            """)
        py_py = os.path.join(pypydir, 'bin', 'pyinteractive.py')
        child = self._spawn(sys.executable, [py_py, '-S', path])
        child.expect('Are you suggesting coconuts migrate?', timeout=120)
        child.sendline('Not at all. They could be carried.')
        child.expect('A five ounce bird could not carry a one pound coconut.')

    def test_no_space_before_argument(self, monkeypatch):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        child = self.spawn(['-cprint("hel" + "lo")'])
        child.expect('hello')

        monkeypatch.chdir(os.path.dirname(app_main))
        child = self.spawn(['-mtest.mymodule'])
        child.expect('mymodule running')

    def test_ps1_only_if_interactive(self):
        argv = ['-c', 'import sys; print(hasattr(sys, "ps1"))']
        child = self.spawn(argv)
        child.expect('False')


class TestNonInteractive:
    def run_with_status_code(self, cmdline, senddata='', expect_prompt=False,
            expect_banner=False, python_flags='', env=None):
        if os.name == 'nt':
            try:
                import __pypy__
            except:
                py.test.skip('app_main cannot run on non-pypy for windows')
        cmdline = '%s %s "%s" %s' % (get_python3(), python_flags,
                                     app_main, cmdline)
        print 'POPEN:', cmdline
        process = subprocess.Popen(
            cmdline,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=True, env=env,
            universal_newlines=True
        )
        child_in, child_out_err = process.stdin, process.stdout
        child_in.write(senddata)
        child_in.close()
        data = child_out_err.read()
        child_out_err.close()
        process.wait()
        assert (banner in data) == expect_banner   # no banner unless expected
        assert ('>>> ' in data) == expect_prompt   # no prompt unless expected
        return data, process.returncode

    def run(self, *args, **kwargs):
        with setpythonpath():
            data, status = self.run_with_status_code(*args, **kwargs)
        return data

    def test_script_on_stdin(self, demo_script):
        for extraargs, expected_argv in [
            ('',              ['']),
            ('-',             ['-']),
            ('- hello world', ['-', 'hello', 'world']),
            ]:
            data = self.run('%s < "%s"' % (extraargs, demo_script))
            assert "hello" in data
            assert "Name: __main__" in data
            assert "File: <stdin>" in data
            assert ("Exec: " + app_main) in data
            assert ("Argv: " + repr(expected_argv)) in data
            assert "goodbye" in data

    def test_run_crashing_script(self, crashing_demo_script):
        data = self.run('"%s"' % (crashing_demo_script,))
        assert 'Hello2' in data
        assert 'NameError' in data
        assert 'Goodbye2' not in data

    def test_crashing_script_on_stdin(self, crashing_demo_script):
        data = self.run(' < "%s"' % (crashing_demo_script,))
        assert 'Hello2' in data
        assert 'NameError' in data
        assert 'Goodbye2' not in data

    def test_option_W(self):
        data = self.run('-W d -c "print(42)"')
        assert '42' in data
        data = self.run('-Wd -c "print(42)"')
        assert '42' in data

    def test_option_W_crashing(self):
        data = self.run('-W')
        assert "Argument expected for the '-W' option" in data

    def test_option_W_arg_ignored(self):
        data = self.run('-Wc')
        assert "Invalid -W option ignored: invalid action: 'c'" in data

    def test_option_W_arg_ignored2(self):
        data = self.run('-W-W')
        assert "Invalid -W option ignored: invalid action:" in data

    def test_option_c(self):
        data = self.run('-c "print(6**5)"')
        assert '7776' in data

    def test_option_c_unencodable(self):
        data, status = self.run_with_status_code(b"""-c 'print(b"\xff")'""",
                                                 env={'LC_ALL': 'C'})
        assert status in (0, 1)
        pattern = ("Unable to decode the command from the command line:"
                   if status else
                   "'\\xff' ")
        assert data.startswith(pattern)

    def test_no_pythonstartup(self, monkeypatch, demo_script, crashing_demo_script):
        monkeypatch.setenv('PYTHONSTARTUP', crashing_demo_script)
        data = self.run('"%s"' % (demo_script,))
        assert 'Hello2' not in data
        data = self.run('-c pass')
        assert 'Hello2' not in data

    def test_pythonwarnings(self, monkeypatch):
        # PYTHONWARNINGS_ is special cased by app_main: we cannot directly set
        # PYTHONWARNINGS because else the warnings raised from within pypy are
        # turned in errors.
        monkeypatch.setenv('PYTHONWARNINGS_', "once,error")
        data = self.run('-W ignore -W default '
                        '-c "import sys; print(sys.warnoptions)"')
        assert "['ignore', 'default', 'once', 'error']" in data

    def test_option_m(self, monkeypatch):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'mymodule.py')
        p = os.path.abspath(p)
        monkeypatch.chdir(os.path.dirname(app_main))
        data = self.run('-m test.mymodule extra')
        assert 'mymodule running' in data
        assert 'Name: __main__' in data
        # ignoring case for windows. abspath behaves different from autopath
        # concerning drive letters right now.
        assert ('File: ' + p) in data
        assert ('Argv: ' + repr([p, 'extra'])) in data

    def test_option_m_package(self, monkeypatch):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                         'mypackage', '__main__.py')
        p = os.path.abspath(p)
        monkeypatch.chdir(os.path.dirname(app_main))
        data = self.run('-m test.mypackage extra')
        assert "__init__ argv: ['-m', 'extra']" in data
        assert "__main__ argv: [%r, 'extra']" % p in data

    def test_xoptions(self):
        data = self.run('-Xfoo -Xbar=baz -Xquux=cdrom.com=FreeBSD -Xx=X,d=e '
                        '-c "import sys;print(sorted(sys._xoptions.items()))"')
        expected = ("[('bar', 'baz'), ('foo', True), "
                    "('quux', 'cdrom.com=FreeBSD'), ('x', 'X,d=e')]")
        assert expected in data

    def test_pythoninspect_doesnt_override_isatty(self):
        os.environ['PYTHONINSPECT_'] = '1'
        try:
            data = self.run('', senddata='6*7\nprint(2+3)\n')
            assert data == '5\n'
        finally:
            del os.environ['PYTHONINSPECT_']

    def test_i_flag_overrides_isatty(self):
        data = self.run('-i', senddata='6*7\nraise SystemExit\n',
                              expect_prompt=True, expect_banner=True)
        assert '42\n' in data
        # if a file name is passed, the banner is never printed but
        # we get a prompt anyway
        cmdline = '-i %s' % getscript("""
            print('hello world')
            """)
        data = self.run(cmdline, senddata='6*7\nraise SystemExit\n',
                                 expect_prompt=True, expect_banner=False)
        assert 'hello world\n' in data
        assert '42\n' in data

    def test_q_flag(self):
        data = self.run('-iq', senddata='6*7\nraise SystemExit\n',
                        expect_prompt=True, expect_banner=False)
        assert '42\n' in data

    def test_putenv_fires_interactive_within_process(self):
        try:
            import __pypy__
        except ImportError:
            py.test.skip("This can be only tested on PyPy with real_getenv")

        # should be noninteractive when piped in
        data = 'import os\nos.putenv("PYTHONINSPECT", "1")\n'
        self.run('', senddata=data, expect_prompt=False)

        # should go interactive with -c
        data = data.replace('\n', ';')
        self.run("-c '%s'" % data, expect_prompt=True)

    def test_option_S_copyright(self):
        data = self.run('-S -i', expect_prompt=True, expect_banner=True)
        assert 'copyright' not in data

    def test_non_interactive_stdout_unbuffered(self, monkeypatch):
        monkeypatch.setenv('PYTHONUNBUFFERED', '1')
        if os.name == 'nt':
            try:
                import __pypy__
            except:
                py.test.skip('app_main cannot run on non-pypy for windows')
        path = getscript(r"""
            import sys, time
            sys.stdout.write('\x00(STDOUT)\n\x00')
            time.sleep(1)
            sys.stderr.write('\x00[STDERR]\n\x00')
            time.sleep(1)
            # stdout flushed automatically here
            """)
        cmdline = '%s -E "%s" %s' % (get_python3(), app_main, path)
        print 'POPEN:', cmdline
        child_in, child_out_err = os.popen4(cmdline)
        data = child_out_err.read(11)
        assert data == '\x00(STDOUT)\n\x00'    # from stderr
        data = child_out_err.read(11)
        assert data == '\x00[STDERR]\n\x00'    # from stdout
        child_out_err.close()
        child_in.close()

    # these tests are ported from the stdlib test suite

    def _test_no_stdio(self, streams):
        code = """if 1:
            import os, sys
            for i, s in enumerate({streams}):
                if getattr(sys, s) is not None:
                    os._exit(i + 1)
            os._exit(42)""".format(streams=streams)
        def preexec():
            if 'stdin' in streams:
                os.close(0)
            if 'stdout' in streams:
                os.close(1)
            if 'stderr' in streams:
                os.close(2)
        p = subprocess.Popen(
            [get_python3(), app_main, "-E", "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=preexec)
        out, err = p.communicate()
        err = re.sub(br"\[\d+ refs\]\r?\n?$", b"", err).strip()
        assert err == b''
        assert p.returncode == 42

    @py.test.mark.skipif("os.name != 'posix'")
    def test_no_stdin(self):
        self._test_no_stdio(['stdin'])

    @py.test.mark.skipif("os.name != 'posix'")
    def test_no_stdout(self):
        self._test_no_stdio(['stdout'])

    @py.test.mark.skipif("os.name != 'posix'")
    def test_no_stderr(self):
        self._test_no_stdio(['stderr'])

    @py.test.mark.skipif("os.name != 'posix'")
    def test_no_std_streams(self):
        self._test_no_stdio(['stdin', 'stdout', 'stderr'])

    def test_proper_sys_path(self, tmpdir):
        data = self.run('-c "import _ctypes"', python_flags='-S')
        if data.startswith('Traceback'):
            py.test.skip("'python -S' cannot import extension modules: "
                         "see probably http://bugs.python.org/issue586680")

        @contextmanager
        def chdir_and_unset_pythonpath(new_cwd):
            old_cwd = new_cwd.chdir()
            old_pythonpath = os.getenv('PYTHONPATH')
            os.unsetenv('PYTHONPATH')
            try:
                yield
            finally:
                old_cwd.chdir()
                # Can't call putenv with a None argument.
                if old_pythonpath is not None:
                    os.putenv('PYTHONPATH', old_pythonpath)

        tmpdir.join('site.py').write('print("SHOULD NOT RUN")')
        runme_py = tmpdir.join('runme.py')
        runme_py.write('print("some text")')

        cmdline = str(runme_py)

        with chdir_and_unset_pythonpath(tmpdir):
            data = self.run(cmdline, python_flags='-S')

        assert data in ("'import site' failed\nsome text\n")

        runme2_py = tmpdir.mkdir('otherpath').join('runme2.py')
        runme2_py.write('print("some new text")\n'
                        'import sys\n'
                        'print(sys.path)\n')

        cmdline2 = str(runme2_py)

        with chdir_and_unset_pythonpath(tmpdir):
            data = self.run(cmdline2, python_flags='-S')
        assert data.startswith("some new text\n")
        assert repr(str(tmpdir.join('otherpath'))) in data
        assert "''" not in data

        data = self.run('-c "import sys; print(sys.path)"')
        assert data.startswith("[''")

    def test_pyc_commandline_argument(self):
        p = getscript_pyc(self.space, "print(6*7)\n")
        assert os.path.isfile(p) and p.endswith('.pyc')
        data = self.run(p)
        assert data == '42\n'

    def test_main_in_dir_commandline_argument(self):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = getscript_in_dir('import sys; print(sys.argv[0])\n')
        data = self.run(p)
        assert data == p + '\n'
        data = self.run(p + os.sep)
        assert data == p + os.sep + '\n'

    def test_getfilesystemencoding(self):
        py.test.skip("encoding is only set if stdout.isatty(), test is flawed")
        if sys.version_info < (2, 7):
            skip("test requires Python >= 2.7")
        p = getscript_in_dir("""
        import sys
        sys.stdout.write(u'15\u20ac')
        sys.stdout.flush()
        """)
        env = os.environ.copy()
        env["LC_CTYPE"] = 'en_US.UTF-8'
        data = self.run(p, env=env)
        assert data == '15\xe2\x82\xac'

    def test_pythonioencoding(self):
        if sys.version_info < (2, 7):
            skip("test requires Python >= 2.7")
        for encoding, expected in [
            ("iso-8859-15", "15\xa4"),
            ("utf-8", '15\xe2\x82\xac'),
            ("utf-16-le", '1\x005\x00\xac\x20'),
            ("iso-8859-1:ignore", "15"),
            ("iso-8859-1:replace", "15?"),
            ("iso-8859-1:backslashreplace", "15\\u20ac"),
        ]:
            p = getscript_in_dir("""
            import sys
            sys.stdout.write('15\u20ac')
            sys.stdout.flush()
            """)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = encoding
            data = self.run(p, env=env)
            assert data == expected

    def test_pythonioencoding2(self):
        for encoding, expected in [
            ("ascii:", "strict"),
            (":surrogateescape", "surrogateescape"),
        ]:
            p = getscript_in_dir("import sys; print(sys.stdout.errors, end='')")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = encoding
            data = self.run(p, env=env)
            assert data == expected

    def test_pythonioencoding_c_locale(self):
        p = getscript_in_dir("import sys; print(sys.stdout.errors, end='')")
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        data = self.run(p, env=env)
        assert data == "surrogateescape"

    def test_sys_exit_pythonioencoding(self):
        if sys.version_info < (2, 7):
            skip("test required Python >= 2.7")
        p = getscript_in_dir("""
        import sys
        sys.exit('15\u20ac')
        """)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        data, status = self.run_with_status_code(p, env=env)
        assert status == 1
        assert data.startswith("15\xe2\x82\xac")

    def test_stderr_backslashreplace(self):
        if sys.version_info < (2, 7):
            skip("test required Python >= 2.7")
        p = getscript_in_dir("""
        import sys
        sys.exit('15\u20ac {}'.format((sys.stdout.errors, sys.stderr.errors)))
        """)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = 'ascii'
        data, status = self.run_with_status_code(p, env=env)
        assert status == 1
        assert data.startswith("15\\u20ac ('strict', 'backslashreplace')")


class TestAppMain:
    def test_print_info(self):
        from pypy.interpreter import app_main
        import sys, cStringIO
        prev_so = sys.stdout
        prev_ti = getattr(sys, 'pypy_translation_info', 'missing')
        sys.pypy_translation_info = {
            'translation.foo': True,
            'translation.bar': 42,
            'translation.egg.something': None,
            'objspace.x': 'hello',
        }
        try:
            sys.stdout = f = cStringIO.StringIO()
            py.test.raises(SystemExit, app_main.print_info)
        finally:
            sys.stdout = prev_so
            if prev_ti == 'missing':
                del sys.pypy_translation_info
            else:
                sys.pypy_translation_info = prev_ti
        assert f.getvalue() == ("[objspace]\n"
                                "    x = 'hello'\n"
                                "[translation]\n"
                                "    bar = 42\n"
                                "    [egg]\n"
                                "        something = None\n"
                                "    foo = True\n")


class AppTestAppMain:
    def setup_class(self):
        # ----------------------------------------
        # setup code for test_setup_bootstrap_path
        # ----------------------------------------
        from pypy.module.sys.version import CPYTHON_VERSION, PYPY_VERSION
        cpy_ver = '%d' % CPYTHON_VERSION[0]
        from lib_pypy._pypy_interact import irc_header

        goal_dir = os.path.dirname(app_main)
        # build a directory hierarchy like which contains both bin/pypy-c and
        # lib/pypy1.2/*
        prefix = udir.join('pathtest').ensure(dir=1)
        fake_exe = 'bin/pypy-c'
        if sys.platform == 'win32':
            fake_exe = 'pypy-c.exe'
        fake_exe = prefix.join(fake_exe).ensure(file=1)
        expected_path = [str(prefix.join(subdir).ensure(dir=1))
                         for subdir in ('lib_pypy',
                                        'lib-python/%s' % cpy_ver)]
        # an empty directory from where we can't find the stdlib
        tmp_dir = str(udir.join('tmp').ensure(dir=1))

        self.w_goal_dir = self.space.wrap(goal_dir)
        self.w_fake_exe = self.space.wrap(str(fake_exe))
        self.w_expected_path = self.space.wrap(expected_path)
        self.w_trunkdir = self.space.wrap(os.path.dirname(pypydir))
        self.w_is_release = self.space.wrap(PYPY_VERSION[3] == "final")

        self.w_tmp_dir = self.space.wrap(tmp_dir)

        foo_py = prefix.join('foo.py')
        foo_py.write("pass")
        self.w_foo_py = self.space.wrap(str(foo_py))

    def test_setup_bootstrap_path(self):
        # Check how sys.path is handled depending on if we can find a copy of
        # the stdlib in setup_bootstrap_path.
        import sys, os
        old_sys_path = sys.path[:]
        old_cwd = os.getcwd()

        # make sure cwd does not contain a stdlib
        if self.tmp_dir.startswith(self.trunkdir):
            skip('TMPDIR is inside the PyPy source')
        sys.path.append(self.goal_dir)
        tmp_pypy_c = os.path.join(self.tmp_dir, 'pypy-c')
        try:
            os.chdir(self.tmp_dir)

            # If we are running PyPy with a libpypy-c, the following
            # lines find the stdlib anyway.  Otherwise, it is not found.
            expected_found = (
                getattr(sys, 'pypy_translation_info', {})
                .get('translation.shared'))

            import app_main
            app_main.setup_bootstrap_path(tmp_pypy_c)
            assert sys.executable == ''
            if not expected_found:
                assert sys.path == old_sys_path + [self.goal_dir]

            app_main.setup_bootstrap_path(self.fake_exe)
            if not sys.platform == 'win32':
                # an existing file is always 'executable' on windows
                assert sys.executable == ''      # not executable!
                if not expected_found:
                    assert sys.path == old_sys_path + [self.goal_dir]

            os.chmod(self.fake_exe, 0o755)
            app_main.setup_bootstrap_path(self.fake_exe)
            assert sys.executable == self.fake_exe
            assert self.goal_dir not in sys.path

            newpath = sys.path[:]
            if newpath[0].endswith('__extensions__'):
                newpath = newpath[1:]
            # we get at least 'expected_path', and maybe more (e.g.plat-linux2)
            if not expected_found:
                assert newpath[:len(self.expected_path)] == self.expected_path
        finally:
            sys.path[:] = old_sys_path
            os.chdir(old_cwd)

    def test_trunk_can_be_prefix(self):
        import sys
        import os
        old_sys_path = sys.path[:]
        sys.path.append(self.goal_dir)
        try:
            import app_main
            pypy_c = os.path.join(self.trunkdir, 'pypy', 'goal', 'pypy-c')
            app_main.setup_bootstrap_path(pypy_c)
            newpath = sys.path[:]
            # we get at least lib_pypy
            # lib-python/X.Y.Z, and maybe more (e.g. plat-linux2)
            assert len(newpath) >= 2
            for p in newpath:
                assert p.startswith(self.trunkdir)
        finally:
            sys.path[:] = old_sys_path

    def test_entry_point(self):
        import sys
        import os
        old_sys_path = sys.path[:]
        sys.path.append(self.goal_dir)
        try:
            import app_main
            pypy_c = os.path.join(self.trunkdir, 'pypy', 'goal', 'pypy-c')
            app_main.entry_point(pypy_c, [self.foo_py])
            # assert it did not crash
        finally:
            sys.path[:] = old_sys_path
