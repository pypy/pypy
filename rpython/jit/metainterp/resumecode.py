
""" Resume bytecode. It goes as following:

<numb> <numb> <pc> <jitcode> <numb> <numb> <numb> <pc> <jitcode>

until the length of the array.

The interface is only create_numbering/numb_next_item, but! there is a trick
that uses first_snapshot_size + some knowledge about inside to decode
virtualref/virtualizable_fields/virtualizable in that order in resume.py.

If the algorithm changes, the part about how to find where virtualizable
and virtualrefs are to be found
"""

from rpython.rtyper.lltypesystem import rffi, lltype

NUMBERINGP = lltype.Ptr(lltype.GcForwardReference())
NUMBERING = lltype.GcStruct('Numbering',
#                            ('prev', NUMBERINGP),
#                            ('prev_index', rffi.USHORT),
                            ('first_snapshot_size', rffi.USHORT), # ugh, ugly
                            ('code', lltype.Array(rffi.SHORT)))
NUMBERINGP.TO.become(NUMBERING)
NULL_NUMBER = lltype.nullptr(NUMBERING)

# this is the actually used version

def create_numbering(lst, first_snapshot_size):
    numb = lltype.malloc(NUMBERING, len(lst))
    for i in range(len(lst)):
        numb.code[i] = rffi.cast(rffi.SHORT, lst[i])
    numb.first_snapshot_size = rffi.cast(rffi.USHORT, first_snapshot_size)
    return numb

def numb_next_item(numb, index):
    return rffi.cast(lltype.Signed, numb.code[index]), index + 1

# this is the version that can be potentially used

def _create_numbering(lst, prev, prev_index, first_snapshot_size):
    count = 0
    for item in lst:
        if item < 0:
            if item < -63:
                count += 1
        if item > 127:
            count += 1
        count += 1
    numb = lltype.malloc(NUMBERING, count)
    numb.prev = prev
    numb.prev_index = rffi.cast(rffi.USHORT, prev_index)
    numb.first_snapshot_size = rffi.cast(rffi.USHORT, first_snapshot_size)
    index = 0
    for item in lst:
        if 0 <= item <= 128:
            numb.code[index] = rffi.cast(rffi.UCHAR, item)
            index += 1
        else:
            assert (item >> 8) <= 63
            if item < 0:
                item = -item
                if item <= 63:
                    numb.code[index] = rffi.cast(rffi.UCHAR, item | 0x40)
                    index += 1
                else:
                    numb.code[index] = rffi.cast(rffi.UCHAR, (item >> 8) | 0x80 | 0x40)
                    numb.code[index + 1] = rffi.cast(rffi.UCHAR, item & 0xff)
                    index += 2
            else:
                numb.code[index] = rffi.cast(rffi.UCHAR, (item >> 8) | 0x80)
                numb.code[index + 1] = rffi.cast(rffi.UCHAR, item & 0xff)
                index += 2
    return numb

def copy_from_list_to_numb(lst, numb, index):
    i = 0
    while i < len(lst):
        numb.code[i + index] = lst[i]
        i += 1

def _numb_next_item(numb, index):
    one = rffi.cast(lltype.Signed, numb.code[index])
    if one & 0x40:
        if one & 0x80:
            two = rffi.cast(lltype.Signed, numb.code[index + 1])
            return -(((one & ~(0x80 | 0x40)) << 8) | two), index + 2
        else:
            return -(one & (~0x40)), index + 1
    if one & 0x80:
        two = rffi.cast(lltype.Signed, numb.code[index + 1])
        return ((one & 0x7f) << 8) | two, index + 2
    return one, index + 1

def unpack_numbering(numb):
    l = []
    i = 0
    while i < len(numb.code):
        next, i = numb_next_item(numb, i)
        l.append(next)
    return l
