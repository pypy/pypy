def getitem_string_slice(str, sliceob):
     r = []
     for i in range(*sliceob.indices(len(str))):
         r.append(str[i])
     return ''.join(r)

