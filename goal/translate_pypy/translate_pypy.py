#
#  
#
import autopath

from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.translator.translator import Translator
from pypy.translator.annrpython import AnnotatorError


# __________  Entry point  __________

space = StdObjSpace()

def entry_point():
    w_a = W_IntObject(space, -6)
    w_b = W_IntObject(space, -7)
    return space.mul(w_a, w_b)


# __________  Main  __________

if __name__ == '__main__':

    def about(x):
        """ interactive debugging helper """
        from pypy.objspace.flow.model import Block, flatten
        if isinstance(x, Block):
            for func, graph in t.flowgraphs.items():
                if x in flatten(graph):
                    print x
                    print 'is a block in the graph of'
                    print func
                    print 'at %s:%d' % (func.func_globals.get('__name__', '?'),
                                        func.func_code.co_firstlineno)
                    break
            else:
                print x
                print 'is a block at some unknown location'
            print 'containing the following operations:'
            for op in x.operations:
                print op
            print '--end--'
            return
        print "don't know about", x

    def run_server(background=False, port=8000):
        import graphserver
        server = graphserver.Server(t)
        print >> sys.stderr, '* View the blocks at http://127.0.0.1:%d/' % port
        if background:
            import thread
            thread.start_new_thread(server.serve, ())
        else:
            server.serve()

    t = Translator(entry_point, verbose=True, simplifying=True)
    try:
        a = t.annotate([])
        a.simplify()
    except:
        import sys, traceback, thread
        exc, val, tb = sys.exc_info()
        print >> sys.stderr
        traceback.print_exception(exc, val, tb)
        print >> sys.stderr

        if isinstance(val, AnnotatorError) and hasattr(val, 'block'):
            print '-'*60
            about(val.block)
            print '-'*60
        
        run_server(background=True)
        print >> sys.stderr
        import pdb
        pdb.post_mortem(tb)
    else:
        run_server()
