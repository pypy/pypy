
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
                            ('code', lltype.Array(rffi.UCHAR)))
NUMBERINGP.TO.become(NUMBERING)
NULL_NUMBER = lltype.nullptr(NUMBERING)

# this is the actually used version

## def create_numbering(lst, first_snapshot_size):
##     numb = lltype.malloc(NUMBERING, len(lst))
##     for i in range(len(lst)):
##         numb.code[i] = rffi.cast(rffi.SHORT, lst[i])
##     numb.first_snapshot_size = rffi.cast(rffi.USHORT, first_snapshot_size)
##     return numb

## def numb_next_item(numb, index):
##     return rffi.cast(lltype.Signed, numb.code[index]), index + 1

# this is the version that can be potentially used

def create_numbering(lst, first_snapshot_size):
    result = []
    for item in lst:
        item *= 2
        if item < 0:
            item = -1 - item

        assert item >= 0
        if item < 2**7:
            result.append(rffi.cast(rffi.UCHAR, item))
        elif item < 2**14:
            result.append(rffi.cast(rffi.UCHAR, item | 0x80))
            result.append(rffi.cast(rffi.UCHAR, item >> 7))
        else:
            assert item < 2**16
            result.append(rffi.cast(rffi.UCHAR, item | 0x80))
            result.append(rffi.cast(rffi.UCHAR, (item >> 7) | 0x80))
            result.append(rffi.cast(rffi.UCHAR, item >> 14))

    numb = lltype.malloc(NUMBERING, len(result))
    numb.first_snapshot_size = rffi.cast(rffi.USHORT, first_snapshot_size)
    for i in range(len(result)):
        numb.code[i] = result[i]
    return numb

def numb_next_item(numb, index):
    value = rffi.cast(lltype.Signed, numb.code[index])
    index += 1
    if value & (2**7):
        value &= 2**7 - 1
        value |= rffi.cast(lltype.Signed, numb.code[index]) << 7
        index += 1
        if value & (2**14):
            value &= 2**14 - 1
            value |= rffi.cast(lltype.Signed, numb.code[index]) << 14
            index += 1
    if value & 1:
        value = -1 - value
    value >>= 1
    return value, index

def unpack_numbering(numb):
    l = []
    i = 0
    while i < len(numb.code):
        next, i = numb_next_item(numb, i)
        l.append(next)
    return l
