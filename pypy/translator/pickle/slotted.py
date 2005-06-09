class Missing:
    pass

from copy_reg import _slotnames

# we don't turn _slotnames into a class method, because it
# is also needed externally.

class Slotted(object):
    __slots__ = []
    def __getstate__(self):
        names = _slotnames(self.__class__)
        return tuple([getattr(self, name, Missing) for name in names])
    def __setstate__(self, args):
        names = _slotnames(self.__class__)
        [setattr(self, name, value) for name, value in zip(names, args)
         if value is not Missing]

# support classes which cannot inherit from Slotted

__getstate__ = Slotted.__getstate__.im_func
__setstate__ = Slotted.__setstate__.im_func
