import sys
import weakref

from rpython.jit.codewriter import support, heaptracker, longlong
from rpython.jit.metainterp import history
from rpython.rlib.debug import debug_start, debug_stop, debug_print
from rpython.rlib.debug import have_debug_prints_for
from rpython.rlib.jit import PARAMETERS
from rpython.rlib.nonconst import NonConstant
from rpython.rlib.objectmodel import specialize, we_are_translated, r_dict
from rpython.rlib.rarithmetic import intmask, r_uint
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.annlowlevel import (hlstr, cast_base_ptr_to_instance,
    cast_object_to_ptr)
from rpython.rtyper.lltypesystem import lltype, llmemory, rstr, rffi

# ____________________________________________________________

@specialize.arg(0)
def specialize_value(TYPE, x):
    """'x' must be a Signed, a GCREF or a FLOATSTORAGE.
    This function casts it to a more specialized type, like Char or Ptr(..).
    """
    INPUT = lltype.typeOf(x)
    if INPUT is lltype.Signed:
        if isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'raw':
            # non-gc pointer
            return rffi.cast(TYPE, x)
        elif TYPE is lltype.SingleFloat:
            return longlong.int2singlefloat(x)
        else:
            return lltype.cast_primitive(TYPE, x)
    elif INPUT is longlong.FLOATSTORAGE:
        if longlong.is_longlong(TYPE):
            return rffi.cast(TYPE, x)
        assert TYPE is lltype.Float
        return longlong.getrealfloat(x)
    else:
        return lltype.cast_opaque_ptr(TYPE, x)

@specialize.ll()
def unspecialize_value(value):
    """Casts 'value' to a Signed, a GCREF or a FLOATSTORAGE."""
    if isinstance(lltype.typeOf(value), lltype.Ptr):
        if lltype.typeOf(value).TO._gckind == 'gc':
            return lltype.cast_opaque_ptr(llmemory.GCREF, value)
        else:
            adr = llmemory.cast_ptr_to_adr(value)
            return heaptracker.adr2int(adr)
    elif isinstance(value, float):
        return longlong.getfloatstorage(value)
    else:
        return lltype.cast_primitive(lltype.Signed, value)

@specialize.arg(0)
def unwrap(TYPE, box):
    if TYPE is lltype.Void:
        return None
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == "gc":
            return box.getref(TYPE)
        else:
            return llmemory.cast_adr_to_ptr(box.getaddr(), TYPE)
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
            value = heaptracker.adr2int(adr)
            # fall through to the end of the function
    elif (isinstance(value, float) or
          longlong.is_longlong(lltype.typeOf(value))):
        if isinstance(value, float):
            value = longlong.getfloatstorage(value)
        else:
            value = rffi.cast(lltype.SignedLongLong, value)
        if in_const_box:
            return history.ConstFloat(value)
        else:
            return history.BoxFloat(value)
    elif isinstance(value, str) or isinstance(value, unicode):
        assert len(value) == 1     # must be a character
        value = ord(value)
    elif lltype.typeOf(value) is lltype.SingleFloat:
        value = longlong.singlefloat2int(value)
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
    return x == y

@specialize.arg(0)
def hash_whatever(TYPE, x):
    # Hash of lltype object.
    # Only supports strings, unicodes and regular instances,
    # as well as primitives that can meaningfully be cast to Signed.
    if isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        if TYPE.TO is rstr.STR or TYPE.TO is rstr.UNICODE:
            return rstr.LLHelpers.ll_strhash(x)    # assumed not null
        else:
            if x:
                return lltype.identityhash(x)
            else:
                return 0
    else:
        return rffi.cast(lltype.Signed, x)


JC_TRACING         = 0x01
JC_DONT_TRACE_HERE = 0x02
JC_TEMPORARY       = 0x04
JC_TRACING_OCCURRED= 0x08

