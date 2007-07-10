import py
import sys

py.test.skip("problems to run those on pypy test server")
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
        return self._spawn(str(py.magic.autopath().dirpath().dirpath().join('js_interactive.py')), argv)
    
    def prompt_send(self, message):
        self.child.expect('js>')
        self.child.sendline(message)
    
    def expect(self, message):
        self.child.expect(message)

    def sendline(self, message):
        self.child.sendline(message)
    
    def continue_send(self, message):
        self.child.expect('...')
        self.child.sendline(message)

    def setup_method(cls, method):
        cls.child = cls.spawn([])
    
    def test_interactive(self):
        child = self.child
        #child.expect('JS ')   # banner
        self.prompt_send('x = "hello"')
        self.expect('hello')
        self.sendline('function f (x) {')
        self.continue_send('return x;')
        self.continue_send('')
        self.continue_send('}')
        self.prompt_send('f(100)')
        self.expect('100')
        self.prompt_send('this')
        self.expect('[object Global]')

    def test_prints(self):
        self.prompt_send('x=123')
        self.expect('123')
        self.prompt_send('x=[1,2,3]')
        self.expect('1,2,3')
        self.prompt_send('x={1:1}')
        self.expect('[object Object]')
        
