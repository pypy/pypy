from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.function import Method
from pypy.interpreter.gateway import interp2app, descr_function_get
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, descr_get_dict, descr_set_dict, descr_del_dict)


class W_KwdMark(W_Root):
    """A private, identity-compared marker used to separate positional
    from keyword arguments inside a cache key tuple.  One is allocated
    per wrapper instance, mirroring CPython's `kwd_mark = (object(),)`.
    """


W_KwdMark.typedef = TypeDef("_functools._kwd_mark")


class W_LRUCacheWrapper(W_Root):
    def __init__(self, space, w_user_function, maxsize, typed,
                 w_cache_info_type):
        self.space = space
        self.w_user_function = w_user_function
        self.maxsize = maxsize          # -1 means unbounded
        self.typed = typed
        self.w_cache_info_type = w_cache_info_type
        self.w_cache = space.newdict()
        self.w_kwd_mark = W_KwdMark()
        self.hits = 0
        self.misses = 0
        self.w_dict = None

    def getdict(self, space):
        if self.w_dict is None:
            self.w_dict = space.newdict(instance=True)
        return self.w_dict

    def setdict(self, space, w_dict):
        self.w_dict = w_dict

    def _make_key(self, space, args_w, keyword_names_w, keywords_w):
        # Match CPython's fast path exactly: a single positional int or
        # str argument, untyped, with no keywords, is used bare as the
        # key instead of being wrapped in a tuple.  This isn't just a
        # micro-optimization: skipping it would make e.g. an untyped
        # cache treat 1 and 1.0 as the same key (dict equality doesn't
        # care that one came via the fast path and one didn't), which
        # diverges from CPython's observable behaviour.
        if not self.typed and keyword_names_w is None:
            if len(args_w) == 1 and self._is_fast_arg(space, args_w[0]):
                return args_w[0]
            return space.newtuple(args_w)
        key_w = args_w[:]
        if keyword_names_w is not None:
            key_w.append(self.w_kwd_mark)
            for i in range(len(keyword_names_w)):
                key_w.append(keyword_names_w[i])
                key_w.append(keywords_w[i])
        if self.typed:
            for w_arg in args_w:
                key_w.append(space.type(w_arg))
            if keyword_names_w is not None:
                for w_value in keywords_w:
                    key_w.append(space.type(w_value))
        return space.newtuple(key_w[:])

    def _is_fast_arg(self, space, w_arg):
        w_type = space.type(w_arg)
        return (space.is_w(w_type, space.w_int) or
                space.is_w(w_type, space.w_text))

    def descr_call(self, space, __args__):
        if self.maxsize == 0:
            self.misses += 1
            return space.call_args(self.w_user_function, __args__)

        args_w = __args__.arguments_w
        keyword_names_w = __args__.keyword_names_w
        keywords_w = __args__.keywords_w
        w_key = self._make_key(space, args_w, keyword_names_w, keywords_w)

        w_result = self.w_cache.getitem(w_key)
        if w_result is not None:
            if self.maxsize > 0:
                self.w_cache.nondescr_move_to_end(space, w_key, True)
            self.hits += 1
            return w_result
        self.misses += 1

        w_result = space.call_args(self.w_user_function, __args__)

        # user_function() may have re-entered this same wrapper (directly
        # or via another thread) and already cached this exact key; if so,
        # leave the existing entry (and its position) alone.
        if self.w_cache.getitem(w_key) is None:
            if self.maxsize > 0 and self.w_cache.length() >= self.maxsize:
                self.w_cache.nondescr_popitem_first(space)
            self.w_cache.setitem(w_key, w_result)
        return w_result

    def descr_cache_info(self, space):
        w_maxsize = space.w_None if self.maxsize < 0 \
            else space.newint(self.maxsize)
        return space.call_function(
            self.w_cache_info_type,
            space.newint(self.hits),
            space.newint(self.misses),
            w_maxsize,
            space.newint(self.w_cache.length()))

    def descr_cache_clear(self, space):
        self.w_cache = space.newdict()
        self.hits = 0
        self.misses = 0

    def descr_copy(self, space):
        return self

    def descr_deepcopy(self, space, w_memo):
        return self


def lru_cache_wrapper(space, w_user_function, w_maxsize, w_typed,
                       w_cache_info_type):
    if space.is_none(w_maxsize):
        maxsize = -1
    else:
        maxsize = space.int_w(w_maxsize)
        if maxsize < 0:
            maxsize = 0
    typed = space.is_true(w_typed)
    return W_LRUCacheWrapper(space, w_user_function, maxsize, typed,
                              w_cache_info_type)


W_LRUCacheWrapper.typedef = TypeDef(
    "functools._lru_cache_wrapper",
    __call__=interp2app(W_LRUCacheWrapper.descr_call),
    __get__=interp2app(descr_function_get),
    __copy__=interp2app(W_LRUCacheWrapper.descr_copy),
    __deepcopy__=interp2app(W_LRUCacheWrapper.descr_deepcopy),
    __dict__=GetSetProperty(descr_get_dict, descr_set_dict, descr_del_dict,
                             cls=W_LRUCacheWrapper),
    cache_info=interp2app(W_LRUCacheWrapper.descr_cache_info),
    cache_clear=interp2app(W_LRUCacheWrapper.descr_cache_clear),
)
