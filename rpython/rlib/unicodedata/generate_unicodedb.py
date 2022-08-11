#!/usr/bin/env python
import sys, os
import itertools
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask
from rpython.rtyper.lltypesystem.rffi import r_ushort, r_short
from rpython.rlib.unicodedata.codegen import CodeWriter, getsize_unsigned

MAXUNICODE = 0x10FFFF     # the value of sys.maxunicode of wide Python builds

MANDATORY_LINE_BREAKS = ["BK", "CR", "LF", "NL"] # line break categories

# Private Use Areas -- in planes 1, 15, 16
PUA_1 = range(0xE000, 0xF900)
PUA_15 = range(0xF0000, 0xFFFFE)
PUA_16 = range(0x100000, 0x10FFFE)

class Fraction:
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator

    def __repr__(self):
        return '%r / %r' % (self.numerator, self.denominator)

    def __str__(self):
        return repr(self)

class UnicodeChar:
    def __init__(self, data=None):
        if data is None:
            return
        if not data[1] or data[1][0] == '<' and data[1][-1] == '>':
            self.name = None
        else:
            self.name = data[1]
        self.category = data[2]
        self.east_asian_width = 'N'
        self.combining = 0
        if data[3]:
            self.combining = int(data[3])
        self.bidirectional = data[4]
        self.raw_decomposition = ''
        self.decomposition = []
        self.isCompatibility = False
        self.canonical_decomp = None
        self.compat_decomp = None
        self.excluded = False
        self.linebreak = False
        self.decompositionTag = ''
        self.properties = ()
        self.casefolding = None
        if data[5]:
            self.raw_decomposition = data[5]
            if data[5][0] == '<':
                self.isCompatibility = True
                self.decompositionTag, decomp = data[5].split(None, 1)
            else:
                decomp = data[5]
            self.decomposition = map(lambda x:int(x, 16), decomp.split())
        self.decimal = None
        if data[6]:
            self.decimal = int(data[6])
        self.digit = None
        if data[7]:
            self.digit = int(data[7])
        self.numeric = None
        if data[8]:
            try:
                numerator, denomenator = data[8].split('/')
                self.numeric = Fraction(float(numerator), float(denomenator))
            except ValueError:
                self.numeric = float(data[8])
        self.mirrored = (data[9] == 'Y')
        self.upper = None
        if data[12]:
            self.upper = int(data[12], 16)
        self.lower = None
        if data[13]:
            self.lower = int(data[13], 16)
        self.title = None
        if data[14]:
            self.title = int(data[14], 16)

    def copy(self):
        uc = UnicodeChar()
        uc.__dict__.update(self.__dict__)
        return uc

class UnicodeData(object):
    # we use this range of PUA_15 to store name aliases and named sequences
    NAME_ALIASES_START = 0xF0000
    NAMED_SEQUENCES_START = 0xF0200

    def __init__(self):
        self.table = [None] * (MAXUNICODE + 1)
        self.aliases = []
        self.named_sequences = []

    def add_char(self, code, char):
        assert self.table[code] is None, (
            'Multiply defined character %04X' % code)
        if isinstance(char, list):
            char = UnicodeChar(char)
        self.table[code] = char
        return char

    def all_codes(self):
        return range(len(self.table))

    def enum_chars(self):
        for code in range(len(self.table)):
            yield code, self.table[code]

    def get_char(self, code):
        return self.table[code]

    def clone_char(self, code):
        clone = self.table[code] = self.table[code].copy()
        return clone

    def set_excluded(self, code):
        self.table[code].excluded = True

    def set_linebreak(self, code):
        self.table[code].linebreak = True

    def set_east_asian_width(self, code, width):
        self.table[code].east_asian_width = width

    def add_property(self, code, p):
        self.table[code].properties += (p,)

    def get_compat_decomposition(self, code):
        if not self.table[code].decomposition:
            return [code]
        if not self.table[code].compat_decomp:
            result = []
            for decomp in self.table[code].decomposition:
                result.extend(self.get_compat_decomposition(decomp))
            self.table[code].compat_decomp = result
        return self.table[code].compat_decomp

    def get_canonical_decomposition(self, code):
        if (not self.table[code].decomposition or
            self.table[code].isCompatibility):
            return [code]
        if not self.table[code].canonical_decomp:
            result = []
            for decomp in self.table[code].decomposition:
                result.extend(self.get_canonical_decomposition(decomp))
            self.table[code].canonical_decomp = result
        return self.table[code].canonical_decomp

    def add_alias(self, name, char):
        pua_index = self.NAME_ALIASES_START + len(self.aliases)
        self.aliases.append((name, char))
        # also store the name in the PUA 1
        self.table[pua_index].name = name

    def add_named_sequence(self, name, chars):
        pua_index = self.NAMED_SEQUENCES_START + len(self.named_sequences)
        self.named_sequences.append((name, chars))
        # also store these in the PUA 1
        self.table[pua_index].name = name

    def add_casefold_sequence(self, code, chars):
        self.table[code].casefolding = chars