class BaseJitCell(object):
    """Subclasses of BaseJitCell are used in tandem with the single
    JitCounter instance to record places in the JIT-tracked user program
    where something particular occurs with the JIT.  For some
    'greenkeys' (e.g. Python bytecode position), we create one instance
    of JitCell and attach it to that greenkey.  This is implemented
    with jitcounter.install_new_cell(), but conceptually you can think
    about JitCode instances as attached to some locations of the
    app-level Python code.

    We create subclasses of BaseJitCell --one per jitdriver-- so that
    they can store greenkeys of different types.  

    Note that we don't create a JitCell the first time we see a given
    greenkey position in the interpreter.  At first, we only hash the
    greenkey and use that in the JitCounter to record the number of
    times we have seen it.  We only create a JitCell when the
    JitCounter's total time value reaches 1.0 and we are starting to
    JIT-compile.

    A JitCell has a 'wref_procedure_token' that is non-None when we
    actually have a compiled procedure for that greenkey.  (It is a
    weakref, so that it could later be freed; in this case the JitCell
    will likely be reclaimed a bit later by 'should_remove_jitcell()'.)

    There are other less-common cases where we also create a JitCell: to
    record some long-term flags about the greenkey.  In general, a
    JitCell can have any combination of the following flags set:

        JC_TRACING: we are now tracing the loop from this greenkey.
        We'll likely end up with a wref_procedure_token, soonish.

        JC_TRACING_OCCURRED: set if JC_TRACING was set at least once.

        JC_TEMPORARY: a "temporary" wref_procedure_token.
        It's the procedure_token of a dummy loop that simply calls
        back the interpreter.  Used for a CALL_ASSEMBLER where the
        target was not compiled yet.  In this situation we are still
        ticking the JitCounter for the same hash, until we reach the
        threshold and start tracing the loop in earnest.

        JC_DONT_TRACE_HERE: when tracing, don't inline calls to
        this particular function.  (We only set this flag when aborting
        due to a trace too long, so we use the same flag as a hint to
        also mean "please trace from here as soon as possible".)
    """
    flags = 0     # JC_xxx flags
    wref_procedure_token = None
    next = None

    def get_procedure_token(self):
        if self.wref_procedure_token is not None:
            token = self.wref_procedure_token()
            if token and not token.invalidated:
                return token
        return None

    def has_seen_a_procedure_token(self):
        return self.wref_procedure_token is not None

    def set_procedure_token(self, token, tmp=False):
        self.wref_procedure_token = self._makeref(token)
        if tmp:
            self.flags |= JC_TEMPORARY
        else:
            self.flags &= ~JC_TEMPORARY

    def _makeref(self, token):
        assert token is not None
        return weakref.ref(token)

    def should_remove_jitcell(self):
        if self.get_procedure_token() is not None:
            return False    # don't remove JitCells with a procedure_token
        if self.flags & JC_TRACING:
            return False    # don't remove JitCells that are being traced
        if self.flags & JC_DONT_TRACE_HERE:
            # if we have this flag, and we *had* a procedure_token but
            # we no longer have one, then remove me.  this prevents this
            # JitCell from being immortal.
            return self.has_seen_a_procedure_token()     # i.e. dead weakref
        return True   # Other JitCells can be removed.

# ____________________________________________________________


