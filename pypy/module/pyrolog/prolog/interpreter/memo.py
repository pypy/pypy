from prolog.interpreter.term import NumberedVar

class EnumerationMemo(object):
    """A memo object to enumerate the variables in a term"""
    def __init__(self):
        self.seen = {}
        self.varcount = 0

    def get(self, var):
        res = self.seen.get(var, None)
        if not res:
            self.seen[var] = res = NumberedVar(-1)
        elif res.num == -1:
            # the variable is found a second time, it needs a real number
            res.num = self.varcount
            self.varcount += 1
        return res

    def size(self):
        return self.varcount

class CopyMemo(object):
    def __init__(self):
        self.seen = None

    def get(self, key):
        if self.seen is None:
            self.seen = {}
        return self.seen.get(key, None)

    def set(self, key, val):
        if self.seen is None:
            self.seen = {}
        self.seen[key] = val

