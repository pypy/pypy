from array import array as _array

class array(object):
    def __init__(self, typecode, initializer=None):
        self._array = _array(typecode)
        if initializer is not None:
            self.extend(initializer)


    def append(self ,x):
        self._array.append(x)
    def __getitem__(self, idx):
        return self._array[idx]
    def __setitem__(self, idx, val):
        self._array[idx]=val
    def __len__(self):
        return len(self._array)

    
    def extend(self, iterable):
        for i in iterable: self.append(i)
    

    
