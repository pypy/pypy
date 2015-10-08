
"""typesystem.py -- Typesystem-specific operations for RTyper."""

from rpython.rtyper.lltypesystem import lltype


def _getconcretetype(v):
    return v.concretetype

def getfunctionptr(graph, getconcretetype=_getconcretetype):
    """Return callable given a Python function."""
    llinputs = [getconcretetype(v) for v in graph.getargs()]
    lloutput = getconcretetype(graph.getreturnvar())

    FT = lltype.FuncType(llinputs, lloutput)
    name = graph.name
    if hasattr(graph, 'func') and callable(graph.func):
        # the Python function object can have _llfnobjattrs_, specifying
        # attributes that are forced upon the functionptr().  The idea
        # for not passing these extra attributes as arguments to
        # getcallable() itself is that multiple calls to getcallable()
        # for the same graph should return equal functionptr() objects.
        if hasattr(graph.func, '_llfnobjattrs_'):
            fnobjattrs = graph.func._llfnobjattrs_.copy()
            # can specify a '_name', but use graph.name by default
            name = fnobjattrs.pop('_name', name)
        else:
            fnobjattrs = {}
        # _callable is normally graph.func, but can be overridden:
        # see fakeimpl in extfunc.py
        _callable = fnobjattrs.pop('_callable', graph.func)
        return lltype.functionptr(FT, name, graph=graph,
                                  _callable=_callable, **fnobjattrs)
    else:
        return lltype.functionptr(FT, name, graph=graph)
