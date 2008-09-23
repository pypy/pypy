import autopath
import py
from pypy.lang.smalltalk import squeakimage 
from pypy.lang.smalltalk import constants 
from pypy.lang.smalltalk import model 
from pypy.lang.smalltalk import interpreter 
import sys

mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')

def get_miniimage(space):
    return squeakimage.ImageReader(space, squeakimage.Stream(mini_image.open()))

def create_squeakimage(space):
    example = get_miniimage(space)
    example.initialize()
    
    image = squeakimage.SqueakImage()
    image.from_reader(space, example)
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
    #w_method = s_class.lookup("benchFib")
    w_method = s_class.lookup("tinyBenchmarks")

    assert w_method
    w_frame = w_method.create_frame(w_object, [])
    interp.store_w_active_context(w_frame)

    from pypy.lang.smalltalk.interpreter import BYTECODE_TABLE
    while True:
        try:
            interp.step()
        except interpreter.ReturnFromTopLevel, e:
            print e.object
            return

def test_do():
    #testSelector()
    #printStringsInImage()
    #testDoesNotUnderstand()
    tinyBenchmarks()

if __name__ == '__main__':
    test_do()
