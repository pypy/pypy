import autopath
from pypy.objspace.std import Space
from pypy.interpreter import baseobjspace, executioncontext, pyframe

class MethodChecker(object):
    """ Checks which methods are available on builtin objects."""

    def __init__(self):
        types = (1, 1.0, 'a', [], {}, (), None)

        self.space = Space()

        totalImplemented = 0
        totalNotImplemented = 0
        str = ['-', 'Implemented']

        for oneType in types:
            subImplemented = 0
            subNotImplemented = 0

            attribArr = dir(type(oneType))
            for attrib in attribArr:
                x = self.codetest('def f():\n return hasattr("%s","%s")\n'
                                  % (oneType, attrib), 'f', [])
                print '%-16s%-18s%s' % (type(oneType), attrib, str[x])
                if x:
                    subImplemented += 1
                    totalImplemented += 1
                else:
                    subNotImplemented += 1
                    totalNotImplemented += 1
            print
            print '    %-16s Implemented:     %3d' % (type(oneType),
                                                      subImplemented)
            print '    %-16s Not implemented: %3d' % (type(oneType),
                                                      subNotImplemented)
            print '    %-16s TOTAL:           %3d' % (
                type(oneType), subNotImplemented + subImplemented)
            print
            
        print 'TOTAL Implemented:     %3d' % totalImplemented
        print 'TOTAL Not implemented: %3d' % totalNotImplemented
        print 'GRAND TOTAL:           %3d' % (
            totalNotImplemented + totalImplemented)

    def codetest(self, source, functionname, args):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with arguments 'args'."""
        space = self.space

        compile = space.builtin.compile
        w = space.wrap
        w_code = compile(w(source), w('<string>'), w('exec'), w(0), w(0))

        ec = executioncontext.ExecutionContext(space)

        w_tempmodule = space.newmodule(w("__temp__"))
        w_glob = space.getattr(w_tempmodule, w("__dict__"))
        space.setitem(w_glob, w("__builtins__"), space.w_builtins)
        
        frame = pyframe.PyFrame(space, space.unwrap(w_code), w_glob, w_glob)
        ec.eval_frame(frame)

        wrappedargs = w(args)
        wrappedfunc = space.getitem(w_glob, w(functionname))
        wrappedkwds = space.newdict([])
        try:
            w_output = space.call(wrappedfunc, wrappedargs, wrappedkwds)
        except baseobjspace.OperationError, e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)
        else:
            return space.unwrap(w_output)


if __name__ == '__main__':
    MethodChecker()
