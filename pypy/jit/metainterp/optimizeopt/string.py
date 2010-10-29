from pypy.rpython.lltypesystem import lltype, rstr, llmemory
from pypy.rpython import annlowlevel
from pypy.jit.metainterp.history import Box, BoxInt, BoxPtr
from pypy.jit.metainterp.history import Const, ConstInt, ConstPtr
from pypy.jit.metainterp.history import get_const_ptr_for_string
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeopt import optimizer, virtualize
from pypy.jit.metainterp.optimizeopt.optimizer import CONST_0, CONST_1
from pypy.jit.metainterp.optimizeopt.optimizer import llhelper
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.codewriter.effectinfo import EffectInfo, callinfo_for_oopspec
from pypy.jit.codewriter import heaptracker
from pypy.rlib.unroll import unrolling_iterable


class __extend__(optimizer.OptValue):
    """New methods added to the base class OptValue for this file."""

    def getstrlen(self, newoperations):
        s = self.get_constant_string()
        if s is not None:
            return ConstInt(len(s))
        else:
            if newoperations is None:
                return None
            self.ensure_nonnull()
            box = self.force_box()
            lengthbox = BoxInt()
            newoperations.append(ResOperation(rop.STRLEN, [box], lengthbox))
            return lengthbox

    def get_constant_string(self):
        if self.is_constant():
            s = self.box.getref(lltype.Ptr(rstr.STR))
            return annlowlevel.hlstr(s)
        else:
            return None

    def string_copy_parts(self, newoperations, targetbox, offsetbox):
        # Copies the pointer-to-string 'self' into the target string
        # given by 'targetbox', at the specified offset.  Returns the offset
        # at the end of the copy.
        lengthbox = self.getstrlen(newoperations)
        srcbox = self.force_box()
        return copy_str_content(newoperations, srcbox, targetbox,
                                CONST_0, offsetbox, lengthbox)


class VAbstractStringValue(virtualize.AbstractVirtualValue):
    _attrs_ = ()

    def _really_force(self):
        s = self.get_constant_string()
        if s is not None:
            c_s = get_const_ptr_for_string(s)
            self.make_constant(c_s)
            return
        assert self.source_op is not None
        self.box = box = self.source_op.result
        newoperations = self.optimizer.newoperations
        lengthbox = self.getstrlen(newoperations)
        newoperations.append(ResOperation(rop.NEWSTR, [lengthbox], box))
        self.string_copy_parts(newoperations, box, CONST_0)


class VStringPlainValue(VAbstractStringValue):
    """A string built with newstr(const)."""
    _lengthbox = None     # cache only

    def setup(self, size):
        self._chars = [optimizer.CVAL_UNINITIALIZED_ZERO] * size

    def setup_slice(self, longerlist, start, stop):
        assert 0 <= start <= stop <= len(longerlist)
        self._chars = longerlist[start:stop]

    def getstrlen(self, _):
        if self._lengthbox is None:
            self._lengthbox = ConstInt(len(self._chars))
        return self._lengthbox

    def getitem(self, index):
        return self._chars[index]

    def setitem(self, index, charvalue):
        assert isinstance(charvalue, optimizer.OptValue)
        self._chars[index] = charvalue

    def get_constant_string(self):
        for c in self._chars:
            if c is optimizer.CVAL_UNINITIALIZED_ZERO or not c.is_constant():
                return None
        return ''.join([chr(c.box.getint()) for c in self._chars])

    def string_copy_parts(self, newoperations, targetbox, offsetbox):
        for i in range(len(self._chars)):
            charbox = self._chars[i].force_box()
            newoperations.append(ResOperation(rop.STRSETITEM, [targetbox,
                                                               offsetbox,
                                                               charbox], None))
            offsetbox = _int_add(newoperations, offsetbox, CONST_1)
        return offsetbox

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            charboxes = [value.get_key_box() for value in self._chars]
            modifier.register_virtual_fields(self.keybox, charboxes)
            for value in self._chars:
                value.get_args_for_fail(modifier)

    def enum_forced_boxes(self, boxes, already_seen):
        key = self.get_key_box()
        if key in already_seen:
            return
        already_seen[key] = None
        if self.box is None:
            for box in self._chars:
                box.enum_forced_boxes(boxes, already_seen)
        else:
            boxes.append(self.box)

    def _make_virtual(self, modifier):
        return modifier.make_vstrplain()


