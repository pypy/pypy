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


class TestInteraction:
    """
    Install pexpect to run these tests (UNIX-only)
    http://pexpect.sourceforge.net/
    """

    def spawn(self, *args, **kwds):
        try:
            import pexpect
        except ImportError, e:
            py.test.skip(str(e))
        kwds.setdefault('timeout', 10)
        print 'SPAWN:', args, kwds
        return pexpect.spawn(*args, **kwds)

    def test_interactive(self):
        child = self.spawn(sys.executable, [app_main])
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
        child = self.spawn(sys.executable, [app_main, demo_script])
        idx = child.expect(['hello', 'Python ', '>>> '])
        assert idx == 0   # no banner or prompt
        child.expect(re.escape("Name: __main__"))
        child.expect(re.escape('File: ' + demo_script))
        child.expect(re.escape('Exec: ' + app_main))
        child.expect(re.escape('Argv: ' + repr([demo_script])))
        child.expect('goodbye')