def read_unicodedata(files):
    rangeFirst = {}
    rangeLast = {}
    table = UnicodeData()
    for line in files['data']:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        data = [ v.strip() for v in line.split(';') ]
        if data[1].endswith(', First>'):
            code = int(data[0], 16)
            name = data[1][1:-len(', First>')]
            rangeFirst[name] = (code, data)
            continue
        if data[1].endswith(', Last>'):
            code = int(data[0], 16)
            rangeLast[name]  = code
            continue
        code = int(data[0], 16)
        table.add_char(code, data)

    # Collect ranges
    ranges = {}
    for name, (start, data) in rangeFirst.iteritems():
        end = rangeLast[name]
        ranges[(start, end)] = ['0000', None] + data[2:]

    # Read exclusions
    for line in files['exclusions']:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        table.set_excluded(int(line, 16))

    # Read line breaks
    for line in files['linebreak']:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        data = [v.strip() for v in line.split(';')]
        if len(data) < 2 or data[1] not in MANDATORY_LINE_BREAKS:
            continue
        if '..' not in data[0]:
            first = last = int(data[0], 16)
        else:
            first, last = [int(c, 16) for c in data[0].split('..')]
        for char in range(first, last+1):
            table.set_linebreak(char)

    # Expand ranges
    for (first, last), data in ranges.iteritems():
        for code in range(first, last + 1):
            table.add_char(code, data)

    # Read east asian width
    for line in files['east_asian_width']:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        code, width = line.split(';')
        if '..' in code:
            first, last = map(lambda x:int(x,16), code.split('..'))
            for code in range(first, last + 1):
                uc = table.get_char(code)
                if not uc:
                    uc = table.add_char(code, ['0000', None,
                                               'Cn'] + [''] * 12)
                uc.east_asian_width = width
        else:
            table.set_east_asian_width(int(code, 16), width)

    # Read Derived Core Properties:
    for line in files['derived_core_properties']:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue

        r, p = line.split(";")
        r = r.strip()
        p = p.strip()
        if ".." in r:
            first, last = [int(c, 16) for c in r.split('..')]
            chars = list(range(first, last+1))
        else:
            chars = [int(r, 16)]
        for char in chars:
            if not table.get_char(char):
                # Some properties (e.g. Default_Ignorable_Code_Point)
                # apply to unassigned code points; ignore them
                continue
            table.add_property(char, p)

    defaultChar = UnicodeChar(['0000', None, 'Cn'] + [''] * 12)
    for code, char in table.enum_chars():
        if not char:
            table.add_char(code, defaultChar)

    extra_numeric = read_unihan(files['unihan'])
    for code, value in extra_numeric.iteritems():
        table.clone_char(code).numeric = value

    table.special_casing = {}
    if 'special_casing' in files:
        for line in files['special_casing']:
            line = line[:-1].split('#', 1)[0]
            if not line:
                continue
            data = line.split("; ")
            if data[4]:
                # We ignore all conditionals (since they depend on
                # languages) except for one, which is hardcoded. See
                # handle_capital_sigma in unicodeobject.py.
                continue
            c = int(data[0], 16)
            lower = [int(char, 16) for char in data[1].split()]
            title = [int(char, 16) for char in data[2].split()]
            upper = [int(char, 16) for char in data[3].split()]
            table.special_casing[c] = (lower, title, upper)

    # Compute full decompositions.
    for code, char in table.enum_chars():
        table.get_canonical_decomposition(code)
        table.get_compat_decomposition(code)

    # Name aliases
    for line in files['name_aliases']:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        items = line.split(';')
        char = int(items[0], 16)
        name = items[1]
        table.add_alias(name, char)

    # Named sequences
    for line in files['named_sequences']:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, chars = line.split(';')
        chars = tuple(int(char, 16) for char in chars.split())
        table.add_named_sequence(name, chars)

    # Casefold sequences
    for line in files['casefolding']:
        line = line.strip().split('#', 1)[0]
        if not line or line.startswith('#'):
            continue
        code, status, mapping, _ = line.split('; ')
        code = int(code, 16)
        if status in 'CF':
            chars = [int(char, 16) for char in mapping.split()]
            table.add_casefold_sequence(code, chars)

    return table

