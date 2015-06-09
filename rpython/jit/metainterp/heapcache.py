from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.resoperation import rop

class HeapCacheValue(object):
    def __init__(self, box):
        self.box = box
        self.likely_virtual = False
        self.reset_keep_likely_virtual()

    def reset_keep_likely_virtual(self):
        self.known_class = False
        # did we see the allocation during tracing?
        self.seen_allocation = False
        self.is_unescaped = False
        self.nonstandard_virtualizable = False
        self.length = None
        self.dependencies = None

    def __repr__(self):
        return 'HeapCacheValue(%s)' % (self.box, )


class CacheEntry(object):
    def __init__(self):
        # both are {from_value: to_value} dicts
        # the first is for boxes where we did not see the allocation, the
        # second for anything else. the reason that distinction makes sense is
        # because if we saw the allocation, we know it cannot alias with
        # anything else where we saw the allocation.
        self.cache_anything = {}
        self.cache_seen_allocation = {}

    def _clear_cache_on_write(self, seen_allocation_of_target):
        if not seen_allocation_of_target:
            self.cache_seen_allocation.clear()
        self.cache_anything.clear()

    def _getdict(self, value):
        if value.seen_allocation:
            return self.cache_seen_allocation
        else:
            return self.cache_anything

    def do_write_with_aliasing(self, value, fieldvalue):
        self._clear_cache_on_write(value.seen_allocation)
        self._getdict(value)[value] = fieldvalue

    def read(self, value):
        return self._getdict(value).get(value, None)

    def read_now_known(self, value, fieldvalue):
        self._getdict(value)[value] = fieldvalue

    def invalidate_unescaped(self):
        self._invalidate_unescaped(self.cache_anything)
        self._invalidate_unescaped(self.cache_seen_allocation)

    def _invalidate_unescaped(self, d):
        for value in d.keys():
            if not value.is_unescaped:
                del d[value]

