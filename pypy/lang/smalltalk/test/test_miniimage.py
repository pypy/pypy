# ----- mini.image productline -------------------------------
#       NOT relying on order of methods
#       one big method to rule them all
import py
from pypy.lang.smalltalk import squeakimage as sq


mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')

def test_miniimageexists():
    assert mini_image.check(dir=False)

def get_miniimage():
    return sq.ImageReader(sq.Stream(mini_image.open()))

def test_read_header():
    example = get_miniimage()
    example.read_header()
    assert example.endofmemory == 0x93174
    assert example.oldbaseaddress == 0x6649000
    assert example.specialobjectspointer == 0x6668380

def test_read_all_header(): 
    example = get_miniimage()
    example.read_header()
    next = example.stream.peek()
    assert next != 0 #expects object header, which must not be 0x00000000 
      
def test_readimage_productline():
    example = get_miniimage()
    example.read_header()
    objects = example.read_body()
    assert len(objects) > 0
    assert 15000 < len(objects) < 16000 
    
    # at end of file
    # py.test.raises(IndexError, lambda: example.stream.next())
    
    # all pointers are valid
    for each in example.chunks.itervalues():
        if each.format < 5: 
            for pointer in each.data:
                if (pointer & 1) != 1:
                    assert pointer in example.chunks   
    
    # there are 31 compact classes
    example.init_compactclassesarray()
    assert len(example.compactclasses) == 31
    
    example.init_g_objects()
    
    example.init_w_objects() 

    example.fillin_w_objects() 
    
    image = sq.SqueakImage()
    
    image.from_reader(example)    
    
    for each in image.objects:
        each.invariant()
    
    w_float_class = image.special(sq.FLOAT_CLASS)
    
    #assert w_float_class.size() == 10
          
