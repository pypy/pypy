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
"""

CRASHING_DEMO_SCRIPT = """
print 'hello'
ooups
print 'goodbye'   # should not be reached
"""

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
        return pexpect.spawn(*args, **kwds)

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


class TestNonInteractive:

    def run(self, cmdline):
        cmdline = '"%s" "%s" %s' % (sys.executable, app_main, cmdline)
        print 'POPEN:', cmdline
        child_in, child_out_err = os.popen4(cmdline)
        child_in.close()
        data = child_out_err.read()
        child_out_err.close()
        assert sys.version not in data     # no banner
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
        assert 'hello' in data
        assert 'NameError' in data
        assert 'goodbye' not in data

    def test_crashing_script_on_stdin(self):
        data = self.run(' < "%s"' % (crashing_demo_script,))
        assert 'hello' in data
        assert 'NameError' in data
        assert 'goodbye' not in data
