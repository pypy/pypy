import sys
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import hlstr, cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import cast_object_to_ptr
from pypy.rlib.objectmodel import specialize, we_are_translated, r_dict
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.jit import PARAMETERS, OPTIMIZER_SIMPLE, OPTIMIZER_FULL
from pypy.rlib.jit import DEBUG_PROFILE
from pypy.rlib.jit import BaseJitCell
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.metainterp import support, history

# ____________________________________________________________

@specialize.arg(0)
def unwrap(TYPE, box):
    if TYPE is lltype.Void:
        return None
    if isinstance(TYPE, lltype.Ptr):
        return box.getref(TYPE)
    if isinstance(TYPE, ootype.OOType):
        return box.getref(TYPE)
    if TYPE == lltype.Float:
        return box.getfloat()
    else:
        return lltype.cast_primitive(TYPE, box.getint())

@specialize.ll()
def wrap(cpu, value, in_const_box=False):
    if isinstance(lltype.typeOf(value), lltype.Ptr):
        if lltype.typeOf(value).TO._gckind == 'gc':
            value = lltype.cast_opaque_ptr(llmemory.GCREF, value)
            if in_const_box:
                return history.ConstPtr(value)
            else:
                return history.BoxPtr(value)
        else:
            adr = llmemory.cast_ptr_to_adr(value)
            value = cpu.cast_adr_to_int(adr)
            # fall through to the end of the function
    elif isinstance(lltype.typeOf(value), ootype.OOType):
        value = ootype.cast_to_object(value)
        if in_const_box:
            return history.ConstObj(value)
        else:
            return history.BoxObj(value)
    elif isinstance(value, float):
        if in_const_box:
            return history.ConstFloat(value)
        else:
            return history.BoxFloat(value)
    else:
        value = intmask(value)
    if in_const_box:
        return history.ConstInt(value)
    else:
        return history.BoxInt(value)

@specialize.arg(0)
def equal_whatever(TYPE, x, y):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO is rstr.STR or TYPE.TO is rstr.UNICODE:
            return rstr.LLHelpers.ll_streq(x, y)
    if TYPE is ootype.String or TYPE is ootype.Unicode:
        return x.ll_streq(y)
    return x == y

@specialize.arg(0)
def hash_whatever(TYPE, x):
    # Hash of lltype or ootype object.
    # Only supports strings, unicodes and regular instances,
    # as well as primitives that can meaningfully be cast to Signed.
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO is rstr.STR or TYPE.TO is rstr.UNICODE:
            return rstr.LLHelpers.ll_strhash(x)    # assumed not null
        else:
            if x:
                return lltype.identityhash(x)
            else:
                return 0
    elif TYPE is ootype.String or TYPE is ootype.Unicode:
        return x.ll_hash()
    elif isinstance(TYPE, ootype.OOType):
        if x:
            return ootype.identityhash(x)
        else:
            return 0
    else:
        return lltype.cast_primitive(lltype.Signed, x)

@specialize.ll_and_arg(3)
def set_future_value(cpu, j, value, typecode):
    if typecode == 'ref':
        refvalue = cpu.ts.cast_to_ref(value)
        cpu.set_future_value_ref(j, refvalue)
    elif typecode == 'int':
        intvalue = lltype.cast_primitive(lltype.Signed, value)
        cpu.set_future_value_int(j, intvalue)
    elif typecode == 'float':
        assert isinstance(value, float)
        cpu.set_future_value_float(j, value)
    else:
        assert False

# ____________________________________________________________


