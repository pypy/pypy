import autopath
from pypy.interpreter.error import OperationError

from  py.xml import html

class html_plus(html):
    __tagspec__ = html.__tagspec__.copy()
    
    __tagspec__['button'] = 1
    __tagspec__['script'] = 1

html = html_plus

import os, sys
from sets import Set

W = 125
H = 12

RED   = "#ff0000"
WHITE = "#ffffff"
BLACK = "#000000"
GREY =  "#808080"

def incompleteness_bar(DIR, incompleteness):
    from PIL import Image, ImageDraw, ImageColor

    red = ImageColor.getrgb(RED)
    white = ImageColor.getrgb(WHITE)
    black = ImageColor.getrgb(BLACK)
    grey = ImageColor.getrgb(GREY)

    if incompleteness == -1.0:
        inc = -1
        name = "bar_none.png"
    else:
        inc = round((W-1) * incompleteness)
        if inc == 0 and incompleteness != 0:
            inc == 1
        name = "bar_%d.png" % inc

    imgfname = os.path.join(DIR,'images',name)

    if not os.path.exists(imgfname):
        img = Image.new("RGB",(W,H), red)
        draw = ImageDraw.Draw(img)

        if inc == -1:
            draw.rectangle([0,0,W-1,H-1], outline=black, fill=white)
        else:
            if W-1-inc != 0:
                draw.rectangle([0,0,W-1-inc,H-1],outline=grey, fill=grey)

        IMGDIR = os.path.join(DIR,'images')

        if not os.path.isdir(IMGDIR):
            os.mkdir(IMGDIR)

        img.save(imgfname,optimize=True)

    return html.img(src=os.path.join('images', name),alt="incompleteness=%.2f" % incompleteness)


NOTFOUND = object()

class Explore:

    def __init__(self, label):
        self.label = label
        self.type_names = {}

    def get_module(self, name):
        pass

    def names(self, obj):
        if obj is NOTFOUND:
            return []
        return self.donames(obj)
        

    def donames(self, obj):
        pass

    def findattr(self, obj, name):
        if obj is NOTFOUND:
            return NOTFOUND
        return self.dofindattr(obj, name)

    def dofindattr(self, obj, name):
        pass

    def get_kind(self, obj):
        if obj is NOTFOUND:
            return '-'
        if self.is_class(obj):
            return 'C'
        elif self.findattr(obj, '__call__') is not NOTFOUND:
            return '()'
        else:
            return '_'

    def is_class(self, obj):
        if obj is NOTFOUND:
            return False
        return self.dois_class(obj)

    def is_faked(self, obj):
        return False

    def get_mro(self, obj):
        if obj is NOTFOUND:
            return []
        return self.doget_mro(obj)

    def doget_mro(self, obj):
        pass

    #def get_type(self, obj):
    #    pass
    #
    #def assign_class_name(obj, name):
    #    if obj in self.type_names:
    #        return
    #    self.type_names[obj] = name
    #
    #def get_lazy_class_name(obj):
    #    return lambda: self.type_names[obj]


class HostExplore(Explore):

    def __init__(self):
        import sys
        Explore.__init__(self, "CPython %s" % sys.version)

    def get_module(self, name):
        try:
            return __import__(name,{},{},['*'])
        except ImportError:
            return NOTFOUND

    def donames(self, obj):
        return obj.__dict__.keys()

    def dofindattr(self, obj, name):
        return getattr(obj, name, NOTFOUND)

    def dois_class(self, obj):
        import types
        return type(obj) in (type, types.ClassType)

    def doget_mro(self, obj):
        import inspect
        return inspect.getmro(obj)

    #def get_type(self, obj):
    #    return type(obj)


def abstract_mro(obj, get_bases, acc=None):
    if acc is None:
        acc = []
    if obj in acc:
        return acc
    acc.append(obj)
    for base in get_bases(obj):
        abstract_mro(base, get_bases, acc)
    return acc
    
