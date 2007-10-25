import autopath
import py
from pypy.lang.smalltalk import squeakimage 
from pypy.lang.smalltalk import constants 
from pypy.lang.smalltalk import model 
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import interpreter 

mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')

def get_miniimage():
    return squeakimage.ImageReader(squeakimage.Stream(mini_image.open()))

def create_squeakimage():
    example = get_miniimage()
    example.initialize()
    
    image = squeakimage.SqueakImage()
    image.from_reader(example)
    return image

def printStringsInImage():
    image = create_squeakimage()
    for each in image.objects:
        if isinstance(each,model.W_BytesObject):
          print each.shadow_of_my_class()
          print each.as_string()

def tinyBenchmarks():
    image = create_squeakimage()
    interp = interpreter.Interpreter()

    w_object = model.W_SmallInteger(0)

    # Should get this from w_object
    w_smallint_class = image.special(constants.SO_SMALLINTEGER_CLASS)
    s_class = w_object.shadow_of_my_class()
    w_method = s_class.lookup("tinyBenchmarks")

    assert w_method
    w_frame = w_method.create_frame(w_object, [])
    interp.w_active_context = w_frame

    print w_method
    print "Going to execute %d toplevel bytecodes" % (len(w_method.bytes),)
    counter = 0

    while True:
        try:
            interp.step()
            print interp.w_active_context.stack
            if interp.w_active_context == w_frame:
                counter += 1
                print "Executing toplevel bytecode nr: %d of %d" % (counter, len(w_method.bytes))
        except interpreter.ReturnFromTopLevel, e:
            assert e.object.value == abs(int)
            return



def test_do():
    #testSelector()
    #printStringsInImage()
    #testDoesNotUnderstand()
    tinyBenchmarks()

if __name__ == '__main__':
    test_do()
