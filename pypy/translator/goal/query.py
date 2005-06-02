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

class typerep(object):
    
    def __init__(self, x):
        self.typ = getattr(x, '__class__', type(x))
        self.bound = None
        if hasattr(x, 'im_self'):
            self.bound = x.im_self is not None
        elif hasattr(x, '__self__'):
            self.bound = x.__self__ is not None

    def __hash__(self):
        return hash(self.typ)

    def __cmp__(self, other):
        return cmp((self.typ.__name__, self.bound, self.typ), (other.typ.__name__, other.bound, other.typ))

    def __str__(self):
        if self.bound is None:
            return self.typ.__name__
        elif self.bound:
            return 'bound-%s' % self.typ.__name__
        else:
            return 'unbound-%s' % self.typ.__name__

def typereps(bunch):
    t = dict.fromkeys([typerep(x) for x in bunch]).keys()
    t.sort()
    return t

def rep(bunch):
    if len(bunch) == 1:
        parts = ["one", iter(bunch).next()]
    else:
        parts = ["of type(s)"] + typereps(bunch)
    return ' '.join(map(str, parts))

def pbcaccess(translator):
    annotator = translator.annotator
    for inf in annotator.getpbcaccesssets().root_info.itervalues():
        objs = inf.objects
        print len(objs), rep(objs), inf.attrs.keys()

# PBCs
def pbcs(translator):
    bk = translator.annotator.bookkeeper
    xs = bk.pbccache.keys()
    funcs = [x for x in xs if isinstance(x, types.FunctionType)]
    staticmethods = [x for x in xs if isinstance(x, staticmethod)]
    binstancemethods = [x for x in xs if isinstance(x, types.MethodType) and x.im_self]
    ubinstancemethods = [x for x in xs if isinstance(x, types.MethodType) and not x.im_self]
    typs = [x for x in xs if isinstance(x, (type, types.ClassType))]
    rest = [x for x in xs if not isinstance(x, (types.FunctionType, staticmethod, types.MethodType, type, types.ClassType))]
    for objs in (funcs, staticmethods, binstancemethods, ubinstancemethods, typs, rest):
        print len(objs), rep(objs)

# mutable captured "constants")
def mutables(translator):
    bk = translator.annotator.bookkeeper
    xs = bk.seen_mutable.keys()
    print len(xs), rep(xs)

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
        accum.append("!with and without self")
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
            kinds = typereps(fam.objects)

            flavor = tuple(kinds), patts.keys()[0]

            cntrs = one_pattern_fams.setdefault(flavor, [0,0])
            cntrs[0] += 1
            cntrs[1] += len(fam.objects)

    def pretty_nfam(nfam):
        if nfam == 1:
            return "1 family"
        else:
            return "%d families" % nfam

    def pretty_nels(kinds, nels):
        if nels == 1:
            return "one %s" % str(kinds[0]).title()
        else:
            return "in total %d %s" % (nels, '|'.join([str(kind).title()+'(s)' for kind in kinds]))

    def pretty_els(objs):
        accum = []
        for obj in objs:
            if isinstance(obj, types.FunctionType):
                accum.append("%s:%s" % (obj.__module__ or '?',  obj.__name__))
            else:
                accum.append(str(obj))
        return "{%s}" % ' '.join(accum)

    items = one_pattern_fams.items()

    items.sort(lambda a,b: cmp((a[0][1],a[1][1]), (b[0][1],b[1][1])))

    for (kinds, patt), (nfam, nels) in items:
        print pretty_nfam(nfam), "with", pretty_nels(kinds, nels), "with one call-pattern:",  prettypatt([patt])

    print "- * -"

    rest.sort(lambda a,b: cmp((a[0],a[2]), (b[0],b[2])))

    for n, objs, patts in rest:
        print "family of", pretty_els(objs), "with call-patterns:", prettypatt(patts)
        
        
    