class VStringConcatValue(VAbstractStringValue):
    """The concatenation of two other strings."""

    def setup(self, left, right, lengthbox):
        self.left = left
        self.right = right
        self.lengthbox = lengthbox

    def getstrlen(self, _):
        return self.lengthbox

    def get_constant_string(self):
        s1 = self.left.get_constant_string()
        if s1 is None:
            return None
        s2 = self.right.get_constant_string()
        if s2 is None:
            return None
        return s1 + s2

    def string_copy_parts(self, newoperations, targetbox, offsetbox):
        offsetbox = self.left.string_copy_parts(newoperations, targetbox,
                                                offsetbox)
        offsetbox = self.right.string_copy_parts(newoperations, targetbox,
                                                 offsetbox)
        return offsetbox

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            # we don't store the lengthvalue in guards, because the
            # guard-failed code starts with a regular STR_CONCAT again
            leftbox = self.left.get_key_box()
            rightbox = self.right.get_key_box()
            modifier.register_virtual_fields(self.keybox, [leftbox, rightbox])
            self.left.get_args_for_fail(modifier)
            self.right.get_args_for_fail(modifier)

    def enum_forced_boxes(self, boxes, already_seen):
        key = self.get_key_box()
        if key in already_seen:
            return
        already_seen[key] = None
        if self.box is None:
            self.left.enum_forced_boxes(boxes, already_seen)
            self.right.enum_forced_boxes(boxes, already_seen)
        else:
            boxes.append(self.box)

    def _make_virtual(self, modifier):
        return modifier.make_vstrconcat()


class VStringSliceValue(VAbstractStringValue):
    """A slice."""
    _attrs_ = ('vstr', 'vstart', 'vlength')

    def setup(self, vstr, vstart, vlength):
        self.vstr = vstr
        self.vstart = vstart
        self.vlength = vlength

    def getstrlen(self, _):
        return self.vlength.force_box()

    def get_constant_string(self):
        if self.vstart.is_constant() and self.vlength.is_constant():
            s1 = self.vstr.get_constant_string()
            if s1 is None:
                return None
            start = self.vstart.box.getint()
            length = self.vlength.box.getint()
            assert start >= 0
            assert length >= 0
            return s1[start : start + length]
        return None

    def string_copy_parts(self, newoperations, targetbox, offsetbox):
        lengthbox = self.getstrlen(newoperations)
        return copy_str_content(newoperations,
                                self.vstr.force_box(), targetbox,
                                self.vstart.force_box(), offsetbox,
                                lengthbox)

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            boxes = [self.vstr.get_key_box(),
                     self.vstart.get_key_box(),
                     self.vlength.get_key_box()]
            modifier.register_virtual_fields(self.keybox, boxes)
            self.vstr.get_args_for_fail(modifier)
            self.vstart.get_args_for_fail(modifier)
            self.vlength.get_args_for_fail(modifier)

    def enum_forced_boxes(self, boxes, already_seen):
        key = self.get_key_box()
        if key in already_seen:
            return
        already_seen[key] = None
        if self.box is None:
            self.vstr.enum_forced_boxes(boxes, already_seen)
            self.vstart.enum_forced_boxes(boxes, already_seen)
            self.vlength.enum_forced_boxes(boxes, already_seen)
        else:
            boxes.append(self.box)

    def _make_virtual(self, modifier):
        return modifier.make_vstrslice()