class ObjSpaceExplore(Explore):

    def __init__(self, space):
        Explore.__init__(self, "PyPy/%s" % space.__class__.__name__)
        self.space = space

    def get_module(self, name):
        space = self.space
        w = space.wrap
        try:
            return space.builtin.call('__import__', w(name),w({}),w({}),w(['*']))
        except OperationError:
            return NOTFOUND

    def donames(self, obj):
        space = self.space
        return space.unwrap(space.call_method(space.getattr(obj, space.wrap('__dict__')), 'keys'))

    def dofindattr(self, obj, name):
        space = self.space
        try:
            return space.getattr(obj, space.wrap(name))
        except OperationError, e:
            return NOTFOUND

    def is_faked(self, obj):
        if hasattr(obj, 'instancetypedef'):
            return hasattr(obj.instancetypedef, 'fakedcpytype')
        else:
            return self.is_faked(self.space.type(obj))

    def dois_class(self, obj):
        #space = self.space
        #w_t = space.type(obj)
        #if space.is_w(w_t, space.w_type) or space.is_w(w_t, space.w_classobj):
        #    return True
        return self.findattr(obj, '__bases__') is not NOTFOUND

    def doget_mro(self, obj):
        space = self.space
        try:
            return space.unpackiterable(space.getattr(obj, space.wrap('__mro__')))
        except OperationError:
            def get_bases(obj):
                return space.unpackiterable(space.getattr(obj, space.wrap('__bases__')))

            return abstract_mro(obj, get_bases)

    #def get_type(self, obj):
    #    return type(obj)


class Status:
    def __init__(self, msg, detail_missing, class_, incompleteness, shortmsg = None):
        self.msg = msg
        self.detail_missing = detail_missing
        self.class_ = class_
        self.incompleteness = incompleteness
        if shortmsg is None:
            self.shortmsg = msg
        else:
            self.shortmsg = shortmsg

class Entry:

    def __init__(self, name):
        self.name = name
        self.shortname = name
        self.status = 'PRESENT'

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.name)

    def __str__(self):
        return self.name

    def set_status(self, obj1, obj2, expl1):
        if obj1 is NOTFOUND:
            assert obj2 is not NOTFOUND, "whoopsy %s" % self.name
            self.status = 'MISSING'
            self.specifically = 'missing'
        elif expl1.is_faked(obj1) and obj2 is not NOTFOUND:
            self.status = 'MISSING'
            self.specifically = 'faked'
        elif obj2 is NOTFOUND:
            self.status = expl1

    def only_in(self, parent):
            if parent is not None and parent.status != 'PRESENT':
                return ""           
            return 'only in %s' % self.status.label

    def status_wrt(self, parent=None):
        detail_missing = 0
        incompleteness = 0.0
        if self.status == 'MISSING':
            class_= msg = self.specifically
            detail_missing = 1
            incompleteness = 1.0
        elif self.status == 'PRESENT':
            msg = ''
            class_ = None
        else:
            msg = self.only_in(parent)
            if msg:
                class_ = "only_in"
            else:
                class_ = None
            incompleteness = -1.0            
        return Status(msg, detail_missing, class_, incompleteness)

    def attach(self, parent, annot=None, name=None):
        if self.status == 'MISSING':
            parent.total += 1
            parent.missing += 1
        elif self.status == 'PRESENT':
            parent.total += 1

        if annot is None:
            parent.add_row(self, [], name=name, parent=parent)
        else:
            parent.add_row(self, [annot], name=name, parent=parent)

    def grandadd(self, parent):
        if self.status == 'MISSING':
            parent.grandtotal += 1
            parent.grandmissing += 1
        elif self.status == 'PRESENT':
            parent.grandtotal += 1
        
    def handle(self):
        return self.shortname, # 1-tuple!

    def link(self, name):
        h = self.handle()
        if len(h) == 1:
            h = h[0]
            if name is None:
                return h
            if name.endswith(h):
                return name
            return "%s [%s]" % (name, h)
        else:
            h, dest = h
            if name is None:
                return html.a(h, href=dest)
            if name.endswith(h):
                return html.a(name, href=dest)
            return html.span(name, " [",
                             html.a(h, href=dest), "]")

            