def read_unihan(unihan_file):
    if unihan_file is None:
        return {}
    extra_numeric = {}
    for line in unihan_file:
        if not line.startswith('U+'):
            continue
        code, tag, value = line.split(None, 3)[:3]
        if tag not in ('kAccountingNumeric', 'kPrimaryNumeric', 'kOtherNumeric'):
            continue
        value = value.strip().replace(',', '')
        if '/' in value:
            numerator, denomenator = value.split('/')
            numeric = Fraction(float(numerator), float(denomenator))
        else:
            numeric = float(value)
        code = int(code[2:], 16)
        extra_numeric[code] = numeric
    return extra_numeric

DUMMY = object()

def writeDict(outfile, name, dictionary, base_mod):
    if base_mod:
        base_dict = getattr(base_mod, name)
    else:
        base_dict = {}
    items = {key: value for key, value in dictionary.iteritems()
            if base_dict.get(key, DUMMY) != value}
    outfile.print_dict(name, items)
    if base_mod:
        corrected = {key for key in base_dict if key not in dictionary}
        if len(corrected) == 0:
            # use an empty list. 'in' works as well, and rpython is better able to
            # reason about global lists than dicts (the immutability of dicts is
            # not tracked)
            print >> outfile, '%s_corrected = []' % name
            return
        outfile.print_set(name + "_corrected", corrected)


class Cache:
    def __init__(self):
        self._cache = {}
        self._strings = []
    def get(self, string):
        try:
            return self._cache[string]
        except KeyError:
            index = len(self._cache)
            self._cache[string] = index
            self._strings.append(string)
            return index

def output_table_columnwise(outfile, prefix, l, column_headers):
    for record in l:
        assert len(record) == len(column_headers)

    for tupindex, name in enumerate(column_headers):
        columndata = [record[tupindex] for record in l]
        if not columndata:
            print >> outfile, 'def lookup%s%s(index): assert 0' % (prefix, name)
            continue
        if all(type(x) is int for x in columndata):
            unwrapfunc = outfile.print_listlike(prefix + name, columndata)
        else:
            unwrapfunc = ''
            print >> outfile, '%s%s = [' % (prefix, name)
            for val in columndata:
                print >> outfile, '%r,' % val
            print >> outfile, ']'
            print >> outfile
        print >> outfile, """\
def lookup%s%s(index):
    return %s(%s%s[index])
""" % (prefix, name, unwrapfunc, prefix, name, )

def write_pages(outfile, prefix, lookupfuncname, data):
    pgtbl, pages, pgbits = splitbins(data)
    pgsize = 1 << pgbits
    bytemask = ~(-1 << pgbits)
    unwrapfunc = "intmask"
    unwrapfunc1 = outfile.print_listlike(prefix + "pgtbl", pgtbl)
    unwrapfunc2 = outfile.print_listlike(prefix + "pages", pages)
    print >> outfile, '''
def _get_record_index(code):
    return %s(%spages[(%s(%spgtbl[code >> %d]) << %d) + (code & %d)])
'''%(unwrapfunc2, prefix, unwrapfunc1, prefix, pgbits, pgbits, bytemask)

