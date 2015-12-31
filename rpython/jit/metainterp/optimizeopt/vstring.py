from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import (Const, ConstInt, ConstPtr,
    get_const_ptr_for_string, get_const_ptr_for_unicode, REF, INT,
    DONT_CHANGE)
from rpython.jit.metainterp.optimizeopt import optimizer
from rpython.jit.metainterp.optimizeopt.optimizer import CONST_0, CONST_1
from rpython.jit.metainterp.optimizeopt.optimizer import llhelper, REMOVED
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop, ResOperation,\
     AbstractResOp
from rpython.jit.metainterp.optimizeopt import info
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper import annlowlevel
from rpython.rtyper.lltypesystem import lltype, rstr
from rpython.rlib.rarithmetic import is_valid_int


MAX_CONST_LEN = 100


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



class StrPtrInfo(info.AbstractVirtualPtrInfo):
    #_attrs_ = ('length', 'lenbound', 'lgtop', 'mode', '_cached_vinfo', '_is_virtual')

    lenbound = None
    lgtop = None
    _cached_vinfo = None

    def __init__(self, mode, is_virtual=False, length=-1):
        self.length = length
        self._is_virtual = is_virtual
        self.mode = mode
        self.length = length

    def getlenbound(self, mode):
        from rpython.jit.metainterp.optimizeopt import intutils

        if self.lenbound is None:
            if self.length == -1:
                self.lenbound = intutils.IntBound(0, intutils.MAXINT)
            else:
                self.lenbound = intutils.ConstIntBound(self.length)
        return self.lenbound

    @specialize.arg(2)
    def get_constant_string_spec(self, string_optimizer, mode):
        return None # can't be constant

    def force_box(self, op, optforce):
        if not self.is_virtual():
            return op
        optforce.forget_numberings()
        if self.mode is mode_string:
            s = self.get_constant_string_spec(optforce, mode_string)
            if s is not None:
                c_s = get_const_ptr_for_string(s)
                optforce.get_box_replacement(op).set_forwarded(c_s)
                return c_s
        else:
            s = self.get_constant_string_spec(optforce, mode_unicode)
            if s is not None:
                c_s = get_const_ptr_for_unicode(s)
                optforce.get_box_replacement(op).set_forwarded(c_s)
                return c_s
        self._is_virtual = False
        lengthbox = self.getstrlen(op, optforce.optimizer.optstring, self.mode)
        newop = ResOperation(self.mode.NEWSTR, [lengthbox])
        if not we_are_translated():
            newop.name = 'FORCE'
        optforce.emit_operation(newop)
        newop = optforce.getlastop()
        newop.set_forwarded(self)
        op = optforce.get_box_replacement(op)
        op.set_forwarded(newop)
        optstring = optforce.optimizer.optstring
        self.initialize_forced_string(op, optstring, op, CONST_0, self.mode)
        return newop

    def initialize_forced_string(self, op, string_optimizer, targetbox,
                                 offsetbox, mode):
        return self.string_copy_parts(op, string_optimizer, targetbox,
                                      offsetbox, mode)

    def getstrlen(self, op, string_optimizer, mode, create_ops=True):
        if self.lgtop is not None:
            return self.lgtop
        assert not self.is_virtual()
        if not create_ops:
            return None
        lengthop = ResOperation(mode.STRLEN, [op])
        lengthop.set_forwarded(self.getlenbound(mode))
        self.lgtop = lengthop
        string_optimizer.emit_operation(lengthop)
        return lengthop

    def make_guards(self, op, short, optimizer):
        info.AbstractVirtualPtrInfo.make_guards(self, op, short, optimizer)
        if self.lenbound and self.lenbound.lower >= 1:
            if self.mode is mode_string:
                lenop = ResOperation(rop.STRLEN, [op])
            else:
                assert self.mode is mode_unicode
                lenop = ResOperation(rop.UNICODELEN, [op])
            short.append(lenop)
            self.lenbound.make_guards(lenop, short, optimizer)

    def string_copy_parts(self, op, string_optimizer, targetbox, offsetbox,
                          mode):
        # Copies the pointer-to-string 'self' into the target string
        # given by 'targetbox', at the specified offset.  Returns the offset
        # at the end of the copy.
        lengthbox = self.getstrlen(op, string_optimizer, mode)
        srcbox = self.force_box(op, string_optimizer)
        return copy_str_content(string_optimizer, srcbox, targetbox,
                                CONST_0, offsetbox, lengthbox, mode)
     
