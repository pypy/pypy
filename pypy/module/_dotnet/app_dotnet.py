# NOT_RPYTHON

class ArrayList(object):
    __cliname__ = 'System.Collections.ArrayList'
    ATTRS = ['Add']

    def __init__(self):
        import _dotnet
        self.obj = _dotnet._CliObject_internal(self.__cliname__)

    def Add(self, x):
        return self.obj.call_method('Add', [x])

    def get_Item(self, idx):
        return self.obj.call_method('get_Item', [idx])
