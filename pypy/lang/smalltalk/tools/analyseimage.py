import autopath
import py
from pypy.lang.smalltalk import squeakimage as sq
from pypy.lang.smalltalk import model as sqm
from pypy.lang.smalltalk import interpreter as sqi

mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')

def test_miniimageexists():
    assert mini_image.check(dir=False)

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
          print repr(''.join(each.bytes))

def testCompiledMethods():
    image = create_squeakimage()
    amethod = None
    skip = 0

    for each in image.objects:
        if isinstance(each,sqm.W_CompiledMethod):
            if (amethod == None and
                each.argsize == 0 and
                each.tempsize == 0 and
                each.primitive == 1 and skip >= 0):
                amethod = each
            else:
                skip += 1
            #print "%d %d %d" % (each.argsize, each.tempsize, each.primitive)
    
                        # receiver, arguments
    w_frame = amethod.createFrame("receiver", [])
    interp = sqi.Interpreter()
    interp.activeContext = w_frame
    interp.interpret()

def test_do():
    testCompiledMethods()

if __name__ == '__main__':
    test_do()
