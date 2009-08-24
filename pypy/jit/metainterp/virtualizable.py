from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_instance_to_base_obj
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython import rvirtualizable2
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.typesystem import deref
from pypy.jit.metainterp import history
from pypy.jit.metainterp.warmspot import wrap, unwrap


class VirtualizableInfo:
    def __init__(self, warmrunnerdesc):
        self.warmrunnerdesc = warmrunnerdesc
        jitdriver = warmrunnerdesc.jitdriver
        cpu = warmrunnerdesc.cpu
        self.is_oo = cpu.is_oo
        if not self.is_oo:
            from pypy.rpython.lltypesystem.rvirtualizable2 import VABLERTIPTR
            self.VABLERTI = VABLERTIPTR
            self.null_vable_rti = lltype.nullptr(VABLERTIPTR.TO)
            self.BoxArray = history.BoxPtr
        else:
            from pypy.rpython.ootypesystem.rvirtualizable2 import VABLERTI
            self.VABLERTI = VABLERTI
            self.null_vable_rti = ootype.make_null_instance(VABLERTI)
            self.BoxArray = history.BoxObj
        #
        assert len(jitdriver.virtualizables) == 1    # for now
        [vname] = jitdriver.virtualizables
        index = len(jitdriver.greens) + jitdriver.reds.index(vname)
        self.index_of_virtualizable = index
        VTYPEPTR = warmrunnerdesc.JIT_ENTER_FUNCTYPE.ARGS[index]
        while 'virtualizable2_accessor' not in deref(VTYPEPTR)._hints:
            if not self.is_oo:
                VTYPEPTR = lltype.Ptr(VTYPEPTR.TO._first_struct()[1])
            else:
                VTYPEPTR = VTYPEPTR._superclass
        self.VTYPEPTR = VTYPEPTR
        self.VTYPE = VTYPE = deref(VTYPEPTR)
        if not self.is_oo:
            self.null_vable = lltype.nullptr(VTYPE)
        else:
            self.null_vable = ootype.null(VTYPE)
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
        if not self.is_oo:    # lltype
            assert isinstance(VTYPEPTR, lltype.Ptr)
            FIELDTYPES = [getattr(VTYPE, name) for name in static_fields]
            ARRAYITEMTYPES = []
            for name in array_fields:
                ARRAYPTR = getattr(VTYPE, name)
                assert isinstance(ARRAYPTR, lltype.Ptr)
                assert isinstance(ARRAYPTR.TO, lltype.GcArray)
                ARRAYITEMTYPES.append(ARRAYPTR.TO.OF)
            self.array_descrs = [cpu.arraydescrof(getattr(VTYPE, name).TO)
                                 for name in array_fields]
        else:                 # ootype
            FIELDTYPES = [VTYPE._field_type(name) for name in static_fields]
            ARRAYITEMTYPES = []
            for name in array_fields:
                ARRAY = VTYPE._field_type(name)
                assert isinstance(ARRAY, ootype.Array)
                ARRAYITEMTYPES.append(ARRAY.ITEM)
            self.array_descrs = [cpu.arraydescrof(VTYPE._field_type(name))
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
        getlength = warmrunnerdesc.ts.getlength
        getarrayitem = warmrunnerdesc.ts.getarrayitem
        setarrayitem = warmrunnerdesc.ts.setarrayitem
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
        def force_if_necessary(virtualizable):
            if virtualizable.vable_rti:
                self.force_now(virtualizable)
        force_if_necessary._always_inline_ = True
        #
        all_graphs = self.warmrunnerdesc.translator.graphs
        ts = self.warmrunnerdesc.ts
        (_, FUNCPTR) = ts.get_FuncType([self.VTYPEPTR], lltype.Void)
        funcptr = self.warmrunnerdesc.helper_func(FUNCPTR, force_if_necessary)
        rvirtualizable2.replace_promote_virtualizable_with_call(
            all_graphs, self.VTYPEPTR, funcptr)

    def unwrap_virtualizable_box(self, virtualizable_box):
        if not self.is_oo:
            return virtualizable_box.getptr(self.VTYPEPTR)
        else:
            obj = virtualizable_box.getobj()
            return ootype.cast_from_object(self.VTYPE, obj)

    def cast_to_vtype(self, virtualizable):
        if not self.is_oo:
            return lltype.cast_pointer(self.VTYPEPTR, virtualizable)
        else:
            return virtualizable
    cast_to_vtype._annspecialcase_ = 'specialize:ll'

    def is_vtypeptr(self, TYPE):
        return rvirtualizable2.match_virtualizable_type(TYPE, self.VTYPEPTR)

    def cast_instance_to_base_ptr(self, vable_rti):
        if we_are_translated():
            if not self.is_oo:
                return cast_instance_to_base_ptr(vable_rti)
            else:
                return cast_instance_to_base_obj(vable_rti)
        else:
            vable_rti._TYPE = self.VABLERTI   # hack for non-translated mode
            return vable_rti

    def clear_vable_rti(self, virtualizable):
        if virtualizable.vable_rti:
            self.force_now(virtualizable)
            assert not virtualizable.vable_rti

    def tracing_before_residual_call(self, virtualizable):
        assert not virtualizable.vable_rti
        ptr = self.cast_instance_to_base_ptr(tracing_vable_rti)
        virtualizable.vable_rti = ptr

    def tracing_after_residual_call(self, virtualizable):
        if virtualizable.vable_rti:
            # not modified by the residual call; assert that it is still
            # set to 'tracing_vable_rti' and clear it.
            ptr = self.cast_instance_to_base_ptr(tracing_vable_rti)
            assert virtualizable.vable_rti == ptr
            virtualizable.vable_rti = self.null_vable_rti
            return False
        else:
            # marker "modified during residual call" set.
            return True

    def force_now(self, virtualizable):
        rti = virtualizable.vable_rti
        virtualizable.vable_rti = self.null_vable_rti
        if we_are_translated():
            rti = cast_base_ptr_to_instance(AbstractVableRti, rti)
        rti.force_now(virtualizable)
    force_now._dont_inline_ = True

# ____________________________________________________________
#
# The 'vable_rti' field of a virtualizable is either NULL or points
# to an instance of the following classes.  It is:
#
#   1. NULL if not in the JIT at all, except as described below.
#
#   2. always NULL when tracing is in progress.
#
#   3. 'tracing_vable_rti' during tracing when we do a residual call,
#      calling random unknown other parts of the interpreter; it is
#      reset to NULL as soon as something occurs to the virtualizable.
#
#   4. NULL for now when running the machine code with a virtualizable;
#      later it will be a RunningVableRti().


class AbstractVableRti(object):

    def force_now(self, virtualizable):
        raise NotImplementedError


class TracingVableRti(AbstractVableRti):

    def force_now(self, virtualizable):
        # The values if the virtualizable are always correct during tracing.
        # We only need to set a marker to tell that forcing occurred.
        # As the caller resets vable_rti to NULL, it plays the role of marker.
        pass

tracing_vable_rti = TracingVableRti()
