import py
from pypy.lang.smalltalk import squeakimage
from pypy.lang.smalltalk.squeakimage import chrs2int
from pypy.lang.smalltalk import objspace

space = objspace.ObjSpace()

# ----- helpers ----------------------------------------------

def ints2str(*ints):
    import struct
    return struct.pack(">" + "i" * len(ints), *ints)

def joinbits(values, lengths):
    result = 0
    for each, length in reversed(zip(values, lengths)):
        result = result << length
        result += each
    return result   

def imagereader_mock(string):
    import StringIO
    f = StringIO.StringIO(string)
    stream = squeakimage.Stream(f)
    return squeakimage.ImageReader(space, stream)


# ----- tests ------------------------------------------------

def test_chrs2int():
    assert 1 == chrs2int('\x00\x00\x00\x01')
    assert -1 == chrs2int('\xFF\xFF\xFF\xFF')

def test_stream():
    stream = imagereader_mock('\x00\x00\x19\x66').stream
    n = stream.peek()
    assert n == 6502 
    n = stream.next()
    assert n == 6502 
    py.test.raises(IndexError, lambda: stream.next())
    
def test_stream_swap():
    stream = imagereader_mock('\x66\x19\x00\x00').stream
    stream.swap = True
    first = stream.next()
    assert first == 6502 
    py.test.raises(IndexError, lambda: stream.next())
    
def test_stream_many():
    stream = imagereader_mock('\x00\x00\x19\x66' * 5).stream
    for each in range(5):
        first = stream.peek()
        assert first == 6502 
        value = stream.next()
        assert value == 6502 
    py.test.raises(IndexError, lambda: stream.next())
    
def test_stream_skipbytes():
    stream = imagereader_mock('\xFF\xFF\xFF\x00\x00\x19\x66').stream
    stream.skipbytes(3)
    value = stream.next()
    assert value == 6502 
    py.test.raises(IndexError, lambda: stream.next())
        
def test_stream_count():
    stream = imagereader_mock('\xFF' * 20).stream
    stream.next()
    stream.next()
    stream.reset_count()
    assert stream.count == 0
    stream.next()        
    assert stream.count == 4
    stream.next()        
    assert stream.count == 8
    
   
def test_simple_joinbits():
    assert 0x01010101 == joinbits(([1] * 4), [8,8,8,8])
    assert 0xFfFfFfFf == joinbits([255] * 4, [8,8,8,8])
    
def test_fancy_joinbits():    
    assert 0x01020304 == joinbits([4,3,2,1], [8,8,8,8])
    assert 0x3Ff == joinbits([1,3,7,15], [1,2,3,4])
    
    
def test_ints2str():
    assert "\x00\x00\x00\x02" == ints2str(2)       
    assert '\x00\x00\x19\x66\x00\x00\x00\x02' == ints2str(6502,2)
    
def test_freeblock():
    r = imagereader_mock("\x00\x00\x00\x02")
    py.test.raises(squeakimage.CorruptImageError, lambda: r.read_object())

def test_1wordobjectheader():
    s = ints2str(joinbits([3, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s)
    assert (squeakimage.ImageChunk(space, 1, 2, 3, 4), 0) == r.read_1wordobjectheader()

def test_1wordobjectheader2():
    s = ints2str(joinbits([3, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s * 3)
    assert (squeakimage.ImageChunk(space, 1, 2, 3, 4), 0) == r.read_1wordobjectheader()
    assert (squeakimage.ImageChunk(space, 1, 2, 3, 4), 4) == r.read_1wordobjectheader()
    assert (squeakimage.ImageChunk(space, 1, 2, 3, 4), 8) == r.read_1wordobjectheader()

def test_2wordobjectheader():
    s = ints2str(4200 + 1, joinbits([1, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s)
    assert (squeakimage.ImageChunk(space, 1, 2, 4200, 4), 4) == r.read_2wordobjectheader()

def test_3wordobjectheader():
    s = ints2str(1701 << 2, 4200 + 0, joinbits([0, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s)
    assert (squeakimage.ImageChunk(space, 1701, 2, 4200, 4), 8) == r.read_3wordobjectheader()
    
def test_read3wordheaderobject():
    size = 42
    s = ints2str(size << 2, 4200 + 0, joinbits([0, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s + '\x00\x00\x19\x66' * (size - 1))
    chunk, pos = r.read_object()
    chunk0 = squeakimage.ImageChunk(space, size, 2, 4200, 4)
    chunk0.data = [6502] * (size - 1)
    assert pos == 8
    assert chunk0 == chunk
    
