# functions to query information out of the translator and annotator from the debug prompt of translate_pypy

import pypy.annotation.model as annmodel
import pypy.objspace.flow.model as flowmodel

#def sources(translator):
#    annotator = translator.annotator
#    d = {}
#    for v, s in annotator.bindings.iteritems():
#        if s.__class__ == annmodel.SomeObject and s.knowntype != type:
#            if s.origin:
#                d[s.origin[0]] = 1
#    for func in d:
#        print func.__module__ or '?', func.__name__
#    print len(d)
#    return d.keys()

class Found(Exception):
    pass

def sovars(translator, g):
    annotator = translator.annotator
    def visit(block):
        if isinstance(block, flowmodel.Block):
            for v in block.getvariables():
                s = annotator.binding(v, extquery=True)
                if s and s.__class__ == annmodel.SomeObject and s.knowntype != type:
                    print v,s
    flowmodel.traverse(visit, g)

def polluted(translator):
    """list functions with still real SomeObject variables"""
    annotator = translator.annotator
    def visit(block):
        if isinstance(block, flowmodel.Block):
            for v in block.getvariables():
                s = annotator.binding(v, extquery=True)
                if s and s.__class__ == annmodel.SomeObject and s.knowntype != type:
                    raise Found
    c = 0
    for f,g in translator.flowgraphs.iteritems():
        try:
            flowmodel.traverse(visit, g)
        except Found:
            print f.__module__ or '?', f.__name__
            c += 1
    print c

def rep(bunch):
    if len(bunch) == 1:
        return "one", iter(bunch).next()
    else:
        t = dict.fromkeys([getattr(x, '__class__', type(x)) for x in bunch]).keys()
        return "of types", t

def pbcaccess(translator):
    bk = translator.annotator.bookkeeper
    for inf in bk.pbc_maximal_access_sets.root_info.itervalues():
        objs = inf.objects
        print len(objs), ' '.join(map(str,rep(objs))), inf.attrs.keys()
        
