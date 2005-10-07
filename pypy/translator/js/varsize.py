from pypy.rpython.rstr import STR

def write_constructor(db, codewriter, ref, constructor_decl, ARRAY, 
                      indices_to_array=()): 

    codewriter.comment('TODO: ' + constructor_decl)
    return

    #varsized arrays and structs look like this: 
    #Array: {int length , elemtype*}
    #Struct: {...., Array}

    codewriter.openfunc(constructor_decl, None, [])    

    # Need room for NUL terminator
    if ARRAY is STR.chars:
        codewriter.binaryop("add", "%actuallen", 'word', "%len", 1)
    else:
        codewriter.cast("%actuallen", 'word', "%len", 'word')

    elemindices = list(indices_to_array) + [("uint", 1), ('word', "%actuallen")]
    codewriter.getelementptr("%size", ref + "*", "null", *elemindices) 
    codewriter.cast("%usize", "word*", "%size", 'uword')
    codewriter.malloc("%ptr", "sbyte", "%usize", atomic=ARRAY._is_atomic())
    codewriter.cast("%result", "sbyte*", "%ptr", ref + "*")

    indices_to_arraylength = tuple(indices_to_array) + (("uint", 0),)
    # the following accesses the length field of the array 
    codewriter.getelementptr("%arraylength", ref + "*", 
                             "%result", 
                             *indices_to_arraylength)
    codewriter.store('word', "%len", "%arraylength")

    codewriter.ret(ref + "*", "%result")
    codewriter.closefunc()
