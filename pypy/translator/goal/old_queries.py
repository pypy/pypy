# functions to query information out of the translator and annotator from the debug prompt of translate
import types
import re

import pypy.annotation.model as annmodel
import pypy.objspace.flow.model as flowmodel


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
            s = self.typ.__name__
        elif self.bound:
            s = 'bound-%s' % self.typ.__name__
        else:
            s = 'unbound-%s' % self.typ.__name__

        if self.typ.__module__ == '__builtin__':
            s = "*%s*" % s

        return s

def typereps(bunch):
    t = dict.fromkeys([typerep(x) for x in bunch]).keys()
    t.sort()
    return t

def roots(classes):
    # find independent hierarchy roots in classes,
    # preserve None if it's part of classes
    work = list(classes)
    res = []

    notbound = False
    
    while None in work:
        work.remove(None)
        notbound = True

    if len(work) == 1:
        return notbound, classes[0]

    while work:
        cand = work.pop()
        for cls in work:
            if issubclass(cls, cand):
                continue
            if issubclass(cand, cls):
                cand = cls
                continue
        res.append(cand)
        work = [cls for cls in work if not issubclass(cls, cand)]


    for x in res:
        for y in res:
            if x != y:
                assert not issubclass(x, y), "%s %s %s" % (classes, x,y)
                assert not issubclass(y, x), "%s %s %s" % (classes, x,y)

    return notbound, tuple(res)
            
def callablereps(bunch):
    callables = [func for clsdef, func in bunch]
    classes = [clsdef and clsdef.cls for clsdef, func in bunch]
    return roots(classes), tuple(typereps(callables))

def prettyfunc(func):
    descr = "(%s:%s)" % (getattr(func, '__module__', None) or '?', func.func_code.co_firstlineno)
    funcname = getattr(func, '__name__', None) or 'UNKNOWN'
    cls = getattr(func, 'class_', None)
    if cls:
        funcname = "%s.%s" % (cls.__name__, funcname)
    return descr+funcname

def prettycallable((cls, obj)):
    if cls is None or cls == (True, ()):
        cls = None
    else:
        notbound = False
        if isinstance(cls, tuple) and isinstance(cls[0], bool):
            notbound, cls = cls
        if isinstance(cls, tuple):
            cls = "[%s]" % '|'.join([x.__name__ for x in cls])
        else:
            cls = cls.__name__
        if notbound:
            cls = "_|%s" % cls

    if isinstance(obj, types.FunctionType):
        obj = prettyfunc(obj) 
    elif isinstance(obj, tuple):
        obj = "[%s]" % '|'.join([str(x) for x in obj])
    else:
        obj = str(obj)
        if obj.startswith('<'):
            obj = obj[1:-1]

    if cls is None:
        return str(obj)
    else:
        return "%s::%s" % (cls, obj)


def prettybunch(bunch):
    if len(bunch) == 1:
        parts = ["one", iter(bunch).next()]
    else:
        parts = ["of type(s)"] + typereps(bunch)
    return ' '.join(map(str, parts))

def pbcaccess(translator):
    annotator = translator.annotator
    for inf in annotator.getpbcaccesssets().root_info.itervalues():
        objs = inf.objects
        print len(objs), prettybunch(objs), inf.attrs.keys()

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
        print len(objs), prettybunch(objs)

# mutable captured "constants")
def mutables(translator):
    bk = translator.annotator.bookkeeper
    xs = bk.seen_mutable.keys()
    print len(xs), prettybunch(xs)

def prettypatt(patts):
    accum = []
    patts.sort()
    for (sh_cnt, sh_ks, sh_st, sh_stst)  in patts:
        arg = []
        arg.append("+%d" % sh_cnt)
        for kw in sh_ks:
            arg.append("%s=" % kw)
        if sh_st:
           arg.append('*')
        if sh_stst:
           arg.append('**')
        accum.append("(%s)" % ', '.join(arg))
    return ' '.join(accum)
        
