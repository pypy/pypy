#!/usr/bin/env python

import pprint

MAXUNICODE = 0x10FFFF     # the value of sys.maxunicode of wide Python builds

MANDATORY_LINE_BREAKS = ["BK", "CR", "LF", "NL"] # line break categories

class Fraction:
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator

    def __repr__(self):
        return '%r / %r' % (self.numerator, self.denominator)

    def __str__(self):
        return repr(self)

class Unicodechar:
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
        uc = Unicodechar()
        uc.__dict__.update(self.__dict__)
        return uc
        
def get_compat_decomposition(table, code):
    if not table[code].decomposition:
        return [code]
    if not table[code].compat_decomp:
        result = []
        for decomp in table[code].decomposition:
            result.extend(get_compat_decomposition(table, decomp))
        table[code].compat_decomp = result
    return table[code].compat_decomp

def get_canonical_decomposition(table, code):
    if not table[code].decomposition or table[code].isCompatibility:
        return [code]
    if not table[code].canonical_decomp:
        result = []
        for decomp in table[code].decomposition:
            result.extend(get_canonical_decomposition(table, decomp))
        table[code].canonical_decomp = result
    return table[code].canonical_decomp

def read_unicodedata(unicodedata_file, exclusions_file, east_asian_width_file,
                     unihan_file=None, linebreak_file=None):
    rangeFirst = {}
    rangeLast = {}
    table = [None] * (MAXUNICODE + 1)
    for line in unicodedata_file:
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
        u = Unicodechar(data)
        assert table[code] is None, 'Multiply defined character %04X' % code
        table[code] = u

    # Collect ranges
    ranges = {}
    for name, (start, data) in rangeFirst.iteritems():
        end = rangeLast[name]
        unichar = Unicodechar(['0000', None] + data[2:])
        ranges[(start, end)] = unichar

    # Read exclusions
    for line in exclusions_file:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        table[int(line, 16)].excluded = True

    # Read line breaks
    for line in linebreak_file:
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
            table[char].linebreak = True

    # Read east asian width
    for line in east_asian_width_file:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        code, width = line.split(';')
        if '..' in code:
            first, last = map(lambda x:int(x,16), code.split('..'))
            try:
                ranges[(first, last)].east_asian_width = width
            except KeyError:
                ch = Unicodechar(['0000', None, 'Cn'] + [''] * 12)
                ch.east_asian_width = width
                ranges[(first, last)] = ch
        else:
            table[int(code, 16)].east_asian_width = width

    # Expand ranges
    for (first, last), char in ranges.iteritems():
        for code in range(first, last + 1):
            assert table[code] is None, 'Multiply defined character %04X' % code

            table[code] = char

    defaultChar = Unicodechar(['0000', None, 'Cn'] + [''] * 12)
    for code in range(len(table)):
        if table[code] is None:
            table[code] = defaultChar
            
    extra_numeric = read_unihan(unihan_file)
    for code, value in extra_numeric.iteritems():
        uc = table[code].copy()
        uc.numeric = value
        table[code] = uc
        
    # Compute full decompositions.
    for code in range(len(table)):
        get_canonical_decomposition(table, code)
        get_compat_decomposition(table, code)

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

def writeDict(outfile, name, dictionary, base_mod):
    if base_mod:
        base_dict = getattr(base_mod, name)
    else:
        base_dict = {}
    print >> outfile, '%s = {' % name
    items = dictionary.items()
    items.sort()
    for key, value in items:
        if key not in base_dict or base_dict[key] != value:
            print >> outfile, '%r: %r,'%(key, dictionary[key])
    print >> outfile, '}'
    print >> outfile
    print >> outfile, '%s_corrected = {' % name
    for key in sorted(base_dict):
        if key not in dictionary:
            print >> outfile, '%r: None,' % key
    print >> outfile, '}'


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

