from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import jit
from pypy.interpreter.pyopcode import LoopBlock


class GeneratorIterator(Wrappable):
    "An iterator created by a generator."
    
    def __init__(self, frame):
        self.space = frame.space
        self.frame = frame
        self.running = False

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('generator_new')
        w        = space.wrap

        tup = [
            w(self.frame),
            w(self.running),
            ]

        return space.newtuple([new_inst, space.newtuple(tup)])

    def descr__iter__(self):
        """x.__iter__() <==> iter(x)"""
        return self.space.wrap(self)

    def descr_send(self, w_arg=None):
        """send(arg) -> send 'arg' into generator,
return next yielded value or raise StopIteration."""
        return self.send_ex(w_arg)

    def send_ex(self, w_arg, exc=False):
        space = self.space
        if self.running:
            raise OperationError(space.w_ValueError,
                                 space.wrap('generator already executing'))
        if self.frame.frame_finished_execution:
            raise OperationError(space.w_StopIteration, space.w_None)
        # XXX it's not clear that last_instr should be promoted at all
        # but as long as it is necessary for call_assembler, let's do it early
        last_instr = jit.hint(self.frame.last_instr, promote=True)
        if last_instr == -1:
            if w_arg and not space.is_w(w_arg, space.w_None):
                msg = "can't send non-None value to a just-started generator"
                raise OperationError(space.w_TypeError, space.wrap(msg))
        else:
            if not w_arg:
                w_arg = space.w_None
        self.running = True
        try:
            try:
                w_result = self.frame.execute_generator_frame(w_arg, exc)
            except OperationError:
                # errors finish a frame
                self.frame.frame_finished_execution = True
                raise
            # if the frame is now marked as finished, it was RETURNed from
            if self.frame.frame_finished_execution:
                raise OperationError(space.w_StopIteration, space.w_None) 
            else:
                return w_result     # YIELDed
        finally:
            self.frame.f_backref = jit.vref_None
            self.running = False

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        """throw(typ[,val[,tb]]) -> raise exception in generator,
return next yielded value or raise StopIteration."""
        return self.throw(w_type, w_val, w_tb)


    def throw(self, w_type, w_val, w_tb):
        from pypy.interpreter.pytraceback import check_traceback
        space = self.space
        
        msg = "throw() third argument must be a traceback object"
        if space.is_w(w_tb, space.w_None):
            tb = None
        else:
            tb = check_traceback(space, w_tb, msg)
       
        operr = OperationError(w_type, w_val, tb)
        operr.normalize_exception(space)
        
        ec = space.getexecutioncontext()
        next_instr = self.frame.handle_operation_error(ec, operr)
        self.frame.last_instr = intmask(next_instr - 1)

        return self.send_ex(space.w_None, True)
             
    def descr_next(self):
        """next() -> the next value, or raise StopIteration"""
        return self.send_ex(self.space.w_None)
 
    def descr_close(self):
        """close(arg) -> raise GeneratorExit inside generator."""
        space = self.space
        try:
            w_retval = self.throw(space.w_GeneratorExit, space.w_None,
                                  space.w_None)
        except OperationError, e:
            if e.match(space, space.w_StopIteration) or \
                    e.match(space, space.w_GeneratorExit):
                return space.w_None
            raise
        
        if w_retval is not None:
            msg = "generator ignored GeneratorExit"
            raise OperationError(space.w_RuntimeError, space.wrap(msg))

    def descr_gi_frame(space, self):
        if not self.frame.frame_finished_execution:
            return self.frame
        else:
            return space.w_None

    def descr__del__(self):        
        """
        applevel __del__, which is called at a safe point after the
        interp-level __del__ enqueued the object for destruction
        """
        # Only bother raising an exception if the frame is still not
        # finished and finally or except blocks are present.
        if not self.frame.frame_finished_execution:
            block = self.frame.lastblock
            while block is not None:
                if not isinstance(block, LoopBlock):
                    self.descr_close()
                    return
                block = block.previous

    def __del__(self):
        self._enqueue_for_destruction(self.space)
