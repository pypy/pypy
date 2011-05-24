"""
Tests for the entry point of pypy-c, app_main.py.
"""
from __future__ import with_statement
import py
import sys, os, re, runpy, subprocess
import autopath
from pypy.tool.udir import udir
from contextlib import contextmanager

banner = sys.version.splitlines()[0]

app_main = os.path.join(autopath.this_dir, os.pardir, 'app_main.py')
app_main = os.path.abspath(app_main)

_counter = 0
def _get_next_path(ext='.py'):
    global _counter
    p = udir.join('demo_test_app_main_%d%s' % (_counter, ext))
    _counter += 1
    return p

def getscript(source):
    p = _get_next_path()
    p.write(str(py.code.Source(source)))
    # return relative path for testing purposes 
    return py.path.local().bestrelpath(p) 

def getscript_pyc(space, source):
    p = _get_next_path()
    p.write(str(py.code.Source(source)))
    w_dir = space.wrap(str(p.dirpath()))
    w_modname = space.wrap(p.purebasename)
    space.appexec([w_dir, w_modname], """(dir, modname):
        import sys
        d = sys.modules.copy()
        sys.path.insert(0, dir)
        __import__(modname)
        sys.path.pop(0)
        for key in sys.modules.keys():
            if key not in d:
                del sys.modules[key]
    """)
    p = str(p) + 'c'
    assert os.path.isfile(p)   # the .pyc file should have been created above
    return p

def getscript_in_dir(source):
    pdir = _get_next_path(ext='')
    p = pdir.ensure(dir=1).join('__main__.py')
    p.write(str(py.code.Source(source)))
    # return relative path for testing purposes 
    return py.path.local().bestrelpath(pdir)

demo_script = getscript("""
    print 'hello'
    print 'Name:', __name__
    print 'File:', __file__
    import sys
    print 'Exec:', sys.executable
    print 'Argv:', sys.argv
    print 'goodbye'
    myvalue = 6*7
    """)

crashing_demo_script = getscript("""
    print 'Hello2'
    myvalue2 = 11
    ooups
    myvalue2 = 22
    print 'Goodbye2'   # should not be reached
    """)


