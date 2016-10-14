
""" Resume bytecode. It goes as following:

  # ----- resume section
  [total size of resume section, unencoded]
  [<length> <virtualizable object> <numb> <numb> <numb>]    if vinfo is not None
   -OR-
  [1 <ginfo object>]                                        if ginfo is not None
   -OR-
  [0]                                                       if both are None

  [<length> <virtual> <vref> <virtual> <vref>]     for virtualrefs

  [<pc> <jitcode> <numb> <numb> <numb>]            the frames
  [<pc> <jitcode> <numb> <numb>]
  ...

  until the size of the resume section

  # ----- optimization section
  <more code>                                      further sections according to bridgeopt.py
"""

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import objectmodel

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

class Writer(object):
    def __init__(self, size):
        self.current = objectmodel.newlist_hint(size)
        self.grow(size)

    def append_short(self, item):
        self.current.append(item)

    def append_int(self, item):
        short = rffi.cast(rffi.SHORT, item)
        assert rffi.cast(lltype.Signed, short) == item
        return self.append_short(short)

    def create_numbering(self):
        return create_numbering(self.current)

    def grow(self, size):
        pass

    def patch_current_size(self, index):
        item = len(self.current)
        short = rffi.cast(rffi.SHORT, item)
        assert rffi.cast(lltype.Signed, short) == item
        self.current[index] = short

class Reader(object):
    def __init__(self, code):
        self.code = code
        self.cur_pos = 0 # index into the code
        self.items_read = 0 # number of items read

    def next_item(self):
        result, self.cur_pos =  numb_next_item(self.code, self.cur_pos)
        self.items_read += 1
        return result

    def peek(self):
        result, _ =  numb_next_item(self.code, self.cur_pos)
        return result

    def jump(self, size):
        """ jump n items forward without returning anything """
        index = self.cur_pos
        for i in range(size):
            _, index = numb_next_item(self.code, index)
        self.items_read += size
        self.cur_pos = index

    def unpack(self):
        # mainly for debugging
        return unpack_numbering(self.code)
