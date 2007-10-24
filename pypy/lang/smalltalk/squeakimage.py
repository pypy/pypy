import py
import struct
from pypy.lang.smalltalk import model 
from pypy.lang.smalltalk import fakeimage 
from pypy.rlib import objectmodel

def int2str(integer):
    return (chr((integer & 0xff000000) >> 24) + 
            chr((integer & 0x00ff0000) >> 16) + 
            chr((integer & 0x0000ff00) >>  8) + 
            chr((integer & 0x000000ff)))

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
        self.count = 0

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
        self.count += 4
        return integer 
        
    def reset_count(self):
        self.count = 0    
        
    def skipbytes(self, jump):
        assert jump > 0
        assert (self.pos + jump) <= len(self.data)
        self.pos += jump 
        self.count += jump   
     
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
        self.init_compactclassesarray()
        self.init_g_objects()
        
    def init_g_objects(self):
        for chunk in self.chunks.itervalues():
            chunk.as_g_object(self)        

    def init_w_objects(self):
        for chunk in self.chunks.itervalues():
            chunk.g_object.init_w_object()

    def fillin_w_objects(self):
        for chunk in self.chunks.itervalues():
            chunk.g_object.fillin_w_object()
        
    def read_header(self):
        version = self.stream.next()
        if version != 0x1966: raise NotImplementedError
        headersize = self.stream.next()
        self.endofmemory = self.stream.next()   
        self.oldbaseaddress = self.stream.next()   
        self.specialobjectspointer = self.stream.next()   
        lasthash = self.stream.next()
        savedwindowssize = self.stream.next()
        fullscreenflag = self.stream.next()
        extravmmemory = self.stream.next()
        self.stream.skipbytes(headersize - (9 * 4))
        
    def read_body(self):
        self.chunks = {}
        self.stream.reset_count()
        while self.stream.count < self.endofmemory:
            chunk, pos = self.read_object()
            self.chunks[pos + self.oldbaseaddress] = chunk
        return self.chunks.values()
        
    def init_compactclassesarray(self):
        special = self.chunks[self.specialobjectspointer]   
        assert special.size > 24 #at least
        assert special.format == 2
        chunk = self.chunks[special.data[COMPACT_CLASSES_ARRAY]]
        assert len(chunk.data) == 31
        assert chunk.format == 2
        self.compactclasses = [self.chunks[pointer] for pointer in chunk.data]   
        
    def init_actualobjects(self):
        for chunk in self.chunks.itervalues():
            chunk.get_actual() # initialization            

    def read_object(self):
        kind = self.stream.peek() & 3 # 2 bits
        if kind == 0: # 00 bits 
            chunk, pos = self.read_3wordobjectheader()
        elif kind == 1: # 01 bits
            chunk, pos = self.read_2wordobjectheader()
        elif kind == 3: # 11 bits
            chunk, pos = self.read_1wordobjectheader()
        else: # 10 bits
            raise CorruptImageError("Unused block not allowed in image")
        size = chunk.size
        chunk.data = [self.stream.next() 
                     for _ in range(size - 1)] #size-1, excluding header   
        return chunk, pos     
        
    def read_1wordobjectheader(self):
        kind, size, format, classid, idhash = (
            splitbits(self.stream.next(), [2,6,4,5,12]))
        assert kind == 3
        return ImageChunk(size, format, classid, idhash), self.stream.count - 4

    def read_2wordobjectheader(self):
        assert splitbits(self.stream.peek(), [2])[0] == 1 #kind
        classid = self.stream.next() - 1 # remove headertype to get pointer
        kind, size, format, _, idhash = splitbits(self.stream.next(), [2,6,4,5,12])
        assert kind == 1
        return ImageChunk(size, format, classid, idhash), self.stream.count - 4

    def read_3wordobjectheader(self):
        kind, size = splitbits(self.stream.next(), [2,30]) 
        assert kind == 0
        assert splitbits(self.stream.peek(), [2])[0] == 0 #kind
        classid = self.stream.next() - 0 # remove headertype to get pointer
        kind, _, format, _, idhash = splitbits(self.stream.next(), [2,6,4,5,12])
        assert kind == 0
        return ImageChunk(size, format, classid, idhash), self.stream.count - 4

COMPACT_CLASSES_ARRAY = 28

# ____________________________________________________________

