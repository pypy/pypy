import py

class Directory(py.test.collect.Directory): 
    def __iter__(self): 
        return iter([])
