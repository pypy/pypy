from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.history import (BoxInt, Const, ConstInt, ConstPtr,
    get_const_ptr_for_string, get_const_ptr_for_unicode)
from pypy.jit.metainterp.optimizeopt import optimizer, virtualize
from pypy.jit.metainterp.optimizeopt.optimizer import CONST_0, CONST_1, llhelper
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython import annlowlevel
from pypy.rpython.lltypesystem import lltype, rstr


class StrOrUnicode(object):
    def __init__(self, LLTYPE, hlstr, emptystr, chr,
                 NEWSTR, STRLEN, STRGETITEM, STRSETITEM, COPYSTRCONTENT,
                 OS_offset):
        self.LLTYPE = LLTYPE
        self.hlstr = hlstr
        self.emptystr = emptystr
        self.chr = chr
        self.NEWSTR = NEWSTR
        self.STRLEN = STRLEN
        self.STRGETITEM = STRGETITEM
        self.STRSETITEM = STRSETITEM
        self.COPYSTRCONTENT = COPYSTRCONTENT
        self.OS_offset = OS_offset

    def _freeze_(self):
        return True

mode_string = StrOrUnicode(rstr.STR, annlowlevel.hlstr, '', chr,
                           rop.NEWSTR, rop.STRLEN, rop.STRGETITEM,
                           rop.STRSETITEM, rop.COPYSTRCONTENT, 0)
mode_unicode = StrOrUnicode(rstr.UNICODE, annlowlevel.hlunicode, u'', unichr,
                            rop.NEWUNICODE, rop.UNICODELEN, rop.UNICODEGETITEM,
                            rop.UNICODESETITEM, rop.COPYUNICODECONTENT,
                            EffectInfo._OS_offset_uni)

# ____________________________________________________________


class __extend__(optimizer.OptValue):
    """New methods added to the base class OptValue for this file."""

    def getstrlen(self, string_optimizer, mode):
        if mode is mode_string:
            s = self.get_constant_string_spec(mode_string)
            if s is not None:
                return ConstInt(len(s))
        else:
            s = self.get_constant_string_spec(mode_unicode)
            if s is not None:
                return ConstInt(len(s))
        if string_optimizer is None:
            return None
        self.ensure_nonnull()
        box = self.force_box(string_optimizer)
        lengthbox = BoxInt()
        string_optimizer.emit_operation(ResOperation(mode.STRLEN, [box], lengthbox))
        return lengthbox

    @specialize.arg(1)
    def get_constant_string_spec(self, mode):
        if self.is_constant():
            s = self.box.getref(lltype.Ptr(mode.LLTYPE))
            return mode.hlstr(s)
        else:
            return None

    def string_copy_parts(self, string_optimizer, targetbox, offsetbox, mode):
        # Copies the pointer-to-string 'self' into the target string
        # given by 'targetbox', at the specified offset.  Returns the offset
        # at the end of the copy.
        lengthbox = self.getstrlen(string_optimizer, mode)
        srcbox = self.force_box(string_optimizer)
        return copy_str_content(string_optimizer, srcbox, targetbox,
                                CONST_0, offsetbox, lengthbox, mode)


class VAbstractStringValue(virtualize.AbstractVirtualValue):
    _attrs_ = ('mode',)

    def __init__(self, keybox, source_op, mode):
        virtualize.AbstractVirtualValue.__init__(self, keybox,
                                                 source_op)
        self.mode = mode

    def _really_force(self, optforce):
        if self.mode is mode_string:
            s = self.get_constant_string_spec(mode_string)
            if s is not None:
                c_s = get_const_ptr_for_string(s)
                self.make_constant(c_s)
                return
        else:
            s = self.get_constant_string_spec(mode_unicode)
            if s is not None:
                c_s = get_const_ptr_for_unicode(s)
                self.make_constant(c_s)
                return
        assert self.source_op is not None
        self.box = box = self.source_op.result
        lengthbox = self.getstrlen(optforce, self.mode)
        op = ResOperation(self.mode.NEWSTR, [lengthbox], box)
        if not we_are_translated():
            op.name = 'FORCE'
        optforce.emit_operation(op)
        self.string_copy_parts(optforce, box, CONST_0, self.mode)


