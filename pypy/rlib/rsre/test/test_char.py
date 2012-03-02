from pypy.rlib.rsre import rsre_char
from pypy.rlib.rsre.rsre_char import SRE_FLAG_LOCALE, SRE_FLAG_UNICODE

def setup_module(mod):
    from pypy.module.unicodedata import unicodedb
    rsre_char.set_unicode_db(unicodedb)

UPPER_PI = 0x3a0
LOWER_PI = 0x3c0
INDIAN_DIGIT = 0x966
ROMAN_NUMERAL = 0x2165
FULLWIDTH_DIGIT = 0xff10
CIRCLED_NUMBER = 0x32b4
DINGBAT_CIRCLED = 0x2781
EM_SPACE = 0x2001
LINE_SEP = 0x2028

# XXX very incomplete test

def test_getlower():
    assert rsre_char.getlower(ord('A'), 0) == ord('a')
    assert rsre_char.getlower(ord('2'), 0) == ord('2')
    assert rsre_char.getlower(10, 0) == 10
    assert rsre_char.getlower(UPPER_PI, 0) == UPPER_PI
    #
    assert rsre_char.getlower(ord('A'), SRE_FLAG_UNICODE) == ord('a')
    assert rsre_char.getlower(ord('2'), SRE_FLAG_UNICODE) == ord('2')
    assert rsre_char.getlower(10, SRE_FLAG_UNICODE) == 10
    assert rsre_char.getlower(UPPER_PI, SRE_FLAG_UNICODE) == LOWER_PI
    #
    # xxx the following cases are like CPython's.  They are obscure.
    # (iko) that's a nice way to say "broken"
    assert rsre_char.getlower(UPPER_PI, SRE_FLAG_LOCALE) == UPPER_PI
    assert rsre_char.getlower(UPPER_PI, SRE_FLAG_LOCALE | SRE_FLAG_UNICODE) \
                                                         == UPPER_PI

def test_is_word():
    assert rsre_char.is_word(ord('A'))
    assert rsre_char.is_word(ord('_'))
    assert not rsre_char.is_word(UPPER_PI)
    assert not rsre_char.is_word(LOWER_PI)
    assert not rsre_char.is_word(ord(','))
    #
    assert rsre_char.is_uni_word(ord('A'))
    assert rsre_char.is_uni_word(ord('_'))
    assert rsre_char.is_uni_word(UPPER_PI)
    assert rsre_char.is_uni_word(LOWER_PI)
    assert not rsre_char.is_uni_word(ord(','))

def test_category():
    from sre_constants import CHCODES
    cat = rsre_char.category_dispatch
    #
    assert     cat(CHCODES["category_digit"], ord('1'))
    assert not cat(CHCODES["category_digit"], ord('a'))
    assert not cat(CHCODES["category_digit"], INDIAN_DIGIT)
    #
    assert not cat(CHCODES["category_not_digit"], ord('1'))
    assert     cat(CHCODES["category_not_digit"], ord('a'))
    assert     cat(CHCODES["category_not_digit"], INDIAN_DIGIT)
    #
    assert not cat(CHCODES["category_space"], ord('1'))
    assert not cat(CHCODES["category_space"], ord('a'))
    assert     cat(CHCODES["category_space"], ord(' '))
    assert     cat(CHCODES["category_space"], ord('\n'))
    assert     cat(CHCODES["category_space"], ord('\t'))
    assert     cat(CHCODES["category_space"], ord('\r'))
    assert     cat(CHCODES["category_space"], ord('\v'))
    assert     cat(CHCODES["category_space"], ord('\f'))
    assert not cat(CHCODES["category_space"], EM_SPACE)
    #
    assert     cat(CHCODES["category_not_space"], ord('1'))
    assert     cat(CHCODES["category_not_space"], ord('a'))
    assert not cat(CHCODES["category_not_space"], ord(' '))
    assert not cat(CHCODES["category_not_space"], ord('\n'))
    assert not cat(CHCODES["category_not_space"], ord('\t'))
    assert not cat(CHCODES["category_not_space"], ord('\r'))
    assert not cat(CHCODES["category_not_space"], ord('\v'))
    assert not cat(CHCODES["category_not_space"], ord('\f'))
    assert     cat(CHCODES["category_not_space"], EM_SPACE)
    #
    assert     cat(CHCODES["category_word"], ord('l'))
    assert     cat(CHCODES["category_word"], ord('4'))
    assert     cat(CHCODES["category_word"], ord('_'))
    assert not cat(CHCODES["category_word"], ord(' '))
    assert not cat(CHCODES["category_word"], ord('\n'))
    assert not cat(CHCODES["category_word"], LOWER_PI)
    #
    assert not cat(CHCODES["category_not_word"], ord('l'))
    assert not cat(CHCODES["category_not_word"], ord('4'))
    assert not cat(CHCODES["category_not_word"], ord('_'))
    assert     cat(CHCODES["category_not_word"], ord(' '))
    assert     cat(CHCODES["category_not_word"], ord('\n'))
    assert     cat(CHCODES["category_not_word"], LOWER_PI)
    #
    assert     cat(CHCODES["category_linebreak"], ord('\n'))
    assert not cat(CHCODES["category_linebreak"], ord(' '))
    assert not cat(CHCODES["category_linebreak"], ord('s'))
    assert not cat(CHCODES["category_linebreak"], ord('\r'))
    assert not cat(CHCODES["category_linebreak"], LINE_SEP)
    #
    assert     cat(CHCODES["category_uni_linebreak"], ord('\n'))
    assert not cat(CHCODES["category_uni_linebreak"], ord(' '))
    assert not cat(CHCODES["category_uni_linebreak"], ord('s'))
    assert     cat(CHCODES["category_uni_linebreak"], LINE_SEP)
    #
    assert not cat(CHCODES["category_not_linebreak"], ord('\n'))
    assert     cat(CHCODES["category_not_linebreak"], ord(' '))
    assert     cat(CHCODES["category_not_linebreak"], ord('s'))
    assert     cat(CHCODES["category_not_linebreak"], ord('\r'))
    assert     cat(CHCODES["category_not_linebreak"], LINE_SEP)
    #
    assert not cat(CHCODES["category_uni_not_linebreak"], ord('\n'))
    assert     cat(CHCODES["category_uni_not_linebreak"], ord(' '))
    assert     cat(CHCODES["category_uni_not_linebreak"], ord('s'))
    assert not cat(CHCODES["category_uni_not_linebreak"], LINE_SEP)
    #
    assert     cat(CHCODES["category_uni_digit"], INDIAN_DIGIT)
    assert     cat(CHCODES["category_uni_digit"], FULLWIDTH_DIGIT)
    assert not cat(CHCODES["category_uni_digit"], ROMAN_NUMERAL)
    assert not cat(CHCODES["category_uni_digit"], CIRCLED_NUMBER)
    assert not cat(CHCODES["category_uni_digit"], DINGBAT_CIRCLED)
    #
    assert not cat(CHCODES["category_uni_not_digit"], INDIAN_DIGIT)
    assert not cat(CHCODES["category_uni_not_digit"], FULLWIDTH_DIGIT)
    assert     cat(CHCODES["category_uni_not_digit"], ROMAN_NUMERAL)
    assert     cat(CHCODES["category_uni_not_digit"], CIRCLED_NUMBER)
    assert     cat(CHCODES["category_uni_not_digit"], DINGBAT_CIRCLED)
