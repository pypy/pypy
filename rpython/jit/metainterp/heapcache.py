from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.resoperation import rop


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

        # replace_box is called surprisingly often, therefore it's not efficient
        # to go over all the dicts and fix them.
        # instead, these two dicts are kept, and a replace_box adds an entry to
        # each of them.
        # every time one of the dicts heap_cache, heap_array_cache, length_cache
        # is accessed, suitable indirections need to be performed

        # this looks all very subtle, but in practice the patterns of
        # replacements should not be that complex. Usually a box is replaced by
        # a const, once. Also, if something goes wrong, the effect is that less
        # caching than possible is done, which is not a huge problem.
        self.input_indirections = {}
        self.output_indirections = {}

    def _input_indirection(self, box):
        return self.input_indirections.get(box, box)

    def _output_indirection(self, box):
        return self.output_indirections.get(box, box)

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
              opnum != rop.PTR_NE and
              opnum != rop.INSTANCE_PTR_EQ and
              opnum != rop.INSTANCE_PTR_NE):
            idx = 0
            for box in argboxes:
                # setarrayitem_gc don't escape its first argument
                if not (idx == 0 and opnum in [rop.SETARRAYITEM_GC]):
                    self._escape(box)
                idx += 1

    def _escape(self, box):
        if box in self.new_boxes:
            self.new_boxes[box] = False
        try:
            deps = self.dependencies.pop(box)
        except KeyError:
            pass
        else:
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
        if (rop._OVF_FIRST <= opnum <= rop._OVF_LAST or
            rop._NOSIDEEFFECT_FIRST <= opnum <= rop._NOSIDEEFFECT_LAST or
            rop._GUARD_FIRST <= opnum <= rop._GUARD_LAST):
            return
        if opnum == rop.CALL or opnum == rop.CALL_LOOPINVARIANT or opnum == rop.COND_CALL:
            effectinfo = descr.get_extra_info()
            ef = effectinfo.extraeffect
            if (ef == effectinfo.EF_LOOPINVARIANT or
                ef == effectinfo.EF_ELIDABLE_CANNOT_RAISE or
                ef == effectinfo.EF_ELIDABLE_CAN_RAISE):
                return
            # A special case for ll_arraycopy, because it is so common, and its
            # effects are so well defined.
            elif effectinfo.oopspecindex == effectinfo.OS_ARRAYCOPY:
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
                            if argboxes[2] in self.new_boxes:
                                try:
                                    idx_cache = cache[dststart + i]
                                except KeyError:
                                    pass
                                else:
                                    for frombox in idx_cache.keys():
                                        if not self.is_unescaped(frombox):
                                            del idx_cache[frombox]
                            else:
                                cache[dststart + i].clear()
                    return
                elif (
                    argboxes[2] in self.new_boxes and
                    len(effectinfo.write_descrs_arrays) == 1
                ):
                    # Fish the descr out of the effectinfo
                    cache = self.heap_array_cache.get(effectinfo.write_descrs_arrays[0], None)
                    if cache is not None:
                        for idx, cache in cache.iteritems():
                            for frombox in cache.keys():
                                if not self.is_unescaped(frombox):
                                    del cache[frombox]
                    return
            else:
                # Only invalidate things that are either escaped or arguments
                for descr, boxes in self.heap_cache.iteritems():
                    for box in boxes.keys():
                        if not self.is_unescaped(box) or box in argboxes:
                            del boxes[box]
                for descr, indices in self.heap_array_cache.iteritems():
                    for boxes in indices.itervalues():
                        for box in boxes.keys():
                            if not self.is_unescaped(box) or box in argboxes:
                                del boxes[box]
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
        box = self._input_indirection(box)
        d = self.heap_cache.get(descr, None)
        if d:
            tobox = d.get(box, None)
            return self._output_indirection(tobox)
        return None

    def getfield_now_known(self, box, descr, fieldbox):
        box = self._input_indirection(box)
        fieldbox = self._input_indirection(fieldbox)
        self.heap_cache.setdefault(descr, {})[box] = fieldbox

    def setfield(self, box, fieldbox, descr):
        d = self.heap_cache.get(descr, None)
        new_d = self._do_write_with_aliasing(d, box, fieldbox)
        self.heap_cache[descr] = new_d

    def _do_write_with_aliasing(self, d, box, fieldbox):
        box = self._input_indirection(box)
        fieldbox = self._input_indirection(fieldbox)
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

    def getarrayitem(self, box, indexbox, descr):
        if not isinstance(indexbox, ConstInt):
            return
        box = self._input_indirection(box)
        index = indexbox.getint()
        cache = self.heap_array_cache.get(descr, None)
        if cache:
            indexcache = cache.get(index, None)
            if indexcache is not None:
                return self._output_indirection(indexcache.get(box, None))

    def getarrayitem_now_known(self, box, indexbox, valuebox, descr):
        if not isinstance(indexbox, ConstInt):
            return
        box = self._input_indirection(box)
        valuebox = self._input_indirection(valuebox)
        index = indexbox.getint()
        cache = self.heap_array_cache.setdefault(descr, {})
        indexcache = cache.get(index, None)
        if indexcache is not None:
            indexcache[box] = valuebox
        else:
            cache[index] = {box: valuebox}

    def setarrayitem(self, box, indexbox, valuebox, descr):
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
        box = self._input_indirection(box)
        return self._output_indirection(self.length_cache.get(box, None))

    def arraylen_now_known(self, box, lengthbox):
        box = self._input_indirection(box)
        self.length_cache[box] = self._input_indirection(lengthbox)

    def replace_box(self, oldbox, newbox):
        self.input_indirections[self._output_indirection(newbox)] = self._input_indirection(oldbox)
        self.output_indirections[self._input_indirection(oldbox)] = self._output_indirection(newbox)
