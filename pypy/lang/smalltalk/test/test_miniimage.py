# ----- mini.image productline -------------------------------
#       NOT relying on order of methods
#       using setup_module(module) now
import py
from pypy.lang.smalltalk import squeakimage as sq
from pypy.lang.smalltalk import model as sqm
from pypy.lang.smalltalk import constants as sqc
from pypy.lang.smalltalk import interpreter as sqi

# lazy initialization of test data, ie ImageReader and Float class

def setup_module(module):
    global mini_image
    global reader
    global image
    mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')
    reader = open_miniimage()
    reader.initialize()
    image = sq.SqueakImage()
    image.from_reader(get_reader())
    
def open_miniimage():
    return sq.ImageReader(sq.Stream(mini_image.open()))

def get_reader():
    return reader
    
def get_image():
    return image
    
def get_float_class():
    image = get_image()
    return image.special(sqc.SO_FLOAT_CLASS)
     
# ------ tests ------------------------------------------
        
def test_miniimageexists():
    assert mini_image.check(dir=False)

def test_read_header():
    reader = open_miniimage()
    reader.read_header()
    assert reader.endofmemory == 0x93174
    assert reader.oldbaseaddress == 0x6649000
    assert reader.specialobjectspointer == 0x6668380

def test_read_all_header(): 
    reader = open_miniimage()
    reader.read_header()
    next = reader.stream.peek()
    assert next != 0 #expects object header, which must not be 0x00000000 
      
      
      
def test_number_of_objects():
    image = get_image()
    objects = image.objects
    assert len(objects) > 0
    assert 15000 < len(objects) < 16000 
    
def test_all_pointers_are_valid():
    reader = get_reader()
    for each in reader.chunks.itervalues():
        if each.format < 5: 
            for pointer in each.data:
                if (pointer & 1) != 1:
                    assert pointer in reader.chunks   
    
    
def test_there_are_31_compact_classes():
    reader = get_reader()
    assert len(reader.compactclasses) == 31
    
def test_invariant():
    image = get_image()
    for each in image.objects:
        each.invariant()
    
def test_float_class_size():
    w_float_class = get_float_class()
    assert w_float_class.size() == 9

def test_float_class_name():
    w_float_class = get_float_class()
    w_float_class_name = w_float_class.fetch(6)
    assert isinstance(w_float_class_name, sqm.W_BytesObject)
    assert w_float_class_name.bytes == list("Float")
    
def test_str_w_object():
    w_float_class = get_float_class()
    assert str(w_float_class) == "Float class"
    assert str(w_float_class.getclass()) == "a Metaclass" # yes, with article here.
    assert str(w_float_class.getclass().getclass()) == "Metaclass class"


def test_lookup_abs_in_integer(int=10):
    image = get_image()
    amethod = None

    w_smallint_class = image.special(sqc.SO_SMALLINTEGER_CLASS)

    interp = sqi.Interpreter()

    amethod = w_smallint_class.lookup("abs")
                                  # First literal of the abs method is
                                  # a real smalltalk int
    w_frame = amethod.createFrame(sqm.W_SmallInteger(int), [])
    interp.activeContext = w_frame

    print amethod

    while True:
        try:
            interp.step()
            print interp.activeContext.stack
        except sqi.ReturnFromTopLevel, e:
            return e.object

def test_lookup_neg_abs_in_integer():
    py.test.skip("TOFIX methodlookup 'negated' fails in mirror SmallInteger")
    test_lookup_abs_in_integer(-3)
