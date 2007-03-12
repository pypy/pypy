"""
Tests for the entry point of pypy-c, app_main.py.
"""
import py
import sys, os, re
import autopath
from pypy.tool.udir import udir

DEMO_SCRIPT = """
print 'hello'
print 'Name:', __name__
print 'File:', __file__
import sys
print 'Exec:', sys.executable
print 'Argv:', sys.argv
print 'goodbye'
myvalue = 6*7
"""

CRASHING_DEMO_SCRIPT = """
print 'Hello2'
myvalue2 = 11
ooups
myvalue2 = 22
print 'Goodbye2'   # should not be reached
"""

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

demo_script_p = udir.join('demo_test_app_main.py')
demo_script_p.write(DEMO_SCRIPT)
demo_script = relpath(demo_script_p)

crashing_demo_script_p = udir.join('crashing_demo_test_app_main.py')
crashing_demo_script_p.write(CRASHING_DEMO_SCRIPT)
crashing_demo_script = relpath(crashing_demo_script_p)


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
        old = os.environ['PYTHONSTARTUP']
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


class TestNonInteractive:

    def run(self, cmdline):
        cmdline = '"%s" "%s" %s' % (sys.executable, app_main, cmdline)
        print 'POPEN:', cmdline
        child_in, child_out_err = os.popen4(cmdline)
        child_in.close()
        data = child_out_err.read()
        child_out_err.close()
        assert banner not in data          # no banner
        assert '>>> ' not in data          # no prompt
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

    def test_option_c(self):
        data = self.run('-c "print 6**5"')
        assert '7776' in data

    def test_no_pythonstartup(self):
        old = os.environ['PYTHONSTARTUP']
        try:
            os.environ['PYTHONSTARTUP'] = crashing_demo_script
            data = self.run('"%s"' % (demo_script,))
            assert 'Hello2' not in data
            data = self.run('-c pass')
            assert 'Hello2' not in data
        finally:
            os.environ['PYTHONSTARTUP'] = old
