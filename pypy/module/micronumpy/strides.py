from pypy.rlib import jit


@jit.look_inside_iff(lambda shape, start, strides, backstrides, chunks:
    jit.isconstant(len(chunks))
)
def calculate_slice_strides(shape, start, strides, backstrides, chunks):
    rstrides = []
    rbackstrides = []
    rstart = start
    rshape = []
    i = -1
    for i, chunk in enumerate(chunks):
        if chunk.step != 0:
            rstrides.append(strides[i] * chunk.step)
            rbackstrides.append(strides[i] * (chunk.lgt - 1) * chunk.step)
            rshape.append(chunk.lgt)
        rstart += strides[i] * chunk.start
    # add a reminder
    s = i + 1
    assert s >= 0
    rstrides += strides[s:]
    rbackstrides += backstrides[s:]
    rshape += shape[s:]
    return rshape, rstart, rstrides, rbackstrides

def calculate_broadcast_strides(strides, backstrides, orig_shape, res_shape):
    rstrides = []
    rbackstrides = []
    for i in range(len(orig_shape)):
        if orig_shape[i] == 1:
            rstrides.append(0)
            rbackstrides.append(0)
        else:
            rstrides.append(strides[i])
            rbackstrides.append(backstrides[i])
    rstrides = [0] * (len(res_shape) - len(orig_shape)) + rstrides
    rbackstrides = [0] * (len(res_shape) - len(orig_shape)) + rbackstrides
    return rstrides, rbackstrides
