from pypy.rpython.rstr import STR

def write_constructor(db, codewriter, ref, constructor_decl, ARRAY, 
                      indices_to_array=(), atomic=False):

    #varsized arrays and structs look like this: 
    #Array: {int length , elemtype*}
    #Struct: {...., Array}

    # the following indices access the last element in the array
    elemtype = db.repr_type(ARRAY.OF)
    word = lentype = db.get_machine_word()
    uword = db.get_machine_uword()

    codewriter.openfunc(constructor_decl)    

    # Need room for NUL terminator
    if ARRAY is STR.chars:
        codewriter.binaryop("add", "%actuallen", lentype, "%len", 1)
    else:
        codewriter.cast("%actuallen", lentype, "%len", lentype)

    elemindices = list(indices_to_array) + [("uint", 1), (lentype, "%actuallen")]
    codewriter.getelementptr("%size", ref + "*", "null", *elemindices) 
    codewriter.cast("%usize", elemtype + "*", "%size", uword)
    codewriter.malloc("%ptr", "sbyte", "%usize", atomic=atomic)
    codewriter.cast("%result", "sbyte*", "%ptr", ref + "*")

    indices_to_arraylength = tuple(indices_to_array) + (("uint", 0),)
    # the following accesses the length field of the array 
    codewriter.getelementptr("%arraylength", ref + "*", 
                             "%result", 
                             *indices_to_arraylength)
    codewriter.store(lentype, "%len", "%arraylength")

    codewriter.ret(ref + "*", "%result")
    codewriter.closefunc()