class VStringPlainInfo(StrPtrInfo):
    #_attrs_ = ('mode', '_is_virtual')

    _chars = None
    
    def __init__(self, mode, is_virtual, length):
        if length != -1:
            self._chars = [None] * length
        StrPtrInfo.__init__(self, mode, is_virtual, length)

    def strsetitem(self, index, op, cf=None, optheap=None):
        self._chars[index] = op

    def shrink(self, length):
        assert length >= 0
        self.length = length
        del self._chars[length:]

    def setup_slice(self, longerlist, start, stop):
        assert 0 <= start <= stop <= len(longerlist)
        self._chars = longerlist[start:stop]
        # slice the 'longerlist', which may also contain Nones

    def strgetitem(self, index, optheap=None):
        return self._chars[index]

    def is_virtual(self):
        return self._is_virtual

    def getstrlen(self, op, string_optimizer, mode, create_ops=True):
        if self.lgtop is None:
            self.lgtop = ConstInt(len(self._chars))
        return self.lgtop

    @specialize.arg(2)
    def get_constant_string_spec(self, optforce, mode):
        for c in self._chars:
            if c is None or not c.is_constant():
                return None
        return mode.emptystr.join([mode.chr(c.getint())
                                   for c in self._chars])

    def string_copy_parts(self, op, string_optimizer, targetbox, offsetbox,
                          mode):
        if not self.is_virtual():
            return StrPtrInfo.string_copy_parts(self, op, string_optimizer,
                                                targetbox, offsetbox, mode)
        else:
            return self.initialize_forced_string(op, string_optimizer,
                                                 targetbox, offsetbox, mode)

    def initialize_forced_string(self, op, string_optimizer, targetbox,
                                 offsetbox, mode):
        for i in range(len(self._chars)):
            assert not isinstance(targetbox, Const) # ConstPtr never makes sense
            charbox = self.strgetitem(i) # can't be virtual
            if charbox is not None:
                op = ResOperation(mode.STRSETITEM, [targetbox,
                                                    offsetbox,
                                                    charbox])
                string_optimizer.emit_operation(op)
            offsetbox = _int_add(string_optimizer, offsetbox, CONST_1)
        return offsetbox

    def _visitor_walk_recursive(self, instbox, visitor, optimizer):
        visitor.register_virtual_fields(instbox, self._chars)

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        return visitor.visit_vstrplain(self.mode is mode_unicode)

class VStringSliceInfo(StrPtrInfo):
    length = -1
    start = None
    lgtop = None
    s = None
    
    def __init__(self, s, start, length, mode):
        self.s = s
        self.start = start
        self.lgtop = length
        self.mode = mode
        self._is_virtual = True

    def is_virtual(self):
        return self._is_virtual

    def string_copy_parts(self, op, string_optimizer, targetbox, offsetbox,
                          mode):
        return copy_str_content(string_optimizer, self.s, targetbox,
                                self.start, offsetbox, self.lgtop, mode)

    @specialize.arg(2)
    def get_constant_string_spec(self, string_optimizer, mode):
        vstart = string_optimizer.getintbound(self.start)
        vlength = string_optimizer.getintbound(self.lgtop)
        if vstart.is_constant() and vlength.is_constant():
            vstr = string_optimizer.getptrinfo(self.s)
            s1 = vstr.get_constant_string_spec(string_optimizer, mode)
            if s1 is None:
                return None
            start = vstart.getint()
            length = vlength.getint()
            assert start >= 0
            assert length >= 0
            return s1[start : start + length]
        return None

    def getstrlen(self, op, string_optimizer, mode, create_ops=True):
        return self.lgtop

    def _visitor_walk_recursive(self, instbox, visitor, optimizer):
        boxes = [self.s, self.start, self.lgtop]
        visitor.register_virtual_fields(instbox, boxes)
        opinfo = optimizer.getptrinfo(self.s)
        if opinfo and opinfo.is_virtual():
            opinfo.visitor_walk_recursive(self.s, visitor, optimizer)

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        return visitor.visit_vstrslice(self.mode is mode_unicode)