class WarmEnterState(object):

    def __init__(self, warmrunnerdesc, jitdriver_sd):
        "NOT_RPYTHON"
        self.warmrunnerdesc = warmrunnerdesc
        self.jitdriver_sd = jitdriver_sd
        if warmrunnerdesc is not None:       # for tests
            self.cpu = warmrunnerdesc.cpu
        try:
            self.profiler = warmrunnerdesc.metainterp_sd.profiler
        except AttributeError:       # for tests
            self.profiler = None
        # initialize the state with the default values of the
        # parameters specified in rlib/jit.py
        if self.warmrunnerdesc is not None:
            for name, default_value in PARAMETERS.items():
                meth = getattr(self, 'set_param_' + name)
                meth(default_value)

    def _compute_threshold(self, threshold):
        return self.warmrunnerdesc.jitcounter.compute_threshold(threshold)

    def set_param_threshold(self, threshold):
        self.increment_threshold = self._compute_threshold(threshold)

    def set_param_function_threshold(self, threshold):
        self.increment_function_threshold = self._compute_threshold(threshold)

    def set_param_trace_eagerness(self, value):
        self.increment_trace_eagerness = self._compute_threshold(value)

    def set_param_trace_limit(self, value):
        self.trace_limit = value

    def set_param_decay(self, decay):
        self.warmrunnerdesc.jitcounter.set_decay(decay)

    def set_param_inlining(self, value):
        self.inlining = value

    def set_param_enable_opts(self, value):
        from rpython.jit.metainterp.optimizeopt import ALL_OPTS_DICT, ALL_OPTS_NAMES

        d = {}
        if NonConstant(False):
            value = 'blah' # not a constant ''
        if value is None or value == 'all':
            value = ALL_OPTS_NAMES
        for name in value.split(":"):
            if name:
                if name not in ALL_OPTS_DICT:
                    raise ValueError('Unknown optimization ' + name)
                d[name] = None
        self.enable_opts = d

    def set_param_loop_longevity(self, value):
        # note: it's a global parameter, not a per-jitdriver one
        if (self.warmrunnerdesc is not None and
            self.warmrunnerdesc.memory_manager is not None):   # all for tests
            self.warmrunnerdesc.memory_manager.set_max_age(value)

    def set_param_retrace_limit(self, value):
        if self.warmrunnerdesc:
            if self.warmrunnerdesc.memory_manager:
                self.warmrunnerdesc.memory_manager.retrace_limit = value

    def set_param_max_retrace_guards(self, value):
        if self.warmrunnerdesc:
            if self.warmrunnerdesc.memory_manager:
                self.warmrunnerdesc.memory_manager.max_retrace_guards = value

    def set_param_max_unroll_loops(self, value):
        if self.warmrunnerdesc:
            if self.warmrunnerdesc.memory_manager:
                self.warmrunnerdesc.memory_manager.max_unroll_loops = value

    def set_param_max_unroll_recursion(self, value):
        if self.warmrunnerdesc:
            if self.warmrunnerdesc.memory_manager:
                self.warmrunnerdesc.memory_manager.max_unroll_recursion = value

    def disable_noninlinable_function(self, greenkey):
        cell = self.JitCell.ensure_jit_cell_at_key(greenkey)
        cell.flags |= JC_DONT_TRACE_HERE
        debug_start("jit-disableinlining")
        loc = self.get_location_str(greenkey)
        debug_print("disabled inlining", loc)
        debug_stop("jit-disableinlining")

    def attach_procedure_to_interp(self, greenkey, procedure_token):
        cell = self.JitCell.ensure_jit_cell_at_key(greenkey)
        old_token = cell.get_procedure_token()
        cell.set_procedure_token(procedure_token)
        if old_token is not None:
            self.cpu.redirect_call_assembler(old_token, procedure_token)
            # procedure_token is also kept alive by any loop that used
            # to point to old_token.  Actually freeing old_token early
            # is a pointless optimization (it is tiny).
            old_token.record_jump_to(procedure_token)

    # ----------

    def make_entry_point(self):
        "NOT_RPYTHON"
        if hasattr(self, 'maybe_compile_and_run'):
            return self.maybe_compile_and_run

        warmrunnerdesc = self.warmrunnerdesc
        metainterp_sd = warmrunnerdesc.metainterp_sd
        jitdriver_sd = self.jitdriver_sd
        vinfo = jitdriver_sd.virtualizable_info
        index_of_virtualizable = jitdriver_sd.index_of_virtualizable
        num_green_args = jitdriver_sd.num_green_args
        JitCell = self.make_jitcell_subclass()
        self.make_jitdriver_callbacks()
        confirm_enter_jit = self.confirm_enter_jit
        range_red_args = unrolling_iterable(
            range(num_green_args, num_green_args + jitdriver_sd.num_red_args))
        # get a new specialized copy of the method
        ARGS = []
        for kind in jitdriver_sd.red_args_types:
            if kind == 'int':
                ARGS.append(lltype.Signed)
            elif kind == 'ref':
                ARGS.append(llmemory.GCREF)
            elif kind == 'float':
                ARGS.append(longlong.FLOATSTORAGE)
            else:
                assert 0, kind
        func_execute_token = self.cpu.make_execute_token(*ARGS)
        cpu = self.cpu
        jitcounter = self.warmrunnerdesc.jitcounter

        def execute_assembler(loop_token, *args):
            # Call the backend to run the 'looptoken' with the given
            # input args.

            # If we have a virtualizable, we have to clear its
            # state, to make sure we enter with vable_token being NONE
            #
            if vinfo is not None:
                virtualizable = args[index_of_virtualizable]
                vinfo.clear_vable_token(virtualizable)
            
            deadframe = func_execute_token(loop_token, *args)
            #
            # Record in the memmgr that we just ran this loop,
            # so that it will keep it alive for a longer time
            warmrunnerdesc.memory_manager.keep_loop_alive(loop_token)
            #
            # Handle the failure
            fail_descr = cpu.get_latest_descr(deadframe)
            fail_descr.handle_fail(deadframe, metainterp_sd, jitdriver_sd)
            #
            assert 0, "should have raised"

        def bound_reached(hash, cell, *args):
            if not confirm_enter_jit(*args):
                return
            jitcounter.decay_all_counters()
            # start tracing
            from rpython.jit.metainterp.pyjitpl import MetaInterp
            metainterp = MetaInterp(metainterp_sd, jitdriver_sd)
            greenargs = args[:num_green_args]
            if cell is None:
                cell = JitCell(*greenargs)
                jitcounter.install_new_cell(hash, cell)
            cell.flags |= JC_TRACING | JC_TRACING_OCCURRED
            try:
                metainterp.compile_and_run_once(jitdriver_sd, *args)
            finally:
                cell.flags &= ~JC_TRACING

        def maybe_compile_and_run(increment_threshold, *args):
            """Entry point to the JIT.  Called at the point with the
            can_enter_jit() hint.
            """
            # Look for the cell corresponding to the current greenargs.
            # Search for the JitCell that is of the correct subclass of
            # BaseJitCell, and that stores a key that compares equal.
            # These few lines inline some logic that is also on the
            # JitCell class, to avoid computing the hash several times.
            greenargs = args[:num_green_args]
            hash = JitCell.get_uhash(*greenargs)
            cell = jitcounter.lookup_chain(hash)
            while cell is not None:
                if isinstance(cell, JitCell) and cell.comparekey(*greenargs):
                    break    # found
                cell = cell.next
            else:
                # not found. increment the counter
                if jitcounter.tick(hash, increment_threshold):
                    bound_reached(hash, None, *args)
                return

            # Here, we have found 'cell'.
            #
            if cell.flags & (JC_TRACING | JC_TEMPORARY):
                if cell.flags & JC_TRACING:
                    # tracing already happening in some outer invocation of
                    # this function. don't trace a second time.
                    return
                # attached by compile_tmp_callback().  count normally
                if jitcounter.tick(hash, increment_threshold):
                    bound_reached(hash, cell, *args)
                return
            # machine code was already compiled for these greenargs
            procedure_token = cell.get_procedure_token()
            if procedure_token is None:
                if cell.flags & JC_DONT_TRACE_HERE:
                    if not cell.has_seen_a_procedure_token():
                        # A JC_DONT_TRACE_HERE, i.e. a non-inlinable function.
                        # If we never tried to trace it, try it now immediately.
                        # Otherwise, count normally.
                        if cell.flags & JC_TRACING_OCCURRED:
                            tick = jitcounter.tick(hash, increment_threshold)
                        else:
                            tick = True
                        if tick:
                            bound_reached(hash, cell, *args)
                        return
                # it was an aborted compilation, or maybe a weakref that
                # has been freed
                jitcounter.cleanup_chain(hash)
                return
            if not confirm_enter_jit(*args):
                return
            # extract and unspecialize the red arguments to pass to
            # the assembler
            execute_args = ()
            for i in range_red_args:
                execute_args += (unspecialize_value(args[i]), )
            # run it!  this executes until interrupted by an exception
            execute_assembler(procedure_token, *execute_args)
            assert 0, "should not reach this point"

        maybe_compile_and_run._dont_inline_ = True
        self.maybe_compile_and_run = maybe_compile_and_run
        self.execute_assembler = execute_assembler
        return maybe_compile_and_run

    # ----------

    def make_unwrap_greenkey(self):
        "NOT_RPYTHON"
        if hasattr(self, 'unwrap_greenkey'):
            return self.unwrap_greenkey
        #
        jitdriver_sd = self.jitdriver_sd
        green_args_spec = unrolling_iterable(jitdriver_sd._green_args_spec)
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

    def make_jitcell_subclass(self):
        "NOT_RPYTHON"
        if hasattr(self, 'JitCell'):
            return self.JitCell
        #
        jitcounter = self.warmrunnerdesc.jitcounter
        jitdriver_sd = self.jitdriver_sd
        green_args_name_spec = unrolling_iterable([('g%d' % i, TYPE)
                     for i, TYPE in enumerate(jitdriver_sd._green_args_spec)])
        unwrap_greenkey = self.make_unwrap_greenkey()
        #
        class JitCell(BaseJitCell):
            def __init__(self, *greenargs):
                i = 0
                for attrname, _ in green_args_name_spec:
                    setattr(self, attrname, greenargs[i])
                    i = i + 1

            def comparekey(self, *greenargs2):
                i = 0
                for attrname, TYPE in green_args_name_spec:
                    item1 = getattr(self, attrname)
                    if not equal_whatever(TYPE, item1, greenargs2[i]):
                        return False
                    i = i + 1
                return True

            @staticmethod
            def get_uhash(*greenargs):
                x = r_uint(-1888132534)
                i = 0
                for _, TYPE in green_args_name_spec:
                    item = greenargs[i]
                    y = r_uint(hash_whatever(TYPE, item))
                    x = (x ^ y) * r_uint(1405695061)  # prime number, 2**30~31
                    i = i + 1
                return x

            @staticmethod
            def get_jitcell(*greenargs):
                hash = JitCell.get_uhash(*greenargs)
                cell = jitcounter.lookup_chain(hash)
                while cell is not None:
                    if (isinstance(cell, JitCell) and
                            cell.comparekey(*greenargs)):
                        return cell
                    cell = cell.next
                return None

            @staticmethod
            def get_jit_cell_at_key(greenkey):
                greenargs = unwrap_greenkey(greenkey)
                return JitCell.get_jitcell(*greenargs)

            @staticmethod
            def trace_next_iteration(greenkey):
                greenargs = unwrap_greenkey(greenkey)
                hash = JitCell.get_uhash(*greenargs)
                jitcounter.change_current_fraction(hash, 0.98)

            @staticmethod
            def ensure_jit_cell_at_key(greenkey):
                greenargs = unwrap_greenkey(greenkey)
                hash = JitCell.get_uhash(*greenargs)
                cell = jitcounter.lookup_chain(hash)
                while cell is not None:
                    if (isinstance(cell, JitCell) and
                            cell.comparekey(*greenargs)):
                        return cell
                    cell = cell.next
                newcell = JitCell(*greenargs)
                jitcounter.install_new_cell(hash, newcell)
                return newcell
        #
        self.JitCell = JitCell
        return JitCell

    # ----------

    def make_jitdriver_callbacks(self):
        if hasattr(self, 'get_location_str'):
            return
        #
        warmrunnerdesc = self.warmrunnerdesc
        unwrap_greenkey = self.make_unwrap_greenkey()
        JitCell = self.make_jitcell_subclass()
        jd = self.jitdriver_sd
        cpu = self.cpu
        rtyper = self.warmrunnerdesc.rtyper

        def can_inline_callable(greenkey):
            greenargs = unwrap_greenkey(greenkey)
            if can_never_inline(*greenargs):
                return False
            cell = JitCell.get_jitcell(*greenargs)
            if cell is not None and (cell.flags & JC_DONT_TRACE_HERE) != 0:
                return False
            return True
        self.can_inline_callable = can_inline_callable

        def dont_trace_here(greenkey):
            # Set greenkey as somewhere that tracing should not occur into;
            # notice that, as per the description of JC_DONT_TRACE_HERE earlier,
            # if greenkey hasn't been traced separately, setting
            # JC_DONT_TRACE_HERE will force tracing the next time the function
            # is encountered.
            cell = JitCell.ensure_jit_cell_at_key(greenkey)
            cell.flags |= JC_DONT_TRACE_HERE
        self.dont_trace_here = dont_trace_here

        if jd._should_unroll_one_iteration_ptr is None:
            def should_unroll_one_iteration(greenkey):
                return False
        else:
            inline_ptr = jd._should_unroll_one_iteration_ptr
            def should_unroll_one_iteration(greenkey):
                greenargs = unwrap_greenkey(greenkey)
                fn = support.maybe_on_top_of_llinterp(rtyper, inline_ptr)
                return fn(*greenargs)
        self.should_unroll_one_iteration = should_unroll_one_iteration

        redargtypes = ''.join([kind[0] for kind in jd.red_args_types])

        def get_assembler_token(greenkey):
            cell = JitCell.ensure_jit_cell_at_key(greenkey)
            procedure_token = cell.get_procedure_token()
            if procedure_token is None:
                from rpython.jit.metainterp.compile import compile_tmp_callback
                memmgr = warmrunnerdesc.memory_manager
                procedure_token = compile_tmp_callback(cpu, jd, greenkey,
                                                       redargtypes, memmgr)
                cell.set_procedure_token(procedure_token, tmp=True)
            return procedure_token
        self.get_assembler_token = get_assembler_token

        #
        jitdriver = self.jitdriver_sd.jitdriver
        if self.jitdriver_sd.jitdriver:
            drivername = jitdriver.name
        else:
            drivername = '<unknown jitdriver>'
        get_location_ptr = self.jitdriver_sd._get_printable_location_ptr
        if get_location_ptr is None:
            missing = '(%s: no get_printable_location)' % drivername
            def get_location_str(greenkey):
                return missing
        else:
            unwrap_greenkey = self.make_unwrap_greenkey()
            # the following missing text should not be seen, as it is
            # returned only if debug_prints are currently not enabled,
            # but it may show up anyway (consider it bugs)
            missing = ('(%s: get_printable_location '
                       'disabled, no debug_print)' % drivername)
            #
            def get_location_str(greenkey):
                if not have_debug_prints_for("jit-"):
                    return missing
                greenargs = unwrap_greenkey(greenkey)
                fn = support.maybe_on_top_of_llinterp(rtyper, get_location_ptr)
                llres = fn(*greenargs)
                if not we_are_translated() and isinstance(llres, str):
                    return llres
                return hlstr(llres)
        self.get_location_str = get_location_str
        #
        confirm_enter_jit_ptr = self.jitdriver_sd._confirm_enter_jit_ptr
        if confirm_enter_jit_ptr is None:
            def confirm_enter_jit(*args):
                return True
        else:
            #
            def confirm_enter_jit(*args):
                fn = support.maybe_on_top_of_llinterp(rtyper,
                                                      confirm_enter_jit_ptr)
                return fn(*args)
        self.confirm_enter_jit = confirm_enter_jit
        #
        can_never_inline_ptr = self.jitdriver_sd._can_never_inline_ptr
        if can_never_inline_ptr is None:
            def can_never_inline(*greenargs):
                return False
        else:
            #
            def can_never_inline(*greenargs):
                fn = support.maybe_on_top_of_llinterp(rtyper,
                                                      can_never_inline_ptr)
                return fn(*greenargs)
        self.can_never_inline = can_never_inline
        get_unique_id_ptr = self.jitdriver_sd._get_unique_id_ptr
        def get_unique_id(greenkey):
            greenargs = unwrap_greenkey(greenkey)
            fn = support.maybe_on_top_of_llinterp(rtyper, get_unique_id_ptr)
            return fn(*greenargs)
        self.get_unique_id = get_unique_id