def writeDbRecord(outfile, table):
    pgbits = 8
    chunksize = 64
    pgsize = 1 << pgbits
    bytemask = ~(-1 << pgbits)
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
    # Create the records
    db_records = {}
    for code in range(len(table)):
        char = table[code]
        flags = 0
        if char.category == "Zs" or char.bidirectional in ("WS", "B", "S"):
            flags |= IS_SPACE
        if char.category in ("Lm", "Lt", "Lu", "Ll", "Lo"):
            flags |= IS_ALPHA
        if char.linebreak or char.bidirectional == "B":
            flags |= IS_LINEBREAK
        if char.numeric is not None:
            flags |= IS_NUMERIC
        if char.digit is not None:
            flags |= IS_DIGIT
        if char.decimal is not None:
            flags |= IS_DECIMAL
        if char.category == "Lu":
            flags |= IS_UPPER
        if char.category == "Lt":
            flags |= IS_TITLE
        if char.category == "Ll":
            flags |= IS_LOWER
        if char.mirrored:
            flags |= IS_MIRRORED
        char.db_record = (char.category, char.bidirectional, char.east_asian_width, flags, char.combining)
        db_records[char.db_record] = 1
    db_records = db_records.keys()
    db_records.sort()
    print >> outfile, '_db_records = ['
    for record in db_records:
        print >> outfile, '%r,'%(record,)
    print >> outfile, ']'
    print >> outfile, '_db_pgtbl = ('
    pages = []
    line = []
    for i in range(0, len(table), pgsize):
        result = []
        for char in table[i:i + pgsize]:
            result.append(chr(db_records.index(char.db_record)))
        categorytbl = ''.join(result)
        try:
            page = pages.index(categorytbl)
        except ValueError:
            page = len(pages)
            pages.append(categorytbl)
            assert len(pages) < 256, 'Too many unique pages for db_record.'
        line.append(chr(page))
        if len(line) >= chunksize:
            print >> outfile, repr(''.join(line))
            line = []
    if len(line) > 0:
        print >> outfile, repr(''.join(line))
    print >> outfile, ')'
    # Dump pgtbl
    print >> outfile, '_db_pages = ( '
    for page_string in pages:
        for index in range(0, len(page_string), chunksize):
            print >> outfile, repr(page_string[index:index + chunksize])
    print >> outfile, ')'
    print >> outfile, '''
def _get_record(code):
    return _db_records[ord(_db_pages[(ord(_db_pgtbl[code >> %d]) << %d) + (code & %d)])]
'''%(pgbits, pgbits, bytemask)
    print >> outfile, 'def category(code): return _get_record(code)[0]'
    print >> outfile, 'def bidirectional(code): return _get_record(code)[1]'
    print >> outfile, 'def east_asian_width(code): return _get_record(code)[2]'
    print >> outfile, 'def isspace(code): return _get_record(code)[3] & %d != 0'% IS_SPACE
    print >> outfile, 'def isalpha(code): return _get_record(code)[3] & %d != 0'% IS_ALPHA
    print >> outfile, 'def islinebreak(code): return _get_record(code)[3] & %d != 0'% IS_LINEBREAK
    print >> outfile, 'def isnumeric(code): return _get_record(code)[3] & %d != 0'% IS_NUMERIC
    print >> outfile, 'def isdigit(code): return _get_record(code)[3] & %d != 0'% IS_DIGIT
    print >> outfile, 'def isdecimal(code): return _get_record(code)[3] & %d != 0'% IS_DECIMAL
    print >> outfile, 'def isalnum(code): return _get_record(code)[3] & %d != 0'% (IS_ALPHA | IS_NUMERIC)
    print >> outfile, 'def isupper(code): return _get_record(code)[3] & %d != 0'% IS_UPPER
    print >> outfile, 'def istitle(code): return _get_record(code)[3] & %d != 0'% IS_TITLE
    print >> outfile, 'def islower(code): return _get_record(code)[3] & %d != 0'% IS_LOWER
    print >> outfile, 'def iscased(code): return _get_record(code)[3] & %d != 0'% (IS_UPPER | IS_TITLE | IS_LOWER)
    print >> outfile, 'def mirrored(code): return _get_record(code)[3] & %d != 0'% IS_MIRRORED
    print >> outfile, 'def combining(code): return _get_record(code)[4]'

def write_character_names(outfile, table, base_mod):

    import triegenerator

    names = dict((table[code].name,code) for code in range(len(table)) if table[code].name)
    sorted_names_codes = sorted(names.iteritems())

    if base_mod is None:
        triegenerator.build_compression_tree(outfile, names)
        print >> outfile, "# the following dictionary is used by modules that take this as a base"
        print >> outfile, "_orig_names = {"
        for name, code in sorted_names_codes:
            print >> outfile, "%r: %r," % (name, code)
        print >> outfile, "}"
    else:
        print >> outfile, '_names = {'
        for name, code in sorted_names_codes:
            try:
                if base_mod.lookup_charcode(code) == name:
                    continue
            except KeyError:
                pass
            print >> outfile, '%r: %r,' % (code, name)
        print >> outfile, '}'

        
        print >> outfile, '_names_corrected = {'
        for name, code in sorted(base_mod._orig_names.iteritems()):
            if name not in names:
                print >> outfile, '%r: None,' % code
        print >> outfile, '}'

        print >> outfile, '_code_by_name = {'
        corrected = {}
        for name, code in sorted_names_codes:
            try:
                if base_mod.lookup_charcode(code) == name:
                    continue
            except KeyError:
                pass
            print >> outfile, '%r: %r,' % (name, code)
        print >> outfile, '}'

        print >> outfile, '_code_by_name_corrected = {'
        for name, code in sorted(base_mod._orig_names.iteritems()):
            if name not in names:
                print >> outfile, '%r: None,' % name
        print >> outfile, '}'

    