def copy_str_content(newoperations, srcbox, targetbox,
                     srcoffsetbox, offsetbox, lengthbox):
    if isinstance(srcbox, ConstPtr) and isinstance(srcoffsetbox, Const):
        M = 5
    else:
        M = 2
    if isinstance(lengthbox, ConstInt) and lengthbox.value <= M:
        # up to M characters are done "inline", i.e. with STRGETITEM/STRSETITEM
        # instead of just a COPYSTRCONTENT.
        for i in range(lengthbox.value):
            charbox = _strgetitem(newoperations, srcbox, srcoffsetbox)
            srcoffsetbox = _int_add(newoperations, srcoffsetbox, CONST_1)
            newoperations.append(ResOperation(rop.STRSETITEM, [targetbox,
                                                               offsetbox,
                                                               charbox], None))
            offsetbox = _int_add(newoperations, offsetbox, CONST_1)
    else:
        nextoffsetbox = _int_add(newoperations, offsetbox, lengthbox)
        op = ResOperation(rop.COPYSTRCONTENT, [srcbox, targetbox,
                                               srcoffsetbox, offsetbox,
                                               lengthbox], None)
        newoperations.append(op)
        offsetbox = nextoffsetbox
    return offsetbox

def _int_add(newoperations, box1, box2):
    if isinstance(box1, ConstInt):
        if box1.value == 0:
            return box2
        if isinstance(box2, ConstInt):
            return ConstInt(box1.value + box2.value)
    elif isinstance(box2, ConstInt) and box2.value == 0:
        return box1
    resbox = BoxInt()
    newoperations.append(ResOperation(rop.INT_ADD, [box1, box2], resbox))
    return resbox

def _int_sub(newoperations, box1, box2):
    if isinstance(box2, ConstInt):
        if box2.value == 0:
            return box1
        if isinstance(box1, ConstInt):
            return ConstInt(box1.value - box2.value)
    resbox = BoxInt()
    newoperations.append(ResOperation(rop.INT_SUB, [box1, box2], resbox))
    return resbox

def _strgetitem(newoperations, strbox, indexbox):
    if isinstance(strbox, ConstPtr) and isinstance(indexbox, ConstInt):
        s = strbox.getref(lltype.Ptr(rstr.STR))
        return ConstInt(ord(s.chars[indexbox.getint()]))
    resbox = BoxInt()
    newoperations.append(ResOperation(rop.STRGETITEM, [strbox, indexbox],
                                      resbox))
    return resbox


