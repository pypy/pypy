import weakref
import UserDict


class MultiWeakKeyDictionary(UserDict.DictMixin):

    def __init__(self):
        self._bylength = {}

    def __getitem__(self, key):
        key = (len(key),) + key
        d = self._bylength
        for step in key:
            d = d[step]
        return d

    def __setitem__(self, key, value):
        key = (len(key),) + key
        d = self._bylength
        for step in key[:-1]:
            try:
                d = d[step]
            except KeyError:
                d[step] = newd = weakref.WeakKeyDictionary()
                d = newd
        d[key[-1]] = value

    def __delitem__(self, key):
        key = (len(key),) + key
        d = self._bylength
        for step in key[:-1]:
            d = d[step]
        del d[key[-1]]

    def keys(self):
        result = []
        def enumkeys(initialkey, d, result):
            if len(initialkey) == length:
                result.append(initialkey)
            else:
                for key, value in d.iteritems():
                    enumkeys(initialkey + (key,), value, result)
        for length, d in self._bylength.iteritems():
            enumkeys((), d, result)
        return result
