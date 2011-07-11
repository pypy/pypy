from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.rlib import jit
from pypy.interpreter.pyopcode import LoopBlock


class GeneratorIterator(Wrappable):
    "An iterator created by a generator."
    _immutable_fields_ = ['pycode']
    
    def __init__(self, frame):
        self.space = frame.space
        self.frame = frame     # turned into None when frame_finished_execution
        self.pycode = frame.pycode
        self.running = False

    def descr__repr__(self, space):
        code_name = self.pycode.co_name
        addrstring = self.getaddrstring(space)
        return space.wrap("<generator object %s at 0x%s>" %
                          (code_name, addrstring))

    def descr__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('generator_new')
        w        = space.wrap
        if self.frame:
            w_frame = w(self.frame)
        else:
            w_frame = space.w_None

        tup = [
            w_frame,
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

    def send_ex(self, w_arg, operr=None):
        space = self.space
        if self.running:
            raise OperationError(space.w_ValueError,
                                 space.wrap('generator already executing'))
        frame = self.frame
        if frame is None:
            # xxx a bit ad-hoc, but we don't want to go inside
            # execute_frame() if the frame is actually finished
            if operr is None:
                operr = OperationError(space.w_StopIteration, space.w_None)
            raise operr
        # XXX it's not clear that last_instr should be promoted at all
        # but as long as it is necessary for call_assembler, let's do it early
        last_instr = jit.promote(frame.last_instr)
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
                w_result = frame.execute_frame(w_arg, operr)
            except OperationError:
                # errors finish a frame
                self.frame = None
                raise
            # if the frame is now marked as finished, it was RETURNed from
            if frame.frame_finished_execution:
                self.frame = None
                raise OperationError(space.w_StopIteration, space.w_None) 
            else:
                return w_result     # YIELDed
        finally:
            frame.f_backref = jit.vref_None
            self.running = False

    def descr_throw(self, w_type, w_val=None, w_tb=None):
        """x.throw(typ[,val[,tb]]) -> raise exception in generator,
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
        except OperationError, e:
            if e.match(space, space.w_StopIteration) or \
                    e.match(space, space.w_GeneratorExit):
                return space.w_None
            raise
        
        if w_retval is not None:
            msg = "generator ignored GeneratorExit"
            raise OperationError(space.w_RuntimeError, space.wrap(msg))

    def descr_gi_frame(self, space):
        if self.frame is not None and not self.frame.frame_finished_execution:
            return self.frame
        else:
            return space.w_None

    def descr_gi_code(self, space):
        return self.pycode

    def descr__name__(self, space):
        code_name = self.pycode.co_name
        return space.wrap(code_name)

    def __del__(self):
        # Only bother enqueuing self to raise an exception if the frame is
        # still not finished and finally or except blocks are present.
        self.clear_all_weakrefs()
        if self.frame is not None:
            block = self.frame.lastblock
            while block is not None:
                if not isinstance(block, LoopBlock):
                    self.enqueue_for_destruction(self.space,
                                                 GeneratorIterator.descr_close,
                                                 "interrupting generator of ")
                    break
                block = block.previous