class VStringConcatInfo(StrPtrInfo):
    #_attrs_ = ('mode', 'vleft', 'vright', '_is_virtual')

    vleft = None
    vright = None
    _is_virtual = False
    
    def __init__(self, mode, vleft, vright, is_virtual):
        self.vleft = vleft
        self.vright = vright
        StrPtrInfo.__init__(self, mode, is_virtual)

    def is_virtual(self):
        return self._is_virtual

    def getstrlen(self, op, string_optimizer, mode, create_ops=True):
        if self.lgtop is not None:
            return self.lgtop
        lefti = string_optimizer.getptrinfo(self.vleft)
        len1box = lefti.getstrlen(self.vleft, string_optimizer, mode,
                                  create_ops)
        if len1box is None:
            return None
        righti = string_optimizer.getptrinfo(self.vright)
        len2box = righti.getstrlen(self.vright, string_optimizer, mode,
                                   create_ops)
        if len2box is None:
            return None
        self.lgtop = _int_add(string_optimizer, len1box, len2box, create_ops)
            # ^^^ may still be None, if string_optimizer is None
        return self.lgtop

    @specialize.arg(2)
    def get_constant_string_spec(self, string_optimizer, mode):
        ileft = string_optimizer.getptrinfo(self.vleft)
        s1 = ileft.get_constant_string_spec(string_optimizer, mode)
        if s1 is None:
            return None
        iright = string_optimizer.getptrinfo(self.vright)
        s2 = iright.get_constant_string_spec(string_optimizer, mode)
        if s2 is None:
            return None
        return s1 + s2

    def string_copy_parts(self, op, string_optimizer, targetbox, offsetbox,
                          mode):
        lefti = string_optimizer.getptrinfo(self.vleft)
        offsetbox = lefti.string_copy_parts(self.vleft, string_optimizer,
                                            targetbox, offsetbox, mode)
        righti = string_optimizer.getptrinfo(self.vright)
        offsetbox = righti.string_copy_parts(self.vright, string_optimizer,
                                             targetbox, offsetbox, mode)
        return offsetbox

    def _visitor_walk_recursive(self, instbox, visitor, optimizer):
        # we don't store the lengthvalue in guards, because the
        # guard-failed code starts with a regular STR_CONCAT again
        leftbox = self.vleft
        rightbox = self.vright
        visitor.register_virtual_fields(instbox, [leftbox, rightbox])
        leftinfo = optimizer.getptrinfo(leftbox)
        rightinfo = optimizer.getptrinfo(rightbox)
        if leftinfo and leftinfo.is_virtual():
            leftinfo.visitor_walk_recursive(leftbox, visitor, optimizer)
        if rightinfo and rightinfo.is_virtual():
            rightinfo.visitor_walk_recursive(rightbox, visitor, optimizer)

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        return visitor.visit_vstrconcat(self.mode is mode_unicode)