class TestParseCommandLine:

    def check_options(self, options, sys_argv, **expected):
        assert sys.argv == sys_argv
        for key, value in expected.items():
            assert options[key] == value
        for key, value in options.items():
            if key not in expected:
                assert not value, (
                    "option %r has unexpectedly the value %r" % (key, value))

    def check(self, argv, **expected):
        import StringIO
        from pypy.translator.goal import app_main
        saved_sys_argv = sys.argv[:]
        saved_sys_stdout = sys.stdout
        saved_sys_stderr = sys.stdout
        app_main.os = os
        try:
            sys.stdout = sys.stderr = StringIO.StringIO()
            try:
                options = app_main.parse_command_line(argv)
            except SystemExit:
                output = expected['output_contains']
                assert output in sys.stdout.getvalue()
            else:
                self.check_options(options, **expected)
        finally:
            sys.argv[:] = saved_sys_argv
            sys.stdout = saved_sys_stdout
            sys.stderr = saved_sys_stderr

    def test_all_combinations_I_can_think_of(self):
        self.check([], sys_argv=[''], run_stdin=True)
        self.check(['-'], sys_argv=['-'], run_stdin=True)
        self.check(['-S'], sys_argv=[''], run_stdin=True, no_site=1)
        self.check(['-OO'], sys_argv=[''], run_stdin=True, optimize=2)
        self.check(['-O', '-O'], sys_argv=[''], run_stdin=True, optimize=2)
        self.check(['-Qnew'], sys_argv=[''], run_stdin=True, division_new=1)
        self.check(['-Qold'], sys_argv=[''], run_stdin=True, division_new=0)
        self.check(['-Qwarn'], sys_argv=[''], run_stdin=True, division_warning=1)
        self.check(['-Qwarnall'], sys_argv=[''], run_stdin=True,
                   division_warning=2)
        self.check(['-Q', 'new'], sys_argv=[''], run_stdin=True, division_new=1)
        self.check(['-SOQnew'], sys_argv=[''], run_stdin=True,
                   no_site=1, optimize=1, division_new=1)
        self.check(['-SOQ', 'new'], sys_argv=[''], run_stdin=True,
                   no_site=1, optimize=1, division_new=1)
        self.check(['-i'], sys_argv=[''], run_stdin=True,
                   interactive=1, inspect=1)
        self.check(['-h'], output_contains='usage:')
        self.check(['-S', '-tO', '-h'], output_contains='usage:')
        self.check(['-S', '-thO'], output_contains='usage:')
        self.check(['-S', '-tO', '--help'], output_contains='usage:')
        self.check(['-S', '-tO', '--info'], output_contains='translation')
        self.check(['-S', '-tO', '--version'], output_contains='Python')
        self.check(['-S', '-tOV'], output_contains='Python')
        self.check(['--jit', 'foobar', '-S'], sys_argv=[''],
                   run_stdin=True, no_site=1)
        self.check(['-c', 'pass'], sys_argv=['-c'], run_command='pass')
        self.check(['-cpass'], sys_argv=['-c'], run_command='pass')
        self.check(['-cpass','x'], sys_argv=['-c','x'], run_command='pass')
        self.check(['-Sc', 'pass'], sys_argv=['-c'], run_command='pass',
                   no_site=1)
        self.check(['-Scpass'], sys_argv=['-c'], run_command='pass', no_site=1)
        self.check(['-c', '', ''], sys_argv=['-c', ''], run_command='')
        self.check(['-mfoo', 'bar', 'baz'], sys_argv=['foo', 'bar', 'baz'],
                   run_module=True)
        self.check(['-m', 'foo', 'bar', 'baz'], sys_argv=['foo', 'bar', 'baz'],
                   run_module=True)
        self.check(['-Smfoo', 'bar', 'baz'], sys_argv=['foo', 'bar', 'baz'],
                   run_module=True, no_site=1)
        self.check(['-Sm', 'foo', 'bar', 'baz'], sys_argv=['foo', 'bar', 'baz'],
                   run_module=True, no_site=1)
        self.check(['-', 'foo', 'bar'], sys_argv=['-', 'foo', 'bar'],
                   run_stdin=True)
        self.check(['foo', 'bar'], sys_argv=['foo', 'bar'])
        self.check(['foo', '-i'], sys_argv=['foo', '-i'])
        self.check(['-i', 'foo'], sys_argv=['foo'], interactive=1, inspect=1)
        self.check(['--', 'foo'], sys_argv=['foo'])
        self.check(['--', '-i', 'foo'], sys_argv=['-i', 'foo'])
        self.check(['--', '-', 'foo'], sys_argv=['-', 'foo'], run_stdin=True)
        self.check(['-Wbog'], sys_argv=[''], warnoptions=['bog'], run_stdin=True)
        self.check(['-W', 'ab', '-SWc'], sys_argv=[''], warnoptions=['ab', 'c'],
                   run_stdin=True, no_site=1)

    def test_sysflags(self):
        flags = (
            ("debug", "-d", "1"),
            ("py3k_warning", "-3", "1"),
            ("division_warning", "-Qwarn", "1"),
            ("division_warning", "-Qwarnall", "2"),
            ("division_new", "-Qnew", "1"),
            (["inspect", "interactive"], "-i", "1"),
            ("optimize", "-O", "1"),
            ("optimize", "-OO", "2"),
            ("dont_write_bytecode", "-B", "1"),
            ("no_user_site", "-s", "1"),
            ("no_site", "-S", "1"),
            ("ignore_environment", "-E", "1"),
            ("tabcheck", "-t", "1"),
            ("tabcheck", "-tt", "2"),
            ("verbose", "-v", "1"),
            ("unicode", "-U", "1"),
            ("bytes_warning", "-b", "1"),
        )
        for flag, opt, value in flags:
            if isinstance(flag, list):   # this is for inspect&interactive
                expected = {}
                for flag1 in flag:
                    expected[flag1] = int(value)
            else:
                expected = {flag: int(value)}
            self.check([opt, '-c', 'pass'], sys_argv=['-c'],
                       run_command='pass', **expected)

    def test_sysflags_envvar(self, monkeypatch):
        monkeypatch.setenv('PYTHONNOUSERSITE', '1')
        expected = {"no_user_site": True}
        self.check(['-c', 'pass'], sys_argv=['-c'], run_command='pass', **expected)
        

