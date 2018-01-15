from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.pyopcode import LoopBlock
from pypy.interpreter.pycode import CO_YIELD_INSIDE_TRY
from rpython.rlib import jit, rgc


class GeneratorIterator(W_Root):
    "An iterator created by a generator."
    _immutable_fields_ = ['pycode']

    def __init__(self, frame):
        self.space = frame.space
        self.frame = frame     # turned into None when frame_finished_execution
        self.pycode = frame.pycode
        self.running = False
        if self.pycode.co_flags & CO_YIELD_INSIDE_TRY:
            self.register_finalizer(self.space)

    def descr__repr__(self, space):
        if self.pycode is None:
            code_name = '<finished>'
        else:
            code_name = self.pycode.co_name
        addrstring = self.getaddrstring(space)
        return space.newtext("<generator object %s at 0x%s>" %
                             (code_name, addrstring))

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('generator_new')
        if self.frame:
            w_frame = self.frame._reduce_state(space)
        else:
            w_frame = space.w_None

        tup = [
            w_frame,
            space.newbool(self.running),
            ]

        return space.newtuple([new_inst, space.newtuple([]),
                               space.newtuple(tup)])

    def descr__setstate__(self, space, w_args):
        from rpython.rlib.objectmodel import instantiate
        args_w = space.unpackiterable(w_args)
        w_framestate, w_running = args_w
        if space.is_w(w_framestate, space.w_None):
            self.frame = None
            self.space = space
            self.pycode = None
        else:
            frame = instantiate(space.FrameClass)   # XXX fish
            frame.descr__setstate__(space, w_framestate)
            GeneratorIterator.__init__(self, frame)
        self.running = self.space.is_true(w_running)

    def descr__iter__(self):
        """x.__iter__() <==> iter(x)"""
        return self

    def descr_send(self, w_arg):
        """send(arg) -> send 'arg' into generator,
return next yielded value or raise StopIteration."""
        return self.send_ex(w_arg)

    def send_ex(self, w_arg, operr=None):
        pycode = self.pycode
        if pycode is not None:
            if jit.we_are_jitted() and should_not_inline(pycode):
                generatorentry_driver.jit_merge_point(gen=self, w_arg=w_arg,
                                                    operr=operr, pycode=pycode)
        return self._send_ex(w_arg, operr)

    def _send_ex(self, w_arg, operr):
        space = self.space
        if self.running:
            raise oefmt(space.w_ValueError, "generator already executing")
        frame = self.frame
        if frame is None:
            # xxx a bit ad-hoc, but we don't want to go inside
            # execute_frame() if the frame is actually finished
            if operr is None:
                operr = OperationError(space.w_StopIteration, space.w_None)
            raise operr

        last_instr = jit.promote(frame.last_instr)
        if last_instr == -1:
            if w_arg and not space.is_w(w_arg, space.w_None):
                raise oefmt(space.w_TypeError,
                            "can't send non-None value to a just-started "
                            "generator")
        else:
            if not w_arg:
                w_arg = space.w_None
        self.running = True
        try:
            try:
                w_result = frame.execute_frame(w_arg, operr)
            except OperationError:
                # errors finish a frame
                self.frame_is_finished()
                raise
            # if the frame is now marked as finished, it was RETURNed from
            if frame.frame_finished_execution:
                self.frame_is_finished()
                raise OperationError(space.w_StopIteration, space.w_None)
            else:
                return w_result     # YIELDed
        finally:
            frame.f_backref = jit.vref_None
            self.running = False

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        """x.throw(typ[,val[,tb]]) -> raise exception in generator,
return next yielded value or raise StopIteration."""
        if w_val is None:
            w_val = self.space.w_None
        return self.throw(w_type, w_val, w_tb)

    def throw(self, w_type, w_val, w_tb):
        from pypy.interpreter.pytraceback import check_traceback
        space = self.space

        msg = "throw() third argument must be a traceback object"
        if space.is_none(w_tb):
            tb = None
        else:
            tb = check_traceback(space, w_tb, msg)

        operr = OperationError(w_type, w_val, tb)
        operr.normalize_exception(space)
        return self.send_ex(space.w_None, operr)

    def descr_next(self):
        """x.next() -> the next value, or raise StopIteration"""
        return self.send_ex(self.space.w_None)

    def descr_close(self):
        """x.close(arg) -> raise GeneratorExit inside generator."""
        space = self.space
        try:
            w_retval = self.throw(space.w_GeneratorExit, space.w_None,
                                  space.w_None)
        except OperationError as e:
            if e.match(space, space.w_StopIteration) or \
                    e.match(space, space.w_GeneratorExit):
                return space.w_None
            raise

        if w_retval is not None:
            raise oefmt(space.w_RuntimeError,
                        "generator ignored GeneratorExit")

    def descr_gi_frame(self, space):
        if self.frame is not None and not self.frame.frame_finished_execution:
            return self.frame
        else:
            return space.w_None

    def descr_gi_code(self, space):
        return self.pycode

    def descr__name__(self, space):
        if self.pycode is None:
            code_name = '<finished>'
        else:
            code_name = self.pycode.co_name
        return space.newtext(code_name)

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
            # XXX copied and simplified version of send_ex()
            space = self.space
            if self.running:
                raise oefmt(space.w_ValueError, "generator already executing")
            frame = self.frame
            if frame is None:    # already finished
                return
            self.running = True
            try:
                pycode = self.pycode
                while True:
                    jitdriver.jit_merge_point(self=self, frame=frame,
                                              results=results, pycode=pycode)
                    try:
                        w_result = frame.execute_frame(space.w_None)
                    except OperationError as e:
                        if not e.match(space, space.w_StopIteration):
                            raise
                        break
                    # if the frame is now marked as finished, it was RETURNed from
                    if frame.frame_finished_execution:
                        break
                    results.append(w_result)     # YIELDed
            finally:
                frame.f_backref = jit.vref_None
                self.running = False
                self.frame_is_finished()
        return unpack_into
    unpack_into = _create_unpack_into()
    unpack_into_w = _create_unpack_into()

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


def get_printable_location_genentry(bytecode):
    return '%s <generator>' % (bytecode.get_repr(),)
generatorentry_driver = jit.JitDriver(greens=['pycode'],
                                      reds=['gen', 'w_arg', 'operr'],
                                      get_printable_location =
                                          get_printable_location_genentry,
                                      name='generatorentry')

from pypy.tool.stdlib_opcode import HAVE_ARGUMENT, opmap
YIELD_VALUE = opmap['YIELD_VALUE']

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
