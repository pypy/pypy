import os, py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from rpython.memory.gc.test.test_direct import BaseDirectGCTest
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
PYOBJ_HDR = IncrementalMiniMarkGC.PYOBJ_HDR
PYOBJ_HDR_PTR = IncrementalMiniMarkGC.PYOBJ_HDR_PTR
RAWREFCOUNT_VISIT = IncrementalMiniMarkGC.RAWREFCOUNT_VISIT
PYOBJ_GC_HDR = IncrementalMiniMarkGC.PYOBJ_GC_HDR
PYOBJ_GC_HDR_PTR = IncrementalMiniMarkGC.PYOBJ_GC_HDR_PTR

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S',
                         ('x', lltype.Signed),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))


class TestRawRefCount(BaseDirectGCTest):
    GCClass = IncrementalMiniMarkGC

    def setup_method(self, method):
        BaseDirectGCTest.setup_method(self, method)

        self.trigger = []
        self.gcobjs = []
        self.pyobjs = []
        self.pyobj_refs = []

        def rawrefcount_tp_traverse(obj, callback, args):
            refs = self.pyobj_refs[self.pyobjs.index(obj)]
            for ref in refs:
                callback(ref, args)

        def rawrefcount_gc_as_pyobj(gc):
            return self.pyobjs[self.gcobjs.index(gc)]

        def rawrefcount_pyobj_as_gc(pyobj):
            return self.gcobjs[self.pyobjs.index(pyobj)]

        def rawrefcount_finalizer_type(gc):
            return 0

        self.pyobj_list = lltype.malloc(PYOBJ_GC_HDR_PTR.TO, flavor='raw',
                                        immortal=True)
        self.pyobj_list.c_gc_next = self.pyobj_list
        self.pyobj_list.c_gc_prev = self.pyobj_list
        self.gc.rawrefcount_init(lambda: self.trigger.append(1),
                                 rawrefcount_tp_traverse,
                                 llmemory.cast_ptr_to_adr(self.pyobj_list),
                                 rawrefcount_gc_as_pyobj,
                                 rawrefcount_pyobj_as_gc,
                                 rawrefcount_finalizer_type)

    def _collect(self, major, expected_trigger=0):
        if major:
            self.gc.collect()
        else:
            self.gc._minor_collection()
        count1 = len(self.trigger)
        self.gc.rrc_invoke_callback()
        count2 = len(self.trigger)
        # TODO: fix assertion
        # assert count2 - count1 == expected_trigger

    def _rawrefcount_addref(self, pyobj_from, pyobj_to):
        refs = self.pyobj_refs[self.pyobjs.index(pyobj_from)]
        refs.append(pyobj_to)
        pyobj_to.c_ob_refcnt += 1

    def _rawrefcount_pypyobj(self, intval, rooted=False, create_old=True):
        p1 = self.malloc(S)
        p1.x = intval

        if create_old:
            self.stackroots.append(p1)
            self._collect(major=False)
            p1 = self.stackroots.pop()
        if rooted:
            self.stackroots.append(p1)
        p1ref = lltype.cast_opaque_ptr(llmemory.GCREF, p1)

        def check_alive():
            p1 = lltype.cast_opaque_ptr(lltype.Ptr(S), p1ref)
            assert p1.x == intval

        return p1, p1ref, check_alive

    def _rawrefcount_pyobj(self, create_immortal=False):
        r1 = lltype.malloc(PYOBJ_HDR, flavor='raw',
                           immortal=create_immortal)
        r1.c_ob_refcnt = 0
        r1.c_ob_pypy_link = 0
        r1addr = llmemory.cast_ptr_to_adr(r1)

        r1gc = lltype.malloc(PYOBJ_GC_HDR, flavor='raw',
                             immortal=True)
        r1gc.c_gc_next = self.pyobj_list
        r1gc.c_gc_prev = self.pyobj_list.c_gc_prev
        r1gc.c_gc_prev.c_gc_next = r1gc
        self.pyobj_list.c_gc_prev = r1gc

        self.gcobjs.append(r1gc)
        self.pyobjs.append(r1)
        self.pyobj_refs.append([])

        def check_alive(extra_refcount):
            assert r1.c_ob_refcnt == extra_refcount

        return r1, r1addr, check_alive

    def _rawrefcount_pair(self, intval, is_light=False, is_pyobj=False,
                          create_old=False, create_immortal=False,
                          rooted=False, force_external=False):
        if is_light:
            rc = REFCNT_FROM_PYPY_LIGHT
        else:
            rc = REFCNT_FROM_PYPY

        if create_immortal:
            p1 = lltype.malloc(S, immortal=True)
        else:
            saved = self.gc.nonlarge_max
            try:
                if force_external:
                    self.gc.nonlarge_max = 1
                p1 = self.malloc(S)
            finally:
                self.gc.nonlarge_max = saved
        p1.x = intval
        if create_immortal:
            self.consider_constant(p1)
        elif create_old:
            self.stackroots.append(p1)
            self._collect(major=False)
            p1 = self.stackroots.pop()
        if rooted:
            self.stackroots.append(p1)
        p1ref = lltype.cast_opaque_ptr(llmemory.GCREF, p1)
        r1 = lltype.malloc(PYOBJ_HDR, flavor='raw',
                           immortal=create_immortal)
        r1.c_ob_refcnt = rc
        r1.c_ob_pypy_link = 0
        r1addr = llmemory.cast_ptr_to_adr(r1)

        r1gc = lltype.malloc(PYOBJ_GC_HDR, flavor='raw',
                             immortal=True)
        r1gc.c_gc_next = self.pyobj_list
        r1gc.c_gc_prev = self.pyobj_list.c_gc_prev
        r1gc.c_gc_prev.c_gc_next = r1gc
        self.pyobj_list.c_gc_prev = r1gc

        self.gcobjs.append(r1gc)
        self.pyobjs.append(r1)
        self.pyobj_refs.append([])

        if is_pyobj:
            assert not is_light
            self.gc.rawrefcount_create_link_pyobj(p1ref, r1addr)
        else:
            self.gc.rawrefcount_create_link_pypy(p1ref, r1addr)
        assert r1.c_ob_refcnt == rc
        assert r1.c_ob_pypy_link != 0

        def check_alive(extra_refcount):
            assert r1.c_ob_refcnt == rc + extra_refcount
            assert r1.c_ob_pypy_link != 0
            p1ref = self.gc.rawrefcount_to_obj(r1addr)
            p1 = lltype.cast_opaque_ptr(lltype.Ptr(S), p1ref)
            assert p1.x == intval
            if not is_pyobj:
                assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
            else:
                assert self.gc.rawrefcount_from_obj(p1ref) == llmemory.NULL
            return p1
        return p1, p1ref, r1, r1addr, check_alive

    def test_rawrefcount_objects_basic(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        p2 = self.malloc(S)
        p2.x = 84
        p2ref = lltype.cast_opaque_ptr(llmemory.GCREF, p2)
        r2 = lltype.malloc(PYOBJ_HDR_PTR.TO, flavor='raw')
        r2.c_ob_refcnt = 1
        r2.c_ob_pypy_link = 0
        r2addr = llmemory.cast_ptr_to_adr(r2)
        # p2 and r2 are not linked
        assert r1.c_ob_pypy_link != 0
        assert r2.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
        assert self.gc.rawrefcount_from_obj(p2ref) == llmemory.NULL
        assert self.gc.rawrefcount_to_obj(r1addr) == p1ref
        assert self.gc.rawrefcount_to_obj(r2addr) == lltype.nullptr(
            llmemory.GCREF.TO)
        lltype.free(r1, flavor='raw')
        lltype.free(r2, flavor='raw')

    def test_rawrefcount_objects_collection_survives_from_raw(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        r1.c_ob_refcnt += 1
        self._collect(major=False)
        check_alive(+1)
        self._collect(major=True)
        check_alive(+1)
        r1.c_ob_refcnt -= 1
        self._collect(major=False)
        p1 = check_alive(0)
        self._collect(major=True)
        py.test.raises(RuntimeError, "r1.c_ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()
        # TODO: fix assertion
        # assert self.trigger == []
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL

    def test_rawrefcount_dies_quickly(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        self._collect(major=False)
        if old:
            check_alive(0)
            self._collect(major=True)
        py.test.raises(RuntimeError, "r1.c_ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()

    def test_rawrefcount_objects_collection_survives_from_obj(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=True, create_old=old))
        check_alive(0)
        self.stackroots.append(p1)
        self._collect(major=False)
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
        p1 = self.stackroots.pop()
        self._collect(major=False)
        check_alive(0)
        assert p1.x == 42
        self._collect(major=True)
        py.test.raises(RuntimeError, "r1.c_ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()

    def test_rawrefcount_objects_basic_old(self):
        self.test_rawrefcount_objects_basic(old=True)
    def test_rawrefcount_objects_collection_survives_from_raw_old(self):
        self.test_rawrefcount_objects_collection_survives_from_raw(old=True)
    def test_rawrefcount_dies_quickly_old(self):
        self.test_rawrefcount_dies_quickly(old=True)
    def test_rawrefcount_objects_collection_survives_from_obj_old(self):
        self.test_rawrefcount_objects_collection_survives_from_obj(old=True)

    def test_pypy_nonlight_survives_from_raw(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        r1.c_ob_refcnt += 1
        self._collect(major=False)
        check_alive(+1)
        self._collect(major=True)
        check_alive(+1)
        r1.c_ob_refcnt -= 1
        self._collect(major=False)
        p1 = check_alive(0)
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1       # in the pending list
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        assert self.gc.rawrefcount_next_dead() == llmemory.NULL
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nonlight_survives_from_obj(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        self.stackroots.append(p1)
        self._collect(major=False)
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
        p1 = self.stackroots.pop()
        self._collect(major=False)
        check_alive(0)
        assert p1.x == 42
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nonlight_dies_quickly(self, old=False):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_light=False, create_old=old))
        check_alive(0)
        if old:
            self._collect(major=False)
            check_alive(0)
            self._collect(major=True, expected_trigger=1)
        else:
            self._collect(major=False, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nonlight_survives_from_raw_old(self):
        self.test_pypy_nonlight_survives_from_raw(old=True)
    def test_pypy_nonlight_survives_from_obj_old(self):
        self.test_pypy_nonlight_survives_from_obj(old=True)
    def test_pypy_nonlight_dies_quickly_old(self):
        self.test_pypy_nonlight_dies_quickly(old=True)

    @py.test.mark.parametrize('external', [False, True])
    def test_pyobject_pypy_link_dies_on_minor_collection(self, external):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, force_external=external))
        check_alive(0)
        r1.c_ob_refcnt += 1            # the pyobject is kept alive
        self._collect(major=False)
        assert r1.c_ob_refcnt == 1     # refcnt dropped to 1
        assert r1.c_ob_pypy_link == 0  # detached
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old,external', [
        (False, False), (True, False), (False, True)])
    def test_pyobject_dies(self, old, external):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, create_old=old,
                                   force_external=external))
        check_alive(0)
        if old:
            self._collect(major=False)
            check_alive(0)
            self._collect(major=True, expected_trigger=1)
        else:
            self._collect(major=False, expected_trigger=1)
        assert r1.c_ob_refcnt == 1     # refcnt 1, in the pending list
        assert r1.c_ob_pypy_link == 0  # detached
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    @py.test.mark.parametrize('old,external', [
        (False, False), (True, False), (False, True)])
    def test_pyobject_survives_from_obj(self, old, external):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_pyobj=True, create_old=old,
                                   force_external=external))
        check_alive(0)
        self.stackroots.append(p1)
        self._collect(major=False)
        check_alive(0)
        self._collect(major=True)
        check_alive(0)
        p1 = self.stackroots.pop()
        self._collect(major=False)
        check_alive(0)
        assert p1.x == 42
        # TODO: fix assertion
        # assert self.trigger == []
        self._collect(major=True, expected_trigger=1)
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.c_ob_refcnt == 1
        assert r1.c_ob_pypy_link == 0
        assert self.gc.rawrefcount_next_dead() == r1addr
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pyobject_attached_to_prebuilt_obj(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, create_immortal=True))
        check_alive(0)
        self._collect(major=True)
        check_alive(0)

    dot_dir = os.path.join(os.path.realpath(os.path.dirname(__file__)), "dot")
    dot_files = [file for file in os.listdir(dot_dir) if file.endswith(".dot")]
    dot_files.sort()

    @py.test.mark.dont_track_allocations('intentionally keep objects alive, '
                                         'because we do the checks ourselves')
    @py.test.mark.parametrize("file", dot_files)
    def test_dots(self, file):
        from rpython.memory.gc.test.dot import pydot
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT

        class Node:
            def __init__(self, info):
                self.info = info

        class CPythonNode(Node):
            def __init__(self, r, raddr, check_alive, info):
                self.r = r
                self.raddr = raddr
                self.check_alive = check_alive
                self.info = info

        class PyPyNode(Node):
            def __init__(self, p, pref, check_alive, info):
                self.p = p
                self.pref = pref
                self.check_alive = check_alive
                self.info = info

        class BorderNode(Node):
            def __init__(self, p, pref, r, raddr, check_alive, info):
                self.p = p
                self.pref = pref
                self.r = r
                self.raddr = raddr
                self.check_alive = check_alive
                self.info = info

        class NodeInfo:
            def __init__(self, type, alive, ext_refcnt, finalizer, resurrect):
                self.type = type
                self.alive = alive
                self.ext_refcnt = ext_refcnt
                self.finalizer = finalizer
                self.resurrect = resurrect

        path = os.path.join(self.dot_dir, file)
        g = pydot.graph_from_dot_file(path)[0]
        nodes = {}

        # create objects from graph (always create old to prevent moving)
        i = 0
        for n in g.get_nodes():
            name = n.get_name()
            attr = n.obj_dict['attributes']
            type = attr['type']
            alive = attr['alive'] == "y"
            rooted = attr['rooted'] == "y" if 'rooted' in attr else False
            ext_refcnt = int(attr['ext_refcnt']) if 'ext_refcnt' in attr else 0
            finalizer = attr['finalizer'] if 'finalizer' in attr else None
            resurrect = attr['resurrect'] if 'resurrect' in attr else None
            info = NodeInfo(type, alive, ext_refcnt, finalizer, resurrect)
            if type == "C":
                r, raddr, check_alive = self._rawrefcount_pyobj()
                r.c_ob_refcnt += ext_refcnt
                nodes[name] = CPythonNode(r, raddr, check_alive, info)
            elif type == "P":
                p, pref, check_alive = \
                    self._rawrefcount_pypyobj(42 + i, rooted=rooted,
                                              create_old=True)
                nodes[name] = PyPyNode(p, pref, check_alive, info)
                i += 1
            elif type == "B":
                p, pref, r, raddr, check_alive =\
                    self._rawrefcount_pair(42 + i, rooted=rooted,
                                           create_old=True)
                r.c_ob_refcnt += ext_refcnt
                nodes[name] = BorderNode(p, pref, r, raddr, check_alive, info)
                i += 1

        # add references between objects from graph
        for e in g.get_edges():
            source = nodes[e.get_source()]
            dest = nodes[e.get_destination()]
            if source.info.type == "C" or dest.info.type == "C":
                self._rawrefcount_addref(source.r, dest.r)
                if source.info.alive:
                    dest.info.ext_refcnt += 1
            elif source.info.type == "P" or dest.info.type == "P":
                if llmemory.cast_ptr_to_adr(source.p.next) == llmemory.NULL:
                    source.p.next = dest.p
                elif llmemory.cast_ptr_to_adr(source.p.prev) == llmemory.NULL:
                    source.p.prev = dest.p
                else:
                    assert False  # only 2 refs supported from pypy obj

        # quick self check, if traverse works properly
        dests_by_source = {}
        for e in g.get_edges():
            source = nodes[e.get_source()]
            dest = nodes[e.get_destination()]
            if source.info.type == "C" or dest.info.type == "C":
                if not dests_by_source.has_key(source):
                    dests_by_source[source] = []
                dests_by_source[source].append(dest.r)
        for source in dests_by_source:
            dests_target = dests_by_source[source]
            def append(pyobj, ignore):
                dests_target.remove(pyobj)
            self.gc.rrc_tp_traverse(source.r, append, None)
            assert len(dests_target) == 0

        def cleanup():
            # do cleanup after collection (clear all dead pyobjects)
            def decref_children(pyobj):
                self.gc.rrc_tp_traverse(pyobj, decref, None)

            def decref(pyobj, ignore):
                pyobj.c_ob_refcnt -= 1
                if pyobj.c_ob_refcnt == 0:
                    gchdr = self.gc.rrc_pyobj_as_gc(pyobj)
                    next = gchdr.c_gc_next
                    next.c_gc_prev = gchdr.c_gc_prev
                    gchdr.c_gc_prev.c_gc_next = next
                    decref_children(pyobj)
                    self.pyobjs[self.pyobjs.index(pyobj)] = \
                        lltype.nullptr(PYOBJ_HDR_PTR.TO)
                    lltype.free(pyobj, flavor='raw')

            next_dead = self.gc.rawrefcount_next_dead()
            while next_dead <> llmemory.NULL:
                pyobj = llmemory.cast_adr_to_ptr(next_dead,
                                                 self.gc.PYOBJ_HDR_PTR)
                print "nextdead:", pyobj, "refcnt:", pyobj.c_ob_refcnt
                decref(pyobj, None)
                next_dead = self.gc.rawrefcount_next_dead()

            # TODO: call finalizers here and during the next collection it
            #       will be checked if the CI is really trash

            next_dead = self.gc.rawrefcount_cyclic_garbage_head()
            while next_dead <> llmemory.NULL:
                pyobj = llmemory.cast_adr_to_ptr(next_dead,
                                                 self.gc.PYOBJ_HDR_PTR)
                pyobj.c_ob_refcnt += 1

                def clear(pyobj_to, pyobj_from):
                    refs = self.pyobj_refs[self.pyobjs.index(pyobj_from)]
                    refs.remove(pyobj_to)
                    decref(pyobj_to, None)

                self.gc.rrc_tp_traverse(pyobj, clear, pyobj)

                decref(pyobj, None)

                curr = llmemory.cast_adr_to_int(next_dead)
                next_dead = self.gc.rawrefcount_cyclic_garbage_head()

                if llmemory.cast_adr_to_int(next_dead) == curr:
                    self.gc.rawrefcount_cyclic_garbage_remove()
                    next_dead = self.gc.rawrefcount_cyclic_garbage_head()

        # do a collection to find cyclic isolates
        self.gc.collect()

        self.gc.rrc_invoke_callback()
        if self.trigger <> []:
            cleanup()

        # now do another collection, to clean up cyclic trash
        # TODO: maybe optimize, so that we don't need another major collection
        self.gc.collect()

        self.gc.rrc_invoke_callback()
        if self.trigger <> []:
            cleanup()

        # check livelihood of objects, according to graph
        for name in nodes:
            n = nodes[name]
            if n.info.alive:
                if n.info.type == "P":
                    n.check_alive()
                else:
                    n.check_alive(n.info.ext_refcnt)
            else:
                if n.info.type == "P":
                    py.test.raises(RuntimeError, "n.p.x")  # dead
                else:
                    py.test.raises(RuntimeError, "n.r.c_ob_refcnt")  # dead
