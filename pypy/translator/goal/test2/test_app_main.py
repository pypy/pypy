"""
Tests for the entry point of pypy-c, app_main.py.
"""
import py
import sys, os, re
import autopath
from pypy.tool.udir import udir

banner = sys.version.splitlines()[0]

def relpath(path):
    # force 'path' to be a relative path, for testing purposes
    curdir = py.path.local()
    p = py.path.local(path)
    result = []
    while not p.relto(curdir):
        result.append(os.pardir)
        if curdir == curdir.dirpath():
            return str(path)     # no relative path found, give up
        curdir = curdir.dirpath()
    result.append(p.relto(curdir))
    return os.path.join(*result)

app_main = os.path.join(autopath.this_dir, os.pardir, 'app_main.py')
app_main = os.path.abspath(app_main)

_counter = 0
def getscript(source):
    global _counter
    p = udir.join('demo_test_app_main_%d.py' % (_counter,))
    _counter += 1
    p.write(str(py.code.Source(source)))
    return relpath(p)


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

    def test_unbuffered(self):
        line = 'import os,sys;sys.stdout.write(str(789));os.read(0,1)'
        child = self.spawn(['-u', '-c', line])
        child.expect('789')    # expect to see it before the timeout hits
        child.sendline('X')

    def test_options_i_m(self):
        if sys.platform == "win32":
            skip("close_fds is not supported on Windows platforms")
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
        #XXX the following doesn't work on CPython 2.5 either
        #child.sendline('somevalue')
        #child.expect(re.escape(repr("foobar")))
        #child.expect('>>> ')
        child.sendline('import sys')
        child.sendline('"pypy.translator.goal.test2" in sys.modules')
        child.expect('True')
        child.sendline('"pypy.translator.goal.test2.mymodule" in sys.modules')
        child.expect('False')

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
        old = os.environ.get('PYTHONINSPECT', '')
        try:
            os.environ['PYTHONINSPECT'] = '1'
            path = getscript("""
                print 6*7
                """)
            child = self.spawn([path])
            child.expect('42')
            child.expect('>>> ')
        finally:
            os.environ['PYTHONINSPECT'] = old

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
        py.test.skip("obscure difference with CPython -- do we care?")
        old = os.environ.get('PYTHONINSPECT', '')
        try:
            path = getscript("""
                import os
                del os.environ['PYTHONINSPECT']
                """)
            child = self.spawn([path])
            xxx  # do we expect a prompt or not?  CPython gives one
        finally:
            os.environ['PYTHONINSPECT'] = old

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
        child = self.spawn(['-cprint "hel" + "lo"'])
        child.expect('hello')

        child = self.spawn(['-mpypy.translator.goal.test2.mymodule'])
        child.expect('mymodule running')


class TestNonInteractive:

    def run(self, cmdline, senddata='', expect_prompt=False,
            expect_banner=False):
        cmdline = '%s "%s" %s' % (sys.executable, app_main, cmdline)
        print 'POPEN:', cmdline
        child_in, child_out_err = os.popen4(cmdline)
        child_in.write(senddata)
        child_in.close()
        data = child_out_err.read()
        child_out_err.close()
        assert (banner in data) == expect_banner   # no banner unless expected
        assert ('>>> ' in data) == expect_prompt   # no prompt unless expected
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
        assert 'Argument expected for the -W option' in data

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

    def test_option_m(self):
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
        old = os.environ.get('PYTHONINSPECT', '')
        try:
            os.environ['PYTHONINSPECT'] = '1'
            data = self.run('', senddata='6*7\nprint 2+3\n')
            assert data == '5\n'
        finally:
            os.environ['PYTHONINSPECT'] = old

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