class OptString(optimizer.Optimization):
    "Handling of strings and unicodes."

    def make_vstring_plain(self, box, source_op=None):
        vvalue = VStringPlainValue(self.optimizer, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_vstring_concat(self, box, source_op=None):
        vvalue = VStringConcatValue(self.optimizer, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_vstring_slice(self, box, source_op=None):
        vvalue = VStringSliceValue(self.optimizer, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def optimize_CALL(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.  For non-oopspec calls,
        # oopspecindex is just zero.
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
            oopspecindex = effectinfo.oopspecindex
            for value, meth in opt_call_oopspec_ops:
                if oopspecindex == value:
                    if meth(self, op):
                        return
        self.emit_operation(op)

    def opt_call_oopspec_ARRAYCOPY(self, op):
        source_value = self.getvalue(op.getarg(1))
        dest_value = self.getvalue(op.getarg(2))
        source_start_box = self.get_constant_box(op.getarg(3))
        dest_start_box = self.get_constant_box(op.getarg(4))
        length = self.get_constant_box(op.getarg(5))
        if (source_value.is_virtual() and source_start_box and dest_start_box
            and length and dest_value.is_virtual()):
            # XXX optimize the case where dest value is not virtual,
            #     but we still can avoid a mess
            source_start = source_start_box.getint()
            dest_start = dest_start_box.getint()
            for index in range(length.getint()):
                val = source_value.getitem(index + source_start)
                dest_value.setitem(index + dest_start, val)
            return True
        if length and length.getint() == 0:
            return True # 0-length arraycopy
        return False

    def optimize_NEWSTR(self, op):
        length_box = self.get_constant_box(op.getarg(0))
        if length_box:
            # if the original 'op' did not have a ConstInt as argument,
            # build a new one with the ConstInt argument
            if not isinstance(op.getarg(0), ConstInt):
                op = ResOperation(rop.NEWSTR, [length_box], op.result)
            vvalue = self.make_vstring_plain(op.result, op)
            vvalue.setup(length_box.getint())
        else:
            self.getvalue(op.result).ensure_nonnull()
            self.emit_operation(op)

    def optimize_STRSETITEM(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual() and isinstance(value, VStringPlainValue):
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                value.setitem(indexbox.getint(), self.getvalue(op.getarg(2)))
                return
        value.ensure_nonnull()
        self.emit_operation(op)

    def optimize_STRGETITEM(self, op):
        value = self.getvalue(op.getarg(0))
        vindex = self.getvalue(op.getarg(1))
        vresult = self.strgetitem(value, vindex)
        self.make_equal_to(op.result, vresult)

    def strgetitem(self, value, vindex):
        value.ensure_nonnull()
        #
        if value.is_virtual() and isinstance(value, VStringSliceValue):
            fullindexbox = _int_add(self.optimizer.newoperations,
                                    value.vstart.force_box(),
                                    vindex.force_box())
            value = value.vstr
            vindex = self.getvalue(fullindexbox)
        #
        if isinstance(value, VStringPlainValue):  # even if no longer virtual
            if vindex.is_constant():
                return value.getitem(vindex.box.getint())
        #
        resbox = _strgetitem(self.optimizer.newoperations,
                             value.force_box(),vindex.force_box())
        return self.getvalue(resbox)

    def optimize_STRLEN(self, op):
        value = self.getvalue(op.getarg(0))
        lengthbox = value.getstrlen(self.optimizer.newoperations)
        self.make_equal_to(op.result, self.getvalue(lengthbox))

    def opt_call_oopspec_STR_CONCAT(self, op):
        vleft = self.getvalue(op.getarg(1))
        vright = self.getvalue(op.getarg(2))
        vleft.ensure_nonnull()
        vright.ensure_nonnull()
        newoperations = self.optimizer.newoperations
        len1box = vleft.getstrlen(newoperations)
        len2box = vright.getstrlen(newoperations)
        lengthbox = _int_add(newoperations, len1box, len2box)
        value = self.make_vstring_concat(op.result, op)
        value.setup(vleft, vright, lengthbox)
        return True

    def opt_call_oopspec_STR_SLICE(self, op):
        newoperations = self.optimizer.newoperations
        vstr = self.getvalue(op.getarg(1))
        vstart = self.getvalue(op.getarg(2))
        vstop = self.getvalue(op.getarg(3))
        #
        if (isinstance(vstr, VStringPlainValue) and vstart.is_constant()
            and vstop.is_constant()):
            # slicing with constant bounds of a VStringPlainValue
            value = self.make_vstring_plain(op.result, op)
            value.setup_slice(vstr._chars, vstart.box.getint(),
                                           vstop.box.getint())
            return True
        #
        vstr.ensure_nonnull()
        lengthbox = _int_sub(newoperations, vstop.force_box(),
                                            vstart.force_box())
        #
        if isinstance(vstr, VStringSliceValue):
            # double slicing  s[i:j][k:l]
            vintermediate = vstr
            vstr = vintermediate.vstr
            startbox = _int_add(newoperations,
                                vintermediate.vstart.force_box(),
                                vstart.force_box())
            vstart = self.getvalue(startbox)
        #
        value = self.make_vstring_slice(op.result, op)
        value.setup(vstr, vstart, self.getvalue(lengthbox))
        return True

    def opt_call_oopspec_STR_EQUAL(self, op):
        v1 = self.getvalue(op.getarg(1))
        v2 = self.getvalue(op.getarg(2))
        #
        l1box = v1.getstrlen(None)
        l2box = v2.getstrlen(None)
        if (l1box is not None and l2box is not None and
            isinstance(l1box, ConstInt) and
            isinstance(l2box, ConstInt) and
            l1box.value != l2box.value):
            # statically known to have a different length
            self.make_constant(op.result, CONST_0)
            return True
        #
        if self.handle_str_equal_level1(v1, v2, op.result):
            return True
        if self.handle_str_equal_level1(v2, v1, op.result):
            return True
        if self.handle_str_equal_level2(v1, v2, op.result):
            return True
        if self.handle_str_equal_level2(v2, v1, op.result):
            return True
        #
        if v1.is_nonnull() and v2.is_nonnull():
            if l1box is not None and l2box is not None and (
                l1box == l2box or (isinstance(l1box, ConstInt) and
                                   isinstance(l2box, ConstInt) and
                                   l1box.value == l2box.value)):
                do = EffectInfo.OS_STREQ_LENGTHOK
            else:
                do = EffectInfo.OS_STREQ_NONNULL
            self.generate_modified_call(do, [v1.force_box(),
                                             v2.force_box()], op.result)
            return True
        return False

    def handle_str_equal_level1(self, v1, v2, resultbox):
        l2box = v2.getstrlen(None)
        if isinstance(l2box, ConstInt):
            if l2box.value == 0:
                lengthbox = v1.getstrlen(self.optimizer.newoperations)
                seo = self.optimizer.send_extra_operation
                seo(ResOperation(rop.INT_EQ, [lengthbox, CONST_0], resultbox))
                return True
            if l2box.value == 1:
                l1box = v1.getstrlen(None)
                if isinstance(l1box, ConstInt) and l1box.value == 1:
                    # comparing two single chars
                    vchar1 = self.strgetitem(v1, optimizer.CVAL_ZERO)
                    vchar2 = self.strgetitem(v2, optimizer.CVAL_ZERO)
                    seo = self.optimizer.send_extra_operation
                    seo(ResOperation(rop.INT_EQ, [vchar1.force_box(),
                                                  vchar2.force_box()],
                                     resultbox))
                    return True
                if isinstance(v1, VStringSliceValue):
                    vchar = self.strgetitem(v2, optimizer.CVAL_ZERO)
                    do = EffectInfo.OS_STREQ_SLICE_CHAR
                    self.generate_modified_call(do, [v1.vstr.force_box(),
                                                     v1.vstart.force_box(),
                                                     v1.vlength.force_box(),
                                                     vchar.force_box()],
                                                resultbox)
                    return True
        #
        if v2.is_null():
            if v1.is_nonnull():
                self.make_constant(resultbox, CONST_0)
                return True
            if v1.is_null():
                self.make_constant(resultbox, CONST_1)
                return True
            op = ResOperation(rop.PTR_EQ, [v1.force_box(),
                                           llhelper.CONST_NULL],
                              resultbox)
            self.optimizer.newoperations.append(op)
            return True
        #
        return False

    def handle_str_equal_level2(self, v1, v2, resultbox):
        l2box = v2.getstrlen(None)
        if isinstance(l2box, ConstInt):
            if l2box.value == 1:
                vchar = self.strgetitem(v2, optimizer.CVAL_ZERO)
                if v1.is_nonnull():
                    do = EffectInfo.OS_STREQ_NONNULL_CHAR
                else:
                    do = EffectInfo.OS_STREQ_CHECKNULL_CHAR
                self.generate_modified_call(do, [v1.force_box(),
                                                 vchar.force_box()], resultbox)
                return True
        #
        if v1.is_virtual() and isinstance(v1, VStringSliceValue):
            if v2.is_nonnull():
                do = EffectInfo.OS_STREQ_SLICE_NONNULL
            else:
                do = EffectInfo.OS_STREQ_SLICE_CHECKNULL
            self.generate_modified_call(do, [v1.vstr.force_box(),
                                             v1.vstart.force_box(),
                                             v1.vlength.force_box(),
                                             v2.force_box()], resultbox)
            return True
        return False

    def generate_modified_call(self, oopspecindex, args, result):
        calldescr, func = callinfo_for_oopspec(oopspecindex)
        op = ResOperation(rop.CALL, [ConstInt(func)] + args, result,
                          descr=calldescr)
        self.optimizer.newoperations.append(op)

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptString, 'optimize_')

def _findall_call_oopspec():
    prefix = 'opt_call_oopspec_'
    result = []
    for name in dir(OptString):
        if name.startswith(prefix):
            value = getattr(EffectInfo, 'OS_' + name[len(prefix):])
            assert isinstance(value, int) and value != 0
            result.append((value, getattr(OptString, name)))
    return unrolling_iterable(result)
opt_call_oopspec_ops = _findall_call_oopspec()
