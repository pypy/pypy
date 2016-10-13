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
# ---- heap knowledge
# <length>
# (<box1> <descr> <box2>) length times, if getfield(box1, descr) == box2
#                         both boxes should be in the liveboxes
#
# ----

def tag_box(box, liveboxes_from_env, memo):
    from rpython.jit.metainterp.history import Const
    # XXX bit of code duplication (but it's a subset)
    if isinstance(box, Const):
        return memo.getconst(box)
    else:
        return liveboxes_from_env[box] # has to exist

def decode_box(resumestorage, tagged, liveboxes, cpu):
    from rpython.jit.metainterp.resume import untag, TAGCONST, TAGINT, TAGBOX
    from rpython.jit.metainterp.resume import NULLREF, TAG_CONST_OFFSET, tagged_eq
    from rpython.jit.metainterp.history import ConstInt
    num, tag = untag(tagged)
    if tag == TAGCONST:
        if tagged_eq(tagged, NULLREF):
            box = cpu.ts.CONST_NULL
        else:
            box = resumestorage.rd_consts[num - TAG_CONST_OFFSET]
    elif tag == TAGINT:
        box = ConstInt(num)
    elif tag == TAGBOX:
        box = liveboxes[num]
    else:
        raise AssertionError("unreachable")
    return box

def serialize_optimizer_knowledge(optimizer, numb_state, liveboxes, liveboxes_from_env, memo):
    liveboxes_set = {}
    for box in liveboxes:
        if box is not None:
            liveboxes_set[box] = None
    metainterp_sd = optimizer.metainterp_sd

    numb_state.grow(len(liveboxes)) # bit too much
    # class knowledge
    bitfield = 0
    shifts = 0
    for box in liveboxes:
        if box is None or box.type != "r":
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

    # heap knowledge
    if optimizer.optheap:
        triples = optimizer.optheap.serialize_optheap(liveboxes_set)
        numb_state.grow(len(triples) * 3 + 1)
        numb_state.append_int(len(triples))
        for box1, descr, box2 in triples:
            index = metainterp_sd.descrs_dct.get(descr, -1)
            if index == -1:
                continue # just skip it, if the descr is not encodable
            numb_state.append_short(tag_box(box1, liveboxes_from_env, memo))
            numb_state.append_int(index)
            numb_state.append_short(tag_box(box2, liveboxes_from_env, memo))
    else:
        numb_state.grow(1)
        numb_state.append_int(0)

def deserialize_optimizer_knowledge(optimizer, resumestorage, frontend_boxes, liveboxes):
    assert len(frontend_boxes) == len(liveboxes)
    numb = resumestorage.rd_numb
    metainterp_sd = optimizer.metainterp_sd

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
            cls = optimizer.cpu.ts.cls_of_box(frontend_boxes[i])
            optimizer.make_constant_class(box, cls)

    # heap knowledge
    length, index = numb_next_item(numb, index)
    result = []
    for i in range(length):
        tagged, index = numb_next_item(numb, index)
        box1 = decode_box(resumestorage, tagged, liveboxes, metainterp_sd.cpu)
        tagged, index = numb_next_item(numb, index)
        descr = metainterp_sd.opcode_descrs[tagged]
        tagged, index = numb_next_item(numb, index)
        box2 = decode_box(resumestorage, tagged, liveboxes, metainterp_sd.cpu)
        result.append((box1, descr, box2))
    if optimizer.optheap:
        optimizer.optheap.deserialize_optheap(result)

def skip_resume_section(numb, optimizer):
    startcount, index = numb_next_item(numb, 0)
    return numb_next_n_items(numb, startcount, 0)
