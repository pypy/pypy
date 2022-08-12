from collections import Counter

from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask
from rpython.rlib.unicodedata.supportcode import signed_ord
from rpython.rtyper.lltypesystem.rffi import r_ushort, r_short

WORDSIZE = 8

def get_size_unsignedness(data):
    # return smallest possible integer size for the given array, and a flag of
    # unsigned or not
    maxdata = max(data)
    mindata = min(data)
    if mindata < 0:
        assert -2 ** 63 - 1 <= mindata and maxdata < 2 ** 63
        assert maxdata < 2 ** 64
        for size in [1, 2, 4, 8]:
            bits = size * 8 - 1
            if -2 ** bits - 1 <= mindata and maxdata < 2 ** bits:
                return size, False
    else:
        if not maxdata < 2 ** 64:
            import pdb; pdb.set_trace()
        for size in [1, 2, 4, 8]:
            bits = size * 8
            if maxdata < 2 ** bits:
                return size, True
    assert 0, "unreachable"

def getsize_unsigned(data):
    size, unsigned = get_size_unsignedness(data)
    assert unsigned
    return size

class CodeWriter(object):
    def __init__(self, outfile):
        self.outfile = outfile
        # category -> size
        self.size_estimates = Counter()
        self.seen_strings = set()

    def print_stats(self):
        def kib(size):
            return round(size/1024., 2)
        print "estimated output sizes [KiB]"
        print "TOTAL", kib(sum(value for key, value in self.size_estimates.iteritems() if key != "unknown" and key != "code"))
        for category, size in self.size_estimates.most_common():
            if category == "code":
                continue
            print category, kib(size)

        print "python code [source KiB]", kib(self.size_estimates['code'])
        
    def print_listlike(self, name, lst, category=None):
        if not lst:
            print >> self.outfile, '%s = []' % (name, )
            return
        if not all(type(x) is int for x in lst):
            unwrapfunc = ''
            print >> self.outfile, '%s = [' % (name, )
            for val in lst:
                self._estimate_any(name, val, category)
                print >> self.outfile, '%r,' % val
            print >> self.outfile, ']'
            print >> self.outfile
            size = len(lst) * WORDSIZE + WORDSIZE * 2
            self._estimate_any(name, size, category)
            return ''
        itemsize, unsigned = get_size_unsignedness(lst)
        chunksize = 64
        if itemsize == 1:
            # a byte string is fine
            if unsigned:
                unwrapfunc = "ord"
            else:
                unwrapfunc = "signed_ord"
            self.print_string(
                name, "".join(chr(c & 0xff) for c in lst), category)
            return unwrapfunc
        unwrapfunc = "intmask"
        if itemsize == 2:
            if unsigned:
                typ = r_ushort
                conv_func = "_all_ushort"
            else:
                typ = r_short
                conv_func = "_all_short"
        else:
            assert itemsize == 4
            if unsigned:
                typ = r_uint32
                conv_func = "_all_uint32"
            else:
                typ = r_int32
                conv_func = "_all_int32"
        print >> self.outfile, "%s = [" % name
        chunksize = 16
        res = []
        for element in lst:
            assert intmask(typ(element)) == element
            res.append(str(element))
            if len(res) == chunksize:
                print >> self.outfile, ", ".join(res) + ","
                res = []
        if res:
            print >> self.outfile, ", ".join(res) + ","
        print >> self.outfile, "]"
        print >> self.outfile, "%s = %s(%s)" % (name, conv_func, name)
        
        size = len(lst) * itemsize + WORDSIZE * 2
        self._estimate(name, size, category)
        return unwrapfunc

    def print_string(self, name, string, category=None):
        chunksize = 20
        self._estimate_string(name, string, category)
        result = ''
        print >> self.outfile, "%s = (" % name
        for i in range(0, len(string), chunksize):
            print >> self.outfile, repr(string[i : i + chunksize])
        print >> self.outfile, ")"

    def print_dict(self, name, d, category=None, outfunc=repr):
        items = d.items()
        items.sort()
        print >> self.outfile, '%s = {' % name
        for key, value in items:
            self._estimate_any(name, key, category)
            self._estimate_any(name, value, category)
            print >> self.outfile, '%s: %s,' % (outfunc(key), outfunc(value))
        # tough to estimate size, just use something
        size = len(d) * 16 + WORDSIZE * 4
        self._estimate(name, size, category)
        print >> self.outfile, '}'
        print >> self.outfile

    def print_set(self, name, s, category=None):
        items = sorted(s)
        print >> self.outfile, '%s = {' % name
        for key in items:
            self._estimate_any(name, key, category)
            print >> self.outfile, '%r: None,' % (key, )
        # tough to estimate size, just use something
        size = len(s) * 16 + WORDSIZE * 4
        self._estimate(name, size, category)
        print >> self.outfile, '}'
        print >> self.outfile

    def write(self, s):
        self._estimate("unknown", len(s))
        return self.outfile.write(s)

    def print_code(self, s):
        self._estimate("code", len(s))
        print >> self.outfile, s

    def _estimate_any(self, name, obj, category):
        if isinstance(obj, str):
            return self._estimate_string(name, obj, category)
        if isinstance(obj, int):
            return self._estimate(name, WORDSIZE, category)
        if isinstance(obj, float):
            return self._estimate(name, WORDSIZE, category)
        if isinstance(obj, list):
            for elt in obj:
                if not isinstance(elt, int):
                    return self._estimate(name, elt, category)
            return self._estimate(name, WORDSIZE * (len(obj) + 1), category)
        print "unknown type", obj
        #import pdb; pdb.set_trace()

    def _estimate_string(self, name, string, category=None):
        # size estimate for 64 bit, hash plus GC
        if string in self.seen_strings:
            return
        self.seen_strings.add(string)
        size = len(string) + 8 * 2
        self._estimate(name, size, category)

    def _estimate(self, name, size, category=None):
        if category is None:
            category = name
        self.size_estimates[category] += size