class TestInteraction:
    """
    These tests require pexpect (UNIX-only).
    http://pexpect.sourceforge.net/
    """

    def _spawn(self, *args, **kwds):
        try:
            import pexpect
        except ImportError, e:
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
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        return self._spawn(sys.executable, [app_main] + argv)

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

    def test_help(self):
        # test that -h prints the usage, including the name of the executable
        # which should be /full/path/to/app_main.py in this case
        child = self.spawn(['-h'])
        child.expect(r'usage: .*app_main.py \[options\]')

    def test_run_script(self):
        child = self.spawn([demo_script])
        idx = child.expect(['hello', 'Python ', '>>> '])
        assert idx == 0   # no banner or prompt
        child.expect(re.escape("Name: __main__"))
        child.expect(re.escape('File: ' + demo_script))
        child.expect(re.escape('Exec: ' + app_main))
        child.expect(re.escape('Argv: ' + repr([demo_script])))
        child.expect('goodbye')

    def test_run_script_with_args(self):
        argv = [demo_script, 'hello', 'world']
        child = self.spawn(argv)
        child.expect(re.escape('Argv: ' + repr(argv)))
        child.expect('goodbye')

    def test_no_such_script(self):
        import errno
        msg = os.strerror(errno.ENOENT)   # 'No such file or directory'
        child = self.spawn(['xxx-no-such-file-xxx'])
        child.expect(re.escape(msg))

    def test_option_i(self):
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

    def test_option_i_crashing(self):
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

    def test_options_i_c_crashing(self):
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

    def test_atexit(self):
        child = self.spawn([])
        child.expect('>>> ')
        child.sendline('def f(): print "foobye"')
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

    def test_pythonstartup(self):
        old = os.environ.get('PYTHONSTARTUP', '')
        try:
            os.environ['PYTHONSTARTUP'] = crashing_demo_script
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
        finally:
            os.environ['PYTHONSTARTUP'] = old

    def test_ignore_python_startup(self):
        old = os.environ.get('PYTHONSTARTUP', '')
        try:
            os.environ['PYTHONSTARTUP'] = crashing_demo_script
            child = self.spawn(['-E'])
            child.expect(re.escape(banner))
            index = child.expect(['Traceback', '>>> '])
            assert index == 1      # no traceback
        finally:
            os.environ['PYTHONSTARTUP'] = old

    def test_ignore_python_inspect(self):
        os.environ['PYTHONINSPECT_'] = '1'
        try:
            child = self.spawn(['-E', '-c', 'pass'])
            from pexpect import EOF
            index = child.expect(['>>> ', EOF])
            assert index == 1      # no prompt
        finally:
            del os.environ['PYTHONINSPECT_']

    def test_ignore_python_path(self):
        old = os.environ.get('PYTHONPATH', '')
        try:
            os.environ['PYTHONPATH'] = 'foobarbaz'
            child = self.spawn(['-E', '-c', 'import sys; print sys.path'])
            from pexpect import EOF
            index = child.expect(['foobarbaz', EOF])
            assert index == 1      # no foobarbaz
        finally:
            os.environ['PYTHONPATH'] = old

    def test_unbuffered(self):
        line = 'import os,sys;sys.stdout.write(str(789));os.read(0,1)'
        child = self.spawn(['-u', '-c', line])
        child.expect('789')    # expect to see it before the timeout hits
        child.sendline('X')

    def test_options_i_m(self):
        if sys.platform == "win32":
            skip("close_fds is not supported on Windows platforms")
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = os.path.join(autopath.this_dir, 'mymodule.py')
        p = os.path.abspath(p)
        child = self.spawn(['-i',
                            '-m', 'pypy.translator.goal.test2.mymodule',
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
        child.sendline('"pypy.translator.goal.test2" in sys.modules')
        child.expect('True')
        child.sendline('"pypy.translator.goal.test2.mymodule" in sys.modules')
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
        python = sys.executable
        pipe = subprocess.Popen([python, app_main, "-u", "-i"],
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
                print 6*7
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
            print 6*7
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
        # This doesn't really test app_main.py, but a behavior that
        # can only be checked on top of py.py with pexpect.
        path = getscript("""
            import sys
            sys.stdout.write('Are you suggesting coconuts migrate? ')
            line = sys.stdin.readline()
            assert line.rstrip() == 'Not at all. They could be carried.'
            print 'A five ounce bird could not carry a one pound coconut.'
            """)
        py_py = os.path.join(autopath.pypydir, 'bin', 'py.py')
        child = self._spawn(sys.executable, [py_py, path])
        child.expect('Are you suggesting coconuts migrate?', timeout=120)
        child.sendline('Not at all. They could be carried.')
        child.expect('A five ounce bird could not carry a one pound coconut.')

    def test_no_space_before_argument(self):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        child = self.spawn(['-cprint "hel" + "lo"'])
        child.expect('hello')

        child = self.spawn(['-mpypy.translator.goal.test2.mymodule'])
        child.expect('mymodule running')

    def test_ps1_only_if_interactive(self):
        argv = ['-c', 'import sys; print hasattr(sys, "ps1")']
        child = self.spawn(argv)
        child.expect('False')

class TestNonInteractive:

    def run_with_status_code(self, cmdline, senddata='', expect_prompt=False,
            expect_banner=False, python_flags='', env=None):
        cmdline = '%s %s "%s" %s' % (sys.executable, python_flags,
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
        data, status = self.run_with_status_code(*args, **kwargs)
        return data

    def test_script_on_stdin(self):
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

    def test_run_crashing_script(self):
        data = self.run('"%s"' % (crashing_demo_script,))
        assert 'Hello2' in data
        assert 'NameError' in data
        assert 'Goodbye2' not in data

    def test_crashing_script_on_stdin(self):
        data = self.run(' < "%s"' % (crashing_demo_script,))
        assert 'Hello2' in data
        assert 'NameError' in data
        assert 'Goodbye2' not in data

    def test_option_W(self):
        data = self.run('-W d -c "print 42"')
        assert '42' in data
        data = self.run('-Wd -c "print 42"')
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
        data = self.run('-c "print 6**5"')
        assert '7776' in data

    def test_no_pythonstartup(self):
        old = os.environ.get('PYTHONSTARTUP', '')
        try:
            os.environ['PYTHONSTARTUP'] = crashing_demo_script
            data = self.run('"%s"' % (demo_script,))
            assert 'Hello2' not in data
            data = self.run('-c pass')
            assert 'Hello2' not in data
        finally:
            os.environ['PYTHONSTARTUP'] = old

    def test_pythonwarnings(self):
        old = os.environ.get('PYTHONWARNINGS', '')
        try:
            os.environ['PYTHONWARNINGS'] = "once,error"
            data = self.run('-W ignore -W default '
                            '-c "import sys; print sys.warnoptions"')
            assert "['ignore', 'default', 'once', 'error']" in data
        finally:
            os.environ['PYTHONWARNINGS'] = old

    def test_option_m(self):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = os.path.join(autopath.this_dir, 'mymodule.py')
        p = os.path.abspath(p)
        data = self.run('-m pypy.translator.goal.test2.mymodule extra')
        assert 'mymodule running' in data
        assert 'Name: __main__' in data
        # ignoring case for windows. abspath behaves different from autopath
        # concerning drive letters right now.
        assert ('File: ' + p) in data
        assert ('Argv: ' + repr([p, 'extra'])) in data

    def test_pythoninspect_doesnt_override_isatty(self):
        os.environ['PYTHONINSPECT_'] = '1'
        try:
            data = self.run('', senddata='6*7\nprint 2+3\n')
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
            print 'hello world'
            """)
        data = self.run(cmdline, senddata='6*7\nraise SystemExit\n',
                                 expect_prompt=True, expect_banner=False)
        assert 'hello world\n' in data
        assert '42\n' in data

    def test_non_interactive_stdout_fully_buffered(self):
        path = getscript(r"""
            import sys, time
            sys.stdout.write('\x00(STDOUT)\n\x00')   # stays in buffers
            time.sleep(1)
            sys.stderr.write('\x00[STDERR]\n\x00')
            time.sleep(1)
            # stdout flushed automatically here
            """)
        cmdline = '%s -u "%s" %s' % (sys.executable, app_main, path)
        print 'POPEN:', cmdline
        child_in, child_out_err = os.popen4(cmdline)
        data = child_out_err.read(11)
        assert data == '\x00[STDERR]\n\x00'    # from stderr
        child_in.close()
        data = child_out_err.read(11)
        assert data == '\x00(STDOUT)\n\x00'    # from stdout
        child_out_err.close()

    def test_proper_sys_path(self, tmpdir):

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

        tmpdir.join('site.py').write('print "SHOULD NOT RUN"')
        runme_py = tmpdir.join('runme.py')
        runme_py.write('print "some text"')

        cmdline = str(runme_py)

        with chdir_and_unset_pythonpath(tmpdir):
            data = self.run(cmdline, python_flags='-S')

        assert data == "some text\n"

        runme2_py = tmpdir.mkdir('otherpath').join('runme2.py')
        runme2_py.write('print "some new text"\n'
                        'import sys\n'
                        'print sys.path\n')

        cmdline2 = str(runme2_py)

        with chdir_and_unset_pythonpath(tmpdir):
            data = self.run(cmdline2, python_flags='-S')
        assert data.startswith("some new text\n")
        assert repr(str(tmpdir.join('otherpath'))) in data
        assert "''" not in data

        data = self.run('-c "import sys; print sys.path"')
        assert data.startswith("[''")

    def test_pyc_commandline_argument(self):
        p = getscript_pyc(self.space, "print 6*7\n")
        assert os.path.isfile(p) and p.endswith('.pyc')
        data = self.run(p)
        assert data == 'in _run_compiled_module\n'

    def test_main_in_dir_commandline_argument(self):
        if not hasattr(runpy, '_run_module_as_main'):
            skip("requires CPython >= 2.6")
        p = getscript_in_dir('import sys; print sys.argv[0]\n')
        data = self.run(p)
        assert data == p + '\n'
        data = self.run(p + os.sep)
        assert data == p + os.sep + '\n'

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
            sys.stdout.write(u'15\u20ac')
            sys.stdout.flush()
            """)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = encoding
            data = self.run(p, env=env)
            assert data == expected

    def test_sys_exit_pythonioencoding(self):
        if sys.version_info < (2, 7):
            skip("test required Python >= 2.7")
        p = getscript_in_dir("""
        import sys
        sys.exit(u'15\u20ac')
        """)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        data, status = self.run_with_status_code(p, env=env)
        assert status == 1
        assert data.startswith("15\xe2\x82\xac")


class AppTestAppMain:

    def setup_class(self):
        # ------------------------------------
        # setup code for test_get_library_path
        # ------------------------------------
        from pypy.module.sys.version import CPYTHON_VERSION, PYPY_VERSION
        cpy_ver = '%d.%d' % CPYTHON_VERSION[:2]
        
        goal_dir = os.path.dirname(app_main)
        # build a directory hierarchy like which contains both bin/pypy-c and
        # lib/pypy1.2/*
        prefix = udir.join('pathtest').ensure(dir=1)
        fake_exe = prefix.join('bin/pypy-c').ensure(file=1)
        expected_path = [str(prefix.join(subdir).ensure(dir=1))
                         for subdir in ('lib_pypy',
                                        'lib-python/modified-%s' % cpy_ver,
                                        'lib-python/%s' % cpy_ver)]
        
        self.w_goal_dir = self.space.wrap(goal_dir)
        self.w_fake_exe = self.space.wrap(str(fake_exe))
        self.w_expected_path = self.space.wrap(expected_path)
        self.w_trunkdir = self.space.wrap(os.path.dirname(autopath.pypydir))

    def test_get_library_path(self):
        import sys
        import os
        sys.path.append(self.goal_dir)
        try:
            import app_main
            app_main.os = os
            newpath = app_main.get_library_path('/tmp/pypy-c') # stdlib not found
            assert newpath == sys.path
            newpath = app_main.get_library_path(self.fake_exe)
            # we get at least 'expected_path', and maybe more (e.g.plat-linux2)
            assert newpath[:len(self.expected_path)] == self.expected_path
        finally:
            sys.path.pop()

    def test_trunk_can_be_prefix(self):
        import sys
        import os
        sys.path.append(self.goal_dir)
        try:
            import app_main
            app_main.os = os
            pypy_c = os.path.join(self.trunkdir, 'pypy', 'translator', 'goal', 'pypy-c')
            newpath = app_main.get_library_path(pypy_c)
            # we get at least lib_pypy, lib-python/modified-X.Y.Z,
            # lib-python/X.Y.Z, and maybe more (e.g. plat-linux2)
            assert len(newpath) >= 3
            for p in newpath:
                assert p.startswith(self.trunkdir)
        finally:
            sys.path.pop()