class VStringPlainValue(VAbstractStringValue):
    """A string built with newstr(const)."""
    _lengthbox = None     # cache only

    def setup(self, size):
        self._chars = [optimizer.CVAL_UNINITIALIZED_ZERO] * size

    def setup_slice(self, longerlist, start, stop):
        assert 0 <= start <= stop <= len(longerlist)
        self._chars = longerlist[start:stop]

    def getstrlen(self, _, mode):
        if self._lengthbox is None:
            self._lengthbox = ConstInt(len(self._chars))
        return self._lengthbox

    def getitem(self, index):
        return self._chars[index]

    def setitem(self, index, charvalue):
        assert isinstance(charvalue, optimizer.OptValue)
        self._chars[index] = charvalue

    @specialize.arg(1)
    def get_constant_string_spec(self, mode):
        for c in self._chars:
            if c is optimizer.CVAL_UNINITIALIZED_ZERO or not c.is_constant():
                return None
        return mode.emptystr.join([mode.chr(c.box.getint())
                                   for c in self._chars])

    def string_copy_parts(self, string_optimizer, targetbox, offsetbox, mode):
        if not self.is_virtual() and targetbox is not self.box:
            lengthbox = self.getstrlen(string_optimizer, mode)
            srcbox = self.force_box(string_optimizer)
            return copy_str_content(string_optimizer, srcbox, targetbox,
                                CONST_0, offsetbox, lengthbox, mode)
        for i in range(len(self._chars)):
            charbox = self._chars[i].force_box(string_optimizer)
            if not (isinstance(charbox, Const) and charbox.same_constant(CONST_0)):
                string_optimizer.emit_operation(ResOperation(mode.STRSETITEM, [targetbox,
                                                                               offsetbox,
                                                                               charbox],
                                                  None))
            offsetbox = _int_add(string_optimizer, offsetbox, CONST_1)
        return offsetbox

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            charboxes = [value.get_key_box() for value in self._chars]
            modifier.register_virtual_fields(self.keybox, charboxes)
            for value in self._chars:
                value.get_args_for_fail(modifier)

    def _make_virtual(self, modifier):
        return modifier.make_vstrplain(self.mode is mode_unicode)


class VStringConcatValue(VAbstractStringValue):
    """The concatenation of two other strings."""

    lengthbox = None     # or the computed length

    def setup(self, left, right):
        self.left = left
        self.right = right

    def getstrlen(self, string_optimizer, mode):
        if self.lengthbox is None:
            len1box = self.left.getstrlen(string_optimizer, mode)
            if len1box is None:
                return None
            len2box = self.right.getstrlen(string_optimizer, mode)
            if len2box is None:
                return None
            self.lengthbox = _int_add(string_optimizer, len1box, len2box)
            # ^^^ may still be None, if string_optimizer is None
        return self.lengthbox

    @specialize.arg(1)
    def get_constant_string_spec(self, mode):
        s1 = self.left.get_constant_string_spec(mode)
        if s1 is None:
            return None
        s2 = self.right.get_constant_string_spec(mode)
        if s2 is None:
            return None
        return s1 + s2

    def string_copy_parts(self, string_optimizer, targetbox, offsetbox, mode):
        offsetbox = self.left.string_copy_parts(string_optimizer, targetbox,
                                                offsetbox, mode)
        offsetbox = self.right.string_copy_parts(string_optimizer, targetbox,
                                                 offsetbox, mode)
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

    def _make_virtual(self, modifier):
        return modifier.make_vstrconcat(self.mode is mode_unicode)


