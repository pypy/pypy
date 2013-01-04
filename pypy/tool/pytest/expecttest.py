# Collects and executes "Expect" tests.
#
# Classes which names start with "ExpectTest", are started in a
# separate process, and monitored by the pexpect module.  This allows
# execution of dangerous code, which messes with the terminal for
# example.


import py
import os, sys
from rpython.tool.udir import udir
from pypy.conftest import pypydir


class ExpectTestMethod(py.test.collect.Function):
    @staticmethod
    def safe_name(target):
        s = "_".join(target)
        s = s.replace("()", "paren")
        s = s.replace(".py", "")
        s = s.replace(".", "_")
        s = s.replace(os.sep, "_")
        return s

    def safe_filename(self):
        name = self.safe_name(self.listnames())
        num = 0
        while udir.join(name + '.py').check():
            num += 1
            name = self.safe_name(self.listnames()) + "_" + str(num)
        return name + '.py'

    def _spawn(self, *args, **kwds):
        import pexpect
        kwds.setdefault('timeout', 600)
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        return self._spawn(sys.executable, argv)

    def runtest(self):
        target = self.obj
        import pexpect
        source = py.code.Source(target)[1:].deindent()
        filename = self.safe_filename()
        source.lines = ['import sys',
                      'sys.path.insert(0, %s)' % repr(os.path.dirname(pypydir))
                        ] + source.lines
        source.lines.append('print "%s ok!"' % filename)
        f = udir.join(filename)
        f.write(source)
        # run target in the guarded environment
        child = self.spawn([str(f)])
        import re
        child.expect(re.escape(filename + " ok!"))


class ExpectClassInstance(py.test.collect.Instance):
    Function = ExpectTestMethod


class ExpectClassCollector(py.test.collect.Class):
    Instance = ExpectClassInstance

    def setup(self):
        super(ExpectClassCollector, self).setup()
        try:
            import pexpect
        except ImportError:
            py.test.skip("pexpect not found")


