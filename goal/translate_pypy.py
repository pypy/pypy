#
#  
#
import autopath, sys
from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.objspace.std.intobject import W_IntObject
from pypy.translator.translator import Translator
from pypy.annotation import model as annmodel

import buildcache 

# __________  Entry point  __________

def entry_point():
    w_a = W_IntObject(space, -6)
    w_b = W_IntObject(space, -7)
    return space.mul(w_a, w_b)


# __________  Main  __________

def analyse(entry_point=entry_point):
    global t, space
    space = StdObjSpace()
    buildcache.buildcache(space) 
    t = Translator(entry_point, verbose=True, simplifying=True)
    a = t.annotate([])
    a.simplify()


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

    def run_server():
        from pypy.translator.tool.pygame.flowviewer import TranslatorLayout
        from pypy.translator.tool.pygame.graphdisplay import GraphDisplay
        display = GraphDisplay(TranslatorLayout(t))
        display.run()

    def debug():
        import traceback
        exc, val, tb = sys.exc_info()
        print >> sys.stderr
        traceback.print_exception(exc, val, tb)
        print >> sys.stderr

        block = getattr(val, '__annotator_block', None)
        if block:
            print '-'*60
            about(block)
            print '-'*60
        
        print >> sys.stderr
        import threading
        import pdb
        t = threading.Thread(target=pdb.post_mortem, args=(tb,))
        t.start()
        run_server()
        import pygame
        pygame.quit()

    try:
        analyse()
        t.frozen = True
        print '-'*60
        print 'Generating C code...'
        t.ccompile()
    except:
        debug()
    else:
        run_server()
