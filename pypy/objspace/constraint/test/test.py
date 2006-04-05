from pypy.annotation.model import SomeTuple, SomeInteger
from pypy.objspace.logic import Space, unify, newvar

space = Space(nofaking=True,
              compiler="ast", # interpreter/astcompiler
              translating=True,
              usemodules=[],
              geninterp=False)
#              geninterp=not getattr(driver.options, 'lowmem', False))

def cfunc(pyfunc, annotations):
    from pypy.translator.interactive import Translation
    from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
    compiled = None
    try:
        print "translating"
        t = Translation(pyfunc, policy=PyPyAnnotatorPolicy(space))
        print 'translated'
        compiled = t.compile_c(annotations)
        print 'compiled'
    except Exception, e:
        print e.__class__.__name__, e
        t.view()
        raise
    return compiled

##     compiledFunc = cfunc(self.filterFunc,
##                      [SomeTuple([SomeInteger(), SomeInteger()])] * len(variables))



def unify_42():
    #X = newvar(space)
    space.unify(space.newint(42),
                space.newint(42))
    return space.newint(42)


def test_unify_var_val():
    compiled = cfunc(unify_42, [])
    if compiled:
        assert compiled() == space.newint(42)