def pbccallsanity(translator):
    callb = translator.annotator.getpbccallables()
    bk = translator.annotator.bookkeeper
    typs = [x for x in callb if isinstance(x, (type, types.ClassType))]
    for t in typs:
        assert len(callb[t]) == 1
        assert callb[t] == {(None,t): True}
    print len(typs), "of ",prettycallable(callablereps([(None, Exception), (None, object)]))
    ubm = [x for x in callb if isinstance(x, types.MethodType) and x.im_self is None]
    assert len(ubm) == 0
    bm = [x for x in callb if isinstance(x, types.MethodType) and x.im_self is not None]
    frompbc = 0
    notfrompbc = []
    for b in bm:
        assert len(callb[b]) == 1
        assert callb[b] == {(None,b): True}
        if b.im_class in bk.pbctypes or (b.im_class is None and b.im_self in bk.pbccache):
            frompbc += 1
        else:
            notfrompbc.append(b)
    class A:
        def m():
            pass
    print frompbc, "of", prettycallable(callablereps([(None, A().m)])), "from PBCs"
    print len(bm)-frompbc, "of", prettycallable(callablereps([(None, A().m)])), "not from PBCs"
    if len(notfrompbc) < 40:
        for b in notfrompbc:
            print " "*4, prettycallable((None, b))
    fs = [x for x in callb if isinstance(x, types.FunctionType)]
    assert len(fs) + len(typs) + frompbc + len(notfrompbc) == len(callb)
    plain = []
    r = []
    for x in fs:
        if len(callb[x]) == 1 and callb[x].keys()[0][0] == None:
            r.extend(callb[x].keys())
            plain.append(x)
    print len(plain), "of", prettycallable(callablereps(r))
    r = []
    for x in fs:
        if x not in plain and len(callb[x]) == 1:
            r.extend(callb[x].keys())
    print len(r), "of", prettycallable(callablereps(r))
    r = []
    b_nb = []
    for x in fs:
        if len(callb[x]) == 2 and [1 for clsdef, f in callb[x].keys() if clsdef is None]:
            r.extend(callb[x].keys())
            b_nb.append(x)
    print len(r), "of", prettycallable(callablereps(r))
    print "- other -"
    for x in fs:
        if len(callb[x]) >= 2 and x not in b_nb:
            print ' '.join([prettycallable((classdef and classdef.cls, func)) for (classdef,func) in callb[x].keys()])

def pretty_els(objs):
    accum = []
    for classdef, obj in objs:
        cls = classdef and classdef.cls
        accum.append(prettycallable((cls, obj)))
        els = ' '.join(accum)
    if len(accum) == 1:
        return els
    else:
        return "{%s}" % els

def pbccall(translator):
    fams = translator.annotator.getpbccallfamilies().root_info.itervalues()
    one_pattern_fams = {}
    rest = []
    for fam in fams:
        shapes = fam.patterns

        if len(shapes) != 1:
            rest.append((len(fam.objects), fam.objects, shapes.keys()))
        else:
            kinds = callablereps(fam.objects)

            flavor = tuple(kinds), shapes.keys()[0]
                
            cntrs = one_pattern_fams.setdefault(flavor, [0,0])
            cntrs[0] += 1
            cntrs[1] += len(fam.objects)

    def pretty_nfam(nfam):
        if nfam == 1:
            return "1 family"
        else:
            return "%d families" % nfam

    def pretty_nels(kinds, nels, nfam):
        if nels == 1 or nels == nfam:
            return "one %s" % prettycallable(kinds)
        else:
            return "in total %d %s" % (nels, prettycallable(kinds))

    items = one_pattern_fams.items()

    items.sort(lambda a,b: cmp((a[0][1],a[1][1]), (b[0][1],b[1][1]))) # sort by pattern and then by els

    for (kinds, patt), (nfam, nels) in items:
        print pretty_nfam(nfam), "with", pretty_nels(kinds, nels, nfam), "with one call-pattern:",  prettypatt([patt])

    print "- many patterns  -"

    manycallb = False
    rest.sort(lambda a,b: cmp((a[0],a[2]), (b[0],b[2])))

    for n, objs, patts in rest:
        if len(objs) > 1 and not manycallb:
            manycallb = True
            print " - many callables, many patterns -"
        print "family of", pretty_els(objs), "with call-patterns:", prettypatt(patts)

def pbcbmsanity(translator):
    callb = translator.annotator.getpbccallables()
    bk = translator.annotator.bookkeeper
    bmeths = [x for x in callb if isinstance(x, types.MethodType) and x.im_self is not None]
    print "%d bound-methods" % len(bmeths)
    fams = translator.annotator.getpbccallfamilies()
    plural_bm_families = {}
    one_el = 0
    for bm in bmeths:
        notpbc = bm.im_self not in bk.pbccache
        freestanding = bm.im_func in callb
        if notpbc or freestanding:
            print "! %s," % bm,
        if notpbc:
            print "of non-PBC %s,",
        if freestanding:
            print "found freestanding too"
        bm_fam = fams[(None, bm)]
        if len(bm_fam.objects) == 1:
            one_el += 1
        else:
            plural_bm_families[bm_fam] = True
    print "%d families of one bound-method" % one_el
    print "%d families with more than just one bound-method" % len(plural_bm_families)
    for bm_fam in plural_bm_families:
        print pretty_els(bm_fam.objects)
    return plural_bm_families

