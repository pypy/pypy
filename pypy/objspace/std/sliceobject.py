

class W_SliceObject(object):
    def __init__(self, w_start, w_stop, w_step):
        self.w_start = w_start
        self.w_stop = w_stop
        self.w_step = w_step
    def indices(w_self, space, w_length):
        length = space.int.as_long(w_length)
        
        if self.w_step == space.w_None:
            step = 1
        elif isinstance(self.w_step, W_IntObject):
            step = self.w_step.intval
            if step == 0:
                raise OperationError(
                    space.w_ValueError,
                    space.W_StringObject("slice step cannot be zero"))
        else:
            raise OperationError(space.w_TypeError)
            
        if step < 0:
            defstart = length - 1
            defstop = -1
        else:
            defstart = 0
            defstop = length
            
        if isinstance(self.w_start, space.W_NoneObject):
            start = defstart
        else:
            start = space.eval_slice_index(self.w_start)
            if start < 0:
                start = start + length
                if start < 0:
                    if step < 0:
                        start = -1
                    else:
                        start = 0
                elif start >= length:
                    if step < 0:
                        start = length - 1
                    else:
                        start = length

        if isinstance(self.w_stop, space.W_NoneObject):
            stop = defstop
        else:
            stop = space.eval_slice_index(self.w_stop)
            if stop < 0:
                stop = stop + length
            if stop < 0:
                stop = -1
            elif stop > length:
                stop = length

        return space.newtuple([space.W_IntObject(start),
                               space.W_IntObject(stop),
                               space.W_IntObject(step)])
                
