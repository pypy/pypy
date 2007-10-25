import autopath
import py
from pypy.lang.smalltalk import squeakimage 
from pypy.lang.smalltalk import constants 
from pypy.lang.smalltalk import model 
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import interpreter 
import sys

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

    from pypy.lang.smalltalk.interpreter import BYTECODE_TABLE
    while True:
        try:
            counter += 1
            #if interp.w_active_context == w_frame:
               # print "Executing toplevel bytecode nr: %d of %d" % (counter, len(w_method.bytes))
            interp.step()
            #if hasattr(interp.w_active_context,"currentBytecode"):
            #    print "Executing bytecode: %s" % (BYTECODE_TABLE[interp.w_active_context.currentBytecode].__name__,)
            #else:
            #    print "Jump to new stackframe"
            # print interp.w_active_context.stack
            if counter == 100000:
                counter = 0
                sys.stderr.write("#")
        except interpreter.ReturnFromTopLevel, e:
            assert e.object.value == abs(int)
            return
        except:
            if hasattr(interp.w_active_context,"currentBytecode"):
                cb = interp.w_active_context.currentBytecode
                print "Failing bytecode: %s %d" % (BYTECODE_TABLE[cb].__name__,cb)
            raise



def test_do():
    #testSelector()
    #printStringsInImage()
    #testDoesNotUnderstand()
    tinyBenchmarks()

if __name__ == '__main__':
    test_do()
