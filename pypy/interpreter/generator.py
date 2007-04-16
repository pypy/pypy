from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable


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

    def descr_next(self):
        """x.next() -> the next value, or raise StopIteration"""
        space = self.space
        if self.running:
            raise OperationError(space.w_ValueError,
                                 space.wrap('generator already executing'))
        if self.frame.frame_finished_execution:
            raise OperationError(space.w_StopIteration, space.w_None) 
        self.running = True
        try:
            try:
                w_result = self.frame.execute_generator_frame(space.w_None)
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
            self.frame.f_back = None
            self.running = False