class VStringSliceValue(VAbstractStringValue):
    """A slice."""
    _attrs_ = ('vstr', 'vstart', 'vlength')

    def setup(self, vstr, vstart, vlength):
        self.vstr = vstr
        self.vstart = vstart
        self.vlength = vlength

    def getstrlen(self, optforce, mode):
        return self.vlength.force_box(optforce)

    @specialize.arg(1)
    def get_constant_string_spec(self, mode):
        if self.vstart.is_constant() and self.vlength.is_constant():
            s1 = self.vstr.get_constant_string_spec(mode)
            if s1 is None:
                return None
            start = self.vstart.box.getint()
            length = self.vlength.box.getint()
            assert start >= 0
            assert length >= 0
            return s1[start : start + length]
        return None

    def string_copy_parts(self, string_optimizer, targetbox, offsetbox, mode):
        lengthbox = self.getstrlen(string_optimizer, mode)
        return copy_str_content(string_optimizer,
                                self.vstr.force_box(string_optimizer), targetbox,
                                self.vstart.force_box(string_optimizer), offsetbox,
                                lengthbox, mode)

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            boxes = [self.vstr.get_key_box(),
                     self.vstart.get_key_box(),
                     self.vlength.get_key_box()]
            modifier.register_virtual_fields(self.keybox, boxes)
            self.vstr.get_args_for_fail(modifier)
            self.vstart.get_args_for_fail(modifier)
            self.vlength.get_args_for_fail(modifier)

    def _make_virtual(self, modifier):
        return modifier.make_vstrslice(self.mode is mode_unicode)


def copy_str_content(string_optimizer, srcbox, targetbox,
                     srcoffsetbox, offsetbox, lengthbox, mode, need_next_offset=True):
    if isinstance(srcbox, ConstPtr) and isinstance(srcoffsetbox, Const):
        M = 5
    else:
        M = 2
    if isinstance(lengthbox, ConstInt) and lengthbox.value <= M:
        # up to M characters are done "inline", i.e. with STRGETITEM/STRSETITEM
        # instead of just a COPYSTRCONTENT.
        for i in range(lengthbox.value):
            charbox = _strgetitem(string_optimizer, srcbox, srcoffsetbox, mode)
            srcoffsetbox = _int_add(string_optimizer, srcoffsetbox, CONST_1)
            string_optimizer.emit_operation(ResOperation(mode.STRSETITEM, [targetbox,
                                                                           offsetbox,
                                                                           charbox],
                                              None))
            offsetbox = _int_add(string_optimizer, offsetbox, CONST_1)
    else:
        if need_next_offset:
            nextoffsetbox = _int_add(string_optimizer, offsetbox, lengthbox)
        else:
            nextoffsetbox = None
        op = ResOperation(mode.COPYSTRCONTENT, [srcbox, targetbox,
                                                srcoffsetbox, offsetbox,
                                                lengthbox], None)
        string_optimizer.emit_operation(op)
        offsetbox = nextoffsetbox
    return offsetbox

def _int_add(string_optimizer, box1, box2):
    if isinstance(box1, ConstInt):
        if box1.value == 0:
            return box2
        if isinstance(box2, ConstInt):
            return ConstInt(box1.value + box2.value)
    elif isinstance(box2, ConstInt) and box2.value == 0:
        return box1
    if string_optimizer is None:
        return None
    resbox = BoxInt()
    string_optimizer.emit_operation(ResOperation(rop.INT_ADD, [box1, box2], resbox))
    return resbox

def _int_sub(string_optimizer, box1, box2):
    if isinstance(box2, ConstInt):
        if box2.value == 0:
            return box1
        if isinstance(box1, ConstInt):
            return ConstInt(box1.value - box2.value)
    resbox = BoxInt()
    string_optimizer.emit_operation(ResOperation(rop.INT_SUB, [box1, box2], resbox))
    return resbox

def _strgetitem(string_optimizer, strbox, indexbox, mode):
    if isinstance(strbox, ConstPtr) and isinstance(indexbox, ConstInt):
        if mode is mode_string:
            s = strbox.getref(lltype.Ptr(rstr.STR))
            return ConstInt(ord(s.chars[indexbox.getint()]))
        else:
            s = strbox.getref(lltype.Ptr(rstr.UNICODE))
            return ConstInt(ord(s.chars[indexbox.getint()]))
    resbox = BoxInt()
    string_optimizer.emit_operation(ResOperation(mode.STRGETITEM, [strbox, indexbox],
                                                 resbox))
    return resbox


