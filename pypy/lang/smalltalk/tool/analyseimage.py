import autopath
import py
from pypy.lang.smalltalk import squeakimage 
from pypy.lang.smalltalk import constants 
from pypy.lang.smalltalk import model 
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
          print each.bytes

def testCompiledMethods():
    image = create_squeakimage()
    amethod = None

    w_smallint_class = image.special(constants.SO_SMALLINTEGER_CLASS)

    interp = interpreter.Interpreter()

    amethod = w_smallint_class.lookup("abs")
                                  # First literal of the abs method is
                                  # a real smalltalk int
    w_frame = amethod.createFrame(model.W_SmallInteger(3), [])
    interp.activeContext = w_frame

    print amethod

    while True:
        try:
            interp.step()
            print interp.activeContext.stack
        except interpreter.ReturnFromTopLevel, e:
            return e.object

def testSelector():
    image = create_squeakimage()
    w_doesnot = image.special(constants.SO_DOES_NOT_UNDERSTAND)
    assert repr(w_doesnot.shadow_of_my_class()) == "<ClassShadow Symbol>"
    print w_doesnot.getclass().fetch(constants.CLASS_METHODDICT_INDEX)._vars

def test_do():
    testSelector()
    #printStringsInImage()

if __name__ == '__main__':
    test_do()
