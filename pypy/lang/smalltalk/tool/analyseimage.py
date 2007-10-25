import autopath
import py
from pypy.lang.smalltalk import squeakimage 
from pypy.lang.smalltalk import constants 
from pypy.lang.smalltalk import model 
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk import interpreter 

mini_image = py.magic.autopath().dirpath().dirpath().join('tool/squeak3.9.image')

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

def testCompiledMethods():
    image = create_squeakimage()
    amethod = None

    w_smallint_class = image.special(constants.SO_SMALLINTEGER_CLASS)

    interp = interpreter.Interpreter()

    amethod = w_smallint_class.lookup("abs")
                                  # First literal of the abs method is
                                  # a real smalltalk int
    w_frame = amethod.create_frame(model.W_SmallInteger(3), [])
    interp.activeContext = w_frame

    print amethod

    while True:
        try:
            interp.step()
            print interp.activeContext.stack
        except interpreter.ReturnFromTopLevel, e:
            return e.object

def testDoesNotUnderstand():
    image = create_squeakimage()
    amethod = None

    w_doesnot = image.special(constants.SO_DOES_NOT_UNDERSTAND)
    w_object = objtable.wrap_int(3)
    w_message_class = image.special(constants.SO_MESSAGE_CLASS)
    s_message_class = w_message_class.as_class_get_shadow()

    #Build message argument
    w_message = s_message_class.new(1)
    w_message.store(constants.MESSAGE_SELECTOR_INDEX, objtable.wrap_string("zork"))
    w_aarray = classtable.w_Array.as_class_get_shadow().new(0)
    w_message.store(constants.MESSAGE_ARGUMENTS_INDEX,  w_aarray)
    if s_message_class.instsize() > constants.MESSAGE_LOOKUP_CLASS_INDEX:
        w_message.store(constants.MESSAGE_LOOKUP_CLASS_INDEX, w_object.getclass())

    s_class = w_object.shadow_of_my_class()
    w_method = s_class.lookup(w_doesnot)

    interp = interpreter.Interpreter()

                                  # First literal of the abs method is
                                  # a real smalltalk int
    w_frame = w_method.create_frame(w_object, [w_message])
    print "WFRAME: %r" % (w_frame,)
    interp.w_active_context = w_frame

    print w_method

    while True:
        try:
            print "Stackbefore: %r" % (interp.w_active_context.stack,)
            interp.step()
            print "Stackafter: %r" % (interp.w_active_context.stack,)
        except interpreter.ReturnFromTopLevel, e:
            return e.object


def testSelector():
    image = create_squeakimage()
    w_doesnot = image.special(constants.SO_DOES_NOT_UNDERSTAND)
    assert repr(w_doesnot.shadow_of_my_class()) == "<ClassShadow Symbol>"
    print w_doesnot.getclass().fetch(constants.CLASS_METHODDICT_INDEX).shadow_of_my_class().instance_kind
    print w_doesnot.getclass().fetch(constants.CLASS_METHODDICT_INDEX).shadow_of_my_class().instance_size
    print
    print w_doesnot.getclass().fetch(constants.CLASS_METHODDICT_INDEX)._vars
    print
    print w_doesnot.getclass().fetch(constants.CLASS_METHODDICT_INDEX)._vars[constants.METHODDICT_NAMES_INDEX:]
    print
    print w_doesnot.getclass().fetch(constants.CLASS_METHODDICT_INDEX)._vars[constants.METHODDICT_VALUES_INDEX]._vars

def test_do():
    #testSelector()
    printStringsInImage()
    #testDoesNotUnderstand()

if __name__ == '__main__':
    test_do()
