def getitem_string_slice(str, sliceob):
     r = []
     for i in xrange(*sliceob.indices(len(str))):
         r.append(str[i])
     return ''.join(r)