class HeapCache(object):
    def __init__(self):
        self.reset()

    def reset(self):
        # maps boxes to values
        self.values = {}
        # store the boxes that contain newly allocated objects, this maps the
        # boxes to a bool, the bool indicates whether or not the object has
        # escaped the trace or not (True means the box never escaped, False
        # means it did escape), its presences in the mapping shows that it was
        # allocated inside the trace
        #if trace_branch:
            #self.new_boxes = {}
        #    pass
        #else:
            #for box in self.new_boxes:
            #    self.new_boxes[box] = False
        #    pass
        #if reset_virtuals:
        #    self.likely_virtuals = {}      # only for jit.isvirtual()
        # Tracks which boxes should be marked as escaped when the key box
        # escapes.
        #self.dependencies = {}

        # heap cache
        # maps descrs to CacheEntry
        self.heap_cache = {}
        # heap array cache
        # maps descrs to {index: {from_value: to_value}} dicts
        self.heap_array_cache = {}

    def reset_keep_likely_virtuals(self):
        for value in self.values.itervalues():
            value.reset_keep_likely_virtual()
        self.heap_cache = {}
        self.heap_array_cache = {}

    def getvalue(self, box):
        value = self.values.get(box, None)
        if not value:
            value = self.values[box] = HeapCacheValue(box)
        return value

    def getvalues(self, boxes):
        return [self.getvalue(box) for box in boxes]

    def invalidate_caches(self, opnum, descr, argboxes):
        self.mark_escaped(opnum, descr, argboxes)
        self.clear_caches(opnum, descr, argboxes)

    def mark_escaped(self, opnum, descr, argboxes):
        if opnum == rop.SETFIELD_GC:
            assert len(argboxes) == 2
            value, fieldvalue = self.getvalues(argboxes)
            if value.is_unescaped and fieldvalue.is_unescaped:
                if value.dependencies is None:
                    value.dependencies = []
                value.dependencies.append(fieldvalue)
            else:
                self._escape(fieldvalue)
        elif opnum == rop.SETARRAYITEM_GC:
            assert len(argboxes) == 3
            value, indexvalue, fieldvalue = self.getvalues(argboxes)
            if value.is_unescaped and fieldvalue.is_unescaped:
                if value.dependencies is None:
                    value.dependencies = []
                value.dependencies.append(fieldvalue)
            else:
                self._escape(fieldvalue)
        elif (opnum == rop.CALL and
              descr.get_extra_info().oopspecindex == descr.get_extra_info().OS_ARRAYCOPY and
              isinstance(argboxes[3], ConstInt) and
              isinstance(argboxes[4], ConstInt) and
              isinstance(argboxes[5], ConstInt) and
              len(descr.get_extra_info().write_descrs_arrays) == 1):
            # ARRAYCOPY with constant starts and constant length doesn't escape
            # its argument
            # XXX really?
            pass
        # GETFIELD_GC, MARK_OPAQUE_PTR, PTR_EQ, and PTR_NE don't escape their
        # arguments
        elif (opnum != rop.GETFIELD_GC and
              opnum != rop.GETFIELD_GC_PURE and
              opnum != rop.MARK_OPAQUE_PTR and
              opnum != rop.PTR_EQ and
              opnum != rop.PTR_NE and
              opnum != rop.INSTANCE_PTR_EQ and
              opnum != rop.INSTANCE_PTR_NE):
            for box in argboxes:
                self._escape_box(box)

    def _escape_box(self, box):
        value = self.values.get(box, None)
        if not value:
            return
        self._escape(value)

    def _escape(self, value):
        value.is_unescaped = False
        value.likely_virtual = False
        deps = value.dependencies
        value.dependencies = None
        if deps is not None:
            for dep in deps:
                self._escape(dep)

    def clear_caches(self, opnum, descr, argboxes):
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETARRAYITEM_GC or
            opnum == rop.SETFIELD_RAW or
            opnum == rop.SETARRAYITEM_RAW or
            opnum == rop.SETINTERIORFIELD_GC or
            opnum == rop.COPYSTRCONTENT or
            opnum == rop.COPYUNICODECONTENT or
            opnum == rop.STRSETITEM or
            opnum == rop.UNICODESETITEM or
            opnum == rop.SETFIELD_RAW or
            opnum == rop.SETARRAYITEM_RAW or
            opnum == rop.SETINTERIORFIELD_RAW or
            opnum == rop.RAW_STORE):
            return
        if (rop._OVF_FIRST <= opnum <= rop._OVF_LAST or
            rop._NOSIDEEFFECT_FIRST <= opnum <= rop._NOSIDEEFFECT_LAST or
            rop._GUARD_FIRST <= opnum <= rop._GUARD_LAST):
            return
        if opnum == rop.CALL or opnum == rop.CALL_LOOPINVARIANT or opnum == rop.COND_CALL:
            effectinfo = descr.get_extra_info()
            ef = effectinfo.extraeffect
            if (ef == effectinfo.EF_LOOPINVARIANT or
                ef == effectinfo.EF_ELIDABLE_CANNOT_RAISE or
                ef == effectinfo.EF_ELIDABLE_OR_MEMORYERROR or
                ef == effectinfo.EF_ELIDABLE_CAN_RAISE):
                return
            # A special case for ll_arraycopy, because it is so common, and its
            # effects are so well defined.
            elif effectinfo.oopspecindex == effectinfo.OS_ARRAYCOPY:
                self._clear_caches_arraycopy(opnum, descr, argboxes, effectinfo)
                return
            else:
                # Only invalidate things that are escaped
                # XXX can do better, only do it for the descrs in the effectinfo
                for descr, cache in self.heap_cache.iteritems():
                    cache.invalidate_unescaped()
                for descr, indices in self.heap_array_cache.iteritems():
                    for cache in indices.itervalues():
                        cache.invalidate_unescaped()
                return

        # XXX not completely sure, but I *think* it is needed to reset() the
        # state at least in the 'CALL_*' operations that release the GIL.  We
        # tried to do only the kind of resetting done by the two loops just
        # above, but hit an assertion in "pypy test_multiprocessing.py".
        self.reset_keep_likely_virtuals()

    def _clear_caches_arraycopy(self, opnum, desrc, argboxes, effectinfo):
        seen_allocation_of_target = self.getvalue(argboxes[2]).seen_allocation
        if (
            isinstance(argboxes[3], ConstInt) and
            isinstance(argboxes[4], ConstInt) and
            isinstance(argboxes[5], ConstInt) and
            len(effectinfo.write_descrs_arrays) == 1
        ):
            descr = effectinfo.write_descrs_arrays[0]
            cache = self.heap_array_cache.get(descr, None)
            srcstart = argboxes[3].getint()
            dststart = argboxes[4].getint()
            length = argboxes[5].getint()
            for i in xrange(length):
                value = self.getarrayitem(
                    argboxes[1],
                    ConstInt(srcstart + i),
                    descr,
                )
                if value is not None:
                    self.setarrayitem(
                        argboxes[2],
                        ConstInt(dststart + i),
                        value,
                        descr,
                    )
                elif cache is not None:
                    try:
                        idx_cache = cache[dststart + i]
                    except KeyError:
                        pass
                    else:
                        idx_cache._clear_cache_on_write(seen_allocation_of_target)
            return
        elif (
            len(effectinfo.write_descrs_arrays) == 1
        ):
            # Fish the descr out of the effectinfo
            cache = self.heap_array_cache.get(effectinfo.write_descrs_arrays[0], None)
            if cache is not None:
                for idx, cache in cache.iteritems():
                    cache._clear_cache_on_write(seen_allocation_of_target)
            return
        self.reset_keep_likely_virtuals()

    def is_class_known(self, box):
        value = self.values.get(box, None)
        if value:
            return value.known_class
        return False

    def class_now_known(self, box):
        self.getvalue(box).known_class = True

    def is_nonstandard_virtualizable(self, box):
        value = self.values.get(box, None)
        if value:
            return value.nonstandard_virtualizable
        return False

    def nonstandard_virtualizables_now_known(self, box):
        self.getvalue(box).nonstandard_virtualizable = True

    def is_unescaped(self, box):
        value = self.values.get(box, None)
        if value:
            return value.is_unescaped
        return False

    def is_likely_virtual(self, box):
        value = self.values.get(box, None)
        if value:
            return value.likely_virtual
        return False

    def new(self, box):
        value = self.getvalue(box)
        value.is_unescaped = True
        value.likely_virtual = True
        value.seen_allocation = True

    def new_array(self, box, lengthbox):
        self.new(box)
        self.arraylen_now_known(box, lengthbox)

    def getfield(self, box, descr):
        value = self.values.get(box, None)
        if value:
            cache = self.heap_cache.get(descr, None)
            if cache:
                tovalue = cache.read(value)
                if tovalue:
                    return tovalue.box
        return None

    def getfield_now_known(self, box, descr, fieldbox):
        value = self.getvalue(box)
        fieldvalue = self.getvalue(fieldbox)
        cache = self.heap_cache.get(descr, None)
        if cache is None:
            cache = self.heap_cache[descr] = CacheEntry()
        cache.read_now_known(value, fieldvalue)

    def setfield(self, box, fieldbox, descr):
        cache = self.heap_cache.get(descr, None)
        if cache is None:
            cache = self.heap_cache[descr] = CacheEntry()
        value = self.getvalue(box)
        fieldvalue = self.getvalue(fieldbox)
        cache.do_write_with_aliasing(value, fieldvalue)

    def getarrayitem(self, box, indexbox, descr):
        if not isinstance(indexbox, ConstInt):
            return None
        value = self.values.get(box, None)
        if value is None:
            return None
        index = indexbox.getint()
        cache = self.heap_array_cache.get(descr, None)
        if cache:
            indexcache = cache.get(index, None)
            if indexcache is not None:
                resvalue = indexcache.read(value)
                if resvalue:
                    return resvalue.box
        return None

    def _get_or_make_array_cache_entry(self, indexbox, descr):
        if not isinstance(indexbox, ConstInt):
            return None
        index = indexbox.getint()
        cache = self.heap_array_cache.setdefault(descr, {})
        indexcache = cache.get(index, None)
        if indexcache is None:
            cache[index] = indexcache = CacheEntry()
        return indexcache


    def getarrayitem_now_known(self, box, indexbox, fieldbox, descr):
        value = self.getvalue(box)
        fieldvalue = self.getvalue(fieldbox)
        indexcache = self._get_or_make_array_cache_entry(indexbox, descr)
        if indexcache:
            indexcache.read_now_known(value, fieldvalue)

    def setarrayitem(self, box, indexbox, fieldbox, descr):
        if not isinstance(indexbox, ConstInt):
            cache = self.heap_array_cache.get(descr, None)
            if cache is not None:
                cache.clear()
            return
        value = self.getvalue(box)
        fieldvalue = self.getvalue(fieldbox)
        indexcache = self._get_or_make_array_cache_entry(indexbox, descr)
        if indexcache:
            indexcache.do_write_with_aliasing(value, fieldvalue)

    def arraylen(self, box):
        value = self.values.get(box, None)
        if value and value.length:
            return value.length.box
        return None

    def arraylen_now_known(self, box, lengthbox):
        value = self.getvalue(box)
        value.length = self.getvalue(lengthbox)

    def replace_box(self, oldbox, newbox):
        value = self.values.get(oldbox, None)
        if value is None:
            return
        value.box = newbox
        self.values[newbox] = value
