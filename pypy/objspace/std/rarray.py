#The goal is to use a primitive array, which we 
#later implement directly in c. We want to get 
#rid of cpython dependencies. We wrap the original
#array module to see, which methods do we need

import array

def CharArrayFromStr(newstr):
    b = CharArray()
    b.setvalue(newstr)
    return b

def CharArraySize(size):
    b = CharArray()
    b.setsize(size)
    return b

class CharArray:
    def __init__(self):
        self._value = None

    def setvalue(self, value):
        self._value = array.array('c', value)
        self.len = len(value)

    def __repr__(self):
        return self._value.tostring()


    def hash(self):
        #of cource, it doesn't make much sense hier, but the hash function
        #also has to be implemented in c
        return hash(self.value())

    def value(self):
        """returns back the string"""
        return self._value.tostring()

    def getsubstring(self, startat, length):
        """returns back the substring"""
        return self._value[startat:startat+length].tostring()

    def charat(self, idx):
        """returns char at the index"""
        return self._value[idx]

    def setsize(self, size):
        """set size of the buffer to size"""
        self._value = array.array('c', ' ' * size)
        self.len = size

    def append(self, newstr):
        """append the new string to the buffer"""
        newstr = self._value.tostring() + newstr
        self._value = array.array('c', newstr)
        self.len = len(newstr)

    def setsubstring(self, idx, substr):
        """set the buffer to substr at the idx"""
        #it's a hack, but this is not very important, while
        #we are going to reimplement this stuff in c
        list = self._value.tolist()
        for char in substr:
            list[idx] = char
            idx = idx + 1
        self._value = array.array('c', "".join(list))

