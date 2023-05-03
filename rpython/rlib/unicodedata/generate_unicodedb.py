#!/usr/bin/env python
import sys, os
import itertools
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask
from rpython.rtyper.lltypesystem.rffi import r_ushort, r_short
from rpython.rlib.unicodedata.codegen import CodeWriter, getsize_unsigned, get_char_list_offset

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

class Database(object):
    """ Code generation for compactly storing a "database", which maps
    consecutive integers (typically 0, ..., maxunicode) to tuples of
    information about them (called the columns). The storage is compact if the
    tuples repeat a lot. """

    def __init__(self, outfile, name, column_headers, need_index=True):
        self.outfile = outfile
        self.records = []
        self.records_index = {}
        self.name = name

        self.input_to_record_index = []
        self.column_headers = column_headers
        self.need_index = need_index

    def add_entry(self, data):
        data = tuple(data)
        assert len(data) == len(self.column_headers)
        if data not in self.records_index:
            self.records_index[data] = len(self.records)
            self.records.append(data)
        index = self.records_index[data]
        self.input_to_record_index.append(index)
        return index

    def output(self):
        print "====", self.name, "===="
        print "number of records", len(self.records)
        self._output_columns()
        if self.need_index:
            self._output_index()

    def _output_columns(self):
        prefix = "_" + self.name + "_"
        for tupindex, name in enumerate(self.column_headers):
            columndata = [record[tupindex] for record in self.records]
            self.outfile.print_listlike("lookup" + prefix + name, columndata)

    def _output_index(self):
        prefix = "_" + self.name + "_"
        lookupfuncname = prefix + 'index'
        write_pages(self.outfile, prefix, lookupfuncname, self.input_to_record_index)

def write_pages(outfile, prefix, lookupfuncname, data):
    pgtbl, pages, pgbits = splitbins(data)
    pgsize = 1 << pgbits
    bytemask = ~(-1 << pgbits)
    outfile.print_listlike(prefix + "pgtbl", pgtbl)
    outfile.print_listlike(prefix + "pages", pages)
    outfile.print_code('''
def %s(code):
    return %spages((%spgtbl(code >> %d) << %d) + (code & %d))
'''%(lookupfuncname, prefix, prefix, pgbits, pgbits, bytemask))