def writeDbRecord(outfile, table, base_mod):
    IS_SPACE = 1
    IS_ALPHA = 2
    IS_LINEBREAK = 4
    IS_UPPER = 8
    IS_TITLE = 16
    IS_LOWER = 32
    IS_NUMERIC = 64
    IS_DIGIT = 128
    IS_DECIMAL = 256
    IS_MIRRORED = 512
    IS_XID_START = 1024
    IS_XID_CONTINUE = 2048
    IS_PRINTABLE = 4096 # PEP 3138
    IS_CASE_IGNORABLE = 8192

    # Prepare special casing
    sc_list = []
    sc_db = {} # mapping code: index in sc_list
    for code, value in sorted(table.special_casing.items()):
        sc_db[code] = len(sc_list)
        sc_list.append(value)

    output_table_columnwise(outfile, "_special_casing_", sc_list,
        ("lower", "title", "upper"))

    # Create the records
    db_records_list = []
    db_records = {}

    for code in table.all_codes():
        char = table.get_char(code)
        # default values
        decimal = digit = 0
        numeric = 0.0

        # categories and flags, decimal, digit, numeric
        flags = 0
        if char.category == "Zs" or char.bidirectional in ("WS", "B", "S"):
            flags |= IS_SPACE
        if char.category in ("Lm", "Lt", "Lu", "Ll", "Lo"):
            flags |= IS_ALPHA
        if char.linebreak or char.bidirectional == "B":
            flags |= IS_LINEBREAK
        if char.numeric is not None:
            flags |= IS_NUMERIC
            numeric = char.numeric
        if char.digit is not None:
            flags |= IS_DIGIT
            digit = char.digit
        if char.decimal is not None:
            flags |= IS_DECIMAL
            decimal = char.decimal
        if char.category == "Lu" or (table.upper_lower_from_properties and
                                     "Uppercase" in char.properties):
            flags |= IS_UPPER
        if char.category == "Lt":
            flags |= IS_TITLE
        if char.category == "Ll" or (table.upper_lower_from_properties and
                                     "Lowercase" in char.properties):
            flags |= IS_LOWER
        if char.mirrored:
            flags |= IS_MIRRORED
        if code == ord(" ") or char.category[0] not in ("C", "Z"):
            flags |= IS_PRINTABLE
        if "XID_Start" in char.properties:
            flags |= IS_XID_START
        if "XID_Continue" in char.properties:
            flags |= IS_XID_CONTINUE
        if "Case_Ignorable" in char.properties:
            flags |= IS_CASE_IGNORABLE

        # casing
        upperdist = 0
        if char.upper:
            if code < 128:
                assert ord('a') <= code <= ord('z')
                assert char.upper == code - 32
                assert code not in table.special_casing
            else:
                upperdist = code - char.upper
        lowerdist = 0
        if char.lower:
            if code < 128:
                assert ord('A') <= code <= ord('Z')
                assert char.lower == code + 32
                assert code not in table.special_casing
            else:
                lowerdist = code - char.lower
        if char.title:
            titledist = code - char.title
        else:
            titledist = 0
        # special casing
        special_casing_index = sc_db.get(code, -1)
        db_record = (char.category, char.bidirectional,
                char.east_asian_width, numeric, decimal, digit, upperdist,
                lowerdist, titledist, special_casing_index, flags)
        if db_record not in db_records:
            db_records[db_record] = len(db_records)
            db_records_list.append(db_record)
        char.db_record_index = db_records[db_record]
    output_table_columnwise(outfile, "_db_", db_records_list,
        ("category", "bidirectional", "east_asian_width", "numeric", "decimal",
            "digit", "upperdist", "lowerdist", "titledist", "special_casing_index",
            "flags"))

    data = [char.db_record_index for code, char in table.enum_chars()]
    write_pages(outfile, "_db_", "_get_record_index", data)
    print >> outfile, 'def category(code): return lookup_db_category(_get_record_index(code))'
    print >> outfile, 'def bidirectional(code): return lookup_db_bidirectional(_get_record_index(code))'
    print >> outfile, 'def east_asian_width(code): return lookup_db_east_asian_width(_get_record_index(code))'
    print >> outfile, 'def isspace(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_SPACE
    print >> outfile, 'def isalpha(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_ALPHA
    print >> outfile, 'def islinebreak(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_LINEBREAK
    print >> outfile, 'def isnumeric(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_NUMERIC
    print >> outfile, 'def isdigit(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_DIGIT
    print >> outfile, 'def isdecimal(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_DECIMAL
    print >> outfile, 'def isalnum(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% (IS_ALPHA | IS_NUMERIC)
    print >> outfile, 'def isupper(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_UPPER
    print >> outfile, 'def istitle(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_TITLE
    print >> outfile, 'def islower(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_LOWER
    print >> outfile, 'def iscased(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% (IS_UPPER | IS_TITLE | IS_LOWER)
    print >> outfile, 'def isxidstart(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% (IS_XID_START)
    print >> outfile, 'def isxidcontinue(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% (IS_XID_CONTINUE)
    print >> outfile, 'def isprintable(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_PRINTABLE
    print >> outfile, 'def mirrored(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_MIRRORED
    print >> outfile, 'def iscaseignorable(code): return lookup_db_flags(_get_record_index(code)) & %d != 0'% IS_CASE_IGNORABLE
    print >> outfile, '''\
def decimal(code):
    if isdecimal(code):
        return lookup_db_decimal(_get_record_index(code))
    else:
        raise KeyError

def digit(code):
    if isdigit(code):
        return lookup_db_digit(_get_record_index(code))
    else:
        raise KeyError

def numeric(code):
    if isnumeric(code):
        return lookup_db_numeric(_get_record_index(code))
    else:
        raise KeyError

'''