def copy_str_content(string_optimizer, srcbox, targetbox,
                     srcoffsetbox, offsetbox, lengthbox, mode,
                     need_next_offset=True):
    srcbox = string_optimizer.get_box_replacement(srcbox)
    srcoffset = string_optimizer.getintbound(srcoffsetbox)
    lgt = string_optimizer.getintbound(lengthbox)
    if isinstance(srcbox, ConstPtr) and srcoffset.is_constant():
        M = 5
    else:
        M = 2
    if lgt.is_constant() and lgt.getint() <= M:
        # up to M characters are done "inline", i.e. with STRGETITEM/STRSETITEM
        # instead of just a COPYSTRCONTENT.
        for i in range(lgt.getint()):
            charbox = string_optimizer.strgetitem(None, srcbox, srcoffsetbox,
                                                  mode)
            srcoffsetbox = _int_add(string_optimizer, srcoffsetbox, CONST_1)
            assert not isinstance(targetbox, Const)# ConstPtr never makes sense
            string_optimizer.emit_operation(ResOperation(mode.STRSETITEM,
                    [targetbox, offsetbox, charbox]))
            offsetbox = _int_add(string_optimizer, offsetbox, CONST_1)
    else:
        if need_next_offset:
            nextoffsetbox = _int_add(string_optimizer, offsetbox, lengthbox)
        else:
            nextoffsetbox = None
        assert not isinstance(targetbox, Const)   # ConstPtr never makes sense
        op = ResOperation(mode.COPYSTRCONTENT, [srcbox, targetbox,
                                                srcoffsetbox, offsetbox,
                                                lengthbox])
        string_optimizer.emit_operation(op)
        offsetbox = nextoffsetbox
    return offsetbox

def _int_add(string_optimizer, box1, box2, create_ops=True):
    if isinstance(box1, ConstInt):
        if box1.value == 0:
            return box2
        if isinstance(box2, ConstInt):
            return ConstInt(box1.value + box2.value)
    elif isinstance(box2, ConstInt) and box2.value == 0:
        return box1
    if not create_ops:
        return None
    op = ResOperation(rop.INT_ADD, [box1, box2])
    string_optimizer.send_extra_operation(op)
    return op

def _int_sub(string_optimizer, box1, box2):
    if isinstance(box2, ConstInt):
        if box2.value == 0:
            return box1
        if isinstance(box1, ConstInt):
            return ConstInt(box1.value - box2.value)
    op = ResOperation(rop.INT_SUB, [box1, box2])
    string_optimizer.send_extra_operation(op)
    return op

def _strgetitem(string_optimizer, strbox, indexbox, mode, resbox=None):
    if isinstance(strbox, ConstPtr) and isinstance(indexbox, ConstInt):
        if mode is mode_string:
            s = strbox.getref(lltype.Ptr(rstr.STR))
            resnewbox = ConstInt(ord(s.chars[indexbox.getint()]))
        else:
            s = strbox.getref(lltype.Ptr(rstr.UNICODE))
            resnewbox = ConstInt(ord(s.chars[indexbox.getint()]))
        if resbox is not None:
            string_optimizer.make_equal_to(resbox, resnewbox)
        return resnewbox
    if resbox is None:
        resbox = ResOperation(mode.STRGETITEM, [strbox, indexbox])
    else:
        resbox = string_optimizer.replace_op_with(resbox, mode.STRGETITEM,
                                                  [strbox, indexbox])
    string_optimizer.emit_operation(resbox)
    return resbox