class Counters(dict):

    def __getitem__(self, outcome):
        if (isinstance(outcome, annmodel.SomeObject) or 
            isinstance(outcome, tuple) and outcome and 
            isinstance(outcome[0], annmodel.SomeObject)):
            for k in self.iterkeys():
                if k == outcome:
                    outcome = k
                    break
            else:
                raise KeyError
        return dict.__getitem__(self, outcome)

    def get(self, outcome, defl):
        try:
            return self[outcome]
        except KeyError:
            return defl

    def __setitem__(self, outcome, c):
        if (isinstance(outcome, annmodel.SomeObject) or 
            isinstance(outcome, tuple) and outcome and 
            isinstance(outcome[0], annmodel.SomeObject)):
            for k in self.iterkeys():
                if k == outcome:
                    outcome = k
                    break
        return dict.__setitem__(self, outcome, c)


def keyrepr(k):
    if isinstance(k, tuple):
        return "(%s)" % ', '.join([keyrepr(x) for x in k])
    else:
        return str(k)

def statsfor(t, category):
    stats = t.annotator.bookkeeper.stats
    for_category = stats.classify[category]
    print "%s total = %d" % (category, len(for_category))
    counters = Counters()
    for pos, outcome in for_category.iteritems():
        counters[outcome] = counters.get(outcome, 0) + 1
        
    w = max([len(keyrepr(o)) for o in counters.keys()])+1
    if w < 60:
        for outcome, n in counters.iteritems():
            print "%*s | %d" % (w, keyrepr(outcome), n)
    else:
        for outcome, n in counters.iteritems():
            print "%s | %d" % (keyrepr(outcome), n)

def statsforstrformat(t):
    stats = t.annotator.bookkeeper.stats
    stats = stats.classify['strformat']
    result = {}
    for fmt, args in stats.itervalues():
        fmts = re.findall("%l?.", fmt)
        if not isinstance(args, tuple):
            args = (args,)
        for f, a in zip(fmts, args):
            result[(f,a)] = result.get((f,a), 0) + 1
    for (f,a), c in result.iteritems():
        print "%s %s %d" % (f, keyrepr(a), c)

def statbuiltins(t):
    stats = t.annotator.bookkeeper.stats.classify
    for k in stats:
        if k.startswith('__builtin__'):
            statsfor(t, k)

def dicts(t):
    ann = t.annotator
    r = []

    def sdicts():
        for so in ann.bindings.itervalues():
            if isinstance(so, annmodel.SomeDict):
                yield so
        for so in ann.bookkeeper.immutable_cache.itervalues():
            if isinstance(so, annmodel.SomeDict):
                yield so
    
    for so in sdicts():
            sk, sv = so.dictdef.dictkey.s_value, so.dictdef.dictvalue.s_value
            for x in r:
                if x == (sk, sv):
                    break
            else:
                r.append((sk, sv))

    for x in r:
        print x

# debug helper
def tryout(f, *args):
    try:
        f(*args)
    except:
        import traceback
        traceback.print_exc()

def graph_footprint(graph):
    class Counter:
        blocks = 0
        links = 0
        ops = 0
    count = Counter()
    def visit(block):
        if isinstance(block, flowmodel.Block):
            count.blocks += 1
            count.ops += len(block.operations)
        elif isinstance(block, flowmodel.Link):
            count.links += 1
    flowmodel.traverse(visit, graph)
    return count.blocks, count.links, count.ops

# better used before backends opts
def duplication(t):
    d = {}
    funcs = t.flowgraphs.keys()
    print len(funcs)
    for f in funcs:
        fingerprint = f.func_code, graph_footprint(t.flowgraphs[f])
        d.setdefault(fingerprint  ,[]).append(f)
    l = []
    for fingerprint, funcs in d.iteritems():
        if len(funcs) > 1:
            l.append((fingerprint[0].co_name, len(funcs)))
    l.sort()
    for name, c in l:
        print name, c

def backcalls(t):
    g = {}
    for caller, callee in t.callgraph.itervalues():
        g.setdefault(caller,[]).append(callee)
    
    back = []
    color = {}
    WHITE, GRAY, BLACK = 0,1,2

    def visit(fcur,witness=[]):
        color[fcur] = GRAY
        for f in dict.fromkeys(g.get(fcur, [])):
            fcolor = color.get(f, WHITE)
            if fcolor == WHITE:
                visit(f,witness+[f])
            elif fcolor == GRAY:
                print "*", witness, f
                back.append((fcur, f))
        color[fcur] = BLACK
    
    visit(t.entrypoint, [t.entrypoint])

    return back

#

def worstblocks_topten(t, n=10):
    from pypy.tool.ansi_print import ansi_print
    ann = t.annotator
    h = [(count, block) for block, count in ann.reflowcounter.iteritems()]
    h.sort()
    if not h:
        print "annotator should have been run with debug collecting enabled"
        return
    print
    ansi_print(',-----------------------  Top %d Most Reflown Blocks  -----------------------.' % n, 36)
    for i in range(n):
        if not h:
            break
        count, block = h.pop()
        ansi_print('                                                      #%3d: reflown %d times  |' % (i+1, count), 36)
        t.about(block)
    ansi_print("`----------------------------------------------------------------------------'", 36)
    print
