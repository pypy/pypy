# this file implements a little interactive loop that can be
# optionally entered at the end of a test run to allow inspection (and
# pdb-ing) of failures and/or errors.

import autopath
from pypy.tool import ppdb
import cmd, traceback

class TestPM(cmd.Cmd):
    def __init__(self, efs):
        cmd.Cmd.__init__(self)
        self.efs = efs
        self.prompt = 'tbi> '
    def emptyline(self):
        return 1

    def do_EOF(self, line):
        return 1
    do_q = do_EOF

    def print_tb(self, ef):
        from pypy.interpreter.baseobjspace import OperationError
        err = ef[1]
        print ''.join(traceback.format_exception(*err))
        if isinstance(err[1], OperationError):
            print 'and at app-level:'
            print
            err[1].print_application_traceback(ef[0].space)
    
    def do_l(self, line):
        i = 0
        for t, e in self.efs:
            print i, t.__class__.__module__, t.__class__.__name__, t.methodName
            i += 1

    def do_tb(self, arg):
        args = arg.split()
        if len(args) == 0:
            for x in self.efs:
                t = x[0]
                print t.__class__.__module__, t.__class__.__name__, t.methodName
                print
                self.print_tb(x)
                print
        elif len(args) == 1:
            try:
                tbi = int(args[0])
            except ValueError:
                print "error2"
            else:
                if 0 <= tbi < len(self.efs):
                    self.print_tb(self.efs[tbi])
                else:
                    print "error3"
        else:
            print "error"

    def do_d(self, arg):
        args = arg.split()
        if len(args) == 1:
            try:
                efi = int(args[0])
            except ValueError:
                print "error2"
            else:
                if 0 <= efi < len(self.efs):
                    s, (t, v, tb) = self.efs[efi]
                    ppdb.post_mortem(s.space, tb, v)
                else:
                    print "error3"
        else:
            print "error"


if __name__ == '__main__':
    # just for testing
    c = TestPM([])
    c.cmdloop()

