# functions to query information out of the translator and annotator from the debug prompt of translate_pypy
import types

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
        return ["one", iter(bunch).next()]
    else:
        t = dict.fromkeys([getattr(x, '__class__', type(x)) for x in bunch]).keys()
        return ["of type(s)"] + t

def strfy(x):
    try:
        return x.__name__
    except AttributeError:
        return str(x)

def pbcaccess(translator):
    annotator = translator.annotator
    for inf in annotator.getpbcaccesssets().root_info.itervalues():
        objs = inf.objects
        print len(objs), ' '.join(map(strfy,rep(objs))), inf.attrs.keys()

# PBCs
def pbcs(translator):
    bk = translator.annotator.bookkeeper
    xs = bk.pbccache.keys()
    funcs = [x for x in xs if isinstance(x, types.FunctionType)]
    staticmethods = [x for x in xs if isinstance(x, staticmethod)]
    instancemethods = [x for x in xs if isinstance(x, types.MethodType)]
    typs = [x for x in xs if isinstance(x, (type, types.ClassType))]
    rest = [x for x in xs if not isinstance(x, (types.FunctionType, staticmethod, types.MethodType, type, types.ClassType))]
    for objs in (funcs, staticmethods, instancemethods, typs, rest):
        print len(objs), ' '.join(map(strfy,rep(objs)))

# mutable captured "constants")
def mutables(translator):
    bk = translator.annotator.bookkeeper
    xs = bk.seen_mutable.keys()
    print len(xs), ' '.join(map(strfy,rep(xs)))

def prettypatt(patts):
    accum = []
    wslf = False
    woslf = False
    patts.sort()
    for slf, (sh_cnt, sh_ks, sh_st, sh_stst)  in patts:
        arg = []
        if slf is None:
            woslf = True
        else:
            wslf = True
            arg.append(slf)
        arg.append("+%d" % sh_cnt)
        for kw in sh_ks:
            arg.append("%s=" % kw)
        if sh_st:
           arg.append('*')
        if sh_stst:
           arg.append('**')
        accum.append("(%s)" % ', '.join(arg))
    if wslf and woslf:
        accum.append("!!!")
    return ' '.join(accum)
        

def pbccall(translator):
    fams = translator.annotator.getpbccallfamilies().root_info.itervalues()
    one_pattern_fams = {}
    rest = []
    for fam in fams:
        patts = {}
        for clsdef, sh in fam.patterns:
            if clsdef is None:
                slf = None
            else:
                slf = 'self'
            patts[(slf, sh)] = True
        if len(patts) != 1:
            rest.append((len(fam.objects), fam.objects, patts.keys()))
        else:
            cntrs = one_pattern_fams.setdefault(patts.keys()[0], [0,0])
            cntrs[0] += 1
            cntrs[1] += len(fam.objects)

    def pretty_nfam(nfam):
        if nfam == 1:
            return "1 family"
        else:
            return "%d families" % nfam

    def pretty_nels(nels):
        if nels == 1:
            return "one callable"
        else:
            return "in total %d callables" % nels

    def pretty_els(objs):
        accum = []
        for obj in objs:
            if isinstance(obj, types.FunctionType):
                accum.append("%s:%s" % (obj.__module__ or '?',  obj.__name__))
            else:
                accum.append(str(obj))
        return "{%s}" % ' '.join(accum)
        
    for patt, (nfam, nels) in one_pattern_fams.iteritems():
        print pretty_nfam(nfam), "with", pretty_nels(nels), "with one call-pattern:",  prettypatt([patt])

    print "- * -"

    rest.sort(lambda a,b: cmp(a[0], b[0]))

    for n, objs, patts in rest:
        print "family of", pretty_els(objs), "with call-patterns:", prettypatt(patts)
        
        
    