class GenericObject(object):
    """ Intermediate representation of squeak objects. To establish all
        pointers as object references, ImageReader creates instances of
        GenericObject from the image chunks, and uses them as starting
        point for the actual create of pypy.lang.smalltalk.model classes.
        """
    def __init__(self):
        self.owner = None
        
    def isinitialized(self):
        return self.owner is not None     
    
    def initialize_int(self, value, reader):
        self.owner = reader
        self.value = value
        self.size = -1
        self.w_object = fakeimage.small_int(value)
    
    def initialize(self, chunk, reader):
        self.owner = reader
        self.size = chunk.size
        self.hash12 = chunk.hash12 
        self.format = chunk.format
        self.init_class(chunk)
        self.init_data(chunk) # for pointers
        self.chunk = chunk # for bytes, words and compiledmethod
        self.w_object = None
        self.init_w_object()
        
    def init_class(self, chunk):    
        if chunk.iscompact():
            self.g_class = self.owner.compactclasses[chunk.classid].g_object
        else:
            self.g_class = self.owner.chunks[chunk.classid].g_object

    def init_data(self, chunk):    
        if not self.ispointers(): return
        self.pointers = []
        for pointer in chunk.data:
            g_object = self.decode_pointer(pointer)
            self.pointers.append(g_object)
            
    def decode_pointer(self, pointer):
        if (pointer & 1) == 1:
            return GenericObject().initialize_int(pointer >> 1, self.owner)
        else:
            return self.owner.chunks[pointer].g_object
            
    def isbytes(self):
        return 8 <= self.format <= 11
        
    def iswords(self):
        return self.format == 6
        
    def ispointers(self):
        return self.format < 5 #TODO, what about compiled methods?             

    def init_w_object(self):
        if self.w_object is None: 
            if self.format < 5: 
                self.w_object = objectmodel.instantiate(model.W_PointersObject)
            elif self.format == 5:
                raise CorruptImageError("Unknown format 5")
            elif self.format == 6:         
                self.w_object = objectmodel.instantiate(model.W_WordsObject)
            elif self.format == 7:
                raise CorruptImageError("Unknown format 7, no 64-bit support yet :-)")
            elif 8 <= self.format <= 11:
                self.w_object = objectmodel.instantiate(model.W_BytesObject)
            elif 12 <= self.format <= 15:
                self.w_object = objectmodel.instantiate(model.W_CompiledMethod)
            else:
                assert 0, "not reachable"                
        return self.w_object
        
    def fillin_w_object(self):
        # below we are using an RPython idiom to 'cast' self.w_object
        # and pass the casted reference to the fillin_* methods
        casted = self.w_object 
        case = type(casted)
        if case == model.W_PointersObject:
            self.fillin_poingersobject(casted)
        elif case == model.W_WordsObject:
            self.fillin_wordsobject(casted)
        elif case == model.W_BytesObject:
            self.fillin_bytesobject(casted)   
        elif case == model.W_CompiledMethod:
            self.fillin_compiledmethod(casted)

    def fillin_pointersobject(self, w_pointersobject):
        w_pointersobject.vars = [g_object.w_object for g_object in self.pointers]
        w_pointersobject.w_class = self.g_class.w_object
        
    def fillin_wordsobject(self, w_wordsobject):
        w_wordsobject.w_class = self.g_class.w_object

    def fillin_bytesobject(self, w_bytesobject):
        w_bytesobject.w_class = self.g_class.w_object
            
    def fillin_compiledmethod(self, w_compiledmethod):
        header = chunk.data[0]
        #(index 0)	9 bits:	main part of primitive number   (#primitive)
        #(index 9)	8 bits:	number of literals (#numLiterals)
        #(index 17)	1 bit:	whether a large frame size is needed (#frameSize)
        #(index 18)	6 bits:	number of temporary variables (#numTemps)
        #(index 24)	4 bits:	number of arguments to the method (#numArgs)
        #(index 28)	1 bit:	high-bit of primitive number (#primitive)
        #(index 29)	1 bit:	flag bit, ignored by the VM  (#flag)
        highbit, numargs, tempsize, islarge, literalsize, primitive = (
            splitbits(header, [1,4,6,1,8,9]))
        primitive = primitive + (highbit << 10)
        assert (1 + literalsize) < len(chunk.data)
        l = []
        for each in chunk.data[(1 + literalsize):]:
            l.append(int2str(each))
        l[-1] = l[-1][:-(self.format & 3)] # omit odd bytes
        bytes = "".join(l) 
        w_compiledmethod.__init__(
            w_class = self.g_class.w_object,
            size = self.literalsize,
            bytes = bytes,
            argsize = numargs,
            tempsize = tempsize,
            primitive = primitive)
             
    

class ImageChunk(object):
    def __init__(self, size, format, classid, hash12):
        self.size = size
        self.format = format
        self.classid = classid
        self.hash12 = hash12
        self.data = None
        self.g_object = GenericObject()
    
    def __eq__(self, other):
        "(for testing)"
        return (self.__class__ is other.__class__ and 
                self.format == other.format and
                self.classid == other.classid and
                self.hash12 == other.hash12 and
                self.data == other.data)

    def __ne__(self, other):
        "(for testing)"
        return not self == other
        
    def as_g_object(self, reader):
        if not self.g_object.isinitialized():
            self.g_object.initialize(self, reader)
        return self.g_object  
        
    def iscompact(self):
        return 0 < self.classid < 32                      
            
            
