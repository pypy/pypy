from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.pyopcode import LoopBlock, SApplicationException, Yield
from pypy.interpreter.pycode import CO_YIELD_INSIDE_TRY
from pypy.interpreter.astcompiler import consts
from rpython.rlib import jit, rgc, rweakref
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint


class GeneratorOrCoroutine(W_Root):
    _immutable_fields_ = ['pycode']

    w_yielded_from = None

    def __init__(self, frame, name=None, qualname=None):
        self.space = frame.space
        self.frame = frame     # turned into None when frame_finished_execution
        self.pycode = frame.pycode  # usually never None but see __setstate__
        self.running = False
        self._name = name           # may be null, use get_name()
        self._qualname = qualname   # may be null, use get_qualname()
        if (isinstance(self, Coroutine)
                or self.pycode.co_flags & CO_YIELD_INSIDE_TRY):
            self.register_finalizer(self.space)
        self.saved_operr = None

    def get_name(self):
        # 'name' is a byte string that is valid utf-8
        if self._name is not None:
            return self._name
        elif self.pycode is None:
            return "<finished>"
        else:
            return self.pycode.co_name

    def get_qualname(self):
        # 'qualname' is a unicode string
        if self._qualname is not None:
            return self._qualname
        return self.get_name()

    def descr__repr__(self, space):
        addrstring = self.getaddrstring(space)
        return space.newtext("<%s object %s at 0x%s>" %
                          (self.KIND, self.get_qualname(), addrstring))

    def descr_send(self, w_arg):
        """send(arg) -> send 'arg' into generator/coroutine,
return next yielded value or raise StopIteration."""
        return self.send_ex(w_arg)

    def send_error(self, operr):
        return self.send_ex(SApplicationException(operr))

    def send_ex(self, w_arg_or_err):
        assert w_arg_or_err is not None
        pycode = self.pycode
        if pycode is not None:
            if jit.we_are_jitted() and should_not_inline(pycode):
                generatorentry_driver.jit_merge_point(gen=self,
                                                      w_arg=w_arg_or_err,
                                                      pycode=pycode)
        return self._send_ex(w_arg_or_err)

    def _send_ex(self, w_arg_or_err):
        space = self.space

        frame = self.frame
        if frame is None:
            if isinstance(self, Coroutine):
                # NB. CPython checks a flag 'closing' here, but instead
                # we can simply not be here at all if frame is None in
                # this case
                raise oefmt(space.w_RuntimeError,
                            "cannot reuse already awaited coroutine")
            # xxx a bit ad-hoc, but we don't want to go inside
            # execute_frame() if the frame is actually finished
            if isinstance(w_arg_or_err, SApplicationException):
                operr = w_arg_or_err.operr
            elif isinstance(self, AsyncGenerator):
                operr = OperationError(space.w_StopAsyncIteration, space.w_None)
            else:
                operr = OperationError(space.w_StopIteration, space.w_None)
            raise operr

        w_result = self._invoke_execute_frame(frame, w_arg_or_err)
        assert w_result is not None

        # if the frame is now marked as finished, it was RETURNed from
        if frame.frame_finished_execution:
            self.frame_is_finished()
            if isinstance(self, AsyncGenerator):
                assert space.is_w(w_result, space.w_None), (
                    "getting non-None here should be forbidden by the bytecode")
                raise OperationError(space.w_StopAsyncIteration, space.w_None)
            else:
                if space.is_w(w_result, space.w_None):
                    raise OperationError(space.w_StopIteration, space.w_None)
                else:
                    raise stopiteration_value(space, w_result)
        else:
            return w_result     # YIELDed

    def _invoke_execute_frame(self, frame, w_arg_or_err):
        space = self.space
        if self.running:
            raise oefmt(space.w_ValueError, "%s already executing", self.KIND)
        ec = space.getexecutioncontext()
        current_exc_info = ec.sys_exc_info()
        if self.saved_operr is not None:
            ec.set_sys_exc_info(self.saved_operr)
            self.saved_operr = None
        #
        # Optimization only: after we've started a Coroutine without
        # CO_YIELD_INSIDE_TRY, then Coroutine._finalize_() will be a no-op
        if frame.last_instr == -1:
            if (isinstance(self, Coroutine) and
                not (self.pycode.co_flags & CO_YIELD_INSIDE_TRY)):
                rgc.may_ignore_finalizer(self)

            if (not space.is_w(w_arg_or_err, space.w_None) and
                not isinstance(w_arg_or_err, SApplicationException)):
                raise oefmt(space.w_TypeError,
                            "can't send non-None value to a just-started %s",
                            self.KIND)
        self.running = True
        try:
            w_result = frame.execute_frame(self, w_arg_or_err)
        except OperationError as e:
            # errors finish a frame
            try:
                if e.match(space, space.w_StopIteration):
                    self._leak_stopiteration(e)
                elif (isinstance(self, AsyncGenerator) and
                      e.match(space, space.w_StopAsyncIteration)):
                    self._leak_stopasynciteration(e)
            finally:
                self.frame_is_finished()
            raise
        finally:
            frame.f_backref = jit.vref_None
            self.running = False
            # note: this is not perfectly correct: see
            # test_exc_info_in_generator_4.  But it's simpler and
            # bug-to-bug compatible with CPython 3.5.
            if frame._any_except_or_finally_handler():
                self.saved_operr = ec.sys_exc_info()
            ec.set_sys_exc_info(current_exc_info)
        return w_result

    def resume_execute_frame(self, frame, w_arg_or_err):
        # Called from execute_frame() just before resuming the bytecode
        # interpretation.
        space = self.space
        w_yf = self.w_yielded_from
        if w_yf is not None:
            self.w_yielded_from = None
            try:
                self.next_yield_from(frame, w_yf, w_arg_or_err)
            except OperationError as operr:
                operr.record_context(space, space.getexecutioncontext())
                return frame.handle_generator_error(operr)
            # Normal case: the call above raises Yield.
            # We reach this point if the iterable is exhausted.
            last_instr = jit.promote(frame.last_instr)
            assert last_instr & 1 == 0
            assert last_instr >= 0
            return r_uint(last_instr + 2)

        if isinstance(w_arg_or_err, SApplicationException):
            return frame.handle_generator_error(w_arg_or_err.operr)

        last_instr = jit.promote(frame.last_instr)
        if last_instr != -1:
            assert last_instr & 1 == 0
            frame.pushvalue(w_arg_or_err)
            return r_uint(last_instr + 2)
        else:
            return r_uint(0)

    def next_yield_from(self, frame, w_yf, w_inputvalue_or_err):
        """Fetch the next item of the current 'yield from', push it on
        the frame stack, and raises Yield.  If there isn't one, push
        w_stopiteration_value and returns.  May also just raise.
        """
        space = self.space
        try:
            if isinstance(w_yf, GeneratorOrCoroutine):
                w_retval = w_yf.send_ex(w_inputvalue_or_err)
            elif isinstance(w_yf, AsyncGenASend):   # performance only
                w_retval = w_yf.do_send(w_inputvalue_or_err)
            elif space.is_w(w_inputvalue_or_err, space.w_None):
                w_retval = space.next(w_yf)
            else:
                w_retval = delegate_to_nongen(space, w_yf, w_inputvalue_or_err)
        except OperationError as e:
            if not e.match(space, space.w_StopIteration):
                raise
            frame._report_stopiteration_sometimes(w_yf, e)
            try:
                w_stop_value = space.getattr(e.get_w_value(space),
                                             space.newtext("value"))
            except OperationError as e:
                if not e.match(space, space.w_AttributeError):
                    raise
                w_stop_value = space.w_None
            frame.pushvalue(w_stop_value)
            return
        else:
            frame.pushvalue(w_retval)
            self.w_yielded_from = w_yf
            raise Yield

    def _leak_stopiteration(self, e):
        # Check for __future__ generator_stop and conditionally turn
        # a leaking StopIteration into RuntimeError (with its cause
        # set appropriately).
        space = self.space
        if self.pycode.co_flags & (consts.CO_FUTURE_GENERATOR_STOP |
                                   consts.CO_COROUTINE |
                                   consts.CO_ITERABLE_COROUTINE |
                                   consts.CO_ASYNC_GENERATOR):
            e2 = OperationError(space.w_RuntimeError,
                                space.newtext("%s raised StopIteration" %
                                              self.KIND))
            e2.chain_exceptions_from_cause(space, e)
            raise e2
        else:
            space.warn(space.newtext("generator '%s' raised StopIteration"
                                        % self.get_qualname()),
                       space.w_DeprecationWarning)

    def _leak_stopasynciteration(self, e):
        space = self.space
        e2 = OperationError(space.w_RuntimeError,
                   space.newtext("async generator raised StopAsyncIteration"))
        e2.chain_exceptions_from_cause(space, e)
        raise e2

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        """throw(typ[,val[,tb]]) -> raise exception in generator/coroutine,
return next yielded value or raise StopIteration."""
        return self.throw(w_type, w_val, w_tb)

    def throw(self, w_type, w_val, w_tb):
        from pypy.interpreter.pytraceback import check_traceback

        space = self.space
        if w_val is None:
            w_val = space.w_None

        msg = "throw() third argument must be a traceback object"
        if space.is_none(w_tb):
            tb = None
        else:
            tb = check_traceback(space, w_tb, msg)

        operr = OperationError(w_type, w_val, tb)
        operr.normalize_exception(space)

        # note: w_yielded_from is always None if 'self.running'
        if (self.w_yielded_from is not None and
                    operr.match(space, space.w_GeneratorExit)):
            try:
                self._gen_close_iter(space)
            except OperationError as e:
                return self.send_error(e)

        if tb is None:
            tb = space.getattr(operr.get_w_value(space),
                               space.newtext('__traceback__'))
            if not space.is_w(tb, space.w_None):
                operr.set_traceback(tb)
        return self.send_error(operr)

    def _gen_close_iter(self, space):
        assert not self.running
        w_yf = self.w_yielded_from
        self.w_yielded_from = None
        self.running = True
        try:
            gen_close_iter(space, w_yf)
        finally:
            self.running = False

    def descr_close(self):
        """close() -> raise GeneratorExit inside generator/coroutine."""
        if self.frame is None:
            return     # nothing to do in this case
        space = self.space
        operr = None
        # note: w_yielded_from is always None if 'self.running'
        w_yf = self.w_yielded_from
        if w_yf is not None:
            try:
                self._gen_close_iter(space)
            except OperationError as e:
                operr = e
        if operr is None:
            operr = OperationError(space.w_GeneratorExit, space.w_None)
        try:
            self.send_error(operr)
        except OperationError as e:
            if e.match(space, space.w_StopIteration) or \
                    e.match(space, space.w_GeneratorExit):
                return space.w_None
            raise
        else:
            raise oefmt(space.w_RuntimeError,
                        "%s ignored GeneratorExit", self.KIND)

    def descr_gicr_frame(self, space):
        if self.frame is not None and not self.frame.frame_finished_execution:
            return self.frame
        else:
            return space.w_None

    def descr__name__(self, space):
        return space.newtext(self.get_name())

    def descr_set__name__(self, space, w_name):
        if space.isinstance_w(w_name, space.w_unicode):
            self._name = space.text_w(w_name)
        else:
            raise oefmt(space.w_TypeError,
                        "__name__ must be set to a string object")

    def descr__qualname__(self, space):
        return space.newtext(self.get_qualname())

    def descr_set__qualname__(self, space, w_name):
        try:
            self._qualname = space.utf8_w(w_name)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_TypeError,
                            "__qualname__ must be set to a string object")
            raise

    def _finalize_(self):
        # This is only called if the CO_YIELD_INSIDE_TRY flag is set
        # on the code object.  If the frame is still not finished and
        # finally or except blocks are present at the current
        # position, then raise a GeneratorExit.  Otherwise, there is
        # no point.
        if self.frame is not None:
            block = self.frame.lastblock
            while block is not None:
                if not isinstance(block, LoopBlock):
                    self.descr_close()
                    break
                block = block.previous

    def frame_is_finished(self):
        self.frame = None
        rgc.may_ignore_finalizer(self)


