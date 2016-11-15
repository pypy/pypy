
""" Resume bytecode. It goes as following:

  [<length> <virtualizable object> <numb> <numb> <numb>]    if vinfo is not None
   -OR-
  [1 <ginfo object>]                                        if ginfo is not None
   -OR-
  [0]                                                       if both are None

  [<length> <virtual> <vref> <virtual> <vref>]     for virtualrefs

  [<pc> <jitcode> <numb> <numb> <numb>]            the frames
  [<pc> <jitcode> <numb> <numb>]
  ...

  until the length of the array.
"""

from rpython.rtyper.lltypesystem import rffi, lltype

NUMBERINGP = lltype.Ptr(lltype.GcForwardReference())
NUMBERING = lltype.GcStruct('Numbering',
                            ('code', lltype.Array(rffi.UCHAR)))
NUMBERINGP.TO.become(NUMBERING)
NULL_NUMBER = lltype.nullptr(NUMBERING)

def create_numbering(lst, total=-1):
    if total == -1:
        total = len(lst)
    result = []
    for i in range(total):
        item = lst[i]
        item = rffi.cast(lltype.Signed, item)
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
numb_next_item._always_inline_ = True

def numb_next_n_items(numb, size, index):
    for i in range(size):
        _, index = numb_next_item(numb, index)
    return index

def unpack_numbering(numb):
    l = []
    i = 0
    while i < len(numb.code):
        next, i = numb_next_item(numb, i)
        l.append(next)
    return l
