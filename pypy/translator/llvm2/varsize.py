
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

def write_constructor(codewriter, ref, constructor_decl, elemtype, 
                      indices_to_array=(), atomicmalloc=False): 
    #varsized arrays and structs look like this: 
    #Array: {int length , elemtype*}
    #Struct: {...., Array}

    # the following indices access the last element in the array 
    elemindices = list(indices_to_array) + [("uint", 1), ("int", "%len")]
   
    codewriter.openfunc(constructor_decl)
    codewriter.getelementptr("%size", ref + "*", "null", *elemindices) 
    codewriter.cast("%usize", elemtype + "*", "%size", "uint")
    codewriter.malloc("%ptr", "sbyte", "%usize", atomic=atomicmalloc)
    codewriter.cast("%result", "sbyte*", "%ptr", ref + "*")
 
    indices_to_array = tuple(indices_to_array) + (("uint", 0),)
    # the following accesses the length field of the array 
    codewriter.getelementptr("%arraylength", ref + "*", 
                             "%result", 
                             *indices_to_array)
    codewriter.store("int", "%len", "%arraylength")
    codewriter.ret(ref + "*", "%result")
    codewriter.closefunc()