def write_character_names(outfile, table, base_mod):
    from rpython.rlib.unicodedata import dawg

    names = dict((table.get_char(code).name, code)
                 for code in table.all_codes()
                 if table.get_char(code).name)
    sorted_names_codes = sorted(names.iteritems())
    if base_mod is None:
        dawg.build_compression_dawg(outfile, names)
        print >> outfile, "# the following dictionary is used by modules that take this as a base"
        print >> outfile, "# only used by generate_unicodedb, not after translation"
        print >> outfile, "_orig_names = {"
        for name, code in sorted_names_codes:
            print >> outfile, "%r: %r," % (name, code)
        print >> outfile, "}"
    else:
        corrected_names = []

        for name, code in sorted_names_codes:
            try:
                if base_mod.lookup_charcode(code) == name:
                    continue
            except KeyError:
                pass
            corrected_names.append((name, code))
        corrected_names_dict = dict(corrected_names)
        dawg.build_compression_dawg(outfile, corrected_names_dict)

        removed_names = []
        for name, code in sorted(base_mod._orig_names.iteritems()):
            if name not in names:
                removed_names.append((name, code))
        assert not removed_names

def writeUnicodedata(version, version_tuple, table, outfile, base):
    if base:
        print >> outfile, 'import %s as base_mod' % base
        base_mod = __import__(base)
    else:
        print >> outfile, 'base_mod = None'
        base_mod = None
    # Version
    print >> outfile, 'version = %r' % version
    print >> outfile

    if version_tuple < (4, 1, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FA5 or"
                        " 0x20000 <= code <= 0x2A6D6)")
    elif version_tuple < (5, 0, 0):    # don't know the exact limit
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FBB or"
                        " 0x20000 <= code <= 0x2A6D6)")
    elif version_tuple < (6, 0, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FCB or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734)")
    elif version_tuple < (6, 1, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FCB or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734 or"
                        " 0x2B740 <= code <= 0x2B81D)")
    elif version_tuple < (8, 0, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FCC or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734 or"
                        " 0x2B740 <= code <= 0x2B81D)")
    elif version_tuple < (10, 0, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FD5 or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734 or"
                        " 0x2B740 <= code <= 0x2B81D or"
                        " 0x2B820 <= code <= 0x2CEA1)")
    elif version_tuple == (11, 0, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FEF or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734 or"
                        " 0x2B740 <= code <= 0x2B81D or"
                        " 0x2B820 <= code <= 0x2CEA1)")
    elif version_tuple == (12, 1, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FEF or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734 or"
                        " 0x2B740 <= code <= 0x2CEA1 or"
                        " 0x2CEB0 <= code <= 0x2EBE0)")
    elif version_tuple == (13, 0, 0):
        cjk_interval = ("(0x3400 <= code <= 0x4DB5 or"
                        " 0x4E00 <= code <= 0x9FFC or"
                        " 0x20000 <= code <= 0x2A6D6 or"
                        " 0x2A700 <= code <= 0x2B734 or"
                        " 0x2B740 <= code <= 0x2CEA1 or"
                        " 0x2CEB0 <= code <= 0x2EBE0)")
    else:
        raise ValueError("please look up CJK ranges and fix the script, e.g. here: https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)")

    write_character_names(outfile, table, base_mod)

    outfile.write_code('''
def _lookup_cjk(cjk_code):
    if len(cjk_code) != 4 and len(cjk_code) != 5:
        raise KeyError
    for c in cjk_code:
        if not ('0' <= c <= '9' or 'A' <= c <= 'F'):
            raise KeyError
    code = int(cjk_code, 16)
    if %(cjk_interval)s:
        return code
    raise KeyError

def lookup(name, with_named_sequence=False):
    from rpython.rlib.rstring import startswith
    if startswith(name, _cjk_prefix):
        return _lookup_cjk(name[len(_cjk_prefix):])
    if startswith(name, _hangul_prefix):
        return _lookup_hangul(name[len(_hangul_prefix):])

    if not base_mod:
        code = dawg_lookup(name)
    else:
        try:
            code = dawg_lookup(name)
        except KeyError:
            code = base_mod.dawg_lookup(name)
    if not with_named_sequence and %(named_sequence_interval)s:
        raise KeyError
    return code

def name(code):
    if %(cjk_interval)s:
        return "CJK UNIFIED IDEOGRAPH-" + hex(code)[2:].upper()
    if 0xAC00 <= code <= 0xD7A3:
        # vl_code, t_code = divmod(code - 0xAC00, len(_hangul_T))
        vl_code = (code - 0xAC00) // len(_hangul_T)
        t_code = (code - 0xAC00) %% len(_hangul_T)
        # l_code, v_code = divmod(vl_code,  len(_hangul_V))
        l_code = vl_code // len(_hangul_V)
        v_code = vl_code %% len(_hangul_V)
        return ("HANGUL SYLLABLE " + _hangul_L[l_code] +
                _hangul_V[v_code] + _hangul_T[t_code])
    if %(pua_interval)s:
        raise KeyError

    if base_mod is None:
        return lookup_charcode(code)
    else:
        try:
            return lookup_charcode(code)
        except KeyError:
            return base_mod.lookup_charcode(code)
''' % dict(cjk_interval=cjk_interval,
           pua_interval="0xF0000 <= code < 0xF0400",
           named_sequence_interval="0xF0200 <= code < 0xF0400"))

    # Categories
    writeDbRecord(outfile, table, base_mod)
    outfile.write_code('''
def toupper(code):
    if code < 128:
        if ord('a') <= code <= ord('z'):
            return code - 32
        return code
    return code - lookup_db_upperdist(_get_record_index(code))

def tolower(code):
    if code < 128:
        if ord('A') <= code <= ord('Z'):
            return code + 32
        return code
    return code - lookup_db_lowerdist(_get_record_index(code))

def totitle(code):
    if code < 128:
        if ord('A') <= code <= ord('Z'):
            return code - 32
        return code
    return code - lookup_db_titledist(_get_record_index(code))

def toupper_full(code):
    if code < 128:
        if ord('a') <= code <= ord('z'):
            return [code - 32]
        return [code]
    index = lookup_db_special_casing_index(_get_record_index(code))
    if index == -1:
        return [toupper(code)]
    return lookup_special_casing_upper(index)

def tolower_full(code):
    if code < 128:
        if ord('A') <= code <= ord('Z'):
            return [code + 32]
        return [code]
    index = lookup_db_special_casing_index(_get_record_index(code))
    if index == -1:
        return [tolower(code)]
    return lookup_special_casing_lower(index)

def totitle_full(code):
    index = lookup_db_special_casing_index(_get_record_index(code))
    if index == -1:
        return [totitle(code)]
    return lookup_special_casing_title(index)
''')
    # Decomposition
    decomposition = {}
    for code, char in table.enum_chars():
        if char.raw_decomposition:
            decomposition[code] = char.raw_decomposition
    writeDict(outfile, '_raw_decomposition', decomposition, base_mod)
    print >> outfile, '''
def decomposition(code):
    try:
        return _raw_decomposition[code]
    except KeyError:
        if base_mod is not None and code not in _raw_decomposition_corrected:
            return base_mod._raw_decomposition.get(code, '')
        else:
            return ''
'''
    # Collect the composition pairs.
    compositions = []
    for code, unichar in table.enum_chars():
        if (not unichar.decomposition or
            unichar.isCompatibility or
            unichar.excluded or
            len(unichar.decomposition) != 2 or
            table.get_char(unichar.decomposition[0]).combining):
            continue
        left, right = unichar.decomposition
        compositions.append((left, right, code))
    print >> outfile, '_composition = {'
    for left, right, code in compositions:
        print >> outfile, 'r_longlong(%5d << 32 | %5d): %5d,' % (
            left, right, code)
    print >> outfile, '}'
    print >> outfile

    decomposition = {}
    for code, char in table.enum_chars():
        if char.canonical_decomp:
            decomposition[code] = char.canonical_decomp
    writeDict(outfile, '_canon_decomposition', decomposition, base_mod)

    decomposition = {}
    for code, char in table.enum_chars():
        if char.compat_decomp:
            decomposition[code] = char.compat_decomp
    writeDict(outfile, '_compat_decomposition', decomposition, base_mod)
    print >> outfile, '''
def canon_decomposition(code):
    try:
        return _canon_decomposition[code]
    except KeyError:
        if base_mod is not None and code not in _canon_decomposition_corrected:
            return base_mod._canon_decomposition.get(code, [])
        else:
            return []
def compat_decomposition(code):
    try:
        return _compat_decomposition[code]
    except KeyError:
        if base_mod is not None and code not in _compat_decomposition_corrected:
            return base_mod._compat_decomposition.get(code, [])
        else:
            return []

'''

    # named sequences
    print >> outfile, '_named_sequences = ['
    for name, chars in table.named_sequences:
        print >> outfile, "%r," % (u''.join(unichr(c) for c in chars))
    print >> outfile, ']'
    print >> outfile, '''

def lookup_named_sequence(code):
    if 0 <= code - %(start)s < len(_named_sequences):
        return _named_sequences[code - %(start)s]
    else:
        return None
''' % dict(start=table.NAMED_SEQUENCES_START)

    # aliases
    print >> outfile, '_name_aliases = ['
    for name, char in table.aliases:
        print >> outfile, "%s," % (char,)
    print >> outfile, ']'
    print >> outfile, '''

def lookup_with_alias(name, with_named_sequence=False):
    code = lookup(name, with_named_sequence=with_named_sequence)
    if 0 <= code - %(start)s < len(_name_aliases):
        return _name_aliases[code - %(start)s]
    else:
        return code
''' % dict(start=table.NAME_ALIASES_START)

    casefolds = {}
    for code, char in table.enum_chars():
        full_casefold = char.casefolding
        if full_casefold is None:
            full_casefold = [code]
        full_lower = char.lower
        if full_lower is None:
            full_lower = code
        # if we don't write anything into the file, then the RPython
        # program would compute the result 'full_lower' instead.
        # Is that the right answer?
        if full_casefold != [full_lower]:
            casefolds[code] = full_casefold
    writeDict(outfile, '_casefolds', casefolds, base_mod)
    print >> outfile, '''

def casefold_lookup(code):
    try:
        return _casefolds[code]
    except KeyError:
        if base_mod is not None and code not in _casefolds_corrected:
            return base_mod._casefolds.get(code, None)
        else:
            return None
'''

    combining = {}
    for code, char in table.enum_chars():
        if char.combining:
            combining[code] = char.combining
    writeDict(outfile, '_combining', combining, base_mod)
    print >> outfile, '''

def combining(code):
    try:
        return _combining[code]
    except KeyError:
        if base_mod is not None and code not in _combining_corrected:
            return base_mod._combining.get(code, 0)
        else:
            return 0
'''


