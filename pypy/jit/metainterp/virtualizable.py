from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython import rvirtualizable2
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.nonconst import NonConstant
from pypy.jit.metainterp.typesystem import deref, fieldType, arrayItem
from pypy.jit.metainterp import history
from pypy.jit.metainterp.warmstate import wrap, unwrap


class VirtualizableInfo:
    TOKEN_NONE            = 0
    TOKEN_TRACING_RESCALL = -1

    def __init__(self, warmrunnerdesc):
        self.warmrunnerdesc = warmrunnerdesc
        jitdriver = warmrunnerdesc.jitdriver
        cpu = warmrunnerdesc.cpu
        if cpu.ts.name == 'ootype':
            import py
            py.test.skip("ootype: fix virtualizables")
        self.cpu = cpu
        self.BoxArray = cpu.ts.BoxRef
        #
        assert len(jitdriver.virtualizables) == 1    # for now
        [vname] = jitdriver.virtualizables
        index = len(jitdriver.greens) + jitdriver.reds.index(vname)
        self.index_of_virtualizable = index
        VTYPEPTR = warmrunnerdesc.JIT_ENTER_FUNCTYPE.ARGS[index]
        while 'virtualizable2_accessor' not in deref(VTYPEPTR)._hints:
            VTYPEPTR = cpu.ts.get_superclass(VTYPEPTR)
        self.VTYPEPTR = VTYPEPTR
        self.VTYPE = VTYPE = deref(VTYPEPTR)
        self.vable_token_descr = cpu.fielddescrof(VTYPE, 'vable_token')
        #
        accessor = VTYPE._hints['virtualizable2_accessor']
        all_fields = accessor.fields
        static_fields = []
        array_fields = []
        for name, suffix in all_fields.iteritems():
            if suffix == '[*]':
                array_fields.append(name)
            else:
                static_fields.append(name)
        self.static_fields = static_fields
        self.array_fields = array_fields
        #
        FIELDTYPES = [fieldType(VTYPE, name) for name in static_fields]
        ARRAYITEMTYPES = []
        for name in array_fields:
            ARRAYPTR = fieldType(VTYPE, name)
            ARRAY = deref(ARRAYPTR)
            assert isinstance(ARRAYPTR, (lltype.Ptr, ootype.Array))
            assert isinstance(ARRAY, (lltype.GcArray, ootype.Array))
            ARRAYITEMTYPES.append(arrayItem(ARRAY))
        self.array_descrs = [cpu.arraydescrof(deref(fieldType(VTYPE, name)))
                             for name in array_fields]
        #
        self.num_static_extra_boxes = len(static_fields)
        self.num_arrays = len(array_fields)
        self.static_field_to_extra_box = dict(
            [(name, i) for (i, name) in enumerate(static_fields)])
        self.array_field_counter = dict(
            [(name, i) for (i, name) in enumerate(array_fields)])
        self.static_extra_types = [history.getkind(TYPE)
                                   for TYPE in FIELDTYPES]
        self.arrayitem_extra_types = [history.getkind(ITEM)
                                      for ITEM in ARRAYITEMTYPES]
        self.static_field_descrs = [cpu.fielddescrof(VTYPE, name)
                                    for name in static_fields]
        self.array_field_descrs = [cpu.fielddescrof(VTYPE, name)
                                   for name in array_fields]
        #
        getlength = cpu.ts.getlength
        getarrayitem = cpu.ts.getarrayitem
        setarrayitem = cpu.ts.setarrayitem
        #
        def read_boxes(cpu, virtualizable):
            boxes = []
            for _, fieldname in unroll_static_fields:
                x = getattr(virtualizable, fieldname)
                boxes.append(wrap(cpu, x))
            for _, fieldname in unroll_array_fields:
                lst = getattr(virtualizable, fieldname)
                for i in range(getlength(lst)):
                    boxes.append(wrap(cpu, getarrayitem(lst, i)))
            return boxes
        #
        def write_boxes(virtualizable, boxes):
            i = 0
            for FIELDTYPE, fieldname in unroll_static_fields:
                x = unwrap(FIELDTYPE, boxes[i])
                setattr(virtualizable, fieldname, x)
                i = i + 1
            for ARRAYITEMTYPE, fieldname in unroll_array_fields:
                lst = getattr(virtualizable, fieldname)
                for j in range(getlength(lst)):
                    x = unwrap(ARRAYITEMTYPE, boxes[i])
                    setarrayitem(lst, j, x)
                    i = i + 1
            assert len(boxes) == i + 1
        #
        def check_boxes(virtualizable, boxes):
            # for debugging
            i = 0
            for FIELDTYPE, fieldname in unroll_static_fields:
                x = unwrap(FIELDTYPE, boxes[i])
                assert getattr(virtualizable, fieldname) == x
                i = i + 1
            for ARRAYITEMTYPE, fieldname in unroll_array_fields:
                lst = getattr(virtualizable, fieldname)
                for j in range(getlength(lst)):
                    x = unwrap(ARRAYITEMTYPE, boxes[i])
                    assert getarrayitem(lst, j) == x
                    i = i + 1
            assert len(boxes) == i + 1
        #
        def get_index_in_array(virtualizable, arrayindex, index):
            index += self.num_static_extra_boxes
            j = 0
            for _, fieldname in unroll_array_fields:
                if arrayindex == j:
                    return index
                lst = getattr(virtualizable, fieldname)
                index += getlength(lst)
                j = j + 1
            assert False, "invalid arrayindex"
        #
        def get_array_length(virtualizable, arrayindex):
            j = 0
            for _, fieldname in unroll_array_fields:
                if arrayindex == j:
                    lst = getattr(virtualizable, fieldname)
                    return getlength(lst)
                j = j + 1
            assert False, "invalid arrayindex"
        #
        unroll_static_fields = unrolling_iterable(zip(FIELDTYPES,
                                                      static_fields))
        unroll_array_fields = unrolling_iterable(zip(ARRAYITEMTYPES,
                                                     array_fields))
        self.read_boxes = read_boxes
        self.write_boxes = write_boxes
        self.check_boxes = check_boxes
        self.get_index_in_array = get_index_in_array
        self.get_array_length = get_array_length

    def _freeze_(self):
        return True

    def finish(self):
        #
        def force_virtualizable_if_necessary(virtualizable):
            if virtualizable.vable_token:
                self.force_now(virtualizable)
        force_virtualizable_if_necessary._always_inline_ = True
        #
        all_graphs = self.warmrunnerdesc.translator.graphs
        ts = self.warmrunnerdesc.cpu.ts
        (_, FUNCPTR) = ts.get_FuncType([self.VTYPEPTR], lltype.Void)
        funcptr = self.warmrunnerdesc.helper_func(
            FUNCPTR, force_virtualizable_if_necessary)
        rvirtualizable2.replace_force_virtualizable_with_call(
            all_graphs, self.VTYPEPTR, funcptr)

    def unwrap_virtualizable_box(self, virtualizable_box):
        return virtualizable_box.getref(self.VTYPEPTR)

    def cast_to_vtype(self, virtualizable):
        return self.cpu.ts.cast_to_instance_maybe(self.VTYPEPTR, virtualizable)
    cast_to_vtype._annspecialcase_ = 'specialize:ll'

    def is_vtypeptr(self, TYPE):
        return rvirtualizable2.match_virtualizable_type(TYPE, self.VTYPEPTR)

    def reset_vable_token(self, virtualizable):
        virtualizable.vable_token = self.TOKEN_NONE

    def clear_vable_token(self, virtualizable):
        if virtualizable.vable_token:
            self.force_now(virtualizable)
            assert not virtualizable.vable_token

    def tracing_before_residual_call(self, virtualizable):
        assert not virtualizable.vable_token
        virtualizable.vable_token = self.TOKEN_TRACING_RESCALL

    def tracing_after_residual_call(self, virtualizable):
        if virtualizable.vable_token:
            # not modified by the residual call; assert that it is still
            # set to TOKEN_TRACING_RESCALL and clear it.
            assert virtualizable.vable_token == self.TOKEN_TRACING_RESCALL
            virtualizable.vable_token = self.TOKEN_NONE
            return False
        else:
            # marker "modified during residual call" set.
            return True

    def force_now(self, virtualizable):
        token = virtualizable.vable_token
        if token == self.TOKEN_TRACING_RESCALL:
            # The values in the virtualizable are always correct during
            # tracing.  We only need to reset vable_token to TOKEN_NONE
            # as a marker for the tracing, to tell it that this
            # virtualizable escapes.
            virtualizable.vable_token = self.TOKEN_NONE
        else:
            from pypy.jit.metainterp.compile import ResumeGuardForcedDescr
            ResumeGuardForcedDescr.force_now(self.cpu, token)
            assert virtualizable.vable_token == self.TOKEN_NONE
    force_now._dont_inline_ = True

    def forced_vable(self, virtualizable_boxes):
        virtualizable_box = virtualizable_boxes[-1]
        virtualizable = self.unwrap_virtualizable_box(virtualizable_box)
        self.write_boxes(virtualizable, virtualizable_boxes)
        virtualizable.vable_token = self.TOKEN_NONE

# ____________________________________________________________
#
# The 'vable_token' field of a virtualizable is either 0, -1, or points
# into the CPU stack to a particular field in the current frame.  It is:
#
#   1. 0 (TOKEN_NONE) if not in the JIT at all, except as described below.
#
#   2. equal to 0 when tracing is in progress; except:
#
#   3. equal to -1 (TOKEN_TRACING_RESCALL) during tracing when we do a
#      residual call, calling random unknown other parts of the interpreter;
#      it is reset to 0 as soon as something occurs to the virtualizable.
#
#   4. when running the machine code with a virtualizable, it is set
#      to the address in the CPU stack by the FORCE_TOKEN operation.
