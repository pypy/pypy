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
            if (each.argsize == 0 and amethod == None and
                each.tempsize == 0 and
                each.primitive == 1):
                
                if len(each.bytes) == 0:
                    pass
                else:
                    if skip >= SKIPMETHODS:
                        amethod = each
                    else:
                        skip += 1
            #print "%d %d %d" % (each.argsize, each.tempsize, each.primitive)
    
                        # receiver, arguments
    interp = sqi.Interpreter()

    anObject = sqm.W_PointersObject(sqm.W_Class(None,None,100),0)
    for i in range(0,99):
        anObject.store(i, interp.ONE)

    w_frame = amethod.createFrame(anObject, [])
    interp.activeContext = w_frame
    #w_frame.push(interp.TRUE)
    w_frame.push(interp.ONE)
    w_frame.push(interp.TWO)

    while True:
        try:
            interp.step()
            print interp.activeContext.stack
        except sqi.ReturnFromTopLevel, e:
            return e.object

# apply to Xth method
SKIPMETHODS=3 #X

def test_do():
    testCompiledMethods()

if __name__ == '__main__':
    test_do()