class OptString(optimizer.Optimization):
    "Handling of strings and unicodes."
    def new(self):
        return OptString()

    def make_vstring_plain(self, box, source_op, mode):
        vvalue = VStringPlainValue(box, source_op, mode)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_vstring_concat(self, box, source_op, mode):
        vvalue = VStringConcatValue(box, source_op, mode)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_vstring_slice(self, box, source_op, mode):
        vvalue = VStringSliceValue(box, source_op, mode)
        self.make_equal_to(box, vvalue)
        return vvalue

    def optimize_NEWSTR(self, op):
        self._optimize_NEWSTR(op, mode_string)
    def optimize_NEWUNICODE(self, op):
        self._optimize_NEWSTR(op, mode_unicode)

    def _optimize_NEWSTR(self, op, mode):
        length_box = self.get_constant_box(op.getarg(0))
        if length_box:
            # if the original 'op' did not have a ConstInt as argument,
            # build a new one with the ConstInt argument
            if not isinstance(op.getarg(0), ConstInt):
                op = ResOperation(mode.NEWSTR, [length_box], op.result)
            vvalue = self.make_vstring_plain(op.result, op, mode)
            vvalue.setup(length_box.getint())
        else:
            self.getvalue(op.result).ensure_nonnull()
            self.emit_operation(op)
            self.pure(mode.STRLEN, [op.result], op.getarg(0))

    def optimize_STRSETITEM(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual() and isinstance(value, VStringPlainValue):
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                value.setitem(indexbox.getint(), self.getvalue(op.getarg(2)))
                return
        value.ensure_nonnull()
        self.emit_operation(op)

    optimize_UNICODESETITEM = optimize_STRSETITEM

    def optimize_STRGETITEM(self, op):
        self._optimize_STRGETITEM(op, mode_string)
    def optimize_UNICODEGETITEM(self, op):
        self._optimize_STRGETITEM(op, mode_unicode)

    def _optimize_STRGETITEM(self, op, mode):
        value = self.getvalue(op.getarg(0))
        vindex = self.getvalue(op.getarg(1))
        vresult = self.strgetitem(value, vindex, mode)
        self.make_equal_to(op.result, vresult)

    def strgetitem(self, value, vindex, mode):
        value.ensure_nonnull()
        #
        if value.is_virtual() and isinstance(value, VStringSliceValue):
            fullindexbox = _int_add(self,
                                    value.vstart.force_box(self),
                                    vindex.force_box(self))
            value = value.vstr
            vindex = self.getvalue(fullindexbox)
        #
        if isinstance(value, VStringPlainValue):  # even if no longer virtual
            if vindex.is_constant():
                res = value.getitem(vindex.box.getint())
                # If it is uninitialized we can't return it, it was set by a
                # COPYSTRCONTENT, not a STRSETITEM
                if res is not optimizer.CVAL_UNINITIALIZED_ZERO:
                    return res
        #
        resbox = _strgetitem(self, value.force_box(self), vindex.force_box(self), mode)
        return self.getvalue(resbox)

    def optimize_STRLEN(self, op):
        self._optimize_STRLEN(op, mode_string)
    def optimize_UNICODELEN(self, op):
        self._optimize_STRLEN(op, mode_unicode)

    def _optimize_STRLEN(self, op, mode):
        value = self.getvalue(op.getarg(0))
        lengthbox = value.getstrlen(self, mode)
        self.make_equal_to(op.result, self.getvalue(lengthbox))

    def optimize_COPYSTRCONTENT(self, op):
        self._optimize_COPYSTRCONTENT(op, mode_string)
    def optimize_COPYUNICODECONTENT(self, op):
        self._optimize_COPYSTRCONTENT(op, mode_unicode)

    def _optimize_COPYSTRCONTENT(self, op, mode):
        # args: src dst srcstart dststart length
        src = self.getvalue(op.getarg(0))
        dst = self.getvalue(op.getarg(1))
        srcstart = self.getvalue(op.getarg(2))
        dststart = self.getvalue(op.getarg(3))
        length = self.getvalue(op.getarg(4))

        if length.is_constant() and length.box.getint() == 0:
            return
        copy_str_content(self,
            src.force_box(self),
            dst.force_box(self),
            srcstart.force_box(self),
            dststart.force_box(self),
            length.force_box(self),
            mode, need_next_offset=False
        )

    def optimize_CALL(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.  For non-oopspec calls,
        # oopspecindex is just zero.
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex != EffectInfo.OS_NONE:
            for value, meth in opt_call_oopspec_ops:
                if oopspecindex == value:      # a match with the OS_STR_xxx
                    if meth(self, op, mode_string):
                        return
                    break
                if oopspecindex == value + EffectInfo._OS_offset_uni:
                    # a match with the OS_UNI_xxx
                    if meth(self, op, mode_unicode):
                        return
                    break
            if oopspecindex == EffectInfo.OS_STR2UNICODE:
                if self.opt_call_str_STR2UNICODE(op):
                    return
        self.emit_operation(op)

    optimize_CALL_PURE = optimize_CALL

    def opt_call_str_STR2UNICODE(self, op):
        # Constant-fold unicode("constant string").
        # More generally, supporting non-constant but virtual cases is
        # not obvious, because of the exception UnicodeDecodeError that
        # can be raised by ll_str2unicode()
        varg = self.getvalue(op.getarg(1))
        s = varg.get_constant_string_spec(mode_string)
        if s is None:
            return False
        try:
            u = unicode(s)
        except UnicodeDecodeError:
            return False
        self.make_constant(op.result, get_const_ptr_for_unicode(u))
        return True

    def opt_call_stroruni_STR_CONCAT(self, op, mode):
        vleft = self.getvalue(op.getarg(1))
        vright = self.getvalue(op.getarg(2))
        vleft.ensure_nonnull()
        vright.ensure_nonnull()
        value = self.make_vstring_concat(op.result, op, mode)
        value.setup(vleft, vright)
        return True

    def opt_call_stroruni_STR_SLICE(self, op, mode):
        vstr = self.getvalue(op.getarg(1))
        vstart = self.getvalue(op.getarg(2))
        vstop = self.getvalue(op.getarg(3))
        #
        if (isinstance(vstr, VStringPlainValue) and vstart.is_constant()
            and vstop.is_constant()):
            # slicing with constant bounds of a VStringPlainValue, if any of
            # the characters is unitialized we don't do this special slice, we
            # do the regular copy contents.
            for i in range(vstart.box.getint(), vstop.box.getint()):
                if vstr.getitem(i) is optimizer.CVAL_UNINITIALIZED_ZERO:
                    break
            else:
                value = self.make_vstring_plain(op.result, op, mode)
                value.setup_slice(vstr._chars, vstart.box.getint(),
                                               vstop.box.getint())
                return True
        #
        vstr.ensure_nonnull()
        lengthbox = _int_sub(self, vstop.force_box(self),
                                   vstart.force_box(self))
        #
        if isinstance(vstr, VStringSliceValue):
            # double slicing  s[i:j][k:l]
            vintermediate = vstr
            vstr = vintermediate.vstr
            startbox = _int_add(self,
                                vintermediate.vstart.force_box(self),
                                vstart.force_box(self))
            vstart = self.getvalue(startbox)
        #
        value = self.make_vstring_slice(op.result, op, mode)
        value.setup(vstr, vstart, self.getvalue(lengthbox))
        return True

    def opt_call_stroruni_STR_EQUAL(self, op, mode):
        v1 = self.getvalue(op.getarg(1))
        v2 = self.getvalue(op.getarg(2))
        #
        l1box = v1.getstrlen(None, mode)
        l2box = v2.getstrlen(None, mode)
        if (l1box is not None and l2box is not None and
            isinstance(l1box, ConstInt) and
            isinstance(l2box, ConstInt) and
            l1box.value != l2box.value):
            # statically known to have a different length
            self.make_constant(op.result, CONST_0)
            return True
        #
        if self.handle_str_equal_level1(v1, v2, op.result, mode):
            return True
        if self.handle_str_equal_level1(v2, v1, op.result, mode):
            return True
        if self.handle_str_equal_level2(v1, v2, op.result, mode):
            return True
        if self.handle_str_equal_level2(v2, v1, op.result, mode):
            return True
        #
        if v1.is_nonnull() and v2.is_nonnull():
            if l1box is not None and l2box is not None and l1box.same_box(l2box):
                do = EffectInfo.OS_STREQ_LENGTHOK
            else:
                do = EffectInfo.OS_STREQ_NONNULL
            self.generate_modified_call(do, [v1.force_box(self),
                                             v2.force_box(self)], op.result, mode)
            return True
        return False

    def handle_str_equal_level1(self, v1, v2, resultbox, mode):
        l2box = v2.getstrlen(None, mode)
        if isinstance(l2box, ConstInt):
            if l2box.value == 0:
                lengthbox = v1.getstrlen(self, mode)
                seo = self.optimizer.send_extra_operation
                seo(ResOperation(rop.INT_EQ, [lengthbox, CONST_0], resultbox))
                return True
            if l2box.value == 1:
                l1box = v1.getstrlen(None, mode)
                if isinstance(l1box, ConstInt) and l1box.value == 1:
                    # comparing two single chars
                    vchar1 = self.strgetitem(v1, optimizer.CVAL_ZERO, mode)
                    vchar2 = self.strgetitem(v2, optimizer.CVAL_ZERO, mode)
                    seo = self.optimizer.send_extra_operation
                    seo(ResOperation(rop.INT_EQ, [vchar1.force_box(self),
                                                  vchar2.force_box(self)],
                                     resultbox))
                    return True
                if isinstance(v1, VStringSliceValue):
                    vchar = self.strgetitem(v2, optimizer.CVAL_ZERO, mode)
                    do = EffectInfo.OS_STREQ_SLICE_CHAR
                    self.generate_modified_call(do, [v1.vstr.force_box(self),
                                                     v1.vstart.force_box(self),
                                                     v1.vlength.force_box(self),
                                                     vchar.force_box(self)],
                                                resultbox, mode)
                    return True
        #
        if v2.is_null():
            if v1.is_nonnull():
                self.make_constant(resultbox, CONST_0)
                return True
            if v1.is_null():
                self.make_constant(resultbox, CONST_1)
                return True
            op = ResOperation(rop.PTR_EQ, [v1.force_box(self),
                                           llhelper.CONST_NULL],
                              resultbox)
            self.emit_operation(op)
            return True
        #
        return False

    def handle_str_equal_level2(self, v1, v2, resultbox, mode):
        l2box = v2.getstrlen(None, mode)
        if isinstance(l2box, ConstInt):
            if l2box.value == 1:
                vchar = self.strgetitem(v2, optimizer.CVAL_ZERO, mode)
                if v1.is_nonnull():
                    do = EffectInfo.OS_STREQ_NONNULL_CHAR
                else:
                    do = EffectInfo.OS_STREQ_CHECKNULL_CHAR
                self.generate_modified_call(do, [v1.force_box(self),
                                                 vchar.force_box(self)], resultbox,
                                            mode)
                return True
        #
        if v1.is_virtual() and isinstance(v1, VStringSliceValue):
            if v2.is_nonnull():
                do = EffectInfo.OS_STREQ_SLICE_NONNULL
            else:
                do = EffectInfo.OS_STREQ_SLICE_CHECKNULL
            self.generate_modified_call(do, [v1.vstr.force_box(self),
                                             v1.vstart.force_box(self),
                                             v1.vlength.force_box(self),
                                             v2.force_box(self)], resultbox, mode)
            return True
        return False

    def generate_modified_call(self, oopspecindex, args, result, mode):
        oopspecindex += mode.OS_offset
        cic = self.optimizer.metainterp_sd.callinfocollection
        calldescr, func = cic.callinfo_for_oopspec(oopspecindex)
        op = ResOperation(rop.CALL, [ConstInt(func)] + args, result,
                          descr=calldescr)
        self.emit_operation(op)

    def propagate_forward(self, op):
        dispatch_opt(self, op)

dispatch_opt = make_dispatcher_method(OptString, 'optimize_',
        default=OptString.emit_operation)

def _findall_call_oopspec():
    prefix = 'opt_call_stroruni_'
    result = []
    for name in dir(OptString):
        if name.startswith(prefix):
            value = getattr(EffectInfo, 'OS_' + name[len(prefix):])
            assert isinstance(value, int) and value != 0
            result.append((value, getattr(OptString, name)))
    return unrolling_iterable(result)
opt_call_oopspec_ops = _findall_call_oopspec()