reports = []

class Report(Entry):

    useshort = False

    notes = None

    descr = granddescr = "<not specified>"
    
    def __init__(self, name, title=None, fname=None, **kwds):
        if title is None:
            title = name
        Entry.__init__(self, name)

        self.title = title

        self.rows = []

        reports.append(self)

        self.total = 0
        self.missing = 0

        self.grandtotal = 0
        self.grandmissing = 0

        self._fname = fname

        self.__dict__.update(kwds)


    def add_row(self, entry, rest, name=None, parent=None):
        self.rows.append((name, entry, rest, parent))

    def missing_stats(self, missing, total, descr):
        return "%s/%s %s missing (%.1f%%)" % (missing, total, descr, float(missing)/total*100)        

    def status_wrt(self, parent=None):
        detail_missing = 0
        incompleteness = 0.0
        
        if self.status == 'MISSING':
            count = "%s %s" % (self.total, self.descr)
            shortmsg = "%s (%s)" % (self.specifically, count)
            detail_missing = self.total
            if self.grandtotal:
                count = "%s or in detail %s %s" % (count, self.granddescr, self.grandtotal)
                detail_missing = self.grandtotal
            msg = "%s (%s)" % (self.specifically, count)
            return Status(msg, detail_missing, class_=self.specifically, incompleteness=1.0,
                          shortmsg = shortmsg)
        elif self.status == 'PRESENT':
            if self.missing == 0 and self.grandmissing == 0:
                return Status(msg="complete", detail_missing=detail_missing, class_=None,
                              incompleteness=incompleteness)
            disj = "or "
            if self.missing == 0:
                msg = "all present but"
                incompleteness = 1.0
                disj = ""
            else:
                msg = self.missing_stats(self.missing, self.total, self.descr)
                detail_missing = self.missing
                incompleteness = float(self.missing) / self.total

            shortmsg = msg
                
            if self.grandtotal:
                msg = "%s %sin detail %s" % (msg, disj,
                                             self.missing_stats(self.grandmissing, self.grandtotal,
                                                                self.granddescr))
                detail_missing = self.grandmissing
                incompleteness = (incompleteness + float(self.grandmissing)/self.grandtotal)/2
            return Status(msg, detail_missing, class_='somemissing',
                          incompleteness=incompleteness, shortmsg = shortmsg)
        else:
            msg = self.only_in(parent)
            if msg:
                class_ = "only_in"
            else:
                class_ = None
            return Status(msg, detail_missing=0, class_=class_,
                          incompleteness=-1.0)                

    def fname(self):
        fname = self._fname
        if fname is None:
            fname = self.name
        return fname+'.html'

    def handle(self):
        return self.shortname, self.fname()

    def fill_table(self, dir, tbl, rows):
        def set_class(class_):
            if class_ is None:
                return {}
            else:
                return {'class': class_}
        
        i = 0
        for name, entry, rest, st in rows:
            tr_class = i%2 == 0 and "even" or "odd"
            if self.useshort:
                msg = st.shortmsg
            else:
                msg = st.msg
            rest = rest + [incompleteness_bar(dir, st.incompleteness), msg]            
            tbl.append(html.tr(
                html.td(entry.link(name), **set_class(st.class_)),
                *map(html.td,rest), **{'class': tr_class})
                       )
            i += 1
        
    def html(self, dir):
        title = self.title

        def set_class(class_):
            if class_ is None:
                return {}
            else:
                return {'class': class_}

        if self.notes is not None:
            notes = html.p(self.notes)
        else:
            notes = html.p()

        st = self.status_wrt()

        msg = st.msg
        class_ = st.class_
        bar = incompleteness_bar(dir, st.incompleteness)

        HEADER = '''<?xml version="1.0" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'''

        HIDE = 'display: none'
        SHOW = 'display: table'

        alpha_table = html.table(id="alpha", style=SHOW)
        grandmissing_table = html.table(id="grandmissing", style=HIDE)
        incompleteness_table = html.table(id="incompleteness", style=HIDE)

        toggle = html.p("sort:",
            html.button("alphabetical", type="button", onclick="toggle(ALPHA)"),'|',
            html.button("incompleteness", type="button", onclick="toggle(INCOMPLETENESS)"),'|',
            html.button("# overall missing", type="button", onclick="toggle(GRANDMISSING)"))

        page = html.html(
            html.head(html.title(title),
                      html.link(href="delta.css", rel="stylesheet", type="text/css"),
                      html.script(' ',type="text/javascript",src="delta.js")),
            html.body(self.navig(),
                      html.p(msg, bar, **set_class(class_)),
                      toggle,
                      alpha_table,
                      grandmissing_table,
                      incompleteness_table,
                      notes), xmlns="http://www.w3.org/1999/xhtml")

        rows = []
        for name, entry, rest, parent in self.rows:
            st = entry.status_wrt(parent)
            rows.append((name, entry, rest, st))

        self.fill_table(dir, alpha_table, rows)

        rows.sort(lambda (name1, ent1, r1, st1),(name2, ent2, r2, st2): -cmp(st1.detail_missing, st2.detail_missing))
        self.fill_table(dir, grandmissing_table, rows)

        rows.sort(lambda (name1, ent1, r1, st1),(name2, ent2, r2, st2): -cmp(st1.incompleteness, st2.incompleteness))
        self.fill_table(dir, incompleteness_table, rows)

        f = open(os.path.join(dir, self.fname()),'w')

        f.write(HEADER+page.unicode().encode("utf8"))

        f.close()

    def navig(self):
        return html.h1(self.title)

