try:
    import ctypes as _
except ImportError:
    CPyObjSpace = None
else:
    from objspace import CPyObjSpace
    
Space = CPyObjSpace
