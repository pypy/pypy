import py
import struct

class Reader(object):    
    def __init__(self, inputfile):
        try:
            self.data = inputfile.read()
        finally:
            inputfile.close()
        self.swap = False
        self.pos = 0

    def peek(self):
        if self.pos >= len(self.data): 
            raise IndexError
        if self.swap:
            format = "<i"
        else: 
            format = ">i"                
        integer, = struct.unpack(format, self.data[self.pos:self.pos+4])
        return integer 
        
    def next(self):
        integer = self.peek()
        self.pos += 4
        return integer 
        
    def skipbytes(self, jump):
        assert jump > 0
        assert (self.pos + jump) <= len(self.data)
        self.pos += jump    
     
def splitbits(integer, lengths):
    assert sum(lengths) <= 32
    result = []
    for length in lengths:
        result.append(integer & (2**length - 1))
        integer = integer >> length
    #XXX we can later mask and unroll this
    return result
    
class CorruptImageError(Exception):
    pass            
    
class ImageReader(object):
    def __init__(self, reader):
        self.reader = reader
        
    def readheader(self):
        version = self.reader.next()
        if version != 0x1966: raise NotImplementedError
        self.headersize = self.reader.next()
        self.endofmemory = self.reader.next()   
        self.oldbaseaddress = self.reader.next()   
        self.specialobjectspointer = self.reader.next()   
        lasthash = self.reader.next()
        savedwindowssize = self.reader.next()
        fullscreenflag = self.reader.next()
        extravmmemory = self.reader.next()
        self.reader.skipbytes(self.headersize - (9 * 4))
        
    def readbody(self):
        dumps = []
        self.pointer2dump = {}
        while self.reader.pos <= self.endofmemory:
            dump = self.readobject()
            dumps.append(dump)
            self.pointer2dump[dump.pos - self.headersize + self.oldbaseaddress] = dump
        return dumps
        
    def init_specialobjectdumps(self):
        dump = self.pointer2dump[self.specialobjectspointer]   
        assert dump.size > 24 #and more
        assert dump.format == 2
        self.sodumps = [self.pointer2dump[pointer] for pointer in dump.data]
        
    def init_compactclassdumps(self):
        dump = self.sodumps[COMPACT_CLASSES_ARRAY]  
        assert len(dump.data) == 31
        assert dump.format == 2
        self.ccdumps = [self.pointer2dump[pointer] for pointer in dump.data]   
        
    def mark_classdescription(self):
        #XXX quite some assumptions here
        for dump in self.pointer2dump.itervalues():
            if dump.compact:
                classdump = self.ccdumps[dump.classid]
            else:
                classdump = self.pointer2dump[dump.classid]
            classdump.classdescription = True                       

    def init_actualobjects(self):
        for dump in self.pointer2dump.itervalues():
            dump.get_actual() # initialization            

    def readobject(self):
        kind, = splitbits(self.reader.peek(), [2])
        if kind == 0: # 00r2 
            dump = self.read3wordobjectheader()
        elif kind == 1: # 01r2
            dump = self.read2wordobjectheader()
        elif kind == 3: # 11r2
            dump = self.read1wordobjectheader()
        else:
            raise CorruptImageError("Unused block not allowed in image")
        size = dump.size
        dump.data = [self.reader.next() 
                     for _ in range(size - 1)] #size-1, excluding header   
        return dump     
        
    def read1wordobjectheader(self):
        kind, size, format, classid, idhash = (
            splitbits(self.reader.next(), [2,6,4,5,12]))
        assert kind == 3
        return ObjectDump(size, format, classid, idhash, self.reader.pos - 4,
                          compact = True)

    def read2wordobjectheader(self):
        assert splitbits(self.reader.peek(), [2])[0] == 1 #kind
        classid = self.reader.next() - 1 # remove headertype to get pointer
        kind, size, format, _, idhash = splitbits(self.reader.next(), [2,6,4,5,12])
        assert kind == 1
        return ObjectDump(size, format, classid, idhash, self.reader.pos - 4)

    def read3wordobjectheader(self):
        kind, size = splitbits(self.reader.next(), [2,30]) 
        assert kind == 0
        assert splitbits(self.reader.peek(), [2])[0] == 0 #kind
        classid = self.reader.next() - 0 # remove headertype to get pointer
        kind, _, format, _, idhash = splitbits(self.reader.next(), [2,6,4,5,12])
        assert kind == 0
        return ObjectDump(size, format, classid, idhash, self.reader.pos - 4)

COMPACT_CLASSES_ARRAY = 28

class ObjectDump(object):
    def __init__(self, size, format, classid, idhash, pos, compact = False):
        self.pos = pos
        self.size = size
        self.format = format
        self.classid = classid
        self.idhash = idhash
        self.data = None
        self.classdescription = False
        self.actual = None
        self.compact = compact
    
    def __eq__(self, other):
        "(for testing)"
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__  

    def __ne__(self, other):
        "(for testing)"
        return not self == other
        
    def get_actual(self):
        if self.actual is None: 
            self.actual = self.create_actual()
        return self.actual    
        
    def create_actual(self):
        from pypy.lang.smalltalk import model
        if self.classdescription:
            print self.format
            return None
        if self.format == 0: # no instvars, non-indexed
            assert self.size == 0
            return model.W_PointersObject(size = 0)
        elif self.format == 1: # instvars, non-indexed      
            return model.W_PointersObject(size = self.size)
        elif self.format == 2: # no instvars, indexed        
            return model.W_PointersObject(size = self.size)
        elif self.format == 3: # instvars, indexed        
            return model.W_PointersObject(size = self.size)
        elif self.format == 4: # XXX W_WeakPointersObject         
            return model.W_PointersObject(size = self.size)
        elif self.format == 5:          
            raise CorruptImageError("Unknown format 5")
        elif self.format == 6:         
            return model.W_WordsObject(size = self.size)
        elif self.format == 7:
            raise CorruptImageError("Unknown format 7, no 64-bit support yet :-)")
        elif 8 <= self.format <= 11:
            byte_size = self.size * 4 + self.format & 3
            return model.W_BytesObject(size = byte_size)
        elif 12 <= self.format <= 15:
            return model.W_CompiledMethod(size = 0) #XXX to be figured out how to get
            #both the size of literals and the size of bytes in bytecode!!!
        else:
            assert 0, "not reachable"                
        
            
            