class ClassReport(Report):

    descr = "methods+attrs"

    def navig(self):
        return html.p(html.span(self.title,**{'class': 'title'}),
                      "|",mods_report.link(None),"|",cls_report.link(None))

    def grandadd(self, parent):
        parent.grandtotal += self.total
        parent.grandmissing += self.missing

class ModuleReport(Report):

    descr = "module funcs+types+etc"

    granddescr = "module funcs+others and contained types/classes methods+attrs"

    def navig(self):
        return html.p(html.span(self.title,**{'class': 'title'}),
                      "|",mods_report.link(None),"|",cls_report.link(None))    

    notes = ("(): callable, C: type/class")
    
    def grandadd(self, parent):
        if self.status == 'MISSING':
            parent.grandtotal += self.grandtotal
            parent.grandmissing += self.grandmissing
        elif self.status == 'PRESENT':
            parent.grandtotal += self.grandtotal


def delta(expl1, expl2, modnames):

    rep = Report('Modules', fname="modules-index",
                 descr = "modules",
                 granddescr = "of all modules funcs+others and contained types/classes methods+attrs",
                 useshort = True)
    def navig():
        return html.p(html.span('Modules',**{'class': 'title'}),
                      "|",cls_report.link(None))        

    rep.navig = navig
        
    for modname in modnames:

        mod1 = expl1.get_module(modname)
        mod2 = expl2.get_module(modname)

        mod_rep = mod_delta(modname, expl1, mod1, expl2, mod2)

        mod_rep.attach(rep)
        mod_rep.grandadd(rep)

    return rep


def mod_delta(modname, expl1, mod1, expl2, mod2):
    print "; mod %s" % modname
    rep = ModuleReport(modname)

    rep.set_status(mod1, mod2, expl1)

    names = Set()

    names.update(expl1.names(mod1))
    names.update(expl2.names(mod2))    

    names = list(names)
    names.sort()

    for name in names:
        obj1 = expl1.findattr(mod1, name)
        obj2 = expl2.findattr(mod2, name)

        if expl1.is_class(obj1) or expl2.is_class(obj2):
            entry = cls_delta("%s.%s" % (modname, name), expl1, obj1, expl2, obj2)
        else:
            entry = Entry(name)
            entry.set_status(obj1, obj2, expl1)

        kind1 = expl1.get_kind(obj1)
        kind2 = expl2.get_kind(obj2)

        if kind1 == '-':
            kindinf = kind2
        elif kind2 == '-':
            kindinf = kind1
        else:
            if kind1 == kind2:
                kindinf = kind1
            else:
                if kind1 == '_': kind1 = '?'
                if kind2 == '_': kind2 = '?'
                kindinf = "%s/%s" % (kind1, kind2)

        if kindinf == '_':
            kindinf = ''

        entry.attach(rep, kindinf, name=name)
        entry.grandadd(rep)

    return rep