class GeneratorIterator(GeneratorOrCoroutine):
    "An iterator created by a generator."
    KIND = "generator"
    KIND_U = u"generator"

    def descr__iter__(self):
        """Implement iter(self)."""
        return self

    def descr_next(self):
        """Implement next(self)."""
        return self.send_ex(self.space.w_None)

    # Results can be either an RPython list of W_Root, or it can be an
    # app-level W_ListObject, which also has an append() method, that's why we
    # generate 2 versions of the function and 2 jit drivers.
    def _create_unpack_into():
        jitdriver = jit.JitDriver(greens=['pycode'],
                                  reds=['self', 'frame', 'results'],
                                  name='unpack_into')

        def unpack_into(self, results):
            """This is a hack for performance: runs the generator and collects
            all produced items in a list."""
            frame = self.frame
            if frame is None:    # already finished
                return
            pycode = self.pycode
            while True:
                jitdriver.jit_merge_point(self=self, frame=frame,
                                          results=results, pycode=pycode)
                space = self.space
                try:
                    w_result = self._invoke_execute_frame(
                                            frame, space.w_None)
                except OperationError as e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break
                # if the frame is now marked as finished, it was RETURNed from
                if frame.frame_finished_execution:
                    self.frame_is_finished()
                    break
                results.append(w_result)     # YIELDed
        return unpack_into
    unpack_into = _create_unpack_into()
    unpack_into_w = _create_unpack_into()


