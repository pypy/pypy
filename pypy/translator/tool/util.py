from pypy.annotation.model import SomeObject
from pypy.tool.udir import udir 
import sys

def update_usession_dir(stabledir = udir.dirpath('usession')): 
    from py import path 
    try:
        if stabledir.check(dir=1): 
            for x in udir.visit(lambda x: x.check(file=1)): 
                target = stabledir.join(x.relto(udir)) 
                if target.check():
                    target.remove()
                else:
                    target.dirpath().ensure(dir=1) 
                try:
                    target.mklinkto(x) 
                except path.Invalid: 
                    x.copy(target) 
    except path.Invalid: 
        print "ignored: couldn't link or copy to %s" % stabledir 

def mkexename(name):
    if sys.platform == 'win32':
        name = os.path.normpath(name + '.exe')
    return name

def assert_rpython_mostly_not_imported(): 
    prefix = 'pypy.rpython.'
    oknames = ('rarithmetic memory memory.lladdress extfunctable ' 
               'lltype objectmodel error ros'.split())
    wrongimports = []
    for name, module in sys.modules.items(): 
        if module is not None and name.startswith(prefix): 
            sname = name[len(prefix):]
            for okname in oknames: 
                if sname.startswith(okname): 
                    break
            else:
                wrongimports.append(name) 
    if wrongimports: 
       raise RuntimeError("cannot fork because improper rtyper code"
                          " has already been imported: %r" %(wrongimports,))

def sanity_check_exceptblocks(translator):
    annotator = translator.annotator
    irreg = 0
    for graph in translator.flowgraphs.itervalues():
        et, ev = graph.exceptblock.inputargs
        s_et = annotator.binding(et, extquery=True)
        s_ev = annotator.binding(ev, extquery=True)
        if s_et:
            if s_et.knowntype == type:
                if s_et.__class__ == SomeObject:
                    if hasattr(s_et, 'is_type_of') and  s_et.is_type_of == [ev]:
                        continue
                else:
                    if s_et.__class__ == annmodel.SomePBC:
                        continue
            print "*****", graph.name, "exceptblock is not completely sane"
            irreg += 1
    if irreg == 0:
        print "*** All exceptblocks seem sane."

def find_someobjects(translator, quiet=False):
    """Find all functions in that have SomeObject in their signature."""
    annotator = translator.annotator
    if not annotator:
        return # no annotations available

    translator.highlight_functions = {}

    def is_someobject(var):
        try:
            return annotator.binding(var).__class__ == SomeObject
        except KeyError:
            return False

    def short_binding(var):
        try:
            binding = annotator.binding(var)
        except KeyError:
            return "?"
        if binding.is_constant():
            return 'const %s' % binding.__class__.__name__
        else:
            return binding.__class__.__name__

    header = True
    items = [(graph.name, func, graph)
             for func, graph in translator.flowgraphs.items()]
    items.sort()
    num = someobjnum = 0
    for graphname, func, graph in items:
        unknown_input_args = len(filter(is_someobject, graph.getargs()))
        unknown_return_value = is_someobject(graph.getreturnvar())
        if unknown_input_args or unknown_return_value:
            someobjnum += 1
            translator.highlight_functions[func] = True
            if not quiet:
                if header:
                    header = False
                    print "=" * 70
                    print "Functions that have SomeObject in their signature"
                    print "=" * 70
                print ("%(name)s(%(args)s) -> %(result)s\n"
                       "%(filename)s:%(lineno)s\n"
                       % {'name': graph.name,
                          'filename': func.func_globals.get('__name__', '?'),
                          'lineno': func.func_code.co_firstlineno,
                          'args': ', '.join(map(short_binding,
                                                graph.getargs())),
                          'result': short_binding(graph.getreturnvar())})
        num += 1
    if not quiet:
        print "=" * 70
        percent = int(num and (100.0*someobjnum / num) or 0)
        print "someobjectness: %2d percent" % (percent)
        print "(%d out of %d functions get or return SomeObjects" % (
            someobjnum, num) 
        print "=" * 70

def worstblocks_topten(ann, n=10):
    from pypy.tool.ansi_print import ansi_print
    h = [(count, block) for block, count in ann.reflowcounter.iteritems()]
    h.sort()
    if not h:
        return
    print
    ansi_print(',-----------------------  Top %d Most Reflown Blocks  -----------------------.' % n, 36)
    for i in range(n):
        if not h:
            break
        count, block = h.pop()
        ansi_print('                                                      #%3d: reflown %d times  |' % (i+1, count), 36)
        ann.translator.about(block)
    ansi_print("`----------------------------------------------------------------------------'", 36)
    print