cls_delta_cache = {}

def cls_delta(clsname, expl1, cls1, expl2, cls2):
    cache = cls_delta_cache
    print "; cls %s" % clsname
    try:
        rep = cache[(cls1, cls2)]
        return rep
    except KeyError:
        pass
    
    rep = ClassReport(clsname)
    rep.shortname = clsname.split('.')[1]
    rep.set_status(cls1, cls2, expl1)

    cls1_is_not_a_class = False

    if not expl1.is_class(cls1):
        if cls1 is not NOTFOUND:
            cls1 = NOTFOUND
            cls1_is_not_a_class = True

    if not expl2.is_class(cls2):
        cls2 = NOTFOUND
        assert not cls1_is_not_a_class

    names = Set()

    for cls in expl1.get_mro(cls1):
        names.update(expl1.names(cls))

    for cls in expl2.get_mro(cls2):
        names.update(expl2.names(cls))
    
    names = list(names)
    names.sort()

    for name in names:
        obj1 = expl1.findattr(cls1, name)
        obj2 = expl2.findattr(cls2, name)

        if obj1 is NOTFOUND and obj2 is NOTFOUND:
            continue # spurious :(

        entry = Entry(name)
        if cls1_is_not_a_class:
            entry.status = expl2
        else:
            entry.set_status(obj1, obj2, expl1)

        entry.attach(rep)

    cache[(cls1, cls2)] = rep
        
    return rep

def cls_delta_rep():
    reps = cls_delta_cache.values()
    cls_rep = Report('Types/Classes', fname="types-index",
                     descr = "types/classes",
                     granddescr = "of all types/classes methods+attrs"
                     )

    def navig():
        return html.p(mods_report.link(None),
                      "|",html.span('Types/Classes',**{'class': 'title'}))

    cls_rep.navig = navig
    

    reps.sort(lambda rep1,rep2: cmp(rep1.name, rep2.name))

    for rep in reps:
        cls_rep.add_row(rep, [], name=rep.name)
        cls_rep.total += 1
        cls_rep.missing += rep.status == 'MISSING'
        rep.grandadd(cls_rep)
        
    return cls_rep

#__________________________________________

host_explore = HostExplore()


basic = ['__builtin__', 'types', 'sys']

os_layer = []
for modname in ['posix', 'nt', 'os2', 'mac', 'ce', 'riscos', 'errno', '_socket', 'select', 'thread']:
    if host_explore.get_module(modname) is not NOTFOUND:
        os_layer.append(modname)

mods = """
_codecs
_random
_sre
_weakref
array
binascii
cPickle
cStringIO
struct
datetime
gc
itertools
math
cmath
md5
operator
parser
sha
unicodedata
zipimport
time
""".split()

TO_CHECK = (basic +
            os_layer +
            mods)
TO_CHECK.sort()

def getpypyrevision(cache=[]): 
    try:
        return cache[0]
    except IndexError: 
        import pypy
        import py
        pypydir = py.path.svnwc(pypy.__file__).dirpath()
        rev = pypydir.info().rev 
        cache.append(rev) 
        return rev 

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print "usage: delta.py <dest-dir>"
        print "Then copy delta.css, delta.js to dest-dir if they are not already there"
        sys.exit(0)

    DIR = sys.argv[1]

    
    from pypy.objspace.std.objspace import StdObjSpace

    space = StdObjSpace()
    
    mods_report = delta(ObjSpaceExplore(space), host_explore, TO_CHECK)
    cls_report = cls_delta_rep()

    if not os.path.isdir(DIR):
        os.mkdir(DIR)

    for rep in reports:
        rep.html(DIR)
