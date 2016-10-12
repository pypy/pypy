""" Code to feed information from the optimizer via the resume code into the
optimizer of the bridge attached to a guard. """

from rpython.jit.metainterp.resumecode import numb_next_item, numb_next_n_items, unpack_numbering

# XXX at the moment this is all quite ad-hoc. Could be delegated to the
# different optimization passes

# adds the following sections at the end of the resume code:
#
# ---- known classes
# <bitfield> size is the number of reference boxes in the liveboxes
#            1 klass known
#            0 klass unknown
#            (the class is found by actually looking at the runtime value)
#            the bits are bunched in bunches of 7
#
# ----

def serialize_optimizer_knowledge(optimizer, numb_state, liveboxes, memo):
    numb_state.grow(len(liveboxes)) # bit too much
    # class knowledge
    bitfield = 0
    shifts = 0
    for box in liveboxes:
        if box.type != "r":
            continue
        info = optimizer.getptrinfo(box)
        known_class = info is not None and info.get_known_class(optimizer.cpu) is not None
        bitfield <<= 1
        bitfield |= known_class
        shifts += 1
        if shifts == 7:
            numb_state.append_int(bitfield)
            bitfield = shifts = 0
    if shifts:
        numb_state.append_int(bitfield << (7 - shifts))

def deserialize_optimizer_knowledge(optimizer, numb, runtime_boxes, liveboxes):
    # skip resume section
    index = skip_resume_section(numb, optimizer)
    # class knowledge
    bitfield = 0
    mask = 0
    for i, box in enumerate(liveboxes):
        if box.type != "r":
            continue
        if not mask:
            bitfield, index = numb_next_item(numb, index)
            mask = 0b1000000
        class_known = bitfield & mask
        mask >>= 1
        if class_known:
            cls = optimizer.cpu.ts.cls_of_box(runtime_boxes[i])
            optimizer.make_constant_class(box, cls)

def skip_resume_section(numb, optimizer):
    startcount, index = numb_next_item(numb, 0)
    return numb_next_n_items(numb, startcount, 0)
