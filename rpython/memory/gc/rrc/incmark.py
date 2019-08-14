from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem import rffi
from rpython.memory.gc.rrc.base import RawRefCountBaseGC

class RawRefCountIncMarkGC(RawRefCountBaseGC):

    def _take_snapshot(self, pygclist):
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
        from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_LIGHT
        #
        total_refcnt = 0
        total_objs = 0
        pygchdr = pygclist.c_gc_next
        while pygchdr <> pygclist:
            refcnt = self.gc_as_pyobj(pygchdr).c_ob_refcnt
            if refcnt >= REFCNT_FROM_PYPY_LIGHT:
                refcnt -= REFCNT_FROM_PYPY_LIGHT
            elif refcnt >= REFCNT_FROM_PYPY:
                refcnt -= REFCNT_FROM_PYPY
            total_refcnt += refcnt
            total_objs += 1
            pygchdr = pygchdr.c_gc_next
        self.snapshot_refs = lltype.malloc(self._ADDRARRAY, total_refcnt,
                                           flavor='raw',
                                           track_allocation=False)
        self.snapshot_objs = lltype.malloc(self.PYOBJ_SNAPSHOT, total_objs,
                                           flavor='raw',
                                           track_allocation=False)
        objs_index = 0
        refs_index = 0
        pygchdr = pygclist.c_gc_next
        while pygchdr <> pygclist:
            pyobj = self.gc_as_pyobj(pygchdr)
            refcnt = pyobj.c_ob_refcnt
            if refcnt >= REFCNT_FROM_PYPY_LIGHT:
                refcnt -= REFCNT_FROM_PYPY_LIGHT
            elif refcnt >= REFCNT_FROM_PYPY:
                refcnt -= REFCNT_FROM_PYPY
            obj = self.snapshot_objs[objs_index]
            obj.pyobj = llmemory.cast_ptr_to_adr(pyobj)
            obj.refcnt = refcnt
            obj.refcnt_internal = 0
            obj.refs_index = refs_index
            obj.refs_len = 0
            self.snapshot_curr = obj
            self._take_snapshot_traverse(pyobj)
            objs_index += 1
            refs_index += obj.refs_len
            pygchdr = pygchdr.c_gc_next

    def _take_snapshot_visit(pyobj, self_ptr):
        from rpython.rtyper.annlowlevel import cast_adr_to_nongc_instance
        #
        self_adr = rffi.cast(llmemory.Address, self_ptr)
        self = cast_adr_to_nongc_instance(RawRefCountIncMarkGC, self_adr)
        self._rrc_visit_snapshot_action(pyobj, None)
        return rffi.cast(rffi.INT_real, 0)

    def _take_snapshot_visit_action(self, pyobj, ignore):
        pygchdr = self.pyobj_as_gc(pyobj)
        if pygchdr <> lltype.nullptr(self.PYOBJ_GC_HDR) and \
                pygchdr.c_gc_refs != self.RAWREFCOUNT_REFS_UNTRACKED:
            curr = self.snapshot_curr
            index = curr.refs_index + curr.refs_len
            self.snapshot_refs[index] = llmemory.cast_ptr_to_adr(pyobj)
            curr.refs_len += 1

    def _take_snapshot_traverse(self, pyobj):
        from rpython.rlib.objectmodel import we_are_translated
        from rpython.rtyper.annlowlevel import (cast_nongc_instance_to_adr,
                                                llhelper)
        #
        if we_are_translated():
            callback_ptr = llhelper(self.RAWREFCOUNT_VISIT,
                                    RawRefCountIncMarkGC._take_snapshot_visit)
            self_ptr = rffi.cast(rffi.VOIDP, cast_nongc_instance_to_adr(self))
            self.tp_traverse(pyobj, callback_ptr, self_ptr)
        else:
            self.tp_traverse(pyobj, self._take_snapshot_visit_action, None)

    def _discard_snapshot(self):
        lltype.free(self.snapshot_objs, flavor='raw', track_allocation=False)
        lltype.free(self.snapshot_refs, flavor='raw', track_allocation=False)