class WarmEnterState(object):
    THRESHOLD_LIMIT = sys.maxint // 2
    default_jitcell_dict = None

    def __init__(self, warmrunnerdesc):
        "NOT_RPYTHON"
        self.warmrunnerdesc = warmrunnerdesc
        try:
            self.profiler = warmrunnerdesc.metainterp_sd.profiler
        except AttributeError:       # for tests
            self.profiler = None
        # initialize the state with the default values of the
        # parameters specified in rlib/jit.py
        for name, default_value in PARAMETERS.items():
            meth = getattr(self, 'set_param_' + name)
            meth(default_value)

    def set_param_threshold(self, threshold):
        if threshold < 2:
            threshold = 2
        self.increment_threshold = (self.THRESHOLD_LIMIT // threshold) + 1
        # the number is at least 1, and at most about half THRESHOLD_LIMIT

    def set_param_trace_eagerness(self, value):
        self.trace_eagerness = value

    def set_param_trace_limit(self, value):
        self.trace_limit = value

    def set_param_inlining(self, value):
        self.inlining = value

    def set_param_optimizer(self, optimizer):
        if optimizer == OPTIMIZER_SIMPLE:
            from pypy.jit.metainterp import simple_optimize
            self.optimize_loop = simple_optimize.optimize_loop
            self.optimize_bridge = simple_optimize.optimize_bridge
        elif optimizer == OPTIMIZER_FULL:
            from pypy.jit.metainterp import optimize
            self.optimize_loop = optimize.optimize_loop
            self.optimize_bridge = optimize.optimize_bridge
        else:
            raise ValueError("unknown optimizer")

    def set_param_debug(self, value):
        self.debug_level = value
        if self.profiler is not None:
            self.profiler.set_printing(value >= DEBUG_PROFILE)

    def disable_noninlinable_function(self, metainterp):
        greenkey = metainterp.greenkey_of_huge_function
        if greenkey is not None:
            cell = self.jit_cell_at_key(greenkey)
            cell.dont_trace_here = True
            debug_start("jit-disableinlining")
            sd = self.warmrunnerdesc.metainterp_sd
            loc = sd.state.get_location_str(greenkey)
            debug_print("disabled inlining", loc)
            debug_stop("jit-disableinlining")

    def attach_unoptimized_bridge_from_interp(self, greenkey,
                                              entry_loop_token):
        cell = self.jit_cell_at_key(greenkey)
        cell.counter = -1
        cell.entry_loop_token = entry_loop_token

    # ----------

    def make_entry_point(self):
        "NOT_RPYTHON"
        if hasattr(self, 'maybe_compile_and_run'):
            return self.maybe_compile_and_run

        metainterp_sd = self.warmrunnerdesc.metainterp_sd
        vinfo = metainterp_sd.virtualizable_info
        ContinueRunningNormally = self.warmrunnerdesc.ContinueRunningNormally
        num_green_args = self.warmrunnerdesc.num_green_args
        get_jitcell = self.make_jitcell_getter()
        set_future_values = self.make_set_future_values()
        self.make_jitdriver_callbacks()
        confirm_enter_jit = self.confirm_enter_jit

        def maybe_compile_and_run(*args):
            """Entry point to the JIT.  Called at the point with the
            can_enter_jit() hint.
            """
            globaldata = metainterp_sd.globaldata
            if NonConstant(False):
                # make sure we always see the saner optimizer from an
                # annotation point of view, otherwise we get lots of
                # blocked ops
                self.set_param_optimizer(OPTIMIZER_FULL)

            if vinfo is not None:
                virtualizable = args[vinfo.index_of_virtualizable]
                virtualizable = vinfo.cast_to_vtype(virtualizable)
            else:
                virtualizable = None

            # look for the cell corresponding to the current greenargs
            greenargs = args[:num_green_args]
            cell = get_jitcell(*greenargs)

            if cell.counter >= 0:
                # update the profiling counter
                n = cell.counter + self.increment_threshold
                if n <= self.THRESHOLD_LIMIT:       # bound not reached
                    cell.counter = n
                    return
                if not confirm_enter_jit(*args):
                    cell.counter = 0
                    return
                # bound reached; start tracing
                from pypy.jit.metainterp.pyjitpl import MetaInterp
                metainterp = MetaInterp(metainterp_sd)
                # set counter to -2, to mean "tracing in effect"
                cell.counter = -2
                try:
                    loop_token = metainterp.compile_and_run_once(*args)
                except ContinueRunningNormally:
                    # the trace got too long, reset the counter
                    cell.counter = 0
                    self.disable_noninlinable_function(metainterp)
                    raise
                finally:
                    if cell.counter == -2:
                        cell.counter = 0
            else:
                if cell.counter == -2:
                    # tracing already happening in some outer invocation of
                    # this function. don't trace a second time.
                    return
                assert cell.counter == -1
                if not confirm_enter_jit(*args):
                    return
                # machine code was already compiled for these greenargs
                # get the assembler and fill in the boxes
                set_future_values(*args[num_green_args:])
                loop_token = cell.entry_loop_token

            # ---------- execute assembler ----------
            while True:     # until interrupted by an exception
                metainterp_sd.profiler.start_running()
                debug_start("jit-running")
                fail_descr = metainterp_sd.cpu.execute_token(loop_token)
                debug_stop("jit-running")
                metainterp_sd.profiler.end_running()
                if vinfo is not None:
                    vinfo.reset_vable_token(virtualizable)
                loop_token = fail_descr.handle_fail(metainterp_sd)
       
        maybe_compile_and_run._dont_inline_ = True
        self.maybe_compile_and_run = maybe_compile_and_run
        return maybe_compile_and_run

    # ----------

    def make_unwrap_greenkey(self):
        "NOT_RPYTHON"
        if hasattr(self, 'unwrap_greenkey'):
            return self.unwrap_greenkey
        #
        warmrunnerdesc = self.warmrunnerdesc
        green_args_spec = unrolling_iterable(warmrunnerdesc.green_args_spec)
        #
        def unwrap_greenkey(greenkey):
            greenargs = ()
            i = 0
            for TYPE in green_args_spec:
                greenbox = greenkey[i]
                assert isinstance(greenbox, history.Const)
                value = unwrap(TYPE, greenbox)
                greenargs += (value,)
                i = i + 1
            return greenargs
        #
        unwrap_greenkey._always_inline_ = True
        self.unwrap_greenkey = unwrap_greenkey
        return unwrap_greenkey

    # ----------

    def make_jitcell_getter(self):
        "NOT_RPYTHON"
        if hasattr(self, 'jit_getter'):
            return self.jit_getter
        #
        class JitCell(BaseJitCell):
            # the counter can mean the following things:
            #     counter >=  0: not yet traced, wait till threshold is reached
            #     counter == -1: there is an entry bridge for this cell
            #     counter == -2: tracing is currently going on for this cell
            counter = 0
            compiled_merge_points = None
            dont_trace_here = False
            entry_loop_token = None
        #
        if self.warmrunnerdesc.get_jitcell_at_ptr is None:
            jit_getter = self._make_jitcell_getter_default(JitCell)
        else:
            jit_getter = self._make_jitcell_getter_custom(JitCell)
        #
        unwrap_greenkey = self.make_unwrap_greenkey()
        #
        def jit_cell_at_key(greenkey):
            greenargs = unwrap_greenkey(greenkey)
            return jit_getter(*greenargs)
        self.jit_cell_at_key = jit_cell_at_key
        self.jit_getter = jit_getter
        #
        return jit_getter

    def _make_jitcell_getter_default(self, JitCell):
        "NOT_RPYTHON"
        warmrunnerdesc = self.warmrunnerdesc
        green_args_spec = unrolling_iterable(warmrunnerdesc.green_args_spec)
        #
        def comparekey(greenargs1, greenargs2):
            i = 0
            for TYPE in green_args_spec:
                if not equal_whatever(TYPE, greenargs1[i], greenargs2[i]):
                    return False
                i = i + 1
            return True
        #
        def hashkey(greenargs):
            x = 0x345678
            i = 0
            for TYPE in green_args_spec:
                item = greenargs[i]
                y = hash_whatever(TYPE, item)
                x = intmask((1000003 * x) ^ y)
                i = i + 1
            return x
        #
        jitcell_dict = r_dict(comparekey, hashkey)
        #
        def get_jitcell(*greenargs):
            try:
                cell = jitcell_dict[greenargs]
            except KeyError:
                cell = JitCell()
                jitcell_dict[greenargs] = cell
            return cell
        return get_jitcell

    def _make_jitcell_getter_custom(self, JitCell):
        "NOT_RPYTHON"
        rtyper = self.warmrunnerdesc.rtyper
        get_jitcell_at_ptr = self.warmrunnerdesc.get_jitcell_at_ptr
        set_jitcell_at_ptr = self.warmrunnerdesc.set_jitcell_at_ptr
        lltohlhack = {}
        #
        def get_jitcell(*greenargs):
            fn = support.maybe_on_top_of_llinterp(rtyper, get_jitcell_at_ptr)
            cellref = fn(*greenargs)
            # <hacks>
            if we_are_translated():
                BASEJITCELL = lltype.typeOf(cellref)
                cell = cast_base_ptr_to_instance(JitCell, cellref)
            elif isinstance(cellref, (BaseJitCell, type(None))):
                BASEJITCELL = None
                cell = cellref
            else:
                BASEJITCELL = lltype.typeOf(cellref)
                if cellref:
                    cell = lltohlhack[rtyper.type_system.deref(cellref)]
                else:
                    cell = None
            # </hacks>
            if cell is None:
                cell = JitCell()
                # <hacks>
                if we_are_translated():
                    cellref = cast_object_to_ptr(BASEJITCELL, cell)
                elif BASEJITCELL is None:
                    cellref = cell
                else:
                    if isinstance(BASEJITCELL, lltype.Ptr):
                        cellref = lltype.malloc(BASEJITCELL.TO)
                    elif isinstance(BASEJITCELL, ootype.Instance):
                        cellref = ootype.new(BASEJITCELL)
                    else:
                        assert False, "no clue"
                    lltohlhack[rtyper.type_system.deref(cellref)] = cell
                # </hacks>
                fn = support.maybe_on_top_of_llinterp(rtyper,
                                                      set_jitcell_at_ptr)
                fn(cellref, *greenargs)
            return cell
        return get_jitcell

    # ----------

    def make_set_future_values(self):
        "NOT_RPYTHON"
        if hasattr(self, 'set_future_values'):
            return self.set_future_values

        warmrunnerdesc = self.warmrunnerdesc
        cpu = warmrunnerdesc.cpu
        vinfo = warmrunnerdesc.metainterp_sd.virtualizable_info
        red_args_types = unrolling_iterable(warmrunnerdesc.red_args_types)
        #
        def set_future_values(*redargs):
            i = 0
            for typecode in red_args_types:
                set_future_value(cpu, i, redargs[i], typecode)
                i = i + 1
            if vinfo is not None:
                set_future_values_from_vinfo(*redargs)
        #
        if vinfo is not None:
            i0 = len(warmrunnerdesc.red_args_types)
            num_green_args = warmrunnerdesc.num_green_args
            vable_static_fields = unrolling_iterable(
                zip(vinfo.static_extra_types, vinfo.static_fields))
            vable_array_fields = unrolling_iterable(
                zip(vinfo.arrayitem_extra_types, vinfo.array_fields))
            getlength = cpu.ts.getlength
            getarrayitem = cpu.ts.getarrayitem
            #
            def set_future_values_from_vinfo(*redargs):
                i = i0
                virtualizable = redargs[vinfo.index_of_virtualizable -
                                        num_green_args]
                virtualizable = vinfo.cast_to_vtype(virtualizable)
                for typecode, fieldname in vable_static_fields:
                    x = getattr(virtualizable, fieldname)
                    set_future_value(cpu, i, x, typecode)
                    i = i + 1
                for typecode, fieldname in vable_array_fields:
                    lst = getattr(virtualizable, fieldname)
                    for j in range(getlength(lst)):
                        x = getarrayitem(lst, j)
                        set_future_value(cpu, i, x, typecode)
                        i = i + 1
        else:
            set_future_values_from_vinfo = None
        #
        self.set_future_values = set_future_values
        return set_future_values

    # ----------

    def make_jitdriver_callbacks(self):
        if hasattr(self, 'get_location_str'):
            return
        #
        can_inline_ptr = self.warmrunnerdesc.can_inline_ptr
        unwrap_greenkey = self.make_unwrap_greenkey()
        if can_inline_ptr is None:
            def can_inline_callable(*greenargs):
                # XXX shouldn't it be False by default?
                return True
        else:
            rtyper = self.warmrunnerdesc.rtyper
            #
            def can_inline_callable(*greenargs):
                fn = support.maybe_on_top_of_llinterp(rtyper, can_inline_ptr)
                return fn(*greenargs)
        def can_inline(*greenargs):
            cell = self.jit_getter(*greenargs)
            if cell.dont_trace_here:
                return False
            return can_inline_callable(*greenargs)
        self.can_inline_greenargs = can_inline
        def can_inline_greenkey(greenkey):
            greenargs = unwrap_greenkey(greenkey)
            return can_inline(*greenargs)
        self.can_inline_callable = can_inline_greenkey
        
        get_jitcell = self.make_jitcell_getter()
        def get_assembler_token(greenkey):
            greenargs = unwrap_greenkey(greenkey)
            cell = get_jitcell(*greenargs)
            if cell.counter >= 0:
                return None
            return cell.entry_loop_token
        self.get_assembler_token = get_assembler_token
        
        #
        get_location_ptr = self.warmrunnerdesc.get_printable_location_ptr
        if get_location_ptr is None:
            def get_location_str(greenkey):
                return '(no jitdriver.get_printable_location!)'
        else:
            rtyper = self.warmrunnerdesc.rtyper
            unwrap_greenkey = self.make_unwrap_greenkey()
            #
            def get_location_str(greenkey):
                greenargs = unwrap_greenkey(greenkey)
                fn = support.maybe_on_top_of_llinterp(rtyper, get_location_ptr)
                res = fn(*greenargs)
                if not we_are_translated() and not isinstance(res, str):
                    res = hlstr(res)
                return res
        self.get_location_str = get_location_str
        #
        confirm_enter_jit_ptr = self.warmrunnerdesc.confirm_enter_jit_ptr
        if confirm_enter_jit_ptr is None:
            def confirm_enter_jit(*args):
                return True
        else:
            rtyper = self.warmrunnerdesc.rtyper
            #
            def confirm_enter_jit(*args):
                fn = support.maybe_on_top_of_llinterp(rtyper,
                                                      confirm_enter_jit_ptr)
                return fn(*args)
        self.confirm_enter_jit = confirm_enter_jit