class OptString(optimizer.Optimization):
    "Handling of strings and unicodes."

    def setup(self):
        self.optimizer.optstring = self

    def make_vstring_plain(self, op, mode, length):
        vvalue = VStringPlainInfo(mode, True, length)
        op = self.replace_op_with(op, op.getopnum())
        op.set_forwarded(vvalue)
        return vvalue

    def make_vstring_concat(self, op, mode, vleft, vright):
        vvalue = VStringConcatInfo(mode, vleft, vright, True)
        op = self.replace_op_with(op, op.getopnum())
        op.set_forwarded(vvalue)
        return vvalue

    def make_vstring_slice(self, op, strbox, startbox, mode, lengthbox):
        vvalue = VStringSliceInfo(strbox, startbox, lengthbox, mode)
        op = self.replace_op_with(op, op.getopnum())
        op.set_forwarded(vvalue)
        return vvalue

    def optimize_NEWSTR(self, op):
        self._optimize_NEWSTR(op, mode_string)
    def optimize_NEWUNICODE(self, op):
        self._optimize_NEWSTR(op, mode_unicode)

    def _optimize_NEWSTR(self, op, mode):
        length_box = self.get_constant_box(op.getarg(0))
        if length_box and length_box.getint() <= MAX_CONST_LEN:
            assert not op.get_forwarded()
            self.make_vstring_plain(op, mode, length_box.getint())
        else:
            self.make_nonnull_str(op, mode)
            self.emit_operation(op)
            self.pure_from_args(mode.STRLEN, [op], op.getarg(0))

    def optimize_STRSETITEM(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo:
            assert not opinfo.is_constant()
            # strsetitem(ConstPtr) never makes sense
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                opinfo.strsetitem(indexbox.getint(),
                              self.get_box_replacement(op.getarg(2)))
                return
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)

    optimize_UNICODESETITEM = optimize_STRSETITEM

    def optimize_STRGETITEM(self, op):
        self._optimize_STRGETITEM(op, mode_string)
    def optimize_UNICODEGETITEM(self, op):
        self._optimize_STRGETITEM(op, mode_unicode)

    def _optimize_STRGETITEM(self, op, mode):
        self.strgetitem(op, op.getarg(0), op.getarg(1), mode)

    def strgetitem(self, op, s, index, mode):
        self.make_nonnull_str(s, mode)
        sinfo = self.getptrinfo(s)
        #
        if isinstance(sinfo, VStringSliceInfo) and sinfo.is_virtual(): # slice
            index = _int_add(self.optimizer, sinfo.start, index)
            s = sinfo.s
            sinfo = self.getptrinfo(sinfo.s)
        #
        if isinstance(sinfo, VStringPlainInfo):
            # even if no longer virtual
            vindex = self.getintbound(index)
            if vindex.is_constant():
                result = sinfo.strgetitem(vindex.getint())
                if result is not None:
                    if op is not None:
                        self.make_equal_to(op, result)
                    return result
        #
        vindex = self.getintbound(index)
        if isinstance(sinfo, VStringConcatInfo) and vindex.is_constant():
            leftinfo = self.getptrinfo(sinfo.vleft)
            len1box = leftinfo.getstrlen(sinfo.vleft, self, mode)
            if isinstance(len1box, ConstInt):
                raw_index = vindex.getint()
                len1 = len1box.getint()
                if raw_index < len1:
                    return self.strgetitem(op, sinfo.vleft, index, mode)
                else:
                    index = ConstInt(raw_index - len1)
                    return self.strgetitem(op, sinfo.vright, index, mode)
        #
        return _strgetitem(self, s, index, mode, op)

    def optimize_STRLEN(self, op):
        self._optimize_STRLEN(op, mode_string)
    def optimize_UNICODELEN(self, op):
        self._optimize_STRLEN(op, mode_unicode)

    def _optimize_STRLEN(self, op, mode):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo:
            lgtop = opinfo.getstrlen(op, self, mode, False)
            if lgtop is not None:
                self.make_equal_to(op, lgtop)
                return
        self.emit_operation(op)

    def optimize_COPYSTRCONTENT(self, op):
        self._optimize_COPYSTRCONTENT(op, mode_string)

    def optimize_COPYUNICODECONTENT(self, op):
        self._optimize_COPYSTRCONTENT(op, mode_unicode)

    def _optimize_COPYSTRCONTENT(self, op, mode):
        # args: src dst srcstart dststart length
        assert op.getarg(0).type == REF
        assert op.getarg(1).type == REF
        assert op.getarg(2).type == INT
        assert op.getarg(3).type == INT
        assert op.getarg(4).type == INT
        src = self.getptrinfo(op.getarg(0))
        dst = self.getptrinfo(op.getarg(1))
        srcstart = self.getintbound(op.getarg(2))
        dststart = self.getintbound(op.getarg(3))
        length = self.getintbound(op.getarg(4))
        dst_virtual = (isinstance(dst, VStringPlainInfo) and dst.is_virtual())

        if length.is_constant() and length.getint() == 0:
            return
        elif ((str and (src.is_virtual() or src.is_constant())) and
              srcstart.is_constant() and dststart.is_constant() and
              length.is_constant() and
              (length.getint() < 20 or ((src.is_virtual() or src.is_constant()) and dst_virtual))):
            src_start = srcstart.getint()
            dst_start = dststart.getint()
            actual_length = length.getint()
            for index in range(actual_length):
                vresult = self.strgetitem(None, op.getarg(0),
                                          ConstInt(index + src_start), mode)
                if dst_virtual:
                    dst.strsetitem(index + dst_start, vresult)
                else:
                    new_op = ResOperation(mode.STRSETITEM, [
                        op.getarg(1), ConstInt(index + dst_start),
                        vresult,
                    ])
                    self.emit_operation(new_op)
        else:
            copy_str_content(self, op.getarg(0), op.getarg(1), op.getarg(2),
                             op.getarg(3), op.getarg(4), mode,
                             need_next_offset=False)

    def optimize_CALL_I(self, op):
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
            if oopspecindex == EffectInfo.OS_SHRINK_ARRAY:
                if self.opt_call_SHRINK_ARRAY(op):
                    return
        self.emit_operation(op)
    optimize_CALL_R = optimize_CALL_I
    optimize_CALL_F = optimize_CALL_I
    optimize_CALL_N = optimize_CALL_I
    optimize_CALL_PURE_I = optimize_CALL_I
    optimize_CALL_PURE_R = optimize_CALL_I
    optimize_CALL_PURE_F = optimize_CALL_I
    optimize_CALL_PURE_N = optimize_CALL_I

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            return
        self.emit_operation(op)

    def opt_call_str_STR2UNICODE(self, op):
        # Constant-fold unicode("constant string").
        # More generally, supporting non-constant but virtual cases is
        # not obvious, because of the exception UnicodeDecodeError that
        # can be raised by ll_str2unicode()
        varg = self.getptrinfo(op.getarg(1))
        s = None
        if varg:
            s = varg.get_constant_string_spec(self, mode_string)
        if s is None:
            return False
        try:
            u = unicode(s)
        except UnicodeDecodeError:
            return False
        self.make_constant(op, get_const_ptr_for_unicode(u))
        self.last_emitted_operation = REMOVED
        return True

    def opt_call_stroruni_STR_CONCAT(self, op, mode):
        self.make_nonnull_str(op.getarg(1), mode)
        self.make_nonnull_str(op.getarg(2), mode)
        self.make_vstring_concat(op, mode,
                                 self.get_box_replacement(op.getarg(1)),
                                 self.get_box_replacement(op.getarg(2)))
        self.last_emitted_operation = REMOVED
        return True

    def opt_call_stroruni_STR_SLICE(self, op, mode):
        self.make_nonnull_str(op.getarg(1), mode)
        vstr = self.getptrinfo(op.getarg(1))
        vstart = self.getintbound(op.getarg(2))
        vstop = self.getintbound(op.getarg(3))
        #
        #---The following looks reasonable, but see test_str_slice_bug:
        #   the problem is what occurs if the source string has been forced
        #   but still contains None in its _chars
        #if (isinstance(vstr, VStringPlainInfo) and vstart.is_constant()
        #    and vstop.is_constant()):
        #    value = self.make_vstring_plain(op, mode, -1)
        #    value.setup_slice(vstr._chars, vstart.getint(),
        #                      vstop.getint())
        #    return True
        #
        startbox = op.getarg(2)
        strbox = op.getarg(1)
        lengthbox = _int_sub(self.optimizer, op.getarg(3), op.getarg(2))
        #
        if isinstance(vstr, VStringSliceInfo):
            # double slicing  s[i:j][k:l]
            strbox = vstr.s
            startbox = _int_add(self.optimizer, vstr.start, startbox)
        #
        self.make_vstring_slice(op, strbox, startbox, mode, lengthbox)
        self.last_emitted_operation = REMOVED
        return True

    @specialize.arg(2)
    def opt_call_stroruni_STR_EQUAL(self, op, mode):
        arg1 = self.get_box_replacement(op.getarg(1))
        arg2 = self.get_box_replacement(op.getarg(2))
        i1 = self.getptrinfo(arg1)
        i2 = self.getptrinfo(arg2)
        #
        if i1:
            l1box = i1.getstrlen(arg1, self, mode, create_ops=False)
        else:
            l1box = None
        if i2:
            l2box = i2.getstrlen(arg2, self, mode, create_ops=False)
        else:
            l2box = None
        if (l1box is not None and l2box is not None and
            isinstance(l1box, ConstInt) and
            isinstance(l2box, ConstInt) and
            l1box.value != l2box.value):
            # statically known to have a different length
            self.make_constant(op, CONST_0)
            return True
        #
        if self.handle_str_equal_level1(arg1, arg2, op, mode):
            return True
        if self.handle_str_equal_level1(arg2, arg1, op, mode):
            return True
        if self.handle_str_equal_level2(arg1, arg2, op, mode):
            return True
        if self.handle_str_equal_level2(arg2, arg1, op, mode):
            return True
        #
        if i1 and i1.is_nonnull() and i2 and i2.is_nonnull():
            if l1box is not None and l2box is not None and l1box.same_box(l2box):
                do = EffectInfo.OS_STREQ_LENGTHOK
            else:
                do = EffectInfo.OS_STREQ_NONNULL
            self.generate_modified_call(do, [arg1, arg2], op, mode)
            return True
        return False

    def handle_str_equal_level1(self, arg1, arg2, resultop, mode):
        i1 = self.getptrinfo(arg1)
        i2 = self.getptrinfo(arg2)
        l2box = None
        l1box = None
        if i2:
            l2box = i2.getstrlen(arg2, self, mode, create_ops=False)
        if isinstance(l2box, ConstInt):
            if l2box.value == 0:
                if i1 and i1.is_nonnull():
                    self.make_nonnull_str(arg1, mode)
                    i1 = self.getptrinfo(arg1)
                    lengthbox = i1.getstrlen(arg1, self, mode)
                else:
                    lengthbox = None
                if lengthbox is not None:
                    seo = self.optimizer.send_extra_operation
                    op = self.replace_op_with(resultop, rop.INT_EQ,
                                              [lengthbox, CONST_0],
                                              descr=DONT_CHANGE)
                    seo(op)
                    return True
            if l2box.value == 1:
                if i1:
                    l1box = i1.getstrlen(arg1, self, mode, False)
                if isinstance(l1box, ConstInt) and l1box.value == 1:
                    # comparing two single chars
                    vchar1 = self.strgetitem(None, arg1, optimizer.CONST_0,
                                             mode)
                    vchar2 = self.strgetitem(None, arg2, optimizer.CONST_0,
                                             mode)
                    seo = self.optimizer.send_extra_operation
                    op = self.optimizer.replace_op_with(resultop, rop.INT_EQ,
                                [vchar1, vchar2], descr=DONT_CHANGE)
                    seo(op)
                    return True
                if isinstance(i1, VStringSliceInfo):
                    vchar = self.strgetitem(None, arg2, optimizer.CONST_0,
                                            mode)
                    do = EffectInfo.OS_STREQ_SLICE_CHAR
                    self.generate_modified_call(do, [i1.s, i1.start,
                                                     i1.lgtop, vchar],
                                                     resultop, mode)
                    return True
        #
        if i2 and i2.is_null():
            if i1 and i1.is_nonnull():
                self.make_constant(resultop, CONST_0)
                return True
            if i1 and i1.is_null():
                self.make_constant(resultop, CONST_1)
                return True
            op = self.optimizer.replace_op_with(resultop, rop.PTR_EQ,
                                                [arg1, llhelper.CONST_NULL],
                                                descr=DONT_CHANGE)
            self.emit_operation(op)
            return True
        #
        return False

    def handle_str_equal_level2(self, arg1, arg2, resultbox, mode):
        i1 = self.getptrinfo(arg1)
        i2 = self.getptrinfo(arg2)
        l2box = None
        if i2:
            l2box = i2.getstrlen(arg1, self, mode, create_ops=False)
        if l2box:
            l2info = self.getintbound(l2box)
            if l2info.is_constant():
                if l2info.getint() == 1:
                    vchar = self.strgetitem(None, arg2, optimizer.CONST_0, mode)
                    if i1 and i1.is_nonnull():
                        do = EffectInfo.OS_STREQ_NONNULL_CHAR
                    else:
                        do = EffectInfo.OS_STREQ_CHECKNULL_CHAR
                    self.generate_modified_call(do, [arg1, vchar],
                                                resultbox, mode)
                    return True
            #
        if isinstance(i1, VStringSliceInfo) and i1.is_virtual():
            if i2 and i2.is_nonnull():
                do = EffectInfo.OS_STREQ_SLICE_NONNULL
            else:
                do = EffectInfo.OS_STREQ_SLICE_CHECKNULL
            self.generate_modified_call(do, [i1.s, i1.start, i1.lgtop,
                                             arg2], resultbox, mode)
            return True
        return False

    def opt_call_stroruni_STR_CMP(self, op, mode):
        i1 = self.getptrinfo(op.getarg(1))
        i2 = self.getptrinfo(op.getarg(2))
        if not i1 or not i2:
            return False
        l1box = i1.getstrlen(None, self, mode, False)
        l2box = i2.getstrlen(None, self, mode, False)
        if (l1box is not None and l2box is not None and
            isinstance(l1box, ConstInt) and
            isinstance(l2box, ConstInt) and
            l1box.getint() == l2box.getint() == 1):
            # comparing two single chars
            char1 = self.strgetitem(None, op.getarg(1), optimizer.CONST_0, mode)
            char2 = self.strgetitem(None, op.getarg(2), optimizer.CONST_0, mode)
            seo = self.optimizer.send_extra_operation
            op = self.replace_op_with(op, rop.INT_SUB, [char1, char2],
                                      descr=DONT_CHANGE)
            seo(op)
            return True
        return False

    def opt_call_SHRINK_ARRAY(self, op):
        i1 = self.getptrinfo(op.getarg(1))
        i2 = self.getintbound(op.getarg(2))
        # If the index is constant, if the argument is virtual (we only support
        # VStringPlainValue for now) we can optimize away the call.
        if (i2 and i2.is_constant() and i1 and i1.is_virtual() and
            isinstance(i1, VStringPlainInfo)):
            length = i2.getint()
            i1.shrink(length)
            self.last_emitted_operation = REMOVED
            self.make_equal_to(op, op.getarg(1))
            return True
        return False

    def generate_modified_call(self, oopspecindex, args, result, mode):
        oopspecindex += mode.OS_offset
        cic = self.optimizer.metainterp_sd.callinfocollection
        calldescr, func = cic.callinfo_for_oopspec(oopspecindex)
        op = self.optimizer.replace_op_with(result, rop.CALL_I,
                                            [ConstInt(func)] + args,
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
            assert is_valid_int(value) and value != 0
            result.append((value, getattr(OptString, name)))
    return unrolling_iterable(result)
opt_call_oopspec_ops = _findall_call_oopspec()
