import py
import pytest
import sys
import re
import pytest
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rtyper import rclass
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    BaseTest, convert_old_style_to_targets, FakeJitDriverStaticData)
from rpython.jit.metainterp.history import (
    JitCellToken, ConstInt, get_const_ptr_for_string)
from rpython.jit.metainterp import executor, compile
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef)
from rpython.jit.metainterp.test.test_resume import (
    ResumeDataFakeReader, MyMetaInterp)
from rpython.jit.tool.oparser import parse, convert_loop_to_trace

# ____________________________________________________________


class BaseTestBasic(BaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"

    def optimize_loop(self, ops, optops, call_pure_results=None):
        loop = self.parse(ops)
        token = JitCellToken()
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        exp = parse(optops, namespace=self.namespace.copy())
        expected = convert_old_style_to_targets(exp, jump=True)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        compile_data = compile.SimpleCompileData(
            trace, call_pure_results=call_pure_results,
            enable_opts=self.enable_opts)
        jitdriver_sd = FakeJitDriverStaticData()
        info, ops = compile_data.optimize_trace(self.metainterp_sd, jitdriver_sd, {})
        label_op = ResOperation(rop.LABEL, info.inputargs)
        loop.inputargs = info.inputargs
        loop.operations = [label_op] + ops
        self.loop = loop
        self.assert_equal(loop, expected)


class TestOptimizeBasic(BaseTestBasic):
    def test_keep_guard_no_exception(self):
        ops = """
        [i1]
        i2 = call_i(i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_keep_guard_no_exception_with_call_pure_that_is_not_folded(self):
        ops = """
        [i1]
        i2 = call_pure_i(123456, i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        jump(i2)
        """
        expected = """
        [i1]
        i2 = call_i(123456, i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_no_exception_with_call_pure_on_constant_args(self):
        arg_consts = [ConstInt(i) for i in (123456, 81)]
        call_pure_results = {tuple(arg_consts): ConstInt(5)}
        ops = """
        [i1]
        i3 = same_as_i(81)
        i2 = call_pure_i(123456, i3, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        jump(i2)
        """
        expected = """
        [i1]
        jump(5)
        """
        self.optimize_loop(ops, expected, call_pure_results)

    def test_remove_guard_no_exception_with_duplicated_call_pure(self):
        ops = """
        [i1]
        i2 = call_pure_i(123456, i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        i3 = call_pure_i(123456, i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2, i3]
        jump(i3)
        """
        expected = """
        [i1]
        i2 = call_i(123456, i1, descr=nonwritedescr)
        guard_no_exception() [i1, i2]
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    # ----------

    def test_call_loopinvariant(self):
        ops = """
        [i1]
        i2 = call_loopinvariant_i(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i2, 1) []
        i3 = call_loopinvariant_i(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i3, 1) []
        i4 = call_loopinvariant_i(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i4, 1) []
        jump(i1)
        """
        expected = """
        [i1]
        i2 = call_i(1, i1, descr=nonwritedescr)
        guard_no_exception() []
        guard_value(i2, 1) []
        jump(i1)
        """
        self.optimize_loop(ops, expected)


    # ----------


    def test_array_non_optimized(self):
        ops = """
        [i1, p0]
        setarrayitem_gc(p0, 0, i1, descr=arraydescr)
        guard_nonnull(p0) []
        p1 = new_array(i1, descr=arraydescr)
        jump(i1, p1)
        """
        expected = """
        [i1, p0]
        p1 = new_array(i1, descr=arraydescr)
        setarrayitem_gc(p0, 0, i1, descr=arraydescr)
        jump(i1, p1)
        """
        self.optimize_loop(ops, expected)

    def test_p123_array(self):
        ops = """
        [i1, p2, p3]
        i3 = getarrayitem_gc_i(p3, 0, descr=arraydescr)
        escape_n(i3)
        p1 = new_array(1, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.optimize_loop(ops, ops)

    def test_varray_negative_items_from_invalid_loop_v(self):
        ops = """
        []
        p1 = new_array(10, descr=arraydescr)
        i2 = getarrayitem_gc_i(p1, -1, descr=arraydescr)
        jump(i2)
        """
        py.test.raises(InvalidLoop, self.optimize_loop, ops, ops)
        #
        ops = """
        [i2]
        p1 = new_array(10, descr=arraydescr)
        setarrayitem_gc(p1, -1, i2, descr=arraydescr)
        jump()
        """
        expected = """
        [i2]
        jump()
        """
        # the setarrayitem_gc is completely dropped because of invalid index.
        # we could also raise InvalidLoop, but both choices seem OK
        self.optimize_loop(ops, expected)

    def test_varray_too_large_items_from_invalid_loop_v(self):
        ops = """
        []
        p1 = new_array(10, descr=arraydescr)
        i2 = getarrayitem_gc_i(p1, 10, descr=arraydescr)
        jump(i2)
        """
        py.test.raises(InvalidLoop, self.optimize_loop, ops, ops)
        #
        ops = """
        [i2]
        p1 = new_array(10, descr=arraydescr)
        setarrayitem_gc(p1, 10, i2, descr=arraydescr)
        jump()
        """
        expected = """
        [i2]
        jump()
        """
        # the setarrayitem_gc is completely dropped because of invalid index.
        # we could also raise InvalidLoop, but both choices seem OK
        self.optimize_loop(ops, expected)

    def test_varray_struct_negative_items_from_invalid_loop_v(self):
        ops = """
        []
        p1 = new_array_clear(10, descr=complexarraydescr)
        f0 = getinteriorfield_gc_f(p1, -1, descr=complexrealdescr)
        jump(f0)
        """
        py.test.raises(InvalidLoop, self.optimize_loop, ops, ops)
        #
        ops = """
        [f0]
        p1 = new_array_clear(10, descr=complexarraydescr)
        setinteriorfield_gc(p1, -1, f0, descr=complexrealdescr)
        jump()
        """
        expected = """
        [f0]
        jump()
        """
        # the setinteriorfield_gc is completely dropped because of invalid
        # index.  we could also raise InvalidLoop, but both choices seem OK
        self.optimize_loop(ops, expected)

    def test_varray_struct_too_large_items_from_invalid_loop_v(self):
        ops = """
        []
        p1 = new_array_clear(10, descr=complexarraydescr)
        f0 = getinteriorfield_gc_f(p1, 10, descr=complexrealdescr)
        jump(f0)
        """
        py.test.raises(InvalidLoop, self.optimize_loop, ops, ops)
        #
        ops = """
        [f0]
        p1 = new_array_clear(10, descr=complexarraydescr)
        setinteriorfield_gc(p1, 10, f0, descr=complexrealdescr)
        jump()
        """
        expected = """
        [f0]
        jump()
        """
        # the setinteriorfield_gc is completely dropped because of invalid
        # index.  we could also raise InvalidLoop, but both choices seem OK
        self.optimize_loop(ops, expected)

    def test_p123_vstruct(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc_i(p3, descr=adescr)
        escape_n(i3)
        p1 = new(descr=ssize)
        setfield_gc(p1, i1, descr=adescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.optimize_loop(ops, ops)

    def test_merge_guard_class_guard_value(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_class(p1, ConstClass(node_vtable)) [i0]
        i3 = int_add(i1, i2)
        guard_value(p1, ConstPtr(myptr)) [i1]
        jump(p2, i0, i1, i3, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_value(p1, ConstPtr(myptr)) [i0]
        i3 = int_add(i1, i2)
        jump(p2, i0, i1, i3, p2)
        """
        self.optimize_loop(ops, expected)

    def test_merge_guard_nonnull_guard_class(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_nonnull(p1) [i0]
        i3 = int_add(i1, i2)
        guard_class(p1, ConstClass(node_vtable)) [i1]
        jump(p2, i0, i1, i3, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_nonnull_class(p1, ConstClass(node_vtable)) [i0]
        i3 = int_add(i1, i2)
        jump(p2, i0, i1, i3, p2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr("i0", rop.GUARD_NONNULL_CLASS)

    def test_merge_guard_nonnull_guard_value(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_nonnull(p1) [i0]
        i3 = int_add(i1, i2)
        guard_value(p1, ConstPtr(myptr)) [i1]
        jump(p2, i0, i1, i3, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_value(p1, ConstPtr(myptr)) [i0]
        i3 = int_add(i1, i2)
        jump(p2, i0, i1, i3, p2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr("i0", rop.GUARD_VALUE)

    def test_merge_guard_nonnull_guard_class_guard_value(self):
        ops = """
        [p1, i0, i1, i2, p2]
        guard_nonnull(p1) [i0]
        i3 = int_add(i1, i2)
        guard_class(p1, ConstClass(node_vtable)) [i2]
        i4 = int_sub(i3, 1)
        guard_value(p1, ConstPtr(myptr)) [i1]
        jump(p2, i0, i1, i4, p2)
        """
        expected = """
        [p1, i0, i1, i2, p2]
        guard_value(p1, ConstPtr(myptr)) [i0]
        i3 = int_add(i1, i2)
        i4 = int_sub(i3, 1)
        jump(p2, i0, i1, i4, p2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr("i0", rop.GUARD_VALUE)

    def test_remove_duplicate_pure_op(self):
        ops = """
        [p1, p2]
        i1 = ptr_eq(p1, p2)
        i2 = ptr_eq(p1, p2)
        i3 = int_add(i1, 1)
        i3b = int_is_true(i3)
        guard_true(i3b) []
        i4 = int_add(i2, 1)
        i4b = int_is_true(i4)
        guard_true(i4b) []
        escape_n(i3)
        escape_n(i4)
        guard_true(i1) []
        guard_true(i2) []
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = ptr_eq(p1, p2)
        i3 = int_add(i1, 1)
        escape_n(i3)
        escape_n(i3)
        guard_true(i1) []
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_fold_constant_partial_ops_float(self):
        ops = """
        [f0]
        f1 = float_mul(f0, 1.0)
        f2 = escape_f(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f2 = escape_f(f0)
        jump(f2)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [f0]
        f1 = float_mul(1.0, f0)
        f2 = escape_f(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f2 = escape_f(f0)
        jump(f2)
        """
        self.optimize_loop(ops, expected)


        ops = """
        [f0]
        f1 = float_mul(f0, -1.0)
        f2 = escape_f(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f1 = float_neg(f0)
        f2 = escape_f(f1)
        jump(f2)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [f0]
        f1 = float_mul(-1.0, f0)
        f2 = escape_f(f1)
        jump(f2)
        """
        expected = """
        [f0]
        f1 = float_neg(f0)
        f2 = escape_f(f1)
        jump(f2)
        """
        self.optimize_loop(ops, expected)

    def test_fold_repeated_float_neg(self):
        ops = """
        [f0]
        f1 = float_neg(f0)
        f2 = float_neg(f1)
        f3 = float_neg(f2)
        f4 = float_neg(f3)
        escape_n(f4)
        jump(f4)
        """
        expected = """
        [f0]
        # The backend removes this dead op.
        f1 = float_neg(f0)
        escape_n(f0)
        jump(f0)
        """
        self.optimize_loop(ops, expected)

    def test_float_division_by_multiplication(self):
        ops = """
        [f0]
        f1 = float_truediv(f0, 2.0)
        f2 = float_truediv(f1, 3.0)
        f3 = float_truediv(f2, -0.25)
        f4 = float_truediv(f3, 0.0)
        f5 = escape_f(f4)
        jump(f5)
        """

        expected = """
        [f0]
        f1 = float_mul(f0, 0.5)
        f2 = float_truediv(f1, 3.0)
        f3 = float_mul(f2, -4.0)
        f4 = float_truediv(f3, 0.0)
        f5 = escape_f(f4)
        jump(f5)
        """
        self.optimize_loop(ops, expected)

    # ----------
    def get_class_of_box(self, box):
        base = box.getref_base()
        return lltype.cast_opaque_ptr(rclass.OBJECTPTR, base).typeptr

    def _verify_fail_args(self, boxes, oparse, text):
        r = re.compile(r"\bwhere\s+(\w+)\s+is a\s+(\w+)")
        parts = list(r.finditer(text))
        ends = [match.start() for match in parts] + [len(text)]
        #
        virtuals = {}
        for match, end in zip(parts, ends[1:]):
            pvar = match.group(1)
            fieldstext = text[match.end():end]
            if match.group(2) == 'varray':
                arrayname, fieldstext = fieldstext.split(':', 1)
                tag = ('varray', self.namespace[arrayname.strip()])
            elif match.group(2) == 'vstruct':
                if ',' in fieldstext:
                    structname, fieldstext = fieldstext.split(',', 1)
                else:
                    structname, fieldstext = fieldstext, ''
                tag = ('vstruct', self.namespace[structname.strip()])
            else:
                tag = ('virtual', self.namespace[match.group(2)])
            virtuals[pvar] = (tag, None, fieldstext)
        #
        r2 = re.compile(r"([\w\d()]+)[.](\w+)\s*=\s*([\w\d()]+)")
        pendingfields = []
        for match in r2.finditer(text):
            pvar = match.group(1)
            pfieldname = match.group(2)
            pfieldvar = match.group(3)
            pendingfields.append((pvar, pfieldname, pfieldvar))
        #
        def _variables_equal(box, varname, strict):
            if varname not in virtuals:
                if strict:
                    assert box.same_box(oparse.getvar(varname))
            else:
                tag, resolved, fieldstext = virtuals[varname]
                if tag[0] == 'virtual':
                    assert self.get_class_of_box(box) == tag[1]
                elif tag[0] == 'varray':
                    pass    # xxx check arraydescr
                elif tag[0] == 'vstruct':
                    pass    # xxx check typedescr
                else:
                    assert 0
                if resolved is not None:
                    assert resolved.getvalue() == box.getvalue()
                else:
                    virtuals[varname] = tag, box, fieldstext
        #
        basetext = text.splitlines()[0]
        varnames = [s.strip() for s in basetext.split(',')]
        if varnames == ['']:
            varnames = []
        assert len(boxes) == len(varnames)
        for box, varname in zip(boxes, varnames):
            _variables_equal(box, varname, strict=False)
        for pvar, pfieldname, pfieldvar in pendingfields:
            box = oparse.getvar(pvar)
            fielddescr = self.namespace[pfieldname.strip()]
            opnum = OpHelpers.getfield_for_descr(fielddescr)
            fieldval = executor.execute(self.cpu, None,
                                        opnum,
                                        fielddescr,
                                        box)
            _variables_equal(executor.wrap_constant(fieldval), pfieldvar,
                             strict=True)
        #
        for match in parts:
            pvar = match.group(1)
            tag, resolved, fieldstext = virtuals[pvar]
            assert resolved is not None
            index = 0
            for fieldtext in fieldstext.split(','):
                fieldtext = fieldtext.strip()
                if not fieldtext:
                    continue
                if tag[0] in ('virtual', 'vstruct'):
                    fieldname, fieldvalue = fieldtext.split('=')
                    fielddescr = self.namespace[fieldname.strip()]
                    opnum = OpHelpers.getfield_for_descr(fielddescr)
                    fieldval = executor.execute(self.cpu, None, opnum,
                                                fielddescr,
                                                resolved)
                elif tag[0] == 'varray':
                    fieldvalue = fieldtext
                    #opnum = OpHelpers.getarrayitem_for_descr(fielddescr)
                    fieldval = executor.execute(self.cpu, None,
                                                rop.GETARRAYITEM_GC_I,
                                                tag[1],
                                                resolved, ConstInt(index))
                else:
                    assert 0
                _variables_equal(executor.wrap_constant(fieldval),
                                 fieldvalue.strip(), strict=False)
                index += 1

    def check_expanded_fail_descr(self, expectedtext, guard_opnum, values=None):
        guard_op, = [op for op in self.loop.operations if op.is_guard()]
        fail_args = guard_op.getfailargs()
        if values is not None:
            fail_args = values
        fdescr = guard_op.getdescr()
        reader = ResumeDataFakeReader(fdescr, fail_args,
                                      MyMetaInterp(self.cpu))
        boxes = reader.consume_boxes()
        self._verify_fail_args(boxes, self.oparse, expectedtext)

    def test_expand_fail_1(self):
        ops = """
        [i1, i3]
        # first rename i3 into i4
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i3, descr=valuedescr)
        i4 = getfield_gc_i(p1, descr=valuedescr)
        #
        i2 = int_add(10, 5)
        guard_true(i1) [i2, i4]
        jump(i1, i4)
        """
        expected = """
        [i1, i3]
        guard_true(i1) [i3]
        jump(1, i3)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('15, i3', rop.GUARD_TRUE)

    def test_expand_fail_2(self):
        ops = """
        [i1, i2]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i2, descr=valuedescr)
        setfield_gc(p1, p1, descr=nextdescr)
        guard_true(i1) [p1]
        jump(i1, i2)
        """
        expected = """
        [i1, i2]
        guard_true(i1) [i2]
        jump(1, i2)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''ptr
            where ptr is a node_vtable, valuedescr=i2
            ''', rop.GUARD_TRUE)

    def test_expand_fail_3(self):
        ops = """
        [i1, i2, i3, p3]
        p1 = new_with_vtable(descr=nodesize)
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, 1, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p2, p3, descr=nextdescr)
        guard_true(i1) [i3, p1]
        jump(i2, i1, i3, p3)
        """
        expected = """
        [i1, i2, i3, p3]
        guard_true(i1) [i3, i2, p3]
        jump(i2, 1, i3, p3)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''i3, p1
            where p1 is a node_vtable, valuedescr=1, nextdescr=p2
            where p2 is a node_vtable, valuedescr=i2, nextdescr=p3
            ''', rop.GUARD_TRUE)

    def test_expand_fail_4(self):
        for arg in ['p1', 'i2,p1', 'p1,p2', 'p2,p1',
                    'i2,p1,p2', 'i2,p2,p1']:
            ops = """
            [i1, i2, i3]
            p1 = new_with_vtable(descr=nodesize)
            setfield_gc(p1, i3, descr=valuedescr)
            i4 = getfield_gc_i(p1, descr=valuedescr)   # copy of i3
            p2 = new_with_vtable(descr=nodesize)
            setfield_gc(p1, i2, descr=valuedescr)
            setfield_gc(p1, p2, descr=nextdescr)
            setfield_gc(p2, i2, descr=valuedescr)
            guard_true(i1) [i4, i3, %s]
            jump(i1, i2, i3)
            """
            expected = """
            [i1, i2, i3]
            guard_true(i1) [i3, i2]
            jump(1, i2, i3)
            """
            self.optimize_loop(ops % arg, expected)
            self.check_expanded_fail_descr('''i3, i3, %s
                where p1 is a node_vtable, valuedescr=i2, nextdescr=p2
                where p2 is a node_vtable, valuedescr=i2''' % arg,
                                           rop.GUARD_TRUE)

    def test_expand_fail_5(self):
        ops = """
        [i1, i2, i3, i4]
        p1 = new_with_vtable(descr=nodesize)
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i4, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p2, p1, descr=nextdescr)      # a cycle
        guard_true(i1) [i3, i4, p1, p2]
        jump(i2, i1, i3, i4)
        """
        expected = """
        [i1, i2, i3, i4]
        guard_true(i1) [i3, i4, i2]
        jump(i2, 1, i3, i4)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''i3, i4, p1, p2
            where p1 is a node_vtable, valuedescr=i4, nextdescr=p2
            where p2 is a node_vtable, valuedescr=i2, nextdescr=p1
            ''', rop.GUARD_TRUE)

    def test_expand_fail_varray(self):
        ops = """
        [i1]
        p1 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 1, i1, descr=arraydescr)
        setarrayitem_gc(p1, 0, 25, descr=arraydescr)
        guard_true(i1) [p1]
        i2 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        guard_true(i1) [i1]
        jump(1)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''p1
            where p1 is a varray arraydescr: 25, i1
            ''', rop.GUARD_TRUE)

    def test_expand_fail_vstruct(self):
        ops = """
        [i1, p1]
        p2 = new(descr=ssize)
        setfield_gc(p2, i1, descr=adescr)
        setfield_gc(p2, p1, descr=bdescr)
        guard_true(i1) [p2]
        i3 = getfield_gc_i(p2, descr=adescr)
        p3 = getfield_gc_r(p2, descr=bdescr)
        jump(i3, p3)
        """
        expected = """
        [i1, p1]
        guard_true(i1) [i1, p1]
        jump(1, p1)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''p2
            where p2 is a vstruct ssize, adescr=i1, bdescr=p1
            ''', rop.GUARD_TRUE)

    def test_expand_fail_lazy_setfield_1(self):
        ops = """
        [p1, i2, i3]
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        expected = """
        [p1, i2, i3]
        guard_true(i3) [i2, p1]
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        self.optimize_loop(ops, expected)
        #
        # initialize p1.getref_base() to return a random pointer to a NODE
        # (it doesn't have to be self.nodeaddr, but it's convenient)
        failargs = self.loop.operations[1].getfailargs()
        if failargs[0].type == 'r':
            values = [InputArgRef(self.nodeaddr), InputArgInt(0)]
        else:
            values = [InputArgInt(0), InputArgRef(self.nodeaddr)]
        assert hasattr(self.oparse.getvar('p1'), '_resref')
        self.oparse.getvar('p1')._resref = self.nodeaddr
        #
        self.check_expanded_fail_descr(
            '''
            p1.nextdescr = p2
            where p2 is a node_vtable, valuedescr=i2
            ''', rop.GUARD_TRUE, values=values)

    def test_expand_fail_lazy_setfield_2(self):
        ops = """
        [i2, i3]
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(ConstPtr(myptr), p2, descr=nextdescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(ConstPtr(myptr), NULL, descr=nextdescr)
        jump(i2, i4)
        """
        expected = """
        [i2, i3]
        guard_true(i3) [i2]
        i4 = int_neg(i2)
        setfield_gc(ConstPtr(myptr), NULL, descr=nextdescr)
        jump(i2, i4)
        """
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''
            ConstPtr(myptr).nextdescr = p2
            where p2 is a node_vtable, valuedescr=i2
            ''', rop.GUARD_TRUE)

    def test_residual_call_does_not_invalidate_caches(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        i2 = call_i(i1, descr=nonwritedescr)
        i3 = getfield_gc_i(p1, descr=valuedescr)
        escape_n(i1)
        escape_n(i3)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        i2 = call_i(i1, descr=nonwritedescr)
        escape_n(i1)
        escape_n(i1)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidate_some_caches(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=adescr)
        i2 = getfield_gc_i(p1, descr=bdescr)
        i3 = call_i(i1, descr=writeadescr)
        i4 = getfield_gc_i(p1, descr=adescr)
        i5 = getfield_gc_i(p1, descr=bdescr)
        escape_n(i1)
        escape_n(i2)
        escape_n(i4)
        escape_n(i5)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=adescr)
        i2 = getfield_gc_i(p1, descr=bdescr)
        i3 = call_i(i1, descr=writeadescr)
        i4 = getfield_gc_i(p1, descr=adescr)
        escape_n(i1)
        escape_n(i2)
        escape_n(i4)
        escape_n(i2)
        jump(p1, p2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidate_arrays(self):
        ops = """
        [p1, p2, i1]
        p3 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        i3 = call_i(i1, descr=writeadescr)
        p5 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        escape_n(p3)
        escape_n(p4)
        escape_n(p5)
        escape_n(p6)
        jump(p1, p2, i1)
        """
        expected = """
        [p1, p2, i1]
        p3 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        i3 = call_i(i1, descr=writeadescr)
        escape_n(p3)
        escape_n(p4)
        escape_n(p3)
        escape_n(p4)
        jump(p1, p2, i1)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidate_some_arrays(self):
        ops = """
        [p1, p2, i1]
        p3 = getarrayitem_gc_r(p2, 0, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        i2 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        i3 = call_i(i1, descr=writearraydescr)
        p5 = getarrayitem_gc_r(p2, 0, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        i4 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        escape_n(p3)
        escape_n(p4)
        escape_n(p5)
        escape_n(p6)
        escape_n(i2)
        escape_n(i4)
        jump(p1, p2, i1)
        """
        expected = """
        [p1, p2, i1]
        p3 = getarrayitem_gc_r(p2, 0, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        i2 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        i3 = call_i(i1, descr=writearraydescr)
        i4 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        escape_n(p3)
        escape_n(p4)
        escape_n(p3)
        escape_n(p4)
        escape_n(i2)
        escape_n(i4)
        jump(p1, p2, i1)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidates_some_read_caches_1(self):
        ops = """
        [p1, i1, p2, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=adescr)
        i3 = call_i(i1, descr=readadescr)
        setfield_gc(p1, i3, descr=valuedescr)
        setfield_gc(p2, i3, descr=adescr)
        jump(p1, i1, p2, i2)
        """
        expected = """
        [p1, i1, p2, i2]
        setfield_gc(p2, i2, descr=adescr)
        i3 = call_i(i1, descr=readadescr)
        setfield_gc(p2, i3, descr=adescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, p2, i2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidates_some_read_caches_2(self):
        ops = """
        [p1, i1, p2, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=adescr)
        i3 = call_i(i1, descr=writeadescr)
        setfield_gc(p2, i3, descr=adescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, p2, i2)
        """
        expected = """
        [p1, i1, p2, i2]
        setfield_gc(p2, i2, descr=adescr)
        i3 = call_i(i1, descr=writeadescr)
        setfield_gc(p2, i3, descr=adescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, p2, i2)
        """
        self.optimize_loop(ops, expected)

    def test_residual_call_invalidates_some_read_caches_3(self):
        ops = """
        [p1, i1, p2, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=adescr)
        i3 = call_i(i1, descr=plaincalldescr)
        setfield_gc(p2, i3, descr=adescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, p2, i2)
        """
        expected = """
        [p1, i1, p2, i2]
        setfield_gc(p2, i2, descr=adescr)
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call_i(i1, descr=plaincalldescr)
        setfield_gc(p2, i3, descr=adescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, p2, i2)
        """
        self.optimize_loop(ops, expected)

    def test_call_assembler_invalidates_caches(self):
        ops = '''
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call_assembler_i(i1, descr=asmdescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i3)
        '''
        self.optimize_loop(ops, ops)

    def test_call_pure_invalidates_caches(self):
        # CALL_PURE should still force the setfield_gc() to occur before it
        ops = '''
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call_pure_i(p1, descr=plaincalldescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i3)
        '''
        expected = '''
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i3 = call_i(p1, descr=plaincalldescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i3)
        '''
        self.optimize_loop(ops, expected)

    def test_call_pure_constant_folding(self):
        # CALL_PURE is not marked as is_always_pure(), because it is wrong
        # to call the function arbitrary many times at arbitrary points in
        # time.  Check that it is either constant-folded (and replaced by
        # the result of the call, recorded as the first arg), or turned into
        # a regular CALL.
        arg_consts = [ConstInt(i) for i in (123456, 4, 5, 6)]
        call_pure_results = {tuple(arg_consts): ConstInt(42)}
        ops = '''
        [i0, i1, i2]
        escape_n(i1)
        escape_n(i2)
        i3 = call_pure_i(123456, 4, 5, 6, descr=plaincalldescr)
        i4 = call_pure_i(123456, 4, i0, 6, descr=plaincalldescr)
        jump(i0, i3, i4)
        '''
        expected = '''
        [i0, i1, i2]
        escape_n(i1)
        escape_n(i2)
        i4 = call_i(123456, 4, i0, 6, descr=plaincalldescr)
        jump(i0, 42, i4)
        '''
        self.optimize_loop(ops, expected, call_pure_results)

    def test_vref_nonvirtual_nonescape(self):
        ops = """
        [p1]
        p2 = virtual_ref(p1, 5)
        virtual_ref_finish(p2, p1)
        jump(p1)
        """
        expected = """
        [p1]
        p0 = force_token()
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_vref_nonvirtual_escape(self):
        ops = """
        [p1]
        p2 = virtual_ref(p1, 5)
        escape_n(p2)
        virtual_ref_finish(p2, p1)
        jump(p1)
        """
        expected = """
        [p1]
        p0 = force_token()
        p2 = new_with_vtable(descr=vref_descr)
        setfield_gc(p2, p0, descr=virtualtokendescr)
        setfield_gc(p2, NULL, descr=virtualforceddescr)
        escape_n(p2)
        setfield_gc(p2, NULL, descr=virtualtokendescr)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        jump(p1)
        """
        # XXX we should optimize a bit more the case of a nonvirtual.
        # in theory it is enough to just do 'p2 = p1'.
        self.optimize_loop(ops, expected)

    def test_vref_virtual_1(self):
        ops = """
        [p0, i1]
        #
        p1 = new_with_vtable(descr=nodesize)
        p1b = new_with_vtable(descr=nodesize)
        setfield_gc(p1b, 252, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        #
        p2 = virtual_ref(p1, 3)
        setfield_gc(p0, p2, descr=nextdescr)
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        virtual_ref_finish(p2, p1)
        setfield_gc(p0, NULL, descr=nextdescr)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        p3 = force_token()
        #
        p2 = new_with_vtable(descr=vref_descr)
        setfield_gc(p2, p3, descr=virtualtokendescr)
        setfield_gc(p2, NULL, descr=virtualforceddescr)
        setfield_gc(p0, p2, descr=nextdescr)
        #
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        #
        setfield_gc(p0, NULL, descr=nextdescr)
        setfield_gc(p2, NULL, descr=virtualtokendescr)
        p1 = new_with_vtable(descr=nodesize)
        p1b = new_with_vtable(descr=nodesize)
        setfield_gc(p1b, 252, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        jump(p0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_vref_virtual_2(self):
        ops = """
        [p0, i1]
        #
        p1 = new_with_vtable(descr=nodesize)
        p1b = new_with_vtable(descr=nodesize)
        setfield_gc(p1b, i1, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        #
        p2 = virtual_ref(p1, 2)
        setfield_gc(p0, p2, descr=nextdescr)
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() [p2, p1]
        virtual_ref_finish(p2, p1)
        setfield_gc(p0, NULL, descr=nextdescr)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        p3 = force_token()
        #
        p2 = new_with_vtable(descr=vref_descr)
        setfield_gc(p2, p3, descr=virtualtokendescr)
        setfield_gc(p2, NULL, descr=virtualforceddescr)
        setfield_gc(p0, p2, descr=nextdescr)
        #
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() [p2, i1]
        #
        setfield_gc(p0, NULL, descr=nextdescr)
        setfield_gc(p2, NULL, descr=virtualtokendescr)
        p1 = new_with_vtable(descr=nodesize)
        p1b = new_with_vtable(descr=nodesize)
        setfield_gc(p1b, i1, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        jump(p0, i1)
        """
        # the point of this test is that 'i1' should show up in the fail_args
        # of 'guard_not_forced', because it was stored in the virtual 'p1b'.
        self.optimize_loop(ops, expected)
        self.check_expanded_fail_descr('''p2, p1
            where p1 is a node_vtable, nextdescr=p1b
            where p1b is a node_vtable, valuedescr=i1
            ''', rop.GUARD_NOT_FORCED)

    @pytest.mark.xfail
    def test_vref_virtual_and_lazy_setfield(self):
        ops = """
        [p0, i1]
        #
        p1 = new_with_vtable(descr=nodesize)
        p1b = new_with_vtable(descr=nodesize)
        setfield_gc(p1b, i1, descr=valuedescr)
        setfield_gc(p1, p1b, descr=nextdescr)
        #
        p2 = virtual_ref(p1, 2)
        setfield_gc(p0, p2, descr=refdescr)
        call_n(i1, descr=nonwritedescr)
        guard_no_exception() [p2, p1]
        virtual_ref_finish(p2, p1)
        setfield_gc(p0, NULL, descr=refdescr)
        jump(p0, i1)
        """
        expected = """
        [p0, i1]
        p3 = force_token()
        call_n(i1, descr=nonwritedescr)
        guard_no_exception() [p3, i1, p0]
        setfield_gc(p0, NULL, descr=refdescr)
        jump(p0, i1)
        """
        self.optimize_loop(ops, expected)
        # the fail_args contain [p3, i1, p0]:
        #  - p3 is from the virtual expansion of p2
        #  - i1 is from the virtual expansion of p1
        #  - p0 is from the extra pendingfields
        self.loop.inputargs[0].setref_base(self.nodeobjvalue)
        self.check_expanded_fail_descr('''p2, p1
            p0.refdescr = p2
            where p2 is a jit_virtual_ref_vtable, virtualtokendescr=p3
            where p1 is a node_vtable, nextdescr=p1b
            where p1b is a node_vtable, valuedescr=i1
            ''', rop.GUARD_NO_EXCEPTION)

    def test_vref_virtual_after_finish(self):
        ops = """
        [i1]
        p1 = new_with_vtable(descr=nodesize)
        p2 = virtual_ref(p1, 7)
        escape_n(p2)
        virtual_ref_finish(p2, p1)
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() []
        jump(i1)
        """
        expected = """
        [i1]
        p3 = force_token()
        p2 = new_with_vtable(descr=vref_descr)
        setfield_gc(p2, p3, descr=virtualtokendescr)
        setfield_gc(p2, NULL, descr=virtualforceddescr)
        escape_n(p2)
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, NULL, descr=virtualtokendescr)
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() []
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_vref_nonvirtual_and_lazy_setfield(self):
        ops = """
        [i1, p1]
        p2 = virtual_ref(p1, 23)
        escape_n(p2)
        virtual_ref_finish(p2, p1)
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        jump(i1, p1)
        """
        expected = """
        [i1, p1]
        p3 = force_token()
        p2 = new_with_vtable(descr=vref_descr)
        setfield_gc(p2, p3, descr=virtualtokendescr)
        setfield_gc(p2, NULL, descr=virtualforceddescr)
        escape_n(p2)
        setfield_gc(p2, p1, descr=virtualforceddescr)
        setfield_gc(p2, NULL, descr=virtualtokendescr)
        call_may_force_n(i1, descr=mayforcevirtdescr)
        guard_not_forced() [i1]
        jump(i1, p1)
        """
        self.optimize_loop(ops, expected)



    # ----------
    def optimize_strunicode_loop(self, ops, optops):
        # check with the arguments passed in
        self.optimize_loop(ops, optops)
        # check with replacing 'str' with 'unicode' everywhere
        self.optimize_loop(ops.replace('str','unicode').replace('s"', 'u"'),
                           optops.replace('str','unicode').replace('s"', 'u"'))

    def test_newstr_1(self):
        ops = """
        [i0]
        p1 = newstr(1)
        strsetitem(p1, 0, i0)
        i1 = strgetitem(p1, 0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_newstr_2(self):
        ops = """
        [i0, i1]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        i2 = strgetitem(p1, 1)
        i3 = strgetitem(p1, 0)
        jump(i2, i3)
        """
        expected = """
        [i0, i1]
        jump(i1, i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_1(self):
        ops = """
        [p1, p2]
        p3 = call_r(0, p1, p2, descr=strconcatdescr)
        jump(p2, p3)
        """
        expected = """
        [p1, p2]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i3 = int_add(i1, i2)
        p3 = newstr(i3)
        copystrcontent(p1, p3, 0, 0, i1)
        copystrcontent(p2, p3, 0, i1, i2)
        jump(p2, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_2(self):
        ops = """
        [p1, p2]
        p3 = call_r(0, s"fo", p1, descr=strconcatdescr)
        escape_n(p3)
        i5 = strgetitem(p3, 0)
        escape_n(i5)
        jump(p2, p3)
        """
        expected = """
        [p1, p2]
        i1 = strlen(p1)
        i0 = int_add(2, i1)
        p5 = newstr(i0)
        strsetitem(p5, 0, 102)
        strsetitem(p5, 1, 111)
        copystrcontent(p1, p5, 0, 2, i1)
        escape_n(p5)
        escape_n(102)
        jump(p2, p5)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_vstr2_str(self):
        ops = """
        [i0, i1, p2]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        p3 = call_r(0, p1, p2, descr=strconcatdescr)
        jump(i1, i0, p3)
        """
        expected = """
        [i0, i1, p2]
        i2 = strlen(p2)
        i3 = int_add(2, i2)
        p3 = newstr(i3)
        strsetitem(p3, 0, i0)
        strsetitem(p3, 1, i1)
        copystrcontent(p2, p3, 0, 2, i2)
        jump(i1, i0, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_vstr2_str_2(self):
        ops = """
        [i0, i1, p2]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        escape_n(p1)
        p3 = call_r(0, p1, p2, descr=strconcatdescr)
        jump(i1, i0, p3)
        """
        expected = """
        [i0, i1, p2]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        escape_n(p1)
        i2 = strlen(p2)
        i3 = int_add(2, i2)
        p3 = newstr(i3)
        strsetitem(p3, 0, i0)
        strsetitem(p3, 1, i1)
        copystrcontent(p2, p3, 0, 2, i2)
        jump(i1, i0, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_str_vstr2(self):
        ops = """
        [i0, i1, p2]
        p1 = newstr(2)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i1)
        p3 = call_r(0, p2, p1, descr=strconcatdescr)
        jump(i1, i0, p3)
        """
        expected = """
        [i0, i1, p2]
        i2 = strlen(p2)
        i3 = int_add(i2, 2)
        p3 = newstr(i3)
        copystrcontent(p2, p3, 0, 0, i2)
        strsetitem(p3, i2, i0)
        i5 = int_add(i2, 1)
        strsetitem(p3, i5, i1)
        jump(i1, i0, p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_str_str_str(self):
        ops = """
        [p1, p2, p3]
        p4 = call_r(0, p1, p2, descr=strconcatdescr)
        p5 = call_r(0, p4, p3, descr=strconcatdescr)
        jump(p2, p3, p5)
        """
        expected = """
        [p1, p2, p3]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i12 = int_add(i1, i2)
        i3 = strlen(p3)
        i123 = int_add(i12, i3)
        p5 = newstr(i123)
        copystrcontent(p1, p5, 0, 0, i1)
        copystrcontent(p2, p5, 0, i1, i2)
        copystrcontent(p3, p5, 0, i12, i3)
        jump(p2, p3, p5)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_str_cstr1(self):
        ops = """
        [p2]
        p3 = call_r(0, p2, s"x", descr=strconcatdescr)
        jump(p3)
        """
        expected = """
        [p2]
        i2 = strlen(p2)
        i3 = int_add(i2, 1)
        p3 = newstr(i3)
        copystrcontent(p2, p3, 0, 0, i2)
        strsetitem(p3, i2, 120)     # == ord('x')
        jump(p3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_consts(self):
        ops = """
        []
        p1 = same_as_r(s"ab")
        p2 = same_as_r(s"cde")
        p3 = call_r(0, p1, p2, descr=strconcatdescr)
        escape_n(p3)
        jump()
        """
        expected = """
        []
        escape_n(s"abcde")
        jump()
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_constant_lengths(self):
        ops = """
        [i0]
        p0 = newstr(1)
        strsetitem(p0, 0, i0)
        p1 = newstr(0)
        p2 = call_r(0, p0, p1, descr=strconcatdescr)
        i1 = call_i(0, p2, p0, descr=strequaldescr)
        finish(i1)
        """
        expected = """
        [i0]
        finish(1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_concat_constant_lengths_2(self):
        ops = """
        [i0]
        p0 = newstr(0)
        p1 = newstr(1)
        strsetitem(p1, 0, i0)
        p2 = call_r(0, p0, p1, descr=strconcatdescr)
        i1 = call_i(0, p2, p1, descr=strequaldescr)
        finish(i1)
        """
        expected = """
        [i0]
        finish(1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_1(self):
        ops = """
        [p1, i1, i2]
        p2 = call_r(0, p1, i1, i2, descr=strslicedescr)
        jump(p2, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        i3 = int_sub(i2, i1)
        p2 = newstr(i3)
        copystrcontent(p1, p2, i1, 0, i3)
        jump(p2, i1, i2)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_2(self):
        ops = """
        [p1, i2]
        p2 = call_r(0, p1, 0, i2, descr=strslicedescr)
        jump(p2, i2)
        """
        expected = """
        [p1, i2]
        p2 = newstr(i2)
        copystrcontent(p1, p2, 0, 0, i2)
        jump(p2, i2)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_3(self):
        ops = """
        [p1, i1, i2, i3, i4]
        p2 = call_r(0, p1, i1, i2, descr=strslicedescr)
        p3 = call_r(0, p2, i3, i4, descr=strslicedescr)
        jump(p3, i1, i2, i3, i4)
        """
        expected = """
        [p1, i1, i2, i3, i4]
        i0 = int_sub(i2, i1)     # killed by the backend
        i5 = int_sub(i4, i3)
        i6 = int_add(i1, i3)
        p3 = newstr(i5)
        copystrcontent(p1, p3, i6, 0, i5)
        jump(p3, i1, i2, i3, i4)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_getitem1(self):
        ops = """
        [p1, i1, i2, i3]
        p2 = call_r(0, p1, i1, i2, descr=strslicedescr)
        i4 = strgetitem(p2, i3)
        escape_n(i4)
        jump(p1, i1, i2, i3)
        """
        expected = """
        [p1, i1, i2, i3]
        i6 = int_sub(i2, i1)      # killed by the backend
        i5 = int_add(i1, i3)
        i4 = strgetitem(p1, i5)
        escape_n(i4)
        jump(p1, i1, i2, i3)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_plain(self):
        ops = """
        [i3, i4]
        p1 = newstr(2)
        strsetitem(p1, 0, i3)
        strsetitem(p1, 1, i4)
        p2 = call_r(0, p1, 1, 2, descr=strslicedescr)
        i5 = strgetitem(p2, 0)
        escape_n(i5)
        jump(i3, i4)
        """
        expected = """
        [i3, i4]
        escape_n(i4)
        jump(i3, i4)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_concat(self):
        ops = """
        [p1, i1, i2, p2]
        p3 = call_r(0, p1, i1, i2, descr=strslicedescr)
        p4 = call_r(0, p3, p2, descr=strconcatdescr)
        jump(p4, i1, i2, p2)
        """
        expected = """
        [p1, i1, i2, p2]
        i3 = int_sub(i2, i1)     # length of p3
        i4 = strlen(p2)
        i5 = int_add(i3, i4)
        p4 = newstr(i5)
        copystrcontent(p1, p4, i1, 0, i3)
        copystrcontent(p2, p4, 0, i3, i4)
        jump(p4, i1, i2, p2)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_slice_plain_virtual(self):
        ops = """
        []
        p0 = newstr(11)
        copystrcontent(s"hello world", p0, 0, 0, 11)
        p1 = call_r(0, p0, 0, 5, descr=strslicedescr)
        finish(p1)
        """
        expected = """
        []
        finish(s"hello")
        """
        self.optimize_strunicode_loop(ops, expected)

    # ----------
    def optimize_strunicode_loop_extradescrs(self, ops, optops):
        self.optimize_strunicode_loop(ops, optops)

    def test_str_equal_noop1(self):
        ops = """
        [p1, p2]
        i0 = call_i(0, p1, p2, descr=strequaldescr)
        escape_n(i0)
        jump(p1, p2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, ops)

    def test_str_equal_noop2(self):
        ops = """
        [p1, p2, p3]
        p4 = call_r(0, p1, p2, descr=strconcatdescr)
        i0 = call_i(0, p3, p4, descr=strequaldescr)
        escape_n(i0)
        jump(p1, p2, p3)
        """
        expected = """
        [p1, p2, p3]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i3 = int_add(i1, i2)
        p4 = newstr(i3)
        copystrcontent(p1, p4, 0, 0, i1)
        copystrcontent(p2, p4, 0, i1, i2)
        i0 = call_i(0, p3, p4, descr=strequaldescr)
        escape_n(i0)
        jump(p1, p2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice1(self):
        ops = """
        [p1, i1, i2, p3]
        p4 = call_r(0, p1, i1, i2, descr=strslicedescr)
        i0 = call_i(0, p4, p3, descr=strequaldescr)
        escape_n(i0)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        i3 = int_sub(i2, i1)
        i0 = call_i(0, p1, i1, i3, p3, descr=streq_slice_checknull_descr)
        escape_n(i0)
        jump(p1, i1, i2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice2(self):
        ops = """
        [p1, i1, i2, p3]
        p4 = call_r(0, p1, i1, i2, descr=strslicedescr)
        i0 = call_i(0, p3, p4, descr=strequaldescr)
        escape_n(i0)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        i4 = int_sub(i2, i1)
        i0 = call_i(0, p1, i1, i4, p3, descr=streq_slice_checknull_descr)
        escape_n(i0)
        jump(p1, i1, i2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice3(self):
        ops = """
        [p1, i1, i2, p3]
        guard_nonnull(p3) []
        p4 = call_r(0, p1, i1, i2, descr=strslicedescr)
        i0 = call_i(0, p3, p4, descr=strequaldescr)
        escape_n(i0)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        guard_nonnull(p3) []
        i4 = int_sub(i2, i1)
        i0 = call_i(0, p1, i1, i4, p3, descr=streq_slice_nonnull_descr)
        escape_n(i0)
        jump(p1, i1, i2, p3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice4(self):
        ops = """
        [p1, i1, i2]
        p3 = call_r(0, p1, i1, i2, descr=strslicedescr)
        i0 = call_i(0, p3, s"x", descr=strequaldescr)
        escape_n(i0)
        jump(p1, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        i3 = int_sub(i2, i1)
        i0 = call_i(0, p1, i1, i3, 120, descr=streq_slice_char_descr)
        escape_n(i0)
        jump(p1, i1, i2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_slice5(self):
        ops = """
        [p1, i1, i2, i3]
        p4 = call_r(0, p1, i1, i2, descr=strslicedescr)
        p5 = newstr(1)
        strsetitem(p5, 0, i3)
        i0 = call_i(0, p5, p4, descr=strequaldescr)
        escape_n(i0)
        jump(p1, i1, i2, i3)
        """
        expected = """
        [p1, i1, i2, i3]
        i4 = int_sub(i2, i1)
        i0 = call_i(0, p1, i1, i4, i3, descr=streq_slice_char_descr)
        escape_n(i0)
        jump(p1, i1, i2, i3)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none1(self):
        ops = """
        [p1]
        i0 = call_i(0, p1, NULL, descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = ptr_eq(p1, NULL)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none2(self):
        ops = """
        [p1]
        i0 = call_i(0, NULL, p1, descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = ptr_eq(p1, NULL)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none3(self):
        ops = """
        []
        p5 = newstr(0)
        i0 = call_i(0, NULL, p5, descr=strequaldescr)
        escape_n(i0)
        jump()
        """
        expected = """
        []
        escape_n(0)
        jump()
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none4(self):
        ops = """
        [p1]
        p5 = newstr(0)
        i0 = call_i(0, p5, p1, descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        # can't optimize more: p1 may be NULL!
        i0 = call_i(0, s"", p1, descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_none5(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        p5 = newstr(0)
        i0 = call_i(0, p5, p1, descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        # p1 is not NULL, so the string comparison (p1=="") becomes:
        i6 = strlen(p1)
        i0 = int_is_zero(i6)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull1(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        i0 = call_i(0, p1, s"hello world", descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        i0 = call_i(0, p1, s"hello world", descr=streq_nonnull_descr)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull2(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        i0 = call_i(0, p1, s"", descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        i1 = strlen(p1)
        i0 = int_is_zero(i1)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull3(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        i0 = call_i(0, p1, s"x", descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        i0 = call_i(0, p1, 120, descr=streq_nonnull_char_descr)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_nonnull4(self):
        ops = """
        [p1, p2]
        p4 = call_r(0, p1, p2, descr=strconcatdescr)
        i0 = call_i(0, s"hello world", p4, descr=strequaldescr)
        escape_n(i0)
        jump(p1, p2)
        """
        expected = """
        [p1, p2]
        i1 = strlen(p1)
        i2 = strlen(p2)
        i3 = int_add(i1, i2)
        p4 = newstr(i3)
        copystrcontent(p1, p4, 0, 0, i1)
        copystrcontent(p2, p4, 0, i1, i2)
        i0 = call_i(0, s"hello world", p4, descr=streq_nonnull_descr)
        escape_n(i0)
        jump(p1, p2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars0(self):
        ops = """
        [i1]
        p1 = newstr(0)
        i0 = call_i(0, p1, s"", descr=strequaldescr)
        escape_n(i0)
        jump(i1)
        """
        expected = """
        [i1]
        escape_n(1)
        jump(i1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars1(self):
        ops = """
        [i1]
        p1 = newstr(1)
        strsetitem(p1, 0, i1)
        i0 = call_i(0, p1, s"x", descr=strequaldescr)
        escape_n(i0)
        jump(i1)
        """
        expected = """
        [i1]
        i0 = int_eq(i1, 120)     # ord('x')
        escape_n(i0)
        jump(i1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars2(self):
        ops = """
        [i1, i2]
        p1 = newstr(2)
        strsetitem(p1, 0, i1)
        strsetitem(p1, 1, i2)
        i0 = call_i(0, p1, s"xy", descr=strequaldescr)
        escape_n(i0)
        jump(i1, i2)
        """
        expected = """
        [i1, i2]
        p1 = newstr(2)
        strsetitem(p1, 0, i1)
        strsetitem(p1, 1, i2)
        i0 = call_i(0, p1, s"xy", descr=streq_lengthok_descr)
        escape_n(i0)
        jump(i1, i2)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_chars3(self):
        ops = """
        [p1]
        i0 = call_i(0, s"x", p1, descr=strequaldescr)
        escape_n(i0)
        jump(p1)
        """
        expected = """
        [p1]
        i0 = call_i(0, p1, 120, descr=streq_checknull_char_descr)
        escape_n(i0)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str_equal_lengthmismatch1(self):
        ops = """
        [i1]
        p1 = newstr(1)
        strsetitem(p1, 0, i1)
        i0 = call_i(0, s"xy", p1, descr=strequaldescr)
        escape_n(i0)
        jump(i1)
        """
        expected = """
        [i1]
        escape_n(0)
        jump(i1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str2unicode_constant(self):
        ops = """
        []
        p0 = call_r(0, "xy", descr=s2u_descr)      # string -> unicode
        escape_n(p0)
        jump()
        """
        expected = """
        []
        escape_n(u"xy")
        jump()
        """
        self.optimize_strunicode_loop_extradescrs(ops, expected)

    def test_str2unicode_nonconstant(self):
        ops = """
        [p0]
        p1 = call_r(0, p0, descr=s2u_descr)      # string -> unicode
        escape_n(p1)
        jump(p1)
        """
        self.optimize_strunicode_loop_extradescrs(ops, ops)
        # more generally, supporting non-constant but virtual cases is
        # not obvious, because of the exception UnicodeDecodeError that
        # can be raised by ll_str2unicode()

    def test_strgetitem_repeated(self):
        ops = """
        [p0, i0]
        i1 = strgetitem(p0, i0)
        i2 = strgetitem(p0, i0)
        i3 = int_eq(i1, i2)
        guard_true(i3) []
        escape_n(i2)
        jump(p0, i0)
        """
        expected = """
        [p0, i0]
        i1 = strgetitem(p0, i0)
        escape_n(i1)
        jump(p0, i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_strslice_subtraction_folds(self):
        ops = """
        [p0, i0]
        i1 = int_add(i0, 1)
        p1 = call_r(0, p0, i0, i1, descr=strslicedescr)
        escape_n(p1)
        jump(p0, i1)
        """
        expected = """
        [p0, i0]
        i1 = int_add(i0, 1)
        p1 = newstr(1)
        i2 = strgetitem(p0, i0)
        strsetitem(p1, 0, i2)
        escape_n(p1)
        jump(p0, i1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_float_mul_reversed(self):
        ops = """
        [f0, f1]
        f2 = float_mul(f0, f1)
        f3 = float_mul(f1, f0)
        jump(f2, f3)
        """
        expected = """
        [f0, f1]
        f2 = float_mul(f0, f1)
        jump(f2, f2)
        """
        self.optimize_loop(ops, expected)

    def test_null_char_str(self):
        ops = """
        [p0]
        p1 = newstr(4)
        strsetitem(p1, 2, 0)
        setfield_gc(p0, p1, descr=valuedescr)
        jump(p0)
        """
        # This test is slightly bogus: the string is not fully initialized.
        # I *think* it is still right to not have a series of extra
        # strsetitem(p1, idx, 0).  We do preserve the single one from the
        # source, though.
        expected = """
        [p0]
        p1 = newstr(4)
        strsetitem(p1, 2, 0)
        setfield_gc(p0, p1, descr=valuedescr)
        jump(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_newstr_strlen(self):
        ops = """
        [i0]
        p0 = newstr(i0)
        escape_n(p0)
        i1 = strlen(p0)
        i2 = int_add(i1, 1)
        jump(i2)
        """
        expected = """
        [i0]
        p0 = newstr(i0)
        escape_n(p0)
        i1 = int_add(i0, 1)
        jump(i1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_bounded_lazy_setfield(self):
        ops = """
        [p0, i0]
        i1 = int_gt(i0, 2)
        guard_true(i1) []
        setarrayitem_gc(p0, 0, 3, descr=arraydescr)
        setarrayitem_gc(p0, 2, 4, descr=arraydescr)
        setarrayitem_gc(p0, i0, 15, descr=arraydescr)
        i2 = getarrayitem_gc_i(p0, 2, descr=arraydescr)
        jump(p0, i2)
        """
        # Remove the getarrayitem_gc, because we know that p[i0] does not alias
        # p0[2]
        expected = """
        [p0, i0]
        i1 = int_gt(i0, 2)
        guard_true(i1) []
        setarrayitem_gc(p0, i0, 15, descr=arraydescr)
        setarrayitem_gc(p0, 0, 3, descr=arraydescr)
        setarrayitem_gc(p0, 2, 4, descr=arraydescr)
        jump(p0, 4)
        """
        self.optimize_loop(ops, expected)

    def test_empty_copystrunicontent(self):
        ops = """
        [p0, p1, i0, i2, i3]
        i4 = int_eq(i3, 0)
        guard_true(i4) []
        copystrcontent(p0, p1, i0, i2, i3)
        jump(p0, p1, i0, i2, i3)
        """
        expected = """
        [p0, p1, i0, i2, i3]
        i4 = int_is_zero(i3)
        guard_true(i4) []
        jump(p0, p1, i0, i2, 0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_empty_copystrunicontent_virtual(self):
        ops = """
        [p0]
        p1 = newstr(23)
        copystrcontent(p0, p1, 0, 0, 0)
        jump(p0)
        """
        expected = """
        [p0]
        jump(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_plain_virtual_string_copy_content(self):
        ops = """
        [i1]
        p0 = newstr(6)
        copystrcontent(s"hello!", p0, 0, 0, 6)
        p1 = call_r(0, p0, s"abc123", descr=strconcatdescr)
        i0 = strgetitem(p1, i1)
        finish(i0)
        """
        expected = """
        [i1]
        i0 = strgetitem(s"hello!abc123", i1)
        finish(i0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_plain_virtual_string_copy_content_2(self):
        ops = """
        []
        p0 = newstr(6)
        copystrcontent(s"hello!", p0, 0, 0, 6)
        p1 = call_r(0, p0, s"abc123", descr=strconcatdescr)
        i0 = strgetitem(p1, 0)
        finish(i0)
        """
        expected = """
        []
        finish(104)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_nonvirtual_newstr_strlen(self):
        ops = """
        [p0]
        p1 = call_r(0, p0, s"X", descr=strconcatdescr)
        i0 = strlen(p1)
        finish(i0)
        """
        expected = """
        [p0]
        i2 = strlen(p0)
        i4 = int_add(i2, 1)
        finish(i4)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_copy_long_string_to_virtual(self):
        ops = """
        []
        p0 = newstr(20)
        copystrcontent(s"aaaaaaaaaaaaaaaaaaaa", p0, 0, 0, 20)
        jump(p0)
        """
        expected = """
        []
        jump(s"aaaaaaaaaaaaaaaaaaaa")
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_ptr_eq_str_constant(self):
        ops = """
        []
        i0 = ptr_eq(s"abc", s"\x00")
        finish(i0)
        """
        expected = """
        []
        finish(0)
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail
    def test_known_equal_ints(self):
        ops = """
        [i0, i1, i2, p0]
        i3 = int_eq(i0, i1)
        guard_true(i3) []

        i4 = int_lt(i2, i0)
        guard_true(i4) []
        i5 = int_lt(i2, i1)
        guard_true(i5) []

        i6 = getarrayitem_gc_i(p0, i2, descr=chararraydescr)
        finish(i6)
        """
        expected = """
        [i0, i1, i2, p0]
        i3 = int_eq(i0, i1)
        guard_true(i3) []

        i4 = int_lt(i2, i0)
        guard_true(i4) []

        i6 = getarrayitem_gc_i(p0, i3, descr=chararraydescr)
        finish(i6)
        """
        self.optimize_loop(ops, expected)

    def test_str_copy_virtual(self):
        ops = """
        [i0]
        p0 = newstr(8)
        strsetitem(p0, 0, i0)
        strsetitem(p0, 1, i0)
        strsetitem(p0, 2, i0)
        strsetitem(p0, 3, i0)
        strsetitem(p0, 4, i0)
        strsetitem(p0, 5, i0)
        strsetitem(p0, 6, i0)
        strsetitem(p0, 7, i0)
        p1 = newstr(12)
        copystrcontent(p0, p1, 0, 0, 8)
        strsetitem(p1, 8, 3)
        strsetitem(p1, 9, 0)
        strsetitem(p1, 10, 0)
        strsetitem(p1, 11, 0)
        finish(p1)
        """
        expected = """
        [i0]
        p1 = newstr(12)
        strsetitem(p1, 0, i0)
        strsetitem(p1, 1, i0)
        strsetitem(p1, 2, i0)
        strsetitem(p1, 3, i0)
        strsetitem(p1, 4, i0)
        strsetitem(p1, 5, i0)
        strsetitem(p1, 6, i0)
        strsetitem(p1, 7, i0)
        strsetitem(p1, 8, 3)
        strsetitem(p1, 9, 0)
        strsetitem(p1, 10, 0)
        strsetitem(p1, 11, 0)
        finish(p1)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_copy_constant_virtual(self):
        ops = """
        []
        p0 = newstr(10)
        copystrcontent(s"abcd", p0, 0, 0, 4)
        strsetitem(p0, 4, 101)
        copystrcontent(s"fghij", p0, 0, 5, 5)
        finish(p0)
        """
        expected = """
        []
        finish(s"abcdefghij")
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_copy_virtual_src_concrete_dst(self):
        ops = """
        [p0]
        p1 = newstr(2)
        strsetitem(p1, 0, 101)
        strsetitem(p1, 1, 102)
        copystrcontent(p1, p0, 0, 0, 2)
        finish(p0)
        """
        expected = """
        [p0]
        strsetitem(p0, 0, 101)
        strsetitem(p0, 1, 102)
        finish(p0)
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_str_copy_bug1(self):
        ops = """
        [i0]
        p1 = newstr(1)
        strsetitem(p1, 0, i0)
        p2 = newstr(1)
        escape_n(p2)
        copystrcontent(p1, p2, 0, 0, 1)
        finish()
        """
        expected = """
        [i0]
        p2 = newstr(1)
        escape_n(p2)
        strsetitem(p2, 0, i0)
        finish()
        """
        self.optimize_strunicode_loop(ops, expected)

    def test_call_pure_vstring_const(self):
        ops = """
        []
        p0 = newstr(3)
        strsetitem(p0, 0, 97)
        strsetitem(p0, 1, 98)
        strsetitem(p0, 2, 99)
        i0 = call_pure_i(123, p0, descr=nonwritedescr)
        finish(i0)
        """
        expected = """
        []
        finish(5)
        """
        call_pure_results = {
            (ConstInt(123), get_const_ptr_for_string("abc"),): ConstInt(5),
        }
        self.optimize_loop(ops, expected, call_pure_results)

    def test_call_pure_quasiimmut(self):
        ops = """
        []
        quasiimmut_field(ConstPtr(quasiptr), descr=quasiimmutdescr)
        guard_not_invalidated() []
        i0 = getfield_gc_i(ConstPtr(quasiptr), descr=quasifielddescr)
        i1 = call_pure_i(123, i0, descr=nonwritedescr)
        finish(i1)
        """
        expected = """
        []
        guard_not_invalidated() []
        finish(5)
        """
        call_pure_results = {
            (ConstInt(123), ConstInt(-4247)): ConstInt(5),
        }
        self.optimize_loop(ops, expected, call_pure_results)

    def test_guard_not_forced_2_virtual(self):
        ops = """
        [i0]
        p0 = new_array(3, descr=arraydescr)
        guard_not_forced_2() [p0]
        finish(p0)
        """
        self.optimize_loop(ops, ops)

    def test_getfield_cmp_above_bounds(self):
        ops = """
        [p0]
        i0 = getfield_gc_i(p0, descr=chardescr)
        i1 = int_lt(i0, 256)
        guard_true(i1) []
        """

        expected = """
        [p0]
        i0 = getfield_gc_i(p0, descr=chardescr)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_cmp_below_bounds(self):
        ops = """
        [p0]
        i0 = getfield_gc_i(p0, descr=chardescr)
        i1 = int_gt(i0, -1)
        guard_true(i1) []
        """

        expected = """
        [p0]
        i0 = getfield_gc_i(p0, descr=chardescr)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_cmp_in_bounds(self):
        ops = """
        [p0]
        i0 = getfield_gc_i(p0, descr=chardescr)
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 255)
        guard_true(i2) []
        """
        self.optimize_loop(ops, ops)

    def test_getfieldraw_cmp_outside_bounds(self):
        ops = """
        [p0]
        i0 = getfield_raw_i(p0, descr=chardescr)
        i1 = int_gt(i0, -1)
        guard_true(i1) []
        """

        expected = """
        [p0]
        i0 = getfield_raw_i(p0, descr=chardescr)
        """
        self.optimize_loop(ops, expected)


    def test_rawarray_cmp_outside_intbounds(self):
        ops = """
        [i0]
        i1 = getarrayitem_raw_i(i0, 0, descr=rawarraydescr_char)
        i2 = int_lt(i1, 256)
        guard_true(i2) []
        """

        expected = """
        [i0]
        i1 = getarrayitem_raw_i(i0, 0, descr=rawarraydescr_char)
        """
        self.optimize_loop(ops, expected)

    def test_gcarray_outside_intbounds(self):
        ops = """
        [p0]
        i0 = getarrayitem_gc_i(p0, 0, descr=chararraydescr)
        i1 = int_lt(i0, 256)
        guard_true(i1) []
        """

        expected = """
        [p0]
        i0 = getarrayitem_gc_i(p0, 0, descr=chararraydescr)
        """
        self.optimize_loop(ops, expected)

    def test_getinterior_outside_intbounds(self):
        ops = """
        [p0]
        f0 = getinteriorfield_gc_f(p0, 0, descr=fc_array_floatdescr)
        i0 = getinteriorfield_gc_i(p0, 0, descr=fc_array_chardescr)
        i1 = int_lt(i0, 256)
        guard_true(i1) []
        """

        expected = """
        [p0]
        f0 = getinteriorfield_gc_f(p0, 0, descr=fc_array_floatdescr)
        i0 = getinteriorfield_gc_i(p0, 0, descr=fc_array_chardescr)
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail
    def test_consecutive_getinteriorfields(self):
        ops = """
        [p0, i0]
        i1 = getinteriorfield_gc_i(p0, i0, descr=valuedescr)
        i2 = getinteriorfield_gc_i(p0, i0, descr=valuedescr)
        jump(i1, i2)
        """
        expected = """
        [p0, i0]
        i1 = getinteriorfield_gc_i(p0, i0, descr=valuedescr)
        jump(i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_replace_result_of_new(self):
        ops = """
        [i0]
        guard_value(i0, 2) []
        p0 = newstr(i0)
        escape_n(p0)
        finish()
        """
        expected = """
        [i0]
        guard_value(i0, 2) []
        p0 = newstr(2)
        escape_n(p0)
        finish()
        """
        self.optimize_loop(ops, expected)

    def test_dirty_array_field_after_force(self):
        ops = """
        []
        p0 = new_array(1, descr=arraydescr)
        setarrayitem_gc(p0, 0, 0, descr=arraydescr)
        escape_n(p0) # force
        call_may_force_n(1, descr=mayforcevirtdescr)
        i1 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        finish(i1)
        """
        self.optimize_loop(ops, ops)

    def test_dirty_array_of_structs_field_after_force(self):
        ops = """
        []
        p0 = new_array_clear(1, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, 0.0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, 0.0, descr=compleximagdescr)
        escape_n(p0) # force
        call_may_force_n(1, descr=mayforcevirtdescr)
        f1 = getinteriorfield_gc_f(p0, 0, descr=compleximagdescr)
        finish(f1)
        """
        self.optimize_loop(ops, ops)

    def test_random_call_forcing_strgetitem(self):
        ops = """
        [p3, i15]
        i13 = strgetitem(p3, i15)
        p0 = newstr(1)
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p2, p0, descr=otherdescr)
        strsetitem(p0, 0, i13)
        i2 = strgetitem(p0, 0)
        i3 = call_pure_i(1, i2, descr=nonwritedescr)
        finish(i3)
        """
        expected = """
        [p3, i15]
        i13 = strgetitem(p3, i15)
        i3 = call_i(1, i13, descr=nonwritedescr)
        finish(i3)
        """
        self.optimize_loop(ops, expected)

    def test_float_guard_value(self):
        ops = """
        [f0]
        guard_value(f0, 3.5) []
        guard_value(f0, 3.5) []
        finish(f0)
        """
        expected = """
        [f0]
        guard_value(f0, 3.5) []
        finish(3.5)
        """
        self.optimize_loop(ops, expected)

    def test_getarrayitem_gc_pure_not_invalidated(self):
        ops = """
        [p0]
        i1 = getarrayitem_gc_pure_i(p0, 1, descr=arrayimmutdescr)
        escape_n(p0)
        i2 = getarrayitem_gc_pure_i(p0, 1, descr=arrayimmutdescr)
        escape_n(i2)
        jump(p0)
        """
        expected = """
        [p0]
        i1 = getarrayitem_gc_pure_i(p0, 1, descr=arrayimmutdescr)
        escape_n(p0)
        escape_n(i1)
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_force_virtual_write(self):
        ops = """
        [i1, i2]
        p1 = new(descr=ssize)
        setfield_gc(p1, i1, descr=adescr)
        setfield_gc(p1, i2, descr=bdescr)
        call_n(123, p1, descr=writeadescr)
        i3 = getfield_gc_i(p1, descr=bdescr)
        finish(i3)
        """
        expected = """
        [i1, i2]
        p1 = new(descr=ssize)
        setfield_gc(p1, i1, descr=adescr)
        call_n(123, p1, descr=writeadescr)
        setfield_gc(p1, i2, descr=bdescr)
        finish(i2)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_gc_type(self):
        ops = """
        [p0, p1]
        setarrayitem_gc(p0, 1, p1, descr=gcarraydescr)
        guard_gc_type(p0, ConstInt(gcarraydescr_tid)) []
        """
        expected = """
        [p0, p1]
        setarrayitem_gc(p0, 1, p1, descr=gcarraydescr)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_is_object_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        guard_is_object(p0) []
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_is_object_2(self):
        ops = """
        [p0]
        i1 = getfield_gc_i(p0, descr=valuedescr)
        guard_is_object(p0) []
        finish(i1)
        """
        expected = """
        [p0]
        i1 = getfield_gc_i(p0, descr=valuedescr)
        finish(i1)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_subclass_1(self):
        ops = """
        [p0]
        i1 = getfield_gc_i(p0, descr=valuedescr)
        guard_subclass(p0, ConstClass(node_vtable)) []
        finish(i1)
        """
        expected = """
        [p0]
        i1 = getfield_gc_i(p0, descr=valuedescr)
        finish(i1)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_subclass_2(self):
        ops = """
        [p0]
        p1 = getfield_gc_i(p0, descr=otherdescr)
        guard_subclass(p0, ConstClass(node_vtable)) []
        finish(p1)
        """
        expected = """
        [p0]
        p1 = getfield_gc_i(p0, descr=otherdescr)
        finish(p1)
        """
        self.optimize_loop(ops, expected)

    def test_nonnull_str2unicode(self):
        ops = """
        [p0]
        guard_nonnull(p0) []
        p1 = call_r(0, p0, descr=s2u_descr)      # string -> unicode
        finish(p1)
        """
        self.optimize_loop(ops, ops)

    def test_random_strange_guards_on_consts(self):
        ops = """
        [p0]
        guard_value(p0, ConstPtr(nodeaddr)) []
        guard_is_object(p0) []
        guard_subclass(p0, ConstClass(node_vtable)) []
        guard_gc_type(p0, ConstInt(node_tid)) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_value(p0, ConstPtr(nodeaddr)) []
        jump(ConstPtr(nodeaddr))
        """
        self.optimize_loop(ops, expected)

    def test_remove_multiple_setarrayitems(self):
        ops = """
        [p0, i1]
        setarrayitem_gc(p0, 2, NULL, descr=gcarraydescr)
        guard_value(i1, 42) []
        setarrayitem_gc(p0, 2, NULL, descr=gcarraydescr)   # remove this
        finish()
        """
        expected = """
        [p0, i1]
        setarrayitem_gc(p0, 2, NULL, descr=gcarraydescr)
        guard_value(i1, 42) []
        finish()
        """
        self.optimize_loop(ops, expected)

    def test_assert_not_none(self):
        ops = """
        [p0]
        assert_not_none(p0)
        guard_nonnull(p0) []
        finish()
        """
        expected = """
        [p0]
        finish()
        """
        self.optimize_loop(ops, expected)

    def test_convert_float_bytes_to_longlong(self):
        ops = """
        [f0, i0]
        i1 = convert_float_bytes_to_longlong(f0)
        f1 = convert_longlong_bytes_to_float(i1)
        escape_f(f1)

        f2 = convert_longlong_bytes_to_float(i0)
        i2 = convert_float_bytes_to_longlong(f2)
        escape_i(i2)
        """

        expected = """
        [f0, i0]
        i1 = convert_float_bytes_to_longlong(f0)
        escape_f(f0)

        f2 = convert_longlong_bytes_to_float(i0)
        escape_i(i0)
        """
        self.optimize_loop(ops, expected)


    def test_float_abs_abs_folds_to_abs(self):
        ops = """
        [f1]
        f2 = float_abs(f1)
        f3 = float_abs(f2)
        f4 = float_abs(f3)
        escape_f(f3)
        """
        expected = """
        [f1]
        f2 = float_abs(f1)
        escape_f(f2)
        """
        self.optimize_loop(ops, expected)

