
def sliceindices(slice, length):
    step = slice.step
    if step is None:
        step = 1
    elif step == 0:
        raise ValueError, "slice step cannot be zero"
    if step < 0:
        defstart = length - 1
        defstop = -1
    else:
        defstart = 0
        defstop = length
    
    start = slice.start
    if start is None:
        start = defstart
    else:
        if start < 0:
            start += length
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

    stop = slice.stop
    if stop is None:
        stop = defstop
    else:
        if stop < 0:
            stop += length
        if stop < 0:
            stop = -1
        elif stop > length:
            stop = length

    if (step < 0 and stop >= start) or (step > 0 and start >= stop):
        slicelength = 0
    elif step < 0:
        slicelength = (stop-start+1)//step + 1
    else:
        slicelength = (stop-start-1)//step + 1

    return start, stop, step, slicelength
