
""" Resume bytecode. It goes as following:

<numb> <numb> <pc> <jitcode> <numb> <numb> <numb> <pc> <jitcode>

until the length of the array, then to the parent at the convinient index.
numb are encoded in the variable length byte encoding as follows:
if the first bit is set, then it's the first
7 bits then the next byte, otherwise it's the next 7 bit.
"""

from rpython.rtyper.lltypesystem import rffi, lltype

NUMBERINGP = lltype.Ptr(lltype.GcForwardReference())
NUMBERING = lltype.GcStruct('Numbering',
                            ('prev', NUMBERINGP),
                            ('prev_index', rffi.USHORT),
                            ('code', lltype.Array(rffi.UCHAR)))
NUMBERINGP.TO.become(NUMBERING)
NULL_NUMBER = lltype.nullptr(NUMBERING)

def create_numbering(lst, prev, prev_index):
	count = 0
	for item in lst:
		if item > 127:
			count += 1
		count += 1
	numb = lltype.malloc(NUMBERING, count)
	numb.prev = prev
	numb.prev_index = rffi.cast(rffi.USHORT, prev_index)
	index = 0
	for item in lst:
		if item <= 128:
			numb.code[index] = rffi.cast(rffi.UCHAR, item)
			index += 1
		else:
			assert (item >> 8) <= 127
			numb.code[index] = rffi.cast(rffi.UCHAR, (item >> 8) | 0x80)
			numb.code[index + 1] = rffi.cast(rffi.UCHAR, item & 0xff)
			index += 2
	return numb

def copy_from_list_to_numb(lst, numb, index):
	i = 0
	while i < len(lst):
		numb.code[i + index] = lst[i]
		i += 1

def numb_next_item(numb, index):
	one = rffi.cast(lltype.Signed, numb.code[index])
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
