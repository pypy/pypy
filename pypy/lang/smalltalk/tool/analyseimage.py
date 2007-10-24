import autopath
import py
from pypy.lang.smalltalk import squeakimage as sq
from pypy.lang.smalltalk import constants as sqc
from pypy.lang.smalltalk import model as sqm
from pypy.lang.smalltalk import interpreter as sqi

mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')

def get_miniimage():
    return sq.ImageReader(sq.Stream(mini_image.open()))

def create_squeakimage():
    example = get_miniimage()
    example.initialize()
    
    image = sq.SqueakImage()
    image.from_reader(example)
    return image

def printStringsInImage():
    image = create_squeakimage()
    for each in image.objects:
        if isinstance(each,sqm.W_BytesObject):
          print each.bytes

def testCompiledMethods():
    image = create_squeakimage()
    amethod = None

    w_smallint_class = image.special(sqc.SO_SMALLINTEGER_CLASS)

    interp = sqi.Interpreter()

    amethod = w_smallint_class.lookup("abs")
                                  # First literal of the abs method is
                                  # a real smalltalk int
    w_frame = amethod.createFrame(amethod.literals[0], [])
    interp.activeContext = w_frame

    print amethod

    while True:
        try:
            interp.step()
            print interp.activeContext.stack
        except sqi.ReturnFromTopLevel, e:
            return e.object

def test_do():
    testCompiledMethods()
    #printStringsInImage()

if __name__ == '__main__':
    test_do()
