import py
import struct

# ____________________________________________________________
#
# Reads an image file and created all model objects

class Stream(object):
    """ Simple input stream """    
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

# ____________________________________________________________
    
class ImageReader(object):
    def __init__(self, stream):
        self.stream = stream
        
    def initialize(self):
        self.read_header()
        self.read_body()
        self.init_specialobjectdumps()
        self.init_compactclassdumps()
        self.init_genericobjects()
        
    def init_genericobjects(self):
        for dump in self.pointer2dump.itervalues():
            dump.as_g_object(self)        
        
    def read_header(self):
        version = self.stream.next()
        if version != 0x1966: raise NotImplementedError
        self.headersize = self.stream.next()
        self.endofmemory = self.stream.next()   
        self.oldbaseaddress = self.stream.next()   
        self.specialobjectspointer = self.stream.next()   
        lasthash = self.stream.next()
        savedwindowssize = self.stream.next()
        fullscreenflag = self.stream.next()
        extravmmemory = self.stream.next()
        self.stream.skipbytes(self.headersize - (9 * 4))
        
    def read_body(self):
        dumps = []
        self.pointer2dump = {}
        while self.stream.pos <= self.endofmemory:
            dump = self.read_object()
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
        
    def init_actualobjects(self):
        for dump in self.pointer2dump.itervalues():
            dump.get_actual() # initialization            

    def read_object(self):
        kind = self.stream.peek() & 3 # 2 bits
        if kind == 0: # 00 bits 
            dump = self.read_3wordobjectheader()
        elif kind == 1: # 01 bits
            dump = self.read_2wordobjectheader()
        elif kind == 3: # 11 bits
            dump = self.read_1wordobjectheader()
        else: # 10 bits
            raise CorruptImageError("Unused block not allowed in image")
        size = dump.size
        dump.data = [self.stream.next() 
                     for _ in range(size - 1)] #size-1, excluding header   
        return dump     
        
    def read_1wordobjectheader(self):
        kind, size, format, classid, idhash = (
            splitbits(self.stream.next(), [2,6,4,5,12]))
        assert kind == 3
        return ObjectDump(size, format, classid, idhash, self.stream.pos - 4,
                          compact = True)

    def read_2wordobjectheader(self):
        assert splitbits(self.stream.peek(), [2])[0] == 1 #kind
        classid = self.stream.next() - 1 # remove headertype to get pointer
        kind, size, format, _, idhash = splitbits(self.stream.next(), [2,6,4,5,12])
        assert kind == 1
        return ObjectDump(size, format, classid, idhash, self.stream.pos - 4)

    def read_3wordobjectheader(self):
        kind, size = splitbits(self.stream.next(), [2,30]) 
        assert kind == 0
        assert splitbits(self.stream.peek(), [2])[0] == 0 #kind
        classid = self.stream.next() - 0 # remove headertype to get pointer
        kind, _, format, _, idhash = splitbits(self.stream.next(), [2,6,4,5,12])
        assert kind == 0
        return ObjectDump(size, format, classid, idhash, self.stream.pos - 4)

COMPACT_CLASSES_ARRAY = 28

class GenericObject(object):
    def __init__(self):
        self.owner = None
        
    def isinitialized(self):
        return self.owner is not None     
    
    def initialize(self, dump, reader):
        self.owner = reader
        self.size = dump.size
        self.hash12 = dump.idhash 
        self.format = dump.format
        self.init_class(dump)
        self.init_data(dump) 
        
    def init_class(self, dump):    
        if dump.compact:
            self.g_class = self.owner.ccdumps[dump.classid].as_g_object(self.owner)
        else:
            self.g_class = self.owner.pointer2dump[dump.classid].as_g_object(self.owner)
            
    def isbytes(self):
        return 8 <= self.format <= 11
        
    def iswords(self):
        return self.format == 6
        
    def ispointers(self):
        return self.format < 8 #TODO, what about compiled methods?             
            
    def init_data(self, dump):        
        if not self.ispointers(): return
        self.data = [self.owner.pointer2dump[p].as_g_object(self.owner)
                     for p in dump.data]

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
        self.g_object = GenericObject()
    
    def __eq__(self, other):
        "(for testing)"
        return (self.__class__ is other.__class__ and 
                self.pos == other.pos and
                self.format == other.format and
                self.classid == other.classid and
                self.idhash == other.idhash and
                self.compact == other.compact)

    def __ne__(self, other):
        "(for testing)"
        return not self == other
        
    def get_actual(self):
        if self.actual is None: 
            self.actual = self.create_actual()
        return self.actual    
        
    def as_g_object(self, reader):
        if self.g_object.isinitialized():
            self.g_object.initialize(self, reader)
        return self.g_object        
        
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
        
            
            
