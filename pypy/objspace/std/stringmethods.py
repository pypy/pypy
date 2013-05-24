class StringMethods(object):
    _mixin_ = True

    def _new(self, value):
        raise NotImplementedError

    def _len(self):
        raise NotImplementedError

    def _val(self):
        raise NotImplementedError

    def descr_eq(self, space):
        pass

    def descr_ne(self, space):
        pass

    def descr_lt(self, space):
        pass

    def descr_le(self, space):
        pass

    def descr_gt(self, space):
        pass

    def descr_ge(self, space):
        pass

    def descr_len(self, space):
        pass

    def descr_iter(self, space):
        pass

    def descr_contains(self, space):
        pass

    def descr_add(self, space):
        pass

    def descr_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                return NotImplemented
            raise
        if times <= 0:
            return self.EMPTY
        if self._len() == 1:
            return self._new(self._val()[0] * times)
        return self._new(self._val() * times)

    def descr_getitem(self, space):
        pass

    def descr_capitalize(self, space):
        pass

    def descr_center(self, space):
        pass

    def descr_count(self, space):
        pass

    def descr_decode(self, space):
        pass

    def descr_expandtabs(self, space):
        pass

    def descr_find(self, space):
        pass

    def descr_rfind(self, space):
        pass

    def descr_index(self, space):
        pass

    def descr_rindex(self, space):
        pass

    def descr_isalnum(self, space):
        pass

    def descr_isalpha(self, space):
        pass

    def descr_isdigit(self, space):
        pass

    def descr_islower(self, space):
        pass

    def descr_isspace(self, space):
        pass

    def descr_istitle(self, space):
        pass

    def descr_isupper(self, space):
        pass

    def descr_join(self, space):
        pass

    def descr_ljust(self, space):
        pass

    def descr_rjust(self, space):
        pass

    def descr_lower(self, space):
        pass

    def descr_partition(self, space):
        pass

    def descr_rpartition(self, space):
        pass

    def descr_replace(self, space):
        pass

    def descr_split(self, space):
        pass

    def descr_rsplit(self, space):
        pass

    def descr_splitlines(self, space):
        pass

    def descr_startswith(self, space):
        pass

    def descr_endswith(self, space):
        pass

    def descr_strip(self, space):
        pass

    def descr_lstrip(self, space):
        pass

    def descr_rstrip(self, space):
        pass

    def descr_swapcase(self, space):
        pass

    def descr_title(self, space):
        pass

    def descr_translate(self, space):
        pass

    def descr_upper(self, space):
        pass

    def descr_zfill(self, space):
        pass