def writeUnicodedata(version, table, outfile, base):
    if base:
        print >> outfile, 'import %s as base_mod' % base
        base_mod = __import__(base)
    else:
        print >> outfile, 'base_mod = None'
        base_mod = None
    # Version
    print >> outfile, 'version = %r' % version
    print >> outfile

    cjk_end = 0x9FA5
    if version >= "4.1":
        cjk_end = 0x9FBB

    write_character_names(outfile, table, base_mod)
    
    print >> outfile, '''
_cjk_prefix = "CJK UNIFIED IDEOGRAPH-"
_hangul_prefix = 'HANGUL SYLLABLE '

_hangul_L = ['G', 'GG', 'N', 'D', 'DD', 'R', 'M', 'B', 'BB',
            'S', 'SS', '', 'J', 'JJ', 'C', 'K', 'T', 'P', 'H']
_hangul_V = ['A', 'AE', 'YA', 'YAE', 'EO', 'E', 'YEO', 'YE', 'O', 'WA', 'WAE',
            'OE', 'YO', 'U', 'WEO', 'WE', 'WI', 'YU', 'EU', 'YI', 'I']
_hangul_T = ['', 'G', 'GG', 'GS', 'N', 'NJ', 'NH', 'D', 'L', 'LG', 'LM',
            'LB', 'LS', 'LT', 'LP', 'LH', 'M', 'B', 'BS', 'S', 'SS',
            'NG', 'J', 'C', 'K', 'T', 'P', 'H']

def _lookup_hangul(syllables):
    l_code = v_code = t_code = -1
    for i in range(len(_hangul_L)):
        jamo = _hangul_L[i]
        if (syllables[:len(jamo)] == jamo and
            (l_code < 0 or len(jamo) > len(_hangul_L[l_code]))):
            l_code = i
    if l_code < 0:
        raise KeyError
    start = len(_hangul_L[l_code])

    for i in range(len(_hangul_V)):
        jamo = _hangul_V[i]
        if (syllables[start:start + len(jamo)] == jamo and
            (v_code < 0 or len(jamo) > len(_hangul_V[v_code]))):
            v_code = i
    if v_code < 0:
        raise KeyError
    start += len(_hangul_V[v_code])

    for i in range(len(_hangul_T)):
        jamo = _hangul_T[i]
        if (syllables[start:start + len(jamo)] == jamo and
            (t_code < 0 or len(jamo) > len(_hangul_T[t_code]))):
            t_code = i
    if t_code < 0:
        raise KeyError
    start += len(_hangul_T[t_code])

    if len(syllables[start:]):
        raise KeyError
    return 0xAC00 + (l_code * 21 + v_code) * 28 + t_code

def _lookup_cjk(cjk_code):
    if len(cjk_code) != 4 and len(cjk_code) != 5:
        raise KeyError
    for c in cjk_code:
        if not ('0' <= c <= '9' or 'A' <= c <= 'F'):
            raise KeyError
    code = int(cjk_code, 16)
    if (0x3400 <= code <= 0x4DB5 or
        0x4E00 <= code <= 0x%X or
        0x20000 <= code <= 0x2A6D6):
        return code
    raise KeyError

def lookup(name):
    if name[:len(_cjk_prefix)] == _cjk_prefix:
        return _lookup_cjk(name[len(_cjk_prefix):])
    if name[:len(_hangul_prefix)] == _hangul_prefix:
        return _lookup_hangul(name[len(_hangul_prefix):])

    if not base_mod:
        return trie_lookup(name)
    else:
        try:
            return _code_by_name[name]
        except KeyError:
            if name not in _code_by_name_corrected:
                return base_mod.trie_lookup(name)
            else:
                raise

def name(code):
    if (0x3400 <= code <= 0x4DB5 or
        0x4E00 <= code <= 0x%X or
        0x20000 <= code <= 0x2A6D6):
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
    
    if not base_mod:
        return lookup_charcode(code)
    else:
        try:
            return _names[code]
        except KeyError:
            if code not in _names_corrected:
                return base_mod.lookup_charcode(code)
            else:
                raise
''' % (cjk_end, cjk_end)

    # Categories
    writeDbRecord(outfile, table)
        # Numeric characters
    decimal = {}
    digit = {}
    numeric = {}
    for code in range(len(table)):
        if table[code].decimal is not None:
            decimal[code] = table[code].decimal
        if table[code].digit is not None:
            digit[code] = table[code].digit
        if table[code].numeric is not None:
            numeric[code] = table[code].numeric
            
    writeDict(outfile, '_decimal', decimal, base_mod)
    writeDict(outfile, '_digit', digit, base_mod)
    writeDict(outfile, '_numeric', numeric, base_mod)
    print >> outfile, '''
def decimal(code):
    try:
        return _decimal[code]
    except KeyError:
        if base_mod is not None and code not in _decimal_corrected:
            return base_mod._decimal[code]
        else:
            raise

def digit(code):
    try:
        return _digit[code]
    except KeyError:
        if base_mod is not None and code not in _digit_corrected:
            return base_mod._digit[code]
        else:
            raise

def numeric(code):
    try:
        return _numeric[code]
    except KeyError:
        if base_mod is not None and code not in _numeric_corrected:
            return base_mod._numeric[code]
        else:
            raise
'''
    # Case conversion
    toupper = {}
    tolower = {}
    totitle = {}
    for code in range(len(table)):
        if table[code].upper:
            toupper[code] = table[code].upper
        if table[code].lower:
            tolower[code] = table[code].lower
        if table[code].title:
            totitle[code] = table[code].title
    writeDict(outfile, '_toupper', toupper, base_mod)
    writeDict(outfile, '_tolower', tolower, base_mod)
    writeDict(outfile, '_totitle', totitle, base_mod)
    print >> outfile, '''
def toupper(code):
    try:
        return _toupper[code]
    except KeyError:
        if base_mod is not None and code not in _toupper_corrected:
            return base_mod._toupper.get(code, code)
        else:
            return code

def tolower(code):
    try:
        return _tolower[code]
    except KeyError:
        if base_mod is not None and code not in _tolower_corrected:
            return base_mod._tolower.get(code, code)
        else:
            return code

def totitle(code):
    try:
        return _totitle[code]
    except KeyError:
        if base_mod is not None and code not in _totitle_corrected:
            return base_mod._totitle.get(code, code)
        else:
            return code
'''
    # Decomposition
    decomposition = {}
    for code in range(len(table)):
        if table[code].raw_decomposition:
            decomposition[code] = table[code].raw_decomposition
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
    for code in range(len(table)):
        unichar = table[code]
        if (not unichar.decomposition or
            unichar.isCompatibility or
            unichar.excluded or
            len(unichar.decomposition) != 2 or
            table[unichar.decomposition[0]].combining):
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
    for code in range(len(table)):
        if table[code].canonical_decomp:
            decomposition[code] = table[code].canonical_decomp
    writeDict(outfile, '_canon_decomposition', decomposition, base_mod)

    decomposition = {}
    for code in range(len(table)):
        if table[code].compat_decomp:
            decomposition[code] = table[code].compat_decomp
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

def main():
    import re, sys
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
    infile = open('UnicodeData-%s.txt' % options.unidata_version)
    exclusions = open('CompositionExclusions-%s.txt' % options.unidata_version)
    east_asian_width = open('EastAsianWidth-%s.txt' % options.unidata_version)
    unihan = open('UnihanNumeric-%s.txt' % options.unidata_version)
    linebreak = open('LineBreak-%s.txt' % options.unidata_version)

    table = read_unicodedata(infile, exclusions, east_asian_width, unihan,
                             linebreak)
    print >> outfile, '# UNICODE CHARACTER DATABASE'
    print >> outfile, '# This file was generated with the command:'
    print >> outfile, '#    ', ' '.join(sys.argv)
    print >> outfile
    print >> outfile, 'from pypy.rlib.rarithmetic import r_longlong'
    print >> outfile
    print >> outfile
    writeUnicodedata(options.unidata_version, table, outfile, options.base)

if __name__ == '__main__':
    main()