class Coroutine(GeneratorOrCoroutine):
    "A coroutine object."
    KIND = "coroutine"
    KIND_U = u"coroutine"

    def descr__await__(self, space):
        return CoroutineWrapper(self)

    def _finalize_(self):
        # If coroutine was never awaited on issue a RuntimeWarning.
        if self.pycode is not None and \
           self.frame is not None and \
           self.frame.last_instr == -1:
            space = self.space
            msg = "coroutine '%s' was never awaited" % self.get_qualname()
            space.warn(space.newtext(msg), space.w_RuntimeWarning)
        GeneratorOrCoroutine._finalize_(self)


class CoroutineWrapper(W_Root):
    _immutable_ = True

    def __init__(self, coroutine):
        self.coroutine = coroutine

    def descr__iter__(self, space):
        return self

    def descr__next__(self, space):
        return self.coroutine.send_ex(space.w_None)

    def descr_send(self, space, w_arg):
        return self.coroutine.send_ex(w_arg)
    descr_send.__doc__ = Coroutine.descr_send.__doc__

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        return self.coroutine.throw(w_type, w_val, w_tb)
    descr_throw.__doc__ = Coroutine.descr_throw.__doc__

    def descr_close(self):
        return self.coroutine.descr_close()
    descr_close.__doc__ = Coroutine.descr_close.__doc__


