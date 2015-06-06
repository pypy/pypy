from weakref import ref


class GcWeakrefs(object):
    def __init__(self, ffi):
        self.ffi = ffi
        self.data = []
        self.freelist = None

    def build(self, cdata, destructor):
        # make a new cdata of the same type as the original one
        new_cdata = self.ffi.cast(self.ffi._backend.typeof(cdata), cdata)
        #
        def remove(key):
            assert self.data[index] is key
            self.data[index] = self.freelist
            self.freelist = index
            destructor(cdata)
        #
        key = ref(new_cdata, remove)
        index = self.freelist
        if index is None:
            index = len(self.data)
            self.data.append(key)
        else:
            self.freelist = self.data[index]
            self.data[index] = key
        return new_cdata
