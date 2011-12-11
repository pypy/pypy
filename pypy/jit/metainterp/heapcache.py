from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp.resoperation import rop


class HeapCache(object):
    def __init__(self):
        self.reset()

    def reset(self):
        # contains boxes where the class is already known
        self.known_class_boxes = {}
        # store the boxes that contain newly allocated objects, this maps the
        # boxes to a bool, the bool indicates whether or not the object has
        # escaped the trace or not (True means the box never escaped, False
        # means it did escape), its presences in the mapping shows that it was
        # allocated inside the trace
        self.new_boxes = {}
        # Tracks which boxes should be marked as escaped when the key box
        # escapes.
        self.dependencies = {}
        # contains frame boxes that are not virtualizables
        self.nonstandard_virtualizables = {}
        # heap cache
        # maps descrs to {from_box, to_box} dicts
        self.heap_cache = {}
        # heap array cache
        # maps descrs to {index: {from_box: to_box}} dicts
        self.heap_array_cache = {}
        # cache the length of arrays
        self.length_cache = {}

    def invalidate_caches(self, opnum, descr, argboxes):
        self.mark_escaped(opnum, argboxes)
        self.clear_caches(opnum, descr, argboxes)

    def mark_escaped(self, opnum, argboxes):
        if opnum == rop.SETFIELD_GC:
            assert len(argboxes) == 2
            box, valuebox = argboxes
            if self.is_unescaped(box) and self.is_unescaped(valuebox):
                self.dependencies.setdefault(box, []).append(valuebox)
            else:
                self._escape(valuebox)
        elif opnum == rop.SETARRAYITEM_GC:
            assert len(argboxes) == 3
            box, indexbox, valuebox = argboxes
            if self.is_unescaped(box) and self.is_unescaped(valuebox):
                self.dependencies.setdefault(box, []).append(valuebox)
            else:
                self._escape(valuebox)
        # GETFIELD_GC, MARK_OPAQUE_PTR, PTR_EQ, and PTR_NE don't escape their
        # arguments
        elif (opnum != rop.GETFIELD_GC and
              opnum != rop.MARK_OPAQUE_PTR and
              opnum != rop.PTR_EQ and
              opnum != rop.PTR_NE):
            idx = 0
            for box in argboxes:
                # setarrayitem_gc don't escape its first argument
                if not (idx == 0 and opnum in [rop.SETARRAYITEM_GC]):
                    self._escape(box)
                idx += 1

    def _escape(self, box):
        if box in self.new_boxes:
            self.new_boxes[box] = False
        if box in self.dependencies:
            deps = self.dependencies[box]
            del self.dependencies[box]
            for dep in deps:
                self._escape(dep)

    def clear_caches(self, opnum, descr, argboxes):
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETARRAYITEM_GC or
            opnum == rop.SETFIELD_RAW or
            opnum == rop.SETARRAYITEM_RAW or
            opnum == rop.SETINTERIORFIELD_GC or
            opnum == rop.COPYSTRCONTENT or
            opnum == rop.COPYUNICODECONTENT):
            return
        if rop._OVF_FIRST <= opnum <= rop._OVF_LAST:
            return
        if rop._NOSIDEEFFECT_FIRST <= opnum <= rop._NOSIDEEFFECT_LAST:
            return
        if opnum == rop.CALL or opnum == rop.CALL_LOOPINVARIANT:
            effectinfo = descr.get_extra_info()
            ef = effectinfo.extraeffect
            if (ef == effectinfo.EF_LOOPINVARIANT or
                ef == effectinfo.EF_ELIDABLE_CANNOT_RAISE or
                ef == effectinfo.EF_ELIDABLE_CAN_RAISE):
                return
            # A special case for ll_arraycopy, because it is so common, and its
            # effects are so well defined.
            elif effectinfo.oopspecindex == effectinfo.OS_ARRAYCOPY:
                # The destination box
                if argboxes[2] in self.new_boxes:
                    # XXX: no descr here so we invalidate any of them, not just
                    # of the correct type
                    # XXX: in theory the indices of the copy could be looked at
                    # as well
                    for descr, cache in self.heap_array_cache.iteritems():
                        for idx, cache in cache.iteritems():
                            for frombox in cache.keys():
                                if frombox not in self.new_boxes:
                                    del cache[frombox]
                    return

        self.heap_cache.clear()
        self.heap_array_cache.clear()

    def is_class_known(self, box):
        return box in self.known_class_boxes

    def class_now_known(self, box):
        self.known_class_boxes[box] = None

    def is_nonstandard_virtualizable(self, box):
        return box in self.nonstandard_virtualizables

    def nonstandard_virtualizables_now_known(self, box):
        self.nonstandard_virtualizables[box] = None

    def is_unescaped(self, box):
        return self.new_boxes.get(box, False)

    def new(self, box):
        self.new_boxes[box] = True

    def new_array(self, box, lengthbox):
        self.new(box)
        self.arraylen_now_known(box, lengthbox)

    def getfield(self, box, descr):
        d = self.heap_cache.get(descr, None)
        if d:
            tobox = d.get(box, None)
            if tobox:
                return tobox
        return None

    def getfield_now_known(self, box, descr, fieldbox):
        self.heap_cache.setdefault(descr, {})[box] = fieldbox

    def setfield(self, box, descr, fieldbox):
        d = self.heap_cache.get(descr, None)
        new_d = self._do_write_with_aliasing(d, box, fieldbox)
        self.heap_cache[descr] = new_d

    def _do_write_with_aliasing(self, d, box, fieldbox):
        # slightly subtle logic here
        # a write to an arbitrary box, all other boxes can alias this one
        if not d or box not in self.new_boxes:
            # therefore we throw away the cache
            return {box: fieldbox}
        # the object we are writing to is freshly allocated
        # only remove some boxes from the cache
        new_d = {}
        for frombox, tobox in d.iteritems():
            # the other box is *also* freshly allocated
            # therefore frombox and box *must* contain different objects
            # thus we can keep it in the cache
            if frombox in self.new_boxes:
                new_d[frombox] = tobox
        new_d[box] = fieldbox
        return new_d

    def getarrayitem(self, box, descr, indexbox):
        if not isinstance(indexbox, ConstInt):
            return
        index = indexbox.getint()
        cache = self.heap_array_cache.get(descr, None)
        if cache:
            indexcache = cache.get(index, None)
            if indexcache is not None:
                return indexcache.get(box, None)

    def getarrayitem_now_known(self, box, descr, indexbox, valuebox):
        if not isinstance(indexbox, ConstInt):
            return
        index = indexbox.getint()
        cache = self.heap_array_cache.setdefault(descr, {})
        indexcache = cache.get(index, None)
        if indexcache is not None:
            indexcache[box] = valuebox
        else:
            cache[index] = {box: valuebox}

    def setarrayitem(self, box, descr, indexbox, valuebox):
        if not isinstance(indexbox, ConstInt):
            cache = self.heap_array_cache.get(descr, None)
            if cache is not None:
                cache.clear()
            return
        index = indexbox.getint()
        cache = self.heap_array_cache.setdefault(descr, {})
        indexcache = cache.get(index, None)
        cache[index] = self._do_write_with_aliasing(indexcache, box, valuebox)

    def arraylen(self, box):
        return self.length_cache.get(box, None)

    def arraylen_now_known(self, box, lengthbox):
        self.length_cache[box] = lengthbox

    def _replace_box(self, d, oldbox, newbox):
        new_d = {}
        for frombox, tobox in d.iteritems():
            if frombox is oldbox:
                frombox = newbox
            if tobox is oldbox:
                tobox = newbox
            new_d[frombox] = tobox
        return new_d

    def replace_box(self, oldbox, newbox):
        for descr, d in self.heap_cache.iteritems():
            self.heap_cache[descr] = self._replace_box(d, oldbox, newbox)
        for descr, d in self.heap_array_cache.iteritems():
            for index, cache in d.iteritems():
                d[index] = self._replace_box(cache, oldbox, newbox)
        self.length_cache = self._replace_box(self.length_cache, oldbox, newbox)