class AIterWrapper(W_Root):
    # NB. this type was added in CPython 3.5.2
    _immutable_ = True

    def __init__(self, w_aiter):
        self.w_aiter = w_aiter

    def descr__await__(self, space):
        return self

    def descr__iter__(self, space):
        return self

    def descr__next__(self, space):
        raise stopiteration_value(space, self.w_aiter)

def stopiteration_value(space, w_value):
    # Mess.  The obvious line, "OperationError(w_StopIteration, w_value)",
    # fails for some types of w_value.  E.g. if it's a subclass of
    # tuple, it will be unpacked as individual arguments.
    raise OperationError(space.w_StopIteration,
                         space.call_function(space.w_StopIteration, w_value))


def gen_close_iter(space, w_yf):
    # This helper function is used by close() and throw() to
    # close a subiterator being delegated to by yield-from.
    if isinstance(w_yf, GeneratorIterator) or isinstance(w_yf, Coroutine):
        w_yf.descr_close()
    else:
        try:
            w_close = space.getattr(w_yf, space.newtext("close"))
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                # aaaaaaaah but that's what CPython does too
                e.write_unraisable(space, "generator/coroutine.close()")
        else:
            space.call_function(w_close)

def delegate_to_nongen(space, w_yf, w_inputvalue_or_err):
    # invoke a "send" or "throw" by method name to a non-generator w_yf
    if isinstance(w_inputvalue_or_err, SApplicationException):
        operr = w_inputvalue_or_err.operr
        try:
            w_meth = space.getattr(w_yf, space.newtext("throw"))
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                raise
            raise operr
        # bah, CPython calls here with the exact same arguments as
        # originally passed to throw().  In our case it is far removed.
        # Let's hope nobody will complain...
        operr.normalize_exception(space)
        w_exc = operr.w_type
        w_val = operr.get_w_value(space)
        w_tb  = operr.get_w_traceback(space)
        return space.call_function(w_meth, w_exc, w_val, w_tb)
    else:
        return space.call_method(w_yf, "send", w_inputvalue_or_err)

def gen_is_coroutine(w_obj):
    return (isinstance(w_obj, GeneratorIterator) and
            (w_obj.pycode.co_flags & consts.CO_ITERABLE_COROUTINE) != 0)

