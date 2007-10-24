import autopath
import py
from pypy.lang.smalltalk import squeakimage as sq
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

def printReadableBytecode(bytecode):
    print "\n\nBytecode:\n---------------------"
    print "\n".join([sqi.BYTECODE_TABLE[ord(i)].__name__ for i in bytecode])
    print "---------------------\n"

def getMethodFromClass(w_class,methodname):
    w_methoddict = w_class.fetch(1)
    for var in w_methoddict.vars:
        if isinstance(var,sqm.W_BytesObject):
            if str(var) == repr(methodname):
                return w_methoddict.vars[1].vars[w_methoddict.vars.index(var)-2]

def testCompiledMethods():
    image = create_squeakimage()
    amethod = None

    w_float_class = image.special(sq.FLOAT_CLASS)

    interp = sqi.Interpreter()
    anObject = sqm.W_Float(1.5)
    amethod = getMethodFromClass(w_float_class,"abs")
                                # receiver, arguments
    w_frame = amethod.createFrame(anObject, [])
    interp.activeContext = w_frame

    print amethod

    while True:
        try:
            interp.step()
            print interp.activeContext.stack
        except sqi.ReturnFromTopLevel, e:
            return e.object

# apply to Xth method
SKIPMETHODS=42 #X

def test_do():
    testCompiledMethods()
    #printStringsInImage()

if __name__ == '__main__':
    test_do()
