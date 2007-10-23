import py
import StringIO
from pypy.lang.smalltalk import squeakimage

filepath = py.magic.autopath().dirpath().dirpath().join('mini.image')

def test_miniimageexists():
    assert filepath.check(dir=False)

def test_reader():
    f = StringIO.StringIO('\x00\x00\x19\x66')
    reader = squeakimage.Stream(f)
    first = reader.peek()
    assert first == 6502 
    first = reader.next()
    assert first == 6502 
    py.test.raises(IndexError, lambda: reader.next())
    
def test_swap():
    f = StringIO.StringIO('\x66\x19\x00\x00')
    reader = squeakimage.Stream(f)
    reader.swap = True
    first = reader.next()
    assert first == 6502 
    py.test.raises(IndexError, lambda: reader.next())
    
def test_many():
    f = StringIO.StringIO('\x00\x00\x19\x66' * 5)
    reader = squeakimage.Stream(f)
    for each in range(5):
        first = reader.peek()
        assert first == 6502 
        value = reader.next()
        assert value == 6502 
    py.test.raises(IndexError, lambda: reader.next())
    
def test_skipbytes():
    f = StringIO.StringIO('\xFF\xFF\xFF\x00\x00\x19\x66')     
    reader = squeakimage.Stream(f)
    reader.skipbytes(3)
    value = reader.next()
    assert value == 6502 
    py.test.raises(IndexError, lambda: reader.next())
        
def test_splitbits():
    assert ([1] * 4) == squeakimage.splitbits(0x01010101, [8,8,8,8])
    assert ([255] * 4) == squeakimage.splitbits(0xFfFfFfFf, [8,8,8,8])
    assert [4,3,2,1] == squeakimage.splitbits(0x01020304, [8,8,8,8])
    assert [1,3,7,15] == squeakimage.splitbits(0xFfFfFfFf, [1,2,3,4])
    
def test_readheader():
    reader = squeakimage.Stream(filepath.open())
    ireader = squeakimage.ImageReader(reader)
    ireader.read_header()
    assert ireader.endofmemory == 0x93174
    assert ireader.oldbaseaddress == 0x6649000
    assert ireader.specialobjectspointer == 0x6668380
    next = reader.next()
    assert next != 0 #expects object header, which can not be 0x0 

def test_readheader_and_body():
    reader = squeakimage.Stream(filepath.open())
    ireader = squeakimage.ImageReader(reader)
    ireader.read_header()
    objects = ireader.read_body()
    assert len(objects) > 0
    assert 15000 < len(objects) < 16000 

def imagereader_mock(string):
    f = StringIO.StringIO(string)
    reader = squeakimage.Stream(f)
    return squeakimage.ImageReader(reader)
    
def joinbits(values, lengths):
    result = 0
    for each, length in reversed(zip(values, lengths)):
        result = result << length
        result += each
    return result   
    
def test_joinbits():
    assert 0x01010101 == joinbits(([1] * 4), [8,8,8,8])
    assert 0xFfFfFfFf == joinbits([255] * 4, [8,8,8,8])
    assert 0x01020304 == joinbits([4,3,2,1], [8,8,8,8])
    assert 0x3Ff == joinbits([1,3,7,15], [1,2,3,4])
    
def ints2str(*ints):
    import struct
    return struct.pack(">" + "i" * len(ints), *ints)
    
def test_ints2str():
    assert "\x00\x00\x00\x02" == ints2str(2)       
    assert '\x00\x00\x19\x66\x00\x00\x00\x02' == ints2str(6502,2)
    
def test_freeblock():
    r = imagereader_mock("\x00\x00\x00\x02")
    py.test.raises(squeakimage.CorruptImageError, lambda: r.read_object())

def test_1wordobjectheader():
    s = ints2str(joinbits([3, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s)
    assert squeakimage.ObjectDump(1, 2, 3, 4, 0, True) == r.read_1wordobjectheader()

def test_1wordobjectheader2():
    s = ints2str(joinbits([3, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s * 3)
    assert squeakimage.ObjectDump(1, 2, 3, 4, 0, True) == r.read_1wordobjectheader()
    assert squeakimage.ObjectDump(1, 2, 3, 4, 4, True) == r.read_1wordobjectheader()
    assert squeakimage.ObjectDump(1, 2, 3, 4, 8, True) == r.read_1wordobjectheader()

def test_2wordobjectheader():
    s = ints2str(4200 + 1, joinbits([1, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s)
    assert squeakimage.ObjectDump(1, 2, 4200, 4, 4) == r.read_2wordobjectheader()

def test_3wordobjectheader():
    s = ints2str(1701 << 2, 4200 + 0, joinbits([0, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s)
    assert squeakimage.ObjectDump(1701, 2, 4200, 4, 8) == r.read_3wordobjectheader()
    
def test_read3wordheaderobject():
    size = 42
    s = ints2str(size << 2, 4200 + 0, joinbits([0, 1, 2, 3, 4], [2,6,4,5,12]))
    r = imagereader_mock(s + '\x00\x00\x19\x66' * (size - 1))
    dump = r.read_object()
    dump0 = squeakimage.ObjectDump(size, 2, 4200, 4, 8)
    dump0.data = [6502] * (size - 1)
    assert dump0 == dump
    
def test_smoketest0():
    reader = squeakimage.Stream(filepath.open())
    ireader = squeakimage.ImageReader(reader)
    ireader.initialize()
    
    
def test_smoketest():
    reader = squeakimage.Stream(filepath.open())
    ireader = squeakimage.ImageReader(reader)
    ireader.read_header()
    ireader.read_body()
    ireader.init_specialobjectdumps()
    ireader.init_compactclassdumps()
    #ireader.init_actualobjects()
           
    