def writeDbRecord(outfile, table, char_list_index, base_mod):
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

    sc_db = Database(outfile, "special_casing", ("lower_len", "lower",
        "title_len", "title", "upper_len", "upper", "casefold_len",
        "casefold"), need_index=False)
    sc_code_to_index = {} # mapping code: index in sc_list
    for code, char in table.enum_chars():
        sc_data = table.special_casing.get(code, (None, None, None))
        if sc_data != (None, None, None):
            full_lower = sc_data[0]
        elif char.lower is None:
            full_lower = [code]
        else:
            full_lower = [char.lower]

        # now the casefolds
        full_casefold = char.casefolding
        if full_casefold is None:
            full_casefold = [code]
        # if we don't write anything into the file, then the RPython
        # program would compute the result 'full_lower' instead.
        if full_casefold != full_lower:
            sc_data += (full_casefold, )
        else:
            sc_data += (None, )
        if sc_data != (None, None, None, None):
            columns = []
            for cl in sc_data:
                if cl is None:
                    columns.append(0)
                    columns.append(0)
                else:
                    columns.append(len(cl))
                    columns.append(get_char_list_offset(
                        cl, None, char_list_index))
            sc_code_to_index[code] = sc_db.add_entry(columns)
    sc_db.output()

    # Create the records
    db = Database(outfile, "db", ("category", "bidirectional", "east_asian_width", "numeric", "decimal",
            "digit", "upperdist", "lowerdist", "titledist", "special_casing_index",
            "flags"))
    for code, char in table.enum_chars():
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
        special_casing_index = sc_code_to_index.get(code, -1)
        db_record = (char.category, char.bidirectional,
                char.east_asian_width, numeric, decimal, digit, upperdist,
                lowerdist, titledist, special_casing_index, flags)
        db.add_entry(db_record)
    db.output()

    outfile.print_code('def category(code): return lookup_db_category(_db_index(code))')
    outfile.print_code('def bidirectional(code): return lookup_db_bidirectional(_db_index(code))')
    outfile.print_code('def east_asian_width(code): return lookup_db_east_asian_width(_db_index(code))')
    outfile.print_code('def isspace(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_SPACE)
    outfile.print_code('def isalpha(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_ALPHA)
    outfile.print_code('def islinebreak(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_LINEBREAK)
    outfile.print_code('def isnumeric(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_NUMERIC)
    outfile.print_code('def isdigit(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_DIGIT)
    outfile.print_code('def isdecimal(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_DECIMAL)
    outfile.print_code('def isalnum(code): return lookup_db_flags(_db_index(code)) & %d != 0'% (IS_ALPHA | IS_NUMERIC))
    outfile.print_code('def isupper(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_UPPER)
    outfile.print_code('def istitle(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_TITLE)
    outfile.print_code('def islower(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_LOWER)
    outfile.print_code('def iscased(code): return lookup_db_flags(_db_index(code)) & %d != 0'% (IS_UPPER | IS_TITLE | IS_LOWER))
    outfile.print_code('def isxidstart(code): return lookup_db_flags(_db_index(code)) & %d != 0'% (IS_XID_START))
    outfile.print_code('def isxidcontinue(code): return lookup_db_flags(_db_index(code)) & %d != 0'% (IS_XID_CONTINUE))
    outfile.print_code('def isprintable(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_PRINTABLE)
    outfile.print_code('def mirrored(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_MIRRORED)
    outfile.print_code('def iscaseignorable(code): return lookup_db_flags(_db_index(code)) & %d != 0'% IS_CASE_IGNORABLE)
    outfile.print_code('''
def decimal(code):
    if isdecimal(code):
        return lookup_db_decimal(_db_index(code))
    else:
        raise KeyError

def digit(code):
    if isdigit(code):
        return lookup_db_digit(_db_index(code))
    else:
        raise KeyError

def numeric(code):
    if isnumeric(code):
        return lookup_db_numeric(_db_index(code))
    else:
        raise KeyError

''')

def get_index(d, l, key):
    try:
        return d[key]
    except KeyError:
        res = len(l)
        d[key] = res
        l.append(key)
        return res

def write_composition_data(outfile, table, char_list_index, base_mod):
    # first the composition data
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

    # map code -> index for left and right
    left_index = {}
    right_index = {}
    for left, right, code in compositions:
        if left not in left_index:
            left_index[left] = len(left_index)
        if right not in right_index:
            right_index[right] = len(right_index)
    composition_values = [0] * (len(left_index) * len(right_index))
    for left, right, code in compositions:
        composition_values[left_index[left] * len(right_index) + right_index[right]] = code

    print "composition_values"
    write_pages(outfile, "_comp_pairs_", "_composition", composition_values)

    # now the decompositions

    def get_index_comp(comp):
        return get_char_list_offset(comp, None, char_list_index)

    db = Database(outfile, "composition", ("prefix_index", "decomp_len",
        "decomp", "compat_decomp_len", "compat_decomp", "canon_decomp_len",
        "canon_decomp", "combining", "left_index", "right_index"))

    prefixes = {'': 0}
    prefix_list = ['']

    composition_db_index = []
    for code, char in table.enum_chars():
        prefix_index = 0
        decomp_len = 0
        decomp = 0
        compat_decomp = 0
        compat_decomp_len = 0
        canon_decomp = 0
        canon_decomp_len = 0
        combining = 0
        if char.raw_decomposition:
            if char.isCompatibility:
                index = char.raw_decomposition.index("> ")
                prefix = char.raw_decomposition[:index + 1]
                prefix_index = get_index(prefixes, prefix_list, prefix)
            decomp = get_index_comp(char.decomposition)
            decomp_len = len(char.decomposition)
        if char.compat_decomp:
            compat_decomp = get_index_comp(char.compat_decomp)
            compat_decomp_len = len(char.compat_decomp)
        if char.canonical_decomp:
            canon_decomp = get_index_comp(char.canonical_decomp)
            canon_decomp_len = len(char.canonical_decomp)
        if char.combining:
            combining = char.combining

        db_record = (prefix_index, decomp_len, decomp,
                compat_decomp_len, compat_decomp, canon_decomp_len,
                canon_decomp, combining, left_index.get(code, -1), right_index.get(code, -1))
        db.add_entry(db_record)

    db.output()

    outfile.print_code("""
def composition(current, next):
    l = lookup_composition_left_index(_composition_index(current))
    if l < 0:
        raise KeyError
    r = lookup_composition_right_index(_composition_index(next))
    if r < 0:
        raise KeyError
    key = l * %s + r
    result = _composition(key)
    if result == 0:
        raise KeyError
    return result
""" % len(right_index))

    outfile.print_listlike("_composition_prefixes", prefix_list)
    outfile.print_code("""
def decomposition(code):
    index = _composition_index(code)
    prefix = _composition_prefixes(lookup_composition_prefix_index(index))
    if prefix:
        res = [prefix]
    else:
        res = []
    start = lookup_composition_decomp(index)
    for i in range(lookup_composition_decomp_len(index)):
        s = hex(char_list_data(start + i))[2:].upper()
        if len(s) < 4:
            s = "0" * (4 - len(s)) + s
        res.append(s)
    return " ".join(res)

def canon_decomposition(code):
    index = _composition_index(code)
    length = lookup_composition_canon_decomp_len(index)
    start = lookup_composition_canon_decomp(index)
    return _get_char_list(length, start)

def compat_decomposition(code):
    index = _composition_index(code)
    length = lookup_composition_compat_decomp_len(index)
    start = lookup_composition_compat_decomp(index)
    return _get_char_list(length, start)

def combining(code):
    index = _composition_index(code)
    return lookup_composition_combining(index)
""")


def write_character_names(outfile, table, base_mod):
    from rpython.rlib.unicodedata import dawg

    names = dict((table.get_char(code).name, code)
                 for code in table.all_codes()
                 if table.get_char(code).name)
    sorted_names_codes = sorted(names.iteritems())
    if base_mod is None:
        d = dawg.build_compression_dawg(outfile, names)
        outfile.print_code("# the following dictionary is used by modules that take this as a base")
        outfile.print_code("# only used by generate_unicodedb, not after translation")
        outfile.print_code("_orig_names = {")
        for name, code in sorted_names_codes:
            outfile.print_code("%r: %r," % (name, code))
        outfile.print_code("}")
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
        outfile.print_code('import %s as base_mod' % base)
        base_mod = __import__(base)
    else:
        outfile.print_code("base_mod = None")
        base_mod = None
    # Version
    outfile.print_code('version = %r\n' % version)

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
                        " 0x2CEB0 <= code <= 0x2EBE0) or"
                        " 0x30000 <= code <= 0x3134A")
    else:
        raise ValueError("please look up CJK ranges and fix the script, e.g. here: https://www.unicode.org/reports/tr38/tr38-29.html#BlockListing")

    write_character_names(outfile, table, base_mod)

    outfile.print_code('''
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

def lookup(name, with_named_sequence=False, with_alias=False):
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
    if not with_alias and %(alias_interval)s:
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
           named_sequence_interval="0xF0200 <= code < 0xF0400",
           alias_interval="0xF0000 <= code < 0xF0200"))

    # shared character list for both compositions and casing
    char_list_index = {}
    char_list_data = []
    if base_mod is not None:
        i = 0
        while 1:
            try:
                char_list_data.append(base_mod._char_list_data(i))
            except IndexError:
                break
            i += 1
        for length in range(1, 20):
            for startindex in range(len(char_list_data) - length + 1):
                key = tuple(char_list_data[startindex: startindex + length])
                char_list_index[key] = startindex

    char_list_data_startsize = len(char_list_data)

    all_code_lists = set()
    for code, char in table.enum_chars():
        sc_data = table.special_casing.get(code, ())
        for cl in [char.decomposition, char.compat_decomp, char.canonical_decomp, char.casefolding] + list(sc_data):
            if cl:
                all_code_lists.add(tuple(cl))
    # add them all to the data, sort by longest
    for cl in sorted(all_code_lists, key=lambda cl: (-len(cl), cl)):
        get_char_list_offset(cl, char_list_data, char_list_index)
    outfile.print_listlike("_char_list_data", char_list_data[char_list_data_startsize:])
    outfile.print_code("""
def char_list_data(index):
    if index < %s:
        assert base_mod is not None
        return base_mod._char_list_data(index)
    return _char_list_data(index - %s)

def _get_char_list(length, start):
    res = [0] * length
    for i in range(length):
        res[i] = char_list_data(start + i)
    return res
    """ % (char_list_data_startsize, char_list_data_startsize))

    # Composition data
    write_composition_data(outfile, table, char_list_index, base_mod)

    # Categories
    writeDbRecord(outfile, table, char_list_index, base_mod)

    # API functions for returning casing information
    outfile.print_code('''
def toupper(code):
    if code < 128:
        if ord('a') <= code <= ord('z'):
            return code - 32
        return code
    return code - lookup_db_upperdist(_db_index(code))

def tolower(code):
    if code < 128:
        if ord('A') <= code <= ord('Z'):
            return code + 32
        return code
    return code - lookup_db_lowerdist(_db_index(code))

def totitle(code):
    if code < 128:
        if ord('a') <= code <= ord('z'):
            return code - 32
        return code
    return code - lookup_db_titledist(_db_index(code))

def toupper_full(code):
    if code < 128:
        if ord('a') <= code <= ord('z'):
            return [code - 32]
        return [code]
    index = lookup_db_special_casing_index(_db_index(code))
    if index == -1:
        return [toupper(code)]
    length = lookup_special_casing_upper_len(index)
    if length == 0:
        return [toupper(code)]
    start = lookup_special_casing_upper(index)
    return _get_char_list(length, start)

def tolower_full(code):
    if code < 128:
        if ord('A') <= code <= ord('Z'):
            return [code + 32]
        return [code]
    index = lookup_db_special_casing_index(_db_index(code))
    if index == -1:
        return [tolower(code)]
    length = lookup_special_casing_lower_len(index)
    if length == 0:
        return [tolower(code)]
    start = lookup_special_casing_lower(index)
    return _get_char_list(length, start)

def totitle_full(code):
    index = lookup_db_special_casing_index(_db_index(code))
    if index == -1:
        return [totitle(code)]
    length = lookup_special_casing_title_len(index)
    if length == 0:
        return [totitle(code)]
    start = lookup_special_casing_title(index)
    return _get_char_list(length, start)

def casefold_lookup(code):
    index = lookup_db_special_casing_index(_db_index(code))
    if index == -1:
        return tolower_full(code)
    length = lookup_special_casing_casefold_len(index)
    if length == 0:
        return tolower_full(code)
    start = lookup_special_casing_casefold(index)
    return _get_char_list(length, start)
    return lookup_special_casing_casefold(index)

''')

    # named sequences
    lst = [(u''.join(unichr(c) for c in chars)).encode("utf-8")
        for _, chars in table.named_sequences]
    outfile.print_listlike("_named_sequences", lst)
    lengths = [len(chars) for _, chars in table.named_sequences]
    outfile.print_listlike("_named_sequence_lengths", lengths)
    outfile.print_code('''

def lookup_named_sequence(code):
    if 0 <= code - %(start)s < %(len)s:
        return _named_sequences(code - %(start)s)
    else:
        return None

def lookup_named_sequence_length(code):
    if 0 <= code - %(start)s < %(len)s:
        return _named_sequence_lengths(code - %(start)s)
    else:
        return -1
''' % dict(start=table.NAMED_SEQUENCES_START, len=len(lst)))

    # aliases
    _name_aliases = [char for name, char in table.aliases]
    assert len(_name_aliases) < 0x200
    outfile.print_listlike("_name_aliases", _name_aliases)
    outfile.print_code('''

def lookup_with_alias(name, with_named_sequence=False):
    code = lookup(name, with_named_sequence=with_named_sequence, with_alias=True)
    if 0 <= code - %(start)s < %(length)s:
        return _name_aliases(code - %(start)s)
    else:
        return code
''' % dict(start=table.NAME_ALIASES_START,
           length=len(_name_aliases)))

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

    print "_" * 60
    print "starting", options.unidata_version

    outfile = CodeWriter(outfile)
    outfile.print_comment('UNICODE CHARACTER DATABASE')
    outfile.print_comment('# This file was generated with the command:')
    outfile.print_comment('#    ' + ' '.join(sys.argv))
    outfile.print_code('')
    outfile.print_code('from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask')
    outfile.print_code('''\
from rpython.rlib.unicodedata.supportcode import (signed_ord, _all_short,
    _all_ushort, _all_int32, _all_uint32, _cjk_prefix, _hangul_prefix,
    _lookup_hangul, _hangul_L, _hangul_V, _hangul_T)''')
    outfile.print_code('')
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
