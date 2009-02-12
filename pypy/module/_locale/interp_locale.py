from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root

from pypy.translator.tool.cbuild import ExternalCompilationInfo

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = ['locale.h']
    )
    lconv = platform.Struct("struct lconv", [
            # Numeric (non-monetary) information.
            ("decimal_point", rffi.CCHARP),    # Decimal point character.
            ("thousands_sep", rffi.CCHARP),    # Thousands separator.

            ## Each element is the number of digits in each group;
            ## elements with higher indices are farther left.
            ## An element with value CHAR_MAX means that no further grouping is done.
            ## An element with value 0 means that the previous element is used
            ## for all groups farther left.  */
            ("grouping", rffi.CCHARP),

            ## Monetary information.

            ## First three chars are a currency symbol from ISO 4217.
            ## Fourth char is the separator.  Fifth char is '\0'.
            ("int_curr_symbol", rffi.CCHARP),
            ("currency_symbol", rffi.CCHARP),   # Local currency symbol.
            ("mon_decimal_point", rffi.CCHARP), # Decimal point character.
            ("mon_thousands_sep", rffi.CCHARP), # Thousands separator.
            ("mon_grouping", rffi.CCHARP),      # Like `grouping' element (above).
            ("positive_sign", rffi.CCHARP),     # Sign for positive values.
            ("negative_sign", rffi.CCHARP),     # Sign for negative values.
            ("int_frac_digits", rffi.UCHAR),    # Int'l fractional digits.

            ("frac_digits", rffi.CHAR),        # Local fractional digits.
            ## 1 if currency_symbol precedes a positive value, 0 if succeeds.
            ("p_cs_precedes", rffi.CHAR),
            ## 1 iff a space separates currency_symbol from a positive value.
            ("p_sep_by_space", rffi.CHAR),
            ## 1 if currency_symbol precedes a negative value, 0 if succeeds.
            ("n_cs_precedes", rffi.CHAR),
            ## 1 iff a space separates currency_symbol from a negative value.
            ("n_sep_by_space", rffi.CHAR),

            ## Positive and negative sign positions:
            ## 0 Parentheses surround the quantity and currency_symbol.
            ## 1 The sign string precedes the quantity and currency_symbol.
            ## 2 The sign string follows the quantity and currency_symbol.
            ## 3 The sign string immediately precedes the currency_symbol.
            ## 4 The sign string immediately follows the currency_symbol.
            ("p_sign_posn", rffi.CHAR),
            ("n_sign_posn", rffi.CHAR),
            ])


constants = {}
constant_names = (
        'LC_CTYPE',
        'LC_NUMERIC',
        'LC_TIME',
        'LC_COLLATE',
        'LC_MONETARY',
        'LC_MESSAGES',
        'LC_ALL',
        'LC_PAPER',
        'LC_NAME',
        'LC_ADDRESS',
        'LC_TELEPHONE',
        'LC_MEASUREMENT',
        'LC_IDENTIFICATION',
        )

for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

class cConfig(object):
    pass

for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)

# needed to export the constants inside and outside. see __init__.py
for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value

locals().update(constants)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=CConfig._compilation_info_)

def setlocale(space, w_category, w_locale):
    pass

setlocale.unwrap_spec = [ObjSpace, W_Root, W_Root]

_lconv = lltype.Ptr(cConfig.lconv)
_localeconv = external('localeconv', [], _lconv)

def localeconv(space):
    lp = _localeconv()

    # hopefully, the localeconv result survives the C library calls
    # involved herein

    # Numeric information
    result = {
        "decimal_point": rffi.charp2str(lp.c_decimal_point),
        #"thousands_sep": rffi.getintfield(lp, "c_thousands_sep"),
        #"grouping": rffi.getintfield(lp, "c_grouping"), #_copy_grouping(l.grouping)),
        #"int_curr_symbol": rffi.getintfield(lp, "c_int_curr_symbol"),
        #"currency_symbol": rffi.getintfield(lp, "c_currency_symbol"),
        #"mon_decimal_point": rffi.getintfield(lp, "c_mon_decimal_point"),
        #"mon_thousands_sep": rffi.getintfield(lp, "c_mon_thousands_sep"),
        #"mon_grouping": rffi.getintfield(lp, "c_mon_grouping"), #_copy_grouping(l.mon_grouping)),
        #"positive_sign": rffi.getintfield(lp, "c_positive_sign"),
        #"negative_sign": rffi.getintfield(lp, "c_negative_sign"),
        #"int_frac_digits": rffi.getintfield(lp, "c_int_frac_digits"),
        #"frac_digits": rffi.getintfield(lp, "c_frac_digits"),
        #"p_cs_precedes": rffi.getintfield(lp, "c_p_cs_precedes"),
        #"p_sep_by_space": rffi.getintfield(lp, "c_p_sep_by_space"),
        #"n_cs_precedes": rffi.getintfield(lp, "c_n_cs_precedes"),
        #"n_sep_by_space": rffi.getintfield(lp, "c_n_sep_by_space"),
        #"p_sign_posn": rffi.getintfield(lp, "c_p_sign_posn"),
        #"n_sign_posn": rffi.getintfield(lp, "c_n_sign_posn"),
    }
    return space.wrap(result)

localeconv.unwrap_spec = [ObjSpace]

