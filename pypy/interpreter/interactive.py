from pypy.interpreter import executioncontext
from pypy.interpreter import pyframe
from pypy.interpreter import baseobjspace
from pypy.objspace import trivial
import code
import linecache

def offset2lineno(c, stopat):
    tab = c.co_lnotab
    line = c.co_firstlineno
    addr = 0
    for i in range(0, len(tab), 2):
        addr = addr + ord(tab[i])
        if addr > stopat:
            break
        line = line + ord(tab[i+1])
    return line

class PyPyConsole(code.InteractiveConsole):
    def __init__(self):
        code.InteractiveConsole.__init__(self)
        self.space = trivial.TrivialObjSpace()
        self.ec = executioncontext.ExecutionContext(self.space)
        self.locals['__builtins__'] = self.space.w_builtins

    def runcode(self, code):
        # ah ha!
        frame = pyframe.PyFrame(self.space, code,
                        self.locals, self.locals)
        try:
            self.ec.eval_frame(frame)
        except baseobjspace.OperationError, e:
            print "Traceback"
            tb = e.w_traceback[:]
            tb.reverse()
            for f, i in tb:
                co = f.bytecode
                fname = co.co_filename
                lineno = offset2lineno(co, i)
                print "  File", `fname`+',',
                print "line", lineno, "in", co.co_name
                l = linecache.getline(fname, lineno)
                if l:
                    print l[:-1]
            print e.w_type.__name__+':', e.w_value
            import traceback
            traceback.print_exc()
        
if __name__ == '__main__':
    con = PyPyConsole()
    con.interact()