def get_awaitable_iter(space, w_obj):
    # This helper function returns an awaitable for `o`:
    #    - `o` if `o` is a coroutine-object;
    #    - otherwise, o.__await__()

    if isinstance(w_obj, Coroutine) or gen_is_coroutine(w_obj):
        return w_obj

    w_await = space.lookup(w_obj, "__await__")
    if w_await is None:
        raise oefmt(space.w_TypeError,
                    "object %T can't be used in 'await' expression",
                    w_obj)
    w_res = space.get_and_call_function(w_await, w_obj)
    if isinstance(w_res, Coroutine) or gen_is_coroutine(w_res):
        raise oefmt(space.w_TypeError,
                    "__await__() returned a coroutine (it must return an "
                    "iterator instead, see PEP 492)")
    elif space.lookup(w_res, "__next__") is None:
        raise oefmt(space.w_TypeError,
                "__await__() returned non-iterator "
                "of type '%T'", w_res)
    return w_res


# ----------


def get_printable_location_genentry(bytecode):
    return '%s <generator>' % (bytecode.get_repr(),)
generatorentry_driver = jit.JitDriver(greens=['pycode'],
                                      reds=['gen', 'w_arg'],
                                      get_printable_location =
                                          get_printable_location_genentry,
                                      name='generatorentry')

from pypy.tool.stdlib_opcode import HAVE_ARGUMENT, opmap
YIELD_VALUE = opmap['YIELD_VALUE']
YIELD_FROM = opmap['YIELD_FROM']

@jit.elidable_promote()
def should_not_inline(pycode):
    # Should not inline generators with more than one "yield",
    # as an approximative fix (see issue #1782).  There are cases
    # where it slows things down; for example calls to a simple
    # generator that just produces a few simple values with a few
    # consecutive "yield" statements.  It fixes the near-infinite
    # slow-down in issue #1782, though...
    count_yields = 0
    code = pycode.co_code
    n = len(code)
    i = 0
    while i < n:
        c = code[i]
        op = ord(c)
        if op == YIELD_VALUE:
            count_yields += 1
        i += 1
        if op >= HAVE_ARGUMENT:
            i += 2
    return count_yields >= 2


# ------------------------------------------------
# Python 3.6 async generators


class AsyncGenerator(GeneratorOrCoroutine):
    "An async generator (i.e. a coroutine with a 'yield')"
    KIND = "async generator"
    KIND_U = u"async_generator"

    def __init__(self, frame, name=None, qualname=None):
        self.hooks_inited = False
        GeneratorOrCoroutine.__init__(self, frame, name, qualname)

    def init_hooks(self):
        if self.hooks_inited:
            return
        self.hooks_inited = True

        self.w_finalizer = self.space.appexec([], '''():
            import sys
            hooks = sys.get_asyncgen_hooks()
            return hooks.finalizer''')

    def _finalize_(self):
        if self.frame is not None and self.frame.lastblock is not None:
            if self.w_finalizer is not self.space.w_None:
                # XXX: this is a hack to resurrect the weakref that was cleared
                # before running _finalize_()
                if self.space.config.translation.rweakref:
                    self.frame.f_generator_wref = rweakref.ref(self)
                try:
                    self.space.call_function(self.w_finalizer, self)
                except OperationError as e:
                    e.write_unraisable(self.space, "async generator finalizer")
                return
        GeneratorOrCoroutine._finalize_(self)

    def descr__aiter__(self):
        """Return an asynchronous iterator."""
        return self

    def descr__anext__(self):
        self.init_hooks()
        return AsyncGenASend(self, self.space.w_None)

    def descr_asend(self, w_arg):
        self.init_hooks()
        return AsyncGenASend(self, w_arg)

    def descr_athrow(self, w_type, w_val=None, w_tb=None):
        self.init_hooks()
        return AsyncGenAThrow(self, w_type, w_val, w_tb)

    def descr_aclose(self):
        self.init_hooks()
        return AsyncGenAThrow(self, None, None, None)


class AsyncGenValueWrapper(W_Root):
    def __init__(self, w_value):
        self.w_value = w_value


class AsyncGenABase(W_Root):
    ST_INIT = 0
    ST_ITER = 1
    ST_CLOSED = 2

    state = ST_INIT

    def __init__(self, async_gen):
        self.space = async_gen.space
        self.async_gen = async_gen

    def descr__iter__(self):
        return self

    def descr__next__(self):
        return self.do_send(self.space.w_None)

    def descr_send(self, w_arg):
        return self.do_send(w_arg)

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        return self.do_throw(w_type, w_val, w_tb)

    def descr_close(self):
        self.state = self.ST_CLOSED

    def unwrap_value(self, w_value):
        if isinstance(w_value, AsyncGenValueWrapper):
            w_value = self.space.call_function(self.space.w_StopIteration,
                                               w_value.w_value)
            raise OperationError(self.space.w_StopIteration, w_value)
        else:
            return w_value


