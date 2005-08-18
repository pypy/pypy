from pypy.rpython.rstr import STR

# example for an array constructor in concrete llvm code: 
# (thanks to chris lattner) 
""" this function generates a LLVM function like the following:
%array = type { int, [0 x double] }
%array *%NewArray(int %len) {
   ;; Get the offset of the 'len' element of the array from the null
   ;; pointer.
   %size = getelementptr %array* null, int 0, uint 1, %int %len
   %usize = cast double* %size to uint
   %ptr = malloc sbyte, uint %usize
   %result = cast sbyte* %ptr to %array*
   %arraylength = getelementptr %array* %result, int 0, uint 0
   store int %len, int* %arraylength 
   ret %array* %result
}"""

def write_constructor(db, codewriter, ref, constructor_decl, ARRAY, 
                      indices_to_array=(), atomicmalloc=False): 
    
    #varsized arrays and structs look like this: 
    #Array: {int length , elemtype*}
    #Struct: {...., Array}

    # the following indices access the last element in the array
    elemtype = db.repr_type(ARRAY.OF)
    lentype = db.get_machine_word()

    codewriter.openfunc(constructor_decl)    

    # Need room for NUL terminator
    if ARRAY is STR.chars:
        codewriter.binaryop("add", "%actuallen", lentype, "%len", 1)
    else:
        codewriter.cast("%actuallen", lentype, "%len", lentype)

    elemindices = list(indices_to_array) + [("uint", 1), (lentype, "%actuallen")]
    codewriter.getelementptr("%size", ref + "*", "null", *elemindices) 
    codewriter.cast("%usize", elemtype + "*", "%size", "uint")
    codewriter.malloc("%ptr", "sbyte", "%usize", atomic=atomicmalloc)
    codewriter.cast("%result", "sbyte*", "%ptr", ref + "*")

    if ARRAY is STR.chars:
        codewriter.call('%memset_result', 'sbyte*', '%memset', ['%ptr', '0', '%usize',], ['sbyte*', 'int', 'uint'], cconv='ccc')
 
    indices_to_arraylength = tuple(indices_to_array) + (("uint", 0),)
    # the following accesses the length field of the array 
    codewriter.getelementptr("%arraylength", ref + "*", 
                             "%result", 
                             *indices_to_arraylength)
    codewriter.store(lentype, "%len", "%arraylength")
    
    #if ARRAY is STR.chars: #(temp. disabled because we are moving memset from gc_malloc to here)
    #    # NUL the last element 
    #    #lastelemindices = list(indices_to_array) + [("uint", 1), (lentype, "%len")]
    #    #codewriter.getelementptr("%terminator",
    #    #                         ref + "*",
    #    #                         "%result", 
    #    #                         *lastelemindices)
    #    #codewriter.store(elemtype, 0, "%terminator")
    
    codewriter.ret(ref + "*", "%result")
    codewriter.closefunc()