def main():
    import sys
    from optparse import OptionParser
    infile = None
    outfile = sys.stdout

    parser = OptionParser('Usage: %prog [options]')
    parser.add_option('--base', metavar='FILENAME', help='Base python version (for import)')
    parser.add_option('--output', metavar='OUTPUT_MODULE', help='Output module (implied py extension)')
    parser.add_option('--unidata_version', metavar='#.#.#', help='Unidata version')
    options, args = parser.parse_args()

    if not options.unidata_version:
        raise Exception("No version specified")

    if options.output:
        outfile = open(options.output + '.py', "w")

    filenames = dict(
        data='UnicodeData-%(version)s.txt',
        exclusions='CompositionExclusions-%(version)s.txt',
        east_asian_width='EastAsianWidth-%(version)s.txt',
        unihan='UnihanNumeric-%(version)s.txt',
        linebreak='LineBreak-%(version)s.txt',
        derived_core_properties='DerivedCoreProperties-%(version)s.txt',
        name_aliases='NameAliases-%(version)s.txt',
        named_sequences = 'NamedSequences-%(version)s.txt',
        casefolding = 'CaseFolding-%(version)s.txt',
    )
    version_tuple = tuple(int(x) for x in options.unidata_version.split("."))
    if version_tuple[0] >= 5:
        filenames['special_casing'] = 'SpecialCasing-%(version)s.txt'
    filenames = dict((name, filename % dict(version=options.unidata_version))
                     for (name, filename) in filenames.items())
    files = dict((name, open(filename))
                 for (name, filename) in filenames.items())

    table = read_unicodedata(files)
    table.upper_lower_from_properties = (version_tuple[0] >= 6)

    outfile = CodeWriter(outfile)
    print >> outfile, '# UNICODE CHARACTER DATABASE'
    print >> outfile, '# This file was generated with the command:'
    print >> outfile, '#    ', ' '.join(sys.argv)
    print >> outfile
    print >> outfile, 'from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask'
    print >> outfile, '''\
from rpython.rlib.unicodedata.supportcode import (signed_ord, _all_short,
    _all_ushort, _all_int32, _all_uint32, _cjk_prefix, _hangul_prefix,
    _lookup_hangul, _hangul_L, _hangul_V, _hangul_T)'''
    print >> outfile
    writeUnicodedata(options.unidata_version, version_tuple, table, outfile, options.base)

    outfile.print_stats()

