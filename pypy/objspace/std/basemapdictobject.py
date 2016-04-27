# this file contains the shared objspace method implementation that are
# imported into W_Root. All W_Root objects have these methods, but most of them
# really only make sense for user-defined subclasses. It is however important
# that they are shared by all subclasses of W_Root.


DICT = 0
SPECIAL = 1
INVALID = 2
SLOTS_STARTING_FROM = 3


class RootObjectMapdictMixin(object):
    # hooks that the mapdict implementations needs.
    # these will be overridden in user-defined subclasses

    def _get_mapdict_map(self):
        # if this method returns None, there is no map, thus the class is no
        # user-defined subclass
        return None

    def _set_mapdict_map(self, map):
        raise NotImplementedError

    def _mapdict_read_storage(self, index):
        raise NotImplementedError

    def _mapdict_write_storage(self, index, value):
        raise NotImplementedError

    def _mapdict_storage_length(self):
        raise NotImplementedError

    def _set_mapdict_storage_and_map(self, storage, map):
        raise NotImplementedError

    def _mapdict_init_empty(self, map):
        raise NotImplementedError

    # ____________________________________________________________
    # objspace interface


    # class handling

    # getclass is not done here, it makes sense to really specialize this per class

    def setclass(self, space, w_cls):
        from pypy.interpreter.error import OperationError
        map = self._get_mapdict_map()
        if map is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("__class__ assignment: only for heap types"))
        new_obj = map.set_terminator(self, w_cls.terminator)
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)


    # dict handling

    # getdictvalue and setdictvalue are not done here, for performance reasons

    def deldictvalue(self, space, attrname):
        from pypy.interpreter.error import OperationError
        map = self._get_mapdict_map()
        if map is None:
            # check whether it has a dict and use that
            w_dict = self.getdict(space)
            if w_dict is not None:
                try:
                    space.delitem(w_dict, space.wrap(attrname))
                    return True
                except OperationError, ex:
                    if not ex.match(space, space.w_KeyError):
                        raise
            return False
        new_obj = map.delete(self, attrname, DICT)
        if new_obj is None:
            return False
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)
        return True

    def getdict(self, space):
        from pypy.objspace.std.mapdict import MapDictStrategy
        from pypy.objspace.std.dictmultiobject import  W_DictMultiObject
        from pypy.objspace.std.dictmultiobject import  W_DictObject
        map = self._get_mapdict_map()
        if map is None:
            return None
        terminator = map.terminator
        if not terminator.has_dict:
            return None
        w_dict = map.read(self, "dict", SPECIAL)
        if w_dict is not None:
            assert isinstance(w_dict, W_DictMultiObject)
            return w_dict

        strategy = space.fromcache(MapDictStrategy)
        storage = strategy.erase(self)
        w_dict = W_DictObject(space, strategy, storage)
        flag = map.write(self, "dict", SPECIAL, w_dict)
        assert flag
        return w_dict

    def setdict(self, space, w_dict):
        from pypy.interpreter.error import OperationError, oefmt
        from pypy.objspace.std.mapdict import MapDictStrategy
        from pypy.objspace.std.dictmultiobject import  W_DictMultiObject
        map = self._get_mapdict_map()
        if map is None or not map.terminator.has_dict:
            raise oefmt(space.w_TypeError,
                         "attribute '__dict__' of %T objects is not writable",
                         self)
        terminator = map.terminator
        if not space.isinstance_w(w_dict, space.w_dict):
            raise OperationError(space.w_TypeError,
                    space.wrap("setting dictionary to a non-dict"))
        assert isinstance(w_dict, W_DictMultiObject)
        w_olddict = self.getdict(space)
        assert isinstance(w_olddict, W_DictMultiObject)
        # The old dict has got 'self' as dstorage, but we are about to
        # change self's ("dict", SPECIAL) attribute to point to the
        # new dict.  If the old dict was using the MapDictStrategy, we
        # have to force it now: otherwise it would remain an empty
        # shell that continues to delegate to 'self'.
        if type(w_olddict.get_strategy()) is MapDictStrategy:
            w_olddict.get_strategy().switch_to_object_strategy(w_olddict)
        flag = self._get_mapdict_map().write(self, "dict", SPECIAL, w_dict)
        assert flag


    # slots

    def getslotvalue(self, slotindex):
        map = self._get_mapdict_map()
        if map is None:
            # not a user-defined subclass
            raise NotImplementedError
        index = SLOTS_STARTING_FROM + slotindex
        return map.read(self, "slot", index)

    def setslotvalue(self, slotindex, w_value):
        map = self._get_mapdict_map()
        if map is None:
            # not a user-defined subclass
            raise NotImplementedError
        index = SLOTS_STARTING_FROM + slotindex
        map.write(self, "slot", index, w_value)

    def delslotvalue(self, slotindex):
        map = self._get_mapdict_map()
        if map is None:
            # not a user-defined subclass
            raise NotImplementedError
        index = SLOTS_STARTING_FROM + slotindex
        new_obj = map.delete(self, "slot", index)
        if new_obj is None:
            return False
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)
        return True


    # weakrefs

    def getweakref(self):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        map = self._get_mapdict_map()
        if map is None:
            return None # not a user-defined subclass
        lifeline = map.read(self, "weakref", SPECIAL)
        if lifeline is None:
            return None
        assert isinstance(lifeline, WeakrefLifeline)
        return lifeline
    getweakref._cannot_really_call_random_things_ = True

    def setweakref(self, space, weakreflifeline):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        map = self._get_mapdict_map()
        if map is None:
            # not a user-defined subclass
            raise oefmt(space.w_TypeError,
                        "cannot create weak reference to '%T' object", self)
        assert isinstance(weakreflifeline, WeakrefLifeline)
        map.write(self, "weakref", SPECIAL, weakreflifeline)
    setweakref._cannot_really_call_random_things_ = True

    def delweakref(self):
        map = self._get_mapdict_map()
        if map is None:
            return
        map.write(self, "weakref", SPECIAL, None)
    delweakref._cannot_really_call_random_things_ = True
