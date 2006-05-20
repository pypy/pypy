"""
Reference tracker for lltype data structures.
"""

import autopath, sys, os
import gc
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gcheader import header2obj
from pypy.translator.tool.reftracker import BaseRefTrackerPage, MARKER
from pypy.tool.uid import uid


class LLRefTrackerPage(BaseRefTrackerPage):

    def formatobject(self, o):
        lines = []
        for name, value in self.enum_content(o):
            if not isinstance(value, str):
                value = '0x%x' % uid(value)
            lines.append('%s = %s' % (name, value))
        s = '\n'.join(lines)
        t = shorttypename(lltype.typeOf(o))
        return t, s, ''

    def get_referrers(self, o):
        return []    # not implemented

    def get_referents(self, o):
        for name, value in self.enum_content(o):
            if not isinstance(value, str):
                yield value

    def edgelabel(self, o1, o2):
        slst = []
        for name, value in self.enum_content(o1):
            if value is o2:
                slst.append(name)
        return '/'.join(slst)

    def enum_content(cls, o, name=''):
        T = lltype.typeOf(o)
        if isinstance(T, lltype.Struct):
            try:
                gcobjptr = header2obj[o]
                fmt = '(%s)'
            except KeyError:
                gcobjptr = None
                fmt = '%s'
            for name in T._names:
                for name, value in cls.enum_content(getattr(o, name), name):
                    yield fmt % (name,), value
            if gcobjptr:
                GCT = lltype.typeOf(gcobjptr)
                yield 'header of', '<%s>' % (shorttypename(GCT.TO),)
                for sub in cls.enum_content(gcobjptr._obj):
                    yield sub
        elif isinstance(T, lltype.Array):
            for index, o1 in enumerate(o.items):
                for sub in cls.enum_content(o1, str(index)):
                    yield sub
        elif isinstance(T, lltype.Ptr):
            if not o:
                yield name, 'null'
            else:
                yield name, o._obj
        elif isinstance(T, lltype.OpaqueType) and hasattr(o, 'container'):
            T = lltype.typeOf(o.container)
            yield 'container', '<%s>' % (shorttypename(T),)
            for sub in cls.enum_content(o.container, name):
                yield sub
        elif T == llmemory.Address:
            if not o:
                yield name, 'NULL'
            else:
                addrof = o.get()
                T1 = lltype.typeOf(addrof)
                if (isinstance(T1, lltype.Ptr) and
                    isinstance(T1.TO, lltype.Struct) and
                    addrof._obj in header2obj):
                    yield name + ' @hdr', addrof._obj
                else:
                    yield name + ' @', o.ob._obj
                    if o.offset:
                        yield '... offset', str(o.offset)
        else:
            yield name, str(o)
    enum_content = classmethod(enum_content)

def shorttypename(T):
    return '%s %s' % (T.__class__.__name__, getattr(T, '__name__', ''))


def track(*ll_objects):
    """Invoke a dot+pygame object reference tracker."""
    lst = [MARKER]
    for ll_object in ll_objects:
        if isinstance(lltype.typeOf(ll_object), lltype.Ptr):
            ll_object = ll_object._obj
        lst.append(ll_object)
    if len(ll_objects) == 1:
        # auto-expand one level
        for name, value in LLRefTrackerPage.enum_content(ll_objects[0]):
            if not isinstance(value, str):
                lst.append(value)
    page = LLRefTrackerPage(lst)
    page.display()


if __name__ == '__main__':
    try:
        sys.path.remove(os.getcwd())
    except ValueError:
        pass
    T = lltype.GcArray(lltype.Signed)
    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('t', lltype.Ptr(T)),
                                  ('next', lltype.Ptr(S))))
    s = lltype.malloc(S)
    s.next = lltype.malloc(S)
    s.next.t = lltype.malloc(T, 5)
    s.next.t[1] = 123
    track(s)