# next function from CPython
def splitbins(t, trace=1):
    """t, trace=0 -> (t1, t2, shift).  Split a table to save space.

    t is a sequence of ints.  This function can be useful to save space if
    many of the ints are the same.  t1 and t2 are lists of ints, and shift
    is an int, chosen to minimize the combined size of t1 and t2 (in C
    code), and where for each i in range(len(t)),
        t[i] == t2[(t1[i >> shift] << shift) + (i & mask)]
    where mask is a bitmask isolating the last "shift" bits.

    If optional arg trace is non-zero (default zero), progress info
    is printed to sys.stderr.  The higher the value, the more info
    you'll get.
    """

    if trace:
        def dump(t1, t2, shift, bytes):
            print "%d+%d bins at shift %d; %d bytes" % (
                len(t1), len(t2), shift, bytes)
        print "Size of original table:", len(t)*getsize_unsigned(t), "bytes"
    n = len(t)-1    # last valid index
    maxshift = 0    # the most we can shift n and still have something left
    if n > 0:
        while n >> 1:
            n >>= 1
            maxshift += 1
    del n
    bytes = sys.maxsize  # smallest total size so far
    t = tuple(t)    # so slices can be dict keys
    for shift in range(maxshift + 1):
        t1, t2, b = _split(t, shift)
        if trace > 1:
            dump(t1, t2, shift, b)
        if b < bytes:
            best = t1, t2, shift
            bytes = b
    t1, t2, shift = best
    if trace:
        print "Best:",
        dump(t1, t2, shift, bytes)
    if 1:
        # exhaustively verify that the decomposition is correct
        mask = ~((~0) << shift) # i.e., low-bit mask of shift bits
        for i in range(len(t)):
            assert t[i] == t2[(t1[i >> shift] << shift) + (i & mask)]
    return best

def _split(t, shift):
    t1 = []
    t2 = []
    size = 2**shift
    bincache = {}
    for i in range(0, len(t), size):
        bin = t[i:i+size]
        index = bincache.get(bin)
        if index is None:
            index = len(t2)
            bincache[bin] = index
            t2.extend(bin)
        t1.append(index >> shift)
    # determine memory size
    b = len(t1)*getsize_unsigned(t1) + len(t2)*getsize_unsigned(t2)
    return t1, t2, b

if __name__ == '__main__':
    main()