class AsyncGenASend(AsyncGenABase):

    def __init__(self, async_gen, w_value_to_send):
        AsyncGenABase.__init__(self, async_gen)
        self.w_value_to_send = w_value_to_send

    def do_send(self, w_arg_or_err):
        space = self.space
        if self.state == self.ST_CLOSED:
            raise OperationError(space.w_StopIteration, space.w_None)

        # We think that the code should look like this:
        #if self.w_value_to_send is not None:
        #    if not space.is_w(w_arg_or_err, space.w_None):
        #        raise ...
        #    w_arg_or_err = self.w_value_to_send
        #    self.w_value_to_send = None

        # But instead, CPython's logic is this, which we think is
        # giving nonsense results for 'g.asend(42).send(43)':
        if self.state == self.ST_INIT:
            if space.is_w(w_arg_or_err, space.w_None):
                w_arg_or_err = self.w_value_to_send
            self.state = self.ST_ITER

        try:
            w_value = self.async_gen.send_ex(w_arg_or_err)
            return self.unwrap_value(w_value)
        except OperationError as e:
            self.state = self.ST_CLOSED
            raise

    def do_throw(self, w_type, w_val, w_tb):
        space = self.space
        if self.state == self.ST_CLOSED:
            raise OperationError(space.w_StopIteration, space.w_None)
        try:
            w_value = self.async_gen.throw(w_type, w_val, w_tb)
            return self.unwrap_value(w_value)
        except OperationError as e:
            self.state = self.ST_CLOSED
            raise


class AsyncGenAThrow(AsyncGenABase):

    def __init__(self, async_gen, w_exc_type, w_exc_value, w_exc_tb):
        AsyncGenABase.__init__(self, async_gen)
        self.w_exc_type = w_exc_type
        self.w_exc_value = w_exc_value
        self.w_exc_tb = w_exc_tb

    def do_send(self, w_arg_or_err):
        # XXX FAR MORE COMPLICATED IN CPYTHON
        space = self.space
        if self.state == self.ST_CLOSED:
            raise OperationError(space.w_StopIteration, space.w_None)

        if self.state == self.ST_INIT:
            if not space.is_w(w_arg_or_err, space.w_None):
                raise OperationError(space.w_RuntimeError, space.newtext(
                    "can't send non-None value to a just-started coroutine"))
            self.state = self.ST_ITER
            throwing = True
        else:
            throwing = False

        try:
            if throwing:
                if self.w_exc_type is None:
                    # TODO: add equivalent to CPython's o->agt_gen->ag_closed = 1;
                    w_value = self.async_gen.throw(space.w_GeneratorExit,
                                                   None, None)
                    if w_value is not None and isinstance(w_value, AsyncGenValueWrapper):
                        raise oefmt(space.w_RuntimeError,
                                    "async generator ignored GeneratorExit")
                else:
                    w_value = self.async_gen.throw(self.w_exc_type,
                                                   self.w_exc_value,
                                                   self.w_exc_tb)
            else:
                w_value = self.async_gen.send_ex(w_arg_or_err)
            return self.unwrap_value(w_value)
        except OperationError as e:
            self.handle_error(e)

    def do_throw(self, w_type, w_val, w_tb):
        space = self.space
        if self.state == self.ST_INIT:
            raise OperationError(self.space.w_RuntimeError,
                space.newtext("can't do async_generator.athrow().throw()"))
        if self.state == self.ST_CLOSED:
            raise OperationError(space.w_StopIteration, space.w_None)
        try:
            w_value = self.async_gen.throw(w_type, w_val, w_tb)
            return self.unwrap_value(w_value)
        except OperationError as e:
            self.handle_error(e)

    def handle_error(self, e):
        space = self.space
        self.state = self.ST_CLOSED
        if (e.match(space, space.w_StopAsyncIteration) or
                    e.match(space, space.w_StopIteration)):
            if self.w_exc_type is None:
                # When aclose() is called we don't want to propagate
                # StopAsyncIteration or GeneratorExit; just raise
                # StopIteration, signalling that this 'aclose()' await
                # is done.
                raise OperationError(space.w_StopIteration, space.w_None)
        if e.match(space, space.w_GeneratorExit):
            if self.w_exc_type is None:
                # Ignore this error.
                raise OperationError(space.w_StopIteration, space.w_None)
        raise e
