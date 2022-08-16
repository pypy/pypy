# UNICODE CHARACTER DATABASE
# # This file was generated with the command:
# #    generate_unicodedb.py --unidata_version=5.2.0 --output=unicodedb_5_2_0 --base=unicodedb_3_2_0

from rpython.rlib.rarithmetic import r_longlong, r_int32, r_uint32, intmask
from rpython.rlib.unicodedata.supportcode import (signed_ord, _all_short,
    _all_ushort, _all_int32, _all_uint32, _cjk_prefix, _hangul_prefix,
    _lookup_hangul, _hangul_L, _hangul_V, _hangul_T)

import unicodedb_3_2_0 as base_mod
version = '5.2.0'

# ____________________________________________________________
# output from build_compression_dawg
from rpython.rlib.rarithmetic import intmask, r_int32
from rpython.rlib.unicodedata.supportcode import signed_ord, _all_short, _all_ushort, _all_int32, _all_uint32
from rpython.rlib.unicodedata.dawg import _lookup as _dawg_lookup, _inverse_lookup
packed_dawg = (
'\xcc\x82\x01'
 '\x8a\xa9\x0bA'
 '\x92IB'
 '\x9a\xa8}C'
 '\xcagD'
 '\xc2\xa3\x7fE'
 '\xeeyF'
 '\xaeAG'
 '\xf6\xba\x7fH'
 '\xaarI'
 '\xf2kJ'
 '\xd2UK'
 '\xd2\xd6~L'
 '\xee\x97\x7fM'
 '\xb2bN'
 '\xbaVO'
 '\xfaSP'
 '\x90\xfc}\x07QUINCUN'
 '\xde\xda\x01R'
 '\xbe\xac\x7fS'
 '\xea\x85\x7fT'
 '\xcatU'
 '\xceMV'
 '\xa6nW'
 '\x95\x7f\x10YI SYLLABLE ITER'
'\x02'
 '\x0bA'
'\x02'
 '\x0bT'
'\x02'
 '\x15\x03ION'
'\x02'
 '\x11\x02 M'
'\x02'
 '\x11\x02AR'
'\x02'
 '\x0bK'
'\x03\x00'
'2'
 '\xf6\x0fA'
 '\xaeqH'
 'Q\x14ORD SEPARATOR MIDDLE'
'\x02'
 '\x11\x02 D'
'\x02'
 '\x0bO'
'\x02'
 '\xe3~T'
','
 '\x94\x0e\x08EELCHAIR'
 '\xb5r\x04ITE '
'*'
 '\x96\x0cD'
 '\xd8~\x04FLAG'
 '\xbe\x7fH'
 '\x8e\x7fL'
 '\x9c\x7f\x06MEDIUM'
 '\xba\x7fP'
 '\xb6\x7fR'
 '\x90\x7f\x06SMALL '
 '\xce|T'
 '\xa3~V'
'\x04'
 '\x11\x02ER'
'\x04'
 '\x90\x01\x03TIC'
 '\xb1\x7f\x07Y SMALL'
'\x02'
 '\x11\x02 S'
'\x02'
 '\x11\x02QU'
'\x02'
 '\x0bA'
'\x02'
 '\x0bR'
'\x02'
 '\xb3{E'
'\x02'
 ')\x08AL ELLIP'
'\x02'
 'CS'
'\x06'
 '\x9e\x01R'
 '\xff~W'
'\x02'
 '\x0bO'
'\x02'
 '\xd9\x00\x13-WAY LEFT WAY TRAFF'
'\x02'
 '\x0bI'
'\x02'
 '\xdbyC'
'\x04'
 '\xe8\x01\x04APEZ'
 '\xb5\x7f\x1dIANGLE CONTAINING SMALL WHITE'
'\x02'
 '\x19\x04 TRI'
'\x02'
 '\x11\x02AN'
'\x02'
 '\x0bG'
'\x02'
 '\xbb|L'
'\x02'
 '\x0bI'
'\x02'
 '\x0bU'
'\x02'
 '\xc7wM'
'\x04'
 ':L'
 '[S'
'\x02'
 '\x0bT'
'\x02'
 '\x0bA'
'\x02'
 '\x8bwR'
'\x02'
 '\x15\x03OZE'
'\x02'
 '\x0bN'
'\x02'
 '\xa3{G'
'\x02'
 '\xc9\x00\x0fIGHT-POINTING P'
'\x02'
 '\x15\x03ENT'
'\x02'
 '\x11\x02AG'
'\x02'
 '\x0bO'
'\x02'
 '\xc3uN'
'\x06'
 '\x0b '
'\x06'
 '\x1eD'
 '\x8e~L'
 '[S'
'\x02'
 '\x19\x04IAMO'
'\x02'
 '\x0bN'
'\x02'
 '\xdftD'
'\x04'
 '\xd8x\x04ARGE'
 '\xd3\x07E'
'\x02'
 '-\tFT LANE M'
'\x02'
 '\x99}\x02ER'
'\x04'
 '2E'
 '\x85x\x07ORIZONT'
'\x02'
 '\xc3}X'
'\x05'
 '\x95\x01" WITH HORIZONTAL MIDDLE BLACK STRI'
'\x02'
 '\xcbvP'
'\x06'
 '\xf8u\tIAMOND IN'
 '\xc7\nR'
'\x04'
 '%\x07AUGHTS '
'\x04'
 '"K'
 'sM'
'\x02'
 '\xaf{A'
'\x02'
 '\x0bI'
'\x02'
 '\x0bN'
'\x02'
 '\xcbpG'
'\x02'
 '\x1d\x05 SYMB'
'\x02'
 '\x0bO'
'\x02'
 '\x8fpL'
'\x04'
 '\xb0\x01\x05RNING'
 'i\x1cVE ARROW POINTING DIRECTLY L'
'\x02'
 '\xfdo\x02EF'
'\x02'
 '\x0b '
'\x02'
 '\x0bS'
'\x02'
 '\xedx\x02IG'
'\x92\t'
 '\xf6\x18A'
 '\xceiE'
 '\xa1~\x0fULGAR FRACTION '
'\x08'
 '\xf8\x00\x04ONE '
 '\xbd\x7f\x03ZER'
'\x02'
 '\x1d\x05O THI'
'\x02'
 '\x11\x02RD'
'\x02'
 '\xc7lS'
'\x06'
 '8\x02NI'
 't\x03SEV'
 '\x03T'
'\x02'
 '\x0bE'
'\x02'
 '\x0bN'
'\x02'
 '\x0bT'
'\x02'
 '\xe3kH'
'R'
 '\xb8\x04\x04DIC '
 '\xb0|\x07RTICAL '
 'gS'
'\x02'
 '\x0bT'
'\x02'
 '\xf7jA'
'\n'
 '\xf0\x02\x11BAR WITH HORIZONT'
 'X\x04FOUR'
 'd\nLINE EXTEN'
 '\xaa\x7fM'
 '[T'
'\x02'
 '\x0bI'
'\x02'
 '\x0bL'
'\x02'
 '\xebmD'
'\x02'
 '\xc5\x00\x0eALE WITH STROK'
'\x02'
 '\xfbyE'
'\x02'
 '\x0bS'
'\x02'
 '\xdbrI'
'\x02'
 '\x15\x03 DO'
'\x02'
 '\xbb{T'
'\x02'
 '\x11\x02AL'
'\x02'
 '\x0b '
'\x02'
 '\x0bS'
'\x02'
 '\x0bT'
'\x02'
 '\x11\x02RO'
'\x02'
 '\xf3kK'
'F'
 '\xd8\t\x05SIGN '
 '\xe9v\x05TONE '
' '
 '\xb8\x05\x0cATHARVAVEDIC'
 '\x90\x01\x06CANDRA'
 '\xa8\x02\x02DO'
 '\xf4~\x02KA'
 'd\x04PREN'
 '\xf0}\x11RIGVEDIC KASHMIRI'
 '\xf4\x01\x02SH'
 '\xa6~T'
 '\xf9|\x0bYAJURVEDIC '
'\x08'
 '\xec\x02\nAGGRAVATED'
 '\x92\x7fI'
 '\xbd\x7f\x1bKATHAKA INDEPENDENT SVARITA'
'\x05'
 '%\x07 SCHROE'
'\x02'
 '\x0bD'
'\x02'
 '\x8bkE'
'\x02'
 '1\nNDEPENDENT'
'\x02'
 '\x11\x02 S'
'\x02'
 '\x15\x03VAR'
'\x02'
 '\xa3vI'
'\x02'
 '\x8d\x7f\x02 I'
'\x06'
 '\xcc\x00\x04HREE'
 '\xf0\x00\x03RIP'
 '\x87\x7fW'
'\x02'
 '\x0bO'
'\x02'
 '\x19\x04 DOT'
'\x02'
 '\x0bS'
'\x02'
 '\x0b '
'\x02'
 '\x0bB'
'\x02'
 '\x11\x02EL'
'\x02'
 '\x0bO'
'\x02'
 '\xcf_W'
'\x02'
 '\x0bL'
'\x02'
 '\xdf}E'
'\x02'
 '\x0bA'
'\x02'
 '\x9ftR'
'\x02'
 '\x0bK'
'\x02'
 '\x83tH'
'\x04'
 '\xec\x00\x03RSH'
 'Q\x07THAKA A'
'\x02'
 '\x11\x02NU'
'\x02'
 '\x91s\x03DAT'
'\x02'
 '\x0bA'
'\x02'
 '\xf7rN'
'\x04'
 '\xd6}T'
 '\xc9\x00\x02UB'
'&'
 '\xca\x05A'
 '\xf8~\x08HEXIFORM'
 '\x16L'
 '\xe4\x00\x07NIHSHVA'
 '\x9a~R'
 'p\x04TIRY'
 '\xc8~\x08VISARGA '
 '\xfd{\x11YAJURVEDIC MIDLIN'
'\n'
 ',\x03ANU'
 '\xc2yS'
 '\xc3\x06U'
'\x04'
 '\x19\x04DATT'
'\x04'
 '\x0bA'
'\x05'
 '\x0b '
'\x02'
 '\x15\x03WIT'
'\x02'
 '\x0bH'
'\x02'
 '\x0b '
'\x02'
 '\x11\x02TA'
'\x02'
 '\xf7iI'
'\x02'
 '\xebYA'
'\x06'
 '\xcc\x01\x10EVERSED VISARGA '
 '\xa1\x7f\x05THANG'
'\x02'
 '\x11\x02 L'
'\x02'
 '\x1d\x05ONG A'
'\x02'
 '\x11\x02NU'
'\x02'
 '\x89y\x02SV'
'\x04'
 '\xeayA'
 '\x17U'
'\x02'
 '\x87mS'
'\x0c'
 '\x80\x01\x08NUSVARA '
 'I\x05RDHAV'
'\x02'
 '\x11\x02IS'
'\x02'
 '\x11\x02AR'
'\x02'
 '\x83lG'
'\n'
 '\xb0\x01\x04ANTA'
 '\x00\x04BAHI'
 'd\tUBHAYATO '
 '\xf1z\nVAMAGOMUKH'
'\x02'
 '\x0bM'
'\x02'
 '\xbfvU'
'\x02'
 'a\x03RGO'
'\xb8\x08'
 '\xf0\x04\x02I '
 '\xf5{\x11RIATION SELECTOR-'
'\xe0\x03'
 '\xa6\x031'
 '\x8a~2'
 '\xaa\x7f3'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x14'
 '\xd6S0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x86\x01'
 '\x9a\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 'B5'
 '\xa2R6'
 '\x027'
 '\x028'
 '\x039'
'\x11'
 '\x9eR0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'\x17'
 '\xdeQ0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\xce\x01'
 '\xaa}0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\xfa\x017'
 '\x028'
 '\x039'
'\xd8\x04'
 '\x92\x14C'
 '\x92}D'
 '\xae\x7fF'
 'bQ'
 '\x95p\x02SY'
'\xbe\x04'
 '\xf4\x02\x07LLABLE '
 '\xd5}\x05MBOL '
'\x1a'
 '\x9a\x02B'
 '\xbe\x7fD'
 'fF'
 'rJ'
 'ZK'
 'fN'
 '_T'
'\x06'
 '\xd2cA'
 '\xa2zI'
 '\x03O'
'\x02'
 '\x0bI'
'\x02'
 '\x9bNI'
'\x04'
 '\x16E'
 '\x9f]U'
'\x02'
 '\x9b]E'
'\x02'
 '\x8b]O'
'\x04'
 '\xdabA'
 '\x87\x1dE'
'\x06'
 '\xde\\A'
 '\xbf#O'
'\x04'
 '\x16-'
 '\xaf\\O'
'\x02'
 '\x83MO'
'\x02'
 '\x9b\\A'
'\xa4\x04'
 '\xea\x03A'
 '\xae~B'
 '\xda\x00C'
 '\xb2\tD'
 '\xfawE'
 '\xda~F'
 '\xa6\x08G'
 '\xaa\x7fH'
 '\xb2yI'
 '\x86\x7fJ'
 '\xc6\x06K'
 '\xfa~L'
 '\xa6\x7fM'
 '\xe2|N'
 'NO'
 '\xf6~P'
 '\x02R'
 '\xaa\x7fS'
 '\x02T'
 '\xd6\x01U'
 '\x86\x7fV'
 '\xd2\x00W'
 '\xb2\x7fY'
 '\xab\x7fZ'
'\x1c'
 '\xc6JA'
 '\xd26E'
 'BH'
 '\xf2II'
 '\x826O'
 '\x83JU'
'\x05'
 '\xffIO'
'\x0e'
 '\xeeIA'
 '\xd26E'
 '\xb2II'
 '\x826O'
 '\x83JU'
'\x05'
 '\xafIE'
'\x1c'
 '*A'
 '.E'
 'VI'
 '\x12O'
 'sU'
'\x05'
 '\xf3HN'
'\t'
 '\xe2HN'
 '\x8f7O'
'\t'
 'RE'
 '\xf7HN'
'Z'
 '\xaeHA'
 '\xc69D'
 '\x8e}E'
 '\xee\x01G'
 '\xc6GI'
 '\x926J'
 'rO'
 '\x82JU'
 '\x936Y'
'\x19'
 '\xfeQA'
 '\x02E'
 '\xb2.G'
 '\xd3QO'
'\x10'
 '\x92GA'
 '\xae9E'
 '\xd6FI'
 '\x826O'
 '\x83JU'
'\x07'
 '\xd2FE'
 '\x03N'
'\x18'
 '\xbaFA'
 '\xd26E'
 '\xb2II'
 '\x86:O'
 '\xffEU'
'\x0f'
 ' \x03LE '
 '\xdbEO'
'\n'
 '\xd2xD'
 '\x8ebF'
 '\x02K'
 '\x02M'
 '\xdb%S'
'\x02'
 '\x9bxO'
'*'
 '\x8eEA'
 '\x926B'
 '\xc2\x00E'
 '@\x02GB'
 '\xf2II'
 '\x826O'
 '\x83JU'
'\x10'
 '\xb2DA'
 '\x8e<E'
 '\xf6CI'
 '\x826O'
 '\x83JU'
'\x07'
 '\xf2CE'
 '\xb9<\x04NGTH'
'\x02'
 '\x0bE'
'\x02'
 '\xa3aN'
'"'
 '\xb6zA'
 'FE'
 '\xb2II'
 '\x826O'
 '\x9e\x07P'
 '\xe7BU'
'\x12'
 '\xeeyA'
 '\xa2\x02E'
 '\xd6FI'
 '\x826O'
 '\x83JU'
'\x18'
 '\xaeyA'
 '\xa2\x02E'
 '\xe2}I'
 '\x92\x07O'
 '\xf3xU'
'\x07'
 '\xe2AN'
 '\x03O'
'"'
 '\xcaAA'
 '\x82?B'
 '\xaezE'
 '\xd6FI'
 '\x826O'
 '\x83JU'
'\x12'
 '\xfe@A'
 '\xae9E'
 '\xd6FI'
 '\x9e>O'
 '\xe7AU'
'*'
 '\xbe@A'
 '\xd26E'
 '\xea~H'
 '\xcaJI'
 '\x826O'
 '\x83JU'
'\x02'
 '\x99\xbf\x7f\x03UES'
'\x02'
 '\x0bU'
'\x02'
 '\x0bL'
'\x02'
 '\x19\x04L ST'
'\x02'
 '\x0bO'
'\x02'
 '\x93\xbf\x7fP'
'\x14'
 '\x0bI'
'\x14'
 '\x19\x04GIT '
'\x14'
 '\xa6\x02E'
 'NF'
 'vN'
 'rO'
 '\xbe\x7fS'
 'NT'
 'gZ'
'\x02'
 '\x0bE'
'\x02'
 '\x83qR'
'\x04'
 '\x16H'
 '\xdfpW'
'\x02'
 '\x0bR'
'\x02'
 '\x9fBE'
'\x04'
 '&E'
 'oI'
'\x02'
 '\xaf\xbd\x7fX'
'\x02'
 '\x0bV'
'\x02'
 '\xcbGE'
'\x02'
 '\xcbAN'
'\x02'
 'oI'
'\x04'
 '"I'
 'sO'
'\x02'
 '\xc3EU'
'\x02'
 '\x8bAV'
'\x02'
 '\xc9\xbd\x7f\x03IGH'
'\x02'
 '\x0bO'
'\x02'
 '\x0bM'
'\x02'
 '\xffPM'
'J'
 '\x98\x04\x08GARITIC '
 '\x80\x7f\x08MBRELLA '
 '\x90H\x14NMARRIED PARTNERSHIP'
 '\x9b6P'
'\x06'
 '\xfc\x00\x07 DOWN B'
 '\xbb\x7fW'
'\x04'
 '\x1d\x05ARDS '
'\x04'
 '\xec\x00\x03ANC'
 '\xbb\x7fB'
'\x02'
 '\x19\x04LACK'
'\x02'
 '\x11\x02 A'
'\x02'
 '\x95Y\x02RR'
'\x02'
 '\xc3YO'
'\x04'
 '\xd8\x00\x02ON'
 '\xa9K\x0eWITH RAIN DROP'
'\x02'
 '\x81C\x05 GROU'
'>'
 '\xec\x00\x07LETTER '
 'GW'
'\x02'
 '\x15\x03ORD'
'\x02'
 '\xd9T\x05 DIVI'
'<'
 '\x86\x06A'
 'rB'
 'ND'
 'FG'
 'p\x02HO'
 '\xe6\xb1\x7fI'
 '\xf2\xcd\x00K'
 '^L'
 'nM'
 'nN'
 '\x86\x7fP'
 '\xec\x00\x02QO'
 'p\x02RA'
 '\x86\x7fS'
 '\xb6\x7fT'
 '\xc6\xb4\x7fU'
 '\xfe2W'
 '\xae\x18Y'
 'gZ'
'\x04'
 '\xeeIE'
 '\x87kU'
'\x02'
 '\xf7\xbf\x7fO'
'\x06'
 '\xde\xb5\x7fE'
 '\xdc\xca\x00\x02HA'
 '\x8b\xb4\x7fO'
'\x02'
 '\x97VN'
'\x08'
 '\xc6\x00A'
 'nH'
 'oS'
'\x02'
 '\xd7\xb3\x7fU'
'\x02'
 '\xff\xbd\x7fI'
'\x04'
 '\xfa\xb7\x7fD'
 '\xab\xc8\x00M'
'\x02'
 '\x93HK'
'\x02'
 '\xffSS'
'\x02'
 '\xf3GP'
'\x02'
 '\x97\xbd\x7fU'
'\x02'
 '\xff\xba\x7fE'
'\x02'
 '\x11\x02AM'
'\x02'
 '\xa7GD'
'\x04'
 '\x16A'
 '\x83GH'
'\x02'
 '\xf7\xb1\x7fF'
'\x05'
 '\xebFT'
'\x04'
 '(\x02AM'
 'sH'
'\x02'
 '\xf3}A'
'\x02'
 '\xafFL'
'\x04'
 '"E'
 'sH'
'\x02'
 '\xf3@A'
'\x02'
 '\xefEL'
'\x02'
 '\xdfEE'
'\x04'
 '\x8e\xbb\x7fI'
 '\xdb\xc2\x00L'
'\xae\x0b'
 '\x82\xc6\x00A'
 '\xf2\\E'
 '\xe2|H'
 '\xdelI'
 '\x92xO'
 'JR'
 '\xd0~\x06URNED '
 '\xbd~\x06WO DOT'
'\x04'
 '\xfa\x00 '
 '\xa3\x7fS'
'\x02'
 '-\t OVER ONE'
'\x02'
 '\x15\x03 DO'
'\x02'
 '\x0bT'
'\x02'
 '\x0b '
'\x02'
 '\x0bP'
'\x02'
 '\x1d\x05UNCTU'
'\x02'
 '\x0bA'
'\x02'
 '\xb7ET'
'\x06'
 '\xe4\x00\x05BLACK'
 '\xf4z\x06SMALL '
 '\x8d\x05\x05WHITE'
'\x02'
 '1\n SHOGI PIE'
'\x02'
 '\x83\xb1\x7fC'
'\x02'
 '\x0bI'
'\x02'
 '\x0bC'
'\x02'
 '\x0bO'
'\x02'
 '\xaf\xb6\x7fL'
'\x1e'
 '\xfe\x04P'
 '\xf9{\x17RTOISE SHELL BRACKETED '
'\x14'
 '\xd0\x01\x16CJK UNIFIED IDEOGRAPH-'
 'm\x14LATIN CAPITAL LETTER'
'\x02'
 '\xeb\xbc\x7f '
'\x12'
 '\x90\x02\x024E'
 'N5'
 '\xa6\x7f6'
 '\xb7\x7f7'
'\x04'
 '4\x020B'
 'm\x026D'
'\x02'
 '\xc3\xa8\x7f7'
'\x02'
 '\xaf\xa8\x7f9'
'\x06'
 '\xc4\x00\x0225'
 'r5'
 '\x89\xae\x7f\x0272'
'\x02'
 '\x9f\x7f5'
'\x02'
 '\xd3\xa7\x7f3'
'\x04'
 '\xdc\xb2\x7f\x022D'
 '\xb1\xcc\x00\x02B8'
'\x04'
 '\xda~0'
 '\xd7\xae\x7f8'
'\n'
 '\x0b '
'\n'
 '\xa8\x01\x05CURLY'
 '\xc0\x00\x03LEF'
 '*P'
 'X\x04RIGH'
 '\xff~T'
'\x02'
 '\xc1\x00\rORTOISE SHELL'
'\x02'
 '\x1d\x05 BRAC'
'\x02'
 '\x0bK'
'\x02'
 '\xa3\xa6\x7fE'
'\x02'
 '\xbd\x7f\x06T HALF'
'\x02'
 '!\x06ARENTH'
'\x02'
 '\x0bE'
'\x02'
 '\x0bS'
'\x02'
 '\xc7\xb7\x7fI'
'\x8a\x01'
 '\xa8\r\x06BETAN '
 '\xe8v\x07FINAGH '
 '\xa8}\x04LDE '
 'A\x02NY'
'\x02'
 '!\x06 TWO D'
'\x02'
 '\xd9s\x03OTS'
'\x08'
 '\xec\x01\x08OPERATOR'
 '\xe1~\x05WITH '
'\x06'
 '\xe6\x00D'
 '\xb7\x7fR'
'\x02'
 '\x15\x03ING'
'\x02'
 '\x0b '
'\x02'
 '\x0bA'
'\x02'
 '\x0bB'
'\x02'
 '\xd3dO'
'\x04'
 '\x11\x02OT'
'\x04'
 '\x0b '
'\x04'
 'BA'
 '\xb3AB'
'\x02'
 ')\x08 ABOVE L'
'\x02'
 '\x11\x02EF'
'\x02'
 '\x81g\x06TWARDS'
'n'
 '\xa4\x01\x07LETTER '
 ']\x14MODIFIER LETTER LABI'
'\x02'
 '\xf9\x9d\x7f\x04ALIZ'
'l'
 '\xf6\x06A'
 'd\x11BERBER ACADEMY YA'
 '\x8e~T'
 '\x8f|Y'
'R'
 '\xc2\x00A'
 'nE'
 '\x9a\x9d\x7fI'
 '\x03U'
'\x02'
 '\x97\x9d\x7fY'
'M'
 '\x82\x9d\x7fA'
 '\xfe\xe5\x00B'
 '\xa2\xae\x7fC'
 '\xf6\xd1\x00D'
 '\xf2\x99\x7fF'
 '\xf2\xe5\x00G'
 '\x0eH'
 '\x86\x9a\x7fJ'
 '\xf2\xe5\x00K'
 '\x92\x9a\x7fL'
 '\x02M'
 '\x02N'
 '\x02P'
 '\x02Q'
 '\xde\xe5\x00R'
 'fS'
 'fT'
 '\xde\x9a\x7fV'
 '\x02W'
 '\x02Y'
 '\x8b\xe5\x00Z'
'\x07'
 '\xf6\x9a\x7fH'
 '\x03Z'
'\x07'
 '\xda\x9a\x7fH'
 '\x03T'
'\x07'
 '\xbe\x9a\x7fH'
 '\x03S'
'\x05'
 '\xa3\x9a\x7fR'
'\x07'
 '\x0bH'
'\x05'
 '\x83\x9a\x7fH'
'\t'
 'jD'
 '\x87\x9a\x7fH'
'\x12'
 '\xdc\x01\x0cAWELLEMET YA'
 '\x8d\x7f\x08UAREG YA'
'\x10'
 '\xd6\x00G'
 '\x92\x98\x7fH'
 '\xfe\xe5\x00K'
 '\xba\xa9\x7fN'
 '\xcepQ'
 '\x9f\x14Z'
'\x04'
 '\x8e\x98\x7fH'
 '\x03N'
'\x02'
 '\xf3\x97\x7fZ'
'\x04'
 '\xde\x97\x7fH'
 '\x03J'
'\x04'
 '\xdc\xab\x7f\nHAGGAR YAZ'
 '\x85\xd5\x00\x06YER YA'
'\x02'
 '\xfb\xaa\x7fG'
'\x12'
 '\xd4\x05\x07LETTER '
 '\xd8{\x05MARK '
 '\x85\x9e\x7f\x15SIGN RDEL NAG RDEL DK'
'\x0c'
 '\xe2\x03B'
 'p CLOSING BRDA RNYING YIG MGO SGAB'
 '\x00 INITIAL BRDA RNYING YIG MGO MDUN'
 '\xb4\x7f\x08MNYAM YI'
 'm\x08NYIS TSH'
'\x02'
 '\xdb\xa1\x7fE'
'\x02'
 '5\x0bG GI MGO RG'
'\x02'
 '\xe7\xa0\x7fY'
'\x02'
 '\xcfU '
'\x04'
 '\x1aK'
 '\x01\x02SK'
'\x02'
 '\x85\x7f\x06A- SHO'
'\x04'
 '\xe6]K'
 '\xf7SR'
'\x0c'
 '\xec\x00\x04REE '
 '\xb1^\x11UNDER CLOUD AND R'
'\n'
 '\xd6\x01D'
 '\xc7~L'
'\x06'
 '\x80\xa3\x7f\x0eEFTWARDS ARROW'
 '\x99\xde\x00\x10INES CONVERGING '
'\x04'
 '\xca\x9f\x7fL'
 '\xb72R'
'\x04'
 '\xc0\x00\nIMENSIONAL'
 '\x9b_O'
'\x02'
 '\xbb\x95\x7f '
'\xc0\x01'
 '\xb4\x1d\x05LUGU '
 'bN'
 '\xd1c\x0cTRAGRAM FOR '
'\xa2\x01'
 '\xa6\x1bA'
 '\xce~B'
 '\x82}C'
 '\xca|D'
 '\xa2}E'
 '\xa2~F'
 '\xc2~G'
 '\x82\x7fH'
 'T\x02IN'
 'rJ'
 '\x82\x7fK'
 '\xf2~L'
 '\x82\x7fM'
 '\x9e\x7fO'
 '\xfa~P'
 '\xc2~R'
 '\xa2~S'
 'ZU'
 'l\x0fVASTNESS OR WAS'
 'X\x02WA'
 'U\x08YOUTHFUL'
'\x02'
 '\x0bN'
'\x02'
 '\x0bE'
'\x02'
 '\x93\x9d\x7fS'
'\x04'
 '&I'
 'oT'
'\x02'
 '\xcf\x9d\x7fC'
'\x02'
 '\xbb\x98\x7fT'
'\x02'
 '\x0bN'
'\x02'
 '\x0bI'
'\x02'
 '\xdbkT'
'\n'
 '\xa2\x01E'
 'l\x02IN'
 '\x9f\x7fT'
'\x06'
 '*O'
 '\x9d\x9c\x7f\x04RENG'
'\x04'
 ' \x02PP'
 '\xb7\x8c\x7fV'
'\x02'
 '\x8f\x91\x7fA'
'\x02'
 '\xef\x96\x7fK'
'\x02'
 '\x0bV'
'\x02'
 '\x11\x02ER'
'\x02'
 '\x0bA'
'\x02'
 '\xdbZN'
'\x0c'
 '"E'
 '\xddU\x03ITU'
'\n'
 '\xaa}A'
 '\xd6\x03L'
 '\xab\x7fS'
'\x06'
 '&I'
 '\x99\x8b\x7f\x03PON'
'\x04'
 '\x1eD'
 '\xd1~\x02ST'
'\x02'
 '\xdb~E'
'\x02'
 '\xe5\x8a\x7f\x02EA'
'\x08'
 '\xca\x00A'
 'p\x04ENET'
 '\x89|\x02UR'
'\x02'
 '\x97WR'
'\x04'
 '\xa2}C'
 '\x85\x03\x03TTE'
'\x02'
 '\x8b\x8f\x7fR'
'\x04'
 '\xc4\x90\x7f\x07N THE V'
 '\x85\xf0\x00\x03PPO'
'\x02'
 '\x89V\x02SI'
'\x06'
 '\xf0\x92\x7f\x03ASS'
 '\xe6\xed\x00E'
 'cI'
'\x02'
 '\x0bR'
'\x02'
 '\xb3\x8e\x7fE'
'\x02'
 '\x11\x02AS'
'\x02'
 '\xab\x87\x7fU'
'\x06'
 '"A'
 '\x89\x9a\x7f\x02EG'
'\x04'
 '\xd4\x00\x03BOU'
 'm\x08W OR MOD'
'\x02'
 '\xdf\x91\x7fE'
'\x02'
 '\xf7\x90\x7fR'
'\x04'
 '\xdc\x00\tEEPING SM'
 'e\x02IN'
'\x02'
 '\xedA\x03SHI'
'\x02'
 '\x0bA'
'\x02'
 '\xcb\x90\x7fL'
'\x02'
 '\xafcO'
'\x04'
 '\x1aC'
 '\x87\x9e\x7fN'
'\x02'
 '\xbbzR'
'\x04'
 '\xec\x00\x02AR'
 'I\x06OLDING'
'\x02'
 '\x0b '
'\x02'
 '\x0bB'
'\x02'
 '\x0bA'
'\x02'
 '\xa3\xff~C'
'\x02'
 '\xa7uD'
'\n'
 '\xac\x01\x08ATHERING'
 'NO'
 'p\x03REA'
 '\x85\x7f\x05UARDE'
'\x02'
 '\xabtT'
'\x02'
 '\x85Y\tING TO ME'
'\x05'
 '\x97J '
'\x0c'
 '\xdcz\x03AIL'
 '\xbeFL'
 '\x82\xc0\x00O'
 '\xb5\x7f\x03ULL'
'\x04'
 '\x16 '
 '\xffrN'
'\x02'
 '\x0bC'
'\x02'
 '\x0bI'
'\x02'
 '\xd9\x84\x7f\x02RC'
'\x04'
 '"L'
 '\xb1z\x03STE'
'\x02'
 '\xa5\x8b\x7f\x03LOW'
'\x0e'
 '\xf2\x80\x7fA'
 '\xd0\x81\x01\x05MBELL'
 '\xc6~N'
 '\xd8q\x03TER'
 '\x99\x0e\x04XHAU'
'\x02'
 '\x8fMS'
'\x06'
 '\x90\x01\x04COUN'
 'l\x04DEAV'
 'U\x05LARGE'
'\x02'
 '\x0bM'
'\x02'
 '\x0bE'
'\x02'
 '\x93\xfb~N'
'\x02'
 '\x93\xbd\x7fO'
'\x02'
 '\x0bT'
'\x02'
 '\xf9\x8c\x7f\x02ER'
'\x02'
 '\x95\x7f\x03ISH'
'\x14'
 '\xa0\x03\x04ARKE'
 '\xde~E'
 '\x8e\x7fI'
 '\x9c\xf9~\x03OUB'
 '\xbf\x86\x01U'
'\x02'
 '\x11\x02TI'
'\x02'
 '\xcb\x8b\x7fE'
'\x08'
 'T\x06FFICUL'
 '\xf6\x00M'
 '\xc5q\x04VERG'
'\x04'
 '\x88~\x02IN'
 '\xc7\x88\x7fM'
'\x06'
 '\x94m\x06CISIVE'
 '\x90\\\x15FECTIVENESS OR DISTOR'
 '\xf9*\x04PART'
'\x02'
 '\x83\x85\x7fN'
'\x16'
 '\x90\xfa~\x03ENT'
 '\xdc\x04\x02HA'
 '\xb8\x83\x01\x03LOS'
 '\xb7~O'
'\x0c'
 '\xac\x01\x03MPL'
 '\xfb~N'
'\x08'
 '\xb4W\x05STANC'
 '\xfb(T'
'\x06'
 '\xc2\x00A'
 '\xf8E\x02EN'
 '\xf1$\x05RARIE'
'\x02'
 '\xf7\xf4~C'
'\x04'
 '\xe2EE'
 '\xc7&I'
'\x06'
 '\x1aE'
 '\xd3\xf7~U'
'\x04'
 '$\x04D MO'
 '\x83iN'
'\x02'
 '\xf7\x86\x7fU'
'\x06'
 '\x9c\x01\x03ARR'
 'd\x07OLD RES'
 'm\nRANCHING O'
'\x02'
 '\xff\xf2~U'
'\x02'
 '\xe9C\x03OLU'
'\x02'
 '\x9b\x8f\x7fI'
'\x08'
 '\xf0\x00\x05CCUMU'
 '\x8ci\x02DV'
 '\xb0Y\x05GGRAV'
 '\xb7=S'
'\x02'
 '\xb7vC'
'\x02'
 '\xbbBL'
'\x04'
 '\xd2\x87\x7fG'
 '\xcbhT'
'\x1a'
 '\x9c\x03\x0fFRACTION DIGIT '
 'P\x07LETTER '
 '\xa4\x7f\x05SIGN '
 '\x8b\x7fV'
'\x04'
 '-\tOWEL SIGN'
'\x04'
 '1\n VOCALIC L'
'\x05'
 '\xfb\xed~L'
'\x04'
 '2A'
 'm\x03TUU'
'\x02'
 '\xef\xb9\x7fM'
'\x02'
 '\xb5\x8e\x7f\x05VAGRA'
'\x04'
 '\x1aD'
 '\xf3\x94\x7fT'
'\x02'
 '\xf7\x81\x7fZ'
'\x0e'
 '\xa0\x02\x02ON'
 '\x8a\x7fT'
 '\xad\x7f\nZERO FOR O'
'\x02'
 '\x11\x02DD'
'\x02'
 '\x89r\x0c POWERS OF F'
'\x08'
 '\xf4\x00\x03HRE'
 '\xb9\x7f\x02WO'
'\x04'
 '\x1d\x05 FOR '
'\x04'
 '\xec~\x04EVEN'
 'oO'
'\x04'
 '\xb7\x7fE'
'\xae\x08'
 '\x9c\x11\x02I '
 '\x95o\x04MIL '
'\xda\x04'
 '\xa0\x81\x7f\x07AS ABOV'
 '\xea\x8c\x01C'
 '\xfe~D'
 'l\x06LETTER'
 '\xac\xee~\x05MONTH'
 '\xae\x91\x01N'
 '\xda\xe5~O'
 '\x8a\x9a\x01R'
 '\xf4u\tSYLLABLE '
 '[Y'
'\x02'
 '\x11\x02EA'
'\x02'
 '\x93\xf9~R'
'\x94\x04'
 '\x92\x01C'
 '\x02H'
 '\x02J'
 '\x9e\x07K'
 '\xca~L'
 '\x9ezM'
 '\x96\x04N'
 '\xee{P'
 '\xba\x03R'
 '\xbe~S'
 '\xaa\x7fT'
 '\xe6~V'
 '\x03Y'
'\x16'
 '\xf6\x00A'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\x9f\xe4\x00U'
'\x05'
 '\xe3\xe5~U'
'\x05'
 '\xcf\xe5~I'
'\x06'
 '\xba\xe5~A'
 '\x02I'
 '\x03U'
','
 'ZA'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\xce\xe3\x00T'
 '\xd3\x00U'
'D'
 '\x82\x7fA'
 '\x8e\x9c\x7fE'
 '\xda\xe5\x00H'
 '\x8a~I'
 '\xd2\x9b\x7fO'
 '\xce\xe3\x00S'
 '\xd3\x00U'
'\x18'
 '\x9a~A'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\xda{R'
 '\xc7\xe8\x00U'
','
 '\xbe}A'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\xce\xe3\x00R'
 '\xd3\x00U'
'n'
 '\xe2|A'
 '\x8e\x9c\x7fE'
 '\xfe\xe2\x00G'
 '\xe6\x00I'
 '\xa6\x04N'
 '\xae\x97\x7fO'
 '\x9e\xe4\x00U'
 '\xb3\x7fY'
','
 '\xee{A'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\x9e\x7fN'
 '\xb6\x9c\x7fO'
 '\x9f\xe4\x00U'
'B'
 '\x92{A'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xde\x05L'
 '\xf6\x95\x7fO'
 '\x9f\xe4\x00U'
','
 '\xb6zA'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\x9e\x7fL'
 '\xb6\x9c\x7fO'
 '\x9f\xe4\x00U'
'.'
 '\xdayA'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\xcc\xeb\x00\x02SS'
 '\xd3xU'
'\x18'
 '\xce\x00A'
 '\xb6\x94\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\x9f\xe4\x00U'
'\t'
 '\xe2\xdd~A'
 '\x02I'
 '\x03U'
'\x02'
 '\xf5\xf4~\x03UPE'
'\x02'
 '\x15\x03UMB'
'\x02'
 '\xa7uE'
'\x02'
 '\xfb\xa9\x7f '
'\x06'
 '\xee\x00A'
 '`\x02EB'
 '[I'
'\x02'
 '\xa5\x9e\x7f\x05GIT Z'
'\x02'
 '\x0bI'
'\x02'
 '\xbb\xed~T'
'\x02'
 '\xa7\xed~Y'
'2'
 '\xc8\x00\tONSONANT '
 '\x81\x7f\x03RED'
'0'
 '\x92\xdb~C'
 '\x02H'
 '\x02J'
 '\xea\xa6\x01K'
 'rL'
 '\xaa\xd9~M'
 '\xae\xa6\x01N'
 '\xd6\xd9~P'
 '\xde\xe5\x00R'
 'fS'
 '\xda\xc0\x00T'
 '\xea\xd9~V'
 '\x03Y'
'\x05'
 '\xe7\xd9~T'
'\x0b'
 '\xd2\xd9~G'
 '\x8e7N'
 '\xf7HY'
'\x07'
 '\xabkL'
'\x05'
 '\xcf\xec~S'
'\xd4\x03'
 '\xa0\x1f\nLE LETTER '
 '\xa8j\x05THAM '
 '\xadw\x05VIET '
'\x90\x01'
 '\xc0\x05\x07LETTER '
 'H\x05MAI K'
 '\xe8~\x07SYMBOL '
 '\x94\x7f\tTONE MAI '
 '\xbd~\x06VOWEL '
'\x1a'
 '\x86\x01A'
 '\xba\xd5~E'
 '\xb6\xaa\x01I'
 '\xce\xd5~O'
 '\x93\xaa\x01U'
'\t'
 '\xee\xd5~A'
 '\xb7\xaa\x01E'
'\x05'
 '\xcb\xd5~A'
'\n'
 '\xb6\xd5~A'
 '\x02M'
 '\x02N'
 '\xce\x04U'
 '\xb7{Y'
'\x08'
 '\xee\xd4~E'
 '\xea\xab\x01N'
 '\xc2\x86\x7fS'
 '\xaf\xf9\x00T'
'\x02'
 '\xb3\x87\x7fH'
'\x02'
 '\xaf\x86\x7fU'
'\n'
 '\x80\x01\x04HO H'
 'X\x02KO'
 '\x92\x7fN'
 '\xdf\x00S'
'\x02'
 '\xff\xdb~A'
'\x04'
 '$\x03I K'
 '\x8f\xd3~N'
'\x02'
 '\xef\x84\x7fO'
'\x04'
 '\x9e\xe2~A'
 '\x87\x9e\x01H'
'\x02'
 '\xef\xd3~I'
'`'
 ',\x04HIGH'
 '\x01\x03LOW'
'0'
 '\x0b '
'0'
 '\xfe\x84\x7fB'
 '\xe6\xfc\x00C'
 '\x9e\x83\x7fD'
 '\x02F'
 '\x02G'
 '\x02H'
 '\xb2\xfd\x00K'
 '\xd2\x82\x7fL'
 '\x02M'
 '\x86\xfd\x00N'
 '\x82\xd0~O'
 '\xe2\xaf\x01P'
 '\x9e\x83\x7fR'
 '\x02S'
 '\xe6\xfc\x00T'
 '\x9e\x83\x7fV'
 '\x03Y'
'\x04'
 '\x9a\x83\x7fH'
 '\x87MO'
'\x06'
 '\xfa\x82\x7fG'
 '\x86MO'
 '\xff2Y'
'\x06'
 '\xb2\x7fH'
 '\xa3\xd0~O'
'\xfe\x01'
 '\xb8\x11\x02CO'
 '\xecr\x04HORA'
 '\xec\x06\x07LETTER '
 '\xb0y\x05SIGN '
 'd\x04THAM'
 '\xa5}\x0bVOWEL SIGN '
'&'
 '\xb6\x02A'
 '\xae\xcb~E'
 '\xb2\x9a\x01I'
 '\x84\x1a\x04MAI '
 'VO'
 '\x9e\x7fT'
 'cU'
'\t'
 '\xfa\xcc~E'
 '\xd36U'
'\x04'
 '6A'
 'm\x04HAM '
'\x02'
 '\x9b\xfe~A'
'\x02'
 '\x15\x03LL '
'\x02'
 '\x93\xe1~A'
'\x0b'
 '\x86\xab\x7fA'
 '\xf2\xa0\x7fO'
 '\x03Y'
'\x02'
 '\x0bS'
'\x02'
 '\xdb\xcc~A'
'\t'
 '\xaa\xcb~A'
 '\x02E'
 '\x03I'
'\x14'
 '\x85\x8c\x7f\x02 D'
'2'
 '\xf4\xfd~\x02CA'
 '\xbc\x80\x01\x04DOKM'
 '\xfa\x07H'
 '\xc6~K'
 '\x8c\x7f\x04MAI '
 '\x82\x7fR'
 '\x8c\x7f\x02SA'
 'X\x04TONE'
 'e\x05WIANG'
'\x05'
 '\xad\xef~\x02WA'
'\x04'
 '\x0b-'
'\x04'
 '\xfe\xc8~1'
 '\x032'
'\x08'
 '\xf2\xc9~K'
 '\xcc\xb6\x01\x03TKA'
 '\xb3\xd7~W'
'\x04'
 '\x11\x02AN'
'\x05'
 '\x0bK'
'\x02'
 '\xab\x94\x7fU'
'\x04'
 '\xa4t\x04A HA'
 '\xc5\x0c\x10EVERSED ROTATED '
'\x02'
 '\x87\xe9~R'
'\x08'
 '\xd4\x00\x04KANG'
 '\xd2rS'
 '\x9d\r\x03YAM'
'\x02'
 '\x9f\xc6~O'
'\x05'
 '\x0b '
'\x02'
 '\xd3yL'
'\x0e'
 '\xd6}A'
 '\xca\xe8~E'
 '\xa1\x9a\x01\x04HUEN'
'\x08'
 '\xd4\x00\x06 TONE-'
 '\xf1\xd3~\x08-LUE KAR'
'\x06'
 '\xe2\xc4~3'
 '\x024'
 '\x035'
'\x04'
 '\xe6\xd3~A'
 '\xc3\xd3\x00O'
'j'
 '\x9a\xc4~A'
 '\x8a\x15B'
 '\x02D'
 '\xc6oE'
 '\x92\xbd\x01G'
 '\xe8~\x05HIGH '
 '\xeeYI'
 '\xee#L'
 '\xee\xd6~M'
 '\xee\xa8\x01N'
 '\x8a\xf5~O'
 '\xc2\x8a\x01R'
 '\xe2\\U'
 '\xef\xfa~W'
'\x08'
 '\x1aA'
 '\xf7\xc6~U'
'\x07'
 '\xae\xd7~N'
 '\x03T'
'\x06'
 '\x8a\xc2~A'
 '\x8a\x15G'
 '\x03Y'
'$'
 '\xb2\xf8~A'
 '\xba^L'
 '\xe0\xa9\x01\x03OW '
 '\xe7\xc5~U'
'\x1c'
 '\xf6\x00C'
 '\xaa\xd5~F'
 '\x02H'
 '\x96\xab\x01K'
 'FP'
 '"R'
 '\x8a\xd5~S'
 '\xda\xaa\x01T'
 '\xab\xd5~Y'
'\x04'
 '\x9e\xc0~A'
 '\x8b\x15H'
'\x02'
 '\x81\xe1~\x02AT'
'\x06'
 '\xe2\xbf~A'
 '\x8a\x15H'
 '\x03X'
' '
 '\x9a\x7fC'
 '\xaa\xd5~F'
 '\x02H'
 '\x96\xab\x01K'
 'FP'
 '"R'
 '\xb6\x01S'
 '\xae~T'
 '\xab\xd5~Y'
'\x06'
 '\xca\xbe~A'
 '\x8a\x15H'
 '\x03S'
'\x02'
 '\x19\x04REAT'
'\x02'
 '\x87\xe6~ '
'\x14'
 '\xec\xbe~\x15MBINING CRYPTOGRAMMIC'
 '\xbd\xc2\x01\rNSONANT SIGN '
'\x12'
 '\xce\xd1~B'
 '\x88\xb1\x01\x06FINAL '
 '`\x10HIGH RATHA OR LO'
 'JL'
 '\xaa\x7fM'
 '\xab\xd0~S'
'\x06'
 '\x9e\xbb~A'
 '\x9d\xc5\x01\x06EDIAL '
'\x04'
 '\xea\xcf~L'
 '\x03R'
'\x04'
 '\xb8t\x07A TANG '
 '\xff\x0bO'
'\x02'
 '\x0bW'
'\x02'
 '\x97\x87\x7f '
'\x02'
 '\xf3\xe2~N'
'F'
 '\xa2\x03A'
 'fE'
 '\xde\xcb~F'
 '\x02H'
 '\xfajI'
 '\xe2\xbf\x01K'
 '\xaa\xd5~L'
 '\x02M'
 '\x86\xb4\x01N'
 '\xf6\xec~O'
 '\xe2\x89\x01P'
 '\xaa\xd5~Q'
 '\x02S'
 '\x86\xb3\x01T'
 '\xc6\xee~U'
 '\xba^V'
 '\x02X'
 '\x03Y'
'\x12'
 '\xf2\xb7~A'
 '\x8a\x15H'
 '\xd0\xb3\x01\x04ONE-'
 '\x8bwS'
'\n'
 '\xa6\xb7~2'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'\x04'
 '\xf2\xb6~A'
 '\x8b\x15G'
'\x07'
 '\xd2\xb6~E'
 '\x03H'
'\x07'
 '\xb6\xb6~I'
 '\xcf\x04U'
'\xfe\x05'
 '\x9a9A'
 'l\x02CA'
 '\xee~E'
 '\x8avH'
 '\xe6\x96\x7fK'
 '\xf0\xe8\x00\tLAVONIC A'
 '\xc8\xe5~\x04MALL'
 '\xa0C\x11NOWMAN WITHOUT SN'
 '\x9e\xd5\x01O'
 'l\x06PESMIL'
 '\x98n\x05QUARE'
 '\xd2~T'
 '\xf6tU'
 '`\x06WUNG D'
 '\x87vY'
'f'
 '\x90\x04\x0bLOTI NAGRI '
 '\xc8\x82\x7f\x17MBOL FOR SAMARITAN SOUR'
 '\x8d\xfb\x00\x0cRIAC LETTER '
'\x0c'
 '\xbc\x01\x08PERSIAN '
 '\x9d\x7f\x08SOGDIAN '
'\x06'
 '\x9a\xb5~F'
 '\xa8\xcb\x01\x02KH'
 '\xd5\xfe~\x02ZH'
'\x02'
 '\x0bA'
'\x02'
 '\x9b\xc4~P'
'\x06'
 '\xd4\x00\x02BH'
 '\xa4\xc3~\x05DHALA'
 '\xed:\x04GHAM'
'\x02'
 '\xa3\xc3~E'
'X'
 '\xe4\x02\x07LETTER '
 'T\x0cPOETRY MARK-'
 '\xb8\x7f\x05SIGN '
 'E\x0bVOWEL SIGN '
'\n'
 '\xc6\xad~A'
 '\x02E'
 '\x02I'
 '\xfe2O'
 '\x87MU'
'\x06'
 '\xc6\xd4~A'
 '\x14\x03DVI'
 '\xadm\x05HASAN'
'\x08'
 '\xc2\xac~1'
 '\x022'
 '\x023'
 '\x034'
'@'
 '\x96\xac~A'
 '\xe2\xaf\x01B'
 '\x02C'
 '\xde&D'
 '\xc6\xa9~E'
 '\xe2\xaf\x01G'
 '\x9e\x83\x7fH'
 '\x86MI'
 '\xe2\xaf\x01J'
 '\x02K'
 '\x9e\x83\x7fL'
 '\x02M'
 '\x02N'
 '\x86MO'
 '\xe2\xaf\x01P'
 '\xbe&R'
 '\xe2\xdc~S'
 '\xf2\xa2\x01T'
 '\x97\xaa~U'
'\x08'
 '\x8e\xdd~H'
 '\x86MO'
 '\xe3\xaf\x01T'
'\x04'
 '\xe2\xa9~O'
 '\xff2R'
'\x08'
 '\xa2YD'
 '\x9e\x83\x7fH'
 '\x87MO'
'\x02'
 '\x0bA'
'\x02'
 '\xa7\xbd~S'
'r'
 '\x82\x01N'
 'm\x16PERSET PRECEDING SOLID'
'\x02'
 '\xbf\xbb~U'
'p'
 '\xf0\t\x0b BEHIND CLO'
 '\xf1v\x07DANESE '
'n'
 '\x90\x08\x11CONSONANT SIGN PA'
 '\xfe\xdf~D'
 '\xb0\x9d\x01\x07LETTER '
 '\xb8~\x07SIGN PA'
 '\x81~\rVOWEL SIGN PA'
'\x0c'
 '\xe2\x01M'
 '\xbb~N'
'\n'
 '\x84\xd7~\x04AELA'
 '\xa0\xaa\x01\x03EUL'
 'l\x03GHU'
 'nO'
 'm\x02YU'
'\x02'
 '\xb7\xf0~K'
'\x02'
 '\x97\xd6~L'
'\x02'
 '\x8f\xf0~L'
'\x02'
 '\x0bE'
'\x02'
 '\xef\xb2~U'
'\x02'
 '\xa9\xfe~\x02EP'
'\x08'
 '\xb0\x01\x03MAA'
 '\xf7~N'
'\x06'
 ':G'
 '[Y'
'\x02'
 '\x11\x02EC'
'\x02'
 '\xbb\xa2~E'
'\x04'
 '2L'
 'm\x03WIS'
'\x02'
 '\xb3\xad~A'
'\x02'
 '\xe5\xaa~\x02AY'
'\x02'
 '\xff\xb5~E'
'@'
 '\x9e\xd8~A'
 '\xba^B'
 '\x02C'
 '\x02D'
 '\x96\x85\x01E'
 '\xee\xfa~F'
 '\x02G'
 '\x02H'
 '\xfajI'
 '\x8a\x15J'
 '\xda\xaa\x01K'
 '\xaa\xd5~L'
 '\x02M'
 '\xee\xa8\x01N'
 '\x8e\xc2~O'
 '\x8a\x15P'
 '\x02Q'
 '\x02R'
 '\xde\xcb\x01S'
 '\xa6\xb4~T'
 '\xfajU'
 '\x8a\x15V'
 '\x02W'
 '\x02X'
 '\x02Y'
 '\x03Z'
'\x04'
 '\x9a\x9f~A'
 '\x8b\x15Y'
'\x06'
 '\xd0\x00\x02MI'
 'U\x02NY'
'\x04'
 '\x16A'
 '\xafzI'
'\x02'
 '\xa3\xbf~K'
'\x02'
 '\x11\x02NG'
'\x02'
 '\x8f\xed~K'
'\x02'
 '\x9f\xa9~U'
'\x06'
 '\xcc\x00\x07AFF OF '
 '\xfd\x9e\x7f\x05RAIGH'
'\x04'
 '\x90u\tAESCULAPI'
 '\xb9\x0b\x03HER'
'\x02'
 '\xbb\xa4\x7fM'
'\x80\x01'
 '\xd6\x0b '
 '\xcdt\x02D '
'^'
 '\x80\x04\x16CJK UNIFIED IDEOGRAPH-'
 '\xc4\xe9~\x04FOUR'
 '\xaa\x95\x01H'
 '\xca\x00K'
 'L\x15LATIN CAPITAL LETTER '
 'nM'
 '\x00\x02PP'
 '\xb7\x7fS'
'\x06'
 '"A'
 '\xce\x99~D'
 '\x03S'
'\x02'
 '\x11\x02LT'
'\x02'
 '\xf7\x9d~I'
'\x02'
 '\xa3\x99~V'
'\n'
 '\x8e\x99~B'
 '\x02N'
 '\x02P'
 '\x02S'
 '\x03W'
'\x04'
 '4\x07ATAKANA'
 '\x8f\xfb~E'
'\x02'
 '\x83\xaf~ '
'B'
 '\xd8\x06\x024E'
 '\xda}5'
 '\x8a~6'
 '\x92\x7f7'
 '\x9a\x7f8'
 '\xb5\xac~\x03904'
'\x06'
 '\xd2\x009'
 '\xa8\xee~\x02CA'
 '\xc5\x91\x01\x02D7'
'\x02'
 '\xeb\x96~0'
'\x02'
 '\x83\xef~E'
'\x06'
 '\xd8\x00\x0212'
 '\xf0\xe3~\x0251'
 '\xfd\x9b\x01\x02D4'
'\x02'
 '\xfb\x95~2'
'\x02'
 '\xe7\x95~1'
'\x12'
 '\xb6\x012'
 'J3'
 '^5'
 '\x8c~\x0262'
 '\xe1\x01\x02F1'
'\x02'
 '\x8b\x95~4'
'\x04'
 '\xc6\xec~9'
 '\xc7\x91\x01B'
'\x04'
 '\x8e\xec~0'
 '\x97\x94\x015'
'\x02'
 '\xaf\x94~5'
'\x06'
 '*4'
 '\x9e\xec~5'
 '\xa7\x93\x019'
'\x02'
 '\xef\x93~B'
'\x18'
 '\xf8\x9e~\x0218'
 '\x92\xe3\x012'
 '^3'
 '\xc4\xe9~\x0243'
 '\xc4\x91\x01\x028F'
 '\xd6\x049'
 '\xb6\xea~B'
 '\xb8\x95\x01\x02DE'
 '\xd1\x98~\x02F8'
'\x02'
 '\xab\x92~6'
'\x04'
 '\x9e\xa7~1'
 '\xcb\xc2\x002'
'\x04'
 '\x96\x98~C'
 '\x8b\xd2\x00F'
'\x04'
 '\xee\x9c~1'
 '\x034'
'\n'
 '60'
 '\x9e\x9c~2'
 '\x86{8'
 '\xd3\xe4\x01A'
'\x04'
 '\xfa\x90~0'
 '\x039'
'"'
 '\xba\x03A'
 '\xca\x01D'
 'bE'
 'X\x04FOUR'
 '\xa2\xdb~G'
 '\x96\xa4\x01H'
 '\x9a\xd9~I'
 '\xb6\xa6\x01V'
 '\xe1}\x05WITH '
'\x08'
 '\xfa\x01B'
 '\x84\x7f\tLOWER LEF'
 '\xea\x00T'
 '\x99\x7f\nUPPER RIGH'
'\x02'
 '1\nT DIAGONAL'
'\x02'
 '\xd1\x8e\x7f\x08 HALF BL'
'\x02'
 'I\x02OP'
'\x02'
 '\xb5\x7f\x05OTTOM'
'\x02'
 '\x1d\x05 OVER'
'\x02'
 '\xbb\x95~ '
'\x04'
 '\xee\x8c~G'
 '\xf5\xcc\x00\nIRAGANA HO'
'\x02'
 '\xdd\x92\x7f\x05 CORN'
'\x04'
 '\xae\x9b~R'
 '\xcfpV'
'\x08'
 '\xda\x8b~J'
 '\xcb\xf4\x01M'
'\x07'
 '\x0b '
'\x04'
 '\x94\x88\x7f\x03CUB'
 '\x9b\xf8\x00S'
'\x02'
 '\x0bQ'
'\x02'
 '\xcd\x87\x7f\x02UA'
'\x02'
 '\x87\x9c~O'
'\n'
 '\xd8\x01\x04CCER'
 '\xe1~\x04UTH '
'\x08'
 '\x8e\x01E'
 '\x8f\x7fW'
'\x04'
 '\x0bE'
'\x04'
 '\x0bS'
'\x04'
 '\x11\x02T '
'\x04'
 '\x96\xd0~B'
 '\x9d\xb0\x01\x04WHIT'
'\x02'
 '\xff\xcf~E'
'\x04'
 '\x97\x7fA'
'\x02'
 '\x0b '
'\x02'
 '\xef\x87\x7fB'
'\x02'
 '\xb5\x88~\x06STERIS'
'd'
 ':A'
 '\xed\xca~\x08INTO SHR'
'b'
 '\xa4\t\x02MR'
 '\xadw\x0cVIAN LETTER '
'`'
 '\xb6\x07A'
 'rB'
 'l\x03CHU'
 'rD'
 '\xbe\x7fE'
 '\xf6\xc2~F'
 '\xfa\xbc\x01G'
 'ZH'
 'VI'
 '\xd8\x8a~\x03JUD'
 '\x96\xf5\x01K'
 '\xe8\x80\x7f\x02LO'
 '\xe2\xfe\x00M'
 '\xa2\xcf~N'
 '\xf6\xaf\x01O'
 'l\x02PE'
 'nR'
 'bS'
 'FT'
 '\xda\xc4~U'
 '\xba_V'
 '\xd0\xdb\x01\x02WO'
 'd\x02YE'
 '\x8b\xbf~Z'
'\x04'
 '\xa6\x84~A'
 '\x03W'
'\x04'
 '\x8a\x84~E'
 '\xf3\x0fO'
'\x06'
 '\x1aH'
 '\xef\x84~O'
'\x04'
 '\xb6\xe6~E'
 '\xbb\x06I'
'\x04'
 '\xae\x83~O'
 '\xc3\x04U'
'\x02'
 '\xf7\x8b~O'
'\x02'
 '\xe7\xc3~E'
'\x0c'
 '\xda\x82~A'
 '\xfe\x0fI'
 '\x92pN'
 '\xf2\xfd\x01O'
 '\x92\x82~R'
 '\x9f\x01U'
'\x02'
 '\xdb\x86~Z'
'\x04'
 '\xfa\xfe~E'
 '\xab\x81\x01I'
'\x02'
 '\xa3\x86~M'
'\x02'
 '\x93\x82\x7fI'
'\x06'
 '\xea\x8b~A'
 '\x92zC'
 '\xb7{F'
'\x04'
 '\x84\xa2~\x02A-'
 '\xa7nU'
'\x02'
 '\x8f\x90~A'
'\x08'
 '&A'
 '\xd6\x8f~G'
 '\xc3yR'
'\x04'
 '\x9e\x80~R'
 '\x03T'
'\x02'
 '\xef]E'
'\x02'
 '\xbf\xf6~R'
'\x02'
 '\xefkI'
'\x10'
 '\xca\xb2~D'
 '\xd2QG'
 '\xb6{H'
 '\xf6\x08I'
 '\xa2\xf8\x01R'
 '\x8a\x93~S'
 '\xb3pW'
'\x04'
 '\xea\xfe}E'
 '\xbb\x81\x02R'
'\x02'
 '\xaf\xe1~A'
'\x02'
 '\x83\xff~O'
'\x06'
 '\xd4\x00\x05MISEX'
 '\x1c\tSQUIQUADR'
 'gX'
'\x02'
 '\xd5\x85~\x02TI'
'\x02'
 '\x0bA'
'\x02'
 '\xeb\x81~T'
'\x02'
 '\xf7\x84\x7fL'
'\x9e\x02'
 '\x88\x1a\x03ILB'
 '\x98p\x08MARITAN '
 '\xd5v\tURASHTRA '
'\xa2\x01'
 '\x84\t\x11CONSONANT SIGN HA'
 '\xfe~D'
 '\xec{\x07LETTER '
 '\xa0\x7f\x05SIGN '
 '\xd1~\x0bVOWEL SIGN '
'\x1e'
 '\xda\x94\x7fA'
 '\x8e\x9c\x7fE'
 '\xe2\xe3\x00I'
 '\xd2\x9b\x7fO'
 '\x9e\xe4\x00U'
 '\xb9\xec\x00\x02VO'
'\x08'
 '!\x06CALIC '
'\x08'
 '\x8a\x8b\x7fL'
 '\xdbSR'
'\x06'
 '\xa2\xa0~A'
 '\x83\xe0\x01V'
'\x04'
 '\x0bI'
'\x04'
 '\x1aR'
 '\x8f\xa1~S'
'\x02'
 '\xa3\xbc~A'
'd'
 '\xa2\x9a\x7fA'
 '\xc6\x1dB'
 '\x02C'
 '\xfa\xcb\x00D'
 '\xfa\xaa~E'
 '\x92\x89\x01G'
 '\xaa\xd5~H'
 '\xaa\x85\x01I'
 '\xb2%J'
 '\x02K'
 '\xda\xcb\x00L'
 '\xd2\x89~M'
 '\x82\xf6\x01N'
 '\xfa\xaa~O'
 '\xe2\x89\x01P'
 '\xaa\xd5~R'
 '\xae\xac\x01S'
 '\xa6\xc9\x00T'
 '\xc6\x8f\x7fU'
 '\x9a\xf0\x00V'
 '\xd7\x8a~Y'
'\n'
 '\xca\xf5}A'
 '\xd7\x86\x02O'
'\x08'
 '\xa6\xf5}A'
 '\x8a\x15H'
 '\xdb\xaa\x01T'
'\x08'
 '\xf6\xf4}A'
 '\x8a\x15G'
 '\x02N'
 '\x03Y'
'\x04'
 '\xc6\xf4}A'
 '\x8b\x15L'
'\x08'
 '\xa6\xf4}A'
 '\xe2\xbf\x01D'
 '\xab\xd5~H'
'\x18'
 '\xee\x00A'
 '\x92\xb4~I'
 '\xb3\xcb\x01O'
'\x02'
 '\x0bU'
'\x02'
 '\x0bB'
'\x02'
 '\x19\x04LE D'
'\x02'
 '\x0bA'
'\x02'
 '\xe3\xc0~N'
'\x02'
 '\x0bA'
'\x02'
 '\x8b\xbf~R'
'z'
 '\xba\x0fA'
 '\xfc{\x07LETTER '
 '\xea|M'
 '\xc8{\x0cPUNCTUATION '
 '\xd1}\x0bVOWEL SIGN '
'\x1e'
 '\xca\x9b\x7fA'
 '\xce\xd5~E'
 '\x02I'
 '\xe4\x90\x02\x05LONG '
 'JO'
 '\xb2\x7fS'
 '\xa7\xf0}U'
'\x04'
 '"H'
 '\xa5\xbd~\x02UK'
'\x02'
 '\x15\x03ORT'
'\x02'
 '\xef\x84~ '
'\x07'
 '\x85\x9a\x7f\tVERLONG A'
'\n'
 '\xce\x99\x7fA'
 '\xce\xd5~E'
 '\x02I'
 '\x03U'
'\x1c'
 '\x8a\x03A'
 'nB'
 '\xbc\x7f\tMELODIC Q'
 '"N'
 'bQ'
 '\x8a\x7fS'
 '\xc8z\x02TU'
 '\x83\x05Z'
'\x04'
 '"A'
 '\xb5\xa1\x7f\x02IQ'
'\x02'
 '\xc7\xbb~E'
'\x04'
 '\xe0\x00\x06HIYYAA'
 'm\x08OF MASHF'
'\x02'
 '\x9b\xa1\x7fA'
'\x02'
 '\xbb\xa0\x7fL'
'\x02'
 '\x0bI'
'\x02'
 '\xa7\x94~T'
'\x02'
 '\x85\xa0\x7f\x04EQUD'
'\x02'
 '\x97\xb8~A'
'\n'
 '\x94\x01\x04FSAA'
 '^N'
 'l\x04RKAA'
 'q\x02TM'
'\x02'
 '\x9b\x7fA'
'\x02'
 '\xa3\xb7~N'
'\x04'
 '\xd2\xe7~G'
 '\x8b\x98\x01N'
'\x02'
 '\xc3\xea}Q'
'\x12'
 '\xe0\x01\x04ARK '
 '\x85\x7f\x0fODIFIER LETTER '
'\x06'
 ':E'
 '\x8e\xe9}I'
 '\xe7\x96\x02S'
'\x02'
 '\x9byH'
'\x02'
 '\xa5\xf7~\x0bPENTHETIC Y'
'\x0c'
 '\x9c\x01\x03DAG'
 '\xa2~E'
 '\xac\x01\x02IN'
 '\xce{N'
 '\xdd\x83~\x05OCCLU'
'\x05'
 '\x11\x02-A'
'\x02'
 '\x0bL'
'\x02'
 '\xc7\xb5~A'
'\x02'
 '\x9f\xbe\x7fE'
','
 'JA'
 '\x9a\x04B'
 '\xf4\x97\x7f\x03DAL'
 '\xa6\xfd~F'
 '\xd4\xea\x01\x02GA'
 '^I'
 'rK'
 'l\x02LA'
 'nM'
 '\xca\xb1~N'
 '\xe4\x00\x02QU'
 '\xc2\xcd\x01R'
 'RS'
 '\xbe\x7fT'
 '\xca\xf3~Y'
 '\xd7\xb4\x7fZ'
'\x06'
 '\xea}A'
 '\xde\xe8}I'
 '\xcd\xe1\x00\x05SAADI'
'\x04'
 '\xf2\xf3}H'
 '\x99\x84\x02\x03ING'
'\x02'
 '\xab\xbb\x7fI'
'\x02'
 '\xdb\xec}I'
'\x02'
 '\xcf\x98\x7fB'
'\x02'
 '\xbb|A'
'\x06'
 '\xea\xe3}N'
 '\x02T'
 '\x03Y'
'\x02'
 '\xd3\xf2}M'
'\x04'
 '\xba\xf8}A'
 '\x97lI'
'\x02'
 '\xad\xe2}\x06BBREVI'
'\x02'
 '\xa7\x97\x7fO'
'\xe8\x01'
 "\xe0'\x02AI"
 '\xe2uE'
 '\xa2qI'
 '\xa8y\x05OMAN '
 '\xe1x\x04UMI '
'>'
 '\xbe\x06D'
 '\xc0~\tFRACTION '
 '\xe9{\x07NUMBER '
'$'
 '\xf4\x03\x05EIGHT'
 '\x9a\x7fF'
 '`\x04NINE'
 'D\x02ON'
 '\x12S'
 '\xab~T'
'\n'
 '\xca\xea}E'
 '\xca\x96\x02H'
 '\x9f\x7fW'
'\x04'
 '\xce\x00E'
 'KO'
'\x02'
 '\x0b '
'\x02'
 '\x0bH'
'\x02'
 '\x8d\xdc~\x03UND'
'\x02'
 '\x9b\xd6~N'
'\x04'
 '\x84\xd6~\x02IR'
 '\xad\xaa\x01\x02RE'
'\x02'
 '\xff~E'
'\x08'
 '(\x04EVEN'
 '\x01\x02IX'
'\x04'
 '\xce~ '
 '\xa7\xc2~T'
'\x08'
 '\xc2\x00I'
 'WO'
'\x04'
 '\xde\xd4~R'
 '\xad\xa9\x01\x02UR'
'\x04'
 '\xb2\xd4~F'
 '\xaf\xaa\x01V'
'\x04'
 '\xc6} '
 '\xbf\xdf}Y'
'\x08'
 '0\x04ONE '
 '\xb5\xef}\x02TW'
'\x06'
 '\xea\x00H'
 'VQ'
 'm\x03THI'
'\x02'
 '\xa3\xe7}R'
'\x02'
 '\x15\x03UAR'
'\x02'
 '\xbf\xf9}T'
'\x02'
 '\x0bA'
'\x02'
 '\xbf\xa9~L'
'\x12'
 '\x1d\x05IGIT '
'\x12'
 '\xd2\x9e~E'
 'NF'
 'vN'
 'rO'
 '\xbe\x7fS'
 'OT'
' '
 '\xee\x02A'
 '\xc8\x03\x07CENTURI'
 '\x9a\x7fD'
 '\xe0}\x08NUMERAL '
 'h\x03QUI'
 '\xb6~S'
 'OU'
'\x02'
 '\x11\x02NC'
'\x02'
 '\x0bI'
'\x02'
 '\xbf\xea}A'
'\n'
 '&E'
 'E\x05ILIQU'
'\x08'
 '\xa0\x7f\x02MU'
 '\xec\x01\x05STERT'
 '\xbd\x7f\x02XT'
'\x04'
 '"A'
 'sU'
'\x02'
 '\xe3~L'
'\x02'
 '\x0bN'
'\x02'
 '\x87\xe9}S'
'\x02'
 'i\x02IU'
'\x02'
 'i\x03NAR'
'\x08'
 '\xf0\x01\x06FIFTY '
 'D\x0cONE HUNDRED '
 'E\x05SIX L'
'\x02'
 '\x15\x03ATE'
'\x02'
 '\xb5\xde}\x04 FOR'
'\x02'
 '\x0bT'
'\x02'
 '\x19\x04HOUS'
'\x02'
 '\xc7\xe0}A'
'\x04'
 '\x9c\x7f\x05EARLY'
 '3T'
'\x06'
 '\xc6}E'
 '\xbc\x7f\x0cIMIDIA SEXTU'
 '1\x05UPOND'
'\x02'
 '\x0bA'
'\x02'
 '\xb3\xe5}L'
'*'
 '\xc0\x00\x03GHT'
 '\xb1\xd9~\x06NG POI'
'('
 '\xfa\x06 '
 '\x82\x7f-'
 '\xc5z\x06WARDS '
'\x0e'
 '\xe0\x00\x06ARROW '
 'OQ'
'\x02'
 '!\x06UADRUP'
'\x02'
 '\x8bIL'
'\x0c'
 '\xe4\x02\x07ABOVE R'
 '\xfc~\x08THROUGH '
 '\x9d\x7f\x07WITH TI'
'\x04'
 '\x11\x02P '
'\x04'
 '6D'
 'e\x02UP'
'\x02'
 '\xf5\xe3}\x02WA'
'\x02'
 'a\x03OWN'
'\x04'
 '\xec\x00\tGREATER-T'
 'Y\x03SUP'
'\x02'
 '\x11\x02ER'
'\x02'
 '\xbb\xaa~S'
'\x02'
 '\xbb\xde}H'
'\x04'
 '%\x07EVERSE '
'\x04'
 '\xee\x00A'
 'M\tTILDE OPE'
'\x02'
 '\x0bR'
'\x02'
 '\x11\x02AT'
'\x02'
 '\x8b\xd7}O'
'\x02'
 '5\x0bLMOST EQUAL'
'\x02'
 '\x0b '
'\x02'
 '\xbb\x80~T'
'\x04'
 '\xd5\x00\x12FACING SVASTI SIGN'
'\x05'
 '\xb5\xe4}\x05 WITH'
'\x16'
 '\xf4\x05\x06ANGLE '
 '\x92\x7fD'
 '\xb2\x7fL'
 'H\x02RA'
 '\xbe~S'
 '\xaa\x7fT'
 '\x93\x7fV'
'\x02'
 '\xd9\x00\x13ERTICAL BAR WITH QU'
'\x02'
 '\xff\xc9~I'
'\x02'
 ')\x08RANSPOSI'
'\x02'
 '\x0bT'
'\x02'
 '\xd9\xa4~\x03ION'
'\x06'
 '\x94n\x12-SHAPED BAG DELIMI'
 '\xa4\xb6~\tIDEWAYS U'
 '\xe3\xdc\x01U'
'\x02'
 '\xb5~\x06BSTITU'
'\x02'
 '\x99~\nISED OMISS'
'\x02'
 '9\x0cOW PARAPHRAS'
'\x02'
 '\x83\xa2~E'
'\x04'
 '\x0bO'
'\x04'
 '\xc0~\x07TTED SU'
 '\x85\x02\x04UBLE'
'\x02'
 '\x81\xa2~\x02 P'
'\x04'
 '0\x08DOTTED S'
 '\x03S'
'\x02'
 '%\x07UBSTITU'
'\x02'
 '\x19\x04TION'
'\x02'
 '\x19\x04 MAR'
'\x02'
 '\x87\xe3}K'
'X'
 '\xbc\x04\x05JANG '
 '\xc0\xf7~\x13STRICTED LEFT ENTRY'
 '\xa5\x85\x01\x05VERSE'
'\n'
 '\xaa\x01 '
 '\xf9~\x02D '
'\x04'
 '$\x03FOR'
 '\xab\x83~Q'
'\x02'
 ')\x08KED PARA'
'\x02'
 '\x1d\x05GRAPH'
'\x02'
 '\x87\xd6}O'
'\x06'
 '\xf4r\x15SOLIDUS PRECEDING SUB'
 '\xcd\x0e\x15TILDE OPERATOR ABOVE '
'\x04'
 '\xd6\xa0~L'
 '\x15\x04RIGH'
'J'
 '\x94\x05\x0fCONSONANT SIGN '
 '\xd4}\x07LETTER '
 'bS'
 '\xbf~V'
'\x12'
 '\xb2\x01I'
 '\x91\x7f\nOWEL SIGN '
'\x10'
 '\xd2\x00A'
 'fE'
 '\xca\xbe}I'
 '\x02O'
 '\x03U'
'\x07'
 '\xc6\xbe}A'
 '\x03U'
'\x04'
 '\xaa\xbe}I'
 '\x03U'
'\x02'
 '\xf3ER'
'\x02'
 '\x0bE'
'\x02'
 '\x9b\xbd}C'
'.'
 '\xde\xbd}A'
 '\x8a\x15B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\x02H'
 '\x02J'
 '\x02K'
 '\x02L'
 '\xa6\xaf\x02M'
 '\xa2\x7fN'
 '\xbe\xd1}P'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x02W'
 '\x03Y'
'\x0c'
 '\xb2\xbc}A'
 '\x8a\x15D'
 '\x86\xb4\x01G'
 '\x83\xfb\x00Y'
'\x04'
 '\xf2\xbb}A'
 '\x8b\x15J'
'\x04'
 '\xd2\xbb}A'
 '\x8b\x15B'
'\x08'
 '\xb2\xbb}H'
 '\x82\xc5\x02N'
 '\x83\xbb}R'
'\x05'
 '\xff\xba}G'
'\x08'
 '\xea\xba}N'
 '\xc9\xc5\x02\x04SED '
'\x06'
 '\xc4\x00\x08DOTTED I'
 '\x02I'
 '\x93\xbe}S'
'\x02'
 '\x95t\x08NTERPOLA'
'\xea\x02'
 '\xda&A'
 '\xd4~\x02ER'
 '\xbeaH'
 '\xa2\xb3~I'
 '\xbd\xc7\x01\x1eRESENTATION FORM FOR VERTICAL '
'\x1a'
 '\x80\x05\x02CO'
 'ZE'
 '\xfc\x8e~\x10HORIZONTAL ELLIP'
 '\xd8\xf0\x01\x0bIDEOGRAPHIC'
 '\xa4\x7f\x05LEFT '
 '\xae\xf4}Q'
 '\xa8\x8a\x02\x06RIGHT '
 'gS'
'\x02'
 '\xc1\x89~\x02EM'
'\x06'
 '\x8a\x01S'
 ']\x14WHITE LENTICULAR BRA'
'\x04'
 '\xce\x8f~C'
 '\r\x02KC'
'\x02'
 '\x85m\x04QUAR'
'\x04'
 '^S'
 '\x8d\x8f~\x10WHITE LENTICULAR'
'\x04'
 '\x0b '
'\x04'
 '\xa6\xf7}C'
 '\xbf|F'
'\x02'
 '\xb1\xb2}\x05XCLAM'
'\x04'
 '\x9e\xbd}L'
 '\xdb9M'
'\x86\x02'
 '\x92\x06A'
 '\xadz\tOENICIAN '
':'
 '\x9c\x02\x07LETTER '
 '\xf0~\x07NUMBER '
 ']\x04WORD'
'\x02'
 '\xe5b\x05 SEPA'
'\x0c'
 '\xf0\x00\x02ON'
 '\xb3\x7fT'
'\x08'
 '\x92\xbb}E'
 '\xe67H'
 '\xbb\x8d\x02W'
'\x04'
 '\x96QE'
 '\x93\xdf}O'
'\x04'
 '\x0bE'
'\x05'
 '\xbfP '
','
 '\x8e\x03A'
 '\xd6\x87~B'
 '\xa4\xa6\x7f\x03DEL'
 '\xd4\x0e\x03GAM'
 '\xa8\x96\x01\x02HE'
 '\xaa\xf2\x00K'
 '\xe0\xf2}\x03LAM'
 '\x9a\xc2\x00M'
 'nN'
 '\xaa\xb7\x7fP'
 '\xbc\xc9\x00\x02QO'
 '\xec\x88\x01\x02RO'
 '\xfa\xfb\x00S'
 '^T'
 '\xcaAW'
 '\x9a\xb7~Y'
 '\xa3\xe8\x00Z'
'\x04'
 '\xde\xf9}A'
 '\xf7\xb4\x7fE'
'\x06'
 '\xf2\xc3}A'
 '\x94i\x02EM'
 '\xcb\xcc\x00H'
'\x04'
 '\x96\xb7}I'
 '\xcf\xc3\x00L'
'\xcc\x01'
 '\xe0\r\x06GS-PA '
 '\x91s\x10ISTOS DISC SIGN '
'\\'
 '\xca\xf2}A'
 '\x86\x99\x02B'
 '\xb2}C'
 '`\x02DO'
 '\xe4\xaa}\x02EA'
 '\x88\xd5\x02\x02FL'
 '\xba\x7fG'
 '\xb6\x7fH'
 '\\\x02LI'
 '@\x02MA'
 '\x98\xa5~\x02OX'
 '\xb6\xd9\x01P'
 'NR'
 '\xd2~S'
 '\x86\x7fT'
 '\x92\xec}V'
 '\xc3\x93\x02W'
'\x04'
 '\xf8S\x05AVY B'
 '\xefqO'
'\x06'
 '\xcc\x00\x05ATTOO'
 '\x8e\xc9}I'
 '\x8d\xc2\x00\x03UNN'
'\x02'
 '\x15\x03ED '
'\x02'
 '\x93\xa8\x7fH'
'\x0c'
 '\xb2\xc8}A'
 '\xcc\xb8\x02\x02HI'
 '\xa2\xb6}L'
 '\xb0u\x07MALL AX'
 '\xf97\x04TRAI'
'\x04'
 '\x1aE'
 '\xeb\xa6}P'
'\x02'
 '\x87\xb2}L'
'\x04'
 '\x8a\xaf}A'
 '\xa9\xfa\x01\x04OSET'
'\x08'
 '\x9c\x01\x03APY'
 '\x8c\xb4}\x07EDESTRI'
 '\xaf\xcb\x02L'
'\x04'
 '(\x03ANE'
 '\xed|\x02UM'
'\x02'
 '\xb9\xe7}\x02 T'
'\x02'
 '\xf7\xfc~R'
'\x04'
 '(\x02NA'
 '\x8d\xa6\x7f\x02TT'
'\x02'
 '\xb3\xa7\x7fC'
'\x04'
 '\xaa\xa4}D'
 '\xeb\xe2\x00L'
'\x06'
 '*E'
 '\xbe\xba}I'
 '\xd3\xe4\x00O'
'\x02'
 '\x0bL'
'\x02'
 '\xc7\xfe}M'
'\x04'
 '\xb0\xfe}\x05AUNTL'
 '\x87\x82\x02R'
'\x02'
 '\xabGA'
'\x02'
 '\xd3\xa5\x7fU'
'\x04'
 '\xfe\xaa}L'
 '\xaf|V'
'\x10'
 '\xd6\x01A'
 '\x80z\x02HI'
 '\xee\x05L'
 '\xfb~O'
'\x06'
 '\xea\x00L'
 '\xb9\x7f\x02MB'
'\x05'
 '\xfd\xb9}\rINING OBLIQUE'
'\x02'
 '\xd1\xab}\x02UM'
'\x02'
 '\x8b\x8d\x7fU'
'\x06'
 '\xe0\x00\x02PT'
 '\x84\xe3}\x0bRPENTRY PLA'
 '\x83\xbd\x7fT'
'\x02'
 '\xc3\xe3}I'
'\n'
 '\x8c\x01\x02EE'
 'FO'
 'e\x04ULLS'
'\x02'
 '\x8d\x8d~\x02 L'
'\x04'
 '$\x03OME'
 '\xf7\x9e}W'
'\x02'
 '\xff\xd1}R'
'\x05'
 '\xdb~H'
'p'
 '\xec\x02\x04DOUB'
 '\xf8\x00\x07LETTER '
 '\xb8\x7f\x05MARK '
 '\xd7}S'
'\n'
 '\xf8\x01\x03ING'
 '\xaf~U'
'\x08'
 '\xe6\x00B'
 'm\x0fPERFIXED LETTER'
'\x02'
 '\xc7\xbd} '
'\x06'
 '\xc5\x00\x0eJOINED LETTER '
'\x06'
 '\x8a\xb1}R'
 '\x02W'
 '\x03Y'
'\x02'
 '\xa9\x9b}\x07LE HEAD'
'\x04'
 '0\x08DOUBLE S'
 '\x03S'
'\x02'
 '\xe7\xf8~H'
'`'
 '\xc2\x05A'
 '\xae\xaa}B'
 '\xea\xd4\x02C'
 'ZD'
 '\x8a\xcd}E'
 '\xba^F'
 '\x86\xb4\x01G'
 '\xfe\xcb~H'
 '\xfajI'
 '\x8a\x15J'
 '\xda\xaa\x01K'
 '\xaa\xd5~L'
 '\x02M'
 '\x82\xf6\x01N'
 '\xfa\xf4}O'
 '\xe2\xbf\x01P'
 '\xaa\xd5~Q'
 '\x02R'
 '\x82\xd4\x02S'
 'JT'
 '\xb2\x97}U'
 '\x90\xe8\x02\x05VOICE'
 '\xfa\xac}W'
 '\x02X'
 '\x02Y'
 '\xdb\xaa\x01Z'
'\x04'
 '*D'
 '\xcd\xba~\x04LESS'
'\x02'
 '\xc7\xb8} '
'\x0c'
 '\xae\x97}A'
 '\x8a\x15H'
 '\xda\xaa\x01S'
 '\x03T'
'\x06'
 '\xf6\x96}A'
 '\x8a\x15H'
 '\x91\xfb\x01\x04MALL'
'\x06'
 '\xb6\x96}A'
 '\x8a\x15D'
 '\x03Z'
'\x06'
 '\x1aA'
 '\xff\xaa}H'
'\x05'
 '\x0bN'
'\x02'
 '\x19\x04DRAB'
'\x02'
 '\x11\x02IN'
'\x02'
 '\xdf\xe1}D'
'\x07'
 '\xf4\x00\x08LTERNATE'
 'a\x08SPIRATED'
'\x02'
 '\x0b '
'\x02'
 '\xc7\xa9}F'
'\x02'
 '\x0b '
'\x02'
 '\xa7\xa9}Y'
'\x08'
 '\xca\xa5} '
 '\xb8\x91\x01\nMANENT PAP'
 '\xf0\xe5~\x08PENDICUL'
 '\xb5\xee\x01\x08SON WITH'
'@'
 '\xde\x04L'
 '\xbf{R'
'<'
 '\xd2OA'
 '\xa41\x0bENTHESIZED '
 '\x81\xa3}\x08TNERSHIP'
'8'
 '\x90\x03\x12KOREAN CHARACTER O'
 '\xa5~\x15LATIN CAPITAL LETTER '
'4'
 '\x92\x90}A'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02I'
 '\x02J'
 '\x02K'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x02O'
 '\x02P'
 '\x02Q'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x02U'
 '\x02V'
 '\x02W'
 '\x02X'
 '\x02Y'
 '\x03Z'
'\x04'
 '" '
 '\xc5\x98}\x02JE'
'\x02'
 '\xbb\xda}H'
'\x04'
 '2L'
 '\x99\x84~\x06M BRAN'
'\x02'
 '\x83\xa1}A'
'\xfa\x03'
 '\xee\tL'
 '\xa0\x7f\x04NE D'
 'd\x06PEN SU'
 '\xba}R'
 '\xa0{\x07SMANYA '
 '\xc5\x94}\x0fUTLINED WHITE S'
'P'
 '\xe6\xcc}D'
 '\xd9\xb3\x02\x07LETTER '
'<'
 '\xfa\x03A'
 '\xb6\x9c}B'
 '\xb2\xe3\x02C'
 '^D'
 '\xbe\xbe}E'
 '\xba^F'
 '\x02G'
 '\x02H'
 '\xfajI'
 '\x8a\x15J'
 '\xea\xe2\x02K'
 '\x9c\x97}\x02LA'
 '\xd2\xe8\x02M'
 '\xc8\xd5}\x02NU'
 '\xdehO'
 '\x86\xe6\x01Q'
 '\x86\xf9}R'
 '\xb2\xe2\x02S'
 '\xd2\x9d}T'
 '\xfajU'
 '\xa6\xf7\x02W'
 '\xe6\x9d}X'
 '\x03Y'
'\x02'
 '\x8b\xa9}A'
'\x04'
 '\xc6\x88}A'
 '\xdf\xf7\x02H'
'\x02'
 '\xdf\xd4}I'
'\x04'
 '\xce\xa0\x7fA'
 '\xcb\xfc}H'
'\x04'
 '\xfa\x85~E'
 '\xfb\x96\x7fH'
'\x02'
 '\x81\x92}\x02AY'
'\x07'
 '\xaa\x87}A'
 '\xc3\x92\x02L'
'\x0c'
 '\x9c\x02\t WITH DOT'
 '\xb1~\x04IYA '
'\n'
 '\xb0\x01\x07LETTER '
 '\x87\x7fV'
'\x06'
 '\xd5\x00\x12OWEL SIGN VOCALIC '
'\x06'
 '\xaa\x97~L'
 '\xf3\xf6~R'
'\x04'
 '\x8a\x9a}V'
 '\x03W'
'\x02'
 '\xc5\x9b}\x05 INSI'
'\x04'
 '\xfa\xb4\x7fB'
 'oP'
'\x02'
 '\xc9\x00\x0fOT OVER TWO DOT'
'\x02'
 '\xaf\xd5}S'
'\x96\x03'
 '\xc4\x18\x07 CHIKI '
 '\xf9g\x02D '
'\xb6\x02'
 '\xe0\x10\x08PERSIAN '
 '\xd0x\x0eSOUTH ARABIAN '
 '\x85x\x0eTURKIC LETTER '
'\x92\x01'
 '\xf8\x03\x07ORKHON '
 '\xdd|\x08YENISEI '
'>'
 '\xd2\x01A'
 '\x9e\x7fE'
 'nI'
 'SO'
'\x06'
 '\x1aE'
 '\xa3\x80}Q'
'\x05'
 '\x9f\x80}K'
'\x05'
 '\x8b\x80}Q'
'\x0f'
 '\xf6\xff|C'
 '\xca\x80\x03N'
 '\xd6\x93}S'
 '\xe7kZ'
'\x06'
 '\xb6\xff|C'
 '\x02T'
 '\x03Y'
"'"
 '\x92\xff|B'
 '\x02D'
 '\xf2\x81\x03E'
 '\x92\xfe|G'
 '\x02L'
 '\xb6\x0fN'
 '\xcepQ'
 '\x02R'
 '\x9e\x14S'
 '\xe6kT'
 '\x03Y'
'\x11'
 '\x8e\xfe|B'
 '\x02G'
 '\x02K'
 '\x82\xc5\x02N'
 '\x82\xbb}T'
 '\x03Y'
'T'
 '\x9a\x02A'
 '\x92\xd2~B'
 '\xe2\xac\x01E'
 'fI'
 'SO'
'\r'
 '\xe2|E'
 '\xa2\x80}P'
 '\x02Q'
 '\x03T'
'\x07'
 '\xd2\xfc|C'
 '\x03Q'
'\x14'
 '\xb6\xfc|C'
 '\x9e\x01L'
 '\xe6~M'
 '\xae\x84\x03N'
 '\xd6\xfb|P'
 '\x9e\x14S'
 '\xe7kZ'
'\x08'
 '\xd2\xfb|C'
 '\x02G'
 '\x02T'
 '\x03Y'
'-'
 '\xa6\xfb|B'
 '\x02D'
 '\xde\x85\x03E'
 '\xa6\xfa|G'
 '\x02L'
 '\x02N'
 '\x02Q'
 '\x02R'
 '\xfe\xe5\x00S'
 '\x86\x9a\x7fT'
 '\x03Y'
'\x14'
 '\xa2\xfa|B'
 '\x02D'
 '\x02G'
 '\x02K'
 '\x02L'
 '\x02N'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x03Y'
'@'
 '\xd0\x01\x07LETTER '
 '\xf1~\x03NUM'
'\x06'
 '\xd4\x00\x04BER '
 '\x81\xaa\x7f\nERIC INDIC'
'\x04'
 '\x1aF'
 '\x93\xbb}O'
'\x02'
 '\x99\xef}\x02IF'
':'
 '\xb6\x05A'
 '\xaa\xc3~B'
 '\x8a\xbc\x01D'
 '\xda\xf7|F'
 '\xfa\x87\x03G'
 'bH'
 'bK'
 'fL'
 '\xd2\xc1}M'
 'nN'
 '\xb2\xbe\x02Q'
 '\x82\x8d\x7fR'
 '\x8a\xf2\x00S'
 '\xb2\x7fT'
 '\x9amW'
 '\xca\x12Y'
 '\xcfnZ'
'\x02'
 '\x0bO'
'\x02'
 '\xa3\x8a}D'
'\x08'
 '\xa2\x96}A'
 '\xe2sE'
 '\xaf\xf6\x02H'
'\x04'
 '\xf2\x95}A'
 '\xe3sE'
'\x08'
 '\x1aA'
 '\xc7\xc1}H'
'\x06'
 '\xc6\x00D'
 'bM'
 '\xe3\xf4|T'
'\x02'
 '\x0bE'
'\x02'
 '\xef\x88}K'
'\x02'
 '\x8b\xf9|H'
'\x02'
 '\xab\xc4~O'
'\x02'
 '\x8d~\x03AME'
'\x04'
 '\xfa\xc3~A'
 '\xef\x00H'
'\x04'
 '\x0bE'
'\x05'
 '\xeb\x87}T'
'\x04'
 '\xf2kH'
 '\xab\x14I'
'\x02'
 '\xaf\xf1}M'
'\x06'
 ':A'
 'a\x02HA'
'\x04'
 '\xae~D'
 '\xaf\xc5~L'
'\x02'
 '\xbb\xc3~L'
'\x04'
 '\xfa\x84\x7fL'
 '\xff\xf7}Y'
'd'
 '\xc4\x06\x07NUMBER '
 '\x94z\x05SIGN '
 '\xa7\xba}W'
'X'
 '\x96\x05A'
 'FB'
 '\xea\x81}C'
 '\xba\xfd\x02D'
 '\xca\x82}F'
 '\x9e\xfd\x02G'
 '\xe6\x82}H'
 '\xfajI'
 '\xde\x91\x03J'
 '\xca\x00K'
 '\xe6\x82}L'
 '\xbe\x85\x01M'
 '\xe2\xf7\x01N'
 '\xe6\x82}P'
 '\x9e\xfd\x02R'
 '\x92\xaf~S'
 '\xc6\xd0\x01T'
 '\x8a\xee|U'
 '\xde\x91\x03V'
 '\xae\x7fX'
 '\x82\x84}Y'
 '\x03Z'
'\x04'
 '\xf6\xee|A'
 '\xcd\x91\x03\x08SHAAYATH'
'\x02'
 '\x93ZI'
'\x04'
 '\xa2\xee|A'
 '\x03I'
'\x06'
 '\x86\xee|A'
 '\x8a\x15H'
 '\xfbjU'
'\x04'
 '\xda\xed|A'
 '\x03U'
'\n'
 '"A'
 '\x9e\xed|I'
 '\x03U'
'\x07'
 '%\x07HYAAUSH'
'\x05'
 '\xf7\xd6~-'
'\x06'
 '&A'
 '\x81\x88\x7f\x03UUM'
'\x05'
 '\xbf\x81}G'
'\t'
 '-\tURAMAZDAA'
'\x07'
 '\xf6\xd5~-'
 '\x87\xab~H'
'\n'
 '\x9e\x8c\x7fH'
 '\xb2\xa2~O'
 '\xe7\xd1\x02T'
'\x06'
 '\xd6\xf5|E'
 '\x9f\xc5\x02W'
'`'
 '\xfaOA'
 '\xfe\xdb}D'
 '\x96\xd7\x02G'
 '\xc8\x00\x07LETTER '
 '\xf4~\x02MU'
 '\xca~P'
 '\xa1\xfd~\x02RE'
'\x06'
 '\xd8\x9d~\x05HAARK'
 '\x89\xe3\x01\x0bUNCTUATION '
'\x04'
 '0\x08DOUBLE M'
 '\x03M'
'\x02'
 '\xb9\xc6~\x03UCA'
'\x04'
 '\xd0\xe7~\x06 TTUDD'
 '\xf1\x98\x01\x02-G'
'\x02'
 '\x8d\xe7~\rAAHLAA TTUDDA'
'<'
 '\xca\x02A'
 'NE'
 'FI'
 'FL'
 'NO'
 'OU'
'\x08'
 '\xea\xe6|C'
 '\x02D'
 '\xbe\nN'
 '\xc7uY'
'\x08'
 '\xb6\xe6|B'
 '\x02H'
 '\x9e\x01T'
 '\xe7~V'
'\x0c'
 '\xb6\x90~A'
 '\xce\xd5~E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x08'
 '\xc6\xe5|H'
 '\xea\xe2\x00N'
 '\x9a\x9d\x7fR'
 '\x03S'
'\x08'
 '\xaa\xf0|D'
 '\xe2tN'
 '\x02P'
 '\xf7\x08R'
'\x10'
 ':A'
 '\x9e\xe4|G'
 '\x02L'
 '\xb6\x0fN'
 '\xcfpT'
'\x08'
 '\x9a\xe4|J'
 '\x02K'
 '\x02M'
 '\x03W'
'\xd0\x02'
 '\x9e\x11E'
 '\xc0t\x03KO '
 '\xd7zO'
'\x1e'
 '\xfe\x04 '
 '\xad{\x04RTH '
'\x1c'
 '\x96\xda~E'
 '\xb4\xa6\x01\x06INDIC '
 '\xdb\xd8~W'
'\x14'
 '\xfc\x01\tFRACTION '
 '`\tPLACEHOLD'
 '@\x03QUA'
 'm\x04RUPE'
'\x02'
 '\xff\xe0|E'
'\x04'
 '\xe8\xe0|\x05NTITY'
 '\xd5\x9f\x03\x02RT'
'\x02'
 '\x0bE'
'\x02'
 '\x9f\xe0|R'
'\x0c'
 '\xa4\x01\x04ONE '
 '\x9d\x7f\x06THREE '
'\x04'
 '\xc2\x00Q'
 '\xf1\xf2|\tSIXTEENTH'
'\x02'
 '\xe5\xe5}\x03UAR'
'\x08'
 '\xa4\xf3|\x04EIGH'
 '\xae\x90\x02H'
 'VQ'
 '\xe9\xef}\x05SIXTE'
'\x02'
 '\x15\x03ENT'
'\x02'
 '\x87\xc1}R'
'v'
 '\xd8\x07\x03COM'
 '\xb2\x97}D'
 '\xea\x8b\x02E'
 '\xe8\xd7\x00\x04HIGH'
 '\x96\x7fL'
 '\xa1\x7f\x07SYMBOL '
'\x04'
 '\xc8\x00\x07GBAKURU'
 '\x01\x06OO DEN'
'\x02'
 '\x9f\x9f}N'
'F'
 '\xa4\xeb|\x07AJANYAL'
 '\x8c\x96\x03\x06ETTER '
 '\xb9\x7f\x02OW'
'\x02'
 '\xedf\x0e TONE APOSTROP'
'B'
 '\xe6\xda|A'
 '\x8a\x15B'
 '\xfe\x0bC'
 '\xa4\x88\x03\x02DA'
 '\xaa\x8d}E'
 '\xba^F'
 '\x8e\x94\x03G'
 '\xf6\xeb|H'
 '\xfajI'
 '\xba\xa8\x03J'
 '\xd2\xec|K'
 '\x02L'
 '\x02M'
 '\xe2\x92\x03N'
 '\x9a\x8e}O'
 '\x8a_P'
 '\xc2\x92\x03R'
 '\xc2\xed|S'
 '\x02T'
 '\xfajU'
 '\x8a\x15W'
 '\x03Y'
'\x04'
 '\xb6\xd8|A'
 '\x8b\x15R'
'\x0b'
 '\x1aA'
 '\x01\x02YA'
'\x05'
 '\x1d\x05 WOLO'
'\x02'
 '\xd7\x8a}S'
'\x08'
 '\xc6\xd7|A'
 '\xed\xa8\x03\x04ONA '
'\x06'
 '\x96\xf8|C'
 '\x86tJ'
 '\x03R'
'\x02'
 '\xf3\xeb|B'
'\x05'
 '\xcd\xa2}\x05GBASI'
'\x14'
 '4\x07BINING '
 '\x83\xeb|M'
'\x12'
 '\xf8\x02\x06DOUBLE'
 '\xb4\x7f\x05LONG '
 '\xe8\xb4}\x03NAS'
 '\xf5\xc9\x02\x06SHORT '
'\x06'
 '\x8a\x01H'
 'nL'
 '\xaf\x7fR'
'\x02'
 '\x11\x02IS'
'\x02'
 '\x15\x03ING'
'\x02'
 '\x11\x02 T'
'\x02'
 '\x87\x97}O'
'\x02'
 'U\x02OW'
'\x02'
 'A\x03IGH'
'\x08'
 '\x90\x7f\x07DESCEND'
 '\xd6\x00H'
 'nL'
 '\xaf\x7fR'
'\x02'
 '\x11\x02 D'
'\x02'
 '\xad\xb1}\x02OT'
'\xbc\x01'
 '\xf0\x08\x07GATIVE '
 '\xfe\xed~U'
 '\x85\x8a\x01\nW TAI LUE '
'\xa6\x01'
 '\xce\x92}D'
 '\xec\xf1\x02\x07LETTER '
 'l\x08SIGN LAE'
 '\x9a\x7fT'
 '\xed}\x0bVOWEL SIGN '
'"'
 '\xea\x01A'
 '\xba\xce|E'
 '\xae\xb1\x03I'
 'fO'
 'JU'
 '\xe1\x8b}\x0bVOWEL SHORT'
'\x0b'
 '"E'
 '\x86\xcf|U'
 '\x03Y'
'\x05'
 '\x83\xcf|Y'
'\t'
 'jA'
 '\x87\xcf|Y'
'\x04'
 '\xd2\xce|I'
 '\x03Y'
'\x08'
 '\xb2\x7fA'
 '\x86\xcf|E'
 '\x03Y'
'\x06'
 '\x84z\nHAM DIGIT '
 '\xfd\x8a~\x08ONE MARK'
'\x05'
 '\xa7\xcd|V'
'f'
 '\xf0\x02\x06FINAL '
 '\xe4}\x04HIGH'
 '\x01\x03LOW'
','
 '\x0b '
','
 '\xb6\xe1|B'
 '\x02D'
 '\x02F'
 '\x02H'
 '\x9a\xa0\x03K'
 '\xea\xdf|L'
 '\x02M'
 '\x86\xb4\x01N'
 '\xd6vP'
 '\xaa\xd5~Q'
 '\xba\xa0\x03S'
 '\xf6\x8b~T'
 '\xd6\xd3~V'
 '\x9a\xa0\x03X'
 '\xeb\xdf|Y'
'\x04'
 '\xde\xca|A'
 '\x8b\x15V'
'\x04'
 '\xbe\xca|A'
 '\x8b\x15U'
'\x0e'
 '\x9e\xca|B'
 '\x02D'
 '\x02K'
 '\x02M'
 '\x82\xc5\x02N'
 '\x83\xbb}V'
'\x14'
 '\x94\x02\x08CIRCLED '
 '\xc5~\x08SQUARED '
'\x0e'
 '\x9a\xcf|I'
 '\xf4\xb1\x03\x15LATIN CAPITAL LETTER '
 '\xf2\xdc|P'
 '\x03S'
'\x08'
 '\xe6\xc7|J'
 '\x02L'
 '\x02M'
 '\x03P'
'\x06'
 '\xfc\xea}\x02DI'
 '\x81\x96\x02\x15LATIN CAPITAL LETTER '
'\x04'
 '\xba\xc6|H'
 '\x03P'
'\xb2\x06'
 '\xbe\xd3\x00A'
 '\xbeqE'
 '\x96XO'
 '\xa8\xaa|"USICAL SYMBOL MULTIPLE MEASURE RES'
 '\xb9\xba\x03\x07YANMAR '
'\xdc\x01'
 '\x9c\x19\x0fCONSONANT SIGN '
 '\xf6vL'
 '\xa4\x86}\x1fMODIFIER LETTER KHAMTI REDUPLIC'
 '\x92\xf2\x02S'
 '\xb4\x7f\x15TONE MARK SGAW KAREN '
 '\x91{\x0bVOWEL SIGN '
'"'
 '\xc8\xdb}\x07AITON A'
 '\x9aDE'
 '\xf8\xe4\x02\nGEBA KAREN'
 'X\x06KAYAH '
 '`\x04MON '
 '\xba~S'
 '\xac\xf2}\x02TA'
 '\xb1\x8d\x02\x12WESTERN PWO KAREN '
'\x04'
 '\x9a\x8b}E'
 '\xa7\xb8\x7fU'
'\n'
 '\xb0\x01\nGAW KAREN '
 '\xa1\x7f\x04HAN '
'\x08'
 '\x82\xd3|A'
 '\xca\xad\x03E'
 '\x99\xa0}\x06FINAL '
'\x05'
 '\x83\x9c} '
'\x02'
 '\xc3\x89}E'
'\x04'
 '\xea\xee|I'
 '\x9fNO'
'\x06'
 '\xb2\xc1|E'
 '\x02O'
 '\xb7{U'
'\x02'
 '\xa3\xee| '
'\x04'
 '4\x03HAT'
 '\xbd\xe7}\x04KE P'
'\x02'
 '\xd7\xed|H'
'@'
 '\xd4\xf0}\x03HAN'
 '\xd8\x91\x02\x04IGN '
 '\xb5~\x06YMBOL '
'\n'
 '\x88\x01\x06AITON '
 '\xbd\x7f\x05SHAN '
'\x04'
 '\x1aE'
 '\x9b\xfd|O'
'\x02'
 '\xa5\x8c}\x05XCLAM'
'\x06'
 'VE'
 '\x9a\xfd|O'
 '\xbf\x83\x03T'
'\x02'
 '\xbf\xec|W'
'"'
 '\xe2\xed}A'
 '\x9c\x97\x02\x0cKHAMTI TONE-'
 '\x94`\tPAO KAREN'
 '\xec\xbf~\x13RUMAI PALAUNG TONE-'
 '\x9c\xde\x01\x05SHAN '
 'M\x17WESTERN PWO KAREN TONE-'
'\n'
 '\xc6\xb6|1'
 '\x022'
 '\x023'
 '\x024'
 '\x035'
'\x0e'
 '\xf4\x00\x08COUNCIL '
 'U\x05TONE-'
'\x08'
 '\xc6\xb5|2'
 '\x023'
 '\x025'
 '\x036'
'\x06'
 '\xfc`\x08EMPHATIC'
 '\xd1\x1f\x05TONE-'
'\x04'
 '\xca\xb4|2'
 '\x033'
'\x04'
 '\xae\xb4|1'
 '\x033'
'd'
 '\x9c\x01\x06ETTER '
 'M\x0fOGOGRAM KHAMTI '
'\x06'
 '\xde\xbb|H'
 '\x82\xf9\x01O'
 '\x87\x89~Q'
'^'
 '\x90\x96\x7f\x05AITON'
 '\x9c\xf1\x00\x12EASTERN PWO KAREN '
 '\xa2\xed}G'
 '\x94\x91\x02\x07KHAMTI '
 '\xa8\x7f\x04MON '
 '\x9c\x99\x7f\rRUMAI PALAUNG'
 '\x86\xe5\x00S'
 'Q\x12WESTERN PWO KAREN '
'\x04'
 '\x1aP'
 '\xe3\xd0|T'
'\x02'
 '\xe3\xc4|W'
'\x1e'
 '\xcc\xd2}\tGAW KAREN'
 '\x89\xae\x02\x04HAN '
'\x1c'
 '\xee\xae|A'
 '\x8a\x15B'
 '\x02C'
 '\x02D'
 '\x02F'
 '\x02G'
 '\x02H'
 '\xda\xaa\x01K'
 '\x86!N'
 '\xa2\xc0~P'
 '\x02T'
 '\x87tZ'
'\n'
 '8\x02BB'
 '\xae\xad|E'
 '\x86!J'
 '\x83\x08N'
'\x04'
 '\xaa\xad|A'
 '\x03E'
'&'
 '\xee\xec}C'
 '\xba\x94\x02D'
 '\xf2\xc0|F'
 '\x02G'
 '\xda\xaa\x01H'
 '\x02J'
 '\x86!N'
 '\xa6\xb4~R'
 '\x02S'
 '\xd8\xaa\x01\x02TT'
 '\xaa\xd5~X'
 '\x03Z'
'\x06'
 '\xc6\xeb}D'
 '\xab\xd5~H'
'\x06'
 '*G'
 '\xaa\xcd|N'
 '\x97\xae\x03Y'
'\x02'
 '\xbb{H'
'\x10'
 '\xd2\x00M'
 'q\x0bSHAN MEDIAL'
'\x02'
 '\xe7z '
'\x0e'
 '\xf8\x00\x06EDIAL '
 ']\nON MEDIAL '
'\x06'
 '\xe2\xbe|L'
 '\x02M'
 '\x03N'
'\x08'
 '\xbe\xbe|H'
 '\x02R'
 '\x02W'
 '\x03Y'
'\xb6\x02'
 '\x90\x03\x0eDIFIER LETTER '
 '\xea}N'
 'cU'
'\x02'
 '\x0bN'
'\x02'
 '\xe7\xf6|T'
'\x08'
 '\x8c\xc9|\x1fGOLIAN LETTER MANCHU ALI GALI L'
 '\xb9\xb8\x03\nOGRAM FOR '
'\x06'
 '2E'
 'cY'
'\x04'
 '\xd6\xb5|A'
 '\x97{I'
'\x02'
 '\x9d\xba|\x02AR'
'\xac\x02'
 '\xbc\x03\x05BEGIN'
 '\x96\x1cC'
 '\xf0~\x04DOT '
 '\xb2~E'
 '\xe4\x91|\nGEORGIAN N'
 '\x8c\xee\x03\x04HIGH'
 '\xbc|\x03LOW'
 '\xc8|\x03MID'
 '\xd0\xb4~\x08OPEN SHE'
 '\x90\xca\x01\x07RAISED '
 '\x92nS'
 '\xd3\xb6|U'
'\x90\x01'
 '\x92\x11H'
 '\xf4o\x05MALL '
 'Q\x08TRESS AN'
'\x04'
 '\x0bD'
'\x04'
 '\x0b '
'\x04'
 '\xc2NH'
 'oL'
'\x88\x01'
 '\xe2\x0fA'
 '\x9e\x7fB'
 '\xe2~C'
 '\xae\x7fD'
 'RE'
 '\xae\x95|F'
 '\x8a\xea\x03G'
 '\xba\x7fI'
 '\xa4\xbc|\x0fJ WITH CROSSED-'
 '\x9eZK'
 '\x82\xe9\x03L'
 '\xa6yM'
 '\xa8\x06\x07N WITH '
 'JO'
 'nP'
 '\xb0|\nREVERSED O'
 '\xb6\x02S'
 '\xaa|T'
 'FU'
 'VV'
 '\xd3~Z'
'\x07'
 '!\x06 WITH '
'\x04'
 '\xee\x00C'
 '\xaf\x7fR'
'\x02'
 ')\x08ETROFLEX'
'\x02'
 '\x11\x02 H'
'\x02'
 '\xdf\xd7}O'
'\x02'
 '\xe5\xad|\x02UR'
'\x05'
 '\x0b '
'\x02'
 '\xad\x7f\x04WITH'
'\x07'
 '& '
 '\x89\xf1|\x03PSI'
'\x02'
 '\xef\xa5|B'
'\x1b'
 '\x8a\x03 '
 '\x86\xe9|H'
 '\xbe\x96\x03O'
 '\x89~\x06URNED '
'\x12'
 '\xbe\x01A'
 '\xe2\x9a|H'
 '\x02I'
 '\xe6\xe4\x03M'
 'NO'
 '\xd3\x9b|V'
'\x02'
 '\x0bP'
'\x02'
 '\x11\x02EN'
'\x02'
 '\xfb\x9f| '
'\x05'
 '\xe1\xfb~\n WITH LONG'
'\x07'
 '\xde\x9a|E'
 '\xc7\xe5\x03L'
'\x02'
 '\xbf\xbb|P'
'\x02'
 '\x0bP'
'\x02'
 '\x1d\x05 HALF'
'\x02'
 '\xf7\xcc| '
'\x02'
 '!\x06WITH P'
'\x02'
 '\xa1{\x06ALATAL'
'\x08'
 '\xca{ '
 '\x92\x05C'
 'a\x06IDEWAY'
'\x02'
 '\x0bS'
'\x02'
 '\xfb\xe4| '
'\x04'
 '\xe2hH'
 '\xc9\x17\x04RIPT'
'\x02'
 '\xc7\xa7| '
'\x05'
 '\xe3\xc9|H'
'\x07'
 '\x19\x04PEN '
'\x04'
 '\xce\x97|E'
 '\x03O'
'\x04'
 ' \x03LEF'
 '\xc7xR'
'\x02'
 '\xefxT'
'\x04'
 '!\x06 WITH '
'\x04'
 '\x96}P'
 '\xfbzR'
'\x04'
 '\x1a '
 '\xa3\xab|O'
'\x02'
 '\x15\x03WIT'
'\x02'
 '\xab\xae|H'
'\x07'
 '\x1d\x05REEK '
'\x04'
 '\x16G'
 '\xcfYP'
'\x02'
 '\xbb\xd9|A'
'\x0b'
 '\xde\xa4|N'
 '\xea\x04S'
 '\x02T'
 '\x03Z'
'\x07'
 '\x86\xe4|E'
 '\xbd\x9c\x03\x08OTLESS J'
'\x02'
 '\x93~ '
'\x11'
 '\xacv\x07 WITH C'
 '\xb4\n\x07APITAL '
 '\xab\xc5|H'
'\n'
 '*I'
 '\x9a\x93|L'
 '\x02N'
 '\x03U'
'\x05'
 '\xf3| '
'\t'
 '\x88y\x05ARRED'
 '\xfa\xae|E'
 '\xc3\xd8\x03O'
'\x02'
 '\xa5x\x04TTOM'
'\x07'
 '\xde\x9c|I'
 '\x8b\xdb\x03L'
'\x04'
 '\xc6\xb6~E'
 '\xfd\xc9\x01\x08ORT EQUA'
'\x02'
 '\xe7\xb9~L'
'\n'
 '\x9a\xe5|C'
 '\x84s\x04DOWN'
 '\xf2\x85\x02E'
 '\xda\xa2\x01I'
 '\xb9\xd7|\x02UP'
'\x02'
 '\xa5\xdd~\tNVERTED E'
'\x0c'
 '\xd2\x01 '
 '\xd9~\x04DLE '
'\x06'
 '\xf4\x00\x06DOUBLE'
 '\xbf\x7fG'
'\x02'
 '\x15\x03RAV'
'\x02'
 '\x0bE'
'\x02'
 '\xc5\x9e}\x03 AC'
'\x04'
 '\x0b '
'\x04'
 'D\x04ACUT'
 'kG'
'\x06'
 '\x96\x01D'
 '\x87\x7fL'
'\x02'
 '\x19\x04EFT-'
'\x02'
 '\x19\x04STEM'
'\x02'
 '\x11\x02 T'
'\x02'
 '\x11\x02ON'
'\x02'
 '\x0bE'
'\x02'
 '\xa3p '
'\x04'
 '\x11\x02OT'
'\x04'
 '\x19\x04TED '
'\x04'
 '\xd2~L'
 '\xcf\x00T'
'\x1a'
 '\xda\x00 '
 '\xa9\xfe|\x0fER RIGHT CORNER'
'\x18'
 '\xec|\nCIRCUMFLEX'
 '\xd4\x05\x02DO'
 '\xf2xI'
 '\xcc\x06\x04LEFT'
 'X\x02RI'
 '\xe6\xa0|T'
 '\xf1\xde\x03\x02UP'
'\x02'
 '\xad\xe2~\x06 ARROW'
'\x04'
 'P\x03GHT'
 '\xff\x99|N'
'\x06'
 ',\x06 ARROW'
 '\xcb{-'
'\x05'
 '\xbf\x89~H'
'\x06'
 '\xa6|T'
 '\xc1\x02\x02WN'
'\x06'
 '\xd7z '
'\x12'
 '\xbefN'
 '\xf1\x19\x05XTRA-'
'\x0e'
 '4\x05HIGH '
 '\x89\x7f\x03LOW'
'\x08'
 '\xf6zD'
 '\xbc\x7f\x11EXTRA-LOW CONTOUR'
 'KL'
'\x06'
 '\xe6\x00H'
 '\xac\xdd}\x02SL'
 '\xbd\xa2\x02\x06VERTIC'
'\x02'
 '\xady\x02AL'
'\x02'
 'e\x07ORIZONT'
'D'
 '\xa8\x02\x07APITAL '
 '\x90\x7f\rHINESE TONE Y'
 '\xe2\xd8|O'
 '\x8d\xa7\x03\x07YRILLIC'
'\x02'
 '\xe3\xc7| '
'\x10'
 '$\x03ANG'
 '\x01\x02IN'
'\x08'
 '\x0b '
'\x08'
 '\xc6\x93|P'
 '\x8e=Q'
 '\x02R'
 '\xe5f\x02SH'
'0'
 '\xbe\xba|A'
 '\xde\xc7\x03B'
 '\xd6\x81|D'
 '\x02E'
 '\x02G'
 '\x02H'
 '\x02I'
 '\x02J'
 '\x02K'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x9e\x9a\x01O'
 '\xe6\xe5~P'
 '\xe6\xfd\x03R'
 '\x9e\x82|T'
 '\x02U'
 '\x02V'
 '\x03W'
'\x07'
 ')\x08EVERSED '
'\x04'
 '\xee\x81|E'
 '\x03N'
'\x05'
 '\x0bA'
'\x02'
 '\xd5\xed}\x05RRED '
'\x88\x01'
 '\xb4\r\x05DIUM '
 '\xccw\x0bETEI MAYEK '
 '\x81|\x07TRICAL '
'\x12'
 '\xe2\x03B'
 '\xa0\x7f\nLONG OVER '
 'jP'
 '\x94\x7f\x07SHORT O'
 '\x83\x7fT'
'\x08'
 '\xca\x01E'
 'ZR'
 '\xa9\x7f\nWO SHORTS '
'\x04'
 '\xb4\xfb|\x04JOIN'
 '\xff\x84\x03O'
'\x02'
 '\x99\xda}\x04VER '
'\x02'
 '\x0bI'
'\x02'
 '\x8d\xfc}\x02SE'
'\x02'
 '\x11\x02TR'
'\x02'
 'OA'
'\x02'
 'q\x03ENT'
'\x04'
 '\xc8\x00\x03SHO'
 '\xc5\x94|\x08TWO SHOR'
'\x02'
 '\xe3\xfd{R'
'\x02'
 '\xf1\xbf|\x02RE'
'p'
 '\xe4\x02\x04APUN'
 '\xa4\x05\x04CHEI'
 '\x8e\xb5|D'
 '\x9a\xc5\x03L'
 '\xe5~\x0bVOWEL SIGN '
'\x10'
 '\xfa\x00A'
 '\x00\x04CHEI'
 '\x02I'
 '\xc2\xd6}N'
 '\xc2\xa9\x02O'
 '\x00\x03SOU'
 '\x02U'
 '\x01\x02YE'
'\x02'
 '\x0bN'
'\x02'
 '\xe7\xba|A'
'H'
 '\xd4\x00\x06ETTER '
 'a\x02UM'
'\x02'
 '\xe5\xd6}\x03 IY'
'F'
 '\xd8\x8a\x7f\x02AT'
 '\x86\xfa\x00B'
 '\xa8\x9a|\x02CH'
 '\xba\xe5\x03D'
 'bG'
 'nH'
 '\xb6~I'
 '\xaa\x01J'
 'bK'
 '\xf8~\x03LAI'
 '\x00\x03MIT'
 '\xe6\x00N'
 'bP'
 '\xd6\xa9}R'
 '\xf2xS'
 '\xda\xdc\x02T'
 '\xae\x81|U'
 '\x8e\xa9\x01W'
 '\xc7\xff~Y'
'\x06'
 '\xce\x00H'
 'Q\x02IL'
'\x05'
 '\x19\x04 LON'
'\x02'
 '\xdf\xfe{S'
'\x02'
 '\xc7\xc2|O'
'\x06'
 '\xba\x7fA'
 '\x8b\xa3}H'
'\x08'
 '\x9a\x7fA'
 '\x01\x03GOU'
'\x06'
 '\xa6\x7fH'
 'Q\x02OK'
'\x04'
 '\xde\xa1}H'
 '\xbb\xe3~I'
'\x02'
 '\xf7\xf4{U'
'\x04'
 '\xce~H'
 '\x97\xf6{O'
'\x04'
 '\xae~H'
 '\x93\x86|I'
'\x04'
 '\xae\xf4{A'
 '\xbb\xac\x01H'
'\x02'
 '\x0bK'
'\x02'
 '\xe1\xa5|\x02HE'
'\x06'
 '\xf0\x00\x05BLACK'
 '\\\x07SMALL W'
 '\x03W'
'\x02'
 '\x15\x03HIT'
'\x02'
 '\x0bE'
'\x02'
 '\x8b\xf6| '
'\x96\x01'
 '\xb8\x0c\x0bHJONG TILE '
 '\xdayL'
 '\xcc\xf1{\x15P SYMBOL FOR LIGHTHOU'
 '\xa0\x8e\x04\x05RRIAG'
 '\x89|\x0bTHEMATICAL '
'\x12'
 '\x8c\x03\x05BOLD '
 'd\x15ITALIC SMALL DOTLESS '
 '\x88\x7f\x03LEF'
 '\x00\x04RIGH'
 'm\x0cSCRIPT SMALL'
'\x02'
 '\xd7\xfe{ '
'\x04'
 '\x11\x02T '
'\x04'
 '\xec\xa7~\tFLATTENED'
 '\xd9\xa0~\x07WHITE T'
'\x04'
 '\xda\xed{I'
 '\x03J'
'\x04'
 '8\x06CAPITA'
 '\x01\x04SMAL'
'\x02'
 '\x0bL'
'\x02'
 '\xb5W\x04 DIG'
'\x02'
 '\x9b\xfc{E'
'('
 '\xa4\x02\x07AYALAM '
 '\x99~\x02E '
'\x06'
 '\x92\x01A'
 '\xb9\x7f\x0cWITH STROKE '
'\x04'
 '\xc4\x00\nAND MALE A'
 '\xbf\xfc{S'
'\x02'
 '\x19\x04ND F'
'\x02'
 '\x0bE'
'\x02'
 '\x0bM'
'\x02'
 '\x0bA'
'\x02'
 '\xe7\x81|L'
'"'
 '\xe4\x88\x7f\x03DAT'
 '\xb0\xfa\x00\tFRACTION '
 '@\x0eLETTER CHILLU '
 '\xa4\x7f\x07NUMBER '
 'ZS'
 '\xcb\xe2~V'
'\x02'
 '\x91\xfb|\x05IGN A'
'\x06'
 '\x1aO'
 '\xf7\xaa|T'
'\x04'
 '\x0bN'
'\x04'
 '\x11\x02E '
'\x04'
 '\xb2\x88~H'
 '\xe3\tT'
'\x0c'
 '\xc2\xe7{K'
 '\x86\x92\x01L'
 '\x8a\xa5\x7fN'
 '\xebQR'
'\x06'
 '\xc8\x00\x04ONE '
 '\x81\x87\x7f\x07THREE Q'
'\x04'
 '\xf2\x8a~H'
 'WQ'
'X'
 '\x80\xc5~\x03AUT'
 '\xe4\xc2\x01\x02BA'
 '\xe0\xe6{\x0bCHRYSANTHEM'
 '\xf6\x98\x04E'
 'RF'
 '\xe8{\x05GREEN'
 '\x88\x9e~\x02JO'
 '\xe6\xe5\x01N'
 'FO'
 '\xa4\xe8{\x02PL'
 '\xac\x94\x04\x03RED'
 '\xaa\x02S'
 '\xae~T'
 '\xef~W'
'\x06'
 '\xde\x00E'
 '`\x04HITE'
 '\xd1\x87~\x02IN'
'\x02'
 '\xc1\xed{\x03 DR'
'\x02'
 '\x11\x02ST'
'\x02'
 '\x85\xee{\x03 WI'
'\x0c'
 '\xc0\x01\x03HRE'
 '\xed~\x02WO'
'\x06'
 '\x19\x04 OF '
'\x06'
 '\xb4\x9f~\x05BAMBO'
 '\x83\xe1\x01C'
'\x04'
 '\xfc\xe7|\x05HARAC'
 '\x91\xd5\x01\x02IR'
'\x06'
 '\xeb~E'
'\x12'
 '\xd8~\x04EVEN'
 '\x00\x02IX'
 '\x94\x02\x02OU'
 '\xb6\xde|P'
 '\xc5\x9f\x7f\x03UMM'
'\x02'
 '\x99}\x02TH'
'\x08'
 '\xe6~N'
 '\xc1\x01\x03RCH'
'\x02'
 '\xef\xea{I'
'\x08'
 '\xa8~\x02IN'
 '\x81\x01\x02OR'
'\x0c'
 '\xfc}\x02IV'
 '\xed~\x03OUR'
'\x08'
 '\xd6{A'
 '\xe5\x00\x04IGHT'
'\x04'
 '\xa6\xde{C'
 '\xed:\x02MB'
'\x8c\r'
 '\xa6\xd4\x00A'
 '\xd6lE'
 '\x9aFI'
 '\x8c\x7f\x04ONG '
 '\xb7zY'
'p'
 '\xb8\x03\x0cCIAN LETTER '
 '\xa5}\x05DIAN '
'6'
 '\xdc\x00\x07LETTER '
 '\xa1\xfb~\tTRIANGULA'
'4'
 '\xfe\x92|A'
 '\xf6HB'
 '\x02C'
 '\x02D'
 '\x8e7E'
 '\xf6HF'
 '\x02G'
 '\x02I'
 '\x02K'
 '\xfe\xb0\x03L'
 '\x86\xcf|M'
 '\x8e7N'
 '\xf6HO'
 '\x02Q'
 '\x02R'
 '\xf6\xa5\x04S'
 '\xa6\x80}T'
 '\xea\xd9~U'
 '\x02V'
 '\x03Y'
'\x05'
 '\x8b\xda{S'
':'
 '\x82\x91|A'
 '\xf2.B'
 '\x86\x9a\x7fD'
 '\x8e7E'
 '\xf6HG'
 '\x02H'
 '\x02I'
 '\x02J'
 '\xe2\xff\x02K'
 '\xa2\x80}L'
 '\x86\xa8\x04M'
 '\x8a\x8f|N'
 '\xf6HP'
 '\x02Q'
 '\x02R'
 '\x02S'
 '\xa6\xe5\x00T'
 '\xde\x9a\x7fU'
 '\x02W'
 '\x02X'
 '\x03Z'
'\x05'
 '\xfb\xd7{M'
'\x04'
 '\xac\xef{\x04DIVI'
 '\xa5\x96\x02\x10LEFTWARDS SQUIGG'
'\x8e\x05'
 '\xea1M'
 '\xdcT\x07NEAR B '
 '\xc4z\x03SU '
 '\x91\xfe}\x0bVRE TOURNOI'
'`'
 '\xe4\x00\x07LETTER '
 '\xb9\xa1~\x0bPUNCTUATION'
'\\'
 '\xca\x8b|A'
 '\xba^B'
 '\xda\xaa\x01C'
 '\xda\xef\x02D'
 '\xe6\xea|E'
 '\xee\xfa~F'
 '\xda\xaa\x01G'
 '\x02H'
 '\xa2\xc0~I'
 '\x8a\x15J'
 '\xda\xaa\x01K'
 '\xaa\xd5~L'
 '\x02M'
 '\x86\xb4\x01N'
 '\xc6\xed~O'
 '\x92\x89\x01P'
 '\x02S'
 '\xea\xed\x02T'
 '\xe6\x9b}U'
 '\xde\xcb~W'
 '\x02X'
 '\x02Y'
 '\xdb\xaa\x01Z'
'\x14'
 '\xb6\xd2{A'
 '\x8a\x15H'
 '\x90\x99\x04\x04ONE '
 '\xcb\x91}S'
'\x0c'
 '\xcc\x00\x04MYA '
 'a\x02NA'
'\x02'
 '\x0b '
'\x02'
 '\xa7\x84|P'
'\n'
 '\x92\x84|B'
 '\xe6\xb8\x02C'
 '\x86\xd7\x00J'
 '\xa6\xd2|N'
 '\xdf\x1cT'
'\x04'
 '\xc6\xd0{A'
 '\x8b\x15Z'
'\xa6\x03'
 '\xe0\x17\tIDEOGRAM '
 '\xfc}\nMONOGRAM B'
 '\x9dk\x02SY'
'\xb0\x01'
 '\xd4\x02\tLLABLE B0'
 '\x85~\x07MBOL B0'
'\x1c'
 '\xde\x011'
 '\xee\xb6}2'
 '\xf2\x003'
 '\x8a\xc8\x024'
 '\xda\xba}5'
 '\x8e\xc5\x026'
 '\xf2\xa4|7'
 '\xe7\xda\x038'
'\x08'
 '\xca\xcd{2'
 '\x023'
 '\x026'
 '\x039'
'\x04'
 '\x9e\xcd{3'
 '\x034'
'\x04'
 '\x82\xcd{7'
 '\x039'
'\x04'
 '\xe6\xcc{8'
 '\x039'
'\x94\x01'
 '\x9e\x100'
 '\x9e~1'
 '\xfe}2'
 '\x92~3'
 '\xfe}4'
 '\xe2}5'
 '\x82~6'
 '\xfa}7'
 '\x92\x7f8'
 'O9'
'\x04'
 '\x88\x92\x7f\x030 D'
 '\x01\x031 T'
'\x08'
 '\xd2\xb9|0'
 '\xb8\xed\x00\x021 '
 '\xa08\x025 '
 '\xb1\xa1\x02\x037 T'
'\x02'
 '\x8b\xcf{W'
'\x12'
 '\xf0\x01\x020 '
 '\xf8}\x031 D'
 '\xc0\xd8{\x022 '
 '\xe4#\x033 M'
 '\x8c\xcc\x01\x024 '
 '\xd0\xb7\x02\x025 '
 '\xf4\x01\x036 R'
 'n7'
 '\xad\xcd{\x038 Q'
'\x02'
 '\xd3\x95| '
'\x02'
 '\xcf\xb2}A'
'\x02'
 '\xb3\xfb{K'
'\x10'
 '\xc2\xab~0'
 '\xe6\x82\x011'
 '\xc4\xd3\x00\x022 '
 '\xe0\x92|\x035 J'
 '\x8c\xeb\x03\x036 T'
 '\x80\x02\x027 '
 'd\x028 '
 'm\x029 '
'\x02'
 '\xa3\x93|T'
'\x02'
 '\xe9\xb0}\x02RO'
'\x02'
 '\xaf\xf8{K'
'\x02'
 '\x97\xc9}P'
'\x12'
 '\xc8\x92|\x030 P'
 '\xc2\xef\x031'
 'l\x022 '
 'l\x023 '
 '\xfe\x99\x7f4'
 '\xc8\xbf~\x025 '
 '\xa8\xa6\x02\x027 '
 'f8'
 'o9'
'\x02'
 '\xff\xd9{ '
'\x02'
 '\x95\x91|\x02 S'
'\x02'
 '\xdb\xd9{J'
'\x02'
 '\xa3\xf6{R'
'\x02'
 '\xa7\xf7{N'
'\x02'
 '\xdf\xae~ '
'\x10'
 '\xec\x01\x020 '
 'l\x021 '
 '\xe4\x88\x7f\x022 '
 '\x88\xf7\x00\x023 '
 '\x94\xdb{\x024 '
 '\x86\xcf\x015'
 '\xd4\xd5\x02\x026 '
 '\xf5\x92\x7f\x038 N'
'\x02'
 '\x9b\xc7{J'
'\x02'
 '\xe7\x9a|A'
'\x02'
 '\x8b\xf4{S'
'\x02'
 '\xf7\xf3{W'
'\x10'
 '\xe0\xf3{\x030 N'
 '\x96\x90\x011'
 '\x84\xf1~\x032 Q'
 '\xc8\x8a\x04\x033 R'
 '\xb8\xf5{\x036 J'
 '\xe0\x8c\x04\x027 '
 '\xf6\xa4\x7f8'
 '\xef\xda\x009'
'\x02'
 '\x0b '
'\x02'
 '\x9b\xf2{P'
'\x02'
 '\x87\xf2{T'
'\x12'
 '\x88\xf3{\x030 Z'
 '\xe8~\x031 Q'
 '\xfe\x8f\x043'
 '\xa0\x81|\x024 '
 '\xb4\xf4\x03\x025 '
 '\x9a\n6'
 '\xf4\xc2{\x027 '
 '\x82\xbf\x038'
 '\xf9\xfd\x00\x039 P'
'\x02'
 '\xcb\xa8}U'
'\x02'
 '\xcf\xcb} '
'\x02'
 '\xd7\xd0| '
'\x10'
 '\xb6\xa5\x7f0'
 '\x9e\xc7\x001'
 '\xdc\xf9~\x022 '
 '\x84\xd6~\x023 '
 '\x9c\xc5\x02\x024 '
 '\xb8\xef{\x035 M'
 '\xae\x90\x046'
 'o7'
'\x02'
 '\xfb\xcf| '
'\x02'
 '\xdd\xd1{\x02 Q'
'\x02'
 '\xb7\xef{D'
'\x12'
 '\xce\x011'
 'n2'
 '\xea\x80}3'
 '\xe4<\x024 '
 '\xd6/5'
 '\xce\x92\x026'
 'b7'
 '\xba\xcb}8'
 '\xf1\xf4}\x029 '
'\x02'
 '\x0b '
'\x02'
 '\xf7\xec{D'
'\x02'
 '\x8f\xdd{ '
'\x02'
 '\xe3\xfc{ '
'\x02'
 '\xb7\x88| '
'\x0c'
 '.1'
 '\xdds\x06247 DI'
'\n'
 '\x82\x012'
 '\xba\x7f3'
 '\xf1r\x0556 TU'
'\x04'
 '\xe8\x86|\x053 ARE'
 '\xad\xee\x03\x045 ME'
'\x04'
 '\xe0g\x047 KA'
 '\xdd\x18\x058 KAN'
'\x02'
 '\x97pA'
'\xea\x01'
 '\xf6\x01B'
 '\xc5~\x08VESSEL B'
':'
 '\xcc\xa3}\x0215'
 '\xf6\xdc\x022'
 '\x8d\xa3}\x0230'
'6'
 '\xe2\xe3{0'
 '\x021'
 '\xda\x9c\x042'
 '\x97\xa0}5'
'\x0c'
 '\xfe\xb6{1'
 '\x022'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\xb0\x01'
 '\xba\x051'
 '\xe3z2'
'2'
 '\xae\x042'
 '\x82\x7f3'
 '\x8a~4'
 '\xff~5'
'\x12'
 '\xee\xb5{1'
 '\x022'
 '\x023'
 '\x80\xcb\x04\x034 D'
 '\x82\xb5{5'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x02'
 '\xb7\xb8\x7fA'
'\x10'
 '\xc8\x01\t0 WHEELED'
 '\x021'
 '\xc8\xb1}\r2 CHARIOT FRA'
 '\xe8\xff~\x053 WHE'
 '\xf2\x81\x7f5'
 '\x026'
 '\x028'
 '\x039'
'\x02'
 '\xad\xb4{\x06 CHARI'
'\x0c'
 '\xd8\xbb{\x050 SPE'
 '\x92>1'
 '\x8a\xb9\x7f2'
 '\xfc\xa3\x02\x053 SWO'
 '\x86\xdc}4'
 '\x036'
'\x04'
 '\xd8\x00\x080 FOOTST'
 '\x9d\x90~\x075 BATHT'
'\x02'
 '\xfb\xc0{O'
'~'
 '\x92\x080'
 '\xb6~2'
 '\xba\x7f3'
 '\xfa~4'
 '\xfe~5'
 '\xee~6'
 '\x86\x7f7'
 '\xbe\x7f8'
 'O9'
'\x04'
 '\x96\xb0{0'
 '\xa5\xdc\x02\x041 HE'
'\x0e'
 '\xe2\xaf{0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x039'
'\x12'
 '\x9e\xaf{0'
 '\x021'
 '\x022'
 '\x84\x14\x043 MO'
 '\xfek4'
 '\xe6\xda\x026'
 '\x9e\xa5}7'
 '\x028'
 '\x039'
'\x14'
 '\xa2\xae{0'
 '\x021'
 '\xf0\x85\x01\x052 GAR'
 ',\x053 ARM'
 '\xe6\xf9~4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x10'
 '\x8e\xad{0'
 '\xb0\xfb\x00\x041 HO'
 '\xd2\x84\x7f2'
 '\x023'
 '\x024'
 '\x027'
 '\x028'
 '\x91\x14\x059 CLO'
'\n'
 '\xf8\xa9}\x060 BRON'
 '\xa8\xdb\x00\x041 GO'
 '\xea\xa6}2'
 '\xe8\xce\x04\x035 W'
 '\x9b\xb1{6'
'\x06'
 '\xf8\xd0{\x030 O'
 '\x98\x1d\x031 W'
 '\xf3\xbc\x7f2'
'\n'
 '\xb4\x01\x040 WH'
 '\xec\x8b|\x071 BARLE'
 '\x94\xfd\x01\x042 OL'
 '\xcc\xf3}\x053 SPI'
 '\xb9\x87\x02\x065 CYPE'
'\x02'
 '\xc3\xdd|E'
'\x1c'
 '\xa4\xc5}\x020 '
 '\x00\x042 WO'
 '\xb0\x81~\x044 DE'
 '\xb2\xbc\x045'
 'J6'
 '\xb6\x7f7'
 'F8'
 'C9'
'\x04'
 '\x88\xc8{\x03F C'
 '\x81\xdf\x00\x04M BU'
'\x04'
 '\xc8\xc7{\x03F S'
 '\xcd\xdc\x01\x03M B'
'\x04'
 '$\x03F S'
 '\x01\x02M '
'\x02'
 '\xd9\xc3}\x04HE-G'
'\x04'
 '\xdc[\x03F E'
 '\xf9\xf6|\x03M R'
'\x06'
 '\x94F\x04 EQU'
 '\x84\xe4{\x03F M'
 '\xa1\x13\x07M STALL'
'\x86\x01'
 '\xdc\x00\x03BU '
 '\xad\xc8|\rITED LIABILIT'
'\x84\x01'
 '\x9a\xe5{D'
 '\xea\x8b\x02E'
 '\xb4\x94\x02\x07LETTER '
 '\xf2\xde{Q'
 '\xb2\x9e\x04S'
 '\xb9~\x05VOWEL'
'\x14'
 '\xe4\x00\x06 SIGN '
 '\xcd\xc6}\x0c-CARRIER LET'
'\x12'
 '\xc2\x00A'
 '\xb2\xd8{E'
 '\xb2II'
 '\x826O'
 '\x83JU'
'\x07'
 '\xde\xa1{I'
 '\x03U'
' '
 '\xd0\x01\x04IGN '
 '\xa0\x7f\x0cMALL LETTER '
 '\x85\x84~\x02UB'
'\x12'
 '\x8a\xc8{A'
 '\xcemK'
 '\x02L'
 '\x02M'
 '\x86\xb4\x01N'
 '\xfe\xcb~P'
 '\x02R'
 '\x03T'
'\x08'
 '\xe8\x00\x03KEM'
 '\xe6\xd9{L'
 '\x9c\xa6\x04\x03MUK'
 'm\x02SA'
'\x02'
 '\xfb\xd0{-'
'\x02'
 '\x8d\xd1{\x03PHR'
'8'
 '\xc2\xde|B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\xaa\xd5~H'
 '\xda\xaa\x01J'
 '\x02K'
 '\xaa\xd5~L'
 '\x02M'
 '\x86\xb4\x01N'
 '\xd6vP'
 '\xaa\xd5~R'
 '\xae\xac\x01S'
 '\xae~T'
 '\xaa\xd5~W'
 '\x85"\x02YA'
'\xd8\x01'
 '\xe0\t\x02FT'
 '\xd5v\x05PCHA '
'\x94\x01'
 '\x98\x08\x0fCONSONANT SIGN '
 '\xb2\xd5{D'
 '\x94\xa8\x04\x07LETTER '
 '\xa8~\x0cPUNCTUATION '
 '\xc6~S'
 '\xbd\x7f\x0bVOWEL SIGN '
'\x0e'
 '\xca\xaf{A'
 '\xfajE'
 '\x02I'
 '\x826O'
 '\x9f\xe4\x00U'
'\x08'
 '\x80\x01\x04IGN '
 'e\x10UBJOINED LETTER '
'\x04'
 '\x9e\xae{R'
 '\x03Y'
'\x04'
 '\x1aN'
 '\xef\xa7{R'
'\x02'
 '\xd9\xad{\x02UK'
'\n'
 '\x9a\x01C'
 ' \x0eNYET THYOOM TA'
 '\xa3\x7fT'
'\x06'
 '\xde\x00A'
 'M\x05SHOOK'
'\x05'
 '\x11\x02 C'
'\x02'
 '\xc9\xe7~\x03ER-'
'\x02'
 '\xe9\xa6{\x02-R'
'N'
 '\xea\x96{A'
 '\xba\x8b\x02B'
 '\xaa\xb4\x7fC'
 '\xea\xa9\x01D'
 '\xf2\xa1\x7fF'
 '\x02G'
 '\x02H'
 '\xd2\x89~J'
 '\xa2\xd6\x04K'
 '\xe2\xa9{L'
 '\xb2\xf6\x01M'
 '\xbe\xb2\x7fN'
 '\xb6\xad\x03P'
 '\xe2\xa9{R'
 '\xda\xaa\x01S'
 '\xf2\xa8\x01T'
 '\xba\xac}V'
 '\x02W'
 '\x03Y'
'\x06'
 '\xd6\x94{A'
 '\x8a\x15H'
 '\x03L'
'\x12'
 '\xf6\x00K'
 '\xba\x93{L'
 '\x02M'
 '\xaa\xec\x04N'
 '\xda\x93{P'
 '\x02R'
 '\x03T'
'\x05'
 '\x99W\x04YIN-'
'\x05'
 '\xdf\xa2{A'
'D'
 '\xd6\x06 '
 '\xa2\xbf}-'
 '\xd1\xba\x02\x06WARDS '
'$'
 '\xf8\x03\x06ARROW '
 '\xbe\xd5{B'
 '\xee\xe6\x01Q'
 '\xe1\xc0\x02\x0bTWO-HEADED '
'\x0e'
 '\xe0\x00\x06ARROW '
 '\xed\xd7{\x0bTRIPLE DASH'
'\x0c'
 '\xc4\x83\x7f\x04FROM'
 '\x81\xfd\x00\x05WITH '
'\n'
 '\x9e\x01D'
 '\xbc\x7f\x04TAIL'
 '[V'
'\x02'
 '\x81\xa8{\x05ERTIC'
'\x07'
 '\x0b '
'\x04'
 '\x1d\x05WITH '
'\x04'
 '\x16D'
 '\x97\x7fV'
'\x02'
 '\x91\x7f\x07OUBLE V'
'\x12'
 '\xf0\x01\x06ABOVE '
 '\xbc\xcf{\x08THROUGH '
 '\xcd\xaf\x04\x05WITH '
'\n'
 '\x98\xdb{\tDOTTED ST'
 '\xaf\xa5\x04T'
'\x08'
 '\xd4}\x04AIL '
 '\xc3\xbe}I'
'\x06'
 '\xe6\xbe}A'
 '\xeb~R'
'\x1c'
 '\xe8\x01\x0bARROW WITH '
 '\xa8\xac~\x07CLOSED '
 '\x96\x97\x7fD'
 '\xb2\x7fL'
 '\xe6\xbc\x02R'
 '\xa2\xc1}S'
 '\xaa\x7fT'
 '\x93\x7fV'
'\x06'
 '\xe2\xc2}A'
 '\xdd\xbe\x7f\x03IGH'
'\x04'
 '\xd4\x00\x07CIRCLED'
 '_S'
'\x02'
 '\xb9\x97\x7f\x04MALL'
'\x02'
 '\x11\x02 P'
'\x02'
 '\xeb\xe1|L'
'\xb2\x05'
 '\xa4\xd4\x00\tO LETTER '
 '\xf0}\x04RGE '
 '\xdd\xae\x7f\x04TIN '
'\xa2\x05'
 '\x8c\xc1\x00\x0fCAPITAL LETTER '
 '\xb4~\x12EPIGRAPHIC LETTER '
 '\xdcz\x07LETTER '
 '\xbbGS'
'\x84\x03'
 '\xf8\x01\x05MALL '
 '\x8d\x7f\x16UBSCRIPT SMALL LETTER '
'\x14'
 '\xfe\x85{A'
 '\x02E'
 '\x02I'
 '\x02J'
 '\x02O'
 '\x02R'
 '\xe8\xd4\x03\x02SC'
 '\x9a\xab|U'
 '\x02V'
 '\x03X'
'\xf0\x02'
 '\xa46\x0fCAPITAL LETTER '
 '\xcdJ\x07LETTER '
'\xec\x02'
 '\xb63A'
 '\xae\x7fB'
 '\xf2~C'
 '\xae~D'
 '\xa2|E'
 '@\x02F '
 '\xaa\x7fG'
 '\xae\x7fH'
 '\xc6|I'
 '\xac\x7f\x07J WITH '
 '\xe0~\x07K WITH '
 '\xea}L'
 '\xb6~M'
 '\xce~N'
 '\xba|O'
 '\xe0~\x07P WITH '
 '\xbe~Q'
 '\xf2|R'
 '\xe2{S'
 '\xf6xT'
 '\xf6|U'
 '\xf2}V'
 'nW'
 '\xd4\xe4~\x02X '
 '\xe2\x9a\x01Y'
 '\xb5~\x07Z WITH '
'\x08'
 '\x92\x01D'
 'FM'
 '\xba\xe6~P'
 '\xab\x99\x01S'
'\x02'
 '\xe5\xa5{\x03WAS'
'\x02'
 '\x1d\x05IDDLE'
'\x02'
 '\xa1\x96{\x02 T'
'\x02'
 '\x0bE'
'\x02'
 '\x15\x03SCE'
'\x02'
 '\xf7\x9c{N'
'\x04'
 '!\x06 WITH '
'\x04'
 '\xc0\xbf{\x02LO'
 '\xdbWS'
'\x02'
 '\xeb\xe0~ '
'\x0e'
 '\x8c\x01\x06 WITH '
 '\xae\x88{E'
 '\x9e\xf7\x04I'
 '\xd3\xfdzY'
'\x02'
 '\xd9\xe5{\tSIGOTHIC '
'\x08'
 '\x9e\xdf~C'
 '\xb2\xa1\x01D'
 '\x86\xe3~P'
 '\xb5\x02\x04RIGH'
'\x02'
 '\x0bI'
'\x02'
 '\xc5\x94{\x04AGON'
'\x12'
 '\xe4\x00\x06 WITH '
 '\xb2\xfbzE'
 '\x02M'
 '\xc9\xeb\x03\x06PSILON'
'\x0c'
 '\x9a\x01M'
 '\x92\x7fO'
 '\xbb\xdc~R'
'\x04'
 '\x1d\x05GONEK'
'\x04'
 '\x1d\x05 AND '
'\x04'
 '\x1aA'
 '\xf3\x90{T'
'\x02'
 '\xb3\xd7}C'
'\x06'
 '\x1d\x05ACRON'
'\x06'
 '\x1d\x05 AND '
'\x06'
 '\xaa\x7fA'
 '\x82\x01G'
 '\xf3\x8f{T'
'\x02'
 '\xe5\xbc{\x02RA'
'*'
 '\xd8\x06\x06 WITH '
 '\xbc\xb6~\tAILLESS P'
 '\xb6\xc7\x01H'
 '\x9a\xda~O'
 '\xae\xa5\x01R'
 '\x9a}U'
 '\xe7\xf7zZ'
'\x16'
 '\xe2\xf7zM'
 '\xd5\x88\x05\x05RNED '
'\x14'
 '\xf6\xfbzA'
 '\xb6{G'
 '\xd8\x8a\x05\x0fH WITH FISHHOOK'
 'NI'
 '\xde\xf5zL'
 '\x82\x8a\x05O'
 '\xb5\x9b{\x02R '
'\x04'
 '\xfe\xf5zE'
 '\xbf\xe4\x03P'
'\x05'
 '\x0bN'
'\x02'
 '\xb9\xdd~\x05SULAR'
'\x05'
 '\x0b '
'\x02'
 '\xf1\x9a{\x03AND'
'\x02'
 '\x11\x02ES'
'\x02'
 '\x11\x02IL'
'\x02'
 '\xcf\xa7{L'
'\x06'
 '\xe4\x01\x0c WITH STRIKE'
 '\xe7~O'
'\x04'
 '1\nRN WITH ST'
'\x04'
 '\x19\x04ROKE'
'\x05'
 '\x0b '
'\x02'
 '!\x06THROUG'
'\x02'
 '\xb1s\x03H D'
'\x02'
 '\xf5\xdb{\x05THROU'
'\x06'
 '\xb6\xd4~C'
 '\xb2\xa1\x01D'
 '\xcf|M'
'\x18'
 '\x94\x03\x06 WITH '
 'jA'
 'D\x03CHW'
 '\xad~\x08IDEWAYS '
'\x0c'
 '\xb8\xd8~\x0bDIAERESIZED'
 '\xda\xa8\x01O'
 'd\x04TURN'
 '\x9b\xf0zU'
'\x02'
 '\x91\xe3|\x02ED'
'\x07'
 '\xd6\xd9~ '
 '\xcf\xa6\x01P'
'\x02'
 '\xd9\xd5~\x02EN'
'\x02'
 '\x0bA'
'\x02'
 '\xe1\xd0~\x07 WITH R'
'\x02'
 '\x95z\x02LT'
'\x08'
 '\xeanM'
 '\xba\xe6~P'
 '\xaa\x99\x01S'
 '\xf3\x11V'
'\x02'
 '5\x0bERTICAL LIN'
'\x02'
 '\xeb\x8d{E'
'\x16'
 '\xe2\x01 '
 '\xa0\x7f\x08EVERSED '
 'I\x02UM'
'\x05'
 '\x0b '
'\x02'
 '\x0bR'
'\x02'
 '\xf5\xf9|\x03OTU'
'\x06'
 '.C'
 '\xfd|\x06OPEN E'
'\x05'
 '\x0b '
'\x02'
 '\x99\xedz\x04WITH'
'\x0c'
 '\xfe~R'
 '\xb1\x01\x05WITH '
'\n'
 '\xcck\x0eFISHHOOK AND M'
 '\x02M'
 '\xba\xe6~P'
 '\xfe\xb1|S'
 '\x93~T'
'\x08'
 '\xd4\x00\x06 WITH '
 '[P'
'\x02'
 '\x91\xba|\x05 DIGR'
'\x06'
 '\xaemD'
 '\x9e\x13H'
 '[S'
'\x02'
 '\xb9v\x06TROKE '
'\x02'
 '\x81\x8f{\x03OOK'
'\x0c'
 '\xfa\x00F'
 '\x96hM'
 '\xba\xe6~P'
 '\xf7\xb0\x01S'
'\x06'
 '\xa4\x8e{\x07QUIRREL'
 '\xeb\xe6\x04T'
'\x02'
 '\xd5\x83}\x04LOUR'
'\x12'
 '\xec\x00\x06 WITH '
 '\xfe\xe6zO'
 '\xed\x98\x05\x04PEN '
'\x04'
 '\xe2wE'
 '\x03O'
'\x0c'
 '\xb4\x01\x02LO'
 '\xef~V'
'\x06'
 '\xd5\x00\x12ERTICAL LINE BELOW'
'\x07'
 '\x1d\x05 AND '
'\x04'
 '\xb6kA'
 '\x83\x01G'
'\x06'
 '\xc6\x00N'
 '\xea\xa5{O'
 '\xad\xba\x02\x06W RING'
'\x02'
 ')\x08G STROKE'
'\x02'
 '\x85\xe6|\x06 OVERL'
'\n'
 '\xfc\x00\x06 WITH '
 'l\x0bG WITH TILD'
 '\xf3\xebzU'
'\x02'
 '\xff\xc1{E'
'\x06'
 '\xaa\xc5~C'
 '\xfe\x9d\x01M'
 '\xbb\xe6~P'
'\x0c'
 '\x98\x01\x06 WITH '
 '\xaa\x7fI'
 '\xe7\xeazU'
'\x04'
 '5\x0bDDLE-WELSH '
'\x04'
 '\xe2\xf1zL'
 '\x93pV'
'\x06'
 '\xd6aM'
 '\xba\xe6~P'
 '\x8f\xb0|T'
'\x10'
 '\xa0\x01\x06 WITH '
 'H\x0bONG S WITH '
 '\xf3\xe8zU'
'\x04'
 '\xeecD'
 '\xaf\x1cH'
'\x02'
 '\x8d\xca~\x02IG'
'\n'
 '\x86\xc2~C'
 '\xca\xbe\x01D'
 '\x96\x7fH'
 '\xda\xc6~P'
 '\x8f\xb0|T'
'\x02'
 '\xf5\xd1~\x04OUBL'
'\n'
 '\x82\x01D'
 '\xc6\xc4~P'
 '\xeb\xba\x01S'
'\x04'
 '\x1d\x05TROKE'
'\x05'
 '\x19\x04 AND'
'\x02'
 '\xd5a\x02 D'
'\x04'
 '\xd2^E'
 '\xfb\x02I'
'\x04'
 '\x8c^\rDOT ABOVE AND'
 '\x97\x98{S'
'\x1e'
 '\xbc\x01\x06 WITH '
 '\xa2\x7fN'
 '\x80\xc8~\x03OTA'
 '\xbb\x94|S'
'\x0c'
 '!\x06SULAR '
'\x0c'
 '\x92\xdczD'
 '\x02F'
 '\x02G'
 '\x02R'
 '\x02S'
 '\x03T'
'\x0e'
 '\xe0a\tDOT ABOVE'
 '\xd6\x1fM'
 'P\x0cOGONEK AND D'
 '\x87\xbc~R'
'\x04'
 '\xe9_\x08OT ABOVE'
'\x02'
 '1\nACRON AND '
'\x02'
 '\xc3`G'
'\x06'
 '6 '
 '\xc0\xedz\x04ALF '
 '\x8f{E'
'\x02'
 '\xadf\x03WIT'
'\x06'
 '\x9e\xbf~ '
 '\xf2\xae|H'
 '\xa7\x92\x05L'
'\x02'
 '\x95\x99{\x04OTTA'
'\x04'
 '\x1d\x05WITH '
'\x04'
 '\x92XM'
 '\xbb\xe6~P'
'$'
 '\xd8\x01\x06 WITH '
 '\x9a\x7fG'
 '\xfc\xbf~\x02SH'
 '\x82\x97|T'
 '\xd1\x90\x05\x02ZH'
'\x04'
 '\xc1\x00\rYPTOLOGICAL A'
'\x04'
 '\xf2\xe0zI'
 '\x87\x88\x02L'
'\x18'
 '\xf6\x00C'
 '\xcezD'
 '\x9c\xd1{\x03NOT'
 '\xb2\x8e\x04O'
 '\xba\xdc~R'
 '\x86\xb7|S'
 '\xf3\x80\x05V'
'\x04'
 '\xc5\x00\x0eIRCUMFLEX AND '
'\x04'
 ',\x02CA'
 'oM'
'\x02'
 '\x11\x02AC'
'\x02'
 '\xd3\xdezR'
'\x10'
 '\xfc\x00\x06 WITH '
 '\xf2hB'
 '\xae\xb9{E'
 '\xf4\xb0\x7f\x08OTLESS J'
 '\xbb\x08U'
'\x08'
 '\x96\xb5~C'
 '\xdc\xa8\x01\x05HOOK '
 '\xa2uM'
 '\xbb\xe6~P'
'\x08'
 '\x96\xbc~ '
 '\xe2\xa0|O'
 '\xdd\xa3\x05\x08UATRILLO'
'\x05'
 '\x1d\x05 WITH'
'\x02'
 '\xb5\x95{\x02 C'
'\x08'
 '\xfax '
 '\xee\xc5~O'
 '\xcb\xc1\x01R'
'\x02'
 '\x91\xe2~\x04OKEN'
'\x18'
 '\xb8\x01\x06 WITH '
 '\x9e\xcfzA'
 '\xc4\x90\x05\x03LPH'
 '\xbe\xefzO'
 '\x02U'
 '\xb6\xb0\x05V'
 '\xcf\xcfzY'
'\x05'
 '\x85\xc9~\x07 WITH H'
'\n'
 '\xfatM'
 '\x9e_O'
 '\xba\xdc~R'
 '\x87\xb7|S'
'\x04'
 '\xa6\xba~I'
 '\x03U'
'<'
 '\xfe\x9a{A'
 '\xc4\xe6\x04\x0eSMALL CAPITAL '
 '\x89\xd3{\x16VOICED LARYNGEAL SPIRA'
'8'
 '\xce\x83{A'
 '\xe8\xc7\x03\x02BA'
 '\xca\x81|C'
 '\x02D'
 '\xc6\xb6\x05E'
 '\xbe\xc9zF'
 '\x02J'
 '\x02K'
 '\xca\xeb\x03L'
 '\xba\x94|M'
 '\xa6\xb6\x05O'
 '\xde\xc9zP'
 '\xce\xb5\x05R'
 '\xb6\xcazS'
 '\x8e\xb5\x05T'
 '\xf6\xcazU'
 '\x02V'
 '\x02W'
 '\x03Z'
'\x07'
 '!\x06URNED '
'\x04'
 '\xce\xcazE'
 '\x03R'
'\x06'
 '8\x08EVERSED '
 '\xb3\xd2zU'
'\x04'
 '\xf6\xc9zN'
 '\x03R'
'\x07'
 '\x82ZP'
 '\xdb\xefzU'
'\x07'
 '\xd6\xddzT'
 '\x03Z'
'\n'
 '\x98\xbc|\x07ARCHAIC'
 '\xee\xc4\x03I'
 'e\tREVERSED '
'\x04'
 '\xb2\xc8zF'
 '\x03P'
'\x04'
 '\xa4\x8e|\x03 LO'
 '\xd9\xc9\x03\x05NVERT'
'\xd8\x01'
 '\xde\x0eA'
 '^B'
 '\xdafC'
 '\x9e\x18E'
 '^G'
 '\xea`H'
 '\xba\x1eI'
 '`\x07J WITH '
 'd\x07K WITH '
 '\xb4\x7f\x07L WITH '
 '\xae\x7fM'
 '\x8e\x7fO'
 'h\x07P WITH '
 'd\x07Q WITH '
 '\xb2~R'
 '\xca~S'
 '\xd2~T'
 '\xac\x7f\x02U '
 '\xa6\x7fV'
 '\xd6EW'
 '\xb6\x7fY'
 '\xdd:\x07Z WITH '
'\x04'
 '\xeaDD'
 '\xa7\x7fS'
'\x08'
 ': '
 '\xea\xcezE'
 '\x9e\xf7\x04I'
 '\xd3\xfdzY'
'\x02'
 '\xb1e\x04WITH'
'\x0c'
 '\x9a\xcczB'
 '\x9d\xb4\x05\x05WITH '
'\n'
 '\xe6HM'
 '\x93\x7fO'
'\x14'
 '\x8a\x7f '
 '\xe0O\x02HO'
 '\xfa~R'
 '\x803\x06URNED '
 '\xff\xc1zZ'
'\n'
 '6A'
 '\xf4K\x02IN'
 '\xd2\xf5zL'
 '\x03V'
'\x05'
 '\x87\xa7~L'
'\n'
 '\x94\x01\x06 WITH '
 '\x9aQA'
 '\xcc\xc5{\x04HARP'
 '\x89\xc0\x04\rMALL Q WITH H'
'\x04'
 '\xfa\xbf\x7fS'
 '\xf3\x11V'
'\x0c'
 '\xda\x00 '
 '\xfcR\nEVERSED C '
 '\x99\x7f\x03UM '
'\x08'
 '\x9eRR'
 '\x91.\x05WITH '
'\x06'
 '\xa2\xd7zS'
 '\x83\xa9\x05T'
'\x04'
 '\xbe\xe4zA'
 '\xdfpI'
'\x04'
 '\xdeAD'
 '\xf7\x12S'
'\x08'
 '\xfaUF'
 'CS'
'\x0c'
 '0\x06 WITH '
 '\xc3\xbdzO'
'\n'
 '\x1c\x02LO'
 '\xcbVV'
'\x04'
 '\xa2XN'
 '\xeb\xa5{O'
'\x08'
 ',\x06 WITH '
 '\xa7ZI'
'\x04'
 '\xc2\x9e~H'
 '\xd7\xb4|T'
'\n'
 '\x92\xc5zB'
 '\xea\x97\x05D'
 '\x96\x7fH'
 '\xa2`M'
 '\xc7\x96{T'
'\x08'
 '\xd6]D'
 '\xaf\x7fS'
'\x04'
 '\xfa\xd3zS'
 '\x93~T'
'\x14'
 '\xc0\x00\x06 WITH '
 '\xaa^N'
 '\xbb\xdczS'
'\x06'
 '\xbe`M'
 '\x9f_O'
'\x04'
 '\xca\xcfzH'
 '\xa7\x92\x05L'
'\x1a'
 '\xc0\x00\x06 WITH '
 '\xe2bG'
 '\xff\xd6zT'
'\x14'
 '\xbedC'
 '\xcezD'
 '\xce_O'
 '\xbe\x93{S'
 '\xf3\x80\x05V'
'\x04'
 '\xee\xa2~ '
 '\xab\xc5\x01R'
'\x16'
 '\xfc\x00\x06 WITH '
 '\xf2\xb7zA'
 '\xc6\xe5\x03L'
 '\xbe\x9a|O'
 '\x02U'
 '\xb6\xb0\x05V'
 '\xcf\xcfzY'
'\x08'
 '\xce]M'
 '\x9e_O'
 '\xbf\x93{S'
'\x08'
 '\xa4\x01\x04ONE '
 '\x95\x7f\x04TWO '
'\x04'
 '\xae\x94{D'
 '\xb1t\x13RINGS OVER ONE RING'
'\x04'
 '\xf6\xb1}D'
 '\xcd\x00\x12RING OVER TWO RING'
'\x08'
 '0\x04FO F'
 '\xfe\xe7zL'
 '\x03R'
'\x04'
 '\xe6\x97{A'
 '\xd7\xa7\x7fO'
'\x9e\x04'
 '\x9a\x1aA'
 '\x83fH'
'\xaa\x02'
 '\x80\x0e\tAROSHTHI '
 '\xcdr\x04MER '
'\xa8\x01'
 '\xf0\t\x15CONSONANT SIGN COENG '
 '@\x1dINDEPENDENT VOWEL SIGN COENG '
 '\xbayS'
 '\xb9\x7f\x0bVOWEL SIGN '
'\x06'
 '\xf6\xdd{A'
 '\xf0\x96\x03\x05COENG'
 '\x93\xc5{O'
'V'
 '\x80\xc0z\nIGN ATTHAC'
 '\xe1\xc0\x05\x06YMBOL '
'T'
 '\x92\x03B'
 '\xec\x01\x03DAP'
 '\xb8~\nLEK ATTAK '
 'BM'
 '\xaa~P'
 'm\x05TUTEY'
'\x02'
 '\xbb\xe3{A'
'\x1a'
 'h\x05ATHAM'
 '\xa2\x01I'
 '\xb9\x7f\x03RAM'
'\x14'
 '\xde\x00 '
 '\xbf\x7f-'
'\x10'
 '\x92\x01B'
 'fM'
 '\xb5\x7f\x02PI'
'\x04'
 '\x0bI'
'\x04'
 '\x0b '
'\x04'
 '\xc4\x88{\x02KO'
 '\xad\xab\x7f\x02RO'
'\x04'
 '\xbd\x7f\x03UOY'
'\x08'
 '\x96\x7fE'
 '\r\x03UON'
'\x14'
 '\xa6\x01B'
 'nM'
 '\xa2\x7fP'
 '\xdb\xb6zS'
'\x0c'
 '\x8a\xdezI'
 '\xa5\xa2\x05\x03RAM'
'\x0b'
 '\x0b-'
'\x08'
 '6B'
 'nM'
 '\xa3\xddzP'
'\x02'
 '\xff\xaa{U'
'\x04'
 '\x96\xddzE'
 '\xcfXU'
'\x18'
 '\xc2} '
 '\xdb\x02-'
'\x14'
 '\xf6}B'
 'fM'
 '\xcb\x02P'
'\x08'
 '\xea|I'
 '\r\x03RAM'
'\x08'
 '"Q'
 '\x89\xdb}\x02RY'
'\x04'
 '\x8a\xaazE'
 '\x03U'
'D'
 '\xf6\xbezB'
 '\x92\xc4\x05C'
 '\x92\x7fD'
 '\xe2\xbczH'
 '\x92\xc4\x05K'
 '\x92\x7fL'
 '\xd6\xdazM'
 '\xe6\xa5\x05N'
 'fP'
 '\xba\xdazR'
 '\xba\x8e\x01S'
 '\xaa\x96\x04T'
 '\xa2\xdbzV'
 '\x03Y'
'\x0c'
 '\xa2\xa8zA'
 '\xaa\xd8\x05H'
 '\xda\xa7zO'
 '\xa9\xd8\x05\x02TH'
'\x04'
 '\xd6\xa7zA'
 '\x03O'
'\x06'
 'bH'
 '\xdb\xa7zO'
'\x08'
 '\x9e\xa7zA'
 '\xfe2G'
 '\x86MO'
 '\xff2Y'
'\x08'
 '\xe6\xa6zA'
 '\xaa\xd8\x05H'
 '\xdb\xa7zO'
'\x82\x01'
 '\xc0\x0b\x06DIGIT '
 '\xd8|\x07LETTER '
 '\xb0\x7f\x07NUMBER '
 '\xdc}\x0cPUNCTUATION '
 '\x98~\x05SIGN '
 '\xa3~V'
'\x0e'
 '\xbe\xe6|I'
 '\xf9\x99\x03\x05OWEL '
'\x0c'
 '\xe0\xa3z\x06LENGTH'
 '\xed\xdc\x05\x05SIGN '
'\n'
 '\xc6\xa3zE'
 '\x02I'
 '\x02O'
 '\x02U'
 '\xf5\x08\x08VOCALIC '
'\x0c'
 '\xaa\xcazA'
 '\xa8\xb7\x05\x02BA'
 'bC'
 '\xa4\x7f\x02DO'
 '\xf7\xcazV'
'\x04'
 '\x8e\xc2zT'
 '\xad\xbe\x05\x06UBLE R'
'\x02'
 '\xd1\xc1z\x03ING'
'\x02'
 '\x0bA'
'\x02'
 '\x8f\xefzU'
'\x02'
 '\xe3\xffzR'
'\x12'
 '\xe2\x01C'
 '\xba\x7fD'
 'JL'
 'l\x05MANGA'
 '\x8f\x96\x7fS'
'\x02'
 '\xef\xcc{L'
'\x04'
 '"I'
 '\xf9\xf7{\x02OT'
'\x02'
 '\xeb\xa7{N'
'\x06'
 '\xe6\xac|A'
 '\xbf\xd3\x03O'
'\x04'
 '\xc6\x9fzT'
 '\xcb\x8c\x02U'
'\x04'
 '\xd6\xa2{I'
 '\xa1\xef\x02\x07RESCENT'
'\x08'
 '\xde\xb6~O'
 '\xc7\xc9\x01T'
'\x04'
 '\xfa\xa8zE'
 '\xb5\x96\x02\x02WE'
'F'
 '\x92\x9ezA'
 '\xe2\xbf\x01B'
 '\x02C'
 '\xfa\xcb\x00D'
 '\x8a\xb4\x7fG'
 '\xaa\xd5~H'
 '\x02J'
 '\xe6\xcf\x05K'
 '\x9e\xb0zL'
 '\x02M'
 '\xbe\xcf\x05N'
 '\x9e\xdb{P'
 '\xaa\xd5~R'
 '\xae\xac\x01S'
 '\xb6\xa2\x04T'
 '\xa2\xb1zV'
 '\x02Y'
 '\x03Z'
'\n'
 '\x96\x9czA'
 '\x8a\x15H'
 '\x93\xcf\x05T'
'\x06'
 '\xe6\x9bzA'
 '\x8a\x15H'
 '\xff\x0bT'
'\x06'
 '\xba\x9bzA'
 '\x8a\x15N'
 '\x03Y'
'\x06'
 '\x92\x9bzA'
 '\x8a\x15H'
 '\x03K'
'\x08'
 '\x86\xa1{F'
 '\xe6\xbc\x7fO'
 '\x8b\x7fT'
'\xf4\x01'
 '\xbc\x08\x05ITHI '
 '\x88~\x06NNADA '
 'l\x12TAKANA LETTER AINU'
 '\x8d{\x07YAH LI '
'`'
 '\xf6\xd9zD'
 '\xdc\xa8\x05\x07LETTER '
 'T\x05SIGN '
 '\xa0\x7f\x05TONE '
 'U\x06VOWEL '
'\n'
 '\xaa\xcezE'
 '\xb2IO'
 '\xd36U'
'\x06'
 '\xc8\x00\x05CALYA'
 'cP'
'\x02'
 '\xed\x88}\x03LOP'
'\x05'
 ']\x02 P'
'\x04'
 '\xba\xd4~C'
 '\xf5\xad~\x02SH'
'8'
 '\xa2\x96zA'
 '\x8a\x15B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\xd6\xd6\x05H'
 '\xa6\x94zI'
 '\xe2\xbf\x01K'
 '\xaa\xd5~L'
 '\x02M'
 '\xee\xa8\x01N'
 '\xbe\xaa\x02O'
 '\xb2\xd7}P'
 '\xaa\xd5~R'
 '\xda\xaa\x01S'
 '\x02T'
 '\xaa\xd5~V'
 '\x02W'
 '\x02Y'
 '\x03Z'
'\x04'
 '\xa2\x94zA'
 '\x8b\x15T'
'\x02'
 '\xef\xd4z '
'\x0e'
 '\xe0\x01\x08LETTER L'
 '\xfc~\x05SIGN '
 '\xb3\xa4{V'
'\x08'
 '\xda\xa5{A'
 '\x80\xff\x01\x08JIHVAMUL'
 '\xd6\xd5\x01N'
 '\xad\xaa~\x08UPADHMAN'
'\x02'
 '\xe3\xe0zL'
'\x84\x01'
 '\xb8\x06\x07ABBREVI'
 '2D'
 'P\x06ENUMER'
 '\x80}\x07LETTER '
 '\x9a\xb1{N'
 '\xd6\xcd\x04S'
 '\xad\x7f\x0bVOWEL SIGN '
'\x12'
 '\xe2\xaa{A'
 '\xbe\xe5~E'
 '\xb2\x9a\x01I'
 '\xd2\xe5~O'
 '\x9f\x9a\x01U'
'\x0c'
 '\xd6\xd1|E'
 '\xdd\xae\x03\x04IGN '
'\n'
 '\xd2\xb6zA'
 '\xf2\xc9\x05C'
 '\xf6\xf5~N'
 '\x9f\xa0}V'
'\x02'
 '\xe9\xf8|\x02AN'
'Z'
 '\xd2\xb0{A'
 '\xc6\x1dB'
 '\x02C'
 '\x8a\xb4\x04D'
 '\x9a\x8czE'
 '\xe2\xbf\x01G'
 '\xaa\xd5~H'
 '\xaa\x85\x01I'
 '\xb2%J'
 '\x02K'
 '\xaa\xd5~L'
 '\x02M'
 '\x82\xf6\x01N'
 '\xfa\xf4}O'
 '\xe2\xbf\x01P'
 '\x02R'
 '\xd6\x01S'
 '\xa6\xc9\x00T'
 '\xc6\x8f\x7fU'
 '\xee\xfa~V'
 '\x03Y'
'\n'
 '\x96\x8czA'
 '\x9e\xf4\x05D'
 '\xef\xa0zH'
'\x06'
 '\xe2\x8bzA'
 '\x86!D'
 '\x87tH'
'\x02'
 '\x0bA'
'\x02'
 '\xdd\x9cz\x04TION'
'\x06'
 '\x82\x98|A'
 '\xb9\xe8\x03\x06OUBLE '
'\x04'
 '\xba\x97|D'
 '\x935S'
'\xba\x01'
 '\x1aA'
 '\xe3\xc5~U'
'\xb8\x01'
 '\xd4\x13\nPANESE BAN'
 '\x89m\x07VANESE '
'\xb6\x01'
 '\x90\x12\x0fCONSONANT SIGN '
 '\x92\xb8zD'
 '\xbc\xc0\x05\x02LE'
 '\xf0{\x02PA'
 '@\x04RIGH'
 '\xe0~\x05SIGN '
 '`\x0eTURNED PADA PI'
 '\xe9}\x0bVOWEL SIGN '
'\x12'
 '\xfc\x83{\x07DIRGA M'
 '\xba\xdf\x00P'
 '\xb8\x9e\x04\x04SUKU'
 'BT'
 'Q\x04WULU'
'\x05'
 '\x19\x04 MEL'
'\x02'
 '\xc3\x85zI'
'\x06'
 '\x1aA'
 '\xa7\xe1{O'
'\x04'
 '\xba\x94zL'
 '\x9f\xcd\x01R'
'\x05'
 '\x95\x93{\x05 MEND'
'\x02'
 '\xed\xe2{\x03SEL'
'\n'
 '\xfc\x00\x05CECAK'
 '\xb6\xe1{L'
 '\x84\xcb~\x07PANYANG'
 '\xa1\xc5\x00\x04WIGN'
'\x05'
 '\xc9\xdf{\x03 TE'
'\x02'
 ')\x08T RERENG'
'\x02'
 '\xf3\x91zG'
'\x1c'
 '\xe0\x00\x03DA '
 'I\x02NG'
'\x04'
 '\xd6\x8czK'
 '\xd5\xf2\x01\x05RANGK'
'\x18'
 '\xd2\x02A'
 '\x8c\xc2z\x07ISEN-IS'
 '\x9a\xbd\x05L'
 '\xd8\xeb|\x03MAD'
 '\xf6\x93\x03P'
 '\x98\x88{\x0bTIRTA TUMET'
 '\xcb\xe2\x01W'
'\x04'
 '\xe8\xb4{\x04ANGK'
 '\xef\xc6\x04I'
'\x06'
 '\xf4\xa7z\x03ING'
 '\xbb\xd8\x05U'
'\x04'
 '\xf6\xc2zH'
 '\xa9\xfa\x03\x02NG'
'\x06'
 ',\x03DEG'
 '\xf1\x84~\x02ND'
'\x05'
 '\x0b '
'\x02'
 '\xb5\xecz\x02AD'
'`'
 '\xae{F'
 '\x81\x05\x05TTER '
'^'
 '\xc2\x98{A'
 '\xd6\xec\x04B'
 '\x02C'
 '\xd6\x01D'
 '\xaa\xf7yE'
 '\x86\x87\x06G'
 '\x86\x8ezH'
 '\xa2\xf3\x05I'
 '\x9a|J'
 '\xa4\x03\x02KA'
 '\xa6\x8dzL'
 '\x02M'
 '\xd2\xf1\x05N'
 '\xaa\xf9yO'
 '\x9c\x86\x06\x02PA'
 '`\x02RA'
 'P\x02SA'
 '\xda~T'
 '\xde\xfbyU'
 '\x8a\x15W'
 '\x03Y'
'\x08'
 '\xf2\x00A'
 '\xab\x7fT'
'\x04'
 '\x0bA'
'\x05'
 '\x0b '
'\x02'
 '\x0bM'
'\x02'
 '\x0bA'
'\x02'
 '\x0bH'
'\x02'
 '\xfd\xb3{\x02AP'
'\x05'
 '\x11\x02 M'
'\x02'
 '\x0bU'
'\x02'
 '\xa7\xc8zR'
'\x07'
 '\x11\x02 M'
'\x04'
 '\x8e\x7fA'
 '\xcb\x00U'
'\x05'
 '\xb9\xd6{\x03 AG'
'\x07'
 '\x0b '
'\x04'
 '\x8c\xd7{\x03CER'
 '\xf7\xa7\x04M'
'\x0e'
 '\xbe~A'
 '\xfc\x01\x02GA'
 'sY'
'\x04'
 '\x93~A'
'\x07'
 '!\x06 LELET'
'\x05'
 '\xb1\xbd~\x06 RASWA'
'\x07'
 '\x0b '
'\x04'
 '\xba}M'
 '\xe3\x02S'
'\x02'
 '\xf9\x9dz\x02AS'
'\x07'
 '\xc0\xb5~\x03 KA'
 '\x97\xc2{I'
'\x08'
 '\xf2{A'
 'wD'
'\x06'
 '\xd0\xd8{\x02CA'
 '\xf8\xa7\x04\x02KE'
 '\x9d\xd8{\x02PE'
'\x02'
 '\xbb\xd1zR'
'\x02'
 '\xf3\x85zK'
'\xba\x01'
 '\xe8\xf8{\x05CE SK'
 '\xb0\x93\x04\x10MPERIAL ARAMAIC '
 '\xebtN'
'z'
 '\x84\x03\x0eSCRIPTIONAL PA'
 '\xc4\x87~\x15TERLOCKED FEMALE AND '
 '\xf3\xf6\x01V'
'\x06'
 '\xcc\x00\x06ERTED '
 '\x81\xe9~\x06ISIBLE'
'\x04'
 '\xe4\x00\x07INTERRO'
 'a\x05UNDER'
'\x02'
 '\x0bT'
'\x02'
 '\xff\xf6yI'
'\x02'
 '\xab\xa5zB'
'r'
 '\xb4\x05\x06HLAVI '
 '\x99{\x07RTHIAN '
'<'
 '\x9e\x01L'
 '\xff~N'
'\x10'
 '!\x06UMBER '
'\x10'
 '\x96\xf7zF'
 '\x9e\x89\x05O'
 '\xf3\xbf|T'
'\x06'
 '\x0bN'
'\x06'
 '\x0bE'
'\x07'
 '\xcb\x88~ '
','
 '!\x06ETTER '
','
 '\xf2\x02A'
 '\xf2\xbd{B'
 '\xfe\xc1\x04D'
 'nG'
 '\xd2\xf9|H'
 '\xd2\xc3~K'
 '\xf6\xbb\x01L'
 '\xd2\xc1}M'
 'nN'
 '\xaa\xb7\x7fP'
 '\x8a\x87\x03Q'
 '\x82\x8d\x7fR'
 '\xca\xf9\x03S'
 '\xa2\xf8|T'
 '\xealW'
 '\xca\x12Y'
 '\x97\x88\x03Z'
'\x02'
 '\xb9\xbaz\x02AY'
'\x06'
 '\x1aA'
 '\x87\xbazH'
'\x04'
 '\x86\xf9|D'
 'cM'
'\x02'
 '\x8b\xfa|I'
'\x02'
 '\xc7\xfa|A'
'\x04'
 '\x1aL'
 '\xa7\xb9zY'
'\x02'
 '\xe7\xbc{E'
'6'
 '0\x07LETTER '
 '\x83{N'
'&'
 '\xb4\x7f\x02AL'
 '\xd6\xbd{B'
 '\xfe\xc1\x04D'
 'nG'
 '\xd2\xf9|H'
 '\xd2\xc3~K'
 '\xf6\xbb\x01L'
 'l\x05MEM-Q'
 '\xd2\xc1}N'
 '\xaa\xb7\x7fP'
 '\xd2\x8d\x06S'
 '\xa2\xf8|T'
 '\x98\x8e\x7f\nWAW-AYIN-R'
 '\x9a\xf1\x00Y'
 '\x97\x88\x03Z'
'>'
 '\xdeyL'
 '\xf0\x06\x07NUMBER '
 '\x81^\x03SEC'
'\x10'
 '\xe2xO'
 '\xbb\x07T'
'\n'
 '*E'
 '\x86\xabzH'
 '\xbb\x8d\x02W'
'\x04'
 '\x0bN'
'\x05'
 '\xfb\x92| '
'\x9a\x03'
 '\xb2&A'
 '\xde]E'
 '\x86\x7fI'
 '\xe2~O'
 '\xb4\x8d|\x04RYVN'
 '\xc5\xf1\x03\x02YP'
'\x04'
 '\xa8\xc3z\x0eHEN WITH DIAER'
 '\xc9\xbd\x05\x06ODIAST'
'\x02'
 '\xef\xeeyO'
'\x06'
 '\xdc\x00\tRIZONTAL '
 '\x85\xdez\x07T BEVER'
'\x04'
 '\xc0\xf2y\x08BLACK HE'
 '\x9b\nM'
'\x04'
 '\xe0\xfcy\tGH VOLTAG'
 '\x85\x84\x06\x08STORIC S'
'\x02'
 '\xa3\xe7{I'
'\x9e\x01'
 '\xee\x1cA'
 '\xc4|\x05BREW '
 'd\x11LMET WITH WHITE C'
 '\x9dh\x0bXAGRAM FOR '
'\x80\x01'
 '\xf6\x16A'
 '\xee~B'
 '\xa0\x7f\x02CO'
 '\xae}D'
 '\xfc\xd8y\tENTHUSIAS'
 '\xca\xa6\x06F'
 '\xca~G'
 'D\x04HOLD'
 '\x88\x7f\x02IN'
 '\xfc\xa5z\x05LIMIT'
 '\xc8\xd9\x05\x02MO'
 '\xfa~O'
 '\x8e\x7fP'
 '@\x02RE'
 '\x9a~S'
 '\xceyT'
 '\x9a\x7fW'
 'm\x0cYOUTHFUL FOL'
'\x02'
 '\xe3\xc2zL'
'\x04'
 '\xc4\xd6z\x02AI'
 '\x8d\x06\x10ORK ON THE DECAY'
'\x1e'
 '\xc0\x00\x03HE '
 'm\x03REA'
'\x02'
 '\xeb\xedyD'
'\x1c'
 '\xde\x04A'
 '\xde~C'
 '\x84{\x04FAMI'
 '\x88\xfd}\x06GENTLE'
 '\xcc\xfb{\tJOYOUS LA'
 '\xfc\xbe\x03\x11KEEPING STILL MOU'
 '\x9c\xeb|\rMARRYING MAID'
 '\xf4\xe1\x05\tRECEPTIVE'
 'KW'
'\x04'
 '\xb8\xf9y\x05ANDER'
 '\xbf\xe1\x00E'
'\x02'
 '\x89\xb5}\x02 E'
'\x06'
 '\xd8\x86\x7f\x04AULD'
 '\xec\xba|\tLINGING F'
 '\xc9\xbf\x04\nREATIVE HE'
'\x02'
 '\xd3\x9czA'
'\x06'
 '\xd4\xb6|\x08BYSMAL W'
 '\xef\xc9\x03R'
'\x04'
 '\xfe\xbbzM'
 '\xfd\x9d\x04\nOUSING THU'
'\x08'
 '\x84\x01\x05MALL '
 '\xc4\xa2~\x0bPLITTING AP'
 '\xa5\xea}\x06TANDST'
'\x04'
 '4\x02PR'
 'gT'
'\x02'
 '\xc1\xe6y\x02AM'
'\x02'
 '\xd5\xcfz\x05EPOND'
'\x06'
 '\x1aT'
 '\xfb\xe4zV'
'\x04'
 '\xc2\xad~R'
 '\xb7\xa4|U'
'\x06'
 '\xe8\xa9z\x02EA'
 '\xd0"\x04ROGR'
 '\xe5\xad\x01\x0bUSHING UPWA'
'\x06'
 '\xf0\x00\x05BSTRU'
 'A\x02PP'
'\x04'
 '\x8a\xd1zO'
 '\x9b\xaf\x05R'
'\x02'
 '\x9d\xecy\x02ES'
'\x02'
 '\xd7\xa6zC'
'\x04'
 '\xb0\xcbz\x03DES'
 '\xd1\xfc\x00\x03UTH'
'\x08'
 '\xce\xd3zC'
 '\xacz\x03FLU'
 '\xc3\xb2\x05N'
'\x04'
 '\xc4\xe0z\x05ER TR'
 '\xf9l\x02OC'
'\x02'
 '\xd9\xf0y\nING TOGETH'
'\x0c'
 '@\x05ATHER'
 '\xeb\x00R'
'\n'
 '\xd2\xa5zA'
 '\xe1\xda\x05\x04EAT '
'\x08'
 '\x16P'
 '\x9bzT'
'\x06'
 '\x16O'
 '\x9fzR'
'\x04'
 '\xcc|\x02SS'
 '\xc3\xf2yW'
'\x04'
 '\xf8\xcfz\x05ELLOW'
 '\xf9\x04\x02OL'
'\x0e'
 '\x90\x94z\x11ARKENING OF THE L'
 '\xfa\xed\x05E'
 '\xfa~I'
 '\xbb\xcazU'
'\x04'
 '\xd4\xd9z\x15FFICULTY AT THE BEGIN'
 '\xb1\x8d\x7f\x04SPER'
'\x06'
 '\x9a\xcezC'
 '\xdcx\x02LI'
 '\xb1\r\x05VELOP'
'\x06'
 '\xde\xcfzM'
 '\xc7\xb0\x05N'
'\x04'
 '\xec\xd9z\x03FLI'
 '\xb1\x03\x04TEMP'
'\x06'
 '\xe0\x00\x05EFORE'
 '\xd4\xd9~\x06ITING '
 '\x01\x04REAK'
'\x02'
 '\xc5\x9ez\x07 COMPLE'
'\x06'
 '\xd8\xc4z\x04BUND'
 '\xf4\xba\x05\x04FTER'
 '\xf9\xc2z\x05PPROA'
'\x02'
 '\xb5\xc1z\x02RO'
'\n'
 '\xa4\x03\x10ACCENT ATNAH HAF'
 '\xcc\xc8y\nMARK LOWER'
 '\xa7\xb5\x06P'
'\x06'
 '\xf8\x00\x05OINT '
 '\x9d\xf3y\x12UNCTUATION NUN HAF'
'\x04'
 '\xbc\xaf{\x12HOLAM HASER FOR VA'
 '\xb1\xa8~\nQAMATS QAT'
'\x02'
 '\xfb\xd2|U'
'\x12'
 '\xfc\xd6y\x10DSTONE GRAVEYARD'
 '\xf1\xa9\x06\x03VY '
'\x10'
 '\xb0\x02\x06CIRCLE'
 '\xe8M\x0fEXCLAMATION MAR'
 '\xb4\x83~\x04LARG'
 '\x94\xee~\x0eOVAL WITH OVAL'
 '\xbd\x8c}\x13WHITE DOWN-POINTING'
'\t'
 '\xc4\x00\x06 WITH '
 '\x85\xaa{\x04D SA'
'\x04'
 '\xe4\xbe|\x06CIRCLE'
 '\xf1\xc1\x03\x07STROKE '
'\x02'
 '\x15\x03AND'
'\x02'
 '\x15\x03 TW'
'\x02'
 '\x0bO'
'\x02'
 '\x19\x04 DOT'
'\x02'
 '\xe7\xa0zS'
'\xec\x01'
 '\xc0\xc0{\nMMER AND P'
 '\x9d\xc0\x04\x05NGUL '
'\xea\x01'
 '\xd4\x16\tCHOSEONG '
 '\xebiJ'
'\xa6\x01'
 '\x98\x05\tONGSEONG '
 '\xc9{\tUNGSEONG '
'8'
 '\x82\x04A'
 'T\x03EU-'
 '\xfc~\x02I-'
 '\\\x02O-'
 'T\x02U-'
 '\xe3~Y'
'\x0e'
 '\xbc\x8bz\x02A-'
 '\xb8\x9f\x02\x03EO-'
 '\x88\xd6\x03\x02O-'
 'a\x02U-'
'\x04'
 '\x82\xc3yA'
 '\xb7{O'
'\x06'
 '\xe6\xf4yA'
 '\xaf|E'
'\x04'
 '\xde\x9e~I'
 '\x95\xd2{\x02YE'
'\x08'
 '\xb2\x9e~O'
 '\x83\xe1\x01Y'
'\x10'
 '\xa6\xbdyI'
 '\xea\xe0\x04O'
 '\xa7\xe2\x01Y'
'\x0c'
 '.A'
 '\xc6\xf2yE'
 '\x82JO'
 '\x03U'
'\x04'
 '\xbe\xefy-'
 '\x87ME'
'\x08'
 '\xa2\xbcyA'
 '\x826E'
 '\x83JO'
'\x06'
 '\xda\xfe|-'
 '\xf1\x0f\x05RAEA-'
'n'
 '\xc4\x10\x06CIEUC-'
 '\xf2~K'
 '\x94\x7f\x06MIEUM-'
 '\xb4\x7f\x06NIEUN-'
 '\xd6}P'
 '\xbc}\x06RIEUL-'
 '\xda{S'
 '\xf8}\x07TIKEUT-'
 '\xb1\x7f\tYESIEUNG-'
'\x04'
 '.H'
 'gM'
'\x02'
 '\xc9\xc1y\x02IE'
'\x02'
 '\x9d\xcdy\x03IEU'
'\x0c'
 '\xb6\x01C'
 'bP'
 '@\x04SIOS'
 'cT'
'\x02'
 '\xc1\xc5z\x03HIE'
'\x05'
 '\x0b-'
'\x02'
 '\x0bK'
'\x02'
 '\x0bI'
'\x02'
 '\xb9\xf1z\x02YE'
'\x02'
 '\xb5\xf8y\x03IEU'
'\x04'
 '.H'
 'gI'
'\x02'
 '\xb9\xbdy\x02EU'
'\x02'
 '\xc5\xadz\x03IEU'
' '
 '\xf8\x02\x04IOS-'
 '\xc1}\x04SANG'
'\x12'
 '\xae\x02C'
 '\xd2zM'
 '\x96\x05N'
 '\xc2|P'
 '\x9c\x03\x07RIEUL-K'
 'D\x05SIOS-'
 'e\x06TIKEUT'
'\x05'
 '\x0b-'
'\x02'
 '\xaf}P'
'\x04'
 '\xf6|K'
 '\xa7\x03T'
'\x02'
 '\xe9\xc2z\x03IKE'
'\x02'
 '\x0bH'
'\x02'
 '\xd1l\x02IE'
'\x02'
 '\xad\x81z\x02IE'
'\x02'
 '\xd7|I'
'\x0e'
 '\xb2|C'
 '\xaa~H'
 '\x9e\x06K'
 '\xcayM'
 '\x98\x06\x03PAN'
 '\xdfzT'
'\x02'
 '\x0bS'
'\x02'
 '\xab\xf0{I'
'\x02'
 '\x0bA'
'\x02'
 '\xdd}\x06PYEOUN'
'\x0e'
 '\xe8\x01\x06KIYEOK'
 '\x00\x05MIEUM'
 '\x1c\x06PIEUP-'
 '\xacx\x05SSANG'
 '\xe5\x06\x02YE'
'\x04'
 '\xc4\x00\x08ORINHIEU'
 '\x81\x8d{\x02SI'
'\x02'
 '\x0bH'
'\x02'
 '\x0b-'
'\x02'
 '\xb7wH'
'\x04'
 '\x16P'
 '\xc7{T'
'\x02'
 '\x91\x80{\x04HIEU'
'\x14'
 '\x8c\x02\x07ANSIOS-'
 'd\x07HIEUPH-'
 '\xfd~\x05IEUP-'
'\x0c'
 '\xd2wC'
 '\x8e~M'
 '\x8c\t\x07RIEUL-P'
 '\x80\x02\x04SIOS'
 '\xc7yT'
'\x02'
 '\xc1y\x02-T'
'\x04'
 '\xfezS'
 '\xd3zT'
'\x04'
 '\xf6zK'
 '\x9f{P'
'\x04'
 ':C'
 '[R'
'\x02'
 '\x11\x02IE'
'\x02'
 '\x8b\xbdyU'
'\x02'
 '\x8bvH'
'\x08'
 '\x86yC'
 'fN'
 '\xf0\x07\x05PIEUP'
 '\x91x\x06SSANGN'
'\x02'
 '\x93y-'
'\x0c'
 '\xd8~\x08APYEOUNR'
 '\xf9\x01\x06IYEOK-'
'\n'
 '\xae~C'
 '\x86tH'
 '\xd6\x04K'
 '&N'
 '\xc3|P'
'\x04'
 '\xaesP'
 '\xd1\x02\x05SSANG'
'D'
 '\xac~\x05HIEUH'
 '\xc8\x08\x06IEUNG-'
 '\xc0u\x06KIYEOK'
 '\x98\n\x06MIEUM-'
 'X\x06NIEUN-'
 '\xfe~P'
 '\xb4~\x06RIEUL-'
 '\x8c\x7f\x05SSANG'
 'A\x07TIKEUT-'
'\n'
 '\xb6tC'
 '\xd2zM'
 '\xd6\x01P'
 '\x9e\nR'
 '\xb7zS'
'\x08'
 '\x9cw\x05CIEUC'
 '\xcc{\x05SIOS-'
 '\xd2|T'
 '\xf1\x07\x06YEORIN'
'\x16'
 '\x82sC'
 '\xa2\x0eK'
 '\xb2lM'
 '\xd6\x01P'
 '\xa6\x11S'
 '\xdbqT'
'\x08'
 '\xd6\xe3{I'
 '\xdd\x9c\x04\x04SANG'
'\x06'
 '\xfemK'
 '*P'
 '\xff\x02T'
'\x06'
 '\xf2rA'
 '\xba~H'
 '\xbf|I'
'\x08'
 '\xd0t\x05HIEUP'
 '\xf1\x0b\x05IEUP-'
'\x06'
 '\xdekH'
 '\xd6\x04K'
 '\x85|\x06SIOS-T'
'\x06'
 '\xb2pC'
 '\xeezH'
 '\x8b\x06S'
'\x06'
 '\x86lK'
 '\xfa\x04S'
 '\xaf~T'
'\x04'
 '\xcejH'
 '\xd7\x0bR'
'\xfe\x04'
 '\x826E'
 '\xd8s\nLAGOLITIC '
 '\xf4Y\x05REEK '
 '\xa3}U'
'\x14'
 '\xb4\x02\x02AR'
 '\xbc\x7f\x07JARATI '
 '\x89\x7f\x0cRMUKHI SIGN '
'\x08'
 '\xb0\xe6}\x08ADAK BIN'
 '\xb8\xce}\x02UD'
 '\xba\x95~V'
 '\x8d\xae\x01\x03YAK'
'\n'
 '\x9c\xb2z\x06LETTER'
 '\xf2\x10R'
 '\xe3nV'
'\x02'
 '\x11\x02AN'
'\x02'
 '\xab\xb1yI'
'\xd6\x02'
 '\xe6\x15A'
 '\x9c\x7f\x08CAPITAL '
 '\xa8\x7f\x05DRACH'
 '\x16F'
 'l\x04GRAM'
 '\xb0}\x1dINSTRUMENTAL NOTATION SYMBOL-'
 '\x88v\x07KYATHOS'
 '\x92\x08L'
 '\xaa\x7fM'
 '\xd2~O'
 '\x9c\xa5}\x0eRHO WITH STROK'
 '\xc6\xd5\x02S'
 '\xca}T'
 '\xd8~\x16VOCAL NOTATION SYMBOL-'
 'd\x03XES'
 '\x9e\xb3zY'
 '\xa1\xdd\x00\x03ZER'
'\x02'
 '\xb9\xc3{\x02TE'
':'
 '\x92\xc9y1'
 '\xe2\xb7\x062'
 '\x82\x9ay3'
 '\x024'
 '\x82\xe6\x065'
 '\x82\x9ay6'
 '\x027'
 '\x028'
 '\x039'
'\r'
 '\xfe\x99y0'
 '\x021'
 '\x022'
 '\x023'
 '\x034'
'\x0c'
 '\xc0\xbdz\x04ALEN'
 '\xb8\xc4\x05\x05HREE '
 'T\x07RYBLION'
 '\xb5\x7f\x03WO '
'\x04'
 '.O'
 '\xc5\xc0{\x05THIRD'
'\x02'
 '\xd9\x86}\x02BO'
'\x02'
 '\x15\x03 BA'
'\x02'
 '\x9b\xafyS'
'\x04'
 '\xb6\x7fO'
 '\xc5\xc0{\x07QUARTER'
'\x1a'
 '\xd0\x01\x05MALL '
 '\xb5\x7f\x16UBSCRIPT SMALL LETTER '
'\n'
 '\xa6\xe5yB'
 '\xf2\xf4\x02C'
 '\xb6&G'
 '\xceYP'
 '\xbf\xe7}R'
'\x10'
 '\xba\x01D'
 ',\x02LE'
 '\xc7~R'
'\x04'
 ')\x08EVERSED '
'\x04'
 '\xe2\x00D'
 '\xbb\x7fL'
'\x02'
 '\x0bU'
'\x02'
 '\x81\xa4y\nNATE SIGMA'
'\x02'
 '\xb5\x7f\x07OTTED L'
'\n'
 '\x1d\x05TTER '
'\n'
 '\xac\x01\nARCHAIC SA'
 '\xa6\xe1yH'
 '\xec\xc3\x03\nPAMPHYLIAN'
 '\xd3\xda\x02S'
'\x04'
 '\xe2\x9cyA'
 '\xc3(H'
'\x02'
 '\xcf\xd1}M'
'\x08'
 '\xf0\xbd{\x02BO'
 '\x80\xc3\x04\x0bNE HALF SIG'
 '\xe9\xb7{\x03UNK'
'\x04'
 '\x0bN'
'\x05'
 '\xd9\xba{\x07 ALTERN'
'\x04'
 '\xb0u\x04ETRE'
 '\x8d\xdfy\nUSICAL LEI'
'\x0c'
 '\x80\x01\x14ETTER SMALL CAPITAL '
 'm\x02IT'
'\x02'
 '\xef\xb5{R'
'\n'
 '\xa6\xf9|G'
 '\x8e\xe3|L'
 '\x92\xa4\x06P'
 '\xef\xb9zR'
'\x04'
 '\xa2\x8eyI'
 '\xe71S'
'J'
 '\x8a\x021'
 'F2'
 'F3'
 '\xbe\x7f4'
 '\xb6s5'
 '\x82\x9ay7'
 '\x038'
'\x11'
 '\xb2\x8dy0'
 '\x022'
 '\x023'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x0c'
 '\xee\x8cy0'
 '\x022'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x0f'
 '\xb2\x8cy3'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x11'
 '\xf6\x8by1'
 '\x022'
 '\x023'
 '\x024'
 '\x027'
 '\x028'
 '\x039'
'\x02'
 '\xa7\xb2{M'
'\x04'
 '(\x03IVE'
 '\x01\x03OUR'
'\x02'
 '\xd9r\x02 O'
'\x14'
 '\xd6vD'
 '\xc8\xa3y\x03KAI'
 '\xaa\xe6\x06L'
 '\x83uR'
'\x0c'
 '\xbavE'
 '\x9b\x7fU'
'n'
 '\xf0\x00\nCROPHONIC '
 'OR'
'\x04'
 '\xb8z\x02OU'
 '\xb5\xa6y\x03TAB'
'j'
 '\xf4\x08\x06ATTIC '
 '\xa2\x7fC'
 '\x80}\x0cDELPHIC FIVE'
 '\xa0\x02\x0bEPIDAUREAN '
 '\xd8~\x03HER'
 'l\nMESSENIAN '
 'D\x03NAX'
 'X\x0eSTRATIAN FIFTY'
 '\xbb}T'
' '
 '\xb4\x01\x08HESPIAN '
 '\xad\x7f\nROEZENIAN '
'\x0c'
 '$\x02FI'
 '\xa9t\x02TE'
'\x08'
 '\xb0t\x03FTY'
 '\xef\xe0{V'
'\x14'
 '\xe8\x00\x02FI'
 '\xca\x93\x7fO'
 '\x87\xec\x00T'
'\x08'
 '\xfe\x8eyE'
 '\xca\x96\x02H'
 '\xfb\x91~W'
'\x06'
 '\x9a\xfbyF'
 '\xff\xa0\x03V'
'\x02'
 '\x11\x02 M'
'\x02'
 '\x8b\xf6{N'
'\x02'
 '\x1d\x05IAN F'
'\x02'
 '\xd9\xa4{\x02IV'
'\x02'
 '\xf7\xc5yT'
'\x08'
 '\xcc\xae~\x0eAEUM ONE PLETH'
 '\xad\xd2\x01\x08MIONIAN '
'\x06'
 '\xe6\x89|F'
 '\x92\xbb}O'
 'sT'
'\x06'
 '\xa6~F'
 '\x81\x02\x03TWO'
'\x05'
 '\x0b '
'\x02'
 '\xc9\xf3{\x06DRACHM'
'\x04'
 '\xa4}\x05ARYST'
 '\xad\x02\x0cYRENAIC TWO '
'0'
 '\xe0\x03\x02FI'
 '\x94~\x04ONE '
 '\xd9~\x04TEN '
'\x08'
 '\xe2{M'
 '\x8a\x05S'
 '\xbf\x7fT'
'\x04'
 '\xde\x00A'
 'Y\x08HOUSAND '
'\x02'
 '\x0bS'
'\x02'
 '\xfd\x84z\x02TA'
'\x02'
 '\xad\x96y\x03LEN'
'\x0e'
 '\x98\xc2y\x05DRACH'
 '\x9a\xbf\x06H'
 '\xf2\xa0{Q'
 '\xd1\xde\x04\x07THOUSAN'
'\x04'
 '\x11\x02D '
'\x04'
 '\xba~S'
 '\xe3\x01T'
'\x02'
 '\xbb~A'
'\x06'
 '\xa6\xa1{A'
 '\x99\xde\x04\x05UNDRE'
'\x1a'
 '\xdc\x01\x03FTY'
 '\xd1~\x02VE'
'\x11'
 '\x0b '
'\x0e'
 '\x90\x01\x07HUNDRED'
 '\x8a|S'
 '\xab\x03T'
'\x06'
 '\xf2|A'
 '\xc5\x03\x07HOUSAND'
'\x05'
 '\xfd}\x02 T'
'\x07'
 '\xcb} '
'\x0b'
 '\x0b '
'\x08'
 '\xea{S'
 '\xb3\x04T'
'\x06'
 '\xea{A'
 '\xcd\x04\x07HOUSAND'
'\x05'
 '\x8b{ '
'\xbc\x01'
 '8\x06CAPITA'
 '\x01\x04SMAL'
'^'
 '-\tL LETTER '
'^'
 '\x8c\xc5y\x02AZ'
 '\x82\xc6\x06B'
 'l\x04CHRI'
 '\xb6\x7fD'
 'VF'
 'l\x05GLAGO'
 '\x94\xfcz\x02HE'
 '\xf6\x81\x05I'
 '\xa2\xb8}K'
 '\x92\xc7\x02L'
 'bM'
 '\xec\xb5|\x03NAS'
 '\xfa\xc9\x03O'
 'RP'
 '\x84\xb0}\x03RIT'
 '\xbe\xce\x02S'
 '\x9e\x7fT'
 '\xc2\xd0zU'
 '\xae\xaf\x05V'
 '\xa2\x7fY'
 'CZ'
'\x04'
 '\xac\xb1}\x03EML'
 '\xb5\xc7}\x04HIVE'
'\x0c'
 '\x9e\xb5}A'
 '\x9e\xcb\x02E'
 '\x8a\xf5xO'
 '\x03U'
'\x06'
 '\xda\xb6{R'
 '\xb3\xf7\x01S'
'\x02'
 '\xc3\x8byE'
'\x06'
 '\xe4\x84{\tROKUTASTI'
 '\xce\xa1~S'
 '\xe1\x91\x04\x03VRI'
'\x0e'
 '\xfe\x00H'
 '\xe8\xa5y\x03LOV'
 '\xacr\x08MALL YUS'
 '\x95\xc3\x02\x06PIDERY'
'\x06'
 '\xea\xf2xA'
 '\xc1\x8d\x07\x02TA'
'\x05'
 '\xd7\xf8xP'
'\x04'
 '\xaa\xf2xE'
 '\xe51\x04OKOJ'
'\x04'
 '\xa2\xbeyN'
 '\x03T'
'\x02'
 '\x99\x8d\x7f\x03YSL'
'\x04'
 '\\\tATINATE M'
 '\x91\xaf}\x04JUDI'
'\r'
 '\xac\xfc{\tNITIAL IZ'
 '\xe8\x84\x04\x07OTATED '
 ']\x02ZH'
'\x04'
 '\xfa\xefxE'
 '\xdb\x93\x02I'
'\x04'
 '\xc6\x00B'
 'e\x05SMALL'
'\x02'
 '\xa1\xc7z\x02 Y'
'\x02'
 '\x0bI'
'\x02'
 'WG'
'\x02'
 '\xdb\xa0yL'
'\x04'
 '\xde\x83yI'
 '\x89\xa4\x04\x02RI'
'\x06'
 '\xc8\x00\x03JER'
 '\xe4\xafy\x02OB'
 '\xb5\xc9\x04\x02ZE'
'\x02'
 '\xcf\x9fyV'
'\x04'
 '\xd2~I'
 '\xed\xd1y\x02UK'
'X'
 '\xdc\x07\x02AR'
 '\xe1x\x07ORGIAN '
'R'
 '\xa4\x06\x07LETTER '
 '\xc5z\rSMALL LETTER '
'L'
 '\xbe\xf6xA'
 '\xd2\x04B'
 '\xda\x89\x07C'
 '\xce\xf1xD'
 '\x0eE'
 '\x8a\x8e\x07G'
 'JH'
 '\xb2\xf2xI'
 '\xb2\x8d\x07J'
 'bK'
 '\xea\xda{L'
 '\xda\x9c}M'
 '\xdeyN'
 '\xd6\x01O'
 '\xf6\x8c\x07P'
 '\xba\xf1xQ'
 '\xb6\x8e\x07R'
 '^S'
 '\x90\x9f~\x02TA'
 '\xb6\xd4zU'
 '\x82\xc2\x00V'
 '\x92\xb8\x7fW'
 '\xc2\nX'
 '\xcf\x87\x07Z'
'\x04'
 '\xe2\xf3xE'
 '\xaf~H'
'\x04'
 '\xc2\xf3xA'
 '\x83\xc2\x00H'
'\x02'
 '\xaf\xedxA'
'\x04'
 '\xc2\xf1xA'
 'wH'
'\x04'
 '\xee\xf2xA'
 '\xaf~H'
'\x04'
 '\x9e\xf7xH'
 '\xe7\x00I'
'\n'
 '\xa2\x9d~A'
 '\xd2\xcazE'
 '\xce\x04I'
 '\x03O'
'\x04'
 '\xf6\xf1xA'
 '\xd3\x04H'
'\x08'
 '\xd6\xf1xA'
 '\xde\x8e\x07H'
 '\xdb\xf6xI'
'\x04'
 '\xda\xefxA'
 '\xcb\x01I'
'\x06'
 '\x82\xb3yA'
 '\xdc\xb0\x05\x07TURNED '
 '\x85\x9d\x01\x05U-BRJ'
'\x02'
 '\x8b\xb2yG'
'\x07'
 '\x1d\x05 WITH'
'\x04'
 '\xa0\xe8z\x05 HAND'
 '\x91\xdc\x00\x05OUT H'
'"'
 '\xaa\x04A'
 '\x98\x82|\x02ER'
 '\xd0\xfb\x03\x03IVE'
 '\xc6\x00L'
 '\xf6~O'
 '\x9f\x7fU'
'\x06'
 '\xe4\xa4y\x06EL PUM'
 '\xc4:\x07NERAL U'
 '\x9f\x89\x7fS'
'\x08'
 '\xfa\x9f{R'
 '\xab\xe0\x04U'
'\x06'
 '\xd2\xba|N'
 '\xd3\xc5\x03R'
'\x04'
 '\x1d\x05 DOT '
'\x04'
 '\x8e\xe2xM'
 '\x93\xd2\x00P'
'\n'
 '\x96\x01A'
 '\xe4\xbcy\x08EUR-DE-L'
 '\xe5\xc2\x06\x04OWER'
'\x05'
 '\x0b '
'\x02'
 '\xb9\xe0x\x06PUNCTU'
'\x04'
 '\x90\xfa~\x06G IN H'
 '\xef\xdczT'
'\x04'
 '\x84\xf6|\x05CSIMI'
 '\xb1\x8b\x03 LLING DIAGONAL IN WHITE CIRCLE I'
'\x02'
 '\x89\xe3x\x07N BLACK'
'\xd0\x12'
 '\xd8\xa6y\x04ARTH'
 '\xcc\xb5\x07\rDITORIAL CORO'
 '\x9c\xb3\x7f\x13GYPTIAN HIEROGLYPH '
 'l\x03JEC'
 'd\x0fLECTRICAL INTER'
 '\xec\xaey\nQUALS SIGN'
 '\x85\xc5\x06\x08THIOPIC '
'\xe8\x01'
 '\xdc\xdax\x0fCOMBINING GEMIN'
 '\xf6\xa8\x07S'
 '\xc5}\x0bTONAL MARK '
'\x14'
 '\xe4\xe3~\x03CHI'
 '\x8a\x9e\x01D'
 'fH'
 'VK'
 'bR'
 '\x00\x07SHORT R'
 '\x9d\xb4y\x03YIZ'
'\x02'
 '\xd1\xd3~\x03IKR'
'\x04'
 '\xc0\x8dz\x02EN'
 '\xfb\xce\x02U'
'\x02'
 '\xcd\xb3y\x02ID'
'\x06'
 '0\x04ERET'
 '\xc9\x8cz\x02IF'
'\x05'
 '\xad\x7f\x02-H'
'\xd2\x01'
 '\xf6\x99{E'
 '\xcd\xe6\x04\x08YLLABLE '
'\xd0\x01'
 '\x9a\x05B'
 '\xd6\x01C'
 'bD'
 '\x88~\x02FW'
 '\xea\x00G'
 '\xfa|H'
 '\x02J'
 '\x16K'
 'nL'
 '\xe6\x02M'
 '^N'
 '\xb2\x7fP'
 '\xa6~Q'
 'nR'
 '\xe6\x00S'
 'VT'
 'JW'
 '\x16X'
 'nY'
 '\x9f\x7fZ'
'\x10'
 '\xd6\xeaxO'
 '\xcf\x95\x07Z'
'\x0e'
 '\xde\xffyA'
 '\x9e\x8c\x7fE'
 '\xb2II'
 '\x02O'
 '\x03U'
'\x02'
 '\xf3\xe9xO'
'\x10'
 '\xde\xe9xO'
 '\xcf\x95\x07Y'
'\x06'
 'FH'
 '\xf6\xe9xO'
 '\x8f\x96\x07Z'
'\x1a'
 '\xdc\x00\tEBATBEIT '
 '\xbe~H'
 '\xf6\xe9xO'
 '\xcf\x95\x07S'
'\x08'
 '\xca\xa3|B'
 '\x02F'
 '\x02M'
 '\x03P'
'\n'
 '\x8e~H'
 '\xf6\xe9xO'
 '\xaf\x98\x07W'
'\x06'
 '\x9a\x89yE'
 '\xb3II'
'\x04'
 '\xb2\xe7xO'
 '\x8f\x96\x07Y'
'\x08'
 '\x8e\xe7xO'
 '\xaf\x98\x07W'
'\x1c'
 '\xdc\x00\x02GW'
 '\x98|\x07LOTTAL '
 '\xf6\xe9xO'
 '\xcf\x95\x07Y'
'\n'
 '\xb6\xfbyA'
 '\x9e\x8c\x7fE'
 '\xb3II'
'\x04'
 '\xe6{D'
 '\xf7\xe9xO'
' '
 '&C'
 '\xa2{H'
 '\xf7\xe9xO'
'\x1c'
 '\xbe\xfayA'
 '\x9e\x8c\x7fE'
 '\x86\xf4\x06H'
 '\xae\xd5xI'
 '\x02O'
 '\x03U'
'\x02'
 '\xf9\xfa~\x02SE'
'\x02'
 '\xdf\xdexT'
'\xde\x10'
 '\xbe\xc7\x00A'
 '\xc8a\x03B00'
 '\xc8\x1c\x02C0'
 '\xecz\x02D0'
 '\xa0}\x02E0'
 '\xc8{\x02F0'
 '\xc0{\x02G0'
 '\xa4\x7f\x03H00'
 '\xb4~\x02I0'
 '\xb4\x7f\x03K00'
 '\x94\x7f\x03L00'
 '\x90{\x02M0'
 '\x8ayN'
 '\xf0z\x02O0'
 '\xe4~\x02P0'
 '\xbc\x7f\x03Q00'
 '\xf4}\x02R0'
 '\xb4{\x02S0'
 '\x88}\x02T0'
 '\xd4|\x02U0'
 '\xc4z\x02V0'
 '\x9c}\x02W0'
 '\x8c\x7f\x03X00'
 '\xac\x7f\x03Y00'
 '\xc1|\x02Z0'
'R'
 '\x8a\x020'
 '\x93~1'
'0'
 '\xde\xcax0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\xbe\xb6\x075'
 '\xb7\x7f6'
'\x13'
 '\x8e\xcaxA'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x02F'
 '\x02G'
 '\x03H'
'\x15'
 '\xc2\xc9xA'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x03I'
'"'
 '\xee\xc8x1'
 '\x9a\xb8\x072'
 'f3'
 '\xba\xf2y4'
 '\x025'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\x039'
'\x07'
 '\x82\xc8xA'
 '\x03B'
'\x0b'
 '\xe6\xc7xA'
 '\x02B'
 '\x02C'
 '\x03D'
'\x12'
 '\xee\xf1y1'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'\x18'
 '\xe6\xc6x1'
 '\x022'
 '\x023'
 '\xfe\xb7\x074'
 '\x86\xc8x5'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\xb7\xaa\x018'
'@'
 '\xf6\x010'
 '\xfe~1'
 '\xb7\x7f2'
'\x0e'
 '\xca\xc5x0'
 '\x021'
 '\x022'
 '\x023'
 '\xb6\xaa\x014'
 '\xcf\xd5~5'
'\x1c'
 '\xb2\xefy0'
 '\xce\xd5~1'
 '\x022'
 '\x023'
 '\xb6\xaa\x014'
 '\xce\xd5~5'
 '\x026'
 '\xb6\xaa\x017'
 '\x028'
 '\xcf\xd5~9'
'\x16'
 '\xfa\xc3x1'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\xb7\xaa\x019'
'\x9a\x01'
 '\xc6\x040'
 '\xee~1'
 '\x9e~2'
 '\xfe~3'
 '\xf5\xecy\x0240'
'\x1c'
 '\xf2\xecy0'
 '\x021'
 '\xce\xd5~2'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\xb6\xaa\x017'
 '\xce\xd5~8'
 '\x039'
'2'
 '\xf6\x000'
 '\xc6\xc0x1'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\x027'
 '\xb6\xaa\x018'
 '\x039'
'\x1b'
 '\xc2\xc0xA'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02I'
 '\x02J'
 '\x02K'
 '\x03L'
'\x1e'
 '\xd6\xbfx0'
 '\x9a\xc1\x071'
 '\xe6v2'
 '\x86\xc8x3'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\t'
 '\xe6\xbexA'
 '\x02B'
 '\x03C'
'*'
 '\xfet1'
 '\xfa\xf3y2'
 '\xce\xd5~3'
 '\x024'
 '\x025'
 '\x026'
 '\xfe\xb7\x077'
 '\x86\xc8x8'
 '\x039'
'^'
 '\xc6\x020'
 '\xb6\xe7x1'
 '\xda\x97\x072'
 '\x96\x7f3'
 '_4'
'\x06'
 '\x8e\xbdx0'
 '\x021'
 '\x032'
'\x16'
 '\xea\xbcx0'
 '\x021'
 '\xb6\xaa\x012'
 '\xce\xd5~3'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xfe\xbbx0'
 '\x021'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\xb7\xaa\x019'
'\x16'
 '\x8a\xbbx1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xfe\xb7\x076'
 '\x86\xc8x7'
 '\x028'
 '\x039'
'X'
 '\x8a\x020'
 '\x86\x7f1'
 '\xc2\xe5x2'
 '\xef\x99\x073'
'\x12'
 '\xea\xb9x0'
 '\x021'
 '\xb6\xaa\x012'
 '\x023'
 '\xce\xd5~4'
 '\x025'
 '\x036'
'\x18'
 '\x96\xb9x0'
 '\xb6\xaa\x011'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\x028'
 '\x039'
'\x1a'
 '\x9a\xb8x1'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\xb6\xaa\x017'
 '\x028'
 '\x039'
'l'
 '\xd6\x030'
 '\x86\x7f1'
 '\x96\x7f2'
 '\x96\x7f3'
 '\xbf\x7f4'
'\x0e'
 '\xee\xb6x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'\x16'
 '\xaa\xb6x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\xb6\xaa\x015'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xbe\xb5x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xfe\xb7\x076'
 '\x86\xc8x7'
 '\x028'
 '\x039'
'\x1a'
 '\xd2\xb4x0'
 '\x021'
 '\x022'
 '\x023'
 '\xfe\xb7\x074'
 '\x86\xc8x5'
 '\x026'
 '\xb6\xaa\x017'
 '\xce\xd5~8'
 '\x039'
'\x16'
 '\xd6\xb3x1'
 '\xb6\xaa\x012'
 '\xce\xd5~3'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\x028'
 '\x039'
'D'
 '\x9e\x010'
 '\x8e\x7f1'
 '\xe3\xdex2'
'\x18'
 '\xea\xdcy0'
 '\xce\xd5~1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\x028'
 '\x039'
'\x18'
 '\xc2\xb1x1'
 '\xb6\xaa\x012'
 '\xca\x8d\x063'
 '\x86\xc8x4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x0e'
 '\xd6\xb0x1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x037'
'\x1a'
 '.0'
 'g1'
'\x04'
 '\xfe\xafx0'
 '\x031'
'\x16'
 '\x96\xday1'
 '\xce\xd5~2'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x96\x01'
 '\xda\x030'
 '\x9a\x7f1'
 '\x86\x7f2'
 '\xfe~3'
 '\xaa\xdax4'
 '\xbb\xa5\x075'
'\x08'
 '\x9af0'
 '\x87\xc8x1'
' '
 '\xb2\xd8y0'
 '\xce\xd5~1'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x9a\xb8\x076'
 '\xea\xc7x7'
 '\x028'
 '\x039'
'\x1c'
 '\xae\xd7y0'
 '\xce\xd5~1'
 '\x022'
 '\x023'
 '\xb6\xaa\x014'
 '\x025'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\xb7\xaa\x019'
'\x1c'
 '\x96m0'
 '\xea\xbex1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\xb7\xaa\x019'
'"'
 '\xca\xd5y1'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\xb6\xaa\x015'
 '\xaa\xab\x066'
 '\xa6\xaax7'
 '\x028'
 '\x039'
'\x0f'
 '\xa2\xaaxA'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x03F'
'\xc2\x01'
 '\xca\x040'
 '\x84~\x02L0'
 '\xe9}\x02U0'
'4'
 '\xc2\x010'
 '\x8e\x7f1'
 'W2'
'\x08'
 '\x86\xa9x0'
 '\x021'
 '\xb7\xaa\x012'
'\x1a'
 '\x8e\xd3y0'
 '\x021'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\xb6\xaa\x018'
 '\xcf\xd5~9'
'\x12'
 '\xe6\xa7x1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
','
 '\x96\x010'
 '\x96\x7f1'
 '\xff\x8fz2'
'\x16'
 '\xe6\xa6x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\xb6\xaa\x017'
 '\xce\xd5~8'
 '\x039'
'\x14'
 '\xfa\xa5x1'
 '\x022'
 '\x023'
 '\x024'
 '\xb6\xaa\x015'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\x039'
'b'
 '\xae}0'
 '\x8e\x041'
 '\xb2m2'
 '\xd6\x113'
 '\xcbg4'
'\x1c'
 '\xd6\xa4x0'
 '\x021'
 '\x022'
 '\xb6\xaa\x013'
 '\x024'
 '\x025'
 '\xce\xd5~6'
 '\xb6\xaa\x017'
 '\xce\xd5~8'
 '\x039'
'\x18'
 '\xda\xa3x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\xfe\xb7\x078'
 '\x87\xc8x9'
'\x84\x01'
 '\x82\x040'
 '\xfe~1'
 '\xf6~2'
 '\x86\x7f3'
 'G4'
'\x0c'
 '\xe2\xccy0'
 '\xce\xd5~1'
 '\x022'
 '\x023'
 '\x034'
'\x1a'
 '\xf2\xa1x0'
 '\xb6\xaa\x011'
 '\xce\xd5~2'
 '\xfe\xb7\x073'
 '\x86\xc8x4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x1a'
 '\xf6\xa0x0'
 '\x021'
 '\xb6\xaa\x012'
 '\xce\xd5~3'
 '\xb6\xaa\x014'
 '\xce\xd5~5'
 '\x026'
 '\x027'
 '\xb6\xaa\x018'
 '\xcf\xd5~9'
','
 '\x9e\xcay0'
 '\xce\xd5~1'
 '\xf2\xb5\x072'
 '\x92\xcax3'
 '\x024'
 '\xb6\xaa\x015'
 '\x026'
 '\x027'
 '\xce\xd5~8'
 '\x039'
'\x18'
 '\xe2V1'
 '\x86\xc8x2'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x14'
 '\xfe\x9dx1'
 '\xb6\xaa\x012'
 '\xce\xd5~3'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\x038'
'\x10'
 '\x92\x9dx1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'&'
 '\xde\x000'
 '\xbf\x7f1'
'\x10'
 '\xde\xc6y0'
 '\x021'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x035'
'\x16'
 '\xe6\x9bx1'
 '\x022'
 '\x023'
 '\x024'
 '\xb6\xaa\x015'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\xb7\xaa\x019'
'\x12'
 '\xfa\x9ax1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\x038'
'\x80\x01'
 '\xce\x030'
 '\x96\x7f1'
 '\x82e2'
 '\x96\x1a3'
 '\x86\x7f4'
 'O5'
'\n'
 '\xd2\x99x0'
 '\x021'
 '\x022'
 '\x023'
 '\x034'
'\x18'
 '\x9e\x99x0'
 '\x021'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\xb6\xaa\x015'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xa2\x98x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\x027'
 '\xce\xd5~8'
 '\x039'
'\x16'
 '\xb6\x97x0'
 '\xb6\xaa\x011'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xca\x96x1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xca\x8d\x067'
 '\x86\xc8x8'
 '\x039'
'\x82\x01'
 '\xd6\x030'
 '\x96\x7f1'
 '\xba{2'
 '\xce\x033'
 '\x96\x7f4'
 'G5'
'\x0e'
 '\x92\x95x0'
 '\x9a\xc1\x071'
 '\xea\xbex2'
 '\x033'
'\x1a'
 '\xd6\x94x0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\xb6\xaa\x015'
 '\x026'
 '\x027'
 '\xce\xd5~8'
 '\x039'
'\x1a'
 '\xea\x93x0'
 '\xb6\xaa\x011'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\xb6\xaa\x017'
 '\x028'
 '\xcf\xd5~9'
'\x16'
 '\xee\x92x0'
 '\x021'
 '\x022'
 '\xb6\xaa\x013'
 '\xce\xd5~4'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x14'
 '\xb6\xbcy1'
 '\xce\xd5~2'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'X'
 '\x82\x020'
 '\x82w1'
 '\x8e\x082'
 '\xa7\x7f3'
'\x12'
 '\xf2\x90x0'
 '\x021'
 '\x022'
 '\x023'
 '\xb6\xaa\x014'
 '\xce\xd5~6'
 '\x027'
 '\x038'
'\x18'
 '\xca\xbay0'
 '\xce\xd5~1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\xb6\xaa\x018'
 '\xcf\xd5~9'
'\x16'
 '\xa2\x8fx1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\xb6\xaa\x018'
 '\x039'
'\xb8\x01'
 '\xaa\x040'
 '\xc2\xb6x1'
 '\xf2\xac\x072'
 '\xd6\x1b3'
 '\x86\x7f4'
 '\x82\x7f5'
 '\xaf\x7f6'
' '
 '\xe2\x8dx0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\xf3\xb5\x077'
'*'
 '\xcaC0'
 '\xc6\xc9x1'
 '\xb6\xaa\x012'
 '\xce\xd5~3'
 '\xb6\xaa\x014'
 '\xce\xd5~5'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\x8e\x8cx0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\xb6\xaa\x016'
 '\xce\xd5~7'
 '\xb6\xaa\x018'
 '\xcf\xd5~9'
'\x18'
 '\x92\x8bx0'
 '\xb6\xaa\x011'
 '\xce\xd5~2'
 '\x023'
 '\xb6\xaa\x014'
 '\xce\xd5~5'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x14'
 '\x96\x8ax1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\xb6\xaa\x018'
 '\xcf\xd5~9'
'8'
 '\x8a\x010'
 '\x9e\x7f1'
 '\xbbo2'
'\x16'
 '\xbe\xb3y0'
 '\xce\xd5~1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xa6\x88x1'
 '\x9a\xc1\x072'
 '\xea\xbex3'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\xe4\x01'
 '\xba\x010'
 '\xe9~\x02A0'
'D'
 '20'
 '\x92\xb3x1'
 '\x022'
 '\xcb\x96\x073'
'\x16'
 '\xe6\x86x1'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\xfe\xb7\x077'
 '\x86\xc8x8'
 '\x039'
'\xa0\x01'
 '\xee\x020'
 '\x86\x7f1'
 '\xb6\xb0x2'
 '\xee\x96\x073'
 '\xde74'
 '\xba\xb1x5'
 '\x026'
 '\xef\xbc\x017'
'\x1c'
 '\xc2\xafy0'
 '\xce\xd5~1'
 '\xb6\xaa\x012'
 '\x023'
 '\xce\xd5~4'
 '\xb6\xaa\x015'
 '\xce\xd5~6'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\x8a\x84x0'
 '\x021'
 '\x022'
 '\x023'
 '\xb6\xaa\x014'
 '\xce\xd5~5'
 '\x026'
 '\xb6\xaa\x017'
 '\xce\xd5~8'
 '\x039'
'\x18'
 '\x8e\x83x1'
 '\x022'
 '\x023'
 '\x024'
 '\xb6\xaa\x015'
 '\xca\x8d\x066'
 '\x86\xc8x7'
 '\x028'
 '\x039'
'\x02'
 '\x93\xdexN'
'\xcc\x02'
 '\x82\x0eE'
 '\xe6xI'
 '\xf6yO'
 '\xe5\x92x\tRIVE SLOW'
'\xde\x01'
 '\x9c\x04\nMINO TILE '
 '\xc0~\x05TTED '
 '\xb0~\x04UBLE'
 '\xb1\xc6x\x03WNW'
'\x08'
 '\xac\x01\n OBLIQUE H'
 '\xa8\xbe|\r-STRUCK SMALL'
 '\xbd\xc1\x03\x02D '
'\x04'
 '\xb2\x94|F'
 '\x1bM'
'\x02'
 '\xd9\xc1x\x03YPH'
'\n'
 '\xb6\xb3~C'
 '\xc4\x88|\x04OBEL'
 '\x84\xb5~\x0eRIGHT-POINTING'
 '\xee\x91\x7fS'
 '\x89\xb6\x02\tTRANSPOSI'
'\xc8\x01'
 '\xcc\x00\x08HORIZONT'
 '\x01\x06VERTIC'
'd'
 '\x11\x02AL'
'd'
 '\xda\xfcx '
 '\xd1\x83\x07\x02-0'
'b'
 ':0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'\x0e'
 '\xc9D\x02-0'
'4'
 '\xac\x06\x0bAMOND WITH '
 '\xeazG'
 '\xf4\x82x\x08SABLED C'
 '\xc1\x8a\x04\x04VORC'
'('
 '\xd4\x02\x03IT '
 '\xf1}\x08RAM FOR '
'\x12'
 '\xcc\x01\x05EARTH'
 '\x94\x7f\x05GREAT'
 '&H'
 ']\x04LESS'
'\x04'
 '\xad\xd2{\x04ER Y'
'\x04'
 '\x9c\x9d~\x07EAVENLY'
 '\x01\x04UMAN'
'\x07'
 '\x19\x04LY H'
'\x04'
 '\xe6\x9d~E'
 '\xab\xf6{U'
'\x16'
 '\xe8\xa5}\x05EIGHT'
 '\xa2\xdc\x02F'
 'p\x02NI'
 '\x02O'
 'NS'
 '\xbe\x7fT'
 '\xed\xc2z\x04ZERO'
'\x04'
 ',\x03HRE'
 '\xb9\xa4}\x02WO'
'\x02'
 '\xb7\xa4}E'
'\x04'
 '\xa0\xa4}\x04EVEN'
 '\x01\x02IX'
'\x02'
 '\xb7\x7fN'
'\x04'
 '\xa4\x7f\x02IV'
 '\xb9\xa4}\x03OUR'
'\x08'
 '\xaa\xe7yB'
 '\xac\x99\x06\x03LEF'
 '\x00\x04RIGH'
 '\xc3\xe6yT'
'\x02'
 '\x8b\xe6yT'
'8'
 '\xe8\xa4\x7f\rCIMAL EXPONEN'
 '\xb8\xe4\x00\x06SERET '
 '\xfdw\tVANAGARI '
'.'
 '\xa0\xfc}\x02CA'
 '\xac\x94z\x08GAP FILL'
 '\xc4z\x04HEAD'
 '\x94\xfb\x07\x07LETTER '
 '\xc0|\x05SIGN '
 '\x85\x7f\x0bVOWEL SIGN '
'\x04'
 '\xc8\xd5{\x0bCANDRA LONG'
 '\x01\rPRISHTHAMATRA'
'\x12'
 '\x88\x03\x0cCANDRABINDU '
 'l\x14DOUBLE CANDRABINDU V'
 '\x84\xeew\x0cHIGH SPACING'
 '\xe0\x91\x08\x08INVERTED'
 '\x98\xbax\x06PUSHPI'
 '\xe9\xc5\x07\x07SPACING'
'\x02'
 '\xcd\xde}\x02 C'
'\x02'
 '\xf7\xaezI'
'\x08'
 '\xbe\xffxA'
 '\xbe\xaf\x7fT'
 '\xf3\xd0\x07V'
'\x12'
 '\xd2\x95{B'
 '\x84\xe7~\x06CANDRA'
 '\xc8\xbd~\x02DD'
 '\x9a\xc7\x07G'
 '\xdc\xd6z\x05HEAVY'
 '\xda\xcf\x01J'
 '\xba\xdb}S'
 '\xa3\x8a~Z'
'\x04'
 '\x8e\x80xG'
 '\xa7\x92\x05L'
'\x08'
 '8\x06CAPITA'
 '\x01\x04SMAL'
'\x04'
 '-\tL LETTER '
'\x04'
 '\xa6\x8axE'
 '\xb7\x11O'
'\x86\x1c'
 '\xca\xc3\x02A'
 '^E'
 '\xeatH'
 '\xd0x\x07IRCLED '
 '\xdcx\x03JK '
 '\xa2LO'
 '\xf0}\x04ROSS'
 '\x9a\xa5~U'
 '\xcbhY'
'\xbc\x02'
 '\xfc\x14\x0fPRIOT SYLLABLE '
 '\xf5k\x07RILLIC '
'\xce\x01'
 '\x8c\x12\x0fCAPITAL LETTER '
 'bK'
 '\x94\x7f\x07LETTER '
 '`\x02PA'
 '\xe9p\rSMALL LETTER '
'd'
 '\xf2\x0eA'
 '\x9a\x7fB'
 '^C'
 '\xbe~D'
 '\xaa\x7fE'
 '\x8a\x7fG'
 '\xa6\x7fH'
 '\xaa~I'
 '\xc6\xfewL'
 '\xc6\x80\x08M'
 'ZN'
 '\xb6\x7fP'
 '\xb6\xf4wQ'
 '\xde\x8a\x08R'
 '\x8e\x7fS'
 '\xda~T'
 '\x86\xe7wW'
 '\xfa\x97\x08Y'
 'SZ'
'\x04'
 '\xc8\xcfz\x03EML'
 '\xe3\xc9\x01H'
'\x06'
 '\x86\xe8wA'
 '\xe0\x98\x08\rERU WITH BACK'
 '\xd7\xe2wN'
'\x02'
 '\xb9\x80x\x02 Y'
'\n'
 '\xf6\xedzC'
 '\xe2\x92\x05E'
 'fS'
 '\xcb\xe6wW'
'\x04'
 '\xc6\xe6wS'
 '\x03W'
'\x02'
 '%\x07 WITH M'
'\x02'
 '\x95\xc3{\x05IDDLE'
'\x08'
 '\xce\x96|H'
 '\xe5\xe9\x03\x04OFT '
'\x06'
 '\xa6\xe5wD'
 '\xff\x9a\x08E'
'\x04'
 '\xb6\xe0wL'
 '\x03M'
'\x08'
 '8\x08EVERSED '
 '\xeb\xf4wH'
'\x06'
 '\xce\xddyD'
 '\xba\xce~Y'
 '\xa7\xb8\x7fZ'
'\x04'
 '\x9c\xacx\x05ALOCH'
 '\x9b\xd4\x07E'
'\x02'
 '\xcf\x85} '
'\x02'
 '\x89|\x06EUTRAL'
'\x04'
 '\x15\x03ONO'
'\x04'
 ':C'
 '[G'
'\x02'
 '\x85\xe9{\x05RAPH '
'\x02'
 '\xe5\xc3{\x04ULAR'
'\x08'
 '\x11\x02OT'
'\x08'
 '\xaa\xddwA'
 '\x91\xa3\x08\x06IFIED '
'\x06'
 '\xee\xdcwA'
 '\xcc\xa3\x08\x02CL'
 '\xf7\x90yY'
'\x02'
 '!\x06OSED L'
'\x02'
 '\xe1\xec~\x05ITTLE'
'\x06'
 '4\x07A WITH '
 '\xff\xdfwW'
'\x04'
 '\xa2\xbd{H'
 '\xc7\xb6|S'
'\x04'
 ')\x08HE WITH '
'\x04'
 '\x9e\xdb|D'
 '\xa1\xe1~\nSTROKE AND'
'\x06'
 '0\x07L WITH '
 '\x83xN'
'\x04'
 '\xd2\xbb{H'
 '\xd7\xbc\x04M'
'\x0c'
 '\xa6\x01J'
 '\\\x08OUBLE MO'
 '\x86\xddwW'
 '\xd3\xa2\x08Z'
'\x06'
 '\x8e\xe4|E'
 '\xa2\xf9zW'
 '\x03Z'
'\x02'
 '\x0bN'
'\x02'
 '\xc5z\x02OC'
'\x02'
 '\xed\xbey\x02ER'
'\x04'
 '\xb6\xe3zC'
 '\x8f\x98\x05L'
'\x06'
 '\x9a\x7fI'
 '\x8c\xe9~\x06LENDED'
 '\xb1\x98y\x08ROAD OME'
'\x02'
 '\x89\x8e|\x04LEUT'
'\x02'
 '\x99\x90y\x03YER'
'\x04'
 '\xf8}\x05MULTI'
 '\xbd\xd6x\x0eSMALL CAPITAL '
'\x02'
 '\xad\xa2x\x03AVY'
'b'
 '\xae~A'
 '\x9a\x7fB'
 '^C'
 '\xbe~D'
 '\xaa\x7fE'
 '\x8a\x7fG'
 '\xa6\x7fH'
 '\xaa~I'
 '\xc6\xfewL'
 '\xc6\x80\x08M'
 'ZN'
 'l\x02PE'
 '\xfe\xf3wQ'
 '\xde\x8a\x08R'
 '\x8e\x7fS'
 '\xda~T'
 '\x86\xe7wW'
 '\xfa\x97\x08Y'
 'SZ'
'n'
 '\xa2\xd3wA'
 '\x02E'
 '\x02I'
 '\xaa\xd8\x05J'
 '\xb6\xd6\x02K'
 '\x02L'
 '\x02M'
 '\x02N'
 '\xa6\xd1wO'
 '\xde\xae\x08P'
 '\x02R'
 '\x02S'
 '\x02T'
 '\xa6\xd1wU'
 '\xb2\xae\x08W'
 '\xa6\xa4{X'
 '\xd7\x85\x02Z'
'\x08'
 '\xce\xd1wA'
 '\x02E'
 '\x02I'
 '\x03O'
'\n'
 '\xa2\xd1wA'
 '\x02E'
 '\x02I'
 '\x02O'
 '\x03U'
'\xae\x0f'
 '\xd0\x00\x08NEIFORM '
 'gP'
'\x02'
 '\xb1\xf1~\x02 O'
'\xac\x0f'
 '\xcc\xc5\x01\rNUMERIC SIGN '
 '\xb0~\x11PUNCTUATION SIGN '
 '\xbd\xbd~\x05SIGN '
'\xde\r'
 '\x92\xb3\x01A'
 '\xee{B'
 '\x9avD'
 '\xfevE'
 '\xc2eG'
 '\xda|H'
 '\xf2zI'
 '\xf6kK'
 '\xd6gL'
 '\x96zM'
 '\x8apN'
 '\xc6|P'
 '^R'
 '\xdanS'
 '\xb6xT'
 '\xb6kU'
 '\xf3{Z'
'$'
 '\xe6\x02A'
 '\xa2\xb4yE'
 '\x96\xca\x06I'
 '\xa3\x7fU'
'\x0b'
 '*5'
 '\xce\x8fxB'
 '\xd3\xbc\x7fM'
'\x05'
 '\x1d\x05 TIME'
'\x02'
 '\x93\xdcyS'
'\x0f'
 '\xc8\xfdw\x07 OVER Z'
 '\x9eN3'
 '\x86\xb5\x08B'
 '\xfe\xcawG'
 '\x87\xea\x01Z'
'\x05'
 '\x11\x02 K'
'\x02'
 '\x11\x02AB'
'\x02'
 '\x0bA'
'\x02'
 '\x0b '
'\x02'
 '\x0bT'
'\x02'
 '\xb3\xdfyE'
'\x0b'
 '* '
 '\xf2\xc9wG'
 '\xd3\xc2\x00M'
'\x04'
 '4\x08SQUARED '
 '\x8b\x7fT'
'\x02'
 '\x19\x04TIME'
'\x02'
 '\x0bS'
'\x02'
 '\xbd\x8cx\x02 K'
'\xa5\x01'
 '\xca\x11 '
 '\xa6\xb7w2'
 '\x02B'
 '\xee\xc5\x08D'
 '\xe2}M'
 'VN'
 '\xa6wR'
 '\xc4~\x02SH'
 '\xac\x80|\x02TU'
 '\xf3\xfe\x03Z'
'\x06'
 '\x1a3'
 '\xc3\xc7wU'
'\x05'
 ')\x08 TIMES K'
'\x02'
 '\xfd\xa8y\x02AS'
'\x11'
 '\xe0\x00\x07 TIMES '
 '\x96\xc6w2'
 '\xd0\xc2\x00\x02UM'
 '\xb3\xbd\x7fX'
'\x08'
 '\x92\xc6wA'
 '\xdc\xe5\x00\x02KU'
 '\xcf\xd4\x07T'
'\x02'
 '\xc9\xb0y\x02AK'
'S'
 '\xda\x07 '
 '\xfe}2'
 '\xe6\xbfw4'
 '\x8a\xc0\x08I'
 '\x87{U'
'5'
 '\xe8\x00\x07 TIMES '
 'Q\x02DA'
'\x05'
 '\x0b '
'\x02'
 '\xc9\xab{\x04TIME'
'.'
 '\xd6\x03A'
 '\x9a\xc9wB'
 '\xbe\xc4\x00D'
 '\xce\xf1\x07G'
 '\x9a\xd6wH'
 '\xbe\xa9\x08I'
 '\xa2\xf3wK'
 '\xcaVL'
 '\x92\xc4\x00M'
 '\xceHP'
 '\x92\xa9\x08S'
 '\x92\x8exT'
 '\x9b\xf1\x07U'
'\x06'
 '* '
 '\x96\xc2wD'
 '\xd3\xde\x05R'
'\x02'
 '\x91\xa4y\x06PLUS G'
'\x04'
 '\xb2\xc6wH'
 '\xa9\xe6\x01\x02IG'
'\x06'
 '\x9e\xf3wG'
 '\x9eNM'
 '\x9f\x14S'
'\n'
 '\x1aA'
 '\xf7\xc0wU'
'\t'
 '\xf2\xc0wL'
 '\xc2\xbf\x08N'
 '\xc3\xc0wR'
'\x02'
 '\xf7u2'
'\x05'
 '\x0bS'
'\x02'
 '\x0bH'
'\x02'
 '\x0bG'
'\x02'
 '\x9b\xacyA'
'\x05'
 '\xf7\xbfw3'
'\x13'
 '%\x07 TIMES '
'\x10'
 '\x8a\x01A'
 '\xba\xd3wH'
 '\x9e8N'
 '\xe5\xf3\x07\x02U2'
'\x07'
 '!\x06 PLUS '
'\x04'
 '\xc6\x95yA'
 '\xf3\xda~B'
'\x06'
 '0\x06 PLUS '
 '\xff\xbdwL'
'\x04'
 '\x82\xd3wH'
 '\x03N'
'\x04'
 '\x8c\x81x\tCROSSING '
 '\xbb\xff\x07S'
'\x02'
 '\x0bH'
'\x02'
 '\x15\x03ESH'
'\x02'
 '\xa7\xccwI'
'\x05'
 '\x0b '
'\x02'
 '\x0bG'
'\x02'
 '\xcb\xd1yU'
'\x13'
 '\x98\x01\x07 TIMES '
 '\xd6\x87xB'
 '\xe5\xf7\x07\x02UM'
'\x07'
 '%\x07 TIMES '
'\x04'
 '\xa2tK'
 '\x9f\xdcwP'
'\x08'
 '\xf2\x00L'
 'X\x02ME'
 'nS'
 '\xe3\xbawU'
'\x02'
 '\xa3\xf8{H'
'\x02'
 '\xf1\xff{\x05 PLUS'
'\x02'
 '\x8bzA'
'\x15'
 '\x1a '
 '\xaf\xc9wU'
'\x10'
 '\xae}G'
 '\xfa\x04K'
 '\xbc\x7f\x07SHESHIG'
 '\x85\x7f\x06TIMES '
'\x08'
 '\xfa\x96yB'
 '\xfa\xd3~M'
 '\xf9\x95\x08\x0eU PLUS U PLUS '
'\x04'
 '\xc3{U'
'\x05'
 '\x0b '
'\x02'
 '\x0bT'
'\x02'
 '\xe5\x95y\x06IMES B'
'\x02'
 '\x0bU'
'\x02'
 '\x0bS'
'\x02'
 '\xef\xf8{H'
'\n'
 '\xa2\x99yG'
 '\xac\xe7\x06\x07OVER U '
 '\x83\x9e{U'
'\x06'
 '\xd8\x01\nPA OVER PA'
 '\xa8\xf8w\nSUR OVER S'
 '\xbd9\x18U REVERSED OVER U REVERS'
'\x02'
 '\x0b '
'\x02'
 '-\tGAR OVER '
'\x02'
 '\xa3\xbdwG'
'@'
 '\xc2\x03A'
 '\x86tE'
 '\x82\nI'
 '\xef~U'
'\r'
 '\xf6\x9dyG'
 '\xfe\x95~K'
 '\x02M'
 '\xcb\xcc\x08R'
'\x05'
 '\xc9\xf6{\x11 OVER TUR ZA OVER'
'\x0f'
 '\xa2h '
 '\xbe\xcawL'
 '\xd3\xcd\x08R'
'\t'
 '\x0b '
'\x06'
 '\xdc\x00\x08OVER TIR'
 '[T'
'\x02'
 '\x91l\x06IMES T'
'\x05'
 '\x0b '
'\x02'
 '\x0bG'
'\x02'
 '\x15\x03AD '
'\x02'
 '\x99|\x08OVER GAD'
'#'
 '\xa2\x03 '
 '\xc6~B'
 '\xe2~G'
 '\x92\x9byK'
 '\x8f\x95~R'
'\x0f'
 '%\x07 TIMES '
'\x0c'
 '\xd6\xe1wB'
 '\x9e\xb0\x01G'
 '\xf4\xf3\x03\x02SH'
 '\xf6\xfa\x02T'
 '\xbb\xbawU'
'\x02'
 '\x99\x99y\x02UG'
'\x07'
 '\x0b '
'\x04'
 '\x90\x01\x1dOVER TAB NI OVER NI DISH OVER'
 '\xe3\xa2yS'
'\x02'
 '\xa1\xc9y\x02 D'
'\x08'
 '\xfa\xa4yA'
 '\xfe\xcb\x06G'
 '\xd1\x0f\x06TIMES '
'\x04'
 '\xda\xdewH'
 '\x03M'
'\xb0\x01'
 '\x9a\x0cA'
 '\xc2vH'
 '\xf6~I'
 '\xe7~U'
'\x13'
 '\xb0\xe7{\x05 OVER'
 '\xd6\x99\x04D'
 '\xce\xeewH'
 '\xa2\x91\x08M'
 'oR'
'\x05'
 '\xc3\xabw9'
'\x05'
 '\xa3\x82yA'
'\x05'
 '\x9b\xabw2'
'\x0f'
 '\xb2n '
 '\x8a\x12G'
 '\xd2\x94yK'
 '\xc3\xd3\x02L'
'\x07'
 '\x0b4'
'\x05'
 '1\n OVER SIG4'
'\x02'
 '\xc7r '
'\\'
 '\xc6\x07A'
 '\x82~E'
 '\xee{I'
 '\x83\x7fU'
'\t'
 '\xe8\x00\x0f OVER INVERTED '
 '\xde\xa8w2'
 '\xb3\xc3\x00B'
'\x02'
 '\xc7\x9azS'
'('
 '\xca\x03D'
 '\xfa}M'
 '\x92jN'
 '\xf2\x14R'
 '\x8f\xbdwT'
'\x07'
 '\x0b '
'\x04'
 '\xa4\xebw\x14OVER SHIR BUR OVER B'
 '\xa3\xf2\x07T'
'\x19'
 '%\x07 TIMES '
'\x16'
 '\xda\xa6wA'
 '\xd6\xda\x08B'
 '\xea\xf1wD'
 '\xae\xbc\x7fG'
 '\xb8\xba\x08\x03IGI'
 '\x92\x05K'
 '\xb6\x8a~L'
 '\xde\x87\x02M'
 '\xbf\xf4wS'
'\x02'
 '\xf3\xb4wU'
'\x04'
 '\x9a\xb5wA'
 '\x8b\xcb\x08U'
'\x02'
 'GL'
'\x07'
 '%\x07 TIMES '
'\x04'
 '\xd2\xa4wA'
 '\xbb\x08I'
'\x13'
 '\xea\x00 '
 '\x9a\xfbwG'
 '\xb2\xa8\x7fN'
 '\x95\xdc\x08\x02SH'
'\x07'
 '\xea\xa3w2'
 '\xbb\xac\x01L'
'\x06'
 '\xee\xefwH'
 '\xd9\x90\x08\tOVER SHE '
'\x04'
 '\xd2qG'
 '\xb5|\x0cTAB OVER TAB'
'\x1b'
 '63'
 '\xfe\xa1w6'
 '\xd6\xed\x01B'
 '\xb3|R'
'\x13'
 '%\x07 TIMES '
'\x10'
 '\xd2\xa1wA'
 '\xee\xdd\x01B'
 '\xde=G'
 '\x86\xe9}N'
 '\xfe\xc3\x08S'
 '\xea\xfawT'
 '\xef\x9b\x08U'
'\x05'
 '\x0b '
'\x02'
 '\xd9T\x03PLU'
'5'
 '\xbe\x01G'
 '\x8a\x7fL'
 'nN'
 '\x8b\xa0wR'
'\x02'
 '\xbb\xd7{G'
'\x05'
 '!\x06 LAGAB'
'\x02'
 '%\x07 TIMES '
'\x02'
 '\x0bA'
'\x02'
 '\x0bS'
'\x02'
 '\x93\x89yH'
'+'
 '\x0b '
'('
 '\xa6bG'
 '\xf2 N'
 '\xfc\x9ay\x06OVER S'
 '\xd9\xe2\x06\x06TIMES '
'"'
 '\x82\x9ewA'
 '\x94\xe4\x08\x02DU'
 '\xf6\xb0wH'
 '\xee\xce\x08K'
 '\xba\xa4wL'
 '\xba)M'
 '\xc2\x1bN'
 '\xae\x96\x08S'
 '\xa6\\T'
 '\xa7#U'
'\n'
 '\xe6\x9cw2'
 '\x02B'
 '\x02M'
 '\x02R'
 '\x9f\x14S'
'\x04'
 '\x9e\xacwA'
 '\xc3\x90\x04H'
'\x04'
 '\xfe\x9bwA'
 '\x83\tU'
'\x05'
 '\xeb\x9bwB'
'\x02'
 '\xed\xf7x\x04UTIL'
'\x08'
 'FA'
 '\xee\x9bwI'
 '\x03U'
'*'
 '\x96\x03A'
 '\xdexE'
 '\xb7\x04I'
'!'
 '\xc6\x01 '
 '\xe1~\x03RIG'
'\x0b'
 '\x0b '
'\x08'
 '\xbc]\x0cOPPOSING PIR'
 '\xa5#\x06TIMES '
'\x06'
 '\xca\xe8wK'
 '\xa6\xbc\x7fU'
 '\xeb\tZ'
'\x14'
 '\xd8\xd8{\x08CROSSING'
 '\x81\xa8\x04\x06TIMES '
'\x12'
 '\xd6|A'
 '\xc2\xddyB'
 '\xae\xbe}E'
 '\x96\xe4\x08I'
 '\xd3pU'
'\t'
 '\xf6\x97wD'
 '\x02N'
 '\x03P'
'x'
 '\xce\rA'
 '\xa2\x7fE'
 '\xe2zI'
 '\xe7xU'
'3'
 '\xb6\x81y1'
 '\xef\xfe\x06N'
'/'
 '\xaa\x03 '
 '\xf9|\x02UZ'
'\x1b'
 '\x0b '
'\x18'
 '\x8c\x01\nAB2 TIMES '
 'm\x0fKISIM5 TIMES BI'
'\x05'
 '\xf7\xe1w '
'\x14'
 '\x94U\x02AS'
 '\x8a\xf2wB'
 '\xde\xa8\x08D'
 '\xc2\x87yG'
 '\x8a\x8a\x07I'
 'l\x02KA'
 '\x96\xa9wL'
 '\xc6oN'
 '\xf8\xb8\x04\x03SIL'
 '\xc3\xac}U'
'\x02'
 '\xb7\xecwD'
'\x02'
 '\x0bG'
'\x02'
 '\x0bI'
'\x02'
 '\x8bW '
'\x12'
 '\x80\x03\x0cCROSSING NUN'
 '\xc0~\x0cLAGAR TIMES '
 'NO'
 '\x93HT'
'\x02'
 '\x15\x03VER'
'\x02'
 '\xc9\xdfw\x02 N'
'\n'
 '\xf2\x9awG'
 '\x82\xce\x01M'
 '\xdc\x97\x07\x03SAL'
 '\xb3\xe8xU'
'\x05'
 '\xb5\xe0w\x17 OVER NUN LAGAR TIMES S'
'\x05'
 '\x8d\\\x0e LAGAR OVER LA'
'+'
 '\xd0\xf4z\x06 TIMES'
 '\xb2\x9b|2'
 '\xd2\xf4\x08M'
 '\xa4|\x04NDA2'
 '\xb3\x8eyS'
'\x1d'
 '%\x07 TIMES '
'\x1a'
 '\x8e\x03A'
 '\xd6\xedxG'
 '\xe0\x91\x07\x02ME'
 'bN'
 '\x98\x7f\x03SHE'
 '\xab\x7fU'
'\x04'
 '\x1a2'
 '\x83\xa2wS'
'\x02'
 '\x0b '
'\x02'
 '\x19\x04PLUS'
'\x02'
 '\xa3\xe4x '
'\t'
 '%\x07 PLUS A'
'\x06'
 '\x8a\x9cw '
 '\x9b\xe4\x08S'
'\x04'
 '\x0bH'
'\x05'
 '\xf7~ '
'\x04'
 '\xbe\x8cwE'
 '\xbf\nU'
'\x02'
 '\x19\x04 PLU'
'\x02'
 '\x15\x03S G'
'\x02'
 '\xa9K\x02AN'
'\x06'
 '\xd2\x8bwN'
 '\xa7\xf3\x08S'
'\x07'
 '-\t TIMES GA'
'\x04'
 '\xbeJN'
 '\xa34R'
'\t'
 '\x0b '
'\x06'
 '\xbeMS'
 '\xf52\x06TIMES '
'\x04'
 '\xa2\x8awA'
 '\xa3\x0bU'
'\x15'
 '\x82\x8aw2'
 '\xd8\xf6\x08\x02GA'
 '[M'
'\x07'
 '\xf4m\x02 N'
 '\xdb\x9bw2'
'\x0b'
 '\x1a '
 '\x8f\x89wR'
'\x06'
 '\xf4\x85x\x06INVERT'
 '\x98\xfb\x07\x08OPPOSING'
 '\xb5\xbd\x7f\tTIMES SHU'
'\x02'
 '\xfd\xb0w\x03 NA'
'<'
 '\xfe\x04A'
 '\xd2\xa8{E'
 '\x9a\x91|I'
 '\xdb\xc1\x08U'
'%'
 '\xf8\xc8{\x05 OVER'
 '\xc2\x81\x04G'
 '\xe4\x9bz\x02NS'
 '\xb4\xe2\x01\x02RG'
 '\xad\xb8\x04\x02SH'
'\x19'
 '\x9e\x01 '
 '\xff~3'
'\x0b'
 '\x0b '
'\x08'
 '\xaaIG'
 '\x897\x06TIMES '
'\x06'
 '\x1aA'
 '\x8b\xb7wD'
'\x05'
 '\x81\xca{\x05 PLUS'
'\x0c'
 '\x88\x02\nCROSSING M'
 '\xac\x7f\tOVER MUSH'
 'Q\x06TIMES '
'\x06'
 '\xf2\x83wA'
 '\xb2\xc3\x00K'
 '\xdbQZ'
'\x05'
 ')\x08 TIMES A'
'\x02'
 '\x95\xc8{\x05 PLUS'
'\x02'
 '\xe3\xd9xU'
'\x11'
 '\xce\x00 '
 '\x8e\x82w2'
 '\x02H'
 '\x02R'
 '\xe7\xfd\x08S'
'\x04'
 '\xffVH'
'\x04'
 '\xc2EG'
 '\xdf\nT'
'\xd2\x01'
 '\xde\x08A'
 'FI'
 '\x83xU'
'K'
 '\xbeI '
 '\xfe82'
 '\x8e\xffv3'
 '\xe8\xff\x08\x03GAL'
 '\x9a\x80wH'
 '\x02L'
 '\xab\xff\x08M'
'\x07'
 '-\t OVER LUM'
'\x05'
 '\xbbK '
'\t'
 '\x0b '
'\x06'
 '\x16O'
 '\xdfBS'
'\x04'
 '8\x07PPOSING'
 '\x01\x03VER'
'\x02'
 '\x15\x03 LU'
'\x02'
 '\x9b\xcewG'
'3'
 '\x0b '
'0'
 '\x88\x05\x04CROS'
 '\x00\x04OPPO'
 '^S'
 '\xe7{T'
'('
 '\xb6\x93yE'
 '\x81\xed\x06\x05IMES '
'&'
 '\xea\x8dwA'
 '\xfe\xcd\x01B'
 '\xdc\xa7\x07\x03ESH'
 '\xcenG'
 '\xe4S\x03HI '
 '\xc2\xc0wI'
 '\xca\xfc\x08K'
 'd\x02LA'
 'FM'
 '\xce\xd1|N'
 '\xe0\xad\x03\x02SI'
 '\x97MT'
'\x04'
 '\xd2n '
 '\xe5\x11\x07K2 PLUS'
'\x02'
 '\x99\xc8w\x02 B'
'\x02'
 '\x0bE'
'\x02'
 '\x0b '
'\x02'
 '\xc9\xf6z\x04PLUS'
'\x04'
 '\xc2m '
 '\xcfMG'
'\x08'
 ' \x02AD'
 '\xdf\xfavI'
'\x06'
 '\xda\xfav2'
 '\xb3\xf3\x083'
'\x04'
 '\x0b2'
'\x05'
 '\xef\xaf\x7f '
'\x04'
 '\x8a\xbd\x7fH'
 '\x9f\xb2yQ'
'\x02'
 '\xa9\xbb{\x06SING L'
'\t'
 '\xc6\xf9vL'
 '\xb8\xc1\x04\x02MM'
 '\xe7\xd2{S'
'\x81\x01'
 '\xdc\x01\x02GA'
 '\xceNH'
 '\xee0L'
 '\xa7\x7fM'
'\x07'
 '1\n TIMES KUR'
'\x05'
 '\xe1\xb9{\x05 PLUS'
'\x05'
 '\x0b '
'\x02'
 '\x19\x04TIME'
'\x02'
 '\xc1\xc6w\x03S L'
'r'
 '\x92\x02B'
 '\x8b~R'
'\x0b'
 '\x0b '
'\x08'
 '\xfc\x00\x04GUNU'
 'M\tTIMES SHE'
'\x05'
 '\x0b '
'\x02'
 '\xf1\xffz\x05PLUS '
'\x05'
 '\xcd\x00\x10 OVER LAGAR GUNU'
'\x02'
 '\xed\x80z\x02 S'
'i'
 '\x0b '
'f'
 '\x8a\xeaxS'
 '\xb1\x96\x07\x06TIMES '
'd'
 '\xb2\tA'
 'bB'
 '\xa2\xf4vD'
 '\xd6\x01E'
 '\xce\x89\tG'
 'BH'
 '\xa2\x7fI'
 '\xfe~K'
 'NL'
 'VM'
 '\xca\xf3vN'
 '\xae\x8a\tS'
 '\x82\x7fT'
 '\xeb~U'
'\r'
 '\xcc\x00\x06 PLUS '
 '\xeed2'
 '\xe6\x8dwD'
 '\x9f\x14S'
'\x04'
 '\xce\xf2vA'
 '\xd7\x8d\tU'
'\x02'
 '\xc9\xd9z\x04 PLU'
'\x06'
 '\xda\x00A'
 '\x95n\x10E PLUS A PLUS SU'
'\x04'
 '\xaa\xf1vG'
 '\xf7\xea\x01K'
'\x0c'
 '\x1aH'
 '\xa7\xf9vU'
'\n'
 '\xc0z\x02E '
 '\xcc\x06\x0eITA PLUS GISH '
 ']\x02U2'
'\x05'
 '\xf1E\x05 PLUS'
'\x04'
 '0\x06PLUS E'
 '\xfb\xa4\x7fT'
'\x02'
 '\x0bR'
'\x02'
 '\x0bI'
'\x02'
 '\x93\xd9xN'
'\x06'
 '\x1aE'
 '\xd7\xc5xU'
'\x05'
 '\x9fs '
'\x08'
 '\xb6\xae\x7fA'
 '\x8e\x97yI'
 '\x93\xbb\x7fU'
'\n'
 '\xa6\xa5wI'
 '\xff\xda\x08U'
'\x06'
 '\xf6\xedv3'
 '\xaf\x92\tL'
'\x05'
 ')\x08 PLUS HI'
'\x02'
 '\xcfL '
'\x08'
 '\xaaYG'
 '\xf3&M'
'\x07'
 '!\x06 PLUS '
'\x04'
 '\xde\x81wH'
 '\xa37L'
'\x06'
 '\xba\xfewA'
 '\xd5\xdb\x07\x07I TIMES'
'\x08'
 '\xd2\xd1wA'
 '\xd9\xae\x08\x02UD'
'\x05'
 '\xb7\xa9\x7f '
'\x04'
 '\xd6\xf6vA'
 '\xe3tI'
'\x0f'
 '\xf8\x00\x06 PLUS '
 '\x9e\xeavL'
 '\x02N'
 '\xc9\x95\t\x04SH Z'
'\x02'
 '\xe1\x9f\x7f\x02ID'
'\x06'
 '*D'
 '\xda\xf2vG'
 '\x97\xc6\x00L'
'\x02'
 '\xa9\xd2y\x06A PLUS'
'\xc0\x01'
 '\xca\x05A'
 '\xdaDE'
 '\xa29I'
 '\x9e}U'
 'm\x04WU31'
'\x02'
 '\xf3\xe8v8'
'\x19'
 '\x8cI\x1e OVER HI TIMES ASH2 KU OVER HI'
 '\xd2\x9fw3'
 '\xd2\x99\t4'
 '\xb2\xe6v7'
 '\xa2\xc3\x08L'
 '\xe2\xbcwN'
 '\x9a\x99\tR'
 '\xb3\xaf\x7fS'
'\x05'
 '\xd5\x9d\x7f\t OPPOSING'
'\x05'
 '\xad\x90y\x08 VARIANT'
'\x15'
 '\xcc\x01\x07 TIMES '
 '\xae\xe4vD'
 '\x02N'
 '\xdb\x9a\tS'
'\x08'
 '\x96\xf5vA'
 '\x92pH'
 '\x95\x9b\t\x03IM5'
'\x05'
 '\xb9\xd0x\x0b OVER KISIM'
'\x06'
 '\x96\xc2xB'
 '\x8f\xbe\x07U'
'\x05'
 '\x87\xe4vD'
'\x91\x01'
 '\xa0\x05\x07 TIMES '
 'B2'
 '\x8e\xdfvB'
 '\x8a\xa0\tD'
 'RK'
 '\xae\x7fL'
 'fM'
 '\xb5~\x04SKAL'
'\x07'
 '\x0b '
'\x04'
 '\xca\x00L'
 '\x01\rOVER KASKAL L'
'\x02'
 '\xdd\x9d\x7f\x18AGAB TIMES U OVER LAGAB '
'\x04'
 '\x96\xe1v2'
 '\x034'
'\x07'
 '\x0b '
'\x04'
 '\xd8\xc2x\tCROSSING '
 '\x9b\xe6\x06T'
'\x05'
 '\xadL\x08 TIMES I'
'\n'
 '\xf6\xdfv2'
 '\x023'
 '\x024'
 '\xbf\xa0\t5'
'\x05'
 '\x91\xcbx\t OVER KAD'
'\x05'
 '\xbd\x96{\x0b CROSSING K'
'j'
 '\xc2\x08A'
 '\xb2\x7fB'
 'fE'
 '\xb6}G'
 'bI'
 '^K'
 '\xda\x9byL'
 '\x86\xe3\x06M'
 '\xeaNN'
 '\xa6\xbewP'
 '\xc6\x1aR'
 '\xb6\xd7\x08S'
 '\x8e\xe5vT'
 '\x96\x9a\tU'
 '\xeb\x8ewZ'
'\x0b'
 '\x82\xddv2'
 '\x02D'
 '\xfc\xc5\x01\tMUM TIMES'
 '\xa3\xce~S'
'\x10'
 '\xfe\xc1wA'
 '\xca\xbe\x08H'
 '\x92\xebvI'
 '\xfd3\x02UH'
'\x08'
 '\xda\xdbvA'
 '\x02E'
 '\xa2\x0bI'
 '\xe3tU'
'\x0c'
 '\xd2\x00E'
 'GI'
'\x05'
 '\x99\xc3w\n PLUS NUNU'
'\t'
 '!\x06 PLUS '
'\x06'
 '\xd6\xa6wD'
 '\xbeeG'
 '\xebRT'
'\x06'
 '\xf6\xd9vA'
 '\x87\x9c\tI'
'\x04'
 '\xc2\x8bwG'
 '\x9fNM'
'\x16'
 '\xde\x01A'
 '\xda~I'
 'oU'
'\x05'
 '\xd7\xb0wR'
'\t'
 '\x8a\xc3xR'
 '\xa5\xbd\x07\x03SH '
'\x04'
 '2C'
 '\x8d\xe1v\x06PLUS S'
'\x02'
 '%\x07ROSSING'
'\x02'
 '\xc1\xf3x\x02 G'
'\x0b'
 '\xde\xd7vL'
 '\xc2\xbf\x08N'
 '\x97\xe9\x00R'
'\x05'
 '\x81j\n PLUS SHA3'
'\x04'
 '\xd6gR'
 '\x8fPS'
'\x08'
 '\x1aA'
 '\xbf\xd6vI'
'\x06'
 '\xba\xd6vD'
 '\xa6\xff\x01L'
 '\xdf\x80~R'
'\t'
 '\x1aD'
 '\xdf\xb6\x7fS'
'\x05'
 '\x95\xaew\x08 PLUS KU'
'1'
 '\xbe\xeav '
 '\xfajB'
 '\xfc\xae\t\x03DIM'
 '\xa6~G'
 'FL'
 '\xe6~M'
 '\xba\xd4vN'
 '\x02R'
 '\x9f\x14S'
'\r'
 '\x1a '
 '\xdb\xdevI'
'\x08'
 '\xd4\x00\x04CROS'
 '\x00\x04OPPO'
 '\xca\xc8xS'
 '\x93\xd9\x06T'
'\x02'
 '\x9d\xefx\x05SING '
'\x07'
 '\x1a '
 '\x83\xd3v2'
'\x02'
 '\xf9F\x04TIME'
'\r'
 '\x0bI'
'\x0b'
 '\x0b '
'\x08'
 '\xe6\xd2xD'
 '\x9a\xc3\x06G'
 '\xc8\x9ey OVER IGI SHIR OVER SHIR UD OVER '
 '\xe7\xcf~R'
'\x07'
 '5\x0b OVER IDIM '
'\x04'
 '\xfa\x93wB'
 '\xd7\xb1\x01S'
','
 '\xea\x02A'
 '\xde~I'
 '\xe3~U'
'\x11'
 ' \x02B2'
 '\xe3\xb9xL'
'\r'
 '%\x07 TIMES '
'\n'
 '\xee\xd9vA'
 '\xc2\xc4\x00H'
 '\xf2\xe9\x07K'
 '\xde\xe2yL'
 '\xdb\xef}U'
'\x15'
 '%\x07 TIMES '
'\x12'
 '\x98L\x02AS'
 '\x8a\xe0xB'
 '\xde=D'
 '\xa6BG'
 '\xd2\xee~K'
 '\xea\x00N'
 '\x9e\xbe\x02S'
 '\xc3\xf4|U'
'\t'
 '\x1a '
 '\xa3\xcdvL'
'\x04'
 '\xd6\x90\x7fG'
 '\x9brT'
'\xe8\x01'
 '\xae\nA'
 'l\x06ESHTIN'
 '\xeazI'
 '\xc7{U'
"'"
 '\xcc\xe6}\n CROSSING '
 '\xc2\x9c\x022'
 '\xea~D'
 '\xbe\xcavL'
 '\x96\xb5\tM'
 '\xbf\x7fR'
'\t'
 '\xae\xcbv7'
 '\xf7\xb4\tU'
'\x04'
 '\x8a\xcbvN'
 '\x9f\x14S'
'\x05'
 '\x0b '
'\x02'
 '\xadU\x05TIMES'
'\t'
 '\x0b '
'\x06'
 '\xf4J\x08OVER GUD'
 '\xdd5\x06TIMES '
'\x04'
 '\xbc\x80\x7f\x05A PLU'
 '\xcf\x8cxK'
'\r'
 '\x0b '
'\n'
 '\xce\x8c\x7fG'
 '\xed\xf3\x00\x06TIMES '
'\x08'
 '\xb0h\x03KAK'
 '\xce\xadwN'
 '\xc5\x83\x08\nSAL PLUS T'
'-'
 '\xba\x04 '
 '\x8e\x7f4'
 '\x8e\xe0xD'
 '\x9e\x9e\x07R'
 '\xdb~S'
'\x0c'
 '\x9e\xd7vA'
 '\x87\xa9\tH'
'\x0b'
 '\x0b '
'\x08'
 '\xdanC'
 '\xc3\x11T'
'\x06'
 '\xe6\xdbxE'
 '\xd1\xa4\x07\x05IMES '
'\x04'
 '\x96\xa4xB'
 '\xbf\xdc\x06T'
'\x10'
 '\xa6\x89\x7f2'
 '\xff\xf6\x003'
'\r'
 '%\x07 TIMES '
'\n'
 '\xce\x00A'
 '\x82\xb9\x7fG'
 '\xaa\xc7\x00I'
 'X\x02LU'
 '\xf7\xd9vP'
'\x02'
 '%\x07 PLUS I'
'\x02'
 '\xa7\xf6vG'
'\x07'
 '\x0b '
'\x04'
 '\xc4\x00\x08CROSSING'
 '\x01\x04OVER'
'\x02'
 '\xcd\xaex\x03 GI'
'\x06'
 '\xf4~\tCROSSING '
 '\xb9\x9a|\x06TIMES '
'\x05'
 '\xa7\xf9~ '
'\x93\x01'
 '\xf2\x85\x7f '
 '\x9e\xfd\x002'
 '\xbc\x7f\x02BA'
 'nD'
 '^L'
 '\xb6\xc0vM'
 '\xc2\xbe\tN'
 '\xca\x81\x7fR'
 '\xcb\xf0yS'
'\x0b'
 '\x0b2'
'\t'
 '\x0b '
'\x06'
 '\xd4\x00\x08CROSSING'
 '\x00\x04OVER'
 '\xa3\xf6~T'
'\x02'
 '\xbdQ\x03 GA'
'\x07'
 '\xfa\x8e\x7f '
 '\xf3\xb9wA'
'\x05'
 '\xfb\x8e\x7f '
'\x05'
 '\x8d\xe9y\x0c CROSSING GA'
'o'
 '\x0b '
'l'
 '\xa0\x9f\x7f\x05OVER '
 '\xad\xe1\x00\x06TIMES '
'j'
 '\xa2\nA'
 '\x86\x7fB'
 '\xb6\x7fD'
 'VE'
 '\x86\x7fG'
 '\x92~H'
 '\xba\x7fI'
 '\xe6~K'
 '\x86\xd0vL'
 '\xda\xaf\tM'
 '`\x03NUN'
 '\xca\xd0vP'
 '\xa6\xae\tS'
 '\xfe\xf6~T'
 '\xd3\x88\x01U'
'\x07'
 '\x0bD'
'\x05'
 '\xe1\xf8z\x05 PLUS'
'\x0c'
 '\xf6\x00A'
 '\xb6\x7fH'
 '\xe3\xc4vU'
'\x06'
 '\x1aE'
 '\xaf\xc7vI'
'\x05'
 '\xb9\xffv\x07 PLUS T'
'\x04'
 '\xda\xbbvL'
 '\x03R'
'\x05'
 '\x0b '
'\x02'
 '\xf3\xa8\x7fO'
'\x04'
 '\xd2\xbf\x7fE'
 '\xcf\xfbvI'
'\n'
 '\xf6\x00A'
 '`\x02ID'
 'm\x07U3 PLUS'
'\x02'
 '\xc3\xc9v '
'\x05'
 '\xd9B\x04 PLU'
'\x04'
 '\x82\xbavK'
 '\xef\xe1\x01S'
'\x04'
 '\xf2\xa5\x7fG'
 '\x89\x06\nSH PLUS HU'
'\n'
 '\xd2\x00A'
 '\xcc\xc9}\x07I PLUS '
 '\xfd\xd8z\x02UB'
'\x06'
 '\xf0\x00\x0c PLUS LU PLU'
 'WL'
'\x05'
 '\xd1\x86w\x06 PLUS '
'\x02'
 '\x11\x02S '
'\x02'
 '\x9f\x98\x7fE'
'\x0c'
 '\xd6\x00A'
 'CI'
'\t'
 '\xaa\x96\x7f4'
 '\xf5\xdb{\x07R2 PLUS'
'\x04'
 '\x8e\xf6~N'
 '\xc3\xc0wR'
'\x08'
 '\xae~L'
 '\xef\x01N'
'\x05'
 '\x8fc '
'\x08'
 '\xfe\xb5vA'
 '\xb6\xca\tI'
 '\xdf\xa1xU'
'\x05'
 '\xe9j\x02M '
'\x08'
 '\xce\x00A'
 'Q\x02UR'
'\x05'
 '\x0b '
'\x02'
 '\xa5\x98y\x04PLUS'
'\x04'
 '\xe2\xb4vD'
 '\xf9\xca\t\x02R '
'\x0e'
 '\xc4\x01\x06 PLUS '
 '\xe4\xf2~\x0eB2 TENU PLUS T'
 '\x8e\xc0wN'
 '\xe1\xcc\t\x02SH'
'\x05'
 '\xfd\xb3\x7f\x072 PLUS '
'\x06'
 '\xfeHD'
 '\xfa\xfevH'
 '\xb7\xa6\tI'
'W'
 '\x82\x08 '
 '\xc6~2'
 '\xb6\xf8vD'
 '\xb8\xbc\x7f\x02GI'
 '\x8ewL'
 '\xba\xd2\tN'
 '^R'
 '\xde\x8e\x7fS'
 '\xe5\xed\x00\x03ZEN'
')'
 '%\x07 TIMES '
'&'
 '\xce\x02A'
 '\xa2\x8cxB'
 '\xc0\xf3\x07\x05DUN3 '
 '\xf4\xf1~\x02HA'
 '\xea(I'
 '\xda\xe4\x00K'
 'BL'
 'gU'
'\x04'
 '\xfa\xafv2'
 '\x03D'
'\x08'
 '"A'
 '\xbe\xafvI'
 '\x03U'
'\x05'
 '\xd5\xb7\x7f\x02L '
'\x06'
 ',\x05ASKAL'
 '\x9f\x87wU'
'\x05'
 '\xf1\xa3x\x02 S'
'\x04'
 '\xad\xf6~\x03GUN'
'\t'
 '\xc0\xb6\x7f\t PLUS LAL'
 '\xf3\xf7vN'
'\x04'
 '\xa6\xb8vE'
 '\xb7\x86\tI'
'\x0f'
 '\x0b '
'\x0c'
 '\x9c\x01\x04CROS'
 '\x00\x04OPPO'
 '\xa2\xa1xS'
 '\xb1\xde\x07\x06TIMES '
'\x06'
 '\x90\xb2\x7f\x03GAN'
 '\x87\xffvM'
'\x02'
 '\xa5\xa7z\x04SING'
'\x0f'
 '%\x07 TIMES '
'\x0c'
 '\x80\xf1~\tA PLUS HA'
 '\xb6\xc3wG'
 '\xfe(M'
 '\xc2\xa3\tS'
 '\xdf\xaavU'
'\x04'
 '\xca\xbavA'
 '\xdftH'
'\x04'
 '\x84o\x0bOVER E NUN '
 '\xd1\x11\x04TIME'
'\x02'
 '\x0bS'
'\x02'
 '\xd9\xafz\x02 P'
'j'
 '\xda\x03A'
 '\xd6~I'
 '\xfb}U'
'!'
 '\xc2\x01 '
 'NB'
 'nG'
 '\x9a\xa8vH'
 '\xbe\xd7\tN'
 '\xcb\x92xR'
'\x0b'
 '\x1a3'
 '\xab\xa8v4'
'\x07'
 '\xd3y '
'\x05'
 '\xb7\xb3vU'
'\x07'
 '\xb0p\x05 TIME'
 '\xd3\xb7v2'
'\x06'
 '\x86\xeb~G'
 '\xb0\xf8{\x04OVER'
 '\x83\x87\x04S'
'\x11'
 '\x8a\xa7vB'
 '\x82\xda\tM'
 '\xb6\x7fN'
 '\xeb\xbavS'
'\x05'
 '\xed\xf8~\x0e KASKAL U GUNU'
'\x07'
 '\x9e[ '
 '\xe3\xcav2'
';'
 '\xc2\x00G'
 '\x9e\xa5vM'
 '\xd3\xda\tR'
'\x07'
 '\x8f\xd8zA'
'1'
 '\xc5\x00\x0e KISIM5 TIMES '
'.'
 '\xde\x04A'
 'RB'
 '\x92\x7fG'
 '\x9e\xb6vH'
 '\xb8\xc9\t\x02IR'
 '\xca\xc7vK'
 '\xd6\xb7\tL'
 '\xf2\xa6vN'
 '\xd0\xd1\t\x07PAP PLU'
 '\xca\xdbvS'
 '\xc6\x88\x08T'
 '\xdf\xa2\x01U'
'\x04'
 '\xc0\x00\t2 PLUS GI'
 '\xd7\xb6vS'
'\x02'
 '\xbb\x8cxR'
'\x08'
 '\xa2\xa2vA'
 '\x83\xde\tU'
'\x07'
 '\xd4\x82\x7f\x07 PLUS M'
 '\xab\x9fwM'
'\x05'
 '\xd5\xfdw\x06 PLUS '
'\n'
 '6A'
 'nI'
 '\x93\xacvU'
'\x05'
 '\xf3\x8axR'
'\x05'
 '\x0b '
'\x02'
 '\xb5\xf7w\x06PLUS M'
'\x04'
 '\x1aA'
 '\x8b\xa0vI'
'\x02'
 '\xab\x9fxL'
'\x04'
 '\xa2\x7f '
 '\xbb\xa9vM'
'*'
 '\xee\x02A'
 '\xaa\x7fI'
 '\x93~U'
'\x11'
 '\xe6\x00 '
 'L\x03LUG'
 '\xdf\xf3~R'
'\x05'
 '\xed\xf9~\x08 OVER BU'
'\x06'
 '\xcc\xa2\x7f\x08CROSSING'
 '\x95\xde\x00\x08OVER BU '
'\x04'
 '\xee\x89xA'
 '\xaf\x9e~U'
'\t'
 '%\x07 TIMES '
'\x06'
 '\x92\x9dvA'
 '\xea\x08G'
 '\xa3\xe3\x08I'
'\x13'
 '\xe2\x9cvD'
 '\xae\xd8\x00G'
 '\x86\x8c\tH'
 'FL'
 'oR'
'\x05'
 '\xa3\x86xA'
'\x07'
 '\x84\xebv\x07 OVER B'
 '\xbb@A'
'\x02'
 '\x97yA'
'\x81\x01'
 '\x90\x0e\x07 TIMES '
 '\xaa\x8dv2'
 '\x86\xef\tB'
 '\xfe\x90vD'
 '\x96\xee\tK'
 '\x96~L'
 '\xecH\x03MAR'
 '\x925N'
 '\x9a\xe2vP'
 '\xc2\x9d\tR'
 '\x93|S'
'\x12'
 '\xf4\x83x\x02AL'
 '\xb7\xfc\x07H'
'\x11'
 '* '
 '\x9e\x99v2'
 '\xf7\xbf\x08G'
'\n'
 '\xb2\xce~K'
 '\xa4\xb2\x01\tOVER ASH '
 '\x8f\xae\x7fZ'
'\x06'
 '\xac\x01\x08OVER ASH'
 '\xbdm\x1dTUG2 OVER TUG2 TUG2 OVER TUG2'
'\x05'
 '\xf1\x00\x19 CROSSING ASH OVER ASH OV'
'\x02'
 '\xe1\x88\x7f\x02ER'
'\x06'
 '\xa0S\x02AD'
 '\xd7\x82\x7fK'
'\r'
 '\x1a '
 '\x83\xa1yS'
'\x08'
 '\x84[\x04OVER'
 '\xfc%\nPLUS NAGA '
 '\xed\xf7w\x08THREE TI'
'\x04'
 '\xbc\x8c\x7f\x10OPPOSING AN PLUS'
 '\x83\xfdxS'
'\x17'
 '\xc8\x00\x07 TIMES '
 '\xca\x9dvA'
 '\xc7\xc5\x01E'
'\x10'
 '\xfa\xa2vA'
 '\x94\xda\x01\x03DIM'
 '\xc61G'
 '\xc2\xf9}H'
 '\xea\xd8\tK'
 '\xd2\x9dyS'
 '\xb7\xcb~U'
'\x04'
 '\x82\xfe~A'
 '\x8f\x94wI'
'\x07'
 '%\x07 TIMES '
'\x04'
 '\x9a\xa2\x7fE'
 '\xad\x17\nSHITA PLUS'
'%'
 '\x8e\x01 '
 '\x8f\x7f2'
'\r'
 '%\x07 TIMES '
'\n'
 '\xacp\x02BA'
 '\x9e\x94\x7fG'
 '\x96\x10M'
 '\xfa@S'
 '\x8buT'
'\x16'
 '\xa2\xd3~G'
 '\x99\xad\x01\x06TIMES '
'\x14'
 '\x92\xf0~A'
 '\xbc\x0b\x04DUN3'
 '\x94\x86\x01\x02GA'
 '\xd6\xa2vH'
 '\x8a\xdd\tI'
 '\xce\xd3~L'
 '\xf8\xd2y\x02SH'
 '\x81\xf5\x06\x08U PLUS U'
'\x04'
 '\x82\xfa~G'
 '\xab\xe0wM'
'\x04'
 '\xca\x8dvL'
 '\xc3\xbf\x08N'
'\x10'
 '\xa6\x8dvA'
 '\xee\xdd\x01B'
 '\xaa\x96\x07G'
 '\xf6\xa0wH'
 '\xb6\xa6\tI'
 '\xe4\xb0\x7f\x05LAGAR'
 '\xf2\x10M'
 '\x97\x82yS'
'\x08'
 '\xa8\x01\tDIAGONAL '
 '\xd0\xd3v\x0eOLD ASSYRIAN W'
 '\x81\x0b\tVERTICAL '
'\x04'
 '\xda\xdevC'
 'i\x02TR'
'\xc6\x01'
 '\x90\x13\x06EIGHT '
 '\xbe|F'
 '\xd0}\x02NI'
 '\xae}O'
 '\xc2{S'
 '\xe3zT'
'2'
 '\x98\x03\x05HREE '
 '\xa1}\x03WO '
'\x16'
 '\xc2\x02A'
 '^B'
 'l\x02ES'
 'jG'
 'FS'
 '\xa5\x7f\x06THIRDS'
'\x04'
 '\x0b '
'\x04'
 '\xf6\xa3xD'
 '\xd1t\x0cVARIANT FORM'
'\x04'
 '\x0bH'
'\x04'
 '\x11\x02AR'
'\x04'
 '\xbe\x87v2'
 '\x03U'
'\x04'
 'a\x03ESH'
'\x02'
 '\xb3\xf0wH'
'\x04'
 '\xe6\x97\x7fA'
 '\xaf\xfcxU'
'\x04'
 '\xa5\x8c\x7f\x02SH'
'\x1c'
 'bA'
 '\xf6\x01B'
 '\xaa\xa0xD'
 '\x96\xdd\x07G'
 '\xa8\x02\x04SHAR'
 'a\x10VARIANT FORM ESH'
'\x04'
 '\xee\xf2w1'
 '\xc7|2'
'\x08'
 '\xca\x9e\x7f2'
 '\x03U'
'\x06'
 '\xce\x95\x7fA'
 '\xe1\x08\x03URU'
'"'
 '\xe0\x02\x05EVEN '
 '\\\x14HAR2 TIMES GAL PLUS '
 '\xd5~\x03IX '
'\x0e'
 '\xca|A'
 '\x9e\xa2xD'
 '\xfe\xac\x07G'
 '\xba5S'
 '\x86\x82vU'
 '\xd1\xd7\x00\x10VARIANT FORM ASH'
'\x02'
 '\xb3fH'
'\x04'
 '\xba\x9dxD'
 '\xf7\xb0~M'
'\x10'
 '\xc2\xd8wA'
 '\xd6\xc4\x00D'
 '\xfe\xac\x07G'
 '\xba5S'
 '\x86\x82vU'
 '\xd5\xff\t\x11VARIANT FORM IMIN'
'\x06'
 '\x1a '
 '\x93\x80v3'
'\x04'
 '\x8e\x80vA'
 '\x03B'
'\x18'
 '\xa0\x02\x10LD ASSYRIAN ONE '
 '\xc5~\x03NE '
'\x14'
 '\x92xB'
 '\xf2\x08E'
 '\xe6vG'
 '\x84q\x05QUART'
 '\xb0\xa3x\x02SH'
 '\xb5\xea\x07\x05THIRD'
'\x04'
 '\xc8\xf0~\x05IGHTH'
 '\xb3\x86\x01S'
'\x04'
 '\xde\xa1xQ'
 '\x81\xf0}\x03SIX'
'\x16'
 '\x88\x02\x04GIDA'
 '\xad~\x03NE '
'\x12'
 '\xda\xd3wA'
 '\xd6\xc4\x00D'
 '\xfe\xac\x07G'
 '\xba5S'
 '\x86\x82vU'
 '\xc5\x84\n\x13VARIANT FORM ILIMMU'
'\t'
 '\xc2\x90v '
 '\xfaj3'
 '\x034'
'\x04'
 '\x86\xd2wE'
 '\xcb\xf5~M'
'6'
 '\xb4\x02\x04IVE '
 '\x85~\x04OUR '
'\x1e'
 '\xdesA'
 '\xee\rB'
 '\xb2\x94xD'
 '\x96\xdd\x07G'
 'FS'
 '\xe2\x87vU'
 '\xf9\x86\n\x12VARIANT FORM LIMMU'
'\t'
 '\xf6x '
 '\x93\x80v4'
'\x06'
 '\xb4\x92\x7f\x03AN2'
 '\xcf\xf3xU'
'\x18'
 '\xe2qA'
 '\xee\rB'
 '\xb2\x94xD'
 '\x96\xdd\x07G'
 '\xc6\x0fS'
 '\xe3\xf7uU'
'\x06'
 '\x8apH'
 '\xf9\xd9~\x05IXTHS'
'\x0e'
 '\x9e\xcewA'
 '\xd6\xc4\x00D'
 '\xfe\xac\x07G'
 '\xba5S'
 '\x86\x82vU'
 '\x89\xc0\x08\x11VARIANT FORM USSU'
'\x06'
 '\xc8\x00\x03ED '
 '[I'
'\x02'
 '\xe1\xd5{\x05NG LA'
'\x04'
 '\xb4\xe1{%NEGATIVE SQUARED LATIN CAPITAL LETTER'
 '\xa9\xa7z\x03SWO'
'\x96\x04'
 '\xac\xc0v\x02FF'
 '\x80\xd4\t\x08MBINING '
 '\xc4m\x05PTIC '
 '\xb1\x7f\x0bUNTING ROD '
'$'
 '0\x04TENS'
 '\x01\x04UNIT'
'\x12'
 '\xf5\x96x\x02 D'
'\xf2\x01'
 '\xda\x10C'
 '\x9a\x7fF'
 '\x88\xabv\rMORPHOLOGICAL'
 '\xe8\xd3\t\x0bOLD NUBIAN '
 '\xc7rS'
'v'
 '\x98\x02\x03MAL'
 '\xa5~\x06YMBOL '
'\x0e'
 '\xb6\x01K'
 'nM'
 '\x02P'
 '\xa6\x7fS'
 '\xe1\xb4z\x03TAU'
'\x04'
 '\xc4\x00\x06HIMA S'
 '\xb5\xacx\x04TAUR'
'\x02'
 '\x8b\xb3vI'
'\x02'
 '\x83\xb4zI'
'\x04'
 '\xbe\xa0vA'
 '\xaf\xdf\tH'
'h'
 '-\tL LETTER '
'h'
 '\xaa\nA'
 '\xcc~\x02CR'
 '\xd2~D'
 '\x8e\xf4{E'
 '\x9a\xa4zF'
 '\xde\xb8\x03G'
 '\x96\x98~H'
 '\xf2\xdb\x03I'
 '\xd6\xba\x04K'
 '\xba\x7fL'
 '\x96\x99vM'
 '\x02N'
 '\xba\xe3\tO'
 '\xc2\xdc|P'
 '\xa2\xc1yR'
 '\xf2\xe1\tS'
 'RT'
 '\xce\x80vU'
 '\xd88\x02VI'
 '\xcb\xc6\tZ'
'\x02'
 '\xd3\x80vA'
'\x04'
 '\xea\xb7vA'
 '\x99\xbf\x02\x03HET'
'\x06'
 '\x8a\xd9|A'
 '\x92\xd6yI'
 '\xa3\x08O'
'#'
 '$\x03LD '
 '\xe7\xb6vO'
'\x1e'
 '\x9c\x01\x07COPTIC '
 '\xb5\x7f\x07NUBIAN '
'\x08'
 '.N'
 '\xb4z\x02SH'
 '\x97\x83xW'
'\x04'
 '\x9a\x9bvG'
 '\x03Y'
'\x16'
 '\xd6\xb5vA'
 '\xf2\xee\x03D'
 '\xca\x9b}E'
 '\xba\xc1\x08G'
 'NH'
 '\xea\xf1yO'
 '\xf9\x8d\x06\x02SH'
'\x04'
 '\x8a\x9avE'
 '\xa7\x12I'
'\x08'
 '\x9e\x8ewA'
 '\xce\x8b\x7fE'
 '\xdf\x89\x04O'
'\x02'
 '\xd9\xfcu\x04ANGI'
'\x04'
 '\xe8\xcfx\x07-SHAPED'
 '\x9d\xe6}\x02AU'
'\x06'
 '\xfa\xb3vA'
 '\xd2dH'
 '\x03S'
'\n'
 '\x9c\xb4v\x02AL'
 '\xb1\xcc\t\tIALECT-P '
'\x08'
 '\xca\x00A'
 '\xe4\xa0z\x02HO'
 '\xd4\x91|\x02KA'
 '\xd3dN'
'\x02'
 '\xe3\xf7wL'
'\n'
 '\x8c\xf1y\x07OSSED S'
 '\xe1\x8f\x06\x0cYPTOGRAMMIC '
'\x08'
 '\xea\xf1{E'
 '\xe2\x8a\x04G'
 '\xba\x99vN'
 '\x9f\xda\x03S'
'\x04'
 '\xcc\xefy\x08KHMIMIC '
 '\xcf\xdf~L'
'\x08'
 '\xde\x00D'
 '\xe6\xa2vF'
 '\x9c\xdd\t\x03IND'
 '\xb9\xabv\x05VERSE'
'\x02'
 '\xc1\xa2v\x07IRECT Q'
'\x04'
 '\xc8\x00\x0bRACTION ONE'
 '\xf7\xa1vU'
'\x02'
 '\xf5\x85x\x02 H'
'n'
 '\xe4r\x05APITA'
 '\xed\r\tOMBINING '
'\x06'
 '\x90\xbfv\x02NI'
 '\xbd\xc1\t\tSPIRITUS '
'\x04'
 '\xe0\xfdu\x03ASP'
 '\xf5\xdf\x07\x02LE'
'\xfe\x01'
 '\xd6\x1dA'
 'l\x06BREVE-'
 '\xb2wC'
 '\xf6{D'
 '\x80c\x04FERM'
 '\xb0\x1b\x02GR'
 '\x96\xf0uI'
 '\xe6\x88\nL'
 '\xf4~\x06MACRON'
 '\x84\xb7v\x06OGONEK'
 '\xac\xc5\t\x05RIGHT'
 '\xba\x7fS'
 'fU'
 '\xea\xfcuX'
 '\x99?\x06ZIGZAG'
'\x04'
 '\xb6\xbbvR'
 '\x03S'
'\x04'
 '\xdc\xeez\x03NAK'
 '\xa9\xedz\x06USPENS'
'\x0e'
 '\x8e\x01 '
 '\x8f\x7fW'
'\x02'
 '\xb5\x8bx\x18ARDS HARPOON WITH BARB D'
'\x0c'
 '\xd0\x00\x05ARROW'
 '[H'
'\x02'
 '\xfd\xb8v\x05ALF R'
'\n'
 '\xaa\xfau '
 '\x8d\x86\n\x05HEAD '
'\x08'
 '\x1aA'
 '\xe7\xf9uB'
'\x06'
 '\xbe\xb8vB'
 '\xf1\xc7\t\x03ND '
'\x04'
 '(\x04DOWN'
 '\x01\x02UP'
'\x02'
 '\xed\xf8u\n ARROWHEAD'
'\n'
 '\xca\x00 '
 'O-'
'\x06'
 '\xfa\xddzA'
 '\xf6\xfd~B'
 '\x8f\x83\x01G'
'\x04'
 ',\x03LEF'
 '\x01\x04RIGH'
'\x02'
 '\x83vT'
'6'
 '\x84\x02\x05ATIN '
 '\x8c\x7f\x03EFT'
 '\xcd\xf1z\x12ONG DOUBLE SOLIDUS'
'\n'
 '\x16 '
 '\x97zW'
'\x08'
 '(\x05ARROW'
 '\x8b{H'
'\x06'
 '\xda\xf5u '
 '\x8d?\x04HEAD'
'*'
 '\xc8\x04\x15LETTER SMALL CAPITAL '
 '\xd9|\rSMALL LETTER '
' '
 '\x82\x03A'
 '\xf4\xbe{\x06C CEDI'
 '\x9e\xa6zE'
 '\xdc\x9a\n\x0fFLATTENED OPEN '
 '\x96\xd1uG'
 '\xa0\x0b\x08INSULAR '
 '\xe2tK'
 '\xce\xae\nL'
 '\xb6\xd1uN'
 '\xa8\xae\n\x02R '
 '\xda\xd1uS'
 '\x03Z'
'\x04'
 '\xe6\xf1uB'
 '\xf7\xf2\x04R'
'\x05'
 '\xfd\xa7v\x03ONG'
'\x02'
 '\xdb\xafvA'
'\x06'
 '\xfe\xd0uE'
 '\x02O'
 '\x03V'
'\n'
 '\xda\xd0uG'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x03R'
'\n'
 '\x94\x01\x04AVE-'
 'A\x0cEEK MUSICAL '
'\x06'
 '\xa2\xd2yP'
 '\x83\xae\x06T'
'\x04'
 '\xde\xd1yE'
 '[R'
'\x04'
 '\xa0\xf5z\x06ACUTE-'
 '\xb7\x05M'
'6'
 '\xe8\x02\nEVANAGARI '
 '\xdb}O'
'\x12'
 '\xd6\x01T'
 '\xd9~\x05UBLE '
'\x0c'
 '\x90\x01\x05BREVE'
 '\x98\xabv\nCIRCUMFLEX'
 '\xe8\xd4\t\x06MACRON'
 '\xf7\xaa{R'
'\x05'
 '\xd3\xecu '
'\x06'
 '\x88\x90v\x08 ABOVE R'
 '\xcd\xad\x03\x03TED'
'$'
 '\xea\x8cvD'
 '\xe4\xf3\t\x07LETTER '
 '\xd7\xe2yS'
'\x0e'
 '\x9a\xcbuA'
 '\x8a\x15K'
 '\x02N'
 '\x02P'
 '\x02R'
 '\xfajU'
 '\xe71V'
'P'
 '\xcc\x08\nONJOINING '
 '\x95x\x08YRILLIC '
'N'
 '\xc4\x01\x06HUNDRE'
 '\xe6\xf2}K'
 '\x8c\x8e\x02\x07LETTER '
 'NP'
 '\x8e\x7fT'
 '\x89\xa5x\x02VZ'
'\x04'
 '\xc0\x00\x02EN'
 'u\x06HOUSAN'
'\x02'
 '\x0bD'
'\x02'
 '\xb1\xf0w\x07 MILLIO'
'\x04'
 '\x9a\xf1}A'
 '\x89\xe4}\x04OKRY'
'@'
 '\xae\xc7uA'
 '\xe2\xbd\nB'
 '\xe2\xcdxC'
 '\xfe\xb1\x07D'
 '\xb2\x7fE'
 '\xee\xe1uF'
 '\xea\xec\x02G'
 '\xca\x89}H'
 '\xfe\xa6\nI'
 '\x86\xd9uK'
 '\xea\x8e\x08L'
 '\x84~\x05MONOG'
 '\x8e\xdewO'
 '\xce\x04P'
 '\x98\xb7\n\x02SH'
 'bT'
 '\x8a\xc9uV'
 '\xda\xb6\nY'
 'cZ'
'\x04'
 '\xfa\xc4uE'
 '\xcf\x04H'
'\x04'
 '\xf6\xc5uA'
 '\xe7~U'
'\x04'
 '\xba\xc4uE'
 '\xcf\x04S'
'\x04'
 '\x9a\xc4uA'
 '\x87!C'
'\x06'
 '\xfa\xc3uE'
 '\xc9\xbc\n\x08OTIFIED '
'\x04'
 '\xb6\xc3uA'
 '\xf3\x90\x07B'
'\x0c'
 '\x92\xc3uL'
 '\x02M'
 '\x02N'
 '\x02R'
 '\xab\xbd\nS'
'\x05'
 '\xb7\xc5w-'
'\x04'
 '\xc2\xc2uE'
 '\xef\xa7\x08J'
'\x04'
 '\x9e\xc2uE'
 '\xff\x90\x07I'
'\x02'
 '\xc3\xedzM'
'\n'
 '\x90\x01\x05CUTE-'
 '\xcc\xe0u\x0eLMOST EQUAL TO'
 '\x99?\x07STERISK'
'\x04'
 '\xa8\xc6z\x07GRAVE-A'
 '\xf3%M'
'\xa2\x02'
 '\x94\x05\x1aCOMPATIBILITY IDEOGRAPH-FA'
 '\x89|\x07STROKE '
'H'
 '\xa4\xceu\x02BX'
 '\xcepD'
 '\xc6\xc3\nH'
 '\xbe\xbcuN'
 '\xa2\xc3\nP'
 '\xe2\xbcuQ'
 '\xaa\xc2\nS'
 '\xe6\xf4uT'
 '\xaaXW'
 '\x03X'
'\x15'
 '\xd6\xbduG'
 '\x02P'
 '\x02T'
 '\x86\xc3\nW'
 'cZ'
'\x07'
 '\xce\xccuW'
 '\xcfpZ'
'\x07'
 '\xfa\xbcuG'
 '\x03Z'
'\t'
 '\xde\xbcuD'
 '\x02G'
 '\x03Z'
'\x1d'
 '\xba\xbcuG'
 '\xf2\xc4\nP'
 '\xc4\xcau\x02XW'
 '\xdf\xb4\nZ'
'\x13'
 '\xee\xbbuG'
 '\x02T'
 '\x82\xc5\x02W'
 '\xcf\xff\x07Z'
'\t'
 '\xb2\xbbuP'
 '\x83\xc5\x02Z'
'\x05'
 '\xc3\xcauW'
'\xda\x01'
 '\xde\x016'
 '\xf6~7'
 '\x028'
 '\x029'
 '\x02A'
 '\x02B'
 '\x02C'
 '\xcf\xe6uD'
' '
 '\xa2\xbau0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x029'
 '\x02A'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x03F'
'\x06'
 '\x96\xb9uB'
 '\x02C'
 '\x03D'
'('
 '\xf6\x06C'
 '\xa8\x99y\x0cHANGUL IEUNG'
 '\x8a\xe4\x06I'
 '\xbc\x7f\x11KOREAN CHARACTER '
 '\x84~\x07NUMBER '
 '\x9b\x9fvW'
'\x10'
 '\x8c\x01\x04EIGH'
 '\xce\x00F'
 '^S'
 '\x8b\x7fT'
'\x06'
 '\x94\xe6}\x02EN'
 '\xd4\x9a\x02\x02HI'
 'SW'
'\x02'
 '\x11\x02EN'
'\x02'
 '\xc5\xe5}\x02TY'
'\x02'
 'cR'
'\x04'
 '@\x02EV'
 '\x15\x02IX'
'\x04'
 '\xb0\x7f\x02IF'
 '\x1fO'
'\x04'
 '\xd4\xecy\x04CHAM'
 '\x9d\xfa{\x04JUEU'
'\x0c'
 '\xc0\x01\tDEOGRAPH '
 'e\x1bTALIC LATIN CAPITAL LETTER '
'\x04'
 '\xa2\xb3uC'
 '\x03R'
'\x08'
 '\xc6\x00K'
 '\xcc\xb7v\x03QUE'
 '\xdd\xc9\x03\x03SCH'
'\x04'
 '\xb4\xaf|\x08INDERGAR'
 '\xcb\xb5{O'
'\x04'
 '\xfa\xb1uD'
 '\x9d\x8a\n\x05ROSSI'
'\xac\x01'
 '*A'
 '\xf2\xdczI'
 '\xb3\xd4|U'
'\xa8\x01'
 '\xc4\xc4u\x02IN'
 '\xed\xbb\n\x02M '
'\xa6\x01'
 '\xb0\t\x0fCONSONANT SIGN '
 '\xa6\xe8uD'
 '\xdc\x91\n\x07LETTER '
 '\x94\x7f\x0cPUNCTUATION '
 '\xb5\x7f\x0bVOWEL SIGN '
'\x14'
 '\x9e\xc9vA'
 '\xa2\x97\x7fE'
 '\xce\xe8\x00I'
 '\xa2\x9c\x7fO'
 '\x03U'
'\x08'
 '\xce\x00D'
 '\xbc\xfcu\x04SPIR'
 '\xd9\xbd\x01\x04TRIP'
'\x04'
 '\xba\xbawA'
 'CO'
'h'
 '\xd2\xc7vA'
 '\x86\xbe\tB'
 '\xac\xe7v\x02CH'
 '\xae\x98\tD'
 '\xf6\xa7uE'
 '\x94\xd7\n\x06FINAL '
 '\xce\xe8vG'
 '\xaa\xd5~H'
 '\xfajI'
 '\xe2\xbf\x01J'
 '\x02K'
 '\xaa\xd5~L'
 '\xee\xc1\nM'
 '\x9a\x7fN'
 '\xf6\xa9uO'
 '\xe6\xd5\nP'
 '\xa6\xbfuR'
 '\xbe\xc0\nS'
 '\x9e\xeavT'
 '\xa2\xc0~U'
 '\x8a\x15V'
 '\x03Y'
'\x04'
 '\xba\xaauA'
 '\x8b\x15S'
'\x06'
 '\x9a\xaauA'
 '\x8a\x15H'
 '\x03P'
'\x0e'
 '\xf2\xa9uA'
 '\xf6\xd6\nG'
 'VH'
 '\x87\xaeuU'
'\x06'
 '\xb6\xa9uA'
 '\x8a\x15J'
 '\xc7oU'
'\x04'
 '\x8a\xa9uA'
 '\xcf\x04U'
'\x16'
 '\x86\xbduC'
 '\xe6kG'
 '\x02K'
 '\x02L'
 '\x82\xc5\x02N'
 '\x82\xbb}P'
 '\x02R'
 '\xba\x13S'
 '\xcalT'
 '\x03Y'
'\x06'
 '\xf2\xa7uA'
 '\x8a\x15D'
 '\x03H'
'\x06'
 '\xca\xa7uA'
 '\x8a\x15B'
 '\x03H'
'\x0e'
 '\xcc\x00\x06FINAL '
 '\xde\xbbuL'
 '\x02R'
 '\x02W'
 '\x03Y'
'\x06'
 '\xd2\xa6uH'
 '\x02M'
 '\xb7\x0fN'
'\x04'
 '\xb2\x86|D'
 '\xe7\xa7zR'
'\x86\x02'
 '\xf0\x05\x11NADIAN SYLLABICS '
 '\x86{R'
 '\x9d\xadu\x02ST'
'd'
 '\xb8\xc6{\x04 SLI'
 '\xa5\xba\x04\x0bIAN LETTER '
'b'
 '\x8e\xf9}A'
 '\x9e\xabwB'
 '\xcc\xdf\n\x02C-'
 '\x9a\xf5}D'
 '\x02E'
 '\x02G'
 '\xce\xc5xI'
 '\xb6\xba\x07K'
 '\xd6\x8a\x02L'
 'RM'
 '^N'
 '\x9e\xa1uO'
 '\xe6\xd4\x08P'
 '\x9e\xabwQ'
 '\xde\xe5\x00R'
 '\xd6\xf8\tS'
 'nT'
 'FU'
 '\xa3\xa2uX'
'\r'
 '\x0bU'
'\x0b'
 '\x0bU'
'\t'
 '\x86\xa2u2'
 '\x023'
 '\x03U'
'\x07'
 '\xc7\xf6}T'
'\r'
 '\xb2\xf6}H'
 '\x9e\xabwS'
 '\xe7\xd4\x08T'
'\t'
 '\x9a\xa1uD'
 '\x02G'
 '\x03N'
'\x0b'
 '\x0bB'
'\t'
 '\xea\xa0u2'
 '\x023'
 '\x034'
'\x07'
 '\xab\xf5}D'
'\x04'
 '\xbe\xb7~1'
 '\xc7\xc0w3'
'\xa0\x01'
 '\xf6\rA'
 '\x92\x7fB'
 '\xf0~\x08CARRIER '
 '\xecx\x05EASTE'
 '\xc0\x06\x06FINAL '
 '\xfe\x95}H'
 '\xe2\xe9\x02K'
 '\xc6\x96wL'
 '\x02M'
 '\x92\xe9\x08N'
 '\xb6~O'
 '\xfa}P'
 '\xfa\x00R'
 '\xda~S'
 '\xde~T'
 '\x96}W'
 'gY'
'\x04'
 '\xce\x80vA'
 '\x03O'
'\x18'
 '\xb2\x80vA'
 '\xbc\x81\n\x03EST'
 '\xf5~\nOODS-CREE '
'\x10'
 '\xf4\xb0u\x06FINAL '
 '\xd1\xcf\n\x03THW'
'\x0e'
 '\xd2\xc6vA'
 '\x9a\xda~E'
 '\xe6\x95\x01I'
 '\xd3\x9b\x7fO'
'\x06'
 '\xd8\x00\x07-CREE L'
 '[E'
'\x02'
 '\x11\x02RN'
'\x02'
 '\xc3\xbbu '
'\x04'
 '\x86\xb0uA'
 '\xf7\x1dO'
'\x10'
 '\xc6\xfduA'
 '\xec\xef\x02\x02HW'
 '\xc6\x93\x07L'
 'U\x02TH'
'\x06'
 '\x9a\xafuA'
 '\xf6\x1dO'
 '\xd3QW'
'\x04'
 '\x0bH'
'\x04'
 '\xd6\xccuO'
 '\xd3QW'
'\x12'
 '\xd4\x00\x02AY'
 'ZH'
 '\xf7\xfbuO'
'\x06'
 '\xf2\xfbuA'
 '\x02O'
 '\xd3\x1cW'
'\x0b'
 '\x19\x04ISI '
'\x08'
 '\xa6\xd3uH'
 '\x9e\xfd\x00J'
 '\x9f\xae\tS'
'\x10'
 '\xd0\xcdy\x07-CREE R'
 '\xaa\xad|A'
 '\xd7\x85\nW'
'\x0c'
 '\xc2\x97uA'
 '\xce\x04E'
 '\xe6\x95\x01I'
 '\xd3\x9b\x7fO'
'\x1a'
 '4\x07JIBWAY '
 '\xcf\x96uY'
'\x18'
 '\xca\x96uC'
 '\x02K'
 '\x02M'
 '\x9a\xea\nN'
 '\xea\x95uP'
 '\xfe\xe5\x00S'
 '\x87\x9a\x7fT'
'\x0b'
 '\x0bW'
'\x08'
 '\x8a\xb0vI'
 '\xd3\x9b\x7fO'
'\x0c'
 '\x9e\xf8uA'
 '\x02O'
 '\xbf\x87\nW'
'\x04'
 '\xf2\xf7uA'
 '\xd3\x9e\x01W'
'\x04'
 '\xe0\x95u\x06RAISED'
 '\xa9\xfd\x00\x06SMALL '
'\x0c'
 '\xd4\x00\x03DEN'
 '^G'
 '\x87\xe4xJ'
'\x06'
 '\xe6\xa8uA'
 '\x9f\xfd\x02W'
'\x04'
 '\xe4\xd5u\x03E G'
 '\xa1\x14\x03TAL'
'\x06'
 '\xa4\xd7~\x0bEAVER DENE '
 '\xc9\xa0\x01\x08LACKFOOT'
'\x04'
 '\xfa\xf4uA'
 '\x9b\x9d\x7fY'
'\xa2\x04'
 '\xfa\rA'
 '\x9c~\x02EN'
 '\xe8{\x05LACK '
 '\x92\x7fO'
 '\xbc{\x08UGINESE '
 '\x85\xebu0YZANTINE MUSICAL SYMBOL FTHORA SKLIRON CHROMA VA'
'<'
 '\xe4\xbf|\x07END OF '
 '\x8c\xc2\x03\x07LETTER '
 'l\x04PALL'
 'I\x0bVOWEL SIGN '
'\n'
 '\xc2\x92uA'
 '\xb6{E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x02'
 '\xe3\xddxA'
'.'
 '\xaa\x8duA'
 '\x8a\x15B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\x02H'
 '\x02J'
 '\x02K'
 '\x02L'
 '\xfe\xdf\nM'
 '\xfe~N'
 '\x8a\xa1uP'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x02V'
 '\x03Y'
'\x0c'
 '\xfe\x8buA'
 '\xe6\xf4\nG'
 '\xa6\xa0uR'
 '\xbf\xdf\nY'
'\x04'
 '\xba\x8buA'
 '\x8b\x15C'
'\x04'
 '\x9a\x8buA'
 '\x8b\x15K'
'\x04'
 '\xfa\x8auA'
 '\x8b\x15P'
'\x0c'
 '\xf4\x9eu\x0fPOMOFO LETTER I'
 '\xf9\xc4\x00\x04TTOM'
','
 '\x80\xe3w\rCROSS ON SHIE'
 '\xb8\xb5}\x02DR'
 '\xaa\xd1\tF'
 '\xae\xacvH'
 '\xb6\xed\nL'
 '\x8a\x7fM'
 '\xa6\x91uP'
 '\xb6\x7fR'
 '\xea\xee\nS'
 'VT'
 '\xc3\x8buV'
'\x04'
 '\xd8\x88v\x02RU'
 '\xe3\x84\x7fW'
'\x08'
 '\xa8\x92u\x04MALL'
 '\xed\x91\x02\x03NOW'
'\x06'
 '\xd4\x00\x06EDIUM '
 '\xd9\x9au\x08OON LILI'
'\x04'
 '\xbe\x91uD'
 '\x8f~L'
'\x06'
 ',\x05ARGE '
 '\xd7\x91uE'
'\x04'
 '\x9e\x89vC'
 '\xfb\x80\x7fS'
'\x08'
 '\xe8\x00\x05GALI '
 '\xf9\x91y\x0eZENE RING WITH'
'\x06'
 '\xb0\x84u\x05GANDA'
 '\xb0\xbb\x04\rLETTER KHANDA'
 '\xbf\\S'
'\xa4\x03'
 '\xfc\x0f\x07LINESE '
 '\xe0p\x04MUM '
 '\xb5\xfav\x02SE'
'\xb0\x01'
 '\xd0\r\x02CO'
 '\xe2\xb5uF'
 '\xe4\xbd\n\x07LETTER '
 '\xf8\x92|\x05NJAEM'
 '\x86\xafyQ'
 '\x8f\x8a\x02S'
'\xa0\x01'
 '\xea\x81uA'
 '\xce\x04E'
 '\xba\x85\x0bF'
 '\xfe\xf5tI'
 '\xba\x88\x0bK'
 '\xa6\x7fL'
 '\xf2~M'
 '\xd2}N'
 '\xe6\xfbtO'
 '\x96\x83\x0bP'
 '\xfa~R'
 '\xea~S'
 '\xb2\x7fT'
 '\xde\xfftU'
 '\xf6\xd6\nW'
 '\x87)Y'
'\x06'
 '\x86\x80uA'
 '\xbe\x95\x02O'
 '\x03U'
'\n'
 '\xae\xd2xA'
 '\x86\xae\x07E'
 '\xab\xfftI'
'\x04'
 '\xa6\xfftN'
 '\x03T'
'\x10'
 '\x9c\xa8x\x02AM'
 '\xe6\xd8\x07E'
 'RH'
 '\xba\xfetI'
 '\xab\xcc\x00U'
'\x08'
 '.E'
 '\xee\xafuI'
 '\x9eNO'
 '\x03U'
'\x02'
 '\xd7\xc0uU'
'\x0e'
 '\xbe\x82uA'
 '\x9e\xfe\nE'
 'bI'
 '\xbb\xfdtU'
'\x04'
 '\x82\x82uE'
 '\xb7{I'
'\x06'
 '\x96\xfdtE'
 '\x02N'
 '\xd3\xc2\x00U'
'\x0c'
 '\xea\xfctA'
 '\xfa\x83\x0bE'
 '\x8a\xfctI'
 '\xdb\x83\x0bU'
'\x04'
 '\xf2\x80uA'
 '\xb7{E'
'\x04'
 '\x86\xfctE'
 '\xd3\xc2\x00U'
'\x1e'
 '\xe2\xfbtA'
 '\xf6\xb3\x01D'
 '\xa2\xd2\tG'
 '\xee\xf9tI'
 '\xe2\x85\x0bJ'
 '\xa6\x9buS'
 '\xba\xe4\nT'
 'nU'
 '\xbf\xacuY'
'\x05'
 '\xa3\xfftA'
'\x04'
 '\x8e\xfftE'
 '\xdf\xc7\x00U'
'\x06'
 '\xd6\xc7uA'
 '\x96\xb7\x7fE'
 '\xd3\x92\x07U'
'\x06'
 '\xea\xf9tA'
 '\x8a\x15G'
 '\xe9-\x03KWA'
'\x13'
 '\xb2\xf9tA'
 '\xbe\x87\x0bB'
 '^E'
 '\xea\xf8tI'
 '\x02O'
 '\x03U'
'\x04'
 '\x92\xbbuE'
 '\xd7\xbd\x7fN'
'\x04'
 '\xca\x8duA'
 '\xb7uE'
'\n'
 '\xa2\xf8tA'
 '\xac\xc2\x00\x02EE'
 '\xd6\xbd\x7fI'
 '\xbe\x95\x02O'
 '\xc7\xea}U'
'\x16'
 '\xc6\xf7tA'
 '\xda\x89\x0bE'
 '\xaa\xf6tI'
 '\xaa\x89\x0bO'
 '\xe2\x8buP'
 '\xfajU'
 '\xaf\xc2\x00Y'
'\x07'
 '\x8c\xfft\x03GHO'
 '\xc7\xaf\x01V'
'\x06'
 '\xa6\xf6tN'
 '\x02T'
 '\xd3\xc2\x00U'
'\x08'
 '\x94\x8d|\x03AAM'
 '\xb2\xedxE'
 '\xee\x03O'
 '\xcbwU'
'\x08'
 '\xe2\xfftL'
 '\xc3\x80\x0bM'
'\x06'
 '\xcc\x00\x0cBINING MARK '
 '\xcb\x89uM'
'\x04'
 '\xec\xfet\x05KOQND'
 '\xc1\xd1\x00\x07TUKWENT'
'\xf2\x01'
 '\x84\xf5z\x05ADEG '
 '\xf4\xa2\x05\x06CARIK '
 '\xee\x9cuD'
 '\x84\xda\n\x07LETTER '
 '\x98y\x0fMUSICAL SYMBOL '
 '\xbc\x7f\x02PA'
 '\xa4~\x05SIGN '
 '\xec|\x0bVOWEL SIGN '
 '\xcf\xdbwW'
'\x1e'
 '\xf0\x02\x03LA '
 '\xbc\x7f\x05PEPET'
 '4\x03RA '
 '`\x04SUKU'
 '\xe6~T'
 'a\x03ULU'
'\x05'
 '\xcd\xaby\x03 SA'
'\n'
 '8\x05ALING'
 'oE'
'\x02'
 '\xff\xcbvD'
'\t'
 '\x0b '
'\x06'
 '\x1eR'
 'wT'
'\x02'
 'KE'
'\x04'
 '\x11\x02EP'
'\x04'
 '\x0bA'
'\x05'
 'Q\x02 T'
'\x05'
 '\xed\xfcu\x03 IL'
'\x04'
 '\xab\x7fR'
'\x04'
 '\xad\x7f\x04LENG'
'\x0c'
 '\xc4\x01\x03BIS'
 '\xe2\xc9vC'
 '\xe8\xb1~\x05REREK'
 '\xa6\x84\x0bS'
 'E\x04ULU '
'\x04'
 '\xf0\x8du\x04CAND'
 '\xd1,\x03RIC'
'\x02'
 '\xdb\xcdwU'
'\x02'
 '\xd7\x80uA'
'\x06'
 '\x1aM'
 '\xeb\xabyN'
'\x04'
 '\xea\xb9uA'
 '\xadd\x02EN'
'8'
 '\xe4\x04\nCOMBINING '
 '\xca~D'
 '\x88\x7f\nLEFT-HAND '
 '\xf9~\x0bRIGHT-HAND '
'\x08'
 '\xe8\x00\x08CLOSED T'
 'e\x06OPEN D'
'\x04'
 '\x96\xf9tA'
 '\x03U'
'\x04'
 '\xba\xe9tA'
 '\x03U'
'\n'
 '`\tCLOSED PL'
 '\xf1\x00\x06OPEN P'
'\x06'
 '\xfe\xf7tA'
 '\x02I'
 '\x03U'
'\x14'
 '\xd2\x00A'
 'fE'
 '\xa6\xf7tI'
 '\x02O'
 '\x03U'
'\x04'
 '\xae\xf7tN'
 'wU'
'\n'
 '\x86\xf7tE'
 '\x02I'
 '\xad\x89\x0b\x02NG'
'\x07'
 '\x0b '
'\x04'
 '\xba\xf2{G'
 '\x97\x88\x04S'
'\x12'
 '\xd8\xfdt\x03BEN'
 '\xa4\xe6\x01\x03END'
 '\x9a\xb5~G'
 '\xca\xe8\nJ'
 '\xb4\x7f\x04KEMP'
 '\x85\xc4v\x03TEG'
'\x08'
 ' \x02LI'
 '\x01\x02UL'
'\x05'
 '%\x07 WITH J'
'\x02'
 '\xb1\xe2z\x03EGO'
'l'
 '\xc6\x08A'
 '\\\x02BA'
 '\\\x02CA'
 '\x8c\x7f\x02DA'
 'bE'
 'd\x02GA'
 '\xb6\xf3tH'
 '\xfe\x88\x0bI'
 '\xb0\x03\x02JA'
 '\xba\x7fK'
 'p\x02LA'
 '\xae\xf4tM'
 '\x8e\x8b\x0bN'
 '\xf2}O'
 '\xec\x01\x02PA'
 'p\x02RA'
 'L\x02SA'
 '\xfe~T'
 '^U'
 'd\x02VE'
 '\xa2\xf7tW'
 '\x02Y'
 '\xe1\x88\x0b\x03ZAL'
'\x02'
 '\xa1\xeaz\x02 S'
'\x04'
 '\x0bK'
'\x04'
 '\xf9r\x02AR'
'\n'
 '"A'
 '\x9d\x7f\x03ZIR'
'\t'
 '\x0b '
'\x06'
 '\xd4\xdbz\x03LAT'
 '\xa8\n\x06MURDA '
 '\xeb\xed\x04T'
'\x07'
 '\x15\x03 SA'
'\x04'
 '\xc2\xf5tG'
 '\x03P'
'\x07'
 '\xebq '
'\x05'
 '\x89\xafu\x04 KAP'
'\x08'
 '"A'
 '\xd2\xf4tG'
 '\x03Y'
'\x05'
 '\xb5\xfbv\x04 RAM'
'\x07'
 '\xffp '
'\x08'
 '"A'
 '\xd9|\x03HOT'
'\x07'
 '\xc6\xe3z '
 '\x93\x99\x05F'
'\x05'
 '\xb1\xfft\x03 JE'
'\x05'
 '\xcd\xa5u\x02 G'
'\x04'
 '\xf6{F'
 '\xf7\x82uK'
'\t'
 '\x11\x02 M'
'\x06'
 '\xa2\xc8wA'
 '\x95\xb8\x08\x05URDA '
'\x04'
 '\x9c\xe2z\x03ALP'
 'kM'
'\x05'
 '\x81\xf2t\x04 LAC'
'\x05'
 '\xb5\xeaz\x04 KEM'
'\x08'
 '\x8c\xfdt\x02IK'
 '\xb6\xfd\nK'
 'Y\x05SYURA'
'\x06'
 '(\x02PA'
 '\xf5\x94y\x02SI'
'\x04'
 '\x80o\x05MUNGK'
 '\xad\xafu\x03RER'
'\xa4\x03'
 '\xf4\xe0u\x06C CURR'
 '\xf0\xd5\n\x06EGEAN '
 '\x88\x84{\x03FGH'
 '\x80\xe0\x01\tKTIESELSK'
 '\xa2\x9b\x03L'
 '\xd4\xd6v\x03NCH'
 '\xd4\xfb\x08\x05RABIC'
 '\x88\xe2t\x03TOM'
 '\xb0\x9c\x02\x04USTR'
 '\xed\xfb\x08\x07VESTAN '
'n'
 '\x8a\xf5vA'
 '\xb5\x8b\t\x07LETTER '
'l'
 '\xe6\x04A'
 '\xfe\x8d\x7fB'
 '\xca\xc9uC'
 '\xba\xb6\nD'
 '\xce\xfbuE'
 '\xfeMF'
 '\x96\xa8\x0bG'
 'bH'
 '\xf2\xeduI'
 '\x9e\xea~J'
 '\x02K'
 '\x02L'
 '\x02M'
 '\xba\xa7\x0bN'
 '\xfe\x89uO'
 '\xceNP'
 '\x02R'
 '\x86\xa7\x0bS'
 'ZT'
 '\xf6\xeeuU'
 '\xb2\xea~V'
 '\xb6\xa6\x0bX'
 'bY'
 '\xa7\x90\x7fZ'
'\x04'
 '\x9e\xd5tE'
 '\xcf\x04Y'
'\x06'
 '\xfe\xd4tE'
 '\xce\x04V'
 '\x03Y'
'\x06'
 '\xd6\xd4tE'
 '\xce\x04H'
 '\x03T'
'\x08'
 '\xae\xd4tE'
 '\xe2\xaa\x0bH'
 '\xe3\xe0wS'
'\x0c'
 '\xfa\xd3tE'
 '\x82\xab\x0bG'
 '\xce\xd9tN'
 '\x03Y'
'\x04'
 '\xbe\xd3tE'
 '\xcf\x04M'
'\x06'
 '\x9e\xd3tE'
 '\xce\x04G'
 '\x03H'
'\x11'
 '\x92\x91uA'
 '\xb6xE'
 '\xb2IN'
 '\x03O'
'\xb4\x01'
 '\x92\x02 '
 '\xa5~\x07-INDIC '
'\x08'
 '\xb8\x01\x04CUBE'
 '\x00\x06FOURTH'
 '\xa1\x7f\x04PER '
'\x04'
 '\xf8\xe6x\x03MIL'
 '\xe5\xfb{\x0cTEN THOUSAND'
'\x02'
 '\xd9\xd1t\x03 RO'
'\xac\x01'
 '\x84\x9fw\x04DATE'
 '\xd6\x8b\tF'
 '\xd8`\x06INVERT'
 '&L'
 '\xc8\x90u\rMARK NOON GHU'
 '\xea\xd6\x00N'
 '\xbc\xc5\x05\nPOETIC VER'
 '\xba\xd2\x04R'
 '\xbayS'
 '\xd4\xea{\x0bTRIPLE DOT '
 '\xa0\x94\x04\x0bVOWEL SIGN '
 '\xb9\xcev\x06ZWARAK'
'\x06'
 '\xf4\xect\x03DOT'
 '\xe8\x93\x0b\nINVERTED S'
 '\x03S'
'\x02'
 '\xe5\xaau\x06MALL V'
'\x1e'
 '\x88\x03\x04IGN '
 '\xec}\x05MALL '
 '\xd9\xe5~\nUBSCRIPT A'
'\x0c'
 '\xba\xb5xD'
 '\xc2\xd5}F'
 '\xf0\xf5\t\x05HIGH '
 'm\x02KA'
'\x02'
 '\x8b\xebtS'
'\x06'
 '\xa8\xa8v\x1dLIGATURE ALEF WITH LAM WITH Y'
 '\xaa\xb5\tT'
 '\x87\xbbuZ'
'\x10'
 '\x84\x02\x07ALAYHE '
 '\xbc|\x02MI'
 '\xec\x03\x02RA'
 '\xe0~\x02SA'
 '\xe5\xbdy\x06TAKHAL'
'\x06'
 '\xda\xe8tF'
 '\x9c\x98\x0b\x12LLALLAHOU ALAYHE W'
 '\xa7ZN'
'\x02'
 '\xa5\xa6z\x05ASSAL'
'\x04'
 '\xa0\xb8w\rDI ALLAHOU AN'
 '\xd5\x19\x0eHMATULLAH ALAY'
'\x04'
 '\x92\xa8uA'
 '\xa5\xd8\n\x05EVERS'
'\x02'
 '\xb1\xafx\x04ED D'
'r'
 '\xc0\x01\x06ETTER '
 '\xc5\x90u#IGATURE BISMILLAH AR-RAHMAN AR-RAHE'
'p'
 '\x9e\x1bA'
 '\x84|\tBEH WITH '
 '\xe0}\tDAL WITH '
 '\xfe|F'
 '\xf6{H'
 '\xb2}K'
 '\xbc\xaax\x08LAM WITH'
 '\xa8\xec|\x0bMEEM WITH D'
 '\xc0\xe8\n\nNOON WITH '
 '\x94\x7f\tREH WITH '
 '\xdc{\nSEEN WITH '
 '\xac~\x03WAW'
 '\x01\nYEH BARREE'
'\x04'
 '\x99\x01# WITH EXTENDED ARABIC-INDIC DIGIT T'
'\x04'
 '\xd0\xday\x03HRE'
 '\x81\xc2{\x02WO'
'\n'
 '\xb4\x9cz\x1fEXTENDED ARABIC-INDIC DIGIT FOU'
 '\xe0\xde\x00\x04FOUR'
 '\xd2\x88\x05I'
 '\xe0~\x02SM'
 '\x9b\x7fT'
'\x02'
 '-\tWO DOTS V'
'\x02'
 '\x89\x9au\tERTICALLY'
'\x02'
 '\xed\x00\x18ALL ARABIC LETTER TAH AN'
'\x02'
 '\x0bD'
'\x02'
 '\xf1\xd1t\x04 TWO'
'\x02'
 '%\x07NVERTED'
'\x02'
 '\x9f\xa0v '
'\n'
 '\x98\xe8~\x04HAMZ'
 '\xaa\x97\x01I'
 '\x8a\x01S'
 '\xf3|T'
'\x04'
 '\xd6}M'
 '\xd3\xd3tT'
'\x06'
 '8\x06SMALL '
 '\xcd\xd7t\x02TW'
'\x04'
 '\xcaKT'
 '\xbf\xectV'
'\x0c'
 '\x84\xf5z\x07AF WITH'
 '\xe1\x8b\x05\nEHEH WITH '
'\n'
 '\x96\xe4wD'
 '\x8f\x9c\x08T'
'\x08'
 '\xc4\x00\nHREE DOTS '
 '\xcf\xf3zW'
'\x06'
 '\xf2\x94uA'
 '\xb2AB'
 '\x8f\xaa\x0bP'
'\x02'
 '\xcd\xd5t\x0eOINTING UPWARD'
'\x0e'
 '\xdc\x00\x08AH WITH '
 '\xcdz\tEH WITH I'
'\x0c'
 '\x88\x03\x1dEXTENDED ARABIC-INDIC DIGIT F'
 '@\x18SMALL ARABIC LETTER TAH '
 '\xaf\x7fT'
'\x04'
 '\x1aH'
 '\xdf\xefzW'
'\x02'
 '\xbd|\nREE DOTS P'
'\x06'
 '\x1aA'
 '\xe3\xd1tB'
'\x04'
 '\xba\x90uB'
 '\xfb\xe6\nN'
'\x02'
 '\xa1\xd1t\x03OUR'
'\x10'
 '\x90\x01\x0eARSI YEH WITH '
 'a\tEH WITH T'
'\x04'
 '\xf2}H'
 '\xeb\xd1tW'
'\x0c'
 '\xd0\x01\x1cEXTENDED ARABIC-INDIC DIGIT '
 '\xbatI'
 '\x8f\x0bT'
'\x04'
 '\x1aH'
 '\xff\xebzW'
'\x02'
 '\x85\xecz\x03REE'
'\x06'
 '\xf6|F'
 '\xa3sT'
'\x06'
 '\xd4\x01\tINVERTED '
 '\xf5\xbf\x7f%TWO DOTS VERTICALLY BELOW AND SMALL T'
'\x04'
 '\x1aS'
 '\x97\xactV'
'\x02'
 '\x89\xcct\x06MALL V'
'\x0e'
 '\xa0}\x10DOT BELOW AND TH'
 '\xb0\x02\nINVERTED S'
 '\xd0r\x05SMALL'
 '\x8f\x0fT'
'\x08'
 '\x88\x01\nHREE DOTS '
 '\xb1\xd6w\x11WO DOTS BELOW AND'
'\x06'
 '\xa0\xc9t\x0cHORIZONTALLY'
 '\x89\xb8\x0b\x16POINTING UPWARDS BELOW'
'\x05'
 '\x87\xe5z '
'\n'
 '\xc8\x00\tIN WITH T'
 '\xf9g\x03LEF'
'\x06'
 '\xfc\xe4z\x1bHREE DOTS POINTING DOWNWARD'
 '\xb1\x9c\x05\x08WO DOTS '
'\x04'
 '\xce\x84uA'
 '\xdf\xe5\nV'
'\x04'
 '\xb8k\tATHA WITH'
 '\xd5\xf4v\x07OOTNOTE'
'\x04'
 '\x80\xabt\x03EMB'
 '\xa5\x7f\x0bTERNATE ONE'
'r'
 '\xdc\xa3t\x05CHECK'
 '\xf0\xe4\x0b\x03DRY'
 '\x00\x06LIQUID'
 'd\x08MEASURE '
 '\x9c|\x07NUMBER '
 '\xf3|W'
'\x0e'
 '\x88\x01\x06EIGHT '
 ']\x0eORD SEPARATOR '
'\x04'
 '\xfa\xa2tD'
 '\x83\xc2\x00L'
'\n'
 '\xfc\x00\x05BASE '
 '>F'
 'bS'
 '\xa7\x7fT'
'\x02'
 '\x15\x03HIR'
'\x02'
 '\x0bD'
'\x02'
 '\x19\x04 SUB'
'\x02'
 '\xf1\xcdu\x02UN'
'\x02'
 '\xb9\x7f\x04ECON'
'\x04'
 '*I'
 '\xfd~\x05OURTH'
'\x02'
 '\xf9~\x03RST'
'Z'
 '\xbc\x03\x05EIGHT'
 '\xa6\x7fF'
 '\\\x04NINE'
 '\xbe\xaczO'
 '\x9a\xd3\x05S'
 '\xe3~T'
'\x18'
 '\xea\xb5zE'
 '\x8a\xcb\x05H'
 '\xbf\x7fW'
'\n'
 ' \x02EN'
 '\xcf\xadzO'
'\x04'
 '\x0bT'
'\x04'
 '\x97\xb5zY'
'\n'
 '\\\x02IR'
 '\xc1\xadz\x02RE'
'\x14'
 '(\x04EVEN'
 '\x01\x02IX'
'\x0b'
 '\x9e\xb5x '
 '\xf7\xc9\x07T'
'\x14'
 ':I'
 '[O'
'\n'
 '\xce~R'
 '\xcd\xadz\x02UR'
'\n'
 '\xa6~F'
 '\xc3\xadzV'
'\x0b'
 '\x9e\xb4x '
 '\x8f\xff\x01Y'
'\x04'
 '\xb2{S'
 '\xa7\x7fT'
'\x02'
 '\xe1{\x0b MEASURE FI'

)
# estimated 32.66 KiB
_pos_to_code = [
9190, 65794, 65852, 65853, 65854, 65855, 65806, 65824, 65833, 65815, 65842, 65812, 65839, 65803, 65821, 65830,
65811, 65838, 65802, 65820, 65829, 65807, 65825, 65834, 65816, 65843, 65799, 65817, 65826, 65805, 65823, 65832,
65814, 65841, 65804, 65822, 65831, 65813, 65840, 65808, 65835, 65810, 65837, 65801, 65819, 65828, 65809, 65836,
65800, 65818, 65827, 65847, 65848, 65851, 65849, 65850, 65793, 65792, 1547, 8525, 9879, 9941, 9875, 1549,
1630, 1538, 1623, 1886, 1885, 1887, 1908, 1907, 1873, 1877, 1878, 1872, 1874, 1875, 1876, 1882,
1774, 1881, 1911, 1910, 1909, 1597, 1599, 1598, 1889, 1888, 1916, 1906, 1903, 1902, 1880, 1879,
1791, 1919, 1890, 1891, 1596, 1892, 1595, 1898, 1893, 1894, 1896, 1897, 1895, 1900, 1775, 1905,
1883, 1899, 1917, 1884, 1918, 1904, 1901, 1913, 1912, 1915, 1914, 65021, 1624, 1536, 1550, 1544,
1629, 1553, 1551, 1555, 1554, 1539, 1552, 1537, 1556, 1561, 1560, 1558, 1557, 1559, 1562, 1622,
1566, 1628, 1627, 1626, 1625, 1542, 1543, 1545, 1546, 9883, 8371, 68409, 68352, 68353, 68357, 68355,
68358, 68359, 68356, 68354, 68384, 68385, 68375, 68379, 68380, 68360, 68361, 68383, 68372, 68373, 68374, 68405,
68393, 68364, 68365, 68376, 68368, 68398, 68392, 68389, 68386, 68388, 68387, 68391, 68390, 68362, 68363, 68382,
68397, 68399, 68401, 68403, 68404, 68377, 68378, 68381, 68366, 68367, 68396, 68369, 68371, 68370, 68395, 68394,
68400, 68402, 6980, 7005, 7007, 7006, 7000, 6997, 6996, 7001, 6993, 6999, 6998, 6995, 6994, 6992,
6928, 6917, 6918, 6987, 6953, 6954, 6936, 6937, 6948, 6949, 6943, 6944, 6984, 6927, 6933, 6934,
6963, 6919, 6920, 6938, 6939, 6931, 6932, 6981, 6982, 6958, 6925, 6926, 6955, 6950, 6945, 6935,
6940, 6929, 6930, 6951, 6952, 6957, 6923, 6924, 6962, 6960, 6961, 6946, 6941, 6942, 6947, 6983,
6921, 6922, 6985, 6959, 6956, 6986, 7026, 7020, 7027, 7023, 7022, 7025, 7021, 7024, 7019, 7015,
7017, 7012, 7018, 7013, 7010, 7016, 7014, 7009, 7011, 7034, 7035, 7032, 7036, 7033, 7031, 7030,
7029, 7028, 7003, 7008, 7002, 6916, 6914, 6964, 6915, 6913, 6912, 6972, 6973, 6978, 6979, 6970,
6971, 6968, 6969, 6974, 6975, 6977, 6976, 6965, 6966, 6967, 7004, 42740, 42736, 42737, 42741, 42739,
42656, 42660, 42733, 42699, 42713, 42712, 42665, 42657, 42706, 42683, 42692, 42725, 42719, 42735, 42734, 42729,
42659, 42682, 42666, 42670, 42716, 42718, 42701, 42675, 42723, 42727, 42720, 42671, 42722, 42702, 42726, 42677,
42715, 42673, 42709, 42708, 42707, 42703, 42674, 42694, 42686, 42691, 42695, 42731, 42685, 42684, 42664, 42663,
42667, 42698, 42693, 42717, 42711, 42696, 42705, 42661, 42721, 42704, 42669, 42668, 42700, 42732, 42681, 42680,
42678, 42710, 42688, 42679, 42676, 42672, 42662, 42730, 42728, 42724, 42658, 42714, 42697, 42690, 42687, 42689,
42738, 42743, 42742, 9918, 2555, 2510, 2493, 9187, 9960, 9923, 9922, 9873, 11042, 11052, 11044, 11035,
9944, 11045, 11047, 9912, 11039, 11091, 11049, 11050, 11089, 9927, 9951, 9942, 11054, 11037, 12589, 9183,
11812, 9181, 11813, 9185, 6687, 6677, 6661, 6668, 6665, 6657, 6678, 6669, 6656, 6674, 6662, 6663,
6666, 6658, 6659, 6667, 6670, 6671, 6660, 6673, 6676, 6664, 6675, 6672, 6686, 6683, 6681, 6679,
6682, 6680, 983050, 6322, 6321, 6387, 6388, 5759, 6382, 6389, 6383, 6384, 6381, 6386, 6364, 6367,
6366, 5120, 6328, 6329, 6333, 6330, 6332, 6331, 6342, 6344, 6346, 6348, 6359, 6358, 6360, 6361,
6343, 6345, 6347, 6349, 6356, 6362, 6363, 6357, 6320, 6325, 6324, 6326, 6368, 6341, 6355, 6350,
6351, 6352, 6353, 6354, 6335, 6380, 6385, 6379, 6378, 6337, 6336, 6338, 6334, 6327, 6372, 6371,
6377, 6376, 6375, 6374, 6373, 6323, 6370, 6369, 6365, 5758, 5756, 5757, 5751, 5752, 5753, 5754,
5755, 6340, 6339, 9936, 66208, 66215, 66217, 66225, 66246, 66210, 66220, 66234, 66255, 66240, 66241, 66233,
66245, 66236, 66237, 66211, 66214, 66254, 66218, 66250, 66251, 66252, 66253, 66229, 66238, 66244, 66227, 66219,
66231, 66209, 66216, 66213, 66249, 66224, 66222, 66223, 66232, 66242, 66243, 66221, 66247, 66230, 66226, 66239,
66212, 66248, 66256, 66235, 66228, 9963, 8373, 9907, 9939, 43597, 43596, 43587, 43573, 43572, 43574, 43571,
43608, 43605, 43604, 43609, 43601, 43607, 43606, 43603, 43602, 43600, 43520, 43524, 43549, 43553, 43550, 43532,
43533, 43541, 43545, 43542, 43523, 43588, 43585, 43584, 43594, 43590, 43586, 43591, 43593, 43595, 43589, 43592,
43528, 43529, 43560, 43521, 43534, 43535, 43526, 43527, 43556, 43552, 43551, 43544, 43531, 43530, 43537, 43538,
43536, 43543, 43525, 43546, 43548, 43547, 43555, 43559, 43558, 43539, 43540, 43522, 43557, 43554, 43613, 43614,
43612, 43615, 43561, 43568, 43569, 43564, 43562, 43563, 43567, 43566, 43565, 43570, 9911, 9962, 127277, 9938,
12926, 12869, 12871, 12868, 12870, 127275, 127276, 12924, 12925, 12879, 12876, 12875, 12878, 12877, 12872, 12874,
12873, 127278, 64107, 64108, 64109, 64112, 64113, 64114, 64115, 64116, 64117, 64118, 64119, 64120, 64121, 64122,
64123, 64124, 64125, 64126, 64127, 64128, 64129, 64130, 64131, 64132, 64133, 64134, 64135, 64136, 64137, 64138,
64139, 64140, 64141, 64142, 64143, 64144, 64145, 64146, 64147, 64148, 64149, 64150, 64151, 64152, 64153, 64154,
64155, 64156, 64157, 64158, 64159, 64160, 64161, 64162, 64163, 64164, 64165, 64166, 64167, 64168, 64169, 64170,
64171, 64172, 64173, 64174, 64175, 64176, 64177, 64178, 64179, 64180, 64181, 64182, 64183, 64184, 64185, 64186,
64187, 64188, 64189, 64190, 64191, 64192, 64193, 64194, 64195, 64196, 64197, 64198, 64199, 64200, 64201, 64202,
64203, 64204, 64205, 64206, 64207, 64208, 64209, 64210, 64211, 64212, 64213, 64214, 64215, 64216, 64217, 12739,
12756, 12752, 12758, 12743, 12748, 12768, 12757, 12742, 12746, 12749, 12744, 12741, 12747, 12750, 12769, 12751,
12754, 12763, 12770, 12764, 12771, 12753, 12762, 12755, 12761, 12740, 12767, 12760, 12759, 12745, 12766, 12736,
12765, 12737, 12738, 9904, 7625, 7623, 7677, 8432, 857, 7627, 65062, 42609, 42620, 11766, 11744, 11774,
11761, 11747, 11768, 11751, 11752, 11753, 11756, 11757, 11765, 11764, 11746, 11759, 11767, 11772, 11775, 11750,
11773, 11769, 11754, 11755, 11762, 11763, 11758, 11760, 11745, 11770, 11771, 11749, 11748, 42621, 1159, 42608,
42610, 42607, 43240, 43237, 43236, 43241, 43233, 43239, 43238, 43235, 43234, 43232, 43242, 43244, 43245, 43246,
43247, 43243, 43248, 43249, 856, 7617, 7616, 861, 860, 7629, 862, 863, 858, 850, 7624, 7621,
119364, 119363, 119362, 7632, 7643, 7646, 7647, 7649, 7650, 7636, 7637, 7638, 7639, 7641, 7635, 7642,
7640, 7644, 7645, 7653, 7648, 7626, 7651, 7652, 7654, 8430, 7678, 852, 849, 8429, 8427, 65060,
65061, 7620, 7628, 7622, 7630, 8431, 848, 7679, 854, 853, 855, 8428, 7618, 7619, 7633, 7634,
851, 859, 7631, 11464, 11392, 11458, 11446, 11501, 11452, 11499, 11398, 11442, 11466, 11448, 11450, 11400,
11434, 11396, 11406, 11410, 11412, 11436, 11420, 11472, 11414, 11416, 11418, 11422, 11444, 11480, 11462, 11478,
11470, 11476, 11474, 11468, 11454, 11460, 11482, 11486, 11488, 11484, 11490, 11440, 11424, 11438, 11426, 11456,
11428, 11402, 11430, 11408, 11432, 11394, 11404, 11503, 11504, 11505, 11517, 11518, 11519, 11514, 11513, 11515,
11516, 11465, 11393, 11459, 11447, 11502, 11453, 11500, 11399, 11443, 11467, 11449, 11451, 11401, 11435, 11397,
11407, 11411, 11413, 11437, 11421, 11473, 11415, 11417, 11419, 11423, 11445, 11481, 11463, 11479, 11471, 11477,
11475, 11469, 11455, 11461, 11483, 11487, 11489, 11485, 11491, 11441, 11425, 11439, 11427, 11457, 11429, 11403,
11431, 11409, 11433, 11395, 11405, 11492, 11497, 11493, 11494, 11498, 11495, 11496, 119664, 119661, 119660, 119665,
119657, 119663, 119662, 119659, 119658, 119655, 119652, 119651, 119656, 119648, 119654, 119653, 119650, 119649, 127370, 9876,
9932, 74758, 74765, 74780, 74794, 74771, 74820, 74821, 74755, 74829, 74836, 74837, 74809, 74762, 74777, 74786,
74791, 74801, 74844, 74768, 74754, 74828, 74834, 74835, 74808, 74761, 74776, 74785, 74790, 74800, 74767, 74812,
74814, 74815, 74813, 74839, 74838, 74759, 74766, 74781, 74795, 74772, 74822, 74825, 74823, 74824, 74850, 74849,
74831, 74804, 74847, 74840, 74773, 74782, 74848, 74796, 74842, 74845, 74757, 74764, 74779, 74793, 74770, 74818,
74819, 74817, 74802, 74803, 74756, 74830, 74763, 74778, 74792, 74769, 74816, 74753, 74827, 74833, 74806, 74807,
74760, 74775, 74784, 74788, 74789, 74798, 74799, 74810, 74811, 74752, 74826, 74832, 74805, 74841, 74774, 74783,
74787, 74797, 74843, 74846, 74866, 74867, 74864, 74865, 73728, 73729, 73730, 73731, 73732, 73733, 73734, 73735,
73736, 73737, 73738, 73749, 73739, 73740, 73741, 73742, 73743, 73744, 73745, 73746, 73747, 73748, 73750, 73751,
73752, 73753, 73754, 73755, 73756, 73757, 73758, 73759, 73760, 73761, 73762, 73763, 73764, 73765, 73766, 73767,
73768, 73769, 73770, 73771, 73772, 73773, 73774, 73776, 73777, 73775, 73778, 73779, 73780, 73781, 73782, 73783,
73784, 73786, 73788, 73789, 73787, 73785, 73790, 73791, 73792, 73793, 73794, 73795, 73796, 73797, 73798, 73799,
73800, 73801, 73802, 73803, 73804, 73805, 73808, 73806, 73807, 73809, 73810, 73811, 73812, 73813, 73814, 73815,
73816, 73817, 73818, 73819, 73820, 73821, 73822, 73823, 73824, 73825, 73826, 73827, 73828, 73829, 73830, 73831,
73832, 73833, 73834, 73835, 73836, 73837, 73838, 73839, 73840, 73841, 73842, 73843, 73844, 73845, 73846, 73847,
73848, 73849, 73850, 73852, 73851, 73853, 73854, 73855, 73856, 73857, 73858, 73859, 73860, 73861, 73862, 73863,
73864, 73865, 73866, 73868, 73867, 73869, 73870, 73871, 73872, 73873, 73874, 73875, 73876, 73877, 73878, 73879,
73883, 73884, 73885, 73880, 73881, 73882, 73886, 73887, 73888, 73889, 73890, 73891, 73892, 73893, 73894, 73895,
73896, 73897, 73898, 73899, 73900, 73901, 73902, 73903, 73904, 73905, 73906, 73907, 73908, 73909, 73910, 73911,
73965, 73912, 73913, 73914, 73915, 73916, 73917, 73918, 73919, 73920, 73921, 73922, 73923, 73924, 73925, 73926,
73927, 73928, 73929, 73930, 73931, 73932, 73933, 73934, 73935, 73936, 73937, 73938, 73939, 73940, 73941, 73942,
73943, 73944, 73945, 73946, 73947, 73948, 73949, 73950, 73951, 73952, 73953, 73954, 73955, 73956, 73957, 73958,
73959, 73960, 73961, 73962, 73963, 73964, 73966, 73967, 73968, 73969, 73970, 73971, 73972, 73973, 73974, 73975,
73978, 73977, 73976, 73979, 73980, 73981, 73982, 73983, 73984, 73987, 73985, 73986, 73988, 73990, 73989, 73991,
73992, 73993, 73994, 73995, 73996, 73997, 73998, 73999, 74000, 74001, 74002, 74005, 74003, 74004, 74006, 74007,
74008, 74013, 74009, 74010, 74011, 74012, 74014, 74017, 74015, 74016, 74018, 74019, 74020, 74021, 74022, 74023,
74024, 74025, 74027, 74026, 74028, 74029, 74030, 74031, 74032, 74033, 74034, 74035, 74036, 74037, 74038, 74039,
74040, 74041, 74042, 74043, 74044, 74045, 74046, 74047, 74048, 74049, 74050, 74051, 74052, 74053, 74054, 74055,
74058, 74057, 74056, 74059, 74060, 74061, 74062, 74064, 74065, 74066, 74063, 74067, 74068, 74069, 74070, 74071,
74072, 74073, 74074, 74075, 74076, 74077, 74078, 74079, 74080, 74081, 74082, 74083, 74084, 74085, 74086, 74087,
74088, 74090, 74089, 74091, 74092, 74093, 74094, 74095, 74096, 74097, 74098, 74099, 74100, 74101, 74102, 74103,
74104, 74105, 74106, 74107, 74108, 74109, 74110, 74111, 74112, 74113, 74114, 74115, 74116, 74117, 74118, 74119,
74120, 74121, 74122, 74123, 74124, 74125, 74126, 74127, 74128, 74129, 74130, 74131, 74132, 74133, 74134, 74135,
74137, 74136, 74138, 74139, 74140, 74141, 74142, 74143, 74144, 74145, 74146, 74147, 74148, 74149, 74150, 74151,
74152, 74153, 74154, 74155, 74156, 74157, 74158, 74159, 74160, 74161, 74162, 74163, 74164, 74165, 74166, 74167,
74168, 74219, 74169, 74170, 74171, 74172, 74173, 74174, 74175, 74176, 74177, 74178, 74179, 74180, 74181, 74182,
74183, 74184, 74185, 74186, 74187, 74188, 74189, 74190, 74191, 74192, 74193, 74194, 74195, 74196, 74197, 74198,
74199, 74200, 74201, 74202, 74203, 74204, 74205, 74206, 74207, 74208, 74209, 74210, 74211, 74212, 74213, 74214,
74215, 74216, 74217, 74218, 74220, 74223, 74224, 74221, 74222, 74225, 74226, 74227, 74228, 74229, 74230, 74231,
74232, 74233, 74234, 74235, 74236, 74237, 74258, 74259, 74261, 74260, 74257, 74238, 74239, 74240, 74241, 74242,
74243, 74244, 74245, 74246, 74247, 74248, 74249, 74250, 74251, 74252, 74253, 74254, 74255, 74256, 74262, 74263,
74265, 74264, 74266, 74267, 74268, 74269, 74270, 74271, 74272, 74274, 74273, 74275, 74276, 74277, 74278, 74279,
74280, 74281, 74282, 74283, 74284, 74285, 74286, 74287, 74288, 74289, 74290, 74296, 74294, 74295, 74291, 74292,
74293, 74297, 74301, 74298, 74299, 74300, 74302, 74303, 74304, 74305, 74307, 74306, 74308, 74310, 74309, 74311,
74312, 74315, 74313, 74314, 74316, 74317, 74318, 74319, 74320, 74321, 74322, 74323, 74324, 74325, 74326, 74327,
74328, 74329, 74330, 74331, 74332, 74333, 74334, 74335, 74336, 74337, 74338, 74339, 74347, 74348, 74340, 74341,
74342, 74343, 74344, 74346, 74345, 74349, 74350, 74351, 74352, 74353, 74354, 74355, 74356, 74357, 74358, 74359,
74360, 74361, 74362, 74363, 74364, 74365, 74366, 74367, 74377, 74368, 74369, 74370, 74371, 74372, 74373, 74374,
74375, 74376, 74378, 74382, 74379, 74380, 74381, 74383, 74384, 74385, 74386, 74387, 74389, 74408, 74388, 74407,
74390, 74391, 74392, 74393, 74394, 74395, 74396, 74397, 74398, 74399, 74400, 74401, 74402, 74403, 74404, 74405,
74406, 74409, 74410, 74411, 74412, 74413, 74414, 74415, 74416, 74417, 74418, 74419, 74420, 74421, 74422, 74423,
74424, 74425, 74426, 74427, 74428, 74429, 74430, 74431, 74432, 74433, 74434, 74435, 74436, 74437, 74438, 74439,
74440, 74441, 74442, 74443, 74444, 74445, 74446, 74447, 74448, 74449, 74450, 74451, 74453, 74452, 74454, 74455,
74456, 74457, 74458, 74459, 74460, 74461, 74462, 74463, 74464, 74465, 74466, 74467, 74468, 74469, 74470, 74471,
74472, 74473, 74474, 74475, 74476, 74479, 74477, 74478, 74480, 74481, 74482, 74483, 74484, 74485, 74486, 74487,
74488, 74489, 74490, 74491, 74492, 74493, 74494, 74495, 74496, 74497, 74499, 74500, 74498, 74501, 74502, 74503,
74504, 74505, 74506, 74507, 74508, 74510, 74511, 74512, 74509, 74513, 74514, 74515, 74521, 74516, 74522, 74523,
74517, 74518, 74519, 74520, 74524, 74525, 74526, 74527, 74528, 74529, 74530, 74531, 74532, 74533, 74534, 74535,
74536, 74537, 74538, 74539, 74540, 74541, 74542, 74543, 74544, 74545, 74546, 74547, 74548, 74549, 74550, 74551,
74552, 74553, 74554, 74555, 74556, 74557, 74558, 74559, 74560, 74561, 74562, 74563, 74564, 74565, 74566, 74567,
74568, 74569, 74570, 74571, 74572, 74573, 74574, 74575, 74576, 74577, 74578, 74579, 74580, 74581, 74583, 74584,
74582, 74585, 74586, 74587, 74588, 74589, 74591, 74590, 74592, 74593, 74594, 74595, 74596, 74597, 74598, 74599,
74600, 74601, 74602, 74603, 74604, 74605, 74606, 9982, 67584, 67585, 67586, 67589, 67592, 67594, 67595, 67596,
67597, 67598, 67599, 67600, 67601, 67602, 67603, 67604, 67605, 67606, 67607, 67608, 67609, 67610, 67611, 67612,
67613, 67587, 67614, 67615, 67616, 67617, 67618, 67619, 67620, 67621, 67622, 67623, 67624, 67625, 67626, 67627,
67628, 67629, 67630, 67631, 67632, 67633, 67588, 67634, 67635, 67636, 67637, 67639, 67640, 67644, 67647, 1310,
42602, 42586, 42572, 42630, 42584, 42568, 42604, 42624, 42562, 42626, 42632, 1298, 1312, 1314, 1270, 1274,
1276, 1278, 42644, 42566, 42582, 42588, 42578, 1300, 42600, 42570, 42574, 1316, 1306, 42564, 42580, 1296,
1302, 42646, 42594, 42596, 42598, 42642, 42634, 42640, 42638, 42636, 1308, 1304, 42576, 42590, 42560, 42628,
42622, 42606, 7467, 42623, 1311, 42603, 42587, 42573, 42631, 42585, 42569, 42605, 42625, 42563, 42627, 42633,
1299, 1313, 1315, 1271, 1275, 1277, 1279, 42645, 42567, 42583, 42589, 42579, 1301, 42601, 42571, 42575,
1231, 1317, 1307, 42565, 42581, 1297, 1303, 42647, 42595, 42597, 42599, 42643, 42635, 42641, 42639, 42637,
1309, 1305, 42577, 42591, 42561, 42629, 9192, 66599, 66598, 66639, 66638, 43258, 43257, 43259, 2431, 2418,
2430, 2427, 2429, 2426, 2428, 2308, 2425, 43255, 43254, 43253, 43251, 43252, 2417, 2304, 43256, 43250,
2389, 2382, 11033, 11030, 11031, 11032, 127241, 127238, 127237, 127242, 127234, 127240, 127239, 127236, 127235, 127233,
127232, 119557, 119555, 119556, 9868, 9871, 119553, 119554, 9870, 9869, 9933, 9902, 127024, 127025, 127026, 127027,
127028, 127029, 127030, 127031, 127032, 127033, 127034, 127035, 127036, 127037, 127038, 127039, 127040, 127041, 127042, 127043,
127044, 127045, 127046, 127047, 127048, 127049, 127050, 127051, 127052, 127053, 127054, 127055, 127056, 127057, 127058, 127059,
127060, 127061, 127062, 127063, 127064, 127065, 127066, 127067, 127068, 127069, 127070, 127071, 127072, 127073, 127074, 127075,
127076, 127077, 127078, 127079, 127080, 127081, 127082, 127083, 127084, 127085, 127086, 127087, 127088, 127089, 127090, 127091,
127092, 127093, 127094, 127095, 127096, 127097, 127098, 127099, 127100, 127101, 127102, 127103, 127104, 127105, 127106, 127107,
127108, 127109, 127110, 127111, 127112, 127113, 127114, 127115, 127116, 127117, 127118, 127119, 127120, 127121, 127122, 127123,
8284, 11795, 11798, 11034, 11784, 11799, 8508, 9890, 9891, 11796, 11015, 9946, 9178, 11790, 77824, 77825,
77826, 77827, 77828, 77829, 77830, 77831, 77832, 77833, 77834, 77835, 77836, 77837, 77838, 77839, 77840, 77841,
77842, 77843, 77844, 77845, 77846, 77847, 77848, 77849, 77850, 77851, 77852, 77853, 77854, 77855, 77856, 77857,
77858, 77859, 77860, 77861, 77862, 77863, 77864, 77865, 77866, 77867, 77868, 77869, 77870, 77871, 77872, 77873,
77874, 77875, 77876, 77877, 77878, 77879, 77880, 77881, 77882, 77883, 77884, 77885, 77886, 77887, 77888, 77889,
77890, 77891, 77892, 77893, 77894, 77895, 77896, 77897, 77898, 77899, 77900, 77901, 77902, 77903, 78861, 78862,
78863, 78864, 78865, 78866, 78867, 78868, 78869, 78870, 78871, 78872, 78873, 78874, 78875, 78876, 78877, 78878,
78879, 78880, 78881, 78882, 78883, 78884, 78885, 78886, 78887, 78888, 78889, 78890, 78891, 78892, 78893, 78894,
77904, 77905, 77906, 77907, 77908, 77909, 77910, 77911, 77912, 77913, 77914, 77915, 77916, 77917, 77918, 77919,
77920, 77921, 77922, 77923, 77924, 77925, 77926, 77927, 77928, 77929, 77930, 77931, 77932, 77933, 77934, 77935,
77936, 77937, 77938, 77939, 77940, 77941, 77942, 77943, 77944, 77945, 77946, 77947, 77948, 77949, 77950, 77951,
77952, 77953, 77954, 77955, 77956, 77957, 77958, 77959, 77960, 77961, 77962, 77963, 77964, 77965, 77966, 77967,
77968, 77969, 77970, 77971, 77972, 77973, 77974, 77975, 77976, 77977, 77978, 77979, 77980, 77981, 77982, 77983,
77984, 77985, 77986, 77987, 77988, 77989, 77990, 77991, 77992, 77993, 77994, 77995, 77996, 77997, 77998, 77999,
78000, 78001, 78002, 78003, 78004, 78005, 78006, 78007, 78008, 78009, 78010, 78011, 78012, 78013, 78014, 78015,
78016, 78017, 78018, 78019, 78020, 78021, 78022, 78023, 78024, 78025, 78026, 78027, 78028, 78029, 78030, 78031,
78032, 78033, 78034, 78035, 78036, 78037, 78038, 78039, 78040, 78041, 78042, 78043, 78044, 78045, 78046, 78047,
78048, 78049, 78050, 78051, 78052, 78053, 78054, 78055, 78056, 78057, 78058, 78059, 78060, 78061, 78062, 78063,
78064, 78065, 78066, 78067, 78068, 78069, 78070, 78071, 78072, 78073, 78074, 78075, 78076, 78077, 78078, 78079,
78080, 78081, 78082, 78083, 78084, 78085, 78086, 78087, 78088, 78089, 78090, 78091, 78092, 78093, 78094, 78095,
78096, 78097, 78098, 78099, 78100, 78101, 78102, 78103, 78104, 78105, 78106, 78107, 78108, 78109, 78110, 78111,
78112, 78113, 78114, 78115, 78116, 78117, 78118, 78119, 78120, 78121, 78122, 78123, 78124, 78125, 78126, 78127,
78128, 78129, 78130, 78131, 78132, 78133, 78134, 78135, 78136, 78137, 78138, 78139, 78140, 78141, 78142, 78143,
78144, 78145, 78146, 78147, 78148, 78149, 78150, 78151, 78152, 78153, 78154, 78155, 78156, 78157, 78158, 78159,
78160, 78161, 78162, 78163, 78164, 78165, 78166, 78167, 78168, 78169, 78170, 78171, 78172, 78173, 78174, 78175,
78176, 78177, 78178, 78179, 78180, 78181, 78182, 78183, 78184, 78185, 78186, 78187, 78188, 78189, 78190, 78191,
78192, 78193, 78194, 78195, 78196, 78197, 78198, 78199, 78200, 78201, 78202, 78203, 78204, 78205, 78206, 78207,
78208, 78209, 78210, 78211, 78212, 78213, 78214, 78215, 78216, 78217, 78218, 78219, 78220, 78221, 78222, 78223,
78224, 78225, 78226, 78227, 78228, 78229, 78230, 78231, 78232, 78233, 78234, 78235, 78236, 78237, 78238, 78239,
78240, 78241, 78242, 78243, 78244, 78245, 78246, 78247, 78248, 78249, 78250, 78251, 78252, 78253, 78254, 78255,
78256, 78257, 78258, 78259, 78260, 78261, 78262, 78263, 78264, 78265, 78266, 78267, 78268, 78269, 78270, 78271,
78272, 78273, 78274, 78275, 78276, 78277, 78278, 78279, 78280, 78281, 78282, 78283, 78284, 78285, 78286, 78287,
78288, 78289, 78290, 78291, 78292, 78293, 78294, 78295, 78296, 78297, 78298, 78299, 78300, 78301, 78302, 78303,
78304, 78305, 78306, 78307, 78308, 78309, 78310, 78311, 78312, 78313, 78314, 78315, 78316, 78317, 78318, 78319,
78320, 78321, 78322, 78323, 78324, 78325, 78326, 78327, 78328, 78329, 78330, 78331, 78332, 78333, 78334, 78335,
78336, 78337, 78338, 78339, 78340, 78341, 78342, 78343, 78344, 78345, 78346, 78347, 78348, 78349, 78350, 78351,
78352, 78353, 78354, 78355, 78356, 78357, 78358, 78359, 78360, 78361, 78362, 78363, 78364, 78365, 78366, 78367,
78368, 78369, 78370, 78371, 78372, 78373, 78374, 78375, 78376, 78377, 78378, 78379, 78380, 78381, 78382, 78383,
78384, 78385, 78386, 78387, 78388, 78389, 78390, 78391, 78392, 78393, 78394, 78395, 78396, 78397, 78398, 78399,
78400, 78401, 78402, 78403, 78404, 78405, 78406, 78407, 78408, 78409, 78410, 78411, 78412, 78413, 78414, 78415,
78416, 78417, 78418, 78419, 78420, 78421, 78422, 78423, 78424, 78425, 78426, 78427, 78428, 78429, 78430, 78431,
78432, 78433, 78434, 78435, 78436, 78437, 78438, 78439, 78440, 78441, 78442, 78443, 78444, 78445, 78446, 78447,
78448, 78449, 78450, 78451, 78452, 78453, 78454, 78455, 78456, 78457, 78458, 78459, 78460, 78461, 78462, 78463,
78464, 78465, 78466, 78467, 78468, 78469, 78470, 78471, 78472, 78473, 78474, 78475, 78476, 78477, 78478, 78479,
78480, 78481, 78482, 78483, 78484, 78485, 78486, 78487, 78488, 78489, 78490, 78491, 78492, 78493, 78494, 78495,
78496, 78497, 78498, 78499, 78500, 78501, 78502, 78503, 78504, 78505, 78506, 78507, 78508, 78509, 78510, 78511,
78512, 78513, 78514, 78515, 78516, 78517, 78518, 78519, 78520, 78521, 78522, 78523, 78524, 78525, 78526, 78527,
78528, 78529, 78530, 78531, 78532, 78533, 78534, 78535, 78536, 78537, 78538, 78539, 78540, 78541, 78542, 78543,
78544, 78545, 78546, 78547, 78548, 78549, 78550, 78551, 78552, 78553, 78554, 78555, 78556, 78557, 78558, 78559,
78560, 78561, 78562, 78563, 78564, 78565, 78566, 78567, 78568, 78569, 78570, 78571, 78572, 78573, 78574, 78575,
78576, 78577, 78578, 78579, 78580, 78581, 78582, 78583, 78584, 78585, 78586, 78587, 78588, 78589, 78590, 78591,
78592, 78593, 78594, 78595, 78596, 78597, 78598, 78599, 78600, 78601, 78602, 78603, 78604, 78605, 78606, 78607,
78608, 78609, 78610, 78611, 78612, 78613, 78614, 78615, 78616, 78617, 78618, 78619, 78620, 78621, 78622, 78623,
78624, 78625, 78626, 78627, 78628, 78629, 78630, 78631, 78632, 78633, 78634, 78635, 78636, 78637, 78638, 78639,
78640, 78641, 78642, 78643, 78644, 78645, 78646, 78647, 78648, 78649, 78650, 78651, 78652, 78653, 78654, 78655,
78656, 78657, 78658, 78659, 78660, 78661, 78662, 78663, 78664, 78665, 78666, 78667, 78668, 78669, 78670, 78671,
78672, 78673, 78674, 78675, 78676, 78677, 78678, 78679, 78680, 78681, 78682, 78683, 78684, 78685, 78686, 78687,
78688, 78689, 78690, 78691, 78692, 78693, 78694, 78695, 78696, 78697, 78698, 78699, 78700, 78701, 78702, 78703,
78704, 78705, 78706, 78707, 78708, 78709, 78710, 78711, 78712, 78713, 78714, 78715, 78716, 78717, 78718, 78719,
78720, 78721, 78722, 78723, 78724, 78725, 78726, 78727, 78728, 78729, 78730, 78731, 78732, 78733, 78734, 78735,
78736, 78737, 78738, 78739, 78740, 78741, 78742, 78743, 78744, 78745, 78746, 78747, 78748, 78749, 78750, 78751,
78752, 78753, 78754, 78755, 78756, 78757, 78758, 78759, 78760, 78761, 78762, 78763, 78764, 78765, 78766, 78767,
78768, 78769, 78770, 78771, 78772, 78773, 78774, 78775, 78776, 78777, 78778, 78779, 78780, 78781, 78782, 78783,
78784, 78785, 78786, 78787, 78788, 78789, 78790, 78791, 78792, 78793, 78794, 78795, 78796, 78797, 78798, 78799,
78800, 78801, 78802, 78803, 78804, 78805, 78806, 78807, 78808, 78809, 78810, 78811, 78812, 78813, 78814, 78815,
78816, 78817, 78818, 78819, 78820, 78821, 78822, 78823, 78824, 78825, 78826, 78827, 78828, 78829, 78830, 78831,
78832, 78833, 78834, 78835, 78836, 78837, 78838, 78839, 78840, 78841, 78842, 78843, 78844, 78845, 78846, 78847,
78848, 78849, 78850, 78851, 78852, 78853, 78854, 78855, 78856, 78857, 78858, 78859, 78860, 9167, 9191, 11072,
4959, 4960, 11653, 4999, 4998, 4997, 11688, 11691, 11693, 11692, 11704, 11707, 11709, 11708, 11706, 11710,
11705, 11690, 11694, 11689, 11664, 11655, 11661, 11660, 5003, 5002, 5001, 11667, 4895, 11670, 11669, 11668,
11658, 4879, 11736, 11739, 11741, 11740, 11738, 11742, 11737, 4615, 11662, 4783, 11720, 11723, 11725, 11724,
11722, 11726, 11721, 11648, 11649, 4995, 4994, 4993, 11656, 11657, 11665, 11666, 5007, 5006, 5005, 4679,
11712, 11715, 11717, 11716, 11714, 11718, 11713, 11650, 4996, 5000, 4992, 5004, 11652, 11651, 11680, 11683,
11685, 11684, 11682, 11686, 11681, 11663, 11654, 4935, 4815, 4743, 11728, 11731, 11733, 11732, 11730, 11734,
11729, 4847, 11659, 11696, 11699, 11701, 11700, 11698, 11702, 11697, 5014, 5009, 5016, 5012, 5015, 5013,
5017, 5010, 5011, 5008, 8507, 9950, 9972, 11821, 8281, 9971, 9189, 9884, 9880, 8277, 11792, 9970,
8283, 8280, 9981, 9905, 9179, 9881, 9966, 9965, 4346, 4345, 983902, 11520, 11521, 11546, 11549, 11545,
11548, 11523, 11524, 11522, 11542, 11552, 11556, 11553, 11554, 11557, 11528, 11551, 11547, 11529, 11541, 11530,
11531, 11532, 11533, 11534, 11540, 11543, 11536, 11537, 11544, 11527, 11538, 11539, 11525, 11555, 11550, 11526,
11535, 11264, 11304, 11265, 11293, 11276, 11268, 11271, 11306, 11287, 11267, 11288, 11275, 11274, 11305, 11303,
11273, 11307, 11277, 11310, 11278, 11279, 11280, 11281, 11289, 11290, 11282, 11283, 11294, 11291, 11308, 11284,
11300, 11301, 11298, 11309, 11292, 11285, 11286, 11266, 11297, 11296, 11295, 11269, 11302, 11299, 11272, 11270,
11312, 11352, 11313, 11341, 11324, 11316, 11319, 11354, 11335, 11315, 11336, 11323, 11322, 11353, 11351, 11321,
11355, 11325, 11358, 11326, 11327, 11328, 11329, 11337, 11338, 11330, 11331, 11342, 11339, 11356, 11332, 11348,
11349, 11346, 11357, 11340, 11333, 11334, 11314, 11345, 11344, 11343, 11317, 11350, 11347, 11320, 11318, 65860,
65873, 65866, 65863, 65878, 65859, 65861, 65875, 65868, 65871, 65864, 65862, 65870, 65858, 65857, 65874, 65867,
65856, 65876, 65869, 65879, 65872, 65865, 65877, 65903, 65885, 65907, 65900, 65883, 65886, 65880, 65896, 65882,
65890, 65891, 65904, 65908, 65897, 65902, 65906, 65881, 65898, 65905, 65892, 65893, 65899, 65884, 65894, 65895,
65887, 65901, 65888, 65889, 65927, 65926, 1022, 975, 882, 880, 886, 1018, 1015, 1017, 1023, 1021,
65915, 65920, 65919, 65928, 119325, 119331, 119332, 119333, 119334, 119335, 119336, 119337, 119326, 119338, 119339, 119340,
119341, 119342, 119343, 119344, 119345, 119346, 119347, 119348, 119349, 119327, 119350, 119351, 119352, 119353, 119354, 119355,
119356, 119328, 119357, 119358, 119359, 119360, 119361, 119329, 119330, 65922, 7462, 7463, 7464, 7466, 7465, 65923,
65921, 119365, 65916, 65909, 65910, 65924, 1020, 892, 883, 881, 887, 1019, 1016, 893, 891, 7526,
7530, 7527, 7529, 7528, 65914, 65918, 65912, 65929, 65917, 65911, 119296, 119305, 119306, 119307, 119308, 119309,
119310, 119311, 119312, 119313, 119314, 119297, 119315, 119316, 119317, 119318, 119319, 119298, 119299, 119300, 119320, 119321,
119322, 119323, 119324, 119301, 119302, 119303, 119304, 65925, 65913, 65930, 8370, 2700, 2785, 2801, 2786, 2787,
2561, 2641, 2563, 2677, 9874, 43387, 43383, 43382, 4442, 43375, 43377, 43376, 4444, 4445, 4443, 43386,
43380, 43379, 43378, 43373, 43371, 43374, 43364, 43368, 43369, 43372, 43365, 43370, 43367, 43366, 43384, 43381,
43385, 43388, 43363, 43360, 43361, 4446, 43362, 55287, 55288, 55261, 4604, 4606, 4605, 4602, 4603, 55266,
55262, 55265, 55263, 55244, 55243, 55284, 55283, 55290, 55291, 55273, 55272, 55269, 55268, 55271, 55267, 55254,
55256, 55258, 55257, 55253, 55260, 55259, 55280, 55279, 55282, 55275, 55274, 55278, 55281, 55289, 55264, 4607,
55270, 55255, 55276, 55277, 55245, 55246, 55251, 55250, 55247, 55248, 55249, 55252, 55286, 55285, 4515, 55237,
55238, 55225, 55227, 55226, 55228, 55236, 55233, 55229, 55230, 55232, 55231, 55234, 55235, 55217, 4518, 4519,
55216, 55222, 55221, 4516, 4517, 55218, 55219, 55220, 55223, 55224, 9980, 11096, 11095, 9955, 11097, 10071,
11093, 11094, 9947, 1442, 1477, 1466, 1479, 1478, 9937, 19958, 19966, 19922, 19967, 19924, 19946, 19947,
19909, 19923, 19939, 19944, 19943, 19956, 19906, 19962, 19935, 19919, 19916, 19920, 19948, 19925, 19917, 19937,
19931, 19929, 19911, 19945, 19934, 19964, 19928, 19963, 19918, 19930, 19942, 19941, 19950, 19914, 19938, 19949,
19936, 19927, 19952, 19965, 19912, 19926, 19915, 19932, 19910, 19954, 19953, 19933, 19904, 19940, 19960, 19961,
19955, 19957, 19905, 19959, 19951, 19913, 19908, 19921, 19907, 9889, 9964, 11043, 9897, 9749, 8372, 11802,
11794, 9976, 67648, 67663, 67649, 67651, 67650, 67652, 67655, 67658, 67659, 67660, 67661, 67664, 67666, 67667,
67665, 67662, 67668, 67669, 67656, 67653, 67657, 67654, 67672, 67677, 67678, 67675, 67679, 67674, 67676, 67673,
67671, 68448, 68449, 68451, 68450, 68452, 68455, 68458, 68459, 68460, 68461, 68463, 68464, 68462, 68465, 68466,
68456, 68453, 68457, 68454, 68475, 68472, 68478, 68479, 68476, 68474, 68477, 68473, 68416, 68431, 68417, 68419,
68418, 68420, 68423, 68426, 68427, 68428, 68429, 68432, 68434, 68435, 68433, 68430, 68436, 68437, 68424, 68421,
68425, 68422, 68443, 68440, 68446, 68447, 68444, 68442, 68445, 68441, 9892, 11800, 8276, 8292, 9979, 43455,
43453, 43454, 43480, 43477, 43476, 43481, 43473, 43479, 43478, 43475, 43474, 43472, 43457, 43396, 43405, 43431,
43432, 43413, 43414, 43426, 43427, 43421, 43422, 43404, 43410, 43411, 43442, 43398, 43397, 43399, 43415, 43417,
43407, 43409, 43408, 43437, 43433, 43428, 43423, 43412, 43402, 43403, 43418, 43416, 43406, 43429, 43401, 43430,
43435, 43436, 43441, 43440, 43439, 43424, 43425, 43419, 43420, 43400, 43438, 43434, 43466, 43467, 43459, 43487,
43464, 43461, 43465, 43460, 43463, 43468, 43486, 43462, 43456, 43471, 43458, 43393, 43443, 43394, 43392, 43395,
43469, 43451, 43452, 43448, 43449, 43450, 43444, 43445, 43446, 43447, 9909, 69819, 69824, 69825, 69823, 69820,
69763, 69764, 69770, 69772, 69797, 69798, 69778, 69779, 69792, 69785, 69786, 69787, 69793, 69769, 69775, 69776,
69807, 69765, 69766, 69780, 69781, 69773, 69774, 69802, 69799, 69794, 69777, 69789, 69782, 69771, 69795, 69796,
69801, 69788, 69806, 69804, 69805, 69790, 69791, 69783, 69784, 69767, 69768, 69803, 69800, 69821, 69822, 69761,
69760, 69818, 69817, 69762, 69808, 69814, 69816, 69813, 69809, 69810, 69815, 69811, 69812, 983042, 3261, 3313,
3260, 3314, 3298, 3299, 983944, 43272, 43269, 43268, 43273, 43265, 43271, 43270, 43267, 43266, 43264, 43298,
43289, 43297, 43288, 43276, 43295, 43283, 43300, 43274, 43275, 43292, 43287, 43284, 43277, 43281, 43299, 43301,
43285, 43286, 43290, 43278, 43279, 43282, 43294, 43296, 43293, 43291, 43280, 43310, 43311, 43308, 43309, 43307,
43303, 43305, 43306, 43304, 43302, 68163, 68160, 68162, 68161, 68096, 68134, 68135, 68117, 68118, 68129, 68124,
68125, 68130, 68114, 68115, 68145, 68119, 68112, 68113, 68146, 68139, 68136, 68131, 68126, 68121, 68132, 68133,
68138, 68143, 68141, 68142, 68127, 68128, 68122, 68123, 68147, 68140, 68137, 68144, 68166, 68167, 68164, 68165,
68178, 68179, 68182, 68176, 68183, 68184, 68181, 68180, 68177, 68110, 68152, 68153, 68154, 68109, 68111, 68159,
68108, 68101, 68097, 68102, 68098, 68099, 983923, 983908, 983909, 983911, 983910, 983913, 983915, 983935, 983903, 983904,
983906, 983905, 983936, 983930, 983927, 983917, 983907, 983922, 983912, 983924, 983926, 983925, 983929, 983934, 983932, 983933,
983918, 983919, 983921, 983920, 983914, 983916, 983931, 983928, 983941, 983938, 983939, 983940, 6109, 6627, 6643, 6628,
6644, 6634, 6650, 6637, 6653, 6638, 6654, 6635, 6651, 6636, 6652, 6639, 6655, 6131, 6132, 6129,
6130, 6133, 6136, 6137, 6134, 6135, 6128, 6625, 6641, 6624, 6626, 6642, 6629, 6645, 6632, 6648,
6633, 6649, 6630, 6646, 6631, 6647, 6640, 983943, 983937, 983942, 983044, 983043, 983046, 983045, 68413, 68415,
68412, 68414, 983552, 983578, 983580, 570, 42802, 11373, 42804, 42806, 42808, 42810, 42812, 579, 42822, 571,
42862, 42796, 42798, 983562, 983560, 983586, 983588, 983582, 983584, 582, 983554, 983558, 983556, 42788, 42786, 42858,
983040, 577, 11367, 11381, 42790, 983564, 983592, 983594, 42873, 42875, 42877, 42882, 42884, 42886, 42860, 584,
983596, 11369, 42818, 42816, 42820, 573, 11360, 42824, 11362, 983598, 11374, 983600, 7930, 7932, 42826, 42828,
983568, 983572, 983570, 42830, 42834, 42836, 11363, 42832, 42840, 42838, 42842, 588, 11364, 983602, 42814, 42844,
11390, 983574, 42891, 7838, 586, 574, 42852, 42854, 42794, 11375, 11376, 42878, 42880, 581, 42792, 580,
983608, 983576, 983610, 983604, 983606, 42846, 42856, 42850, 42848, 11378, 7934, 590, 11371, 11391, 43007, 43006,
43005, 43003, 43004, 7461, 7424, 7425, 7427, 7428, 7429, 7431, 7430, 7459, 42800, 7434, 7435, 7436,
7437, 7439, 7440, 7445, 7448, 7438, 7449, 42870, 42801, 7451, 11387, 7450, 7452, 7456, 7457, 7458,
7460, 7547, 7550, 983553, 983579, 983581, 7567, 11365, 42803, 7568, 42805, 42807, 42809, 42811, 42813, 7532,
7552, 7447, 42823, 572, 42863, 42797, 42799, 545, 7569, 7533, 7553, 568, 7839, 567, 42865, 983563,
983561, 983587, 983589, 11384, 983583, 983585, 7570, 583, 983555, 983559, 983557, 42789, 42787, 7563, 7576, 42859,
7578, 7534, 7554, 7555, 983041, 578, 11368, 11382, 42791, 983566, 983590, 983591, 983565, 983593, 983595, 7574,
42874, 42876, 7545, 42883, 42885, 42887, 7548, 42861, 983597, 585, 11370, 42819, 7556, 42817, 42821, 564,
11361, 42825, 7557, 983599, 7836, 7837, 42866, 7535, 7558, 983601, 7931, 7933, 42867, 565, 7536, 7559,
983567, 42868, 42827, 42829, 11386, 983569, 983573, 983571, 42831, 7571, 7575, 42835, 7537, 7560, 42837, 7549,
42833, 42841, 587, 42839, 569, 42843, 7539, 7538, 7561, 589, 983603, 8580, 42815, 7572, 42869, 42845,
7540, 7562, 575, 983575, 42892, 7573, 7454, 7441, 7443, 7442, 7455, 7453, 566, 11366, 7541, 11383,
7546, 42853, 42855, 7446, 42795, 42871, 7426, 7543, 686, 687, 7433, 42879, 42881, 7444, 7432, 11385,
42793, 983609, 983577, 983611, 983605, 983607, 7577, 7531, 42872, 7551, 11380, 42847, 7564, 11377, 42857, 42851,
42849, 11379, 7565, 7935, 591, 11372, 7542, 7566, 576, 8336, 8337, 7522, 11388, 8338, 7523, 8340,
7524, 7525, 8339, 11058, 11056, 9948, 11780, 11816, 11804, 11788, 11020, 11012, 10181, 11814, 11778, 11785,
11808, 4054, 4056, 11082, 11074, 11083, 11070, 11064, 11066, 11065, 11024, 11025, 11013, 11077, 11062, 11061,
11067, 11069, 11068, 11060, 11063, 7213, 7221, 7215, 7214, 7216, 7220, 7217, 7218, 7219, 7240, 7237,
7236, 7241, 7233, 7239, 7238, 7235, 7234, 7232, 7203, 7187, 7188, 7174, 7175, 7180, 7247, 7193,
7185, 7186, 7171, 7172, 7197, 7198, 7176, 7168, 7170, 7169, 7196, 7189, 7190, 7181, 7173, 7177,
7182, 7184, 7183, 7195, 7200, 7201, 7178, 7179, 7191, 7192, 7245, 7246, 7199, 7202, 7194, 7229,
7228, 7227, 7231, 7230, 7223, 7222, 7205, 7204, 7206, 7212, 7207, 7208, 7209, 7210, 7211, 6478,
6475, 6474, 6479, 6471, 6477, 6476, 6473, 6472, 6470, 6468, 6418, 6419, 6406, 6407, 6413, 6414,
6403, 6404, 6428, 6408, 6409, 6401, 6402, 6423, 6420, 6415, 6405, 6416, 6417, 6422, 6427, 6425,
6426, 6411, 6412, 6424, 6421, 6410, 6469, 6458, 6464, 6457, 6459, 6450, 6448, 6456, 6454, 6452,
6449, 6453, 6455, 6451, 6442, 6443, 6441, 6432, 6436, 6438, 6439, 6435, 6433, 6440, 6437, 6434,
6400, 13007, 65664, 65665, 65666, 65667, 65668, 65669, 65670, 65671, 65672, 65673, 65674, 65675, 65676, 65677,
65678, 65679, 65680, 65681, 65682, 65685, 65686, 65687, 65690, 65691, 65692, 65693, 65694, 65695, 65696, 65697,
65698, 65699, 65701, 65702, 65703, 65704, 65705, 65706, 65707, 65708, 65709, 65710, 65711, 65712, 65713, 65714,
65715, 65716, 65717, 65718, 65719, 65720, 65721, 65722, 65723, 65724, 65725, 65726, 65727, 65728, 65729, 65730,
65731, 65732, 65733, 65734, 65735, 65736, 65737, 65738, 65739, 65740, 65741, 65742, 65743, 65744, 65745, 65747,
65748, 65749, 65750, 65751, 65752, 65753, 65754, 65755, 65756, 65757, 65758, 65759, 65760, 65761, 65762, 65763,
65764, 65765, 65766, 65767, 65768, 65769, 65770, 65771, 65772, 65773, 65774, 65775, 65776, 65777, 65778, 65779,
65780, 65781, 65782, 65783, 65784, 65785, 65786, 65683, 65684, 65688, 65689, 65700, 65746, 65541, 65579, 65566,
65587, 65589, 65561, 65543, 65536, 65582, 65540, 65569, 65584, 65557, 65544, 65559, 65571, 65596, 65599, 65573,
65560, 65562, 65600, 65580, 65577, 65538, 65606, 65563, 65581, 65574, 65609, 65549, 65588, 65537, 65568, 65593,
65583, 65594, 65601, 65552, 65542, 65547, 65605, 65570, 65545, 65564, 65578, 65591, 65565, 65546, 65585, 65586,
65576, 65539, 65607, 65550, 65611, 65553, 65610, 65590, 65554, 65603, 65567, 65558, 65597, 65592, 65608, 65551,
65572, 65556, 65555, 65602, 65612, 65604, 65613, 65616, 65617, 65618, 65619, 65620, 65621, 65622, 65623, 65624,
65625, 65626, 65627, 65628, 65629, 42222, 42223, 42192, 42202, 42203, 42195, 42204, 42224, 42225, 42217, 42198,
42221, 42214, 42216, 42226, 42201, 42199, 42200, 42209, 42207, 42208, 42213, 42227, 42231, 42193, 42194, 42210,
42219, 42196, 42197, 42235, 42234, 42237, 42236, 42232, 42233, 42205, 42206, 42228, 42229, 42230, 42218, 42215,
42220, 42212, 42211, 42238, 42239, 8374, 10188, 11059, 66176, 66201, 66178, 66179, 66181, 66177, 66202, 66180,
66203, 66182, 66186, 66187, 66196, 66189, 66190, 66192, 66191, 66193, 66195, 66188, 66197, 66198, 66199, 66185,
66200, 66194, 66183, 66204, 66184, 67872, 67893, 67873, 67897, 67875, 67876, 67894, 67889, 67874, 67878, 67880,
67881, 67895, 67882, 67883, 67896, 67884, 67890, 67885, 67891, 67886, 67887, 67892, 67888, 67877, 67879, 67903,
127016, 127019, 127012, 127013, 126976, 126999, 126990, 127008, 126996, 126987, 127005, 126995, 126986, 127004, 126981, 127018,
127000, 126991, 127009, 126979, 126992, 126983, 127001, 127011, 127010, 126980, 126998, 126989, 127007, 126997, 126988, 127006,
126977, 127014, 127015, 126994, 126985, 127003, 126993, 126984, 127002, 126978, 126982, 127017, 3449, 3444, 3443, 3445,
3455, 3453, 3454, 3451, 3450, 3452, 3441, 3442, 3440, 3389, 3426, 3427, 3396, 9893, 9895, 9894,
9967, 9901, 120778, 120779, 120484, 120485, 10222, 10220, 10223, 10221, 120001, 9899, 9900, 9898, 44013, 44011,
44024, 44021, 44020, 44025, 44017, 44023, 44022, 44019, 44018, 44016, 43985, 43989, 43994, 43974, 43993, 43991,
43992, 43986, 43981, 43983, 44002, 43987, 43990, 43976, 43968, 43995, 43970, 43996, 43971, 43997, 43973, 43999,
43977, 44001, 43972, 43998, 43984, 43988, 43969, 43978, 43975, 44000, 43982, 43979, 43980, 44012, 44005, 44009,
44004, 44010, 44003, 44007, 44008, 44006, 9169, 9170, 9172, 9177, 9171, 9176, 9175, 9174, 9173, 761,
763, 7468, 7469, 7470, 7471, 7472, 7473, 7475, 7476, 7477, 7478, 7479, 7480, 7481, 7482, 7484,
7485, 7486, 7487, 7474, 7483, 7488, 7489, 11389, 7490, 42753, 42757, 42759, 42755, 42752, 42756, 42758,
42754, 42889, 7544, 42777, 42776, 42775, 762, 764, 42765, 42760, 983945, 42770, 42769, 42764, 42774, 4348,
42766, 42761, 42771, 42888, 42768, 42763, 751, 42783, 767, 753, 42773, 754, 755, 759, 752, 42778,
42767, 42762, 42772, 758, 757, 756, 766, 760, 42780, 42781, 42782, 42779, 765, 42890, 7491, 7516,
7493, 7495, 7601, 7517, 7509, 7580, 7581, 7590, 7591, 7595, 7600, 7608, 7521, 7496, 7519, 7585,
7497, 7505, 7604, 7582, 7614, 7584, 7501, 7518, 7520, 7588, 7589, 7592, 7503, 7594, 7593, 7504,
7596, 7598, 7599, 7506, 7499, 7507, 7510, 7602, 7583, 7603, 7498, 7586, 7513, 7511, 7605, 7615,
7508, 7492, 7494, 7579, 7587, 7502, 7514, 7597, 7500, 7610, 7512, 7606, 7607, 7515, 7609, 7611,
7613, 7612, 42784, 42785, 42864, 6314, 119552, 9866, 9867, 9968, 119081, 4158, 4156, 4157, 4155, 4192,
4191, 4190, 4226, 43642, 4208, 4206, 4207, 4159, 43617, 43618, 43624, 43625, 43626, 43631, 43616, 43629,
43630, 43619, 43620, 43627, 43621, 43635, 43628, 43622, 43623, 43633, 43634, 4188, 4189, 4136, 4187, 4186,
4238, 4193, 4130, 4223, 4216, 4219, 4222, 4215, 4225, 4213, 4214, 4220, 4218, 4221, 4224, 4217,
4198, 4197, 43638, 43636, 43637, 43632, 4248, 4245, 4244, 4249, 4241, 4247, 4246, 4243, 4242, 4240,
4154, 4250, 4251, 43643, 4239, 4237, 4235, 4236, 4231, 4232, 4233, 4234, 4201, 4202, 4203, 4204,
4205, 43639, 43640, 43641, 4255, 4254, 4195, 4196, 4252, 4253, 4149, 4209, 4212, 4210, 4211, 4147,
4148, 4194, 4227, 4228, 4229, 4230, 4139, 4199, 4200, 9471, 127319, 127327, 127371, 127353, 127355, 127356,
127359, 127372, 127373, 9906, 6616, 6613, 6612, 6617, 6609, 6615, 6614, 6611, 6610, 6608, 6599, 6598,
6597, 6596, 6595, 6594, 6593, 6562, 6561, 6554, 6560, 6530, 6566, 6556, 6550, 6544, 6532, 6548,
6549, 6528, 6537, 6570, 6542, 6543, 6536, 6555, 6531, 6567, 6538, 6565, 6564, 6557, 6563, 6533,
6568, 6559, 6553, 6547, 6535, 6551, 6552, 6529, 6540, 6571, 6545, 6546, 6539, 6558, 6534, 6569,
6541, 6622, 6623, 6618, 6600, 6601, 6577, 6587, 6582, 6586, 6581, 6578, 6592, 6583, 6584, 6590,
6589, 6579, 6585, 6591, 6580, 6588, 6576, 2035, 2030, 2031, 2032, 2033, 2034, 2027, 2028, 2029,
2040, 1992, 1989, 1988, 1993, 1985, 1991, 1990, 1987, 1986, 1984, 2041, 2036, 2042, 1994, 2003,
2007, 2008, 2001, 1997, 1995, 2013, 2012, 2020, 1996, 2006, 2025, 2024, 2026, 2014, 2015, 2017,
2002, 2019, 2016, 2018, 2023, 2000, 1999, 2004, 2009, 2010, 2011, 2005, 1998, 2021, 2022, 2037,
2039, 2038, 9940, 11016, 11008, 43060, 43057, 43056, 43059, 43058, 43061, 43063, 43065, 43062, 43064, 11017,
11009, 7293, 7256, 7253, 7252, 7257, 7249, 7255, 7254, 7251, 7250, 7248, 7289, 7265, 7264, 7266,
7267, 7260, 7262, 7261, 7259, 7280, 7281, 7279, 7282, 7270, 7271, 7272, 7269, 7258, 7263, 7278,
7268, 7283, 7273, 7285, 7287, 7284, 7286, 7274, 7275, 7276, 7277, 7288, 7290, 7292, 7295, 7294,
7291, 66517, 66513, 66515, 66516, 66514, 66464, 66504, 66505, 66506, 66482, 66510, 66511, 66472, 66477, 66508,
66509, 66478, 66479, 66483, 66469, 66470, 66499, 66465, 66473, 66474, 66467, 66468, 66494, 66486, 66487, 66488,
66484, 66485, 66481, 66492, 66493, 66495, 66497, 66498, 66475, 66480, 66476, 66466, 66490, 66491, 66471, 66507,
66489, 66496, 66512, 68209, 68210, 68200, 68213, 68211, 68217, 68208, 68214, 68212, 68192, 68194, 68203, 68205,
68193, 68195, 68204, 68196, 68199, 68206, 68207, 68202, 68198, 68201, 68215, 68219, 68220, 68197, 68218, 68216,
68222, 68221, 68223, 68608, 68617, 68625, 68619, 68627, 68623, 68634, 68640, 68644, 68668, 68670, 68677, 68632,
68621, 68638, 68643, 68660, 68666, 68669, 68671, 68675, 68630, 68680, 68658, 68641, 68642, 68648, 68653, 68646,
68650, 68655, 68673, 68628, 68611, 68657, 68662, 68614, 68615, 68636, 68656, 68664, 68679, 68609, 68618, 68626,
68610, 68620, 68624, 68635, 68645, 68654, 68678, 68633, 68622, 68639, 68652, 68661, 68667, 68672, 68676, 68631,
68613, 68659, 68649, 68647, 68651, 68674, 68629, 68612, 68663, 68616, 68637, 68665, 11819, 10179, 10180, 10183,
2869, 2929, 2914, 2915, 2884, 66728, 66725, 66724, 66729, 66721, 66727, 66726, 66723, 66722, 66720, 66710,
66715, 66688, 66689, 66699, 66694, 66698, 66711, 66716, 66701, 66700, 66708, 66712, 66691, 66703, 66693, 66704,
66705, 66706, 66713, 66717, 66702, 66695, 66696, 66697, 66690, 66714, 66707, 66692, 66709, 9885, 9908, 11801,
11791, 12830, 12829, 127248, 127249, 127250, 127251, 127252, 127253, 127254, 127255, 127256, 127257, 127258, 127259, 127260,
127261, 127262, 127263, 127264, 127265, 127266, 127267, 127268, 127269, 127270, 127271, 127272, 127273, 12880, 8524, 9854,
10178, 9977, 43125, 43101, 43117, 43120, 43086, 43076, 43123, 43077, 43082, 43115, 43090, 43104, 43110, 43108,
43074, 43109, 43100, 43102, 43078, 43072, 43073, 43097, 43087, 43083, 43075, 43116, 43079, 43105, 43084, 43085,
43106, 43096, 43099, 43098, 43094, 43080, 43081, 43088, 43089, 43113, 43114, 43103, 43119, 43118, 43091, 43107,
43095, 43093, 43092, 43127, 43126, 43124, 43121, 43111, 43112, 43122, 66009, 66033, 66023, 66017, 66010, 66027,
66003, 66018, 66028, 66004, 66012, 66022, 66020, 66045, 66019, 66031, 66030, 66040, 66007, 66041, 66006, 66026,
66025, 66016, 66038, 66013, 66014, 66039, 66036, 66000, 66034, 66001, 66029, 66037, 66015, 66011, 66024, 66021,
66043, 66042, 66002, 66008, 66032, 66035, 66044, 66005, 67855, 67840, 67841, 67843, 67842, 67844, 67847, 67850,
67851, 67852, 67853, 67856, 67858, 67859, 67857, 67854, 67860, 67861, 67848, 67845, 67849, 67846, 67862, 67865,
67863, 67867, 67864, 67866, 67871, 9935, 65043, 65040, 65045, 65049, 65041, 65042, 65095, 65047, 65046, 65096,
983049, 65048, 65044, 9915, 9926, 11783, 11782, 11787, 43346, 43344, 43343, 43345, 43334, 43319, 43321, 43316,
43313, 43329, 43322, 43312, 43326, 43320, 43330, 43317, 43332, 43314, 43331, 43323, 43333, 43318, 43325, 43324,
43315, 43328, 43327, 43359, 43347, 43338, 43340, 43337, 43342, 43341, 43335, 43339, 43336, 9952, 9953, 10184,
11073, 11079, 11793, 11822, 11777, 11776, 11781, 11817, 11805, 11789, 10182, 11815, 11779, 11786, 11809, 4053,
4055, 11080, 11084, 11075, 11076, 11022, 11023, 11078, 11824, 65946, 65947, 65942, 65940, 65945, 8582, 8583,
8584, 8581, 65943, 65938, 65944, 65936, 65939, 65941, 65937, 69223, 69220, 69219, 69224, 69216, 69222, 69221,
69218, 69217, 69243, 69244, 69245, 69246, 69241, 69232, 69229, 69238, 69228, 69237, 69242, 69233, 69234, 69240,
69231, 69239, 69230, 69225, 69227, 69236, 69226, 69235, 9973, 2102, 2048, 2053, 2049, 2051, 2064, 2050,
2063, 2055, 2052, 2058, 2059, 2060, 2061, 2066, 2067, 2068, 2062, 2069, 2056, 2065, 2057, 2054,
2073, 2075, 2070, 2071, 2093, 2072, 2074, 2088, 2084, 2097, 2098, 2110, 2108, 2100, 2099, 2103,
2096, 2105, 2101, 2109, 2107, 2106, 2104, 2083, 2080, 2077, 2090, 2082, 2079, 2076, 2089, 2086,
2091, 2081, 2078, 2085, 2092, 2087, 43188, 43214, 43224, 43221, 43220, 43225, 43217, 43223, 43222, 43219,
43218, 43216, 43215, 43138, 43139, 43150, 43153, 43176, 43177, 43159, 43160, 43171, 43166, 43167, 43172, 43148,
43149, 43156, 43157, 43186, 43140, 43141, 43161, 43162, 43154, 43155, 43181, 43187, 43178, 43173, 43158, 43168,
43163, 43151, 43152, 43174, 43175, 43180, 43185, 43183, 43184, 43169, 43170, 43164, 43165, 43142, 43143, 43182,
43146, 43147, 43144, 43145, 43179, 43136, 43204, 43137, 43189, 43200, 43203, 43198, 43199, 43190, 43191, 43201,
43202, 43192, 43193, 43196, 43197, 43194, 43195, 9878, 9914, 9916, 9913, 9752, 66665, 66673, 66669, 66682,
66680, 66684, 66664, 66679, 66650, 66647, 66651, 66685, 66672, 66663, 66683, 66643, 66652, 66659, 66649, 66686,
66674, 66662, 66657, 66642, 66660, 66656, 66661, 66671, 66676, 66678, 66666, 66677, 66681, 66668, 66640, 66670,
66645, 66646, 66654, 66644, 66641, 66675, 66653, 66658, 66667, 66648, 66687, 66655, 9961, 9975, 42611, 68411,
9924, 9917, 11018, 11010, 11019, 11011, 8375, 13279, 127376, 13175, 13177, 13176, 13005, 13006, 9974, 13311,
13004, 127488, 13178, 13278, 11027, 11029, 11026, 11028, 127529, 127530, 127533, 127508, 127512, 127518, 127520, 127516,
127506, 127534, 127525, 127524, 127509, 127511, 127505, 127532, 127517, 127504, 127537, 127527, 127535, 127528, 127515, 127519,
127513, 127526, 127514, 127522, 127521, 127510, 127523, 127536, 127531, 11820, 127306, 127507, 9919, 127281, 127293, 127295,
127298, 127302, 127307, 127310, 9949, 127308, 127309, 9877, 9882, 9188, 9925, 7073, 7074, 7075, 7096, 7093,
7092, 7097, 7089, 7095, 7094, 7091, 7090, 7088, 7043, 7046, 7064, 7054, 7059, 7048, 7049, 7062,
7052, 7072, 7044, 7055, 7050, 7086, 7068, 7065, 7060, 7053, 7057, 7047, 7061, 7051, 7067, 7070,
7087, 7058, 7045, 7063, 7069, 7071, 7066, 7056, 7082, 7041, 7042, 7040, 7080, 7078, 7081, 7076,
7079, 7077, 10185, 8275, 43008, 43036, 43035, 43021, 43020, 43027, 43026, 43031, 43030, 43012, 43018, 43017,
43042, 43009, 43023, 43022, 43016, 43015, 43039, 43037, 43032, 43013, 43034, 43033, 43038, 43040, 43041, 43029,
43028, 43025, 43024, 43011, 43048, 43049, 43050, 43051, 43019, 43010, 43014, 43043, 43046, 43044, 43047, 43045,
8527, 1837, 1839, 1838, 1871, 1870, 1869, 6499, 6509, 6508, 6507, 6501, 6502, 6492, 6494, 6500,
6480, 6496, 6488, 6491, 6498, 6482, 6505, 6504, 6489, 6490, 6495, 6484, 6486, 6487, 6512, 6513,
6514, 6515, 6516, 6483, 6497, 6503, 6506, 6493, 6481, 6485, 6783, 6749, 6745, 6747, 6743, 6746,
6748, 6742, 6741, 6750, 6792, 6789, 6788, 6793, 6785, 6791, 6790, 6787, 6786, 6784, 6731, 6711,
6703, 6737, 6740, 6695, 6696, 6714, 6729, 6688, 6689, 6690, 6712, 6713, 6702, 6728, 6726, 6727,
6706, 6707, 6720, 6733, 6734, 6723, 6739, 6730, 6697, 6699, 6716, 6732, 6691, 6693, 6692, 6715,
6717, 6704, 6698, 6708, 6709, 6719, 6724, 6718, 6710, 6694, 6700, 6738, 6721, 6705, 6701, 6722,
6735, 6736, 6725, 6829, 6821, 6828, 6820, 6824, 6825, 6819, 6775, 6776, 6777, 6780, 6772, 6744,
6779, 6823, 6778, 6822, 6752, 6826, 6827, 6818, 6773, 6774, 6816, 6817, 6808, 6805, 6804, 6809,
6801, 6807, 6806, 6803, 6802, 6800, 6753, 6755, 6767, 6769, 6766, 6757, 6758, 6754, 6763, 6771,
6764, 6768, 6765, 6756, 6770, 6761, 6759, 6762, 6760, 43675, 43661, 43659, 43667, 43681, 43655, 43693,
43653, 43651, 43649, 43689, 43683, 43657, 43673, 43665, 43695, 43679, 43677, 43687, 43663, 43671, 43669, 43691,
43685, 43674, 43660, 43658, 43666, 43680, 43654, 43692, 43652, 43650, 43648, 43688, 43682, 43656, 43672, 43664,
43694, 43678, 43676, 43686, 43662, 43670, 43668, 43690, 43684, 43696, 43703, 43742, 43743, 43739, 43740, 43741,
43711, 43712, 43714, 43713, 43697, 43710, 43709, 43707, 43708, 43701, 43698, 43704, 43702, 43700, 43706, 43699,
43705, 3064, 983614, 983634, 983630, 983612, 983635, 983624, 983627, 983626, 983621, 983619, 983613, 983617, 983629, 983615,
983620, 983623, 983628, 983633, 983631, 983632, 983618, 983616, 983625, 983622, 3063, 3059, 3062, 3046, 2998, 3060,
3066, 3024, 3065, 983658, 983665, 983668, 983663, 983664, 983659, 983660, 983666, 983667, 983661, 983662, 983878, 983885,
983888, 983883, 983884, 983879, 983880, 983886, 983887, 983881, 983882, 983834, 983841, 983844, 983839, 983840, 983835, 983836,
983842, 983843, 983837, 983838, 983636, 983643, 983646, 983641, 983642, 983637, 983638, 983644, 983645, 983889, 983890, 983897,
983900, 983895, 983896, 983891, 983892, 983898, 983899, 983893, 983894, 983639, 983640, 983768, 983775, 983778, 983773, 983774,
983769, 983770, 983801, 983808, 983811, 983806, 983807, 983802, 983803, 983790, 983797, 983800, 983795, 983796, 983791, 983792,
983798, 983799, 983793, 983794, 983809, 983810, 983804, 983805, 983776, 983777, 983771, 983772, 983735, 983742, 983745, 983740,
983741, 983736, 983737, 983743, 983744, 983738, 983739, 983713, 983720, 983723, 983718, 983719, 983647, 983654, 983657, 983652,
983653, 983648, 983649, 983655, 983656, 983650, 983651, 983714, 983715, 983691, 983698, 983701, 983696, 983697, 983692, 983693,
983823, 983830, 983833, 983828, 983829, 983824, 983825, 983831, 983832, 983826, 983827, 983699, 983700, 983694, 983695, 983721,
983722, 983716, 983717, 983669, 983676, 983679, 983674, 983675, 983670, 983671, 983677, 983678, 983672, 983673, 983724, 983731,
983734, 983729, 983730, 983725, 983726, 983732, 983733, 983727, 983728, 983757, 983764, 983767, 983762, 983763, 983758, 983759,
983765, 983766, 983812, 983819, 983822, 983817, 983818, 983813, 983814, 983820, 983821, 983815, 983816, 983760, 983761, 983867,
983874, 983877, 983872, 983873, 983845, 983852, 983855, 983850, 983851, 983846, 983847, 983853, 983854, 983901, 983848, 983849,
983868, 983869, 983875, 983876, 983856, 983863, 983866, 983861, 983862, 983857, 983858, 983864, 983865, 983859, 983860, 983870,
983871, 983702, 983709, 983712, 983707, 983708, 983703, 983704, 983710, 983711, 983680, 983687, 983690, 983685, 983686, 983681,
983682, 983688, 983689, 983683, 983684, 983705, 983706, 983779, 983786, 983789, 983784, 983785, 983780, 983781, 983787, 983788,
983782, 983783, 983746, 983753, 983756, 983751, 983752, 983747, 983748, 983754, 983755, 983749, 983750, 3061, 3196, 3193,
3198, 3195, 3197, 3194, 3192, 3161, 3160, 3133, 3199, 3170, 3171, 8376, 9978, 119617, 119577, 119633,
119564, 119561, 119587, 119566, 119558, 119585, 119613, 119590, 119631, 119630, 119634, 119608, 119573, 119582, 119563, 119624,
119586, 119567, 119623, 119636, 119612, 119625, 119568, 119619, 119584, 119580, 119618, 119600, 119583, 119603, 119610, 119626,
119632, 119606, 119576, 119638, 119559, 119595, 119592, 119615, 119599, 119602, 119614, 119629, 119574, 119570, 119622, 119581,
119562, 119591, 119637, 119597, 119589, 119616, 119609, 119560, 119635, 119565, 119588, 119604, 119571, 119594, 119572, 119578,
119596, 119579, 119598, 119605, 119627, 119621, 119628, 119601, 119593, 119611, 119607, 119575, 119620, 119569, 10176, 8278,
11057, 9887, 9886, 9928, 3947, 3948, 983047, 4048, 4052, 4051, 4049, 4050, 4046, 11595, 11608, 11585,
11573, 11620, 11607, 11600, 11586, 11582, 11590, 11601, 11592, 11596, 11568, 11588, 11569, 11570, 11614, 11575,
11577, 11578, 11576, 11580, 11571, 11606, 11572, 11584, 11587, 11574, 11581, 11589, 11583, 11597, 11598, 11599,
11602, 11591, 11604, 11605, 11609, 11611, 11610, 11612, 11613, 11615, 11616, 11617, 11618, 11619, 11594, 11621,
11579, 11593, 11603, 11631, 11081, 11806, 11807, 11803, 68410, 9182, 11810, 9180, 11811, 9184, 127553, 127554,
127559, 127555, 127557, 127560, 127552, 127556, 127558, 127274, 8285, 9930, 8526, 9929, 8282, 11818, 66451, 66432,
66433, 66436, 66447, 66434, 66457, 66437, 66440, 66459, 66443, 66435, 66445, 66446, 66448, 66452, 66454, 66455,
66453, 66450, 66444, 66461, 66441, 66456, 66458, 66460, 66438, 66442, 66439, 66449, 66463, 9969, 9748, 9903,
11021, 11797, 11014, 42509, 42536, 42533, 42532, 42537, 42529, 42535, 42534, 42531, 42530, 42528, 42510, 42511,
42313, 42314, 42322, 42474, 42247, 42321, 42473, 42246, 42283, 42434, 42359, 42396, 42284, 42435, 42360, 42397,
42342, 42495, 42266, 42303, 42455, 42379, 42416, 42336, 42489, 42260, 42332, 42485, 42256, 42333, 42486, 42257,
42294, 42446, 42370, 42407, 42293, 42445, 42369, 42406, 42297, 42449, 42373, 42410, 42465, 42240, 42241, 42466,
42328, 42481, 42252, 42289, 42441, 42365, 42402, 42349, 42327, 42479, 42251, 42480, 42288, 42439, 42440, 42364,
42401, 42502, 42272, 42503, 42309, 42461, 42385, 42422, 42316, 42317, 42468, 42242, 42469, 42278, 42279, 42429,
42430, 42355, 42391, 42392, 42276, 42277, 42343, 42496, 42267, 42304, 42456, 42380, 42417, 42346, 42347, 42499,
42270, 42307, 42459, 42383, 42324, 42325, 42476, 42249, 42477, 42286, 42437, 42362, 42399, 42420, 42334, 42487,
42258, 42508, 42295, 42447, 42371, 42408, 42350, 42323, 42475, 42248, 42285, 42436, 42361, 42398, 42504, 42273,
42326, 42478, 42250, 42287, 42438, 42363, 42400, 42310, 42462, 42386, 42423, 42351, 42337, 42490, 42261, 42298,
42450, 42539, 42512, 42513, 42538, 42514, 42374, 42411, 42505, 42274, 42507, 42315, 42467, 42348, 42500, 42271,
42501, 42308, 42460, 42384, 42421, 42428, 42311, 42344, 42497, 42268, 42305, 42457, 42381, 42418, 42463, 42387,
42424, 42352, 42506, 42275, 42312, 42464, 42388, 42425, 42426, 42427, 42353, 42354, 42320, 42472, 42245, 42282,
42433, 42358, 42395, 42335, 42488, 42259, 42296, 42448, 42372, 42409, 42338, 42491, 42262, 42339, 42492, 42263,
42300, 42452, 42376, 42413, 42299, 42451, 42375, 42412, 42330, 42483, 42254, 42331, 42484, 42255, 42292, 42444,
42368, 42405, 42291, 42443, 42367, 42404, 42389, 42390, 42329, 42482, 42253, 42290, 42442, 42366, 42403, 42318,
42319, 42470, 42243, 42244, 42471, 42280, 42281, 42431, 42432, 42356, 42357, 42393, 42394, 42345, 42498, 42269,
42306, 42458, 42382, 42419, 42340, 42493, 42264, 42341, 42494, 42265, 42302, 42454, 42378, 42415, 42301, 42453,
42377, 42414, 42519, 42522, 42526, 42523, 42520, 42515, 42527, 42516, 42524, 42518, 42521, 42517, 42525, 917843,
917844, 917845, 917846, 917847, 917848, 917849, 917850, 917851, 917852, 917853, 917854, 917855, 917856, 917857, 917858, 917859,
917860, 917861, 917862, 917863, 917864, 917865, 917866, 917867, 917868, 917869, 917870, 917871, 917872, 917873, 917874, 917875,
917876, 917877, 917878, 917879, 917880, 917881, 917882, 917883, 917884, 917885, 917886, 917887, 917888, 917889, 917890, 917891,
917892, 917893, 917894, 917895, 917896, 917897, 917898, 917899, 917900, 917901, 917902, 917903, 917904, 917905, 917906, 917907,
917908, 917909, 917910, 917911, 917912, 917760, 917913, 917914, 917915, 917916, 917917, 917918, 917919, 917920, 917921, 917922,
917761, 917923, 917924, 917925, 917926, 917927, 917928, 917929, 917930, 917931, 917932, 917762, 917933, 917934, 917935, 917936,
917937, 917938, 917939, 917940, 917941, 917942, 917763, 917943, 917944, 917945, 917946, 917947, 917948, 917949, 917950, 917951,
917952, 917764, 917953, 917954, 917955, 917956, 917957, 917958, 917959, 917960, 917961, 917962, 917765, 917963, 917964, 917965,
917966, 917967, 917968, 917969, 917970, 917971, 917972, 917766, 917973, 917974, 917975, 917976, 917977, 917978, 917979, 917980,
917981, 917982, 917767, 917983, 917984, 917985, 917986, 917987, 917988, 917989, 917990, 917991, 917992, 917768, 917993, 917994,
917995, 917996, 917997, 917998, 917999, 917769, 917770, 917771, 917772, 917773, 917774, 917775, 917776, 917777, 917778, 917779,
917780, 917781, 917782, 917783, 917784, 917785, 917786, 917787, 917788, 917789, 917790, 917791, 917792, 917793, 917794, 917795,
917796, 917797, 917798, 917799, 917800, 917801, 917802, 917803, 917804, 917805, 917806, 917807, 917808, 917809, 917810, 917811,
917812, 917813, 917814, 917815, 917816, 917817, 917818, 917819, 917820, 917821, 917822, 917823, 917824, 917825, 917826, 917827,
917828, 917829, 917830, 917831, 917832, 917833, 917834, 917835, 917836, 917837, 917838, 917839, 917840, 917841, 917842, 7401,
7402, 7409, 7403, 7404, 7410, 7406, 7407, 7379, 7398, 7396, 7408, 7405, 7397, 7400, 7394, 7395,
7399, 7380, 7393, 7384, 7389, 7386, 7376, 7388, 7378, 7392, 7377, 7391, 7387, 7390, 7381, 7382,
7383, 7385, 10186, 8286, 9168, 9896, 11823, 9910, 8529, 8528, 8530, 8585, 9888, 11071, 9855, 9931,
9921, 9920, 9872, 9983, 11041, 11053, 11036, 9945, 11046, 11048, 11088, 11040, 11092, 11051, 11090, 9186,
10177, 9943, 11055, 11038, 11825, 983048,
]
_pos_to_code = _all_uint32(_pos_to_code)
def pos_to_code(index): return intmask(_pos_to_code[index])

def lookup_charcode(c):
    pos = _charcode_to_pos(c)
    return _inverse_lookup(packed_dawg, pos)

def dawg_lookup(n):
    return pos_to_code(_dawg_lookup(packed_dawg, n))
    
# estimated 0.07 KiB
__charcode_to_pos_564 = [
4863, 4877, 4924, 4813, 4811, 4900, 4645, 4655, 4803, 4693, 4725, 4914, 4968, 4673, 4837, 4653,
4735, 4733, 4665, 4823, 4687, 4857, 4724, 4898, 4715, 4905, 4747, 4964,
]
__charcode_to_pos_564 = _all_ushort(__charcode_to_pos_564)
def _charcode_to_pos_564(index): return intmask(__charcode_to_pos_564[index])
# estimated 0.05 KiB
__charcode_to_pos_751 = [
5670, 5678, 5673, 5675, 5676, 5685, 5684, 5683, 5677, 5687, 5615, 5654, 5616, 5655, 5692, 5686,
5672,
]
__charcode_to_pos_751 = _all_ushort(__charcode_to_pos_751)
def _charcode_to_pos_751(index): return intmask(__charcode_to_pos_751[index])
# estimated 0.05 KiB
__charcode_to_pos_848 = [
982, 972, 941, 992, 971, 985, 984, 986, 932, 872, 940, 993, 936, 935, 938, 939,
]
__charcode_to_pos_848 = _all_ushort(__charcode_to_pos_848)
def _charcode_to_pos_848(index): return intmask(__charcode_to_pos_848[index])
# estimated 0.04 KiB
__charcode_to_pos_880 = [
3849, 3913, 3848, 3912, -1, -1, 3850, 3914, -1, -1, -1, 3918, 3911, 3917,
]
__charcode_to_pos_880 = _all_short(__charcode_to_pos_880)
def _charcode_to_pos_880(index): return intmask(__charcode_to_pos_880[index])
# estimated 0.03 KiB
__charcode_to_pos_1015 = [
3852, 3916, 3853, 3851, 3915, 3910, 3855, 3846, 3854,
]
__charcode_to_pos_1015 = _all_ushort(__charcode_to_pos_1015)
def _charcode_to_pos_1015(index): return intmask(__charcode_to_pos_1015[index])
# estimated 0.04 KiB
__charcode_to_pos_1270 = [
2190, 2243, -1, -1, 2191, 2244, 2192, 2245, 2193, 2246,
]
__charcode_to_pos_1270 = _all_short(__charcode_to_pos_1270)
def _charcode_to_pos_1270(index): return intmask(__charcode_to_pos_1270[index])
# estimated 0.06 KiB
__charcode_to_pos_1296 = [
2207, 2261, 2187, 2240, 2199, 2252, 2208, 2262, 2219, 2273, 2204, 2258, 2218, 2272, 2175, 2228,
2188, 2241, 2189, 2242, 2203, 2257,
]
__charcode_to_pos_1296 = _all_ushort(__charcode_to_pos_1296)
def _charcode_to_pos_1296(index): return intmask(__charcode_to_pos_1296[index])
# estimated 0.08 KiB
__charcode_to_pos_1536 = [
125, 135, 65, 133, -1, -1, 149, 150, 127, 151, 152, 58, -1, 63, 126, 130,
134, 129, 132, 131, 136, 140, 139, 141, 138, 137, 142, -1, -1, -1, 144,
]
__charcode_to_pos_1536 = _all_short(__charcode_to_pos_1536)
def _charcode_to_pos_1536(index): return intmask(__charcode_to_pos_1536[index])
__charcode_to_pos_1622 = (
'\x8fB|\x94\x93\x92\x91\x80@'
)
def _charcode_to_pos_1622(index): return ord(__charcode_to_pos_1622[index])
# estimated 0.12 KiB
__charcode_to_pos_1869 = [
6982, 6981, 6980, 75, 72, 76, 77, 78, 73, 74, 95, 94, 81, 79, 112, 115,
68, 67, 69, 89, 88, 98, 99, 101, 104, 105, 108, 106, 107, 103, 113, 109,
118, 93, 92, 117, 111, 91, 71, 70, 84, 83, 82, 120, 119, 122, 121, 90,
114, 116, 97,
]
__charcode_to_pos_1869 = _all_ushort(__charcode_to_pos_1869)
def _charcode_to_pos_1869(index): return intmask(__charcode_to_pos_1869[index])
# estimated 0.26 KiB
__charcode_to_pos_1984 = [
5994, 5989, 5993, 5992, 5987, 5986, 5991, 5990, 5985, 5988, 5998, 6004, 6008, 6003, 6028, 6022,
6021, 6002, 6016, 5999, 6023, 6027, 6009, 6000, 6001, 6024, 6025, 6026, 6006, 6005, 6013, 6014,
6018, 6015, 6019, 6017, 6007, 6029, 6030, 6020, 6011, 6010, 6012, 5981, 5982, 5983, 5976, 5977,
5978, 5979, 5980, 5975, 5996, 6031, 6033, 6032, 5984, 5995, 5997, -1, -1, -1, -1, -1,
6602, 6604, 6607, 6605, 6610, 6603, 6623, 6609, 6620, 6622, 6611, 6612, 6613, 6614, 6618, 6608,
6606, 6621, 6615, 6616, 6617, 6619, 6626, 6627, 6629, 6624, 6630, 6625, 6653, 6649, 6658, 6652,
6648, 6657, 6651, 6647, 6632, 6659, 6655, 6661, 6631, 6654, 6650, 6656, 6660, 6628, -1, -1,
6640, 6633, 6634, 6638, 6637, 6642, 6601, 6639, 6646, 6641, 6645, 6644, 6636, 6643, 6635,
]
__charcode_to_pos_1984 = _all_short(__charcode_to_pos_1984)
def _charcode_to_pos_1984(index): return intmask(__charcode_to_pos_1984[index])
# estimated 0.03 KiB
__charcode_to_pos_2382 = [
2305, -1, -1, -1, -1, -1, -1, 2304,
]
__charcode_to_pos_2382 = _all_short(__charcode_to_pos_2382)
def _charcode_to_pos_2382(index): return intmask(__charcode_to_pos_2382[index])
# estimated 0.04 KiB
__charcode_to_pos_2417 = [
2300, 2287, -1, -1, -1, -1, -1, -1, 2294, 2291, 2289, 2292, 2290, 2288, 2286,
]
__charcode_to_pos_2417 = _all_short(__charcode_to_pos_2417)
def _charcode_to_pos_2417(index): return intmask(__charcode_to_pos_2417[index])
# estimated 0.03 KiB
__charcode_to_pos_2555 = [
420, -1, -1, -1, -1, -1, 3968, -1, 3970,
]
__charcode_to_pos_2555 = _all_short(__charcode_to_pos_2555)
def _charcode_to_pos_2555(index): return intmask(__charcode_to_pos_2555[index])
# estimated 0.03 KiB
__charcode_to_pos_3059 = [
7243, 7247, 7517, 7244, 7242, 7217, 7250, 7248,
]
__charcode_to_pos_3059 = _all_ushort(__charcode_to_pos_3059)
def _charcode_to_pos_3059(index): return intmask(__charcode_to_pos_3059[index])
# estimated 0.03 KiB
__charcode_to_pos_3192 = [
7524, 7519, 7523, 7521, 7518, 7522, 7520, 7528,
]
__charcode_to_pos_3192 = _all_ushort(__charcode_to_pos_3192)
def _charcode_to_pos_3192(index): return intmask(__charcode_to_pos_3192[index])
# estimated 0.03 KiB
__charcode_to_pos_3389 = [
5529, -1, -1, -1, -1, -1, -1, 5532,
]
__charcode_to_pos_3389 = _all_short(__charcode_to_pos_3389)
def _charcode_to_pos_3389(index): return intmask(__charcode_to_pos_3389[index])
# estimated 0.05 KiB
__charcode_to_pos_3440 = [
5528, 5526, 5527, 5518, 5517, 5519, -1, -1, -1, 5516, 5524, 5523, 5525, 5521, 5522, 5520,
]
__charcode_to_pos_3440 = _all_short(__charcode_to_pos_3440)
def _charcode_to_pos_3440(index): return intmask(__charcode_to_pos_3440[index])
# estimated 0.04 KiB
__charcode_to_pos_4046 = [
7628, -1, 7623, 7626, 7627, 7625, 7624, 6543, 4993, 6544, 4994,
]
__charcode_to_pos_4046 = _all_short(__charcode_to_pos_4046)
def _charcode_to_pos_4046(index): return intmask(__charcode_to_pos_4046[index])
# estimated 0.04 KiB
__charcode_to_pos_4130 = [
5810, -1, -1, -1, -1, -1, 5805, -1, -1, 5878,
]
__charcode_to_pos_4130 = _all_short(__charcode_to_pos_4130)
def _charcode_to_pos_4130(index): return intmask(__charcode_to_pos_4130[index])
# estimated 0.04 KiB
__charcode_to_pos_4147 = [
5871, 5872, 5866, -1, -1, -1, -1, 5840, 5774, 5772, 5773, 5771, 5783,
]
__charcode_to_pos_4147 = _all_short(__charcode_to_pos_4147)
def _charcode_to_pos_4147(index): return intmask(__charcode_to_pos_4147[index])
# estimated 0.15 KiB
__charcode_to_pos_4186 = [
5807, 5806, 5803, 5804, 5777, 5776, 5775, 5809, 5873, 5862, 5863, 5825, 5824, 5879, 5880, 5852,
5853, 5854, 5855, 5856, 5781, 5782, 5780, 5867, 5869, 5870, 5868, 5817, 5818, 5815, 5812, 5823,
5820, 5813, 5819, 5821, 5814, 5811, 5822, 5816, 5778, 5874, 5875, 5876, 5877, 5848, 5849, 5850,
5851, 5846, 5847, 5845, 5808, 5844, 5839, 5834, 5838, 5837, 5832, 5831, 5836, 5835, 5830, 5833,
5841, 5842, 5864, 5865, 5861, 5860,
]
__charcode_to_pos_4186 = _all_ushort(__charcode_to_pos_4186)
def _charcode_to_pos_4186(index): return intmask(__charcode_to_pos_4186[index])
# estimated 0.07 KiB
__charcode_to_pos_4992 = [
3594, 3575, 3574, 3573, 3592, 3525, 3524, 3523, 3593, 3546, 3545, 3544, 3595, 3582, 3581, 3580,
3635, 3627, 3633, 3634, 3629, 3631, 3626, 3630, 3628, 3632,
]
__charcode_to_pos_4992 = _all_ushort(__charcode_to_pos_4992)
def _charcode_to_pos_4992(index): return intmask(__charcode_to_pos_4992[index])
# estimated 0.03 KiB
__charcode_to_pos_5751 = [
556, 557, 558, 559, 560, 554, 555, 553, 487,
]
__charcode_to_pos_5751 = _all_ushort(__charcode_to_pos_5751)
def _charcode_to_pos_5751(index): return intmask(__charcode_to_pos_5751[index])
# estimated 0.04 KiB
__charcode_to_pos_6128 = [
4614, 4607, 4608, 4605, 4606, 4609, 4612, 4613, 4610, 4611,
]
__charcode_to_pos_6128 = _all_ushort(__charcode_to_pos_6128)
def _charcode_to_pos_6128(index): return intmask(__charcode_to_pos_6128[index])
# estimated 0.16 KiB
__charcode_to_pos_6314 = [
5765, -1, -1, -1, -1, -1, 520, 484, 483, 549, 522, 521, 523, 541, 498, 499,
501, 503, 502, 500, 540, 532, 538, 537, 539, 562, 561, 525, 504, 512, 505, 513,
506, 514, 507, 515, 527, 528, 529, 530, 531, 526, 516, 519, 509, 508, 510, 511,
517, 518, 494, 552, 496, 495, 524, 551, 550, 543, 542, 548, 547, 546, 545, 544,
536, 535, 533, 492, 488, 490, 491, 534, 493, 485, 486, 489,
]
__charcode_to_pos_6314 = _all_short(__charcode_to_pos_6314)
def _charcode_to_pos_6314(index): return intmask(__charcode_to_pos_6314[index])
# estimated 0.24 KiB
__charcode_to_pos_6400 = [
5152, 5109, 5110, 5104, 5105, 5114, 5100, 5101, 5107, 5108, 5125, 5121, 5122, 5102, 5103, 5113,
5115, 5116, 5098, 5099, 5112, 5124, 5117, 5111, 5123, 5119, 5120, 5118, 5106, -1, -1, -1,
5143, 5148, 5151, 5147, 5144, 5150, 5145, 5146, 5149, 5142, 5140, 5141, -1, -1, -1, -1,
5132, 5136, 5131, 5139, 5135, 5137, 5134, 5138, 5133, 5129, 5127, 5130, -1, -1, -1, -1,
5128, -1, -1, -1, 5097, 5126, 5096, 5091, 5095, 5094, 5089, 5088, 5093, 5092, 5087, 5090,
6992, 7016, 6997, 7011, 7003, 7017, 7004, 7005, 6994, 7000, 7001, 6995, 6989, 7015, 6990, 7002,
6993, 7012, 6996, 6983, 6991, 6987, 6988, 7013, 6999, 6998, 7014, 6986, 6985, 6984, -1, -1,
7006, 7007, 7008, 7009, 7010,
]
__charcode_to_pos_6400 = _all_short(__charcode_to_pos_6400)
def _charcode_to_pos_6400(index): return intmask(__charcode_to_pos_6400[index])
# estimated 0.61 KiB
__charcode_to_pos_6528 = [
5921, 5943, 5913, 5928, 5918, 5935, 5950, 5940, 5926, 5922, 5930, 5948, 5944, 5952, 5924, 5925,
5917, 5946, 5947, 5939, 5919, 5920, 5916, 5941, 5942, 5938, 5911, 5927, 5915, 5933, 5949, 5937,
5912, 5910, 5909, 5934, 5932, 5931, 5914, 5929, 5936, 5951, 5923, 5945, -1, -1, -1, -1,
5974, 5958, 5963, 5969, 5972, 5962, 5960, 5965, 5966, 5970, 5961, 5959, 5973, 5968, 5967, 5971,
5964, 5908, 5907, 5906, 5905, 5904, 5903, 5902, 5956, 5957, -1, -1, -1, -1, -1, -1,
5901, 5896, 5900, 5899, 5894, 5893, 5898, 5897, 5892, 5895, 5955, -1, -1, -1, 5953, 5954,
4617, 4615, 4618, 4589, 4591, 4620, 4626, 4628, 4622, 4624, 4593, 4599, 4601, 4595, 4597, 4603,
4630, 4616, 4619, 4590, 4592, 4621, 4627, 4629, 4623, 4625, 4594, 4600, 4602, 4596, 4598, 4604,
460, 457, 465, 466, 470, 454, 462, 463, 473, 456, 464, 467, 455, 459, 468, 469,
475, 471, 461, 474, 472, 453, 458, 479, 481, 478, 480, 477, -1, -1, 476, 452,
7047, 7048, 7049, 7068, 7070, 7069, 7081, 7043, 7044, 7064, 7074, 7065, 7082, 7086, 7052, 7040,
7073, 7085, 7056, 7057, 7075, 7076, 7080, 7039, 7050, 7051, 7045, 7071, 7066, 7072, 7079, 7077,
7058, 7084, 7087, 7061, 7078, 7090, 7054, 7055, 7053, 7046, 7063, 7038, 7067, 7059, 7060, 7088,
7089, 7041, 7083, 7062, 7042, 7026, 7025, 7022, 7103, 7020, 7023, 7021, 7024, 7019, 7027, -1,
7108, 7126, 7133, 7127, 7139, 7131, 7132, 7142, 7144, 7141, 7143, 7134, 7136, 7138, 7130, 7128,
7137, 7129, 7140, 7135, 7102, 7112, 7113, 7098, 7099, 7100, 7106, 7104, 7101, -1, -1, 7018,
7037, 7032, 7036, 7035, 7030, 7029, 7034, 7033, 7028, 7031, -1, -1, -1, -1, -1, -1,
7125, 7120, 7124, 7123, 7118, 7117, 7122, 7121, 7116, 7119, -1, -1, -1, -1, -1, -1,
7114, 7115, 7111, 7097, 7094, 7092, 7107, 7105, 7095, 7096, 7109, 7110, 7093, 7091,
]
__charcode_to_pos_6528 = _all_short(__charcode_to_pos_6528)
def _charcode_to_pos_6528(index): return intmask(__charcode_to_pos_6528[index])
# estimated 0.38 KiB
__charcode_to_pos_6912 = [
314, 313, 310, 312, 309, 225, 226, 241, 242, 272, 273, 262, 263, 250, 251, 237,
224, 257, 258, 245, 246, 238, 239, 255, 230, 231, 243, 244, 256, 268, 269, 234,
235, 254, 267, 270, 232, 233, 253, 259, 260, 228, 229, 252, 276, 261, 249, 275,
265, 266, 264, 240, 311, 327, 328, 329, 321, 322, 319, 320, 315, 316, 323, 324,
326, 325, 317, 318, 210, 247, 248, 271, 236, 274, 277, 227, -1, -1, -1, -1,
223, 218, 222, 221, 216, 215, 220, 219, 214, 217, 308, 306, 330, 211, 213, 212,
307, 295, 292, 296, 289, 291, 294, 287, 293, 288, 290, 286, 279, 284, 282, 281,
285, 283, 278, 280, 305, 304, 303, 302, 299, 301, 297, 298, 300, -1, -1, -1,
6923, 6921, 6922, 6888, 6898, 6914, 6889, 6907, 6893, 6894, 6900, 6909, 6896, 6905, 6891, 6899,
6919, 6906, 6913, 6892, 6904, 6908, 6895, 6915, 6890, 6903, 6918, 6910, 6902, 6916, 6911, 6917,
6897, 6875, 6876, 6877, 6927, 6929, 6925, 6928, 6924, 6926, 6920, -1, -1, -1, 6901, 6912,
6887, 6882, 6886, 6885, 6880, 6879, 6884, 6883, 6878, 6881,
]
__charcode_to_pos_6912 = _all_short(__charcode_to_pos_6912)
def _charcode_to_pos_6912(index): return intmask(__charcode_to_pos_6912[index])
# estimated 0.27 KiB
__charcode_to_pos_7168 = [
5047, 5049, 5048, 5042, 5043, 5054, 5035, 5036, 5046, 5055, 5062, 5063, 5037, 5053, 5056, 5058,
5057, 5040, 5041, 5033, 5034, 5051, 5052, 5064, 5065, 5039, 5070, 5059, 5050, 5044, 5045, 5068,
5060, 5061, 5069, 5032, 5079, 5078, 5080, 5082, 5083, 5084, 5085, 5086, 5081, 5013, 5016, 5015,
5017, 5019, 5020, 5021, 5018, 5014, 5077, 5076, -1, -1, -1, 5073, 5072, 5071, 5075, 5074,
5031, 5026, 5030, 5029, 5024, 5023, 5028, 5027, 5022, 5025, -1, -1, -1, 5066, 5067, 5038,
6059, 6054, 6058, 6057, 6052, 6051, 6056, 6055, 6050, 6053, 6077, 6068, 6065, 6067, 6066, 6078,
6062, 6061, 6063, 6064, 6080, 6076, 6073, 6074, 6075, 6082, 6087, 6088, 6089, 6090, 6079, 6071,
6069, 6070, 6072, 6081, 6085, 6083, 6086, 6084, 6091, 6060, 6092, 6096, 6093, 6049, 6095, 6094,
]
__charcode_to_pos_7168 = _all_short(__charcode_to_pos_7168)
def _charcode_to_pos_7168(index): return intmask(__charcode_to_pos_7168[index])
# estimated 0.08 KiB
__charcode_to_pos_7376 = [
8310, 8314, 8312, 8295, 8305, 8318, 8319, 8320, 8307, 8321, 8309, 8316, 8311, 8308, 8317, 8315,
8313, 8306, 8302, 8303, 8297, 8300, 8296, 8304, 8301, 8287, 8288, 8290, 8291, 8299, 8293, 8294,
8298, 8289, 8292,
]
__charcode_to_pos_7376 = _all_ushort(__charcode_to_pos_7376)
def _charcode_to_pos_7376(index): return intmask(__charcode_to_pos_7376[index])
# estimated 0.47 KiB
__charcode_to_pos_7424 = [
4756, 4757, 4934, 4758, 4759, 4760, 4762, 4761, 4942, 4938, 4765, 4766, 4767, 4768, 4773, 4769,
4770, 4919, 4921, 4920, 4941, 4771, 4931, 4801, 4772, 4774, 4779, 4777, 4780, 4923, 4918, 4922,
4781, 4782, 4783, 4763, 4784, 4755, 3898, 3899, 3900, 3902, 3901, 2226, 5617, 5618, 5619, 5620,
5621, 5622, 5635, 5623, 5624, 5625, 5626, 5627, 5628, 5629, 5630, 5636, 5631, 5632, 5633, 5634,
5637, 5638, 5640, 5694, 5745, 5696, 5746, 5697, 5709, 5712, 5738, 5732, 5752, 5718, 5749, 5724,
5727, 5713, 5731, 5733, 5744, 5700, 5734, 5741, 5754, 5740, 5750, 5757, 5695, 5699, 5719, 5710,
5720, 5708, 4971, 4974, 4976, 4977, 3919, 3921, 3923, 3922, 3920, 4951, 4799, 4809, 4833, 4871,
4878, 4892, 4903, 4902, 4912, 4926, 4966, 4935, 5650, 4850, 4928, 4785, 4854, 4895, 4786, 4953,
4800, 4810, 4834, 4835, 4860, 4866, 4872, 4879, 4893, 4904, 4913, 4829, 4956, 4962, 4967, 4790,
4793, 4808, 4822, 4889, 4909, 4917, 4847, 4890, 4830, 4950, 4832, 5747, 5701, 5702, 5715, 5736,
5717, 5711, 5739, 5748, 5721, 5722, 5703, 5704, 5723, 5726, 5725, 5705, 5728, 5751, 5729, 5730,
5706, 5698, 5735, 5737, 5714, 5742, 5755, 5756, 5707, 5758, 5753, 5759, 5761, 5760, 5716, 5743,
934, 933, 988, 989, 977, 943, 979, 869, 942, 868, 965, 873, 978, 937, 980, 994,
947, 990, 991, 958, 953, 954, 955, 956, 960, 957, 959, 948, 961, 962, 949, 950,
964, 951, 952, 966, 967, 963, 968,
]
__charcode_to_pos_7424 = _all_ushort(__charcode_to_pos_7424)
def _charcode_to_pos_7424(index): return intmask(__charcode_to_pos_7424[index])
# estimated 0.05 KiB
__charcode_to_pos_8275 = [
6931, 4268, 3645, 7615, -1, 3649, 3640, 7708, 3648, 2432, 7704, 8323, -1, -1, -1, -1,
-1, 4269,
]
__charcode_to_pos_8275 = _all_short(__charcode_to_pos_8275)
def _charcode_to_pos_8275(index): return intmask(__charcode_to_pos_8275[index])
# estimated 0.03 KiB
__charcode_to_pos_8370 = [
3962, 154, 4174, 614, 5413, 6806, 7531,
]
__charcode_to_pos_8370 = _all_ushort(__charcode_to_pos_8370)
def _charcode_to_pos_8370(index): return intmask(__charcode_to_pos_8370[index])
# estimated 0.03 KiB
__charcode_to_pos_8524 = [
6334, 59, 7706, 6976, 8329, 8328, 8330,
]
__charcode_to_pos_8524 = _all_ushort(__charcode_to_pos_8524)
def _charcode_to_pos_8524(index): return intmask(__charcode_to_pos_8524[index])
# estimated 0.07 KiB
__charcode_to_pos_9167 = [
3517, 8324, 5606, 5607, 5610, 5608, 5614, 5613, 5612, 5611, 5609, 2444, 3652, 7691, 449, 7689,
447, 7693, 451, 8351, 423, 6873, 3642, 0, 3518, 2278,
]
__charcode_to_pos_9167 = _all_ushort(__charcode_to_pos_9167)
def _charcode_to_pos_9167(index): return intmask(__charcode_to_pos_9167[index])
# estimated 0.25 KiB
__charcode_to_pos_9866 = [
5767, 5768, 2324, 2329, 2328, 2325, 8338, 427, 3972, 62, 1135, 6871, 6743, 60, 3644, 3653,
6872, 153, 3643, 6301, 7618, 7617, 8332, 4169, 2439, 2440, 4266, 5533, 5535, 5534, 8325, 4172,
5549, 5547, 5548, 5537, 2331, 7743, 867, 3651, 5891, 615, 6302, 4362, 8327, 700, 435, 6746,
6744, 6483, 6745, 6801, 419, 6860, 8337, 8336, 426, 425, 6800, 6874, 6484, 441, 7619, 7707,
7705, 8335, 1136, 2330, -1, 6469, 563, 4104, 703, 616, 6034, 61, 443, 8353, 432, 8343,
2443, 4098, 4981, 6868, 3637, 442, 6525, 6526, -1, 4093, -1, -1, -1, -1, 424, 6796,
701, 613, 4170, 3655, 3654, 5536, 5769, 7741, 3647, 3641, 3638, 6600, 6814, 6797, 4177, 6337,
7532, 4270, 4090, 3650, 2119, 8339,
]
__charcode_to_pos_9866 = _all_short(__charcode_to_pos_9866)
def _charcode_to_pos_9866(index): return intmask(__charcode_to_pos_9866[index])
# estimated 0.04 KiB
__charcode_to_pos_10176 = [
7614, 8352, 6336, 6253, 6254, 4988, 6538, 6255, 6527, 6930, 8322, -1, 5414,
]
__charcode_to_pos_10176 = _all_short(__charcode_to_pos_10176)
def _charcode_to_pos_10176(index): return intmask(__charcode_to_pos_10176[index])
# estimated 0.19 KiB
__charcode_to_pos_11008 = [
6036, 6048, 6803, 6805, 4987, 5004, 7746, 2442, 6035, 6047, 6802, 6804, 4986, 7744, 6549, 6550,
5002, 5003, 6822, 6820, 6823, 6821, 2307, 2308, 2309, 2306, 2435, 431, 8342, 445, 8355, 436,
8347, 8340, 428, 4171, 430, 433, 8344, 434, 8345, 438, 439, 8349, 429, 8341, 444, 8354,
4980, 7616, 4979, 5415, 5011, 5007, 5006, 5012, 4999, 5001, 5000, 5008, 5010, 5009, 4998, 8333,
3519, 6528, 4996, 6547, 6548, 5005, 6551, 6529, 6545, 7684, 4995, 4997, 6546, -1, -1, -1,
8346, 440, 8350, 437, 8348, 4096, 4097, 4092, 4091, 4094,
]
__charcode_to_pos_11008 = _all_short(__charcode_to_pos_11008)
def _charcode_to_pos_11008(index): return intmask(__charcode_to_pos_11008[index])
# estimated 0.49 KiB
__charcode_to_pos_11264 = [
3697, 3699, 3735, 3706, 3702, 3739, 3743, 3703, 3742, 3712, 3709, 3708, 3701, 3714, 3716, 3717,
3718, 3719, 3722, 3723, 3727, 3733, 3734, 3705, 3707, 3720, 3721, 3725, 3732, 3700, 3724, 3738,
3737, 3736, 3730, 3741, 3728, 3729, 3740, 3711, 3698, 3710, 3704, 3713, 3726, 3731, 3715, -1,
3744, 3746, 3782, 3753, 3749, 3786, 3790, 3750, 3789, 3759, 3756, 3755, 3748, 3761, 3763, 3764,
3765, 3766, 3769, 3770, 3774, 3780, 3781, 3752, 3754, 3767, 3768, 3772, 3779, 3747, 3771, 3785,
3784, 3783, 3777, 3788, 3775, 3776, 3787, 3758, 3745, 3757, 3751, 3760, 3773, 3778, 3762, -1,
4694, 4864, 4696, 4710, 4716, 4791, 4925, 4674, 4838, 4689, 4858, 4748, 4965, 4647, 4698, 4729,
4730, 4957, 4745, 4961, 4954, 4675, 4839, 4927, 4819, 4943, 4884, 4778, 4972, 5639, 4720, 4749,
996, 1058, 1045, 1107, 1009, 1071, 1002, 1064, 1007, 1069, 1041, 1103, 1046, 1108, 1010, 1072,
1043, 1105, 1011, 1073, 1012, 1074, 1016, 1078, 1017, 1079, 1018, 1080, 1014, 1076, 1019, 1081,
1036, 1098, 1038, 1100, 1040, 1102, 1042, 1104, 1044, 1106, 1008, 1070, 1013, 1075, 1037, 1099,
1035, 1097, 1003, 1065, 1020, 1082, 998, 1060, 1005, 1067, 1006, 1068, 1000, 1062, 1028, 1090,
1039, 1101, 997, 1059, 1029, 1091, 1022, 1084, 995, 1057, 1004, 1066, 1027, 1089, 1024, 1086,
1015, 1077, 1026, 1088, 1025, 1087, 1023, 1085, 1021, 1083, 1030, 1092, 1033, 1095, 1031, 1093,
1032, 1094, 1034, 1096, 1109, 1111, 1112, 1114, 1115, 1110, 1113, 1001, 1063, 999, 1061, 1047,
1048, 1049,
]
__charcode_to_pos_11264 = _all_short(__charcode_to_pos_11264)
def _charcode_to_pos_11264(index): return intmask(__charcode_to_pos_11264[index])
# estimated 0.1 KiB
__charcode_to_pos_11513 = [
1054, 1053, 1055, 1056, 1050, 1051, 1052, 3659, 3660, 3667, 3665, 3666, 3692, 3695, 3689, 3674,
3677, 3679, 3680, 3681, 3682, 3683, 3696, 3686, 3687, 3690, 3691, 3684, 3678, 3668, 3685, 3688,
3663, 3661, 3676, 3664, 3662, 3694, 3675, 3669, 3671, 3672, 3693, 3670, 3673,
]
__charcode_to_pos_11513 = _all_ushort(__charcode_to_pos_11513)
def _charcode_to_pos_11513(index): return intmask(__charcode_to_pos_11513[index])
# estimated 0.12 KiB
__charcode_to_pos_11568 = [
7642, 7644, 7645, 7652, 7654, 7632, 7657, 7647, 7650, 7648, 7649, 7680, 7651, 7658, 7637, 7660,
7655, 7631, 7636, 7656, 7643, 7659, 7638, 7665, 7640, 7681, 7678, 7629, 7641, 7661, 7662, 7663,
7635, 7639, 7664, 7682, 7666, 7667, 7653, 7634, 7630, 7668, 7670, 7669, 7671, 7672, 7646, 7673,
7674, 7675, 7676, 7677, 7633, 7679,
]
__charcode_to_pos_11568 = _all_ushort(__charcode_to_pos_11568)
def _charcode_to_pos_11568(index): return intmask(__charcode_to_pos_11568[index])
# estimated 0.06 KiB
__charcode_to_pos_11648 = [
3571, 3572, 3591, 3597, 3596, 3522, 3606, 3541, 3576, 3577, 3552, 3618, 3543, 3542, 3562, 3605,
3540, 3578, 3579, 3547, 3551, 3550, 3549,
]
__charcode_to_pos_11648 = _all_ushort(__charcode_to_pos_11648)
def _charcode_to_pos_11648(index): return intmask(__charcode_to_pos_11648[index])
# estimated 0.3 KiB
__charcode_to_pos_11680 = [
3598, 3604, 3602, 3599, 3601, 3600, 3603, -1, 3526, 3539, 3537, 3527, 3529, 3528, 3538, -1,
3619, 3625, 3623, 3620, 3622, 3621, 3624, -1, 3530, 3536, 3534, 3531, 3533, 3532, 3535, -1,
3584, 3590, 3588, 3585, 3587, 3586, 3589, -1, 3564, 3570, 3568, 3565, 3567, 3566, 3569, -1,
3610, 3616, 3614, 3611, 3613, 3612, 3615, -1, 3554, 3560, 3558, 3555, 3557, 3556, 3559, -1,
878, 904, 890, 881, 908, 907, 895, 883, 884, 885, 898, 899, 886, 887, 902, 891,
903, 880, 900, 901, 889, 888, 877, 892, 882, 897, 905, 906, 893, 896, 879, 894,
6533, 6532, 4990, 6540, 4982, 6534, 6486, 6485, 2436, 4991, 6541, 6487, 4985, 6537, 2445, 6304,
3646, 6530, 4176, 2433, 2441, 7745, 2434, 2437, 4267, 6303, 4175, 7687, 4984, 6536, 7685, 7686,
4992, 6542, 7690, 7692, 448, 450, 4989, 6539, 4983, 6535, 7709, 6252, 6857, 3639, 6531, 8326,
6552, 8356,
]
__charcode_to_pos_11680 = _all_short(__charcode_to_pos_11680)
def _charcode_to_pos_11680(index): return intmask(__charcode_to_pos_11680[index])
# estimated 0.09 KiB
__charcode_to_pos_12736 = [
863, 865, 866, 831, 857, 843, 839, 835, 842, 861, 840, 844, 836, 841, 845, 847,
833, 853, 848, 855, 832, 838, 834, 860, 859, 856, 854, 849, 851, 864, 862, 858,
837, 846, 850, 852,
]
__charcode_to_pos_12736 = _all_ushort(__charcode_to_pos_12736)
def _charcode_to_pos_12736(index): return intmask(__charcode_to_pos_12736[index])
# estimated 0.04 KiB
__charcode_to_pos_12868 = [
707, 705, 708, 706, 718, 720, 719, 715, 714, 717, 716, 713, 6333,
]
__charcode_to_pos_12868 = _all_ushort(__charcode_to_pos_12868)
def _charcode_to_pos_12868(index): return intmask(__charcode_to_pos_12868[index])
# estimated 0.14 KiB
__charcode_to_pos_19904 = [
4156, 4162, 4118, 4168, 4166, 4112, 4152, 4130, 4148, 4165, 4141, 4150, 4122, 4126, 4136, 4121,
4123, 4167, 4107, 4113, 4109, 4125, 4149, 4145, 4134, 4129, 4137, 4128, 4151, 4155, 4132, 4120,
4144, 4127, 4142, 4114, 4157, 4139, 4138, 4116, 4115, 4131, 4110, 4111, 4124, 4143, 4140, 4164,
4146, 4154, 4153, 4160, 4117, 4161, 4105, 4163, 4158, 4159, 4119, 4135, 4133, 4147, 4106, 4108,
]
__charcode_to_pos_19904 = _all_ushort(__charcode_to_pos_19904)
def _charcode_to_pos_19904(index): return intmask(__charcode_to_pos_19904[index])
# estimated 0.7 KiB
__charcode_to_pos_42192 = [
5367, 5389, 5390, 5370, 5393, 5394, 5375, 5381, 5382, 5380, 5368, 5369, 5371, 5401, 5402, 5384,
5385, 5383, 5391, 5410, 5409, 5386, 5377, 5407, 5378, 5374, 5406, 5392, 5408, 5376, 5365, 5366,
5372, 5373, 5379, 5387, 5403, 5404, 5405, 5388, 5399, 5400, 5396, 5395, 5398, 5397, 5411, 5412,
7805, 7806, 7835, 8002, 8003, 7950, 7767, 7764, 7881, 7863, 7890, 7818, 7810, 7994, 7978, 7981,
7788, 7791, 7872, 7957, 7785, 7902, 7964, 7967, 8022, 8025, 7778, 7848, 7929, 8015, 7856, 7919,
7826, 7887, 7913, 7939, 7844, 7845, 7837, 7838, 8005, 8006, 7951, 7768, 7772, 7882, 7865, 7891,
7820, 7811, 7995, 7986, 7982, 7796, 7792, 7874, 7958, 7800, 7903, 7972, 7968, 8030, 8026, 7779,
7849, 7930, 8016, 7857, 7921, 7828, 7895, 7926, 7940, 7760, 7761, 7915, 7832, 7833, 7999, 8000,
7948, 7765, 7762, 7879, 7860, 7861, 7888, 7816, 7808, 7992, 7976, 7979, 7786, 7789, 7870, 7955,
7783, 7900, 7962, 7965, 8020, 8023, 7776, 7846, 7927, 8013, 7853, 7854, 7917, 7815, 7878, 7899,
7937, 7946, 7947, 7841, 8009, 8010, 7953, 7770, 7774, 7884, 7867, 7893, 7823, 7813, 7997, 7988,
7984, 7798, 7794, 7876, 7960, 7802, 7910, 7974, 7970, 8032, 8028, 7781, 7851, 7932, 8018, 7859,
7923, 7830, 7897, 7935, 7942, 7990, 7991, 7842, 7843, 8011, 8012, 7954, 7771, 7775, 7885, 7868,
7894, 7824, 7814, 7998, 7989, 7985, 7799, 7795, 7877, 7961, 7803, 7911, 7975, 7971, 8033, 8029,
7782, 7852, 7933, 8019, 7869, 7924, 7831, 7898, 7936, 7943, 7944, 7945, 7925, 7839, 7840, 8007,
8008, 7952, 7769, 7773, 7883, 7866, 7892, 7821, 7822, 7812, 7996, 7987, 7983, 7797, 7793, 7875,
7959, 7801, 7904, 7973, 7969, 8031, 8027, 7780, 7850, 7931, 8017, 7858, 7922, 7829, 7896, 7934,
7941, 7804, 7807, 7916, 7834, 7836, 8001, 8004, 7949, 7766, 7763, 7880, 7862, 7864, 7889, 7817,
7819, 7809, 7993, 7977, 7980, 7787, 7790, 7871, 7956, 7784, 7901, 7963, 7966, 8021, 8024, 7777,
7847, 7928, 8014, 7855, 7918, 7920, 7825, 7827, 7886, 7912, 7938, 7914, 7873, 7747, 7758, 7759,
7906, 7907, 7909, 8039, 8041, 8045, 8043, 8034, 8038, 8044, 8035, 8037, 8042, 8046, 8036, 8040,
7757, 7752, 7756, 7755, 7750, 7749, 7754, 7753, 7748, 7751, 7908, 7905,
]
__charcode_to_pos_42192 = _all_ushort(__charcode_to_pos_42192)
def _charcode_to_pos_42192(index): return intmask(__charcode_to_pos_42192[index])
# estimated 0.12 KiB
__charcode_to_pos_42560 = [
2222, 2276, 2184, 2237, 2205, 2259, 2195, 2248, 2181, 2234, 2201, 2254, 2178, 2231, 2202, 2255,
2220, 2274, 2198, 2251, 2206, 2260, 2196, 2249, 2180, 2233, 2177, 2230, 2197, 2250, 2221, 2275,
-1, -1, 2210, 2264, 2211, 2265, 2212, 2266, 2200, 2253, 2176, 2229, 2182, 2235, 2225, 913,
911, 875, 912, 6798,
]
__charcode_to_pos_42560 = _all_short(__charcode_to_pos_42560)
def _charcode_to_pos_42560(index): return intmask(__charcode_to_pos_42560[index])
# estimated 0.07 KiB
__charcode_to_pos_42620 = [
876, 909, 2224, 2227, 2183, 2236, 2185, 2238, 2223, 2277, 2179, 2232, 2186, 2239, 2214, 2268,
2217, 2271, 2216, 2270, 2215, 2269, 2213, 2267, 2194, 2247, 2209, 2263,
]
__charcode_to_pos_42620 = _all_ushort(__charcode_to_pos_42620)
def _charcode_to_pos_42620(index): return intmask(__charcode_to_pos_42620[index])
# estimated 0.19 KiB
__charcode_to_pos_42656 = [
336, 343, 410, 352, 337, 391, 406, 383, 382, 342, 354, 384, 395, 394, 355, 363,
405, 369, 374, 359, 404, 367, 400, 403, 399, 398, 353, 345, 381, 380, 376, 414,
402, 415, 413, 377, 346, 386, 375, 378, 389, 412, 385, 339, 396, 358, 365, 373,
393, 390, 344, 372, 371, 370, 401, 388, 341, 340, 411, 368, 356, 387, 357, 348,
362, 392, 364, 360, 409, 347, 366, 361, 408, 351, 407, 379, 397, 338, 350, 349,
332, 333, 416, 335, 331, 334, 418, 417,
]
__charcode_to_pos_42656 = _all_ushort(__charcode_to_pos_42656)
def _charcode_to_pos_42656(index): return intmask(__charcode_to_pos_42656[index])
# estimated 0.29 KiB
__charcode_to_pos_42752 = [
5645, 5641, 5648, 5644, 5646, 5642, 5647, 5643, 5657, 5665, 5681, 5669, 5661, 5656, 5664, 5680,
5668, 5660, 5659, 5666, 5682, 5674, 5662, 5653, 5652, 5651, 5679, 5691, 5688, 5689, 5690, 5671,
5762, 5763, 4670, 4828, 4669, 4827, 4676, 4840, 4734, 4944, 4728, 4932, 4657, 4805, 4658, 4806,
4764, 4776, 4646, 4792, 4648, 4794, 4649, 4795, 4650, 4796, 4651, 4797, 4652, 4798, 4718, 4908,
4691, 4861, 4690, 4859, 4692, 4862, 4654, 4802, 4695, 4865, 4702, 4882, 4703, 4883, 4707, 4888,
4711, 4896, 4708, 4891, 4709, 4894, 4713, 4899, 4712, 4897, 4714, 4901, 4719, 4911, 4741, 4955,
4744, 4960, 4743, 4959, 4726, 4929, 4727, 4930, 4742, 4958, 4671, 4831, 4686, 4855, 4656, 4804,
5764, 4814, 4870, 4876, 4881, 4910, 4775, 4933, 4952, 4680, 4848, 4681, 4849, 4682, 4731, 4939,
4732, 4940, 4683, 4851, 4684, 4852, 4685, 4853, 5667, 5649, 5693, 4722, 4916,
]
__charcode_to_pos_42752 = _all_ushort(__charcode_to_pos_42752)
def _charcode_to_pos_42752(index): return intmask(__charcode_to_pos_42752[index])
# estimated 0.26 KiB
__charcode_to_pos_43003 = [
4753, 4754, 4752, 4751, 4750, 6932, 6945, 6969, 6963, 6941, 6953, 6970, 6949, 6948, 6943, 6942,
6968, 6936, 6935, 6947, 6946, 6962, 6961, 6938, 6937, 6960, 6959, 6940, 6939, 6952, 6955, 6954,
6934, 6933, 6951, 6956, 6950, 6957, 6958, 6944, 6971, 6973, 6975, 6972, 6974, 6964, 6965, 6966,
6967, -1, -1, -1, -1, 6039, 6038, 6041, 6040, 6037, 6042, 6045, 6043, 6046, 6044, -1,
-1, -1, -1, -1, -1, 6357, 6358, 6352, 6362, 6343, 6345, 6356, 6364, 6373, 6374, 6346,
6361, 6366, 6367, 6342, 6360, 6375, 6376, 6348, 6382, 6386, 6385, 6372, 6384, 6369, 6359, 6371,
6370, 6354, 6339, 6355, 6379, 6349, 6365, 6368, 6383, 6351, 6353, 6350, 6391, 6392, 6377, 6378,
6347, 6363, 6340, 6381, 6380, 6341, 6390, 6393, 6344, 6389, 6338, 6388, 6387,
]
__charcode_to_pos_43003 = _all_short(__charcode_to_pos_43003)
def _charcode_to_pos_43003(index): return intmask(__charcode_to_pos_43003[index])
# estimated 0.15 KiB
__charcode_to_pos_43136 = [
6725, 6727, 6675, 6676, 6692, 6693, 6717, 6718, 6722, 6723, 6720, 6721, 6687, 6688, 6677, 6705,
6706, 6678, 6696, 6697, 6689, 6690, 6702, 6681, 6682, 6694, 6695, 6704, 6715, 6716, 6684, 6685,
6703, 6713, 6714, 6683, 6686, 6701, 6707, 6708, 6679, 6680, 6700, 6724, 6709, 6698, 6719, 6711,
6712, 6710, 6691, 6699, 6662, 6728, 6733, 6734, 6737, 6738, 6741, 6742, 6739, 6740, 6731, 6732,
6729, 6735, 6736, 6730, 6726,
]
__charcode_to_pos_43136 = _all_ushort(__charcode_to_pos_43136)
def _charcode_to_pos_43136(index): return intmask(__charcode_to_pos_43136[index])
# estimated 0.28 KiB
__charcode_to_pos_43214 = [
6663, 6674, 6673, 6668, 6672, 6671, 6666, 6665, 6670, 6669, 6664, 6667, -1, -1, -1, -1,
-1, -1, 923, 918, 922, 921, 916, 915, 920, 919, 914, 917, 924, 929, 925, 926,
927, 928, 930, 931, 2303, 2298, 2299, 2297, 2296, 2295, 2302, 2284, 2283, 2285, -1, -1,
-1, -1, 4446, 4441, 4445, 4444, 4439, 4438, 4443, 4442, 4437, 4440, 4455, 4456, 4451, 4460,
4467, 4468, 4474, 4461, 4469, 4453, 4459, 4464, 4465, 4458, 4450, 4448, 4466, 4473, 4457, 4472,
4470, 4452, 4471, 4449, 4447, 4462, 4454, 4463, 4484, 4480, 4483, 4481, 4482, 4479, 4477, 4478,
4475, 4476, 6499, 6496, 6505, 6512, 6495, 6503, 6509, 6493, 6501, 6494, 6498, 6507, 6511, 6510,
6500, 6514, 6513, 6497, 6502, 6506, 6504, 6508, 6492, 6522, 6524, 6519, 6517, 6523, 6518, 6521,
6520, 6490, 6489, 6491, 6488, 6516,
]
__charcode_to_pos_43214 = _all_short(__charcode_to_pos_43214)
def _charcode_to_pos_43214(index): return intmask(__charcode_to_pos_43214[index])
# estimated 0.27 KiB
__charcode_to_pos_43359 = [
6515, 4003, 4004, 4006, 4002, 3990, 3994, 3997, 3996, 3991, 3992, 3995, 3988, 3993, 3987, 3989,
3977, 3979, 3978, 3986, 3985, 3984, 3999, 3975, 3974, 3998, 4000, 3983, 3973, 4001, -1, -1,
-1, 4350, 4347, 4349, 4351, 4285, 4300, 4299, 4301, 4329, 4318, 4312, 4313, 4295, 4286, 4316,
4304, 4306, 4305, 4296, 4297, 4311, 4289, 4290, 4302, 4315, 4303, 4314, 4327, 4328, 4293, 4294,
4310, 4325, 4326, 4291, 4292, 4309, 4317, 4319, 4287, 4288, 4308, 4331, 4320, 4321, 4307, 4330,
4324, 4323, 4322, 4298, 4348, 4358, 4359, 4360, 4361, 4355, 4356, 4357, 4353, 4354, 4272, 4273,
4271, 4344, 4284, 4346, 4334, 4339, 4337, 4343, 4340, 4336, 4338, 4332, 4333, 4341, 4352, -1,
4345, 4283, 4278, 4282, 4281, 4276, 4275, 4280, 4279, 4274, 4277, -1, -1, -1, -1, 4342,
4335,
]
__charcode_to_pos_43359 = _all_short(__charcode_to_pos_43359)
def _charcode_to_pos_43359(index): return intmask(__charcode_to_pos_43359[index])
# estimated 0.12 KiB
__charcode_to_pos_43520 = [
634, 659, 683, 644, 635, 674, 662, 663, 656, 657, 669, 668, 639, 640, 660, 661,
672, 670, 671, 681, 682, 641, 643, 673, 667, 642, 675, 677, 676, 636, 638, 666,
665, 637, 685, 678, 664, 684, 680, 679, 658, 690, 694, 695, 693, 698, 697, 696,
691, 692, 699, 623, 621, 620, 622,
]
__charcode_to_pos_43520 = _all_ushort(__charcode_to_pos_43520)
def _charcode_to_pos_43520(index): return intmask(__charcode_to_pos_43520[index])
# estimated 0.27 KiB
__charcode_to_pos_43584 = [
647, 646, 650, 619, 645, 654, 649, 651, 655, 652, 648, 653, 618, 617, -1, -1,
633, 628, 632, 631, 626, 625, 630, 629, 624, 627, -1, -1, 688, 686, 687, 689,
5790, 5784, 5785, 5793, 5794, 5796, 5799, 5800, 5786, 5787, 5788, 5795, 5798, 5791, 5792, 5789,
5829, 5801, 5802, 5797, 5827, 5828, 5826, 5857, 5858, 5859, 5779, 5843, -1, -1, -1, -1,
7178, 7154, 7177, 7153, 7176, 7152, 7174, 7150, 7181, 7157, 7171, 7147, 7170, 7146, 7188, 7164,
7183, 7159, 7172, 7148, 7190, 7166, 7189, 7165, 7182, 7158, 7169, 7145, 7186, 7162, 7185, 7161,
7173, 7149, 7180, 7156, 7192, 7168, 7187, 7163, 7179, 7155, 7191, 7167, 7175, 7151, 7184, 7160,
7193, 7204, 7210, 7215, 7213, 7209, 7212, 7194, 7211, 7216, 7214, 7207, 7208, 7206, 7205, 7200,
7201, 7203, 7202,
]
__charcode_to_pos_43584 = _all_short(__charcode_to_pos_43584)
def _charcode_to_pos_43584(index): return intmask(__charcode_to_pos_43584[index])
# estimated 0.13 KiB
__charcode_to_pos_43968 = [
5576, 5590, 5578, 5580, 5586, 5582, 5565, 5592, 5575, 5584, 5591, 5595, 5596, 5570, 5594, 5571,
5588, 5562, 5569, 5573, 5589, 5563, 5574, 5567, 5568, 5566, 5564, 5577, 5579, 5581, 5587, 5583,
5593, 5585, 5572, 5602, 5600, 5598, 5605, 5603, 5604, 5599, 5601, 5551, 5597, 5550, -1, -1,
5561, 5556, 5560, 5559, 5554, 5553, 5558, 5557, 5552, 5555,
]
__charcode_to_pos_43968 = _all_short(__charcode_to_pos_43968)
def _charcode_to_pos_43968(index): return intmask(__charcode_to_pos_43968[index])
# estimated 0.16 KiB
__charcode_to_pos_55216 = [
4080, 4077, 4085, 4086, 4087, 4082, 4081, 4088, 4089, 4065, 4067, 4066, 4068, 4071, 4072, 4074,
4073, 4070, 4075, 4076, 4069, 4063, 4064, -1, -1, -1, -1, 4020, 4019, 4052, 4053, 4056,
4057, 4058, 4055, 4054, 4059, 4035, 4031, 4049, 4032, 4034, 4033, 4037, 4036, 4009, 4016, 4018,
4046, 4017, 4015, 4030, 4028, 4027, 4048, 4029, 4026, 4025, 4042, 4041, 4050, 4051, 4043, 4039,
4038, 4044, 4040, 4022, 4021, 4061, 4060, 4007, 4008, 4045, 4023, 4024,
]
__charcode_to_pos_55216 = _all_short(__charcode_to_pos_55216)
def _charcode_to_pos_55216(index): return intmask(__charcode_to_pos_55216[index])
# estimated 0.23 KiB
__charcode_to_pos_64107 = [
722, 723, 724, -1, -1, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735,
736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751,
752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767,
768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783,
784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799,
800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815,
816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830,
]
__charcode_to_pos_64107 = _all_short(__charcode_to_pos_64107)
def _charcode_to_pos_64107(index): return intmask(__charcode_to_pos_64107[index])
# estimated 0.04 KiB
__charcode_to_pos_65040 = [
6471, 6474, 6475, 6470, 6482, 6472, 6478, 6477, 6481, 6473,
]
__charcode_to_pos_65040 = _all_ushort(__charcode_to_pos_65040)
def _charcode_to_pos_65040(index): return intmask(__charcode_to_pos_65040[index])
# estimated 0.2 KiB
__charcode_to_pos_65536 = [
5284, 5309, 5301, 5329, 5286, 5277, 5316, 5283, 5290, 5320, 5325, 5317, -1, 5307, 5331, 5343,
5315, 5333, 5336, 5346, 5345, 5289, 5339, 5291, 5296, 5282, 5297, 5303, 5321, 5324, 5279, 5338,
5310, 5287, 5319, 5292, 5344, 5295, 5305, -1, 5328, 5300, 5322, 5278, 5299, 5304, 5285, 5312,
5288, 5326, 5327, 5280, 5308, 5281, 5335, 5323, 5341, 5311, 5313, -1, 5293, 5340, -1, 5294,
5298, 5314, 5347, 5337, 5349, 5318, 5302, 5330, 5342, 5306, 5334, 5332, 5348, 5350, -1, -1,
5351, 5352, 5353, 5354, 5355, 5356, 5357, 5358, 5359, 5360, 5361, 5362, 5363, 5364,
]
__charcode_to_pos_65536 = _all_short(__charcode_to_pos_65536)
def _charcode_to_pos_65536(index): return intmask(__charcode_to_pos_65536[index])
# estimated 0.57 KiB
__charcode_to_pos_65664 = [
5154, 5155, 5156, 5157, 5158, 5159, 5160, 5161, 5162, 5163, 5164, 5165, 5166, 5167, 5168, 5169,
5170, 5171, 5172, 5271, 5272, 5173, 5174, 5175, 5273, 5274, 5176, 5177, 5178, 5179, 5180, 5181,
5182, 5183, 5184, 5185, 5275, 5186, 5187, 5188, 5189, 5190, 5191, 5192, 5193, 5194, 5195, 5196,
5197, 5198, 5199, 5200, 5201, 5202, 5203, 5204, 5205, 5206, 5207, 5208, 5209, 5210, 5211, 5212,
5213, 5214, 5215, 5216, 5217, 5218, 5219, 5220, 5221, 5222, 5223, 5224, 5225, 5226, 5227, 5228,
5229, 5230, 5276, 5231, 5232, 5233, 5234, 5235, 5236, 5237, 5238, 5239, 5240, 5241, 5242, 5243,
5244, 5245, 5246, 5247, 5248, 5249, 5250, 5251, 5252, 5253, 5254, 5255, 5256, 5257, 5258, 5259,
5260, 5261, 5262, 5263, 5264, 5265, 5266, 5267, 5268, 5269, 5270, -1, -1, -1, -1, -1,
57, 56, 1, -1, -1, -1, -1, 26, 48, 43, 18, 13, 34, 29, 6, 21,
39, 46, 41, 16, 11, 37, 32, 9, 24, 27, 49, 44, 19, 14, 35, 30,
7, 22, 28, 50, 45, 20, 15, 36, 31, 8, 23, 40, 47, 42, 17, 12,
38, 33, 10, 25, -1, -1, -1, 51, 52, 54, 55, 53, 2, 3, 4, 5,
3808, 3805, 3804, 3796, 3791, 3797, 3802, 3794, 3801, 3813, 3793, 3807, 3799, 3810, 3803, 3800,
3812, 3792, 3806, 3798, 3809, 3814, 3795, 3811, 3821, 3831, 3823, 3819, 3837, 3816, 3820, 3840,
3842, 3843, 3824, 3825, 3834, 3835, 3838, 3839, 3822, 3828, 3832, 3836, 3818, 3841, 3829, 3815,
3826, 3833, 3830, 3817, 3827, 3907, 3908, 3929, 3926, 3960, 3924, 3856, 3906, 3928, 3925, 3858,
3857, 3904, 3897, 3903, 3909, 3959, 3845, 3844, 3859, 3927, 3961, -1, -1, -1, -1, -1,
6565, 6568, 6563, 6566, 6556, 6567, 6555, 6562, 6564, 6557, 6553, 6554,
]
__charcode_to_pos_65664 = _all_short(__charcode_to_pos_65664)
def _charcode_to_pos_65664(index): return intmask(__charcode_to_pos_65664[index])
# estimated 0.11 KiB
__charcode_to_pos_66000 = [
6423, 6425, 6434, 6400, 6403, 6439, 6414, 6412, 6435, 6394, 6398, 6429, 6404, 6419, 6420, 6428,
6417, 6397, 6401, 6408, 6406, 6431, 6405, 6396, 6430, 6416, 6415, 6399, 6402, 6426, 6410, 6409,
6436, 6395, 6424, 6437, 6422, 6427, 6418, 6421, 6411, 6413, 6433, 6432, 6438, 6407,
]
__charcode_to_pos_66000 = _all_ushort(__charcode_to_pos_66000)
def _charcode_to_pos_66000(index): return intmask(__charcode_to_pos_66000[index])
# estimated 0.17 KiB
__charcode_to_pos_66176 = [
5416, 5421, 5418, 5419, 5423, 5420, 5425, 5442, 5444, 5439, 5426, 5427, 5435, 5429, 5430, 5432,
5431, 5433, 5441, 5434, 5428, 5436, 5437, 5438, 5440, 5417, 5422, 5424, 5443, -1, -1, -1,
564, 593, 569, 579, 608, 595, 580, 565, 594, 566, 582, 591, 570, 603, 598, 599,
597, 567, 606, 590, 612, 587, 605, 592, 600, 575, 571, 611, 577, 578, 588, 607,
573, 574, 601, 602, 589, 576, 568, 604, 609, 596, 583, 584, 585, 586, 581, 572,
610,
]
__charcode_to_pos_66176 = _all_short(__charcode_to_pos_66176)
def _charcode_to_pos_66176(index): return intmask(__charcode_to_pos_66176[index])
# estimated 0.18 KiB
__charcode_to_pos_66432 = [
7711, 7712, 7715, 7721, 7713, 7717, 7736, 7738, 7718, 7732, 7737, 7720, 7730, 7722, 7723, 7714,
7724, 7739, 7729, 7710, 7725, 7728, 7726, 7727, 7733, 7716, 7734, 7719, 7735, 7731, -1, 7740,
6102, 6119, 6139, 6122, 6123, 6116, 6117, 6142, 6109, 6120, 6121, 6136, 6138, 6110, 6113, 6114,
6137, 6130, 6106, 6115, 6128, 6129, 6125, 6126, 6127, 6144, 6140, 6141, 6131, 6132, 6124, 6133,
6145, 6134, 6135, 6118, -1, -1, -1, -1, 6103, 6104, 6105, 6143, 6111, 6112, 6107, 6108,
6146, 6098, 6101, 6099, 6100, 6097,
]
__charcode_to_pos_66432 = _all_short(__charcode_to_pos_66432)
def _charcode_to_pos_66432(index): return intmask(__charcode_to_pos_66432[index])
# estimated 0.2 KiB
__charcode_to_pos_66638 = [
2282, 2281, 6782, 6788, 6771, 6763, 6787, 6784, 6785, 6757, 6793, 6766, 6756, 6758, 6764, 6790,
6786, 6795, 6773, 6770, 6791, 6765, 6772, 6774, 6769, 6761, 6754, 6748, 6778, 6792, 6781, 6750,
6783, 6775, 6760, 6749, 6768, 6789, 6776, 6779, 6777, 6755, 6752, 6780, 6751, 6762, 6753, 6759,
6767, 6794, 6273, 6274, 6296, 6284, 6299, 6286, 6276, 6293, 6294, 6295, 6277, 6275, 6281, 6280,
6292, 6285, 6287, 6288, 6289, 6298, 6282, 6300, 6271, 6278, 6283, 6290, 6297, 6272, 6279, 6291,
-1, -1, 6270, 6265, 6269, 6268, 6263, 6262, 6267, 6266, 6261, 6264,
]
__charcode_to_pos_66638 = _all_short(__charcode_to_pos_66638)
def _charcode_to_pos_66638(index): return intmask(__charcode_to_pos_66638[index])
# estimated 0.2 KiB
__charcode_to_pos_67584 = [
2120, 2121, 2122, 2145, 2166, 2123, -1, -1, 2124, -1, 2125, 2126, 2127, 2128, 2129, 2130,
2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2146, 2147,
2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163,
2164, 2165, 2167, 2168, 2169, 2170, -1, 2171, 2172, -1, -1, -1, 2173, -1, -1, 2174,
4178, 4180, 4182, 4181, 4183, 4197, 4199, 4184, 4196, 4198, 4185, 4186, 4187, 4188, 4193, 4179,
4189, 4192, 4190, 4191, 4194, 4195, -1, 4208, 4200, 4207, 4205, 4203, 4206, 4201, 4202, 4204,
]
__charcode_to_pos_67584 = _all_short(__charcode_to_pos_67584)
def _charcode_to_pos_67584(index): return intmask(__charcode_to_pos_67584[index])
# estimated 0.14 KiB
__charcode_to_pos_67840 = [
6441, 6442, 6444, 6443, 6445, 6459, 6461, 6446, 6458, 6460, 6447, 6448, 6449, 6450, 6455, 6440,
6451, 6454, 6452, 6453, 6456, 6457, 6462, 6464, 6466, 6463, 6467, 6465, -1, -1, -1, 6468,
5445, 5447, 5453, 5449, 5450, 5469, 5454, 5470, 5455, 5456, 5458, 5459, 5461, 5463, 5465, 5466,
5468, 5452, 5462, 5464, 5467, 5446, 5451, 5457, 5460, 5448, -1, -1, -1, -1, -1, 5471,
]
__charcode_to_pos_67840 = _all_short(__charcode_to_pos_67840)
def _charcode_to_pos_67840(index): return intmask(__charcode_to_pos_67840[index])
# estimated 0.16 KiB
__charcode_to_pos_68096 = [
4489, 4546, 4548, 4549, -1, 4545, 4547, -1, -1, -1, -1, -1, 4544, 4541, 4537, 4542,
4502, 4503, 4498, 4499, -1, 4492, 4493, 4501, -1, 4509, 4518, 4519, 4495, 4496, 4508, 4516,
4517, 4494, 4497, 4507, 4510, 4511, 4490, 4491, 4506, 4522, 4512, 4505, 4521, 4514, 4515, 4513,
4523, 4500, 4504, 4520, -1, -1, -1, -1, 4538, 4539, 4540, -1, -1, -1, -1, 4543,
4486, 4488, 4487, 4485, 4526, 4527, 4524, 4525,
]
__charcode_to_pos_68096 = _all_short(__charcode_to_pos_68096)
def _charcode_to_pos_68096(index): return intmask(__charcode_to_pos_68096[index])
# estimated 0.03 KiB
__charcode_to_pos_68176 = [
4531, 4536, 4528, 4529, 4535, 4534, 4530, 4532, 4533,
]
__charcode_to_pos_68176 = _all_ushort(__charcode_to_pos_68176)
def _charcode_to_pos_68176(index): return intmask(__charcode_to_pos_68176[index])
# estimated 0.08 KiB
__charcode_to_pos_68192 = [
6156, 6160, 6157, 6161, 6163, 6173, 6168, 6164, 6149, 6169, 6167, 6158, 6162, 6159, 6165, 6166,
6153, 6147, 6148, 6151, 6155, 6150, 6154, 6170, 6175, 6152, 6174, 6171, 6172, 6177, 6176, 6178,
]
__charcode_to_pos_68192 = _all_ushort(__charcode_to_pos_68192)
def _charcode_to_pos_68192(index): return intmask(__charcode_to_pos_68192[index])
# estimated 0.27 KiB
__charcode_to_pos_68352 = [
156, 157, 163, 159, 162, 158, 160, 161, 169, 170, 189, 190, 177, 178, 200, 201,
180, 203, 205, 204, 172, 173, 174, 166, 179, 197, 198, 167, 168, 199, 191, 171,
164, 165, 184, 186, 185, 183, 188, 187, 182, 176, 207, 206, 202, 192, 181, 193,
208, 194, 209, 195, 196, 175, -1, -1, -1, 155, 7688, 6799, 4640, 4638, 4641, 4639,
4236, 4238, 4240, 4239, 4241, 4255, 4257, 4242, 4254, 4256, 4243, 4244, 4245, 4246, 4251, 4237,
4247, 4250, 4248, 4249, 4252, 4253, -1, -1, 4259, 4265, 4263, 4258, 4262, 4264, 4260, 4261,
4209, 4210, 4212, 4211, 4213, 4225, 4227, 4214, 4224, 4226, 4215, 4216, 4217, 4218, 4221, 4219,
4220, 4222, 4223, -1, -1, -1, -1, -1, 4229, 4235, 4233, 4228, 4232, 4234, 4230, 4231,
]
__charcode_to_pos_68352 = _all_short(__charcode_to_pos_68352)
def _charcode_to_pos_68352(index): return intmask(__charcode_to_pos_68352[index])
# estimated 0.16 KiB
__charcode_to_pos_68608 = [
6179, 6221, 6224, 6212, 6247, 6240, 6215, 6216, 6249, 6180, 6222, 6182, 6225, 6192, 6232, 6184,
6226, 6181, 6223, 6183, 6211, 6246, 6200, 6239, 6191, 6231, 6185, 6227, 6217, 6250, 6193, 6233,
6186, 6203, 6204, 6194, 6187, 6228, 6207, 6243, 6205, 6242, 6208, 6244, 6234, 6206, 6229, 6209,
6218, 6213, 6202, 6241, 6195, 6235, 6214, 6248, 6219, 6251, 6196, 6236, 6188, 6197, 6189, 6198,
6237, 6210, 6245, 6199, 6238, 6190, 6230, 6220, 6201,
]
__charcode_to_pos_68608 = _all_ushort(__charcode_to_pos_68608)
def _charcode_to_pos_68608(index): return intmask(__charcode_to_pos_68608[index])
# estimated 0.08 KiB
__charcode_to_pos_69216 = [
6573, 6577, 6576, 6571, 6570, 6575, 6574, 6569, 6572, 6595, 6598, 6596, 6586, 6584, 6594, 6592,
6583, 6589, 6590, 6599, 6597, 6587, 6585, 6593, 6591, 6582, 6588, 6578, 6579, 6580, 6581,
]
__charcode_to_pos_69216 = _all_ushort(__charcode_to_pos_69216)
def _charcode_to_pos_69216(index): return intmask(__charcode_to_pos_69216[index])
# estimated 0.14 KiB
__charcode_to_pos_69760 = [
4416, 4415, 4419, 4368, 4369, 4385, 4386, 4409, 4410, 4381, 4370, 4397, 4371, 4389, 4390, 4382,
4383, 4394, 4374, 4375, 4387, 4388, 4396, 4407, 4408, 4377, 4378, 4379, 4401, 4395, 4405, 4406,
4376, 4380, 4393, 4398, 4399, 4372, 4373, 4392, 4412, 4400, 4391, 4411, 4403, 4404, 4402, 4384,
4420, 4424, 4425, 4427, 4428, 4423, 4421, 4426, 4422, 4418, 4417, 4363, 4367, 4413, 4414, 4366,
4364, 4365,
]
__charcode_to_pos_69760 = _all_ushort(__charcode_to_pos_69760)
def _charcode_to_pos_69760(index): return intmask(__charcode_to_pos_69760[index])
# estimated 1.73 KiB
__charcode_to_pos_73728 = [
1240, 1241, 1242, 1243, 1244, 1245, 1246, 1247, 1248, 1249, 1250, 1252, 1253, 1254, 1255, 1256,
1257, 1258, 1259, 1260, 1261, 1251, 1262, 1263, 1264, 1265, 1266, 1267, 1268, 1269, 1270, 1271,
1272, 1273, 1274, 1275, 1276, 1277, 1278, 1279, 1280, 1281, 1282, 1283, 1284, 1285, 1286, 1289,
1287, 1288, 1290, 1291, 1292, 1293, 1294, 1295, 1296, 1301, 1297, 1300, 1298, 1299, 1302, 1303,
1304, 1305, 1306, 1307, 1308, 1309, 1310, 1311, 1312, 1313, 1314, 1315, 1316, 1317, 1319, 1320,
1318, 1321, 1322, 1323, 1324, 1325, 1326, 1327, 1328, 1329, 1330, 1331, 1332, 1333, 1334, 1335,
1336, 1337, 1338, 1339, 1340, 1341, 1342, 1343, 1344, 1345, 1346, 1347, 1348, 1349, 1350, 1351,
1352, 1353, 1354, 1355, 1356, 1357, 1358, 1359, 1360, 1361, 1362, 1364, 1363, 1365, 1366, 1367,
1368, 1369, 1370, 1371, 1372, 1373, 1374, 1375, 1376, 1377, 1378, 1380, 1379, 1381, 1382, 1383,
1384, 1385, 1386, 1387, 1388, 1389, 1390, 1391, 1395, 1396, 1397, 1392, 1393, 1394, 1398, 1399,
1400, 1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408, 1409, 1410, 1411, 1412, 1413, 1414, 1415,
1416, 1417, 1418, 1419, 1420, 1421, 1422, 1423, 1425, 1426, 1427, 1428, 1429, 1430, 1431, 1432,
1433, 1434, 1435, 1436, 1437, 1438, 1439, 1440, 1441, 1442, 1443, 1444, 1445, 1446, 1447, 1448,
1449, 1450, 1451, 1452, 1453, 1454, 1455, 1456, 1457, 1458, 1459, 1460, 1461, 1462, 1463, 1464,
1465, 1466, 1467, 1468, 1469, 1470, 1471, 1472, 1473, 1474, 1475, 1476, 1477, 1424, 1478, 1479,
1480, 1481, 1482, 1483, 1484, 1485, 1486, 1487, 1490, 1489, 1488, 1491, 1492, 1493, 1494, 1495,
1496, 1498, 1499, 1497, 1500, 1502, 1501, 1503, 1504, 1505, 1506, 1507, 1508, 1509, 1510, 1511,
1512, 1513, 1514, 1516, 1517, 1515, 1518, 1519, 1520, 1522, 1523, 1524, 1525, 1521, 1526, 1528,
1529, 1527, 1530, 1531, 1532, 1533, 1534, 1535, 1536, 1537, 1539, 1538, 1540, 1541, 1542, 1543,
1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556, 1557, 1558, 1559,
1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1570, 1569, 1568, 1571, 1572, 1573, 1574, 1578,
1575, 1576, 1577, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588, 1589, 1590, 1591,
1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1602, 1601, 1603, 1604, 1605, 1606, 1607,
1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623,
1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639,
1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1649, 1648, 1650, 1651, 1652, 1653, 1654, 1655,
1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669, 1670, 1671,
1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679, 1680, 1682, 1683, 1684, 1685, 1686, 1687, 1688,
1689, 1690, 1691, 1692, 1693, 1694, 1695, 1696, 1697, 1698, 1699, 1700, 1701, 1702, 1703, 1704,
1705, 1706, 1707, 1708, 1709, 1710, 1711, 1712, 1713, 1714, 1715, 1716, 1717, 1718, 1719, 1720,
1721, 1722, 1723, 1724, 1725, 1726, 1727, 1728, 1729, 1730, 1731, 1681, 1732, 1735, 1736, 1733,
1734, 1737, 1738, 1739, 1740, 1741, 1742, 1743, 1744, 1745, 1746, 1747, 1748, 1749, 1755, 1756,
1757, 1758, 1759, 1760, 1761, 1762, 1763, 1764, 1765, 1766, 1767, 1768, 1769, 1770, 1771, 1772,
1773, 1754, 1750, 1751, 1753, 1752, 1774, 1775, 1777, 1776, 1778, 1779, 1780, 1781, 1782, 1783,
1784, 1786, 1785, 1787, 1788, 1789, 1790, 1791, 1792, 1793, 1794, 1795, 1796, 1797, 1798, 1799,
1800, 1801, 1802, 1806, 1807, 1808, 1804, 1805, 1803, 1809, 1811, 1812, 1813, 1810, 1814, 1815,
1816, 1817, 1819, 1818, 1820, 1822, 1821, 1823, 1824, 1826, 1827, 1825, 1828, 1829, 1830, 1831,
1832, 1833, 1834, 1835, 1836, 1837, 1838, 1839, 1840, 1841, 1842, 1843, 1844, 1845, 1846, 1847,
1848, 1849, 1850, 1851, 1854, 1855, 1856, 1857, 1858, 1860, 1859, 1852, 1853, 1861, 1862, 1863,
1864, 1865, 1866, 1867, 1868, 1869, 1870, 1871, 1872, 1873, 1874, 1875, 1876, 1877, 1878, 1879,
1881, 1882, 1883, 1884, 1885, 1886, 1887, 1888, 1889, 1880, 1890, 1892, 1893, 1894, 1891, 1895,
1896, 1897, 1898, 1899, 1902, 1900, 1904, 1905, 1906, 1907, 1908, 1909, 1910, 1911, 1912, 1913,
1914, 1915, 1916, 1917, 1918, 1919, 1920, 1903, 1901, 1921, 1922, 1923, 1924, 1925, 1926, 1927,
1928, 1929, 1930, 1931, 1932, 1933, 1934, 1935, 1936, 1937, 1938, 1939, 1940, 1941, 1942, 1943,
1944, 1945, 1946, 1947, 1948, 1949, 1950, 1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959,
1960, 1961, 1962, 1963, 1965, 1964, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975,
1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1990, 1991, 1989,
1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007,
2008, 2009, 2012, 2010, 2011, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2024, 2021, 2022,
2023, 2025, 2026, 2027, 2029, 2032, 2033, 2034, 2035, 2028, 2030, 2031, 2036, 2037, 2038, 2039,
2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2055,
2056, 2057, 2058, 2059, 2060, 2061, 2062, 2063, 2064, 2065, 2066, 2067, 2068, 2069, 2070, 2071,
2072, 2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087,
2088, 2089, 2090, 2091, 2092, 2093, 2096, 2094, 2095, 2097, 2098, 2099, 2100, 2101, 2103, 2102,
2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118,
]
__charcode_to_pos_73728 = _all_ushort(__charcode_to_pos_73728)
def _charcode_to_pos_73728(index): return intmask(__charcode_to_pos_73728[index])
# estimated 0.21 KiB
__charcode_to_pos_74752 = [
1225, 1211, 1156, 1144, 1204, 1194, 1137, 1173, 1216, 1161, 1149, 1206, 1195, 1138, 1174, 1166,
1155, 1209, 1198, 1141, 1177, 1188, 1230, 1217, 1162, 1150, 1207, 1196, 1139, 1175, 1189, 1231,
1218, 1163, 1151, 1232, 1219, 1220, 1164, 1152, 1208, 1197, 1140, 1176, 1191, 1233, 1221, 1222,
1165, 1153, 1202, 1203, 1185, 1228, 1214, 1215, 1160, 1148, 1223, 1224, 1167, 1170, 1168, 1169,
1210, 1201, 1199, 1200, 1142, 1143, 1178, 1180, 1181, 1179, 1226, 1212, 1157, 1145, 1205, 1184,
1227, 1213, 1158, 1159, 1146, 1147, 1172, 1171, 1187, 1229, 1192, 1234, 1154, 1193, 1235, 1186,
1190, 1183, 1182,
]
__charcode_to_pos_74752 = _all_ushort(__charcode_to_pos_74752)
def _charcode_to_pos_74752(index): return intmask(__charcode_to_pos_74752[index])
# estimated 2.11 KiB
__charcode_to_pos_77824 = [
2446, 2447, 2448, 2449, 2450, 2451, 2452, 2453, 2454, 2455, 2456, 2457, 2458, 2459, 2460, 2461,
2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470, 2471, 2472, 2473, 2474, 2475, 2476, 2477,
2478, 2479, 2480, 2481, 2482, 2483, 2484, 2485, 2486, 2487, 2488, 2489, 2490, 2491, 2492, 2493,
2494, 2495, 2496, 2497, 2498, 2499, 2500, 2501, 2502, 2503, 2504, 2505, 2506, 2507, 2508, 2509,
2510, 2511, 2512, 2513, 2514, 2515, 2516, 2517, 2518, 2519, 2520, 2521, 2522, 2523, 2524, 2525,
2560, 2561, 2562, 2563, 2564, 2565, 2566, 2567, 2568, 2569, 2570, 2571, 2572, 2573, 2574, 2575,
2576, 2577, 2578, 2579, 2580, 2581, 2582, 2583, 2584, 2585, 2586, 2587, 2588, 2589, 2590, 2591,
2592, 2593, 2594, 2595, 2596, 2597, 2598, 2599, 2600, 2601, 2602, 2603, 2604, 2605, 2606, 2607,
2608, 2609, 2610, 2611, 2612, 2613, 2614, 2615, 2616, 2617, 2618, 2619, 2620, 2621, 2622, 2623,
2624, 2625, 2626, 2627, 2628, 2629, 2630, 2631, 2632, 2633, 2634, 2635, 2636, 2637, 2638, 2639,
2640, 2641, 2642, 2643, 2644, 2645, 2646, 2647, 2648, 2649, 2650, 2651, 2652, 2653, 2654, 2655,
2656, 2657, 2658, 2659, 2660, 2661, 2662, 2663, 2664, 2665, 2666, 2667, 2668, 2669, 2670, 2671,
2672, 2673, 2674, 2675, 2676, 2677, 2678, 2679, 2680, 2681, 2682, 2683, 2684, 2685, 2686, 2687,
2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695, 2696, 2697, 2698, 2699, 2700, 2701, 2702, 2703,
2704, 2705, 2706, 2707, 2708, 2709, 2710, 2711, 2712, 2713, 2714, 2715, 2716, 2717, 2718, 2719,
2720, 2721, 2722, 2723, 2724, 2725, 2726, 2727, 2728, 2729, 2730, 2731, 2732, 2733, 2734, 2735,
2736, 2737, 2738, 2739, 2740, 2741, 2742, 2743, 2744, 2745, 2746, 2747, 2748, 2749, 2750, 2751,
2752, 2753, 2754, 2755, 2756, 2757, 2758, 2759, 2760, 2761, 2762, 2763, 2764, 2765, 2766, 2767,
2768, 2769, 2770, 2771, 2772, 2773, 2774, 2775, 2776, 2777, 2778, 2779, 2780, 2781, 2782, 2783,
2784, 2785, 2786, 2787, 2788, 2789, 2790, 2791, 2792, 2793, 2794, 2795, 2796, 2797, 2798, 2799,
2800, 2801, 2802, 2803, 2804, 2805, 2806, 2807, 2808, 2809, 2810, 2811, 2812, 2813, 2814, 2815,
2816, 2817, 2818, 2819, 2820, 2821, 2822, 2823, 2824, 2825, 2826, 2827, 2828, 2829, 2830, 2831,
2832, 2833, 2834, 2835, 2836, 2837, 2838, 2839, 2840, 2841, 2842, 2843, 2844, 2845, 2846, 2847,
2848, 2849, 2850, 2851, 2852, 2853, 2854, 2855, 2856, 2857, 2858, 2859, 2860, 2861, 2862, 2863,
2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871, 2872, 2873, 2874, 2875, 2876, 2877, 2878, 2879,
2880, 2881, 2882, 2883, 2884, 2885, 2886, 2887, 2888, 2889, 2890, 2891, 2892, 2893, 2894, 2895,
2896, 2897, 2898, 2899, 2900, 2901, 2902, 2903, 2904, 2905, 2906, 2907, 2908, 2909, 2910, 2911,
2912, 2913, 2914, 2915, 2916, 2917, 2918, 2919, 2920, 2921, 2922, 2923, 2924, 2925, 2926, 2927,
2928, 2929, 2930, 2931, 2932, 2933, 2934, 2935, 2936, 2937, 2938, 2939, 2940, 2941, 2942, 2943,
2944, 2945, 2946, 2947, 2948, 2949, 2950, 2951, 2952, 2953, 2954, 2955, 2956, 2957, 2958, 2959,
2960, 2961, 2962, 2963, 2964, 2965, 2966, 2967, 2968, 2969, 2970, 2971, 2972, 2973, 2974, 2975,
2976, 2977, 2978, 2979, 2980, 2981, 2982, 2983, 2984, 2985, 2986, 2987, 2988, 2989, 2990, 2991,
2992, 2993, 2994, 2995, 2996, 2997, 2998, 2999, 3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007,
3008, 3009, 3010, 3011, 3012, 3013, 3014, 3015, 3016, 3017, 3018, 3019, 3020, 3021, 3022, 3023,
3024, 3025, 3026, 3027, 3028, 3029, 3030, 3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3039,
3040, 3041, 3042, 3043, 3044, 3045, 3046, 3047, 3048, 3049, 3050, 3051, 3052, 3053, 3054, 3055,
3056, 3057, 3058, 3059, 3060, 3061, 3062, 3063, 3064, 3065, 3066, 3067, 3068, 3069, 3070, 3071,
3072, 3073, 3074, 3075, 3076, 3077, 3078, 3079, 3080, 3081, 3082, 3083, 3084, 3085, 3086, 3087,
3088, 3089, 3090, 3091, 3092, 3093, 3094, 3095, 3096, 3097, 3098, 3099, 3100, 3101, 3102, 3103,
3104, 3105, 3106, 3107, 3108, 3109, 3110, 3111, 3112, 3113, 3114, 3115, 3116, 3117, 3118, 3119,
3120, 3121, 3122, 3123, 3124, 3125, 3126, 3127, 3128, 3129, 3130, 3131, 3132, 3133, 3134, 3135,
3136, 3137, 3138, 3139, 3140, 3141, 3142, 3143, 3144, 3145, 3146, 3147, 3148, 3149, 3150, 3151,
3152, 3153, 3154, 3155, 3156, 3157, 3158, 3159, 3160, 3161, 3162, 3163, 3164, 3165, 3166, 3167,
3168, 3169, 3170, 3171, 3172, 3173, 3174, 3175, 3176, 3177, 3178, 3179, 3180, 3181, 3182, 3183,
3184, 3185, 3186, 3187, 3188, 3189, 3190, 3191, 3192, 3193, 3194, 3195, 3196, 3197, 3198, 3199,
3200, 3201, 3202, 3203, 3204, 3205, 3206, 3207, 3208, 3209, 3210, 3211, 3212, 3213, 3214, 3215,
3216, 3217, 3218, 3219, 3220, 3221, 3222, 3223, 3224, 3225, 3226, 3227, 3228, 3229, 3230, 3231,
3232, 3233, 3234, 3235, 3236, 3237, 3238, 3239, 3240, 3241, 3242, 3243, 3244, 3245, 3246, 3247,
3248, 3249, 3250, 3251, 3252, 3253, 3254, 3255, 3256, 3257, 3258, 3259, 3260, 3261, 3262, 3263,
3264, 3265, 3266, 3267, 3268, 3269, 3270, 3271, 3272, 3273, 3274, 3275, 3276, 3277, 3278, 3279,
3280, 3281, 3282, 3283, 3284, 3285, 3286, 3287, 3288, 3289, 3290, 3291, 3292, 3293, 3294, 3295,
3296, 3297, 3298, 3299, 3300, 3301, 3302, 3303, 3304, 3305, 3306, 3307, 3308, 3309, 3310, 3311,
3312, 3313, 3314, 3315, 3316, 3317, 3318, 3319, 3320, 3321, 3322, 3323, 3324, 3325, 3326, 3327,
3328, 3329, 3330, 3331, 3332, 3333, 3334, 3335, 3336, 3337, 3338, 3339, 3340, 3341, 3342, 3343,
3344, 3345, 3346, 3347, 3348, 3349, 3350, 3351, 3352, 3353, 3354, 3355, 3356, 3357, 3358, 3359,
3360, 3361, 3362, 3363, 3364, 3365, 3366, 3367, 3368, 3369, 3370, 3371, 3372, 3373, 3374, 3375,
3376, 3377, 3378, 3379, 3380, 3381, 3382, 3383, 3384, 3385, 3386, 3387, 3388, 3389, 3390, 3391,
3392, 3393, 3394, 3395, 3396, 3397, 3398, 3399, 3400, 3401, 3402, 3403, 3404, 3405, 3406, 3407,
3408, 3409, 3410, 3411, 3412, 3413, 3414, 3415, 3416, 3417, 3418, 3419, 3420, 3421, 3422, 3423,
3424, 3425, 3426, 3427, 3428, 3429, 3430, 3431, 3432, 3433, 3434, 3435, 3436, 3437, 3438, 3439,
3440, 3441, 3442, 3443, 3444, 3445, 3446, 3447, 3448, 3449, 3450, 3451, 3452, 3453, 3454, 3455,
3456, 3457, 3458, 3459, 3460, 3461, 3462, 3463, 3464, 3465, 3466, 3467, 3468, 3469, 3470, 3471,
3472, 3473, 3474, 3475, 3476, 3477, 3478, 3479, 3480, 3481, 3482, 3483, 3484, 3485, 3486, 3487,
3488, 3489, 3490, 3491, 3492, 3493, 3494, 3495, 3496, 3497, 3498, 3499, 3500, 3501, 3502, 3503,
3504, 3505, 3506, 3507, 3508, 3509, 3510, 3511, 3512, 3513, 3514, 3515, 3516, 2526, 2527, 2528,
2529, 2530, 2531, 2532, 2533, 2534, 2535, 2536, 2537, 2538, 2539, 2540, 2541, 2542, 2543, 2544,
2545, 2546, 2547, 2548, 2549, 2550, 2551, 2552, 2553, 2554, 2555, 2556, 2557, 2558, 2559,
]
__charcode_to_pos_77824 = _all_ushort(__charcode_to_pos_77824)
def _charcode_to_pos_77824(index): return intmask(__charcode_to_pos_77824[index])
# estimated 0.15 KiB
__charcode_to_pos_119296 = [
3930, 3941, 3947, 3948, 3949, 3955, 3956, 3957, 3958, 3931, 3932, 3933, 3934, 3935, 3936, 3937,
3938, 3939, 3940, 3942, 3943, 3944, 3945, 3946, 3950, 3951, 3952, 3953, 3954, 3860, 3868, 3881,
3889, 3895, 3896, 3861, 3862, 3863, 3864, 3865, 3866, 3867, 3869, 3870, 3871, 3872, 3873, 3874,
3875, 3876, 3877, 3878, 3879, 3880, 3882, 3883, 3884, 3885, 3886, 3887, 3888, 3890, 3891, 3892,
3893, 3894, 946, 945, 944, 3905,
]
__charcode_to_pos_119296 = _all_ushort(__charcode_to_pos_119296)
def _charcode_to_pos_119296(index): return intmask(__charcode_to_pos_119296[index])
# estimated 0.19 KiB
__charcode_to_pos_119552 = [
5766, 2326, 2327, 2322, 2323, 2321, 7540, 7572, 7591, 7537, 7584, 7550, 7536, 7593, 7539, 7553,
7558, 7613, 7581, 7596, 7598, 7548, 7580, 7611, 7570, 7534, 7599, 7601, 7561, 7583, 7549, 7564,
7560, 7541, 7552, 7538, 7594, 7588, 7543, 7585, 7574, 7608, 7597, 7573, 7600, 7587, 7602, 7576,
7563, 7607, 7577, 7565, 7595, 7603, 7569, 7610, 7547, 7590, 7566, 7609, 7556, 7542, 7578, 7575,
7589, 7533, 7562, 7559, 7612, 7605, 7582, 7554, 7551, 7557, 7567, 7604, 7606, 7579, 7545, 7544,
7568, 7535, 7546, 7592, 7555, 7586, 7571,
]
__charcode_to_pos_119552 = _all_ushort(__charcode_to_pos_119552)
def _charcode_to_pos_119552(index): return intmask(__charcode_to_pos_119552[index])
# estimated 0.05 KiB
__charcode_to_pos_119648 = [
1129, 1133, 1132, 1127, 1126, 1131, 1130, 1125, 1128, 1120, 1124, 1123, 1118, 1117, 1122, 1121,
1116, 1119,
]
__charcode_to_pos_119648 = _all_ushort(__charcode_to_pos_119648)
def _charcode_to_pos_119648(index): return intmask(__charcode_to_pos_119648[index])
# estimated 0.3 KiB
__charcode_to_pos_126976 = [
5476, 5504, 5513, 5491, 5497, 5486, 5514, 5493, 5511, 5508, 5484, 5481, 5502, 5499, 5478, 5489,
5492, 5510, 5507, 5483, 5480, 5501, 5498, 5477, 5488, 5494, 5512, 5509, 5485, 5482, 5503, 5500,
5479, 5490, 5496, 5495, 5474, 5475, 5505, 5506, 5472, 5515, 5487, 5473, -1, -1, -1, -1,
2332, 2333, 2334, 2335, 2336, 2337, 2338, 2339, 2340, 2341, 2342, 2343, 2344, 2345, 2346, 2347,
2348, 2349, 2350, 2351, 2352, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362, 2363,
2364, 2365, 2366, 2367, 2368, 2369, 2370, 2371, 2372, 2373, 2374, 2375, 2376, 2377, 2378, 2379,
2380, 2381, 2382, 2383, 2384, 2385, 2386, 2387, 2388, 2389, 2390, 2391, 2392, 2393, 2394, 2395,
2396, 2397, 2398, 2399, 2400, 2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410, 2411,
2412, 2413, 2414, 2415, 2416, 2417, 2418, 2419, 2420, 2421, 2422, 2423, 2424, 2425, 2426, 2427,
2428, 2429, 2430, 2431,
]
__charcode_to_pos_126976 = _all_short(__charcode_to_pos_126976)
def _charcode_to_pos_126976(index): return intmask(__charcode_to_pos_126976[index])
# estimated 0.11 KiB
__charcode_to_pos_127232 = [
2320, 2319, 2314, 2318, 2317, 2312, 2311, 2316, 2315, 2310, 2313, -1, -1, -1, -1, -1,
6307, 6308, 6309, 6310, 6311, 6312, 6313, 6314, 6315, 6316, 6317, 6318, 6319, 6320, 6321, 6322,
6323, 6324, 6325, 6326, 6327, 6328, 6329, 6330, 6331, 6332, 7703, 709, 710, 702, 721, -1,
-1, 6861,
]
__charcode_to_pos_127232 = _all_short(__charcode_to_pos_127232)
def _charcode_to_pos_127232(index): return intmask(__charcode_to_pos_127232[index])
# estimated 0.05 KiB
__charcode_to_pos_127293 = [
6862, -1, 6863, -1, -1, 6864, -1, -1, -1, 6865, -1, -1, -1, 6858, 6866, 6869,
6870, 6867,
]
__charcode_to_pos_127293 = _all_short(__charcode_to_pos_127293)
def _charcode_to_pos_127293(index): return intmask(__charcode_to_pos_127293[index])
# estimated 0.03 KiB
__charcode_to_pos_127353 = [
5885, -1, 5886, 5887, -1, -1, 5888,
]
__charcode_to_pos_127353 = _all_short(__charcode_to_pos_127353)
def _charcode_to_pos_127353(index): return intmask(__charcode_to_pos_127353[index])
# estimated 0.03 KiB
__charcode_to_pos_127370 = [
1134, 5884, 5889, 5890, -1, -1, 6808,
]
__charcode_to_pos_127370 = _all_short(__charcode_to_pos_127370)
def _charcode_to_pos_127370(index): return intmask(__charcode_to_pos_127370[index])
# estimated 0.08 KiB
__charcode_to_pos_127504 = [
6841, 6838, 6832, 6859, 6827, 6836, 6853, 6837, 6828, 6848, 6850, 6846, 6831, 6840, 6829, 6847,
6830, 6852, 6851, 6854, 6835, 6834, 6849, 6843, 6845, 6824, 6825, 6856, 6839, 6826, 6833, 6844,
6855, 6842,
]
__charcode_to_pos_127504 = _all_ushort(__charcode_to_pos_127504)
def _charcode_to_pos_127504(index): return intmask(__charcode_to_pos_127504[index])
# estimated 0.03 KiB
__charcode_to_pos_127552 = [
7700, 7694, 7695, 7697, 7701, 7698, 7702, 7696, 7699,
]
__charcode_to_pos_127552 = _all_ushort(__charcode_to_pos_127552)
def _charcode_to_pos_127552(index): return intmask(__charcode_to_pos_127552[index])
# estimated 0.48 KiB
__charcode_to_pos_917760 = [
8117, 8128, 8139, 8150, 8161, 8172, 8183, 8194, 8205, 8213, 8214, 8215, 8216, 8217, 8218, 8219,
8220, 8221, 8222, 8223, 8224, 8225, 8226, 8227, 8228, 8229, 8230, 8231, 8232, 8233, 8234, 8235,
8236, 8237, 8238, 8239, 8240, 8241, 8242, 8243, 8244, 8245, 8246, 8247, 8248, 8249, 8250, 8251,
8252, 8253, 8254, 8255, 8256, 8257, 8258, 8259, 8260, 8261, 8262, 8263, 8264, 8265, 8266, 8267,
8268, 8269, 8270, 8271, 8272, 8273, 8274, 8275, 8276, 8277, 8278, 8279, 8280, 8281, 8282, 8283,
8284, 8285, 8286, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8054, 8055, 8056, 8057, 8058, 8059,
8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067, 8068, 8069, 8070, 8071, 8072, 8073, 8074, 8075,
8076, 8077, 8078, 8079, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091,
8092, 8093, 8094, 8095, 8096, 8097, 8098, 8099, 8100, 8101, 8102, 8103, 8104, 8105, 8106, 8107,
8108, 8109, 8110, 8111, 8112, 8113, 8114, 8115, 8116, 8118, 8119, 8120, 8121, 8122, 8123, 8124,
8125, 8126, 8127, 8129, 8130, 8131, 8132, 8133, 8134, 8135, 8136, 8137, 8138, 8140, 8141, 8142,
8143, 8144, 8145, 8146, 8147, 8148, 8149, 8151, 8152, 8153, 8154, 8155, 8156, 8157, 8158, 8159,
8160, 8162, 8163, 8164, 8165, 8166, 8167, 8168, 8169, 8170, 8171, 8173, 8174, 8175, 8176, 8177,
8178, 8179, 8180, 8181, 8182, 8184, 8185, 8186, 8187, 8188, 8189, 8190, 8191, 8192, 8193, 8195,
8196, 8197, 8198, 8199, 8200, 8201, 8202, 8203, 8204, 8206, 8207, 8208, 8209, 8210, 8211, 8212,
]
__charcode_to_pos_917760 = _all_ushort(__charcode_to_pos_917760)
def _charcode_to_pos_917760(index): return intmask(__charcode_to_pos_917760[index])
# estimated 0.04 KiB
__charcode_to_pos_983040 = [
4672, 4836, 4429, 4635, 4634, 4637, 4636, 7622, 8357, 6480, 482,
]
__charcode_to_pos_983040 = _all_ushort(__charcode_to_pos_983040)
def _charcode_to_pos_983040(index): return intmask(__charcode_to_pos_983040[index])
# estimated 0.79 KiB
__charcode_to_pos_983552 = [
4642, 4787, 4666, 4824, 4668, 4826, 4667, 4825, 4660, 4816, 4659, 4815, 4677, 4844, 4841, 4880,
4704, 4885, 4706, 4887, 4705, 4886, 4721, 4915, 4737, 4946, 4643, 4788, 4644, 4789, 4663, 4820,
4664, 4821, 4661, 4817, 4662, 4818, 4842, 4843, 4678, 4845, 4679, 4846, 4688, 4856, 4697, 4867,
4699, 4873, 4717, 4906, 4739, 4948, 4740, 4949, 4736, 4945, 4738, 4947, 7221, 7228, 7218, 7231,
7239, 7229, 7238, 7227, 7232, 7226, 7241, 7233, 7223, 7240, 7225, 7224, 7234, 7230, 7220, 7236,
7237, 7235, 7219, 7222, 7284, 7289, 7290, 7305, 7306, 7287, 7288, 7285, 7291, 7292, 7286, 7356,
7361, 7362, 7365, 7366, 7359, 7360, 7357, 7363, 7364, 7358, 7251, 7256, 7257, 7260, 7261, 7254,
7255, 7252, 7258, 7259, 7253, 7395, 7400, 7401, 7404, 7405, 7398, 7399, 7396, 7402, 7403, 7397,
7482, 7487, 7488, 7491, 7492, 7485, 7486, 7483, 7489, 7490, 7484, 7369, 7374, 7375, 7389, 7390,
7372, 7373, 7370, 7387, 7388, 7371, 7473, 7478, 7479, 7493, 7494, 7476, 7477, 7474, 7480, 7481,
7475, 7351, 7367, 7368, 7393, 7394, 7354, 7355, 7352, 7391, 7392, 7353, 7406, 7411, 7412, 7415,
7416, 7409, 7410, 7407, 7413, 7414, 7408, 7340, 7345, 7346, 7349, 7350, 7343, 7344, 7341, 7347,
7348, 7342, 7506, 7511, 7512, 7515, 7516, 7509, 7510, 7507, 7513, 7514, 7508, 7417, 7422, 7423,
7437, 7438, 7420, 7421, 7418, 7424, 7425, 7419, 7307, 7312, 7313, 7338, 7339, 7310, 7311, 7308,
7336, 7337, 7309, 7495, 7500, 7501, 7504, 7505, 7498, 7499, 7496, 7502, 7503, 7497, 7321, 7326,
7327, 7330, 7331, 7324, 7325, 7322, 7328, 7329, 7323, 7314, 7319, 7320, 7334, 7335, 7317, 7318,
7315, 7332, 7333, 7316, 7426, 7431, 7432, 7435, 7436, 7429, 7430, 7427, 7433, 7434, 7428, 7376,
7381, 7382, 7385, 7386, 7379, 7380, 7377, 7383, 7384, 7378, 7273, 7278, 7279, 7282, 7283, 7276,
7277, 7274, 7280, 7281, 7275, 7444, 7449, 7450, 7454, 7455, 7447, 7448, 7445, 7451, 7452, 7446,
7460, 7465, 7466, 7469, 7470, 7463, 7464, 7461, 7467, 7468, 7462, 7439, 7456, 7457, 7471, 7472,
7442, 7443, 7440, 7458, 7459, 7441, 7262, 7267, 7268, 7271, 7272, 7265, 7266, 7263, 7269, 7270,
7264, 7293, 7294, 7299, 7300, 7303, 7304, 7297, 7298, 7295, 7301, 7302, 7296, 7453, 3658, 4558,
4559, 4561, 4560, 4566, 4551, 4552, 4554, 4553, 4568, 4555, 4580, 4556, 4581, 4565, 4576, 4577,
4579, 4578, 4567, 4550, 4569, 4571, 4570, 4564, 4583, 4572, 4563, 4582, 4574, 4575, 4573, 4557,
4562, 4632, 4585, 4586, 4587, 4584, 4633, 4631, 4436, 5658,
]
__charcode_to_pos_983552 = _all_ushort(__charcode_to_pos_983552)
def _charcode_to_pos_983552(index): return intmask(__charcode_to_pos_983552[index])
def _charcode_to_pos(code):
    res = -1
    if code == 545: res = 4807
    elif 564 <= code <= 591: res = _charcode_to_pos_564(code-564)
    elif code == 686: res = 4936
    elif code == 687: res = 4937
    elif 751 <= code <= 767: res = _charcode_to_pos_751(code-751)
    elif 848 <= code <= 863: res = _charcode_to_pos_848(code-848)
    elif 880 <= code <= 893: res = _charcode_to_pos_880(code-880)
    elif code == 975: res = 3847
    elif 1015 <= code <= 1023: res = _charcode_to_pos_1015(code-1015)
    elif code == 1159: res = 910
    elif code == 1231: res = 2256
    elif 1270 <= code <= 1279: res = _charcode_to_pos_1270(code-1270)
    elif 1296 <= code <= 1317: res = _charcode_to_pos_1296(code-1296)
    elif code == 1442: res = 4099
    elif code == 1466: res = 4101
    elif code == 1477: res = 4100
    elif code == 1478: res = 4103
    elif code == 1479: res = 4102
    elif 1536 <= code <= 1566: res = _charcode_to_pos_1536(code-1536)
    elif code == 1595: res = 102
    elif code == 1596: res = 100
    elif code == 1597: res = 85
    elif code == 1598: res = 87
    elif code == 1599: res = 86
    elif 1622 <= code <= 1630: res = _charcode_to_pos_1622(code-1622)
    elif code == 1774: res = 80
    elif code == 1775: res = 110
    elif code == 1791: res = 96
    elif code == 1837: res = 6977
    elif code == 1838: res = 6979
    elif code == 1839: res = 6978
    elif 1869 <= code <= 1919: res = _charcode_to_pos_1869(code-1869)
    elif 1984 <= code <= 2110: res = _charcode_to_pos_1984(code-1984)
    elif code == 2304: res = 2301
    elif code == 2308: res = 2293
    elif 2382 <= code <= 2389: res = _charcode_to_pos_2382(code-2382)
    elif 2417 <= code <= 2431: res = _charcode_to_pos_2417(code-2417)
    elif code == 2493: res = 422
    elif code == 2510: res = 421
    elif 2555 <= code <= 2563: res = _charcode_to_pos_2555(code-2555)
    elif code == 2641: res = 3969
    elif code == 2677: res = 3971
    elif code == 2700: res = 3963
    elif code == 2785: res = 3964
    elif code == 2786: res = 3966
    elif code == 2787: res = 3967
    elif code == 2801: res = 3965
    elif code == 2869: res = 6256
    elif code == 2884: res = 6260
    elif code == 2914: res = 6258
    elif code == 2915: res = 6259
    elif code == 2929: res = 6257
    elif code == 2998: res = 7246
    elif code == 3024: res = 7249
    elif code == 3046: res = 7245
    elif 3059 <= code <= 3066: res = _charcode_to_pos_3059(code-3059)
    elif code == 3133: res = 7527
    elif code == 3160: res = 7526
    elif code == 3161: res = 7525
    elif code == 3170: res = 7529
    elif code == 3171: res = 7530
    elif 3192 <= code <= 3199: res = _charcode_to_pos_3192(code-3192)
    elif code == 3260: res = 4432
    elif code == 3261: res = 4430
    elif code == 3298: res = 4434
    elif code == 3299: res = 4435
    elif code == 3313: res = 4431
    elif code == 3314: res = 4433
    elif 3389 <= code <= 3396: res = _charcode_to_pos_3389(code-3389)
    elif code == 3426: res = 5530
    elif code == 3427: res = 5531
    elif 3440 <= code <= 3455: res = _charcode_to_pos_3440(code-3440)
    elif code == 3947: res = 7620
    elif code == 3948: res = 7621
    elif 4046 <= code <= 4056: res = _charcode_to_pos_4046(code-4046)
    elif 4130 <= code <= 4139: res = _charcode_to_pos_4130(code-4130)
    elif 4147 <= code <= 4159: res = _charcode_to_pos_4147(code-4147)
    elif 4186 <= code <= 4255: res = _charcode_to_pos_4186(code-4186)
    elif code == 4345: res = 3657
    elif code == 4346: res = 3656
    elif code == 4348: res = 5663
    elif code == 4442: res = 3976
    elif code == 4443: res = 3982
    elif code == 4444: res = 3980
    elif code == 4445: res = 3981
    elif code == 4446: res = 4005
    elif code == 4515: res = 4062
    elif code == 4516: res = 4083
    elif code == 4517: res = 4084
    elif code == 4518: res = 4078
    elif code == 4519: res = 4079
    elif code == 4602: res = 4013
    elif code == 4603: res = 4014
    elif code == 4604: res = 4010
    elif code == 4605: res = 4012
    elif code == 4606: res = 4011
    elif code == 4607: res = 4047
    elif code == 4615: res = 3561
    elif code == 4679: res = 3583
    elif code == 4743: res = 3609
    elif code == 4783: res = 3563
    elif code == 4815: res = 3608
    elif code == 4847: res = 3617
    elif code == 4879: res = 3553
    elif code == 4895: res = 3548
    elif code == 4935: res = 3607
    elif code == 4959: res = 3520
    elif code == 4960: res = 3521
    elif 4992 <= code <= 5017: res = _charcode_to_pos_4992(code-4992)
    elif code == 5120: res = 497
    elif 5751 <= code <= 5759: res = _charcode_to_pos_5751(code-5751)
    elif code == 6109: res = 4588
    elif 6128 <= code <= 6137: res = _charcode_to_pos_6128(code-6128)
    elif 6314 <= code <= 6389: res = _charcode_to_pos_6314(code-6314)
    elif 6400 <= code <= 6516: res = _charcode_to_pos_6400(code-6400)
    elif 6528 <= code <= 6829: res = _charcode_to_pos_6528(code-6528)
    elif 6912 <= code <= 7097: res = _charcode_to_pos_6912(code-6912)
    elif 7168 <= code <= 7295: res = _charcode_to_pos_7168(code-7168)
    elif 7376 <= code <= 7410: res = _charcode_to_pos_7376(code-7376)
    elif 7424 <= code <= 7654: res = _charcode_to_pos_7424(code-7424)
    elif code == 7677: res = 870
    elif code == 7678: res = 970
    elif code == 7679: res = 983
    elif code == 7836: res = 4868
    elif code == 7837: res = 4869
    elif code == 7838: res = 4723
    elif code == 7839: res = 4812
    elif code == 7930: res = 4700
    elif code == 7931: res = 4874
    elif code == 7932: res = 4701
    elif code == 7933: res = 4875
    elif code == 7934: res = 4746
    elif code == 7935: res = 4963
    elif 8275 <= code <= 8292: res = _charcode_to_pos_8275(code-8275)
    elif code == 8336: res = 4969
    elif code == 8337: res = 4970
    elif code == 8338: res = 4973
    elif code == 8339: res = 4978
    elif code == 8340: res = 4975
    elif 8370 <= code <= 8376: res = _charcode_to_pos_8370(code-8370)
    elif code == 8427: res = 974
    elif code == 8428: res = 987
    elif code == 8429: res = 973
    elif code == 8430: res = 969
    elif code == 8431: res = 981
    elif code == 8432: res = 871
    elif code == 8507: res = 3636
    elif code == 8508: res = 2438
    elif 8524 <= code <= 8530: res = _charcode_to_pos_8524(code-8524)
    elif code == 8580: res = 4907
    elif code == 8581: res = 6561
    elif code == 8582: res = 6558
    elif code == 8583: res = 6559
    elif code == 8584: res = 6560
    elif code == 8585: res = 8331
    elif 9167 <= code <= 9192: res = _charcode_to_pos_9167(code-9167)
    elif code == 9471: res = 5881
    elif code == 9748: res = 7742
    elif code == 9749: res = 4173
    elif code == 9752: res = 6747
    elif code == 9854: res = 6335
    elif code == 9855: res = 8334
    elif 9866 <= code <= 9983: res = _charcode_to_pos_9866(code-9866)
    elif code == 10071: res = 4095
    elif 10176 <= code <= 10188: res = _charcode_to_pos_10176(code-10176)
    elif code == 10220: res = 5543
    elif code == 10221: res = 5545
    elif code == 10222: res = 5542
    elif code == 10223: res = 5544
    elif 11008 <= code <= 11097: res = _charcode_to_pos_11008(code-11008)
    elif 11264 <= code <= 11505: res = _charcode_to_pos_11264(code-11264)
    elif 11513 <= code <= 11557: res = _charcode_to_pos_11513(code-11513)
    elif 11568 <= code <= 11621: res = _charcode_to_pos_11568(code-11568)
    elif code == 11631: res = 7683
    elif 11648 <= code <= 11670: res = _charcode_to_pos_11648(code-11648)
    elif 11680 <= code <= 11825: res = _charcode_to_pos_11680(code-11680)
    elif code == 12589: res = 446
    elif 12736 <= code <= 12771: res = _charcode_to_pos_12736(code-12736)
    elif code == 12829: res = 6306
    elif code == 12830: res = 6305
    elif 12868 <= code <= 12880: res = _charcode_to_pos_12868(code-12868)
    elif code == 12924: res = 711
    elif code == 12925: res = 712
    elif code == 12926: res = 704
    elif code == 13004: res = 6816
    elif code == 13005: res = 6812
    elif code == 13006: res = 6813
    elif code == 13007: res = 5153
    elif code == 13175: res = 6809
    elif code == 13176: res = 6811
    elif code == 13177: res = 6810
    elif code == 13178: res = 6818
    elif code == 13278: res = 6819
    elif code == 13279: res = 6807
    elif code == 13311: res = 6815
    elif 19904 <= code <= 19967: res = _charcode_to_pos_19904(code-19904)
    elif 42192 <= code <= 42539: res = _charcode_to_pos_42192(code-42192)
    elif 42560 <= code <= 42611: res = _charcode_to_pos_42560(code-42560)
    elif 42620 <= code <= 42647: res = _charcode_to_pos_42620(code-42620)
    elif 42656 <= code <= 42743: res = _charcode_to_pos_42656(code-42656)
    elif 42752 <= code <= 42892: res = _charcode_to_pos_42752(code-42752)
    elif 43003 <= code <= 43127: res = _charcode_to_pos_43003(code-43003)
    elif 43136 <= code <= 43204: res = _charcode_to_pos_43136(code-43136)
    elif 43214 <= code <= 43347: res = _charcode_to_pos_43214(code-43214)
    elif 43359 <= code <= 43487: res = _charcode_to_pos_43359(code-43359)
    elif 43520 <= code <= 43574: res = _charcode_to_pos_43520(code-43520)
    elif 43584 <= code <= 43714: res = _charcode_to_pos_43584(code-43584)
    elif code == 43739: res = 7197
    elif code == 43740: res = 7198
    elif code == 43741: res = 7199
    elif code == 43742: res = 7195
    elif code == 43743: res = 7196
    elif 43968 <= code <= 44025: res = _charcode_to_pos_43968(code-43968)
    elif 55216 <= code <= 55291: res = _charcode_to_pos_55216(code-55216)
    elif 64107 <= code <= 64217: res = _charcode_to_pos_64107(code-64107)
    elif code == 65021: res = 123
    elif 65040 <= code <= 65049: res = _charcode_to_pos_65040(code-65040)
    elif code == 65060: res = 975
    elif code == 65061: res = 976
    elif code == 65062: res = 874
    elif code == 65095: res = 6476
    elif code == 65096: res = 6479
    elif 65536 <= code <= 65629: res = _charcode_to_pos_65536(code-65536)
    elif 65664 <= code <= 65947: res = _charcode_to_pos_65664(code-65664)
    elif 66000 <= code <= 66045: res = _charcode_to_pos_66000(code-66000)
    elif 66176 <= code <= 66256: res = _charcode_to_pos_66176(code-66176)
    elif 66432 <= code <= 66517: res = _charcode_to_pos_66432(code-66432)
    elif code == 66598: res = 2280
    elif code == 66599: res = 2279
    elif 66638 <= code <= 66729: res = _charcode_to_pos_66638(code-66638)
    elif 67584 <= code <= 67679: res = _charcode_to_pos_67584(code-67584)
    elif 67840 <= code <= 67903: res = _charcode_to_pos_67840(code-67840)
    elif 68096 <= code <= 68167: res = _charcode_to_pos_68096(code-68096)
    elif 68176 <= code <= 68184: res = _charcode_to_pos_68176(code-68176)
    elif 68192 <= code <= 68223: res = _charcode_to_pos_68192(code-68192)
    elif 68352 <= code <= 68479: res = _charcode_to_pos_68352(code-68352)
    elif 68608 <= code <= 68680: res = _charcode_to_pos_68608(code-68608)
    elif 69216 <= code <= 69246: res = _charcode_to_pos_69216(code-69216)
    elif 69760 <= code <= 69825: res = _charcode_to_pos_69760(code-69760)
    elif 73728 <= code <= 74606: res = _charcode_to_pos_73728(code-73728)
    elif 74752 <= code <= 74850: res = _charcode_to_pos_74752(code-74752)
    elif code == 74864: res = 1238
    elif code == 74865: res = 1239
    elif code == 74866: res = 1236
    elif code == 74867: res = 1237
    elif 77824 <= code <= 78894: res = _charcode_to_pos_77824(code-77824)
    elif code == 119081: res = 5770
    elif 119296 <= code <= 119365: res = _charcode_to_pos_119296(code-119296)
    elif 119552 <= code <= 119638: res = _charcode_to_pos_119552(code-119552)
    elif 119648 <= code <= 119665: res = _charcode_to_pos_119648(code-119648)
    elif code == 120001: res = 5546
    elif code == 120484: res = 5540
    elif code == 120485: res = 5541
    elif code == 120778: res = 5538
    elif code == 120779: res = 5539
    elif 126976 <= code <= 127123: res = _charcode_to_pos_126976(code-126976)
    elif 127232 <= code <= 127281: res = _charcode_to_pos_127232(code-127232)
    elif 127293 <= code <= 127310: res = _charcode_to_pos_127293(code-127293)
    elif code == 127319: res = 5882
    elif code == 127327: res = 5883
    elif 127353 <= code <= 127359: res = _charcode_to_pos_127353(code-127353)
    elif 127370 <= code <= 127376: res = _charcode_to_pos_127370(code-127370)
    elif code == 127488: res = 6817
    elif 127504 <= code <= 127537: res = _charcode_to_pos_127504(code-127504)
    elif 127552 <= code <= 127560: res = _charcode_to_pos_127552(code-127552)
    elif 917760 <= code <= 917999: res = _charcode_to_pos_917760(code-917760)
    elif 983040 <= code <= 983050: res = _charcode_to_pos_983040(code-983040)
    elif 983552 <= code <= 983945: res = _charcode_to_pos_983552(code-983552)
    if res == -1:
        raise KeyError(code)
    return res
# end output from build_compression_dawg

def _lookup_cjk(cjk_code):
    if len(cjk_code) != 4 and len(cjk_code) != 5:
        raise KeyError
    for c in cjk_code:
        if not ('0' <= c <= '9' or 'A' <= c <= 'F'):
            raise KeyError
    code = int(cjk_code, 16)
    if (0x3400 <= code <= 0x4DB5 or 0x4E00 <= code <= 0x9FCB or 0x20000 <= code <= 0x2A6D6 or 0x2A700 <= code <= 0x2B734):
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
    if not with_named_sequence and 0xF0200 <= code < 0xF0400:
        raise KeyError
    if not with_alias and 0xF0000 <= code < 0xF0200:
        raise KeyError
    return code

def name(code):
    if (0x3400 <= code <= 0x4DB5 or 0x4E00 <= code <= 0x9FCB or 0x20000 <= code <= 0x2A6D6 or 0x2A700 <= code <= 0x2B734):
        return "CJK UNIFIED IDEOGRAPH-" + hex(code)[2:].upper()
    if 0xAC00 <= code <= 0xD7A3:
        # vl_code, t_code = divmod(code - 0xAC00, len(_hangul_T))
        vl_code = (code - 0xAC00) // len(_hangul_T)
        t_code = (code - 0xAC00) % len(_hangul_T)
        # l_code, v_code = divmod(vl_code,  len(_hangul_V))
        l_code = vl_code // len(_hangul_V)
        v_code = vl_code % len(_hangul_V)
        return ("HANGUL SYLLABLE " + _hangul_L[l_code] +
                _hangul_V[v_code] + _hangul_T[t_code])
    if 0xF0000 <= code < 0xF0400:
        raise KeyError

    if base_mod is None:
        return lookup_charcode(code)
    else:
        try:
            return lookup_charcode(code)
        except KeyError:
            return base_mod.lookup_charcode(code)

# estimated 3.68 KiB
__char_list_data = [
40, 4363, 4457, 4364, 4453, 4523, 41, 40, 4363, 4457, 4370, 4462, 41, 4366, 4449, 4535,
4352, 4457, 49, 8260, 49, 48, 4364, 4462, 4363, 4468, 40, 65, 41, 40, 66, 41,
40, 67, 41, 40, 68, 41, 40, 69, 41, 40, 70, 41, 40, 71, 41, 40,
72, 41, 40, 73, 41, 40, 74, 41, 40, 75, 41, 40, 76, 41, 40, 77,
41, 40, 78, 41, 40, 79, 41, 40, 80, 41, 40, 81, 41, 40, 82, 41,
40, 83, 41, 40, 84, 41, 40, 85, 41, 40, 86, 41, 40, 87, 41, 40,
88, 41, 40, 89, 41, 40, 90, 41, 48, 8260, 51, 49, 8260, 55, 49, 8260,
57, 65, 8725, 109, 70, 65, 88, 70, 70, 73, 70, 70, 76, 70, 102, 105,
70, 102, 108, 76, 84, 68, 80, 80, 86, 80, 84, 69, 86, 8725, 109, 100,
109, 50, 100, 109, 51, 100, 109, 178, 100, 109, 179, 101, 114, 103, 103, 97,
108, 913, 834, 837, 913, 834, 921, 919, 834, 837, 919, 834, 921, 921, 776, 768,
921, 776, 769, 921, 776, 834, 933, 776, 768, 933, 776, 769, 933, 776, 834, 933,
787, 768, 933, 787, 769, 933, 787, 834, 937, 834, 837, 937, 834, 921, 12308, 83,
12309, 12308, 19977, 12309, 12308, 20108, 12309, 12308, 21213, 12309, 12308, 23433, 12309, 12308, 25171, 12309,
12308, 25943, 12309, 12308, 26412, 12309, 12308, 28857, 12309, 12308, 30423, 12309, 48, 44, 49, 44,
50, 44, 51, 44, 52, 44, 53, 44, 54, 44, 55, 44, 56, 44, 57, 44,
65, 702, 67, 68, 68, 74, 70, 105, 70, 108, 72, 86, 72, 103, 72, 817,
73, 85, 74, 780, 83, 68, 83, 83, 83, 84, 83, 115, 83, 116, 84, 776,
87, 90, 87, 778, 89, 778, 101, 86, 700, 78, 902, 837, 902, 921, 905, 837,
905, 921, 911, 837, 911, 921, 913, 921, 919, 921, 921, 834, 929, 787, 933, 834,
937, 921, 1333, 1362, 1333, 1410, 1348, 1333, 1348, 1339, 1348, 1341, 1348, 1350, 1348, 1381,
1348, 1387, 1348, 1389, 1348, 1398, 1358, 1350, 1358, 1398, 4363, 4462, 6917, 6965, 6919, 6965,
6921, 6965, 6923, 6965, 6925, 6965, 6929, 6965, 6970, 6965, 6972, 6965, 6974, 6965, 6975, 6965,
6978, 6965, 7944, 921, 7945, 921, 7946, 921, 7947, 921, 7948, 921, 7949, 921, 7950, 921,
7951, 921, 7976, 921, 7977, 921, 7978, 921, 7979, 921, 7980, 921, 7981, 921, 7982, 921,
7983, 921, 8040, 921, 8041, 921, 8042, 921, 8043, 921, 8044, 921, 8045, 921, 8046, 921,
8047, 921, 8122, 837, 8122, 921, 8138, 837, 8138, 921, 8186, 837, 8186, 921, 12411, 12363,
69785, 69818, 69787, 69818, 69797, 69818, 223, 304, 305, 329, 384, 398, 410, 427, 496, 546,
567, 572, 575, 576, 578, 583, 585, 587, 589, 591, 592, 593, 594, 597, 604, 607,
609, 613, 618, 619, 621, 624, 625, 627, 628, 632, 637, 642, 649, 652, 656, 657,
669, 671, 881, 883, 887, 891, 892, 893, 983, 988, 1010, 1016, 1019, 1231, 1271, 1275,
1277, 1279, 1297, 1299, 1301, 1303, 1305, 1307, 1309, 1311, 1313, 1315, 1317, 1415, 4316, 7426,
7446, 7447, 7452, 7453, 7461, 7545, 7547, 7549, 7557, 7830, 7831, 7832, 7833, 7834, 7931, 7933,
7935, 8018, 8020, 8022, 8064, 8065, 8066, 8067, 8068, 8069, 8070, 8071, 8072, 8073, 8074, 8075,
8076, 8077, 8078, 8079, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091,
8092, 8093, 8094, 8095, 8096, 8097, 8098, 8099, 8100, 8101, 8102, 8103, 8104, 8105, 8106, 8107,
8108, 8109, 8110, 8111, 8114, 8115, 8116, 8119, 8124, 8130, 8131, 8132, 8135, 8140, 8146, 8147,
8150, 8151, 8162, 8163, 8164, 8166, 8167, 8178, 8179, 8180, 8183, 8188, 8230, 8526, 8580, 11312,
11313, 11314, 11315, 11316, 11317, 11318, 11319, 11320, 11321, 11322, 11323, 11324, 11325, 11326, 11327, 11328,
11329, 11330, 11331, 11332, 11333, 11334, 11335, 11336, 11337, 11338, 11339, 11340, 11341, 11342, 11343, 11344,
11345, 11346, 11347, 11348, 11349, 11350, 11351, 11352, 11353, 11354, 11355, 11356, 11357, 11358, 11361, 11365,
11366, 11368, 11370, 11372, 11379, 11382, 11393, 11395, 11397, 11399, 11401, 11403, 11405, 11407, 11409, 11411,
11413, 11415, 11417, 11419, 11421, 11423, 11425, 11427, 11429, 11431, 11433, 11435, 11437, 11439, 11441, 11443,
11445, 11447, 11449, 11451, 11453, 11455, 11457, 11459, 11461, 11463, 11465, 11467, 11469, 11471, 11473, 11475,
11477, 11479, 11481, 11483, 11485, 11487, 11489, 11491, 11500, 11502, 11520, 11521, 11522, 11523, 11524, 11525,
11526, 11527, 11528, 11529, 11530, 11531, 11532, 11533, 11534, 11535, 11536, 11537, 11538, 11539, 11540, 11541,
11542, 11543, 11544, 11545, 11546, 11547, 11548, 11549, 11550, 11551, 11552, 11553, 11554, 11555, 11556, 11557,
11617, 12310, 12311, 14076, 16408, 17879, 20006, 20132, 20352, 20805, 20840, 20864, 21021, 21069, 21452, 21561,
21839, 21845, 21986, 22707, 22768, 22852, 22868, 23138, 23336, 23383, 24188, 24274, 24281, 24403, 24425, 24460,
24493, 24693, 24792, 24840, 24928, 25140, 25237, 25351, 25429, 25540, 25628, 25682, 25942, 26032, 26144, 26454,
28379, 28436, 28961, 29359, 29958, 30011, 30237, 30239, 30427, 30528, 30631, 31409, 31470, 31631, 31867, 32066,
32091, 32574, 33304, 33618, 33775, 35137, 35206, 35299, 35519, 35531, 36009, 36938, 36978, 37273, 37494, 38524,
38875, 40771, 40846, 42561, 42563, 42565, 42567, 42569, 42571, 42573, 42575, 42577, 42579, 42581, 42583, 42585,
42587, 42589, 42591, 42595, 42597, 42599, 42601, 42603, 42605, 42625, 42627, 42629, 42631, 42633, 42635, 42637,
42639, 42641, 42643, 42645, 42647, 42787, 42789, 42791, 42793, 42795, 42797, 42799, 42803, 42805, 42807, 42809,
42811, 42813, 42815, 42817, 42819, 42821, 42823, 42825, 42827, 42829, 42831, 42833, 42835, 42837, 42839, 42841,
42843, 42845, 42847, 42849, 42851, 42853, 42855, 42857, 42859, 42861, 42863, 42874, 42876, 42879, 42881, 42883,
42885, 42887, 42892, 64256, 64257, 64258, 64259, 64260, 64261, 64262, 64275, 64276, 64277, 64278, 64279, 66638,
66639, 141380, 141386, 144341, 148206, 148395, 152137, 154832, 163539,
]
__char_list_data = _all_uint32(__char_list_data)
def _char_list_data(index): return intmask(__char_list_data[index])

def char_list_data(index):
    if index < 6646:
        assert base_mod is not None
        return base_mod._char_list_data(index)
    return _char_list_data(index - 6646)

def _get_char_list(length, start):
    res = [0] * length
    for i in range(length):
        res[i] = char_list_data(start + i)
    return res
    
# estimated 9.95 KiB
__comp_pairs_pgtbl = [
0, 1, 2, 3, 4, 4, 4, 4, 4, 5, 6, 7, 4, 4, 8, 9,
10, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 11, 12, 13, 14, 15,
4, 4, 4, 4, 4, 16, 17, 18, 4, 19, 20, 21, 22, 23, 4, 4,
4, 4, 4, 24, 25, 4, 4, 26, 27, 28, 4, 4, 4, 4, 4, 4,
4, 29, 4, 4, 30, 31, 32, 33, 34, 4, 4, 4, 4, 4, 35, 4,
36, 4, 37, 38, 39, 40, 41, 4, 4, 4, 4, 4, 42, 43, 44, 4,
45, 46, 47, 4, 4, 4, 4, 4, 4, 4, 48, 49, 4, 4, 50, 51,
52, 53, 4, 4, 4, 4, 4, 54, 55, 56, 4, 4, 57, 58, 59, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 60, 61, 62, 63, 64, 4, 4,
4, 4, 4, 65, 66, 67, 4, 68, 69, 70, 71, 72, 4, 4, 4, 4,
4, 73, 74, 4, 4, 75, 76, 77, 4, 4, 4, 4, 4, 4, 4, 78,
4, 4, 79, 80, 81, 82, 83, 4, 4, 4, 4, 4, 84, 4, 85, 4,
86, 87, 88, 89, 90, 4, 4, 4, 4, 4, 91, 92, 93, 4, 94, 95,
96, 4, 4, 4, 4, 4, 4, 4, 97, 98, 4, 4, 4, 99, 100, 4,
4, 4, 4, 4, 4, 4, 101, 4, 4, 4, 4, 102, 103, 4, 4, 4,
4, 4, 4, 104, 105, 4, 4, 106, 107, 108, 109, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 110, 111, 112, 113, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 114, 115, 116, 4, 4, 4, 4, 4, 4, 4, 117, 118, 4,
4, 119, 120, 121, 4, 4, 4, 4, 4, 4, 122, 123, 4, 4, 4, 124,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 125, 4, 4, 126,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 127, 128, 129, 4, 4, 4,
4, 4, 4, 4, 130, 4, 4, 4, 131, 132, 133, 4, 4, 4, 4, 4,
4, 134, 135, 4, 4, 136, 4, 137, 138, 4, 4, 4, 4, 4, 4, 139,
140, 4, 4, 141, 142, 4, 143, 4, 4, 4, 4, 4, 4, 144, 4, 4,
4, 145, 146, 147, 148, 4, 4, 4, 4, 4, 4, 149, 4, 4, 4, 150,
151, 152, 153, 4, 4, 4, 4, 4, 154, 155, 4, 4, 156, 157, 158, 159,
160, 4, 4, 4, 4, 4, 161, 4, 4, 4, 162, 163, 164, 165, 166, 4,
4, 4, 4, 4, 167, 4, 4, 4, 4, 168, 169, 4, 170, 4, 4, 4,
4, 4, 171, 4, 4, 4, 172, 173, 174, 175, 4, 4, 4, 4, 4, 176,
177, 4, 4, 178, 179, 4, 180, 4, 4, 4, 4, 4, 4, 181, 4, 4,
4, 182, 183, 184, 4, 4, 4, 4, 4, 4, 4, 185, 4, 4, 4, 186,
4, 187, 4, 4, 4, 4, 4, 4, 4, 188, 4, 4, 4, 189, 4, 190,
4, 4, 4, 4, 4, 4, 191, 192, 4, 4, 193, 4, 194, 195, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 196, 4, 197, 198, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 199, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 200, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 201, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 202, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 203, 204, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 205, 206, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 207, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 208, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 209, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 210, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 211,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 212, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 213, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 214, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 215, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 216, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 217, 218, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
219, 220, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 221,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 222, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 223, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 224, 225, 226, 227, 4, 4, 4, 4, 4, 4, 4,
4, 4, 228, 229, 230, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
231, 4, 232, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 233, 4,
234, 235, 236, 4, 4, 4, 4, 4, 4, 4, 4, 237, 238, 239, 240, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 241, 4, 242, 243, 244, 4, 4,
4, 4, 4, 4, 4, 4, 4, 245, 4, 246, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 247, 4, 248, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 249, 250, 251, 252, 4, 4, 4, 4, 4, 4, 4, 4, 4,
253, 254, 255, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 256, 4,
257, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 258, 4, 259, 260,
261, 4, 4, 4, 4, 4, 4, 4, 4, 262, 263, 264, 265, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 266, 267, 268, 269, 4, 4, 4, 4,
4, 4, 4, 4, 4, 270, 4, 271, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 272, 4, 273, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
274, 275, 4, 276, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
277, 278, 279, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 280, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 281, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 282, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 283, 284, 285, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 286, 287, 288, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 289, 290, 291, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
292, 293, 294, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 295, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 296, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 297, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 298, 299, 300, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 301, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 302, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 303, 304, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 305,
306, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 307, 308, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 309, 310, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 311, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 312, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 313, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 314, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
315, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 316, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 317, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 318, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 319, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 320, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 321, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
322, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 323, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 324, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 325, 326, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 327, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 328, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 329, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 330, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 331, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
332, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 333, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 334, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 335, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 336, 337, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 338, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 339, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 340, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
341, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 342, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 343, 344, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 345, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 346, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 347, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 348, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 349, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
350, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 351, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 352, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 353, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 354, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 355, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 356, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
357, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 358, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 359, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 360, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 361, 4, 4, 4, 4, 4, 4, 362, 4,
4, 4, 4, 4, 4, 4, 363, 4, 4, 4, 4, 4, 364, 4, 4, 4,
4, 4, 4, 365, 366, 4, 4, 367, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 368, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 369, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
370, 371, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
372, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 373, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 374, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 375, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 376, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 377, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 378, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
379, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 380, 4, 4, 381,
4, 4, 4, 4, 4, 4, 382, 4, 4, 4, 383, 4, 384, 4, 4, 4,
4, 4, 4, 4, 385, 4, 4, 4, 386, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 387, 388, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 389, 4, 4, 390, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 391, 4, 392, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
393, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 394, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 395, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 396, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 397, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 398, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 399, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 400, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 401, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 402, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 403, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 404, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 405, 4, 4, 4, 4, 4, 4, 4, 4, 4, 406, 4,
4, 4, 407, 4, 4, 4, 4, 4, 4, 4, 4, 408, 4, 4, 4, 4,
409, 4, 410, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 411, 412,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 413, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 414, 415, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 416, 4, 417, 418, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 419, 4, 420, 4, 421, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 422, 4, 423, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 424,
425, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 426, 4, 427, 428, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 429, 4, 430, 431, 4, 4, 4,
4, 4, 4, 4, 4, 4, 432, 4, 4, 433, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 434, 4, 4, 435, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 436, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 437, 438, 4, 4, 4, 4, 4, 4, 4, 4, 4, 439, 4, 4,
440, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 441, 4, 4, 442, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 443, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 444, 445, 4, 4, 4, 4, 4,
4, 4, 4, 446, 447, 4, 4, 448, 4, 4, 4, 4, 4, 4, 4, 4,
4, 449, 450, 4, 451, 452, 4, 4, 4, 4, 4, 4, 4, 4, 453, 4,
454, 4, 455, 456, 4, 4, 4, 4, 4, 4, 4, 4, 457, 4, 458, 4,
459, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 460, 4, 461, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 462, 463, 464, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 465, 466, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 467, 468, 469, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 470, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 471, 472, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
473, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 474, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 475, 4, 476, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 477, 478, 479, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 480, 481, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 482, 483, 484, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 485, 4, 486, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 487,
488, 489, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 490, 491, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 492, 4, 493, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 494, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 495, 496, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 497, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 498, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 499,
4, 500, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 501, 502, 503,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 504, 505, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 506, 507, 508, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 509, 4, 510, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 511, 512, 513, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 514, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
515, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 516, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 517, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 518, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 519, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 520, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 521, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
522, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 523, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 524, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 525, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 526, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 527, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 528, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
529, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 530, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 531, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 532, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 533, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 534, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 535, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
536, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 537, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 538, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 539, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 540, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 541, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 542, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 543, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 544, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 545, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 546, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 547, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 548, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 549, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 550, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 551,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 552, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 553, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 554, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 555, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 556, 4, 557, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 558, 559, 560, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 561,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 562, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 563, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 564, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 565, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 566, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 567, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 568,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 569, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 570, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 571, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 572, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 573, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 574, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
575, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 576, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 577, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 578, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 579, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 580, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 581, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
582, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 583, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 584, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 585, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 586, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 587, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 588, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
589, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 590, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 591, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 592, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 593, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 594, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 595, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
596, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 597, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 598, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 599, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 600, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 601, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 602, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 603, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 604, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 605, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 606, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 607, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 608, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 609, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 610, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 611,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 612, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 613, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 614, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 615, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 616, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 617, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 618,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 619, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 620, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 621, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 622, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 623, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 624, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 625,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 626, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 627, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 628, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 629, 630, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 631, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 632, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
633, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 634, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 635, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 636, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 637, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 638, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 639, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
640, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 641, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 642, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 643, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 644, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 645, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 646, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
647, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 648, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 649, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 650, 651, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 652, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 653, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 654, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
655, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 656, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 657, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 658, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 4, 4, 659, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 4, 4, 660, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 4, 4, 661, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
4, 662, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 663,
]
__comp_pairs_pgtbl = _all_ushort(__comp_pairs_pgtbl)
def _comp_pairs_pgtbl(index): return intmask(__comp_pairs_pgtbl[index])
# estimated 10.38 KiB
__comp_pairs_pages = [
192, 193, 194, 195, 196, 197, 0, 256, 258, 260, 550, 461, 0, 0, 512, 514,
0, 0, 0, 0, 0, 0, 0, 7680, 7840, 0, 0, 0, 0, 0, 7842, 0,
262, 264, 0, 0, 0, 199, 0, 0, 0, 266, 268, 0, 0, 0, 200, 201,
202, 7868, 203, 0, 552, 274, 276, 280, 278, 282, 0, 0, 516, 518, 0, 0,
0, 0, 7864, 0, 7704, 7706, 0, 0, 7866, 0, 0, 0, 0, 204, 205, 206,
296, 207, 0, 0, 298, 300, 302, 304, 463, 0, 0, 520, 522, 0, 0, 0,
0, 7882, 0, 0, 7724, 0, 0, 7880, 504, 323, 0, 209, 0, 0, 325, 0,
0, 0, 7748, 327, 7750, 7752, 7754, 0, 0, 0, 0, 210, 211, 212, 213, 214,
0, 0, 332, 334, 490, 558, 465, 336, 416, 524, 526, 0, 0, 0, 0, 7884,
0, 7886, 0, 0, 0, 0, 217, 218, 219, 360, 220, 366, 0, 362, 364, 370,
0, 467, 368, 431, 532, 534, 0, 0, 0, 0, 7908, 0, 7798, 7796, 0, 7794,
7910, 0, 0, 0, 0, 7922, 221, 374, 7928, 376, 0, 0, 562, 0, 0, 7822,
0, 7924, 0, 0, 0, 0, 0, 7926, 224, 225, 226, 227, 228, 229, 0, 257,
259, 261, 551, 462, 0, 0, 513, 515, 0, 0, 0, 7681, 7841, 0, 0, 0,
0, 0, 7843, 0, 263, 265, 0, 0, 0, 231, 0, 0, 0, 267, 269, 0,
0, 0, 232, 233, 234, 7869, 235, 0, 553, 275, 277, 281, 279, 283, 0, 0,
517, 519, 0, 0, 0, 0, 7865, 0, 7705, 7707, 0, 0, 7867, 0, 0, 0,
0, 236, 237, 238, 297, 239, 0, 0, 299, 301, 303, 0, 464, 0, 0, 521,
523, 0, 0, 0, 0, 7883, 0, 0, 7725, 0, 0, 7881, 505, 324, 0, 241,
0, 0, 326, 0, 0, 0, 7749, 328, 7751, 7753, 7755, 0, 0, 0, 0, 242,
243, 244, 245, 246, 0, 0, 333, 335, 491, 559, 466, 337, 417, 525, 527, 0,
0, 0, 0, 7885, 0, 7887, 0, 0, 0, 0, 249, 250, 251, 361, 252, 367,
0, 363, 365, 371, 0, 468, 369, 432, 533, 535, 0, 0, 0, 0, 7909, 0,
7799, 7797, 0, 7795, 7911, 0, 0, 0, 0, 7923, 253, 375, 7929, 255, 7833, 0,
563, 0, 0, 7823, 0, 7925, 0, 0, 0, 0, 0, 7927, 0, 0, 7696, 0,
0, 0, 7690, 270, 7692, 7694, 7698, 0, 0, 7697, 0, 0, 0, 7691, 271, 0,
0, 0, 0, 7693, 7695, 7699, 0, 0, 0, 0, 0, 500, 284, 0, 0, 0,
290, 7712, 286, 0, 288, 486, 0, 0, 0, 0, 501, 285, 0, 0, 0, 291,
7713, 287, 0, 289, 487, 0, 0, 0, 0, 0, 292, 0, 7718, 0, 7720, 0,
0, 0, 7714, 542, 7716, 0, 0, 0, 7722, 0, 0, 0, 0, 293, 0, 7719,
0, 7721, 0, 0, 0, 7715, 543, 0, 0, 0, 0, 7717, 7830, 0, 0, 7723,
308, 0, 0, 0, 0, 0, 0, 309, 496, 0, 0, 0, 0, 7728, 0, 0,
0, 0, 310, 0, 0, 0, 0, 488, 7730, 7732, 0, 0, 7729, 0, 0, 0,
0, 311, 0, 0, 0, 0, 489, 0, 0, 0, 0, 7731, 7733, 0, 0, 0,
0, 0, 0, 313, 315, 0, 0, 0, 0, 317, 0, 0, 0, 0, 7734, 7738,
7740, 0, 0, 0, 0, 0, 314, 0, 0, 0, 0, 316, 318, 0, 0, 0,
0, 7735, 7739, 7741, 0, 340, 0, 0, 0, 0, 342, 0, 0, 0, 7768, 344,
0, 0, 528, 530, 7770, 7774, 0, 0, 341, 0, 0, 0, 0, 343, 0, 0,
0, 7769, 345, 0, 0, 529, 531, 0, 0, 0, 0, 7771, 7775, 0, 0, 0,
0, 0, 0, 346, 348, 0, 0, 0, 350, 0, 0, 0, 7776, 352, 0, 0,
0, 0, 536, 0, 0, 0, 7778, 0, 0, 0, 347, 349, 0, 0, 0, 351,
0, 0, 0, 7777, 353, 0, 0, 0, 0, 537, 0, 0, 0, 7779, 0, 0,
0, 0, 354, 0, 0, 0, 7786, 356, 538, 0, 0, 0, 7788, 7790, 7792, 0,
0, 0, 0, 7831, 0, 355, 0, 0, 0, 7787, 357, 0, 0, 0, 0, 539,
0, 0, 0, 7789, 7791, 7793, 0, 0, 0, 0, 7808, 7810, 372, 0, 7812, 0,
7814, 0, 0, 0, 0, 0, 7816, 0, 0, 7809, 7811, 373, 0, 7813, 7832, 0,
0, 0, 0, 7815, 0, 7817, 0, 0, 0, 377, 7824, 0, 0, 0, 379, 381,
7826, 7828, 0, 0, 378, 7825, 0, 0, 0, 380, 382, 0, 0, 0, 0, 7827,
7829, 0, 0, 0, 0, 0, 475, 471, 0, 469, 0, 0, 0, 473, 0, 0,
0, 476, 472, 0, 470, 0, 0, 0, 474, 0, 0, 0, 0, 0, 0, 478,
0, 0, 479, 0, 0, 480, 0, 0, 481, 0, 0, 0, 0, 508, 0, 0,
0, 0, 0, 482, 509, 0, 0, 0, 0, 0, 483, 0, 0, 492, 0, 0,
493, 0, 0, 0, 0, 0, 0, 494, 0, 0, 495, 0, 0, 0, 0, 506,
0, 0, 507, 0, 0, 510, 0, 0, 511, 0, 0, 0, 0, 554, 0, 0,
555, 0, 0, 0, 0, 7756, 0, 0, 7758, 0, 0, 556, 7757, 0, 0, 7759,
0, 0, 557, 0, 0, 560, 0, 0, 561, 0, 0, 0, 8173, 901, 0, 0,
0, 8129, 0, 0, 0, 0, 0, 8122, 902, 0, 0, 0, 0, 0, 8121, 8120,
0, 0, 7944, 7945, 0, 8124, 0, 0, 0, 0, 8136, 904, 0, 7960, 7961, 0,
0, 8138, 905, 0, 7976, 7977, 0, 8140, 8154, 906, 0, 0, 938, 0, 0, 8153,
8152, 0, 0, 0, 0, 0, 0, 7992, 7993, 0, 0, 0, 0, 0, 0, 8184,
908, 0, 0, 0, 0, 0, 8008, 8009, 0, 0, 8170, 910, 0, 0, 939, 0,
0, 8169, 8168, 0, 0, 0, 8025, 0, 0, 8186, 911, 0, 8040, 8041, 0, 8188,
8146, 912, 0, 0, 0, 8151, 0, 0, 0, 0, 0, 8048, 940, 0, 0, 0,
0, 0, 8113, 8112, 0, 0, 7936, 7937, 8118, 8115, 0, 0, 0, 0, 8050, 941,
0, 7952, 7953, 0, 0, 8052, 942, 0, 7968, 7969, 8134, 8131, 8054, 943, 0, 0,
970, 0, 0, 8145, 8144, 0, 0, 0, 0, 0, 0, 7984, 7985, 8150, 0, 0,
0, 0, 0, 8162, 944, 0, 0, 0, 8167, 0, 0, 0, 0, 0, 8058, 973,
0, 0, 971, 0, 0, 8161, 8160, 0, 0, 8016, 8017, 8166, 0, 8056, 972, 0,
8000, 8001, 0, 0, 8060, 974, 0, 0, 0, 0, 0, 8032, 8033, 8182, 8179, 0,
979, 0, 0, 980, 0, 0, 1024, 0, 0, 0, 1025, 0, 0, 0, 1238, 0,
0, 0, 1027, 0, 1031, 0, 0, 0, 1036, 0, 0, 0, 0, 0, 1037, 0,
0, 0, 1252, 0, 0, 1250, 1049, 0, 0, 1264, 0, 0, 1262, 1038, 0, 0,
0, 1266, 0, 0, 1117, 0, 0, 0, 1253, 0, 0, 1251, 1081, 0, 0, 0,
0, 0, 0, 1104, 0, 0, 0, 1105, 0, 0, 0, 1239, 0, 0, 0, 1107,
0, 1111, 0, 0, 0, 1116, 0, 0, 0, 0, 0, 1265, 0, 0, 1263, 1118,
0, 0, 0, 1267, 1142, 0, 0, 0, 0, 0, 0, 1143, 1244, 0, 0, 0,
1217, 0, 0, 0, 0, 0, 0, 1245, 0, 0, 0, 1218, 0, 0, 1234, 0,
0, 0, 1232, 0, 0, 1235, 0, 0, 0, 1233, 0, 0, 1242, 0, 0, 0,
0, 0, 0, 1243, 0, 0, 1246, 0, 0, 1247, 0, 0, 1254, 0, 0, 0,
0, 0, 0, 1255, 0, 0, 1258, 0, 0, 1259, 0, 0, 1260, 0, 0, 0,
0, 0, 0, 1261, 0, 0, 1268, 0, 0, 1269, 0, 0, 1272, 0, 0, 0,
0, 0, 0, 1273, 0, 0, 0, 1570, 1571, 1573, 0, 0, 0, 0, 0, 1572,
0, 0, 1574, 0, 0, 1728, 0, 0, 1730, 0, 0, 0, 0, 0, 0, 1747,
2345, 0, 0, 0, 0, 0, 0, 2353, 0, 0, 2356, 0, 0, 0, 2507, 2508,
0, 0, 0, 2888, 2891, 2892, 0, 0, 0, 2964, 0, 0, 3020, 3018, 0, 0,
3019, 0, 0, 0, 3144, 0, 0, 0, 3264, 0, 0, 0, 0, 0, 0, 3271,
3272, 3274, 0, 0, 0, 0, 3275, 0, 3402, 3404, 0, 0, 0, 0, 0, 3403,
3546, 3548, 3550, 0, 0, 0, 0, 3549, 0, 4134, 0, 0, 0, 6918, 0, 0,
6920, 0, 0, 0, 0, 0, 0, 6922, 0, 0, 6924, 0, 0, 6926, 0, 0,
6930, 0, 0, 0, 0, 0, 0, 6971, 0, 0, 6973, 0, 0, 6976, 0, 0,
6977, 0, 0, 0, 0, 0, 0, 6979, 0, 0, 7682, 0, 7684, 7686, 0, 0,
0, 7683, 0, 0, 0, 0, 0, 7685, 7687, 0, 0, 0, 0, 0, 0, 7688,
0, 0, 7689, 0, 7700, 7702, 0, 0, 0, 0, 0, 7701, 7703, 0, 0, 0,
0, 0, 7708, 0, 0, 7709, 0, 0, 0, 0, 7710, 0, 0, 7711, 0, 0,
0, 0, 0, 7726, 0, 0, 7727, 0, 0, 0, 0, 7736, 0, 0, 7737, 0,
0, 0, 0, 7742, 7744, 0, 0, 0, 0, 0, 7746, 0, 0, 0, 7743, 0,
0, 0, 0, 7745, 0, 7747, 0, 0, 7760, 7762, 0, 0, 0, 0, 0, 7761,
7763, 0, 0, 0, 0, 0, 0, 7764, 7766, 0, 0, 0, 0, 0, 7765, 0,
0, 0, 0, 7767, 0, 0, 0, 7772, 0, 0, 7773, 0, 7780, 0, 0, 0,
0, 0, 0, 7781, 0, 0, 7782, 0, 0, 7783, 0, 0, 7784, 0, 0, 0,
0, 0, 0, 7785, 0, 7800, 0, 0, 7801, 0, 0, 0, 0, 0, 7802, 0,
0, 7803, 0, 0, 0, 0, 0, 7804, 7806, 0, 0, 0, 0, 0, 7805, 0,
0, 0, 0, 7807, 0, 0, 7820, 0, 7818, 0, 0, 0, 0, 7821, 0, 0,
0, 0, 0, 7819, 0, 0, 7835, 0, 0, 0, 0, 7846, 7844, 0, 7850, 0,
0, 7848, 0, 0, 0, 0, 7847, 7845, 0, 7851, 0, 0, 7849, 0, 0, 0,
0, 0, 0, 7852, 0, 7862, 0, 0, 0, 0, 7853, 0, 7863, 0, 0, 0,
0, 0, 0, 7856, 7854, 0, 7860, 0, 0, 7858, 0, 0, 0, 0, 7857, 7855,
0, 7861, 0, 0, 7859, 0, 0, 0, 0, 7872, 7870, 0, 7876, 0, 0, 0,
0, 0, 0, 7874, 7873, 7871, 0, 7877, 0, 0, 7875, 0, 0, 7878, 0, 0,
7879, 0, 0, 0, 0, 7890, 7888, 0, 7894, 0, 0, 0, 0, 0, 0, 7892,
7891, 7889, 0, 7895, 0, 0, 7893, 0, 0, 7896, 0, 0, 7897, 0, 0, 0,
0, 7900, 7898, 0, 7904, 0, 0, 0, 0, 7906, 0, 0, 0, 0, 0, 7902,
7901, 7899, 0, 7905, 7907, 0, 0, 0, 0, 0, 7903, 0, 0, 0, 0, 7914,
7912, 0, 7918, 0, 0, 0, 0, 7920, 0, 7916, 0, 0, 0, 0, 7915, 7913,
0, 7919, 0, 0, 0, 0, 7921, 0, 7917, 0, 0, 0, 0, 7938, 7940, 0,
0, 0, 7942, 8064, 7939, 7941, 0, 0, 0, 7943, 8065, 0, 0, 0, 0, 7946,
7948, 0, 0, 0, 7950, 8072, 0, 0, 0, 0, 7947, 7949, 0, 0, 0, 7951,
8073, 0, 0, 0, 0, 7954, 7956, 0, 7955, 7957, 0, 0, 0, 0, 0, 7962,
7964, 0, 0, 0, 0, 0, 7963, 7965, 0, 7970, 7972, 0, 0, 0, 7974, 8080,
7971, 7973, 0, 0, 0, 7975, 8081, 0, 0, 0, 0, 7978, 7980, 0, 0, 0,
7982, 8088, 0, 0, 0, 0, 7979, 7981, 0, 0, 0, 7983, 8089, 0, 0, 0,
0, 7986, 7988, 0, 0, 0, 7990, 0, 7987, 7989, 0, 0, 0, 7991, 0, 0,
0, 0, 0, 7994, 7996, 0, 0, 0, 7998, 0, 0, 0, 0, 0, 7995, 7997,
0, 0, 0, 7999, 0, 8002, 8004, 0, 8003, 8005, 0, 0, 0, 0, 0, 8010,
8012, 0, 0, 0, 0, 0, 8011, 8013, 0, 8018, 8020, 0, 0, 0, 8022, 0,
8019, 8021, 0, 0, 0, 8023, 0, 0, 0, 0, 0, 8027, 8029, 0, 0, 0,
8031, 0, 0, 0, 0, 0, 8034, 8036, 0, 0, 0, 8038, 8096, 0, 0, 0,
0, 8035, 8037, 0, 0, 0, 8039, 8097, 8042, 8044, 0, 0, 0, 8046, 8104, 0,
0, 0, 0, 8043, 8045, 0, 0, 0, 8047, 8105, 0, 0, 8066, 0, 0, 0,
0, 0, 0, 8067, 0, 0, 8068, 0, 0, 8069, 0, 0, 8070, 0, 0, 0,
0, 0, 0, 8071, 0, 0, 8074, 0, 0, 8075, 0, 0, 8076, 0, 0, 0,
0, 0, 0, 8077, 0, 0, 8078, 0, 0, 8079, 0, 0, 8082, 0, 0, 0,
0, 0, 0, 8083, 0, 0, 8084, 0, 0, 8085, 0, 0, 8086, 0, 0, 0,
0, 0, 0, 8087, 0, 0, 8090, 0, 0, 8091, 0, 0, 8092, 0, 0, 0,
0, 0, 0, 8093, 0, 0, 8094, 0, 0, 8095, 0, 0, 8098, 0, 0, 0,
0, 0, 0, 8099, 0, 0, 8100, 0, 0, 8101, 0, 0, 8102, 0, 0, 0,
0, 0, 0, 8103, 0, 0, 8106, 0, 0, 8107, 0, 0, 8108, 0, 0, 0,
0, 0, 0, 8109, 0, 0, 8110, 0, 0, 8111, 0, 0, 8114, 0, 0, 0,
0, 0, 0, 8116, 0, 0, 8119, 0, 0, 8130, 0, 0, 8132, 0, 0, 0,
0, 0, 0, 8135, 8141, 8142, 0, 0, 0, 8143, 0, 0, 0, 0, 0, 8157,
8158, 0, 0, 0, 8159, 0, 0, 0, 0, 8164, 8165, 0, 0, 8172, 0, 0,
0, 0, 8178, 0, 0, 8180, 0, 0, 8183, 0, 0, 0, 8602, 0, 0, 0,
0, 0, 0, 8603, 0, 0, 8622, 0, 0, 8653, 0, 0, 8654, 0, 0, 0,
0, 0, 0, 8655, 0, 0, 8708, 0, 0, 8713, 0, 0, 8716, 0, 0, 0,
0, 0, 0, 8740, 0, 0, 8742, 0, 0, 8769, 0, 0, 8772, 0, 0, 0,
0, 0, 0, 8775, 0, 0, 8777, 0, 0, 8800, 0, 0, 8802, 0, 0, 0,
0, 0, 0, 8813, 0, 0, 8814, 0, 0, 8815, 0, 0, 8816, 0, 0, 0,
0, 0, 0, 8817, 0, 0, 8820, 0, 0, 8821, 0, 0, 8824, 0, 0, 0,
0, 0, 0, 8825, 0, 0, 8832, 0, 0, 8833, 0, 0, 8836, 0, 0, 0,
0, 0, 0, 8837, 0, 0, 8840, 0, 0, 8841, 0, 0, 8876, 0, 0, 0,
0, 0, 0, 8877, 0, 0, 8878, 0, 0, 8879, 0, 0, 8928, 0, 0, 0,
0, 0, 0, 8929, 0, 0, 8930, 0, 0, 8931, 0, 0, 8938, 0, 0, 0,
0, 0, 0, 8939, 0, 0, 8940, 0, 0, 8941, 0, 0, 0, 12364, 0, 0,
12366, 0, 0, 0, 0, 0, 0, 12368, 0, 0, 12370, 0, 0, 12372, 0, 0,
12374, 0, 0, 0, 0, 0, 0, 12376, 0, 0, 12378, 0, 0, 12380, 0, 0,
12382, 0, 0, 0, 0, 0, 0, 12384, 0, 0, 12386, 0, 0, 12389, 0, 0,
12391, 0, 0, 0, 0, 0, 0, 12393, 0, 0, 12400, 12401, 0, 12403, 12404, 0,
12406, 12407, 0, 0, 0, 0, 0, 12409, 12410, 0, 0, 0, 0, 0, 12412, 12413,
0, 12436, 0, 0, 12446, 0, 0, 0, 0, 0, 0, 12460, 0, 0, 12462, 0,
0, 12464, 0, 0, 12466, 0, 0, 0, 0, 0, 0, 12468, 0, 0, 12470, 0,
0, 12472, 0, 0, 12474, 0, 0, 0, 0, 0, 0, 12476, 0, 0, 12478, 0,
0, 12480, 0, 0, 12482, 0, 0, 0, 0, 0, 0, 12485, 0, 0, 12487, 0,
0, 12489, 0, 0, 12496, 12497, 0, 0, 0, 0, 0, 12499, 12500, 0, 0, 0,
0, 0, 12502, 12503, 0, 12505, 12506, 0, 12508, 12509, 0, 0, 0, 0, 0, 12532,
0, 0, 12535, 0, 0, 12536, 0, 0, 12537, 0, 0, 0, 0, 0, 0, 12538,
0, 0, 12542, 0, 0, 0, 0, 69786, 0, 0, 69788, 0, 0, 69803,
]
__comp_pairs_pages = _all_uint32(__comp_pairs_pages)
def _comp_pairs_pages(index): return intmask(__comp_pairs_pages[index])

def _composition(code):
    return _comp_pairs_pages((_comp_pairs_pgtbl(code >> 2) << 2) + (code & 3))


def lookup_composition_prefix_index(index):
    if 54 <= index <= 4343:
        return lookup_composition_prefix_index_middle(index - 54)
    if index < 54:
        return 0
    if index < 4821:
        return 0
    raise KeyError

_lookup_composition_prefix_index_middle = (
'\x01\x02\x03\x02\x03\x03\x02\x02\x02\x03\x03\x04\x04\x04\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02'
'\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x00\x00\x02\x02\x02'
'\x02\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00'
'\x02\x00\x00\x02\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02'
'\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x05\x05\x05\x05\x05\x05\x05\x05\x05\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x02\x02\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x02\x01\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05\x05'
'\x05\x05\x05\x02\x02\x02\x06\x02\x02\x02\x02\x02\x06\x06\x06\x06\x06\x06\x06\x06'
'\x02\x06\x06\x06\x03\x02\x03\x06\x00\x00\x00\x06\x06\x06\x06\x06\x06\x02\x02\x02'
'\x02\x06\x02\x06\x06\x06\x06\x06\x06\x06\x06\x04\x04\x04\x04\x04\x04\x04\x04\x04'
'\x04\x04\x04\x04\x04\x04\x04\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x04'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x02\x02\x02\x02\x00\x05\x03\x03\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x08\x00\x00\x02\x02\x02'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x00\x00\t\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x07\x07\x07\x07\n\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\n\n\n\n\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'
'\x07\x07\x07\x07\x07\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\n\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00'
'\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x02\x0b\x0c\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r'
'\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r'
'\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c\x0b\x0c\x0b'
'\x0c\x0b\x0c\x0b\x0c\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r'
'\x0e\x0b\x0c\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\x0b'
'\x0c\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c'
'\r\x0e\r\x0e\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\r\x0b'
'\x0c\r\x0b\x0c\r\x0e\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
'\x0b\x0b\x0b\x0b\x0b\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c'
'\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c'
'\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\r\r\r\r\r'
'\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r'
'\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r'
'\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r'
'\r\r\r\r\r\r\r\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e'
'\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0c\x0c\x0c'
'\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c'
'\x0c\x0c\x0c\x0c\x0c\r\r\r\r\r\r\r\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e'
'\x0c\x0b\r\x0c\r\r\r\r\r\r\x0c\r\x0c\x0c\r\r\x0c\x0c\r\r'
'\x0c\r\x0c\r\x0c\x0c\r\x0c\x0c\r\x0c\r\x0c\x0c\r\x0c\r\r\x0c\x0c'
'\x0c\r\x0c\x0c\x0c\x0c\x0c\r\x0c\x0c\x0c\x0c\x0c\r\x0c\x0c\r\x0c\r\r'
'\r\x0c\r\r\r\r\r\r\r\r\x0c\x0c\r\x0c\x0c\x0c\x0c\r\x0c\x0c'
'\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c'
'\r\r\x0c\x0c\r\x0c\r\x0c\x0c\x0c\x0c\x0c\x0c\x0c\x0c\r\r\r\x0c\x0c'
'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\t\t\t\t\t\t\t'
'\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t'
'\t\t\t\t\t\x02\x02\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f'
'\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0b\x0e\x0b\x0b\x0b\x0e\x0b'
'\x0e\x0b\x0e\x0b\x0e\x0b\x0e\x0b\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\r\x0e'
'\x0b\x0c\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e'
'\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\r\x0e'
'\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e'
'\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e'
'\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c'
'\x0b\x0c\r\x0e\x0b\x0c\x0b\x0c\x0b\x0c\x0b\x0c\x08\x08\x08\x08\x08\x08\x08\x08'
'\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08'
'\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08'
'\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08'
'\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08'
'\x08\x08\x08\x08\x08\x08\x08\x08\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10'
'\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10'
'\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10'
'\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10'
'\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10'
'\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10'
'\x10\x10\x10\x08\x08\x08\x08\x08\x08\x08\x10\x10\x10\x10\x10\x10\x10\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x06'
'\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06'
'\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06'
'\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06'
'\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06'
'\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x06\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x07\x07\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\x02\x02\x02\x02\x02\x02\x02\x02\x02'
)
def lookup_composition_prefix_index_middle(index): return ord(_lookup_composition_prefix_index_middle[index])

def lookup_composition_decomp_len(index):
    if 54 <= index <= 4343:
        return lookup_composition_decomp_len_middle(index - 54)
    if index < 54:
        return 0
    if index < 4821:
        return 1
    raise KeyError

_lookup_composition_decomp_len_middle = (
'\x01\x02\x01\x02\x01\x01\x02\x01\x02\x01\x01\x03\x03\x03\x02\x02\x02\x02\x02\x02'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x01\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02'
'\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x01\x01\x00\x01\x02\x00\x00\x00\x01\x02\x01\x02\x02\x01\x02\x02\x02'
'\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x02\x00'
'\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x01\x01\x01\x02\x02\x01\x01\x01'
'\x01\x01\x01\x01\x01\x02\x02\x02\x00\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x02'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x02'
'\x02\x02\x00\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x02\x00\x02\x00\x00\x00'
'\x02\x00\x02\x00\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00\x02\x02'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x02\x02\x02\x00\x00\x02\x02\x00'
'\x02\x00\x00\x00\x02\x02\x02\x00\x00\x02\x00\x00\x00\x02\x00\x00\x02\x02\x02\x02'
'\x00\x00\x00\x00\x00\x02\x02\x02\x00\x00\x00\x00\x02\x02\x02\x02\x00\x02\x00\x00'
'\x02\x00\x00\x02\x02\x01\x00\x02\x02\x02\x02\x02\x02\x00\x00\x02\x00\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x00\x01\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x00\x02\x00\x02\x00\x00\x02\x02\x00\x02\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x01'
'\x02\x01\x02\x01\x02\x01\x02\x01\x02\x01\x02\x01\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x01\x02\x02\x01\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x01\x02\x01\x02\x02\x02\x02\x02\x02\x02\x01\x02\x02\x02\x02\x02\x01'
'\x02\x02\x02\x02\x02\x02\x01\x02\x02\x02\x02\x02\x02\x02\x01\x02\x02\x01\x01\x02'
'\x02\x02\x02\x02\x02\x01\x02\x01\x02\x01\x02\x01\x01\x01\x01\x02\x01\x02\x03\x02'
'\x03\x02\x03\x02\x02\x02\x02\x02\x04\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x02\x03\x03\x01\x02\x03\x03\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x02\x01\x01\x01\x02\x03\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x03\x01\x01\x01\x01\x01\x01\x01\x01\x03\x03\x04\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x02\x01\x02\x03\x02\x01\x02\x03\x04\x02\x01\x02\x03\x01'
'\x01\x01\x01\x01\x02\x03\x02\x01\x02\x03\x04\x02\x01\x02\x03\x01\x01\x01\x01\x03'
'\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x02\x00\x02\x00\x02\x00\x02'
'\x00\x02\x02\x03\x02\x03\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x00'
'\x02\x02\x02\x02\x02\x00\x00\x02\x02\x00\x00\x02\x02\x00\x00\x00\x00\x02\x02\x00'
'\x00\x02\x02\x00\x00\x02\x02\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x00\x00\x00'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x04\x03\x02\x03\x02\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x01\x01\x01'
'\x00\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02'
'\x00\x02\x02\x00\x02\x02\x02\x00\x00\x02\x02\x00\x02\x02\x00\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02'
'\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x04\x04\x04\x04\x04\x04'
'\x04\x04\x04\x04\x04\x04\x04\x04\x04\x07\x06\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x01\x01\x01\x01\x03\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x05\x04\x02\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x02\x03\x02\x03\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x04\x04\x04\x03\x04\x03\x03\x05\x04\x03\x03\x03\x04\x04\x03'
'\x03\x02\x03\x04\x04\x02\x05\x06\x05\x03\x05\x05\x04\x03\x03\x03\x04\x05\x04\x03'
'\x03\x03\x02\x02\x02\x02\x03\x03\x05\x03\x04\x05\x03\x02\x02\x05\x04\x05\x03\x05'
'\x02\x03\x03\x03\x03\x03\x04\x03\x02\x03\x03\x03\x04\x03\x03\x03\x05\x04\x02\x05'
'\x02\x04\x04\x03\x03\x03\x04\x02\x03\x04\x02\x05\x03\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02'
'\x02\x03\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x04\x02\x02\x02\x02\x02\x02\x02'
'\x02\x03\x04\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x03\x03\x02\x03\x03\x03\x02\x03\x03\x04\x02\x03\x03\x03\x03\x05'
'\x06\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x04'
'\x02\x02\x02\x04\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x02\x02\x03\x03'
'\x02\x04\x03\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03'
'\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x04\x04\x04\x04\x04\x04\x04\x03\x12\x08\x04\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x02\x00'
'\x02\x00\x02\x00\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x01\x01\x01\x01'
'\x01\x02\x02\x02\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x03\x03\x03\x03\x03\x03\x03\x03\x03'
)
def lookup_composition_decomp_len_middle(index): return ord(_lookup_composition_decomp_len_middle[index])

def lookup_composition_decomp(index):
    if 54 <= index <= 4819:
        return lookup_composition_decomp_middle(index - 54)
    if index < 54:
        return 0
    if index < 4821:
        return 6645
    raise KeyError

# estimated 9.32 KiB
_lookup_composition_decomp_middle = [
2399, 684, 6805, 2371, 6886, 6888, 2367, 3593, 2383, 6884, 3115, 1086, 1080, 1158, 2469, 2471,
1194, 2473, 1212, 1215, 0, 1227, 2521, 2523, 1245, 2531, 2589, 2591, 2593, 1266, 2675, 2689,
2691, 1287, 1296, 1308, 0, 2757, 2759, 2761, 1368, 2811, 2839, 2841, 1404, 2843, 1422, 1425,
0, 1455, 2899, 2901, 1470, 2909, 2969, 2971, 2973, 1494, 3085, 3101, 3103, 1548, 1557, 1569,
0, 3177, 3179, 3181, 1620, 3231, 3241, 2475, 2845, 1206, 1416, 2487, 2857, 2497, 2869, 2499,
2871, 2501, 2873, 2503, 2875, 2511, 2887, 1251, 1476, 2527, 2905, 2529, 2907, 2541, 2919, 2535,
2913, 2555, 2931, 2559, 2935, 2561, 2937, 2565, 2941, 2569, 2945, 2595, 2975, 2597, 2977, 2599,
2979, 2613, 2993, 2601, 2583, 2961, 2617, 2997, 2631, 3017, 2641, 3035, 2645, 3039, 2643, 3037,
2639, 3033, 2673, 3083, 2683, 3093, 2679, 3089, 3489, 1302, 1563, 2693, 3105, 2697, 3109, 2715,
3133, 2725, 3143, 2719, 3137, 1338, 1596, 2733, 3153, 2739, 3159, 1341, 1599, 2751, 3171, 2745,
3165, 1353, 1605, 1356, 1608, 2763, 3183, 2767, 3187, 2769, 3189, 2781, 3201, 2797, 3215, 2813,
3233, 2821, 2827, 3249, 2831, 3253, 1231, 1459, 6929, 1323, 1584, 1383, 1635, 0, 2505, 2507,
2883, 2635, 2637, 3025, 2665, 2667, 3075, 2479, 2849, 2605, 2985, 2699, 3111, 2771, 3191, 3319,
3373, 3317, 3371, 3321, 3375, 3315, 3369, 3277, 3331, 3475, 3477, 3283, 3337, 2563, 2939, 2627,
3013, 1329, 1590, 3471, 3473, 3469, 3487, 2999, 1230, 1233, 1458, 2553, 2929, 2671, 3081, 3279,
3333, 3281, 3335, 3313, 3367, 2481, 2851, 2483, 2853, 2537, 2915, 2539, 2917, 2607, 2987, 2609,
2989, 2701, 3113, 2703, 3115, 2721, 3139, 2723, 3141, 2773, 3193, 2775, 3195, 2737, 3157, 2749,
3169, 2575, 2951, 1209, 1419, 1257, 1482, 3311, 3365, 3307, 3361, 1305, 1566, 3483, 3485, 2817,
3237, 0, 2959, 4923, 3076, 6802, 4929, 4930, 4932, 3223, 3247, 2375, 2377, 2379, 2385, 2369,
2381, 4922, 6911, 6929, 3227, 4937, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 6839, 6842, 0, 6963, 6832, 0, 0, 0, 4938,
2391, 4757, 3261, 3493, 3034, 3503, 3507, 3513, 3523, 3529, 3539, 3619, 0, 0, 0, 0,
0, 0, 0, 0, 6825, 6834, 1713, 3561, 1743, 3569, 3625, 0, 0, 0, 0, 0,
0, 0, 0, 1764, 1803, 3597, 3605, 1827, 4967, 4971, 6964, 3633, 3635, 4980, 4976, 4972,
3601, 4977, 4952, 3561, 4959, 3645, 3649, 3643, 0, 3637, 3665, 3657, 3671, 0, 0, 0,
0, 0, 0, 3661, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
3705, 0, 0, 0, 0, 0, 0, 3689, 3693, 3687, 0, 3727, 3709, 3701, 3715, 0,
0, 3729, 3731, 3651, 3695, 3639, 3683, 3641, 3685, 3647, 3691, 0, 0, 3733, 3735, 3653,
3697, 3655, 3699, 3659, 3703, 3663, 3707, 3667, 3711, 0, 0, 3737, 3739, 3681, 3725, 3669,
3713, 3673, 3717, 3675, 3719, 3677, 3721, 3679, 3723, 3741, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2041,
2044, 4021, 2047, 2199, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
3853, 4023, 4043, 4039, 4047, 0, 4041, 0, 4045, 0, 0, 0, 4061, 0, 4067, 0,
4069, 0, 0, 4049, 4051, 4053, 4055, 4057, 4059, 4063, 4065, 0, 0, 0, 4077, 4079,
0, 4071, 4073, 4075, 4089, 4091, 4081, 4083, 4085, 4087, 0, 0, 4099, 4097, 4101, 0,
0, 4093, 4095, 0, 4103, 0, 0, 0, 4105, 4109, 4107, 0, 0, 4111, 0, 0,
0, 4113, 0, 0, 4115, 4117, 2202, 4119, 0, 0, 0, 0, 0, 4121, 4125, 4123,
0, 0, 0, 0, 4127, 2205, 4131, 4129, 0, 4133, 0, 0, 4139, 0, 0, 4135,
4137, 5184, 0, 4143, 4145, 4147, 4149, 4151, 4141, 0, 0, 4153, 0, 4155, 4169, 4171,
4173, 4175, 2212, 4159, 4161, 4163, 4165, 4167, 4157, 0, 4177, 0, 7156, 0, 6994, 0,
6996, 0, 6998, 0, 7000, 0, 7002, 0, 7004, 0, 0, 7006, 0, 7008, 0, 0,
7010, 7012, 0, 7014, 6902, 3283, 6676, 6923, 6785, 7089, 6691, 6916, 6918, 6920, 6703, 6777,
6709, 6943, 6715, 7093, 6783, 6724, 6932, 6919, 6936, 7104, 7105, 7157, 3052, 6798, 6940, 4919,
4920, 7108, 6915, 3023, 6799, 4829, 4916, 7158, 7159, 3131, 6931, 3205, 7161, 4926, 3209, 7162,
4967, 4968, 4969, 4980, 4981, 6909, 6802, 3205, 3209, 4967, 4968, 3601, 4980, 4981, 5010, 7106,
3126, 7107, 4786, 6775, 7109, 7110, 7111, 4924, 4925, 7112, 7164, 7126, 7114, 7166, 7127, 7116,
7115, 4927, 7117, 7118, 4928, 7119, 7121, 4933, 7091, 7122, 4935, 7160, 4936, 7123, 3257, 7124,
7125, 3487, 4971, 0, 2485, 2855, 2491, 2859, 2493, 2861, 2495, 2863, 3285, 3339, 2509, 2885,
2513, 2889, 2519, 2895, 2515, 2891, 2517, 2893, 3393, 3397, 3395, 3399, 2543, 2921, 2545, 2923,
3479, 3481, 2547, 2927, 2557, 2933, 2571, 2947, 2577, 2953, 2573, 2949, 2579, 2955, 2581, 2957,
2615, 2995, 3295, 3349, 2625, 3011, 2629, 3015, 2633, 3019, 1269, 1518, 4179, 4181, 2649, 3043,
2647, 3041, 2657, 3059, 2659, 3061, 2661, 3063, 2677, 3087, 2681, 3091, 2687, 3097, 2685, 3095,
3305, 3359, 3309, 3363, 3401, 3405, 3403, 3407, 2709, 3129, 2711, 3131, 2717, 3135, 1335, 1593,
4183, 4185, 2727, 3145, 2735, 3155, 1344, 1602, 3409, 3411, 3413, 3415, 4187, 4189, 2743, 3161,
2747, 3167, 2755, 3175, 2753, 3173, 2779, 3199, 2785, 3205, 2783, 3203, 3417, 3419, 3421, 3423,
2787, 3207, 2789, 3209, 2793, 3211, 2795, 3213, 2801, 3219, 2799, 3217, 2803, 3223, 2805, 3225,
2807, 3227, 2819, 3239, 2829, 3251, 2833, 3255, 2835, 3257, 2959, 3163, 3221, 3245, 2837, 3427,
1221, 1431, 2477, 2847, 3271, 3325, 3269, 3323, 3275, 3329, 3273, 3327, 4191, 4195, 3379, 3387,
3377, 3385, 3383, 3391, 3381, 3389, 4193, 4197, 1254, 1479, 2533, 2911, 2525, 2903, 3289, 3343,
3287, 3341, 3293, 3347, 3291, 3345, 4199, 4201, 2603, 2983, 2611, 2991, 1326, 1587, 2695, 3107,
3299, 3353, 3297, 3351, 3303, 3357, 3301, 3355, 4203, 4205, 3431, 3441, 3429, 3439, 3435, 3445,
3433, 3443, 3437, 3447, 2777, 3197, 2765, 3185, 3451, 3461, 3449, 3459, 3455, 3465, 3453, 3463,
3457, 3467, 2809, 3229, 2825, 3247, 2823, 3243, 2815, 3235, 1716, 1719, 4207, 4217, 4209, 4219,
4211, 4221, 1641, 1644, 4251, 4259, 4253, 4261, 4255, 4263, 1731, 1737, 4279, 4283, 4281, 4285,
1650, 1656, 4287, 4291, 4289, 4293, 1746, 1749, 4295, 4305, 4297, 4307, 4299, 4309, 1659, 1662,
4339, 4347, 4341, 4349, 4343, 4351, 1773, 1782, 4367, 4373, 4369, 4375, 4371, 4377, 1671, 1680,
4379, 4385, 4381, 4387, 4383, 4389, 1788, 1794, 4391, 4395, 4393, 4397, 1686, 1692, 4399, 4403,
4401, 4405, 1812, 1821, 4407, 4413, 4409, 4415, 4411, 4417, 1701, 4419, 4421, 4423, 1830, 1833,
4425, 4435, 4427, 4437, 4429, 4439, 1704, 1707, 4469, 4477, 4471, 4479, 4473, 4481, 1710, 3545,
3559, 4964, 1740, 3549, 3567, 4965, 3595, 4983, 3603, 4984, 1824, 3631, 4213, 4223, 4227, 4231,
4235, 4239, 4243, 4247, 4257, 4265, 4267, 4269, 4271, 4273, 4275, 4277, 4301, 4311, 4315, 4319,
4323, 4327, 4331, 4335, 4345, 4353, 4355, 4357, 4359, 4361, 4363, 4365, 4431, 4441, 4445, 4449,
4453, 4457, 4461, 4465, 4475, 4483, 4485, 4487, 4489, 4491, 4493, 4495, 3553, 3551, 4497, 3555,
3543, 1725, 4509, 3497, 3495, 3491, 6946, 3499, 693, 4508, 693, 2389, 3263, 4501, 3563, 3547,
1755, 4517, 3501, 4941, 3505, 6950, 3509, 4511, 4513, 4515, 3573, 3571, 3617, 4947, 3575, 3621,
3517, 3515, 3511, 4943, 4521, 4523, 4525, 3609, 3607, 3623, 4966, 3599, 3601, 3611, 3627, 3533,
3531, 3527, 4945, 3525, 3259, 4939, 4765, 4505, 3613, 3629, 1839, 4519, 3521, 4944, 3537, 6954,
3541, 4776, 702, 5412, 5413, 2399, 5414, 2387, 1226, 979, 978, 532, 531, 2215, 2214, 2402,
2373, 2465, 2463, 2464, 530, 6882, 6909, 6890, 6892, 6894, 6896, 6898, 6900, 4754, 5441, 2459,
6747, 6749, 3490, 6882, 6884, 6886, 6888, 6890, 6892, 6894, 6896, 6898, 6900, 4754, 5441, 2459,
6747, 6749, 6805, 6940, 3115, 3227, 4919, 2713, 1389, 1392, 6904, 3265, 1437, 1440, 4853, 3267,
6915, 6916, 2959, 4813, 6918, 6777, 6911, 6943, 2669, 6783, 6721, 6724, 2729, 1347, 2741, 6935,
6966, 6703, 3279, 6676, 6940, 6785, 6910, 6709, 3115, 3759, 3763, 3765, 3767, 6909, 6762, 4976,
4968, 4949, 4958, 5440, 6923, 6798, 3076, 6753, 6756, 6664, 1083, 1146, 1089, 1149, 1161, 1167,
1092, 1170, 1095, 1164, 1173, 1176, 6756, 6918, 1387, 339, 2585, 6941, 2586, 338, 338, 2587,
6764, 2588, 1386, 6777, 6904, 6923, 6709, 6909, 1639, 363, 2965, 3209, 2966, 362, 362, 2967,
3227, 2968, 1638, 6911, 3126, 6798, 6799, 6750, 0, 0, 0, 4527, 4529, 4531, 4533, 4537,
4535, 0, 0, 0, 0, 4539, 0, 4541, 0, 4543, 0, 4545, 0, 4547, 536, 535,
2218, 2217, 0, 4549, 0, 4551, 0, 4553, 0, 4555, 0, 2459, 0, 4559, 0, 0,
4557, 2457, 2461, 4561, 4563, 0, 0, 4565, 4567, 0, 0, 4569, 4571, 0, 0, 0,
0, 4573, 4575, 0, 0, 4581, 4583, 0, 0, 4585, 4587, 0, 0, 0, 0, 0,
0, 4593, 4595, 4597, 4599, 0, 0, 0, 0, 4577, 4579, 4589, 4591, 4601, 4603, 4605,
4607, 5475, 5476, 6884, 6886, 6888, 6890, 6892, 6894, 6896, 6898, 6900, 6666, 1002, 1014, 1023,
2426, 1041, 1050, 1059, 1068, 1077, 1104, 723, 726, 729, 732, 735, 738, 741, 744, 747,
230, 234, 238, 242, 246, 250, 254, 258, 262, 266, 270, 994, 1006, 1018, 1027, 1036,
1045, 1054, 1063, 1072, 981, 993, 1005, 1017, 1026, 1035, 1044, 1053, 1062, 1071, 1098, 750,
753, 756, 759, 762, 765, 768, 771, 774, 777, 780, 783, 786, 789, 792, 795, 798,
801, 804, 807, 810, 813, 816, 819, 822, 825, 6902, 6676, 6904, 6923, 6785, 6910, 6691,
6916, 6918, 6920, 6703, 6777, 6709, 6943, 6715, 6783, 6721, 6724, 6930, 6932, 6919, 6941, 6936,
6764, 6938, 6935, 6805, 3052, 3126, 6798, 6940, 6775, 6915, 2959, 6909, 3076, 3023, 6911, 6799,
3490, 3115, 3131, 2490, 6802, 6929, 6931, 3205, 3209, 3223, 3227, 3247, 3257, 6882, 534, 1179,
1183, 1182, 4609, 3076, 6941, 7398, 5990, 6477, 871, 5617, 5620, 5624, 5626, 5628, 6859, 5630,
5632, 5650, 5655, 898, 5659, 5663, 5667, 5675, 5676, 5677, 5688, 5697, 5701, 5703, 5704, 907,
5712, 5713, 5719, 5720, 5722, 5725, 5756, 922, 5774, 5778, 5780, 5781, 4715, 5789, 5798, 5799,
5807, 5810, 5811, 5812, 5818, 5819, 5830, 5833, 5835, 5837, 5841, 5843, 5844, 5853, 5854, 5856,
5857, 5860, 5861, 5864, 5868, 5894, 5897, 5898, 5923, 5924, 5928, 5929, 5931, 5932, 5934, 1157,
5945, 2456, 937, 5977, 5980, 5983, 5986, 5989, 5991, 5992, 5993, 5994, 943, 946, 6053, 6056,
6057, 6058, 6059, 6061, 6062, 6066, 6072, 6074, 6090, 6091, 6092, 6093, 6095, 6096, 6103, 6104,
6109, 6110, 6111, 6112, 6115, 6122, 6123, 6124, 6133, 6146, 6147, 6155, 6158, 6159, 6166, 6174,
6189, 6190, 6195, 6198, 6200, 6202, 6203, 6204, 6210, 6211, 6218, 964, 967, 6221, 6224, 6225,
6226, 6227, 6229, 6230, 6268, 6273, 6286, 6287, 6289, 6299, 6300, 6302, 6303, 6316, 6317, 6319,
6320, 6321, 6329, 6330, 6332, 6337, 6338, 6345, 6347, 6348, 6355, 6362, 6365, 6366, 976, 6377,
6378, 6382, 6390, 6392, 6396, 6402, 6404, 6405, 6406, 6407, 6409, 6410, 6412, 6419, 6420, 6421,
6427, 6428, 6430, 6435, 6436, 6437, 6439, 6440, 6441, 6442, 6443, 6447, 6453, 6454, 6457, 6458,
6459, 6460, 6462, 6463, 6464, 6467, 6469, 6471, 6472, 6473, 6474, 6475, 6476, 6478, 2399, 0,
0, 5485, 5707, 5708, 0, 0, 4613, 0, 4615, 0, 4617, 0, 4619, 0, 4621, 0,
4623, 0, 4625, 0, 4627, 0, 4629, 0, 4631, 0, 4633, 0, 4635, 0, 4637, 0,
4639, 0, 4641, 0, 4643, 4645, 0, 4647, 4649, 0, 4651, 4653, 0, 4655, 4657, 0,
4659, 4661, 4611, 0, 0, 2397, 2399, 0, 4665, 4663, 0, 0, 576, 0, 578, 0,
158, 0, 107, 0, 4671, 0, 4675, 0, 188, 0, 4677, 0, 70, 0, 4679, 0,
606, 0, 4681, 0, 4683, 0, 2262, 0, 2265, 0, 160, 610, 0, 2277, 2280, 0,
222, 4695, 0, 626, 2289, 0, 638, 596, 0, 0, 0, 0, 4667, 4705, 4707, 4709,
4711, 0, 4713, 4673, 6662, 5185, 5243, 832, 5244, 5245, 835, 5186, 838, 5246, 5247, 5248,
5249, 5250, 5251, 5192, 841, 844, 5187, 5197, 847, 5188, 6992, 6668, 5189, 6659, 859, 862,
865, 6656, 6660, 5216, 5217, 5218, 6650, 5220, 5221, 5222, 6663, 5224, 5225, 5226, 5227, 6993,
5228, 5229, 5230, 5231, 5232, 6671, 5234, 5215, 5190, 5191, 5252, 5253, 5254, 5255, 5256, 5257,
5258, 5193, 5259, 5260, 5194, 5195, 5196, 5198, 5199, 5200, 5201, 5202, 5203, 5204, 5205, 5206,
5207, 5208, 5209, 5210, 5211, 5261, 5262, 5212, 5213, 5214, 5235, 5236, 5237, 5238, 5239, 5240,
5241, 5242, 871, 6859, 6856, 919, 5613, 5618, 5614, 6097, 5626, 5616, 5612, 5785, 5760, 5632,
828, 831, 834, 837, 840, 843, 846, 849, 852, 855, 858, 861, 864, 867, 274, 278,
282, 286, 290, 294, 298, 302, 306, 314, 318, 322, 326, 330, 310, 6646, 6653, 870,
882, 876, 918, 885, 900, 873, 897, 879, 906, 930, 945, 942, 936, 975, 921, 927,
939, 933, 954, 912, 948, 969, 957, 903, 888, 915, 924, 951, 891, 972, 909, 960,
894, 963, 966, 7414, 7424, 5928, 7459, 6783, 1110, 1116, 2406, 2428, 1131, 1134, 1137, 1140,
1143, 1152, 1155, 2405, 2408, 2430, 2411, 6662, 832, 835, 838, 841, 844, 847, 6992, 6668,
6659, 859, 862, 865, 6656, 275, 279, 283, 287, 291, 295, 299, 303, 307, 6659, 319,
323, 327, 331, 6659, 6668, 6992, 871, 6859, 6856, 919, 886, 901, 874, 898, 880, 907,
2456, 946, 943, 937, 976, 922, 1157, 940, 934, 955, 913, 949, 970, 958, 904, 6149,
6098, 5789, 6352, 5649, 5714, 6002, 6413, 895, 5665, 4716, 5613, 5618, 5614, 5834, 5729, 5705,
5801, 925, 952, 892, 973, 910, 5783, 2413, 2415, 2417, 2419, 2423, 2425, 2427, 2429, 2432,
2433, 2435, 2437, 2439, 2441, 2445, 1000, 1012, 2421, 2443, 2447, 2449, 2451, 2453, 2455, 987,
999, 1011, 6914, 6801, 6940, 6777, 2335, 2320, 4667, 554, 2232, 2235, 582, 2327, 2247, 4694,
4675, 4686, 4677, 2256, 4698, 2297, 4681, 4683, 2262, 4674, 4689, 2299, 5489, 593, 4690, 2324,
2300, 4695, 2292, 4699, 2325, 650, 4704, 654, 5490, 2331, 2334, 5492, 4702, 4701, 4692, 4703,
2239, 4705, 4707, 4709, 4711, 538, 542, 546, 2220, 550, 2223, 2226, 125, 554, 2229, 2232,
2235, 566, 570, 2238, 2241, 4669, 2244, 582, 586, 135, 130, 56, 135, 145, 145, 140,
590, 2247, 2250, 2253, 598, 150, 602, 2256, 167, 2259, 4685, 4687, 656, 4689, 2268, 2271,
165, 2274, 614, 170, 2283, 4693, 4691, 175, 622, 180, 2286, 190, 4697, 2298, 2292, 2301,
2304, 2295, 642, 2313, 4699, 2316, 2307, 2310, 646, 2319, 2322, 2325, 205, 650, 210, 210,
654, 654, 58, 2328, 2331, 2334, 662, 4701, 2337, 670, 4703, 225, 137, 1105, 1111, 1117,
1123, 1129, 1042, 1051, 1060, 1069, 1078, 990, 1002, 1014, 1023, 1032, 1041, 1050, 1059, 1068,
1077, 1104, 1110, 1116, 1122, 1128, 1491, 2879, 2467, 1434, 3099, 3125, 6798, 6795, 6798, 6918,
4717, 4721, 4715, 4719, 674, 3117, 3067, 3577, 3045, 3001, 2619, 2651, 2549, 347, 346, 3119,
3069, 3579, 3585, 3053, 336, 1498, 1497, 1272, 1260, 1350, 3593, 3065, 2897, 3023, 2925, 3077,
3589, 1533, 1452, 1512, 1530, 1449, 6796, 1509, 1533, 1452, 6799, 1512, 354, 354, 1501, 1500,
1275, 1263, 32, 32, 32, 3127, 3079, 3591, 3057, 3121, 3071, 3581, 3047, 3003, 2653, 3123,
3073, 3583, 3049, 3005, 2655, 3021, 2663, 342, 2489, 2866, 2867, 334, 1224, 2877, 2551, 2943,
2706, 2963, 2622, 2623, 3009, 3056, 3029, 1515, 3031, 3051, 1521, 1536, 2705, 358, 1332, 2707,
3147, 2731, 2791, 6786, 6759, 1156, 1114, 1120, 1126, 1132, 1135, 1138, 1141, 1144, 984, 996,
1008, 1020, 1029, 1038, 1047, 1056, 1065, 1074, 1101, 1107, 1113, 1119, 1125, 1131, 1134, 1137,
1140, 1143, 1152, 1155, 6804, 7552, 6318, 5946, 6338, 6325, 6025, 5619, 5726, 6476, 5787, 976,
5745, 5786, 5892, 6108, 6194, 6267, 6282, 6295, 6354, 5971, 6004, 6043, 6078, 6253, 6363, 6432,
5627, 5716, 5976, 6051, 6266, 6452, 5824, 6031, 6262, 6298, 5901, 6217, 6285, 5850, 5949, 6010,
6068, 6357, 5637, 5670, 5694, 5922, 5974, 6050, 6114, 6200, 6264, 6270, 6335, 6400, 6444, 6451,
6127, 6141, 6180, 6247, 6373, 6454, 6307, 5773, 5855, 6165, 6209, 6063, 6129, 6324, 6398, 5772,
5815, 5972, 6015, 6026, 6178, 6186, 6384, 5693, 6212, 5673, 5672, 6151, 6181, 6252, 6386, 6314,
5902, 6310, 5622, 5804, 5873, 6073, 6102, 5702, 6131, 5641, 5867, 5615, 5999, 5927, 6177, 5721,
5769, 6117, 6254, 6305, 5987, 6347, 5997, 5906, 6238, 5912, 6101, 5631, 5657, 5671, 5963, 6172,
6228, 6306, 6367, 5696, 5734, 5789, 5852, 5933, 6032, 6132, 6380, 6434, 6455, 6461, 5688, 5944,
5982, 6344, 5842, 5886, 5893, 5920, 6028, 6045, 6087, 6148, 6183, 6207, 6340, 6256, 6350, 6374,
5680, 5689, 5739, 6042, 6290, 5849, 5871, 5910, 5985, 6164, 6070, 5635, 5757, 5829, 5874, 6077,
6084, 6197, 6205, 6368, 6397, 6401, 6415, 5638, 6145, 6364, 6391, 5878, 5629, 5647, 5805, 5813,
5930, 6048, 6107, 6259, 6353, 6475, 5940, 6383, 5687, 5955, 5958, 6008, 6021, 6080, 6100, 6126,
6176, 6418, 901, 5896, 6387, 5643, 5822, 6016, 6341, 5865, 5879, 5960, 6388, 5681, 5731, 5817,
5937, 5952, 5966, 6001, 6079, 6105, 6192, 6291, 6294, 6366, 6394, 5706, 6022, 5732, 6049, 6088,
6263, 6389, 6446, 6456, 5957, 6014, 6219, 6158, 6160, 6167, 6067, 6040, 6313, 5633, 6242, 5682,
5679, 5845, 5903, 6170, 5800, 6005, 5943, 6343, 6287, 6385, 6300, 5851, 5651, 5750, 5768, 5939,
5674, 6069, 6113, 6134, 6139, 6140, 6144, 6403, 6168, 6198, 6265, 6309, 6351, 6359, 6423, 6424,
6425, 6450, 5639, 5648, 5652, 5692, 5695, 5710, 5747, 5752, 5754, 5767, 5770, 5816, 5818, 5876,
5883, 5885, 5891, 5925, 5935, 5941, 5964, 6011, 6018, 6027, 6046, 6054, 6081, 6128, 955, 6136,
6135, 6137, 6138, 958, 6142, 6143, 6152, 6156, 6161, 6185, 6187, 6191, 6201, 6220, 6231, 6255,
6297, 6301, 6311, 6312, 6326, 6327, 6349, 6395, 6411, 6417, 7431, 7578, 7464, 7404, 5669, 7408,
7406, 7407, 7409, 5691, 5698, 7415, 5746, 7416, 7417, 7419, 7420, 7421, 7422, 7425, 7426, 7428,
7430, 7432, 5882, 7433, 7434, 7435, 7439, 7440, 7441, 7442, 5950, 7445, 5983, 7446, 6024, 6034,
7456, 6055, 7449, 6085, 7450, 7451, 7452, 7453, 7454, 6116, 6120, 7455, 6130, 7457, 7460, 7462,
7463, 7465, 7466, 6280, 7467, 7468, 7470, 7471, 6308, 6315, 6342, 7474, 7475, 7476, 7477, 7478,
6414, 6438, 7576, 7575, 7577, 5566, 7402, 5576, 7580, 7581, 7582, 7479, 7480, 1488, 6772, 6775,
1485, 1488, 3425, 3151, 3749, 3743, 3745, 3751, 3747, 3779, 0, 3815, 5147, 3759, 3767, 3769,
3787, 3789, 5146, 3807, 3813, 4754, 3809, 3811, 4723, 4725, 3753, 3755, 3757, 3761, 3765, 3767,
3769, 3773, 3775, 3777, 3781, 3783, 3785, 3789, 3791, 3793, 3795, 3797, 3799, 3803, 3805, 3807,
1845, 3813, 3771, 3763, 3787, 3801, 3759, 5151, 5151, 5155, 5155, 5155, 5155, 5156, 5156, 5156,
5156, 5158, 5158, 5158, 5158, 5154, 5154, 5154, 5154, 5157, 5157, 5157, 5157, 5153, 5153, 5153,
5153, 5169, 5169, 5169, 5169, 5170, 5170, 5170, 5170, 5160, 5160, 5160, 5160, 5159, 5159, 5159,
5159, 5161, 5161, 5161, 5161, 5162, 5162, 5162, 5162, 5165, 5165, 5164, 5164, 5166, 5166, 5163,
5163, 5168, 5168, 5167, 5167, 5171, 5171, 5171, 5171, 5173, 5173, 5173, 5173, 5175, 5175, 5175,
5175, 5174, 5174, 5174, 5174, 5176, 5176, 5177, 5177, 5177, 5177, 5179, 5179, 4041, 4041, 4041,
4041, 5178, 5178, 5178, 5178, 4045, 4045, 5183, 5183, 5172, 5172, 5172, 5172, 4043, 4043, 3842,
3842, 3846, 3846, 5152, 5182, 5182, 5180, 5180, 5181, 5181, 3848, 3848, 3848, 3848, 4036, 4036,
3817, 3817, 3849, 3849, 3835, 3835, 3843, 3843, 3841, 3841, 3845, 3845, 3847, 3847, 3847, 3837,
3837, 3837, 519, 519, 519, 519, 3819, 3821, 3829, 3839, 3855, 1848, 1851, 3859, 3865, 3867,
1860, 1866, 1875, 1890, 3877, 3879, 3881, 3887, 3893, 3895, 2107, 2110, 2089, 2119, 2095, 3897,
2098, 1920, 1923, 1929, 1938, 1959, 1965, 3929, 1971, 1974, 3933, 3939, 1983, 3945, 1986, 1995,
3951, 2004, 3963, 3965, 2016, 2019, 3967, 3969, 3971, 2031, 3973, 3975, 3977, 3979, 3981, 3983,
3985, 2037, 3987, 3989, 2055, 2064, 2067, 2073, 1, 10, 2134, 2091, 2100, 2146, 2128, 2171,
2115, 2124, 3999, 2130, 4009, 4034, 4013, 2136, 4015, 4017, 2139, 2142, 4027, 2148, 4035, 4038,
3899, 3901, 4025, 705, 708, 711, 714, 717, 720, 3825, 3827, 3829, 3831, 3839, 512, 3857,
3859, 3861, 3865, 3867, 3869, 3871, 1890, 3873, 3877, 3879, 3883, 3885, 3887, 3889, 3893, 3895,
3967, 3969, 3973, 3975, 3977, 3985, 2037, 3987, 3989, 2073, 1, 10, 3997, 2146, 4001, 4003,
2130, 4006, 4009, 4034, 4025, 4029, 4031, 2148, 4033, 4035, 4038, 3819, 3821, 3823, 3829, 3833,
3855, 1848, 1851, 3859, 3863, 1860, 1866, 1875, 1890, 3875, 3887, 2107, 2110, 2089, 2119, 2095,
2098, 1920, 1923, 1929, 1938, 1959, 3921, 1965, 3929, 1971, 1974, 3933, 3939, 3945, 1986, 1995,
3951, 2004, 3963, 3965, 2016, 2019, 3971, 2031, 3979, 3981, 3983, 3985, 2037, 2055, 2064, 2067,
2073, 24, 2134, 2091, 2100, 2146, 2115, 2124, 3999, 2130, 4007, 4013, 2136, 4019, 2139, 2142,
4027, 2148, 4018, 3829, 3833, 3859, 3863, 1890, 3875, 3887, 3891, 1938, 3905, 1953, 3915, 3985,
2037, 2073, 2130, 4007, 2148, 4018, 2007, 2010, 2013, 3941, 3943, 3947, 3949, 3953, 3955, 3907,
3909, 3917, 3919, 2122, 2159, 2113, 2156, 1927, 4028, 3925, 3927, 3935, 3937, 1941, 1947, 3911,
1953, 3913, 3903, 3923, 3931, 3941, 3943, 3947, 3949, 3953, 3955, 3907, 3909, 3917, 3919, 2122,
2159, 2113, 2156, 1927, 4028, 3925, 3927, 3935, 3937, 1941, 1947, 3911, 1953, 3913, 3903, 3923,
3931, 1941, 1947, 3911, 1953, 3905, 3915, 1983, 1920, 1923, 1929, 1941, 1947, 3911, 1983, 3945,
3851, 3851, 1854, 1863, 1863, 1866, 1869, 1878, 1881, 1884, 2090, 2090, 1914, 1911, 1923, 1917,
1920, 1935, 1935, 1932, 1938, 1938, 1956, 1956, 1965, 1944, 1944, 1941, 1950, 1950, 1953, 1953,
1968, 1974, 1974, 1977, 1977, 1980, 1983, 1986, 1989, 1989, 1992, 1998, 2004, 2001, 2016, 2016,
2025, 2028, 2058, 2064, 2061, 2049, 2049, 2067, 2067, 2070, 2070, 2088, 526, 2091, 2076, 2082,
2094, 2097, 2079, 2133, 2136, 2118, 2121, 2109, 2109, 2112, 2130, 2127, 2145, 2145, 1851, 1860,
1857, 1875, 1872, 1890, 1887, 1905, 1893, 1902, 1926, 1959, 1947, 1971, 2055, 2073, 2142, 2139,
2148, 2146, 2031, 2124, 2025, 2058, 1995, 2037, 2106, 2100, 2052, 2034, 2052, 2106, 1896, 1908,
2085, 2019, 1848, 2034, 1986, 1965, 1929, 2115, 1962, 2022, 4, 510, 526, 522, 514, 9,
14, 0, 0, 18, 518, 6901, 5473, 5474, 1180, 4757, 2464, 2466, 7399, 7400, 7250, 5417,
5416, 5415, 4764, 6747, 6749, 4766, 4768, 6879, 6881, 5483, 5484, 5477, 5478, 5475, 5476, 5479,
5480, 5481, 5482, 4760, 4762, 5418, 4764, 6901, 5473, 1226, 4757, 1180, 2466, 2464, 5416, 6747,
6749, 4766, 4768, 6879, 6881, 4748, 4751, 4753, 4754, 4756, 2457, 2461, 2459, 4761, 4749, 4750,
4758, 2393, 3957, 705, 708, 711, 2007, 714, 2010, 717, 2013, 720, 3959, 2395, 3961, 5148,
3992, 3992, 3994, 3994, 5149, 5149, 3996, 3996, 3849, 3849, 3849, 3849, 3998, 3998, 3867, 3867,
3867, 3867, 5150, 5150, 3879, 3879, 3879, 3879, 3895, 3895, 3895, 3895, 4014, 4014, 4014, 4014,
3982, 3982, 3982, 3982, 4028, 4028, 4028, 4028, 529, 529, 3899, 3899, 4030, 4030, 4032, 4032,
3909, 3909, 3909, 3909, 3919, 3919, 3919, 3919, 3927, 3927, 3927, 3927, 3937, 3937, 3937, 3937,
3943, 3943, 3943, 3943, 3945, 3945, 3945, 3945, 3949, 3949, 3949, 3949, 3955, 3955, 3955, 3955,
3969, 3969, 3969, 3969, 3975, 3975, 3975, 3975, 3989, 3989, 3989, 3989, 3995, 3995, 3995, 3995,
3997, 3997, 3997, 3997, 4034, 4034, 4034, 4034, 4019, 4019, 4019, 4019, 4023, 4023, 4036, 4036,
4039, 4039, 4039, 4039, 3991, 3991, 3993, 3993, 3995, 3995, 2046, 2046, 2464, 4747, 4748, 4749,
4750, 4751, 4752, 6747, 6749, 4753, 4754, 6901, 4756, 1226, 1441, 6882, 6884, 6886, 6888, 6890,
6892, 6894, 6896, 6898, 6900, 1180, 4757, 2457, 2459, 2461, 2466, 4758, 6902, 6676, 6904, 6923,
6785, 6910, 6691, 6916, 6918, 6920, 6703, 6777, 6709, 6943, 6715, 6783, 6721, 6724, 6930, 6932,
6919, 6941, 6936, 6764, 6938, 6935, 4760, 4761, 4762, 4763, 4764, 4765, 6805, 3052, 3126, 6798,
6940, 6775, 6915, 2959, 6909, 3076, 3023, 6911, 6799, 3490, 3115, 3131, 2490, 6802, 6929, 6931,
3205, 3209, 3223, 3227, 3247, 3257, 4766, 4767, 4768, 4769, 5471, 5472, 5474, 5479, 5480, 5473,
5493, 4711, 545, 623, 5488, 183, 2227, 5491, 583, 208, 2323, 2339, 2335, 2320, 4667, 554,
2232, 2235, 582, 2327, 2247, 4694, 4675, 4686, 4677, 2256, 4698, 2297, 4681, 4683, 2262, 4674,
4689, 2299, 5489, 593, 4690, 2324, 2300, 4695, 2292, 4699, 2325, 650, 4704, 654, 5490, 2331,
2334, 5492, 4702, 4701, 4692, 4703, 2239, 4705, 4700, 4714, 4696, 5545, 5494, 5495, 5496, 5497,
5498, 5499, 5500, 5501, 5502, 5503, 5504, 5505, 5506, 5507, 5508, 5509, 5510, 5511, 5512, 5513,
5514, 5515, 5516, 5517, 5518, 5519, 5520, 5521, 5522, 5523, 5524, 5525, 5526, 5527, 5528, 5529,
5530, 5531, 5532, 5533, 5534, 5535, 5536, 5537, 5538, 5539, 5540, 5541, 5542, 5543, 5544, 4770,
4771, 4774, 4775, 4773, 4772, 5419, 5468, 4527, 5436, 4529, 5437, 5469, 5470, 0, 7078, 0,
7080, 0, 7082, 0, 4727, 2352, 4729, 4731, 4733, 4735, 4737, 0, 2358, 2364, 4739, 4743,
4741, 4745, 6902, 6691, 6920, 6703, 6715, 6930, 6932, 6919, 6941, 6936, 6764, 6938, 6805, 3052,
3126, 6775, 3023, 6799, 3490, 3131, 2490, 6802, 6929, 6931, 3205, 3209, 3223, 3227, 3247, 3257,
7086, 7094, 6956, 4948, 4950, 3503, 4951, 6958, 4952, 7075, 4953, 4954, 4955, 4956, 4957, 3523,
6962, 5002, 4959, 4960, 6964, 4961, 4962, 4963, 6966, 5439, 3557, 4967, 4969, 3561, 4970, 3565,
4971, 4508, 4972, 4973, 3593, 4974, 4975, 3597, 3601, 4977, 4978, 4979, 3611, 4980, 4981, 4982,
3615, 5438, 5003, 4985, 5000, 4986, 5001, 4987, 7135, 4990, 6882, 6884, 6886, 6888, 6890, 6892,
6894, 6896, 6898, 6900, 1099, 6882, 6884, 6886, 6888, 6890, 6892, 6894, 6896, 6898, 6900, 6672,
6675, 6678, 6681, 6684, 6687, 6690, 6693, 6696, 6699, 6702, 6705, 6708, 6711, 6714, 6717, 6720,
6723, 6726, 6729, 6732, 6735, 6738, 6741, 6744, 6747, 6852, 6904, 6934, 6676, 6943, 6783, 6930,
6936, 6912, 6922, 6924, 6780, 6906, 7076, 5898, 7423, 7412, 4685, 6859, 5782, 7469, 5785, 7405,
7444, 7448, 5930, 7411, 7429, 5660, 7443, 7410, 7461, 6093, 7472, 7418, 7413, 7447, 7436, 7438,
871, 6856, 7473, 5834, 5618, 5729, 7437, 6330, 6868, 6873, 6855, 6858, 6864, 6876, 6867, 6879,
6861, 6870, 5623, 5621, 5625, 6543, 5636, 5640, 5642, 5644, 5645, 5646, 5546, 6547, 5653, 5654,
5658, 6544, 5547, 5656, 5660, 6546, 5664, 5666, 5634, 5668, 6634, 5676, 5678, 5549, 5683, 5684,
5685, 5686, 5550, 5699, 5700, 5709, 5711, 5715, 5717, 5718, 6550, 6037, 5723, 5724, 6551, 5727,
5728, 5730, 5737, 5733, 5735, 5736, 5738, 5740, 5741, 5742, 5743, 5744, 5748, 5749, 5751, 5758,
5759, 5753, 5755, 5775, 5762, 5763, 5764, 5761, 5766, 5765, 5771, 6553, 5776, 5777, 5779, 5782,
5784, 5788, 6554, 6555, 5791, 5792, 5793, 5790, 5794, 5551, 7401, 5796, 5797, 6556, 5802, 5803,
5806, 6557, 5808, 5809, 7427, 5811, 5552, 5814, 5821, 5820, 6559, 5823, 6560, 5826, 5825, 5827,
5831, 5832, 5553, 5836, 5838, 5839, 5840, 5554, 6561, 5555, 5846, 5847, 5848, 6644, 5854, 6563,
6222, 5858, 5556, 6568, 6605, 5862, 5863, 5557, 5866, 5869, 5870, 5872, 5875, 5559, 5558, 6564,
5877, 5880, 5881, 5884, 5889, 5887, 5888, 5890, 4718, 5895, 5899, 5900, 5904, 5908, 6565, 5907,
5905, 5909, 5911, 5915, 6566, 5916, 5914, 5913, 5560, 5917, 5919, 5921, 5918, 5561, 5926, 6567,
5936, 5947, 5938, 5564, 5563, 5562, 5661, 5662, 5948, 5942, 6213, 5589, 5951, 5954, 5953, 6572,
5565, 5959, 5956, 5962, 6573, 5965, 5961, 5967, 5968, 5969, 5970, 5973, 6574, 5975, 5567, 5978,
6575, 5979, 5568, 5981, 5984, 5988, 6576, 6558, 6577, 5995, 6578, 5998, 6000, 5996, 6003, 6007,
6009, 6012, 6013, 6579, 6006, 6019, 6020, 5569, 6023, 6580, 6017, 6029, 6581, 6582, 6030, 6035,
6033, 5570, 6036, 6039, 6038, 6041, 6545, 6044, 6583, 6047, 7579, 6052, 6060, 6584, 6064, 6065,
6585, 6586, 6071, 6075, 5571, 6076, 5572, 6082, 6083, 6086, 6089, 5573, 6094, 6587, 6099, 6588,
6562, 6106, 6589, 6590, 6591, 5574, 5575, 6593, 6592, 6594, 6595, 6118, 6119, 6121, 5577, 5578,
6596, 6125, 5579, 6597, 6598, 6599, 6150, 5580, 6153, 6154, 6600, 6601, 7458, 5581, 6602, 6162,
6163, 5582, 6603, 6169, 5583, 6173, 6171, 6175, 6604, 6179, 5584, 6182, 6184, 6188, 5585, 6606,
6607, 5586, 6608, 6193, 6609, 6196, 6199, 6610, 6611, 6206, 6612, 6208, 6569, 5588, 6214, 6215,
5590, 6216, 5795, 6613, 6614, 6570, 6571, 6223, 6346, 5591, 6233, 6232, 6234, 5690, 6235, 6236,
6237, 6239, 6615, 6240, 6244, 6245, 6241, 6246, 6251, 6243, 6248, 6249, 6250, 6616, 6618, 6617,
5592, 6257, 6258, 6260, 6622, 6261, 6619, 5593, 5594, 6620, 6621, 5595, 6269, 6271, 6272, 6275,
6274, 6277, 6276, 6278, 6279, 6281, 7403, 6283, 6284, 5596, 6288, 6289, 6623, 6292, 6293, 5597,
6296, 5548, 6624, 6625, 5598, 5599, 6304, 6319, 6626, 6322, 6323, 6328, 6331, 6627, 6548, 6334,
6333, 6336, 6549, 6339, 6628, 6629, 6356, 6358, 6360, 6630, 6361, 6369, 6371, 6372, 6370, 6375,
6376, 6631, 6379, 5600, 6381, 6632, 5601, 6393, 5828, 6399, 6633, 6635, 5602, 5603, 6408, 6636,
5604, 6637, 6416, 6638, 6422, 5605, 6426, 6429, 6431, 6433, 5606, 6639, 6445, 6448, 5607, 5608,
6449, 6640, 5609, 6641, 6642, 6643, 6458, 5610, 6463, 6465, 6466, 6468, 6470, 6472,
]
_lookup_composition_decomp_middle = _all_ushort(_lookup_composition_decomp_middle)
def lookup_composition_decomp_middle(index): return intmask(_lookup_composition_decomp_middle[index])

def lookup_composition_compat_decomp_len(index):
    if 54 <= index <= 4343:
        return lookup_composition_compat_decomp_len_middle(index - 54)
    if index < 54:
        return 0
    if index < 4821:
        return 1
    raise KeyError

_lookup_composition_compat_decomp_len_middle = (
'\x01\x02\x01\x02\x01\x01\x02\x01\x02\x01\x01\x03\x03\x03\x02\x02\x02\x02\x02\x02'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x01\x02\x02\x02\x02\x00\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02'
'\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03'
'\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03'
'\x03\x03\x03\x02\x02\x03\x03\x02\x02\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02'
'\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x01\x01\x00\x01\x02\x00\x00\x00\x01\x02\x01\x03\x02\x01\x02\x02\x02'
'\x02\x02\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x03\x00'
'\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x01\x01\x01\x02\x02\x01\x01\x01'
'\x01\x01\x01\x01\x01\x02\x02\x02\x00\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x02'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x02'
'\x02\x02\x00\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x02\x00\x02\x00\x00\x00'
'\x02\x00\x02\x00\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00\x02\x02'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x02\x02\x02\x00\x00\x02\x02\x00'
'\x02\x00\x00\x00\x02\x02\x02\x00\x00\x02\x00\x00\x00\x02\x00\x00\x02\x02\x02\x03'
'\x00\x00\x00\x00\x00\x02\x02\x02\x00\x00\x00\x00\x02\x02\x03\x02\x00\x02\x00\x00'
'\x02\x00\x00\x02\x02\x01\x00\x02\x02\x02\x02\x02\x02\x00\x00\x02\x00\x02\x02\x03'
'\x02\x03\x02\x02\x02\x02\x02\x02\x02\x00\x02\x00\x01\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x00\x02\x00\x02\x00\x00\x02\x02\x00\x02\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x02\x02\x02\x02\x02\x02\x02\x02'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x02\x02\x02\x02'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02'
'\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03'
'\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03'
'\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02'
'\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x03'
'\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x04\x04\x04\x04\x04\x04'
'\x03\x03\x04\x04\x04\x04\x04\x04\x03\x03\x04\x04\x04\x04\x04\x04\x03\x03\x04\x04'
'\x04\x04\x04\x04\x03\x03\x04\x04\x04\x04\x04\x04\x03\x03\x04\x04\x04\x04\x04\x04'
'\x02\x02\x03\x02\x03\x02\x03\x02\x02\x02\x02\x02\x02\x01\x02\x02\x03\x03\x02\x03'
'\x02\x03\x02\x02\x02\x02\x02\x03\x03\x03\x02\x02\x03\x03\x02\x03\x02\x02\x02\x02'
'\x03\x03\x03\x02\x02\x03\x03\x02\x02\x02\x03\x02\x02\x02\x02\x02\x03\x03\x01\x03'
'\x02\x03\x02\x03\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x02\x01\x02\x03\x02'
'\x03\x02\x03\x02\x02\x02\x02\x02\x04\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x02\x03\x03\x01\x02\x03\x03\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x02\x01\x01\x01\x02\x03\x02\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x03\x01\x01\x01\x01\x01\x01\x01\x01\x03\x03\x04\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x02\x01\x02\x03\x02\x01\x02\x03\x04\x02\x01\x02\x03\x01'
'\x01\x01\x01\x01\x02\x03\x02\x01\x02\x03\x04\x02\x01\x02\x03\x01\x01\x01\x01\x03'
'\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x02\x00\x02\x00\x02\x00\x02'
'\x00\x02\x02\x03\x02\x03\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x00'
'\x02\x02\x02\x02\x02\x00\x00\x02\x02\x00\x00\x02\x02\x00\x00\x00\x00\x02\x02\x00'
'\x00\x02\x02\x00\x00\x02\x02\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x00\x00\x00'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x04\x03\x02\x03\x02\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x01\x01\x01'
'\x00\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02'
'\x00\x02\x02\x00\x02\x02\x02\x00\x00\x02\x02\x00\x02\x02\x00\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02'
'\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x04\x04\x04\x04\x04\x04'
'\x04\x04\x04\x04\x04\x04\x04\x04\x04\x07\x06\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x01\x01\x01\x01\x03\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x05\x04\x02\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x02\x03\x02\x03\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x05\x04\x05\x03\x05\x03\x03\x06\x04\x03\x03\x03\x04\x04\x04'
'\x04\x04\x04\x04\x06\x02\x06\x06\x05\x04\x06\x06\x04\x03\x03\x04\x04\x05\x05\x03'
'\x03\x04\x03\x03\x02\x02\x03\x03\x06\x04\x05\x06\x04\x03\x03\x06\x04\x06\x03\x05'
'\x03\x04\x03\x04\x05\x04\x05\x04\x02\x05\x03\x03\x04\x03\x03\x03\x05\x04\x02\x06'
'\x03\x05\x04\x04\x03\x03\x04\x02\x04\x05\x02\x06\x03\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02'
'\x02\x03\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x04\x02\x02\x02\x02\x02\x02\x02'
'\x02\x03\x04\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x03\x03\x02\x03\x03\x03\x02\x03\x03\x04\x02\x03\x03\x03\x03\x05'
'\x06\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x04'
'\x02\x02\x02\x04\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x02\x02\x03\x03'
'\x02\x04\x03\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02'
'\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x01\x01\x01\x01\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x04\x04\x04\x04\x04\x04\x04\x03\x12\x08\x04\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x03\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x01\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x03\x03\x03\x03\x03\x03\x02\x02\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x02\x00'
'\x02\x00\x02\x00\x02\x02\x03\x03\x03\x03\x03\x00\x02\x02\x03\x03\x03\x03\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x01\x01\x01\x01'
'\x01\x02\x02\x02\x03\x02\x02\x01\x01\x01\x02\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x03\x03\x03\x03\x03\x03\x03\x03\x03'
)
def lookup_composition_compat_decomp_len_middle(index): return ord(_lookup_composition_compat_decomp_len_middle[index])

def lookup_composition_compat_decomp(index):
    if 54 <= index <= 4819:
        return lookup_composition_compat_decomp_middle(index - 54)
    if index < 54:
        return 0
    if index < 4821:
        return 6645
    raise KeyError

# estimated 9.32 KiB
_lookup_composition_compat_decomp_middle = [
2399, 684, 6805, 2371, 6886, 6888, 2367, 3593, 2383, 6884, 3115, 1086, 1080, 1158, 2469, 2471,
1194, 2473, 1212, 1215, 0, 1227, 2521, 2523, 1245, 2531, 2589, 2591, 2593, 1266, 2675, 2689,
2691, 1287, 1296, 1308, 0, 2757, 2759, 2761, 1368, 2811, 2839, 2841, 1404, 2843, 1422, 1425,
0, 1455, 2899, 2901, 1470, 2909, 2969, 2971, 2973, 1494, 3085, 3101, 3103, 1548, 1557, 1569,
0, 3177, 3179, 3181, 1620, 3231, 3241, 2475, 2845, 1206, 1416, 2487, 2857, 2497, 2869, 2499,
2871, 2501, 2873, 2503, 2875, 2511, 2887, 1251, 1476, 2527, 2905, 2529, 2907, 2541, 2919, 2535,
2913, 2555, 2931, 2559, 2935, 2561, 2937, 2565, 2941, 2569, 2945, 2595, 2975, 2597, 2977, 2599,
2979, 2613, 2993, 2601, 2583, 2961, 2617, 2997, 2631, 3017, 2641, 3035, 2645, 3039, 2643, 3037,
2639, 3033, 2673, 3083, 2683, 3093, 2679, 3089, 3489, 1302, 1563, 2693, 3105, 2697, 3109, 2715,
3133, 2725, 3143, 2719, 3137, 1338, 1596, 2733, 3153, 2739, 3159, 1341, 1599, 2751, 3171, 2745,
3165, 1353, 1605, 1356, 1608, 2763, 3183, 2767, 3187, 2769, 3189, 2781, 3201, 2797, 3215, 2813,
3233, 2821, 2827, 3249, 2831, 3253, 1231, 1459, 6929, 1323, 1584, 1383, 1635, 0, 1230, 1233,
1458, 2635, 2637, 3025, 2665, 2667, 3075, 2479, 2849, 2605, 2985, 2699, 3111, 2771, 3191, 1365,
1617, 1362, 1614, 1368, 1620, 1359, 1611, 1212, 1422, 1209, 1419, 3283, 3337, 2563, 2939, 2627,
3013, 1329, 1590, 1329, 1590, 3469, 3487, 2999, 1230, 1233, 1458, 2553, 2929, 2671, 3081, 1215,
1425, 3281, 3335, 3313, 3367, 2481, 2851, 2483, 2853, 2537, 2915, 2539, 2917, 2607, 2987, 2609,
2989, 2701, 3113, 2703, 3115, 2721, 3139, 2723, 3141, 2773, 3193, 2775, 3195, 2737, 3157, 2749,
3169, 2575, 2951, 1209, 1419, 1257, 1482, 1308, 1569, 1293, 1554, 1305, 1566, 1305, 1566, 2817,
3237, 0, 2959, 4923, 3076, 6802, 4929, 4930, 4932, 3223, 3247, 2375, 2377, 2379, 2385, 2369,
2381, 4922, 6911, 6929, 3227, 4937, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 6839, 6842, 0, 6963, 6832, 0, 0, 0, 4938,
2391, 4757, 681, 3493, 3034, 3503, 3507, 3513, 3523, 3529, 3539, 1761, 0, 0, 0, 0,
0, 0, 0, 0, 6825, 6834, 1713, 3561, 1743, 3569, 1800, 0, 0, 0, 0, 0,
0, 0, 0, 1764, 1803, 3597, 3605, 1827, 4967, 4971, 6964, 3529, 6834, 4980, 4976, 4972,
3601, 4977, 4952, 3561, 4959, 3645, 3649, 3643, 0, 3637, 3665, 3657, 3671, 0, 0, 0,
0, 0, 0, 3661, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
3705, 0, 0, 0, 0, 0, 0, 3689, 3693, 3687, 0, 3727, 3709, 3701, 3715, 0,
0, 3729, 3731, 3651, 3695, 3639, 3683, 3641, 3685, 3647, 3691, 0, 0, 3733, 3735, 3653,
3697, 3655, 3699, 3659, 3703, 3663, 3707, 3667, 3711, 0, 0, 3737, 3739, 3681, 3725, 3669,
3713, 3673, 3717, 3675, 3719, 3677, 3721, 3679, 3723, 3741, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2041,
2044, 4021, 2047, 2199, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
3853, 4023, 4043, 4039, 4047, 0, 4041, 0, 4045, 0, 0, 0, 4061, 0, 4067, 0,
4069, 0, 0, 4049, 4051, 4053, 4055, 4057, 4059, 4063, 4065, 0, 0, 0, 4077, 4079,
0, 4071, 4073, 4075, 4089, 4091, 4081, 4083, 4085, 4087, 0, 0, 4099, 4097, 4101, 0,
0, 4093, 4095, 0, 4103, 0, 0, 0, 4105, 4109, 4107, 0, 0, 4111, 0, 0,
0, 4113, 0, 0, 4115, 4117, 2202, 2202, 0, 0, 0, 0, 0, 4121, 4125, 4123,
0, 0, 0, 0, 4127, 2205, 2205, 4129, 0, 4133, 0, 0, 4139, 0, 0, 4135,
4137, 5184, 0, 4143, 4145, 4147, 4149, 4151, 4141, 0, 0, 4153, 0, 4155, 4169, 2208,
4173, 2211, 2212, 4159, 4161, 4163, 4165, 4167, 4157, 0, 4177, 0, 7156, 0, 6994, 0,
6996, 0, 6998, 0, 7000, 0, 7002, 0, 7004, 0, 0, 7006, 0, 7008, 0, 0,
7010, 7012, 0, 7014, 6902, 3283, 6676, 6923, 6785, 7089, 6691, 6916, 6918, 6920, 6703, 6777,
6709, 6943, 6715, 7093, 6783, 6724, 6932, 6919, 6936, 7104, 7105, 7157, 3052, 6798, 6940, 4919,
4920, 7108, 6915, 3023, 6799, 4829, 4916, 7158, 7159, 3131, 6931, 3205, 7161, 4926, 3209, 7162,
4967, 4968, 4969, 4980, 4981, 6909, 6802, 3205, 3209, 4967, 4968, 3601, 4980, 4981, 5010, 7106,
3126, 7107, 4786, 6775, 7109, 7110, 7111, 4924, 4925, 7112, 7164, 7126, 7114, 7166, 7127, 7116,
7115, 4927, 7117, 7118, 4928, 7119, 7121, 4933, 7091, 7122, 4935, 7160, 4936, 7123, 3257, 7124,
7125, 3487, 4971, 0, 2485, 2855, 2491, 2859, 2493, 2861, 2495, 2863, 1227, 1455, 2509, 2885,
2513, 2889, 2519, 2895, 2515, 2891, 2517, 2893, 1248, 1473, 1251, 1476, 2543, 2921, 2545, 2923,
1257, 1482, 2547, 2927, 2557, 2933, 2571, 2947, 2577, 2953, 2573, 2949, 2579, 2955, 2581, 2957,
2615, 2995, 1266, 1494, 2625, 3011, 2629, 3015, 2633, 3019, 1269, 1518, 1269, 1518, 2649, 3043,
2647, 3041, 2657, 3059, 2659, 3061, 2661, 3063, 2677, 3087, 2681, 3091, 2687, 3097, 2685, 3095,
1290, 1551, 1296, 1557, 1299, 1560, 1302, 1563, 2709, 3129, 2711, 3131, 2717, 3135, 1335, 1593,
1335, 1593, 2727, 3145, 2735, 3155, 1344, 1602, 1338, 1596, 1341, 1599, 1344, 1602, 2743, 3161,
2747, 3167, 2755, 3175, 2753, 3173, 2779, 3199, 2785, 3205, 2783, 3203, 1353, 1605, 1356, 1608,
2787, 3207, 2789, 3209, 2793, 3211, 2795, 3213, 2801, 3219, 2799, 3217, 2803, 3223, 2805, 3225,
2807, 3227, 2819, 3239, 2829, 3251, 2833, 3255, 2835, 3257, 2959, 3163, 3221, 3245, 2837, 3155,
1221, 1431, 2477, 2847, 1188, 1398, 1185, 1395, 1194, 1404, 1191, 1401, 1218, 1428, 1200, 1410,
1197, 1407, 1206, 1416, 1203, 1413, 1221, 1431, 1254, 1479, 2533, 2911, 2525, 2903, 1239, 1464,
1236, 1461, 1245, 1470, 1242, 1467, 1254, 1479, 2603, 2983, 2611, 2991, 1326, 1587, 2695, 3107,
1281, 1542, 1278, 1539, 1287, 1548, 1284, 1545, 1326, 1587, 1314, 1575, 1311, 1572, 1320, 1581,
1317, 1578, 1323, 1584, 2777, 3197, 2765, 3185, 1374, 1626, 1371, 1623, 1380, 1632, 1377, 1629,
1383, 1635, 2809, 3229, 2825, 3247, 2823, 3243, 2815, 3235, 1716, 1719, 438, 450, 442, 454,
446, 458, 1641, 1644, 366, 378, 370, 382, 374, 386, 1731, 1737, 1728, 1734, 1731, 1737,
1650, 1656, 1647, 1653, 1650, 1656, 1746, 1749, 462, 474, 466, 478, 470, 482, 1659, 1662,
390, 402, 394, 406, 398, 410, 1773, 1782, 1767, 1776, 1770, 1779, 1773, 1782, 1671, 1680,
1665, 1674, 1668, 1677, 1671, 1680, 1788, 1794, 1785, 1791, 1788, 1794, 1686, 1692, 1683, 1689,
1686, 1692, 1812, 1821, 1806, 1815, 1809, 1818, 1812, 1821, 1701, 1695, 1698, 1701, 1830, 1833,
486, 498, 490, 502, 494, 506, 1704, 1707, 414, 426, 418, 430, 422, 434, 1710, 1713,
3559, 3561, 1740, 1743, 3567, 3569, 3595, 3597, 3603, 3605, 1824, 1827, 1716, 1719, 438, 450,
442, 454, 446, 458, 1641, 1644, 366, 378, 370, 382, 374, 386, 1746, 1749, 462, 474,
466, 478, 470, 482, 1659, 1662, 390, 402, 394, 406, 398, 410, 1830, 1833, 486, 498,
490, 502, 494, 506, 1704, 1707, 414, 426, 418, 430, 422, 434, 3553, 3551, 1710, 3555,
1713, 1725, 1722, 3497, 3495, 3491, 3493, 3499, 693, 4508, 693, 2389, 684, 1740, 3563, 1743,
1755, 1752, 3501, 3503, 3505, 3507, 3509, 687, 690, 693, 3573, 3571, 1758, 1761, 3575, 1764,
3517, 3515, 3511, 3513, 696, 699, 702, 3609, 3607, 1797, 1800, 3599, 3601, 3611, 1803, 3533,
3531, 3527, 3529, 3525, 678, 681, 4765, 1824, 3613, 1827, 1839, 1836, 3521, 3523, 3537, 3539,
3541, 2367, 702, 2399, 2399, 2399, 5414, 2387, 1226, 979, 978, 532, 531, 2215, 2214, 2402,
2373, 2465, 2463, 2464, 530, 6882, 6909, 6890, 6892, 6894, 6896, 6898, 6900, 4754, 5441, 2459,
6747, 6749, 3490, 6882, 6884, 6886, 6888, 6890, 6892, 6894, 6896, 6898, 6900, 4754, 5441, 2459,
6747, 6749, 6805, 6940, 3115, 3227, 4919, 2713, 1389, 1392, 6904, 3265, 1437, 1440, 4853, 3267,
6915, 6916, 2959, 4813, 6918, 6777, 6911, 6943, 2669, 6783, 6721, 6724, 2729, 1347, 2741, 6935,
6966, 6703, 1215, 6676, 6940, 6785, 6910, 6709, 3115, 3759, 3763, 3765, 3767, 6909, 6762, 4976,
4968, 4949, 4958, 5440, 6923, 6798, 3076, 6753, 6756, 6664, 1083, 1146, 1089, 1149, 1161, 1167,
1092, 1170, 1095, 1164, 1173, 1176, 6756, 6918, 1387, 339, 2585, 6941, 2586, 338, 338, 2587,
6764, 2588, 1386, 6777, 6904, 6923, 6709, 6909, 1639, 363, 2965, 3209, 2966, 362, 362, 2967,
3227, 2968, 1638, 6911, 3126, 6798, 6799, 6750, 0, 0, 0, 4527, 4529, 4531, 4533, 4537,
4535, 0, 0, 0, 0, 4539, 0, 4541, 0, 4543, 0, 4545, 0, 4547, 536, 535,
2218, 2217, 0, 4549, 0, 4551, 0, 4553, 0, 4555, 0, 2459, 0, 4559, 0, 0,
4557, 2457, 2461, 4561, 4563, 0, 0, 4565, 4567, 0, 0, 4569, 4571, 0, 0, 0,
0, 4573, 4575, 0, 0, 4581, 4583, 0, 0, 4585, 4587, 0, 0, 0, 0, 0,
0, 4593, 4595, 4597, 4599, 0, 0, 0, 0, 4577, 4579, 4589, 4591, 4601, 4603, 4605,
4607, 5475, 5476, 6884, 6886, 6888, 6890, 6892, 6894, 6896, 6898, 6900, 6666, 1002, 1014, 1023,
2426, 1041, 1050, 1059, 1068, 1077, 1104, 723, 726, 729, 732, 735, 738, 741, 744, 747,
230, 234, 238, 242, 246, 250, 254, 258, 262, 266, 270, 994, 1006, 1018, 1027, 1036,
1045, 1054, 1063, 1072, 981, 993, 1005, 1017, 1026, 1035, 1044, 1053, 1062, 1071, 1098, 750,
753, 756, 759, 762, 765, 768, 771, 774, 777, 780, 783, 786, 789, 792, 795, 798,
801, 804, 807, 810, 813, 816, 819, 822, 825, 6902, 6676, 6904, 6923, 6785, 6910, 6691,
6916, 6918, 6920, 6703, 6777, 6709, 6943, 6715, 6783, 6721, 6724, 6930, 6932, 6919, 6941, 6936,
6764, 6938, 6935, 6805, 3052, 3126, 6798, 6940, 6775, 6915, 2959, 6909, 3076, 3023, 6911, 6799,
3490, 3115, 3131, 2490, 6802, 6929, 6931, 3205, 3209, 3223, 3227, 3247, 3257, 6882, 534, 1179,
1183, 1182, 4609, 3076, 6941, 7398, 5990, 6477, 871, 5617, 5620, 5624, 5626, 5628, 6859, 5630,
5632, 5650, 5655, 898, 5659, 5663, 5667, 5675, 5676, 5677, 5688, 5697, 5701, 5703, 5704, 907,
5712, 5713, 5719, 5720, 5722, 5725, 5756, 922, 5774, 5778, 5780, 5781, 4715, 5789, 5798, 5799,
5807, 5810, 5811, 5812, 5818, 5819, 5830, 5833, 5835, 5837, 5841, 5843, 5844, 5853, 5854, 5856,
5857, 5860, 5861, 5864, 5868, 5894, 5897, 5898, 5923, 5924, 5928, 5929, 5931, 5932, 5934, 1157,
5945, 2456, 937, 5977, 5980, 5983, 5986, 5989, 5991, 5992, 5993, 5994, 943, 946, 6053, 6056,
6057, 6058, 6059, 6061, 6062, 6066, 6072, 6074, 6090, 6091, 6092, 6093, 6095, 6096, 6103, 6104,
6109, 6110, 6111, 6112, 6115, 6122, 6123, 6124, 6133, 6146, 6147, 6155, 6158, 6159, 6166, 6174,
6189, 6190, 6195, 6198, 6200, 6202, 6203, 6204, 6210, 6211, 6218, 964, 967, 6221, 6224, 6225,
6226, 6227, 6229, 6230, 6268, 6273, 6286, 6287, 6289, 6299, 6300, 6302, 6303, 6316, 6317, 6319,
6320, 6321, 6329, 6330, 6332, 6337, 6338, 6345, 6347, 6348, 6355, 6362, 6365, 6366, 976, 6377,
6378, 6382, 6390, 6392, 6396, 6402, 6404, 6405, 6406, 6407, 6409, 6410, 6412, 6419, 6420, 6421,
6427, 6428, 6430, 6435, 6436, 6437, 6439, 6440, 6441, 6442, 6443, 6447, 6453, 6454, 6457, 6458,
6459, 6460, 6462, 6463, 6464, 6467, 6469, 6471, 6472, 6473, 6474, 6475, 6476, 6478, 2399, 0,
0, 5485, 5707, 5708, 0, 0, 4613, 0, 4615, 0, 4617, 0, 4619, 0, 4621, 0,
4623, 0, 4625, 0, 4627, 0, 4629, 0, 4631, 0, 4633, 0, 4635, 0, 4637, 0,
4639, 0, 4641, 0, 4643, 4645, 0, 4647, 4649, 0, 4651, 4653, 0, 4655, 4657, 0,
4659, 4661, 4611, 0, 0, 2397, 2399, 0, 4665, 4663, 0, 0, 576, 0, 578, 0,
158, 0, 107, 0, 4671, 0, 4675, 0, 188, 0, 4677, 0, 70, 0, 4679, 0,
606, 0, 4681, 0, 4683, 0, 2262, 0, 2265, 0, 160, 610, 0, 2277, 2280, 0,
222, 4695, 0, 626, 2289, 0, 638, 596, 0, 0, 0, 0, 4667, 4705, 4707, 4709,
4711, 0, 4713, 4673, 6662, 5185, 5243, 832, 5244, 5245, 835, 5186, 838, 5246, 5247, 5248,
5249, 5250, 5251, 5192, 841, 844, 5187, 5197, 847, 5188, 6992, 6668, 5189, 6659, 859, 862,
865, 6656, 6660, 5216, 5217, 5218, 6650, 5220, 5221, 5222, 6663, 5224, 5225, 5226, 5227, 6993,
5228, 5229, 5230, 5231, 5232, 6671, 5234, 5215, 5190, 5191, 5252, 5253, 5254, 5255, 5256, 5257,
5258, 5193, 5259, 5260, 5194, 5195, 5196, 5198, 5199, 5200, 5201, 5202, 5203, 5204, 5205, 5206,
5207, 5208, 5209, 5210, 5211, 5261, 5262, 5212, 5213, 5214, 5235, 5236, 5237, 5238, 5239, 5240,
5241, 5242, 871, 6859, 6856, 919, 5613, 5618, 5614, 6097, 5626, 5616, 5612, 5785, 5760, 5632,
828, 831, 834, 837, 840, 843, 846, 849, 852, 855, 858, 861, 864, 867, 274, 278,
282, 286, 290, 294, 298, 302, 306, 314, 318, 322, 326, 330, 310, 6646, 6653, 870,
882, 876, 918, 885, 900, 873, 897, 879, 906, 930, 945, 942, 936, 975, 921, 927,
939, 933, 954, 912, 948, 969, 957, 903, 888, 915, 924, 951, 891, 972, 909, 960,
894, 963, 966, 7414, 7424, 5928, 7459, 6783, 1110, 1116, 2406, 2428, 1131, 1134, 1137, 1140,
1143, 1152, 1155, 2405, 2408, 2430, 2411, 6662, 832, 835, 838, 841, 844, 847, 6992, 6668,
6659, 859, 862, 865, 6656, 275, 279, 283, 287, 291, 295, 299, 303, 307, 6659, 319,
323, 327, 331, 6659, 6668, 6992, 871, 6859, 6856, 919, 886, 901, 874, 898, 880, 907,
2456, 946, 943, 937, 976, 922, 1157, 940, 934, 955, 913, 949, 970, 958, 904, 6149,
6098, 5789, 6352, 5649, 5714, 6002, 6413, 895, 5665, 4716, 5613, 5618, 5614, 5834, 5729, 5705,
5801, 925, 952, 892, 973, 910, 5783, 2413, 2415, 2417, 2419, 2423, 2425, 2427, 2429, 2432,
2433, 2435, 2437, 2439, 2441, 2445, 1000, 1012, 2421, 2443, 2447, 2449, 2451, 2453, 2455, 987,
999, 1011, 6914, 6801, 6940, 6777, 2335, 2320, 4667, 554, 2232, 2235, 582, 2327, 2247, 4694,
4675, 4686, 4677, 2256, 4698, 2297, 4681, 4683, 2262, 4674, 4689, 2299, 5489, 593, 4690, 2324,
2300, 4695, 2292, 4699, 2325, 650, 4704, 654, 5490, 2331, 2334, 5492, 4702, 4701, 4692, 4703,
2239, 4705, 4707, 4709, 4711, 110, 542, 115, 2220, 120, 2223, 2226, 38, 554, 2229, 2232,
2235, 566, 570, 558, 562, 574, 578, 582, 44, 135, 50, 56, 135, 62, 62, 68,
590, 2247, 2250, 594, 598, 150, 155, 2256, 167, 606, 2262, 2265, 656, 4689, 2268, 2271,
74, 610, 160, 80, 618, 2280, 2277, 92, 622, 86, 2286, 190, 2289, 630, 2292, 634,
185, 626, 195, 638, 4699, 200, 2307, 2310, 646, 2319, 2322, 2325, 205, 650, 210, 98,
215, 215, 58, 658, 2331, 2334, 662, 4701, 666, 220, 4703, 104, 137, 1105, 1111, 1117,
1123, 1129, 1042, 1051, 1060, 1069, 1078, 990, 1002, 1014, 1023, 1032, 1041, 1050, 1059, 1068,
1077, 1104, 1110, 1116, 1122, 1128, 1491, 2879, 2467, 1434, 3099, 3125, 6798, 6789, 6792, 6918,
4717, 4721, 4715, 4719, 674, 3117, 3067, 3577, 3045, 3001, 2619, 2651, 2549, 347, 346, 3119,
3069, 3579, 3585, 3053, 336, 1498, 1497, 1272, 1260, 1350, 3587, 3055, 2881, 3007, 2925, 3077,
3589, 1533, 1452, 1512, 1524, 1443, 6790, 1503, 1527, 1446, 6793, 1506, 354, 350, 1501, 1500,
1275, 1263, 32, 32, 26, 3127, 3079, 3591, 3057, 3121, 3071, 3581, 3047, 3003, 2653, 3123,
3073, 3583, 3049, 3005, 2655, 3021, 2663, 342, 2489, 2866, 2867, 334, 1224, 2877, 2551, 2943,
2706, 2963, 2622, 2623, 3009, 3056, 3029, 1515, 3031, 3051, 1521, 1536, 2705, 358, 1332, 2707,
3147, 2731, 2791, 6786, 6759, 1156, 1114, 1120, 1126, 1132, 1135, 1138, 1141, 1144, 984, 996,
1008, 1020, 1029, 1038, 1047, 1056, 1065, 1074, 1101, 1107, 1113, 1119, 1125, 1131, 1134, 1137,
1140, 1143, 1152, 1155, 6804, 7552, 6318, 5946, 6338, 6325, 6025, 5619, 5726, 6476, 5787, 976,
5745, 5786, 5892, 6108, 6194, 6267, 6282, 6295, 6354, 5971, 6004, 6043, 6078, 6253, 6363, 6432,
5627, 5716, 5976, 6051, 6266, 6452, 5824, 6031, 6262, 6298, 5901, 6217, 6285, 5850, 5949, 6010,
6068, 6357, 5637, 5670, 5694, 5922, 5974, 6050, 6114, 6200, 6264, 6270, 6335, 6400, 6444, 6451,
6127, 6141, 6180, 6247, 6373, 6454, 6307, 5773, 5855, 6165, 6209, 6063, 6129, 6324, 6398, 5772,
5815, 5972, 6015, 6026, 6178, 6186, 6384, 5693, 6212, 5673, 5672, 6151, 6181, 6252, 6386, 6314,
5902, 6310, 5622, 5804, 5873, 6073, 6102, 5702, 6131, 5641, 5867, 5615, 5999, 5927, 6177, 5721,
5769, 6117, 6254, 6305, 5987, 6347, 5997, 5906, 6238, 5912, 6101, 5631, 5657, 5671, 5963, 6172,
6228, 6306, 6367, 5696, 5734, 5789, 5852, 5933, 6032, 6132, 6380, 6434, 6455, 6461, 5688, 5944,
5982, 6344, 5842, 5886, 5893, 5920, 6028, 6045, 6087, 6148, 6183, 6207, 6340, 6256, 6350, 6374,
5680, 5689, 5739, 6042, 6290, 5849, 5871, 5910, 5985, 6164, 6070, 5635, 5757, 5829, 5874, 6077,
6084, 6197, 6205, 6368, 6397, 6401, 6415, 5638, 6145, 6364, 6391, 5878, 5629, 5647, 5805, 5813,
5930, 6048, 6107, 6259, 6353, 6475, 5940, 6383, 5687, 5955, 5958, 6008, 6021, 6080, 6100, 6126,
6176, 6418, 901, 5896, 6387, 5643, 5822, 6016, 6341, 5865, 5879, 5960, 6388, 5681, 5731, 5817,
5937, 5952, 5966, 6001, 6079, 6105, 6192, 6291, 6294, 6366, 6394, 5706, 6022, 5732, 6049, 6088,
6263, 6389, 6446, 6456, 5957, 6014, 6219, 6158, 6160, 6167, 6067, 6040, 6313, 5633, 6242, 5682,
5679, 5845, 5903, 6170, 5800, 6005, 5943, 6343, 6287, 6385, 6300, 5851, 5651, 5750, 5768, 5939,
5674, 6069, 6113, 6134, 6139, 6140, 6144, 6403, 6168, 6198, 6265, 6309, 6351, 6359, 6423, 6424,
6425, 6450, 5639, 5648, 5652, 5692, 5695, 5710, 5747, 5752, 5754, 5767, 5770, 5816, 5818, 5876,
5883, 5885, 5891, 5925, 5935, 5941, 5964, 6011, 6018, 6027, 6046, 6054, 6081, 6128, 955, 6136,
6135, 6137, 6138, 958, 6142, 6143, 6152, 6156, 6161, 6185, 6187, 6191, 6201, 6220, 6231, 6255,
6297, 6301, 6311, 6312, 6326, 6327, 6349, 6395, 6411, 6417, 7431, 7578, 7464, 7404, 5669, 7408,
7406, 7407, 7409, 5691, 5698, 7415, 5746, 7416, 7417, 7419, 7420, 7421, 7422, 7425, 7426, 7428,
7430, 7432, 5882, 7433, 7434, 7435, 7439, 7440, 7441, 7442, 5950, 7445, 5983, 7446, 6024, 6034,
7456, 6055, 7449, 6085, 7450, 7451, 7452, 7453, 7454, 6116, 6120, 7455, 6130, 7457, 7460, 7462,
7463, 7465, 7466, 6280, 7467, 7468, 7470, 7471, 6308, 6315, 6342, 7474, 7475, 7476, 7477, 7478,
6414, 6438, 7576, 7575, 7577, 5566, 7402, 5576, 7580, 7581, 7582, 7479, 7480, 1488, 6772, 6775,
1485, 1488, 3151, 3151, 3749, 3743, 3745, 3751, 3747, 3779, 0, 3815, 5147, 3759, 3767, 3769,
3787, 3789, 5146, 3807, 3813, 4754, 3809, 3811, 1842, 1845, 3753, 3755, 3757, 3761, 3765, 3767,
3769, 3773, 3775, 3777, 3781, 3783, 3785, 3789, 3791, 3793, 3795, 3797, 3799, 3803, 3805, 3807,
1845, 3813, 3771, 3763, 3787, 3801, 3759, 5151, 5151, 5155, 5155, 5155, 5155, 5156, 5156, 5156,
5156, 5158, 5158, 5158, 5158, 5154, 5154, 5154, 5154, 5157, 5157, 5157, 5157, 5153, 5153, 5153,
5153, 5169, 5169, 5169, 5169, 5170, 5170, 5170, 5170, 5160, 5160, 5160, 5160, 5159, 5159, 5159,
5159, 5161, 5161, 5161, 5161, 5162, 5162, 5162, 5162, 5165, 5165, 5164, 5164, 5166, 5166, 5163,
5163, 5168, 5168, 5167, 5167, 5171, 5171, 5171, 5171, 5173, 5173, 5173, 5173, 5175, 5175, 5175,
5175, 5174, 5174, 5174, 5174, 5176, 5176, 5177, 5177, 5177, 5177, 4047, 4047, 4041, 4041, 4041,
4041, 5178, 5178, 5178, 5178, 4045, 4045, 4045, 4045, 5172, 5172, 5172, 5172, 4043, 4043, 3842,
3842, 3846, 3846, 4043, 5182, 5182, 5180, 5180, 5181, 5181, 3848, 3848, 3848, 3848, 4036, 4036,
2151, 2151, 2199, 2199, 2178, 2178, 2190, 2190, 2187, 2187, 2193, 2193, 2196, 2196, 2196, 2181,
2181, 2181, 519, 519, 519, 519, 2154, 2157, 2169, 2184, 3855, 1848, 1851, 3859, 3865, 3867,
1860, 1866, 1875, 1890, 3877, 3879, 3881, 3887, 3893, 3895, 2107, 2110, 2089, 2119, 2095, 3897,
2098, 1920, 1923, 1929, 1938, 1959, 1965, 3929, 1971, 1974, 3933, 3939, 1983, 3945, 1986, 1995,
3951, 2004, 3963, 3965, 2016, 2019, 3967, 3969, 3971, 2031, 3973, 3975, 3977, 3979, 3981, 3983,
3985, 2037, 3987, 3989, 2055, 2064, 2067, 2073, 1, 10, 2134, 2091, 2100, 2146, 2128, 2171,
2115, 2124, 3999, 2130, 4009, 4034, 4013, 2136, 4015, 4017, 2139, 2142, 4027, 2148, 4035, 4038,
3899, 3901, 4025, 705, 708, 711, 714, 717, 720, 2163, 2166, 2169, 2172, 2184, 512, 3857,
3859, 3861, 3865, 3867, 3869, 3871, 1890, 3873, 3877, 3879, 3883, 3885, 3887, 3889, 3893, 3895,
3967, 3969, 3973, 3975, 3977, 3985, 2037, 3987, 3989, 2073, 1, 10, 3997, 2146, 4001, 4003,
2130, 4006, 4009, 4034, 4025, 4029, 4031, 2148, 4033, 4035, 4038, 2154, 2157, 2160, 2169, 2175,
3855, 1848, 1851, 3859, 3863, 1860, 1866, 1875, 1890, 3875, 3887, 2107, 2110, 2089, 2119, 2095,
2098, 1920, 1923, 1929, 1938, 1959, 3921, 1965, 3929, 1971, 1974, 3933, 3939, 3945, 1986, 1995,
3951, 2004, 3963, 3965, 2016, 2019, 3971, 2031, 3979, 3981, 3983, 3985, 2037, 2055, 2064, 2067,
2073, 24, 2134, 2091, 2100, 2146, 2115, 2124, 3999, 2130, 4007, 4013, 2136, 4019, 2139, 2142,
4027, 2148, 4018, 2169, 2175, 3859, 3863, 1890, 3875, 3887, 3891, 1938, 3905, 1953, 3915, 3985,
2037, 2073, 2130, 4007, 2148, 4018, 2007, 2010, 2013, 3941, 3943, 3947, 3949, 3953, 3955, 3907,
3909, 3917, 3919, 2122, 2159, 2113, 2156, 1927, 4028, 3925, 3927, 3935, 3937, 1941, 1947, 3911,
1953, 3913, 3903, 3923, 3931, 3941, 3943, 3947, 3949, 3953, 3955, 3907, 3909, 3917, 3919, 2122,
2159, 2113, 2156, 1927, 4028, 3925, 3927, 3935, 3937, 1941, 1947, 3911, 1953, 3913, 3903, 3923,
3931, 1941, 1947, 3911, 1953, 3905, 3915, 1983, 1920, 1923, 1929, 1941, 1947, 3911, 1983, 3945,
3851, 3851, 1854, 1863, 1863, 1866, 1869, 1878, 1881, 1884, 2090, 2090, 1914, 1911, 1923, 1917,
1920, 1935, 1935, 1932, 1938, 1938, 1956, 1956, 1965, 1944, 1944, 1941, 1950, 1950, 1953, 1953,
1968, 1974, 1974, 1977, 1977, 1980, 1983, 1986, 1989, 1989, 1992, 1998, 2004, 2001, 2016, 2016,
2025, 2028, 2058, 2064, 2061, 2049, 2049, 2067, 2067, 2070, 2070, 2088, 526, 2091, 2076, 2082,
2094, 2097, 2079, 2133, 2136, 2118, 2121, 2109, 2109, 2112, 2130, 2127, 2145, 2145, 1851, 1860,
1857, 1875, 1872, 1890, 1887, 1905, 1893, 1902, 1926, 1959, 1947, 1971, 2055, 2073, 2142, 2139,
2148, 2146, 2031, 2124, 2025, 2058, 1995, 2037, 2106, 2100, 2052, 2034, 2052, 2106, 1896, 1908,
2085, 2019, 1848, 2034, 1986, 1965, 1929, 2115, 1962, 2022, 4, 510, 526, 522, 514, 9,
14, 0, 0, 18, 518, 6901, 5473, 5474, 1180, 4757, 2464, 2466, 7399, 7400, 978, 979,
5416, 5415, 4764, 6747, 6749, 4766, 4768, 6879, 6881, 5483, 5484, 5477, 5478, 5475, 5476, 5479,
5480, 5481, 5482, 4760, 4762, 2373, 4764, 6901, 5473, 1226, 4757, 1180, 2466, 2464, 5416, 6747,
6749, 4766, 4768, 6879, 6881, 4748, 4751, 4753, 4754, 4756, 2457, 2461, 2459, 4761, 4749, 4750,
4758, 2393, 3957, 705, 708, 711, 2007, 714, 2010, 717, 2013, 720, 3959, 2395, 3961, 5148,
2041, 2041, 2044, 2044, 4021, 4021, 2047, 2047, 2199, 2199, 2199, 2199, 3998, 3998, 3867, 3867,
3867, 3867, 5150, 5150, 3879, 3879, 3879, 3879, 3895, 3895, 3895, 3895, 4014, 4014, 4014, 4014,
3982, 3982, 3982, 3982, 4028, 4028, 4028, 4028, 529, 529, 3899, 3899, 4030, 4030, 4032, 4032,
3909, 3909, 3909, 3909, 3919, 3919, 3919, 3919, 3927, 3927, 3927, 3927, 3937, 3937, 3937, 3937,
3943, 3943, 3943, 3943, 3945, 3945, 3945, 3945, 3949, 3949, 3949, 3949, 3955, 3955, 3955, 3955,
3969, 3969, 3969, 3969, 3975, 3975, 3975, 3975, 3989, 3989, 3989, 3989, 3995, 3995, 3995, 3995,
3997, 3997, 3997, 3997, 4034, 4034, 4034, 4034, 4019, 4019, 4019, 4019, 4023, 4023, 4036, 4036,
4039, 4039, 4039, 4039, 2040, 2040, 2043, 2043, 2046, 2046, 2046, 2046, 2464, 4747, 4748, 4749,
4750, 4751, 4752, 6747, 6749, 4753, 4754, 6901, 4756, 1226, 1441, 6882, 6884, 6886, 6888, 6890,
6892, 6894, 6896, 6898, 6900, 1180, 4757, 2457, 2459, 2461, 2466, 4758, 6902, 6676, 6904, 6923,
6785, 6910, 6691, 6916, 6918, 6920, 6703, 6777, 6709, 6943, 6715, 6783, 6721, 6724, 6930, 6932,
6919, 6941, 6936, 6764, 6938, 6935, 4760, 4761, 4762, 4763, 4764, 4765, 6805, 3052, 3126, 6798,
6940, 6775, 6915, 2959, 6909, 3076, 3023, 6911, 6799, 3490, 3115, 3131, 2490, 6802, 6929, 6931,
3205, 3209, 3223, 3227, 3247, 3257, 4766, 4767, 4768, 4769, 5471, 5472, 5474, 5479, 5480, 5473,
5493, 4711, 545, 623, 5488, 183, 2227, 5491, 583, 208, 2323, 2339, 2335, 2320, 4667, 554,
2232, 2235, 582, 2327, 2247, 4694, 4675, 4686, 4677, 2256, 4698, 2297, 4681, 4683, 2262, 4674,
4689, 2299, 5489, 593, 4690, 2324, 2300, 4695, 2292, 4699, 2325, 650, 4704, 654, 5490, 2331,
2334, 5492, 4702, 4701, 4692, 4703, 2239, 4705, 4700, 4714, 4696, 5215, 6662, 5185, 5243, 832,
5244, 5245, 835, 5186, 838, 5246, 5247, 5248, 5249, 5250, 5251, 5192, 841, 844, 5187, 5197,
847, 5188, 6992, 6668, 5189, 6659, 859, 862, 865, 6656, 6660, 5216, 5217, 5218, 6650, 5220,
5221, 5222, 6663, 5224, 5225, 5226, 5227, 6993, 5228, 5229, 5230, 5231, 5232, 6671, 5234, 4770,
4771, 4774, 2371, 4773, 4772, 5419, 5468, 4527, 5436, 4529, 5437, 5469, 5470, 0, 7078, 0,
7080, 0, 7082, 0, 4727, 2352, 2340, 2343, 2346, 2349, 2352, 0, 2358, 2364, 2355, 2361,
2358, 2364, 6902, 6691, 6920, 6703, 6715, 6930, 6932, 6919, 6941, 6936, 6764, 6938, 6805, 3052,
3126, 6775, 3023, 6799, 3490, 3131, 2490, 6802, 6929, 6931, 3205, 3209, 3223, 3227, 3247, 3257,
7086, 7094, 6956, 4948, 4950, 3503, 4951, 6958, 4952, 7075, 4953, 4954, 4955, 4956, 4957, 3523,
6962, 4952, 4959, 4960, 6964, 4961, 4962, 4963, 6966, 5439, 3557, 4967, 4969, 3561, 4970, 3565,
4971, 4508, 4972, 4973, 3593, 4974, 4975, 3597, 3601, 4977, 4978, 4979, 3611, 4980, 4981, 4982,
3615, 5438, 3561, 4971, 4972, 4980, 3601, 4976, 7135, 4990, 6882, 6884, 6886, 6888, 6890, 6892,
6894, 6896, 6898, 6900, 1099, 6882, 6884, 6886, 6888, 6890, 6892, 6894, 6896, 6898, 6900, 6672,
6675, 6678, 6681, 6684, 6687, 6690, 6693, 6696, 6699, 6702, 6705, 6708, 6711, 6714, 6717, 6720,
6723, 6726, 6729, 6732, 6735, 6738, 6741, 6744, 6747, 6852, 6904, 6934, 6676, 6943, 6783, 6930,
6936, 6912, 6922, 6924, 6780, 6906, 7076, 5898, 7423, 7412, 2262, 6859, 5782, 7469, 5785, 7405,
7444, 7448, 5930, 7411, 7429, 5660, 7443, 7410, 7461, 6093, 7472, 7418, 7413, 7447, 7436, 7438,
871, 6856, 7473, 5834, 5618, 5729, 7437, 6330, 6868, 6873, 6855, 6858, 6864, 6876, 6867, 6879,
6861, 6870, 5623, 5621, 5625, 6543, 5636, 5640, 5642, 5644, 5645, 5646, 5546, 6547, 5653, 5654,
5658, 6544, 5547, 5656, 5660, 6546, 5664, 5666, 5634, 5668, 6634, 5676, 5678, 5549, 5683, 5684,
5685, 5686, 5550, 5699, 5700, 5709, 5711, 5715, 5717, 5718, 6550, 6037, 5723, 5724, 6551, 5727,
5728, 5730, 5737, 5733, 5735, 5736, 5738, 5740, 5741, 5742, 5743, 5744, 5748, 5749, 5751, 5758,
5759, 5753, 5755, 5775, 5762, 5763, 5764, 5761, 5766, 5765, 5771, 6553, 5776, 5777, 5779, 5782,
5784, 5788, 6554, 6555, 5791, 5792, 5793, 5790, 5794, 5551, 7401, 5796, 5797, 6556, 5802, 5803,
5806, 6557, 5808, 5809, 7427, 5811, 5552, 5814, 5821, 5820, 6559, 5823, 6560, 5826, 5825, 5827,
5831, 5832, 5553, 5836, 5838, 5839, 5840, 5554, 6561, 5555, 5846, 5847, 5848, 6644, 5854, 6563,
6222, 5858, 5556, 6568, 6605, 5862, 5863, 5557, 5866, 5869, 5870, 5872, 5875, 5559, 5558, 6564,
5877, 5880, 5881, 5884, 5889, 5887, 5888, 5890, 4718, 5895, 5899, 5900, 5904, 5908, 6565, 5907,
5905, 5909, 5911, 5915, 6566, 5916, 5914, 5913, 5560, 5917, 5919, 5921, 5918, 5561, 5926, 6567,
5936, 5947, 5938, 5564, 5563, 5562, 5661, 5662, 5948, 5942, 6213, 5589, 5951, 5954, 5953, 6572,
5565, 5959, 5956, 5962, 6573, 5965, 5961, 5967, 5968, 5969, 5970, 5973, 6574, 5975, 5567, 5978,
6575, 5979, 5568, 5981, 5984, 5988, 6576, 6558, 6577, 5995, 6578, 5998, 6000, 5996, 6003, 6007,
6009, 6012, 6013, 6579, 6006, 6019, 6020, 5569, 6023, 6580, 6017, 6029, 6581, 6582, 6030, 6035,
6033, 5570, 6036, 6039, 6038, 6041, 6545, 6044, 6583, 6047, 7579, 6052, 6060, 6584, 6064, 6065,
6585, 6586, 6071, 6075, 5571, 6076, 5572, 6082, 6083, 6086, 6089, 5573, 6094, 6587, 6099, 6588,
6562, 6106, 6589, 6590, 6591, 5574, 5575, 6593, 6592, 6594, 6595, 6118, 6119, 6121, 5577, 5578,
6596, 6125, 5579, 6597, 6598, 6599, 6150, 5580, 6153, 6154, 6600, 6601, 7458, 5581, 6602, 6162,
6163, 5582, 6603, 6169, 5583, 6173, 6171, 6175, 6604, 6179, 5584, 6182, 6184, 6188, 5585, 6606,
6607, 5586, 6608, 6193, 6609, 6196, 6199, 6610, 6611, 6206, 6612, 6208, 6569, 5588, 6214, 6215,
5590, 6216, 5795, 6613, 6614, 6570, 6571, 6223, 6346, 5591, 6233, 6232, 6234, 5690, 6235, 6236,
6237, 6239, 6615, 6240, 6244, 6245, 6241, 6246, 6251, 6243, 6248, 6249, 6250, 6616, 6618, 6617,
5592, 6257, 6258, 6260, 6622, 6261, 6619, 5593, 5594, 6620, 6621, 5595, 6269, 6271, 6272, 6275,
6274, 6277, 6276, 6278, 6279, 6281, 7403, 6283, 6284, 5596, 6288, 6289, 6623, 6292, 6293, 5597,
6296, 5548, 6624, 6625, 5598, 5599, 6304, 6319, 6626, 6322, 6323, 6328, 6331, 6627, 6548, 6334,
6333, 6336, 6549, 6339, 6628, 6629, 6356, 6358, 6360, 6630, 6361, 6369, 6371, 6372, 6370, 6375,
6376, 6631, 6379, 5600, 6381, 6632, 5601, 6393, 5828, 6399, 6633, 6635, 5602, 5603, 6408, 6636,
5604, 6637, 6416, 6638, 6422, 5605, 6426, 6429, 6431, 6433, 5606, 6639, 6445, 6448, 5607, 5608,
6449, 6640, 5609, 6641, 6642, 6643, 6458, 5610, 6463, 6465, 6466, 6468, 6470, 6472,
]
_lookup_composition_compat_decomp_middle = _all_ushort(_lookup_composition_compat_decomp_middle)
def lookup_composition_compat_decomp_middle(index): return intmask(_lookup_composition_compat_decomp_middle[index])

def lookup_composition_canon_decomp_len(index):
    if 68 <= index <= 4343:
        return lookup_composition_canon_decomp_len_middle(index - 68)
    if index < 68:
        return 0
    if index < 4821:
        return 1
    raise KeyError

_lookup_composition_canon_decomp_len_middle = (
'\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02'
'\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x00\x00'
'\x00\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03\x02\x02\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x00\x01\x02\x00\x00\x00\x01\x00\x01'
'\x02\x02\x01\x02\x02\x02\x02\x02\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02'
'\x02\x02\x02\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x00'
'\x00\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x00\x02\x02\x02\x02\x00'
'\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00'
'\x00\x00\x00\x00\x00\x02\x02\x02\x00\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00'
'\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02'
'\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00'
'\x02\x00\x02\x00\x00\x00\x02\x00\x02\x00\x02\x00\x00\x02\x02\x02\x02\x02\x02\x02'
'\x02\x00\x00\x00\x02\x02\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x02\x02'
'\x02\x00\x00\x02\x02\x00\x02\x00\x00\x00\x02\x02\x02\x00\x00\x02\x00\x00\x00\x02'
'\x00\x00\x02\x02\x02\x03\x00\x00\x00\x00\x00\x02\x02\x02\x00\x00\x00\x00\x02\x02'
'\x03\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00'
'\x00\x02\x00\x02\x02\x00\x02\x00\x02\x02\x02\x02\x02\x02\x02\x00\x02\x00\x00\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x00\x02\x00\x02\x00\x00\x02\x02'
'\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02'
'\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x02\x02\x02\x02\x02\x03\x03'
'\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02'
'\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02'
'\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03'
'\x03\x03\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x03\x03\x03\x03\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03'
'\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03'
'\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03'
'\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03\x03\x03\x02\x02\x03\x03'
'\x03\x03\x03\x03\x02\x03\x03\x03\x02\x02\x03\x03\x03\x03\x03\x03\x02\x02\x03\x03'
'\x03\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x04\x04\x04\x04\x04\x04\x03\x03\x04\x04\x04\x04\x04\x04\x03\x03\x04\x04\x04\x04'
'\x04\x04\x03\x03\x04\x04\x04\x04\x04\x04\x03\x03\x04\x04\x04\x04\x04\x04\x03\x03'
'\x04\x04\x04\x04\x04\x04\x02\x02\x03\x02\x03\x02\x03\x02\x02\x02\x02\x02\x00\x01'
'\x00\x00\x02\x03\x02\x03\x02\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03'
'\x02\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x03\x02\x02\x02\x03\x02\x02\x02'
'\x02\x02\x02\x02\x01\x03\x02\x03\x02\x03\x02\x02\x02\x02\x02\x01\x00\x01\x01\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x02\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x02'
'\x00\x02\x00\x02\x00\x02\x00\x02\x00\x00\x00\x00\x00\x02\x00\x02\x00\x02\x00\x02'
'\x00\x02\x00\x02\x00\x00\x02\x02\x02\x02\x02\x00\x00\x02\x02\x00\x00\x02\x02\x00'
'\x00\x00\x00\x02\x02\x00\x00\x02\x02\x00\x00\x02\x02\x00\x00\x00\x00\x00\x00\x02'
'\x02\x02\x02\x00\x00\x00\x00\x02\x02\x02\x02\x02\x02\x02\x02\x01\x01\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x02'
'\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x02\x00\x00\x00\x00\x00\x02\x00'
'\x00\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00'
'\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02'
'\x00\x02\x02\x00\x02\x02\x00\x00\x00\x00\x02\x02\x02\x02\x02\x00\x02\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x02\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x03\x03'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x02\x00\x02\x00\x02\x00\x02\x02\x03\x03\x03\x03\x03\x00\x02\x02'
'\x03\x03\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
)
def lookup_composition_canon_decomp_len_middle(index): return ord(_lookup_composition_canon_decomp_len_middle[index])

def lookup_composition_canon_decomp(index):
    if 68 <= index <= 4819:
        return lookup_composition_canon_decomp_middle(index - 68)
    if index < 68:
        return 0
    if index < 4821:
        return 6645
    raise KeyError

# estimated 9.3 KiB
_lookup_composition_canon_decomp_middle = [
2469, 2471, 1194, 2473, 1212, 1215, 0, 1227, 2521, 2523, 1245, 2531, 2589, 2591, 2593, 1266,
2675, 2689, 2691, 1287, 1296, 1308, 0, 2757, 2759, 2761, 1368, 2811, 2839, 2841, 1404, 2843,
1422, 1425, 0, 1455, 2899, 2901, 1470, 2909, 2969, 2971, 2973, 1494, 3085, 3101, 3103, 1548,
1557, 1569, 0, 3177, 3179, 3181, 1620, 3231, 3241, 2475, 2845, 1206, 1416, 2487, 2857, 2497,
2869, 2499, 2871, 2501, 2873, 2503, 2875, 2511, 2887, 1251, 1476, 2527, 2905, 2529, 2907, 2541,
2919, 2535, 2913, 2555, 2931, 2559, 2935, 2561, 2937, 2565, 2941, 2569, 2945, 2595, 2975, 2597,
2977, 2599, 2979, 2613, 2993, 2601, 0, 0, 2617, 2997, 2631, 3017, 2641, 3035, 2645, 3039,
2643, 3037, 0, 0, 2673, 3083, 2683, 3093, 2679, 3089, 0, 1302, 1563, 2693, 3105, 2697,
3109, 2715, 3133, 2725, 3143, 2719, 3137, 1338, 1596, 2733, 3153, 2739, 3159, 1341, 1599, 2751,
3171, 2745, 3165, 1353, 1605, 1356, 1608, 2763, 3183, 2767, 3187, 2769, 3189, 2781, 3201, 2797,
3215, 2813, 3233, 2821, 2827, 3249, 2831, 3253, 1231, 1459, 0, 1323, 1584, 1383, 1635, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 2479, 2849, 2605, 2985, 2699, 3111, 2771,
3191, 1365, 1617, 1362, 1614, 1368, 1620, 1359, 1611, 1212, 1422, 1209, 1419, 3283, 3337, 2563,
2939, 2627, 3013, 1329, 1590, 1329, 1590, 3469, 3487, 2999, 0, 0, 0, 2553, 2929, 2671,
3081, 1215, 1425, 3281, 3335, 3313, 3367, 2481, 2851, 2483, 2853, 2537, 2915, 2539, 2917, 2607,
2987, 2609, 2989, 2701, 3113, 2703, 3115, 2721, 3139, 2723, 3141, 2773, 3193, 2775, 3195, 2737,
3157, 2749, 3169, 2575, 2951, 1209, 1419, 1257, 1482, 1308, 1569, 1293, 1554, 1305, 1566, 1305,
1566, 2817, 3237, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 6839, 6842, 0, 6963, 6832, 0, 0,
0, 4938, 0, 4757, 3261, 3493, 3034, 3503, 3507, 3513, 3523, 3529, 3539, 1761, 0, 0,
0, 0, 0, 0, 0, 0, 6825, 6834, 1713, 3561, 1743, 3569, 1800, 0, 0, 0,
0, 0, 0, 0, 0, 1764, 1803, 3597, 3605, 1827, 0, 0, 0, 3633, 3635, 0,
0, 0, 0, 0, 0, 0, 0, 3645, 3649, 3643, 0, 3637, 3665, 3657, 3671, 0,
0, 0, 0, 0, 0, 3661, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 3705, 0, 0, 0, 0, 0, 0, 3689, 3693, 3687, 0, 3727, 3709, 3701,
3715, 0, 0, 3729, 3731, 3651, 3695, 3639, 3683, 3641, 3685, 3647, 3691, 0, 0, 3733,
3735, 3653, 3697, 3655, 3699, 3659, 3703, 3663, 3707, 3667, 3711, 0, 0, 3737, 3739, 3681,
3725, 3669, 3713, 3673, 3717, 3675, 3719, 3677, 3721, 3679, 3723, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 2041, 2044, 4021, 2047, 2199, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 4047, 0, 4041, 0, 4045, 0, 0, 0, 4061, 0,
4067, 0, 4069, 0, 0, 4049, 4051, 4053, 4055, 4057, 4059, 4063, 4065, 0, 0, 0,
4077, 4079, 0, 4071, 4073, 4075, 4089, 4091, 4081, 4083, 4085, 4087, 0, 0, 4099, 4097,
4101, 0, 0, 4093, 4095, 0, 4103, 0, 0, 0, 4105, 4109, 4107, 0, 0, 4111,
0, 0, 0, 4113, 0, 0, 4115, 4117, 2202, 2202, 0, 0, 0, 0, 0, 4121,
4125, 4123, 0, 0, 0, 0, 4127, 2205, 2205, 4129, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 4143, 4145, 4147, 4149, 4151, 4141, 0, 0, 4153, 0, 4155,
4169, 0, 4173, 0, 2212, 4159, 4161, 4163, 4165, 4167, 4157, 0, 4177, 0, 0, 0,
6994, 0, 6996, 0, 6998, 0, 7000, 0, 7002, 0, 7004, 0, 0, 7006, 0, 7008,
0, 0, 7010, 7012, 0, 7014, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 2485, 2855, 2491, 2859, 2493, 2861, 2495, 2863, 1227, 1455,
2509, 2885, 2513, 2889, 2519, 2895, 2515, 2891, 2517, 2893, 1248, 1473, 1251, 1476, 2543, 2921,
2545, 2923, 1257, 1482, 2547, 2927, 2557, 2933, 2571, 2947, 2577, 2953, 2573, 2949, 2579, 2955,
2581, 2957, 2615, 2995, 1266, 1494, 2625, 3011, 2629, 3015, 2633, 3019, 1269, 1518, 1269, 1518,
2649, 3043, 2647, 3041, 2657, 3059, 2659, 3061, 2661, 3063, 2677, 3087, 2681, 3091, 2687, 3097,
2685, 3095, 1290, 1551, 1296, 1557, 1299, 1560, 1302, 1563, 2709, 3129, 2711, 3131, 2717, 3135,
1335, 1593, 1335, 1593, 2727, 3145, 2735, 3155, 1344, 1602, 1338, 1596, 1341, 1599, 1344, 1602,
2743, 3161, 2747, 3167, 2755, 3175, 2753, 3173, 2779, 3199, 2785, 3205, 2783, 3203, 1353, 1605,
1356, 1608, 2787, 3207, 2789, 3209, 2793, 3211, 2795, 3213, 2801, 3219, 2799, 3217, 2803, 3223,
2805, 3225, 2807, 3227, 2819, 3239, 2829, 3251, 2833, 3255, 2835, 3257, 2959, 3163, 3221, 3245,
0, 3427, 1221, 1431, 2477, 2847, 1188, 1398, 1185, 1395, 1194, 1404, 1191, 1401, 1218, 1428,
1200, 1410, 1197, 1407, 1206, 1416, 1203, 1413, 1221, 1431, 1254, 1479, 2533, 2911, 2525, 2903,
1239, 1464, 1236, 1461, 1245, 1470, 1242, 1467, 1254, 1479, 2603, 2983, 2611, 2991, 1326, 1587,
2695, 3107, 1281, 1542, 1278, 1539, 1287, 1548, 1284, 1545, 1326, 1587, 1314, 1575, 1311, 1572,
1320, 1581, 1317, 1578, 1323, 1584, 2777, 3197, 2765, 3185, 1374, 1626, 1371, 1623, 1380, 1632,
1377, 1629, 1383, 1635, 2809, 3229, 2825, 3247, 2823, 3243, 2815, 3235, 1716, 1719, 438, 450,
442, 454, 446, 458, 1641, 1644, 366, 378, 370, 382, 374, 386, 1731, 1737, 1728, 1734,
1731, 1737, 1650, 1656, 1647, 1653, 1650, 1656, 1746, 1749, 462, 474, 466, 478, 470, 482,
1659, 1662, 390, 402, 394, 406, 398, 410, 1773, 1782, 1767, 1776, 1770, 1779, 1773, 1782,
1671, 1680, 1665, 1674, 1668, 1677, 1671, 1680, 1788, 1794, 1785, 1791, 1788, 1794, 1686, 1692,
1683, 1689, 1686, 1692, 1812, 1821, 1806, 1815, 1809, 1818, 1812, 1821, 1701, 1695, 1698, 1701,
1830, 1833, 486, 498, 490, 502, 494, 506, 1704, 1707, 414, 426, 418, 430, 422, 434,
1710, 1713, 3559, 3561, 1740, 1743, 3567, 3569, 3595, 3597, 3603, 3605, 1824, 1827, 1716, 1719,
438, 450, 442, 454, 446, 458, 1641, 1644, 366, 378, 370, 382, 374, 386, 1746, 1749,
462, 474, 466, 478, 470, 482, 1659, 1662, 390, 402, 394, 406, 398, 410, 1830, 1833,
486, 498, 490, 502, 494, 506, 1704, 1707, 414, 426, 418, 430, 422, 434, 3553, 3551,
1710, 3555, 1713, 1725, 1722, 3497, 3495, 3491, 3493, 3499, 0, 4508, 0, 0, 3263, 1740,
3563, 1743, 1755, 1752, 3501, 3503, 3505, 3507, 3509, 4511, 4513, 4515, 3573, 3571, 1758, 1761,
3575, 1764, 3517, 3515, 3511, 3513, 4521, 4523, 4525, 3609, 3607, 1797, 1800, 3599, 3601, 3611,
1803, 3533, 3531, 3527, 3529, 3525, 3259, 3261, 4765, 1824, 3613, 1827, 1839, 1836, 3521, 3523,
3537, 3539, 3541, 4776, 0, 5412, 5413, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 6966, 6703, 1215, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4527, 4529, 4531,
4533, 4537, 4535, 0, 0, 0, 0, 4539, 0, 4541, 0, 4543, 0, 4545, 0, 4547,
0, 0, 0, 0, 0, 4549, 0, 4551, 0, 4553, 0, 4555, 0, 2459, 0, 4559,
0, 0, 4557, 2457, 2461, 4561, 4563, 0, 0, 4565, 4567, 0, 0, 4569, 4571, 0,
0, 0, 0, 4573, 4575, 0, 0, 4581, 4583, 0, 0, 4585, 4587, 0, 0, 0,
0, 0, 0, 4593, 4595, 4597, 4599, 0, 0, 0, 0, 4577, 4579, 4589, 4591, 4601,
4603, 4605, 4607, 5475, 5476, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4609, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 4613, 0, 4615, 0, 4617, 0, 4619, 0,
4621, 0, 4623, 0, 4625, 0, 4627, 0, 4629, 0, 4631, 0, 4633, 0, 4635, 0,
4637, 0, 4639, 0, 4641, 0, 4643, 4645, 0, 4647, 4649, 0, 4651, 4653, 0, 4655,
4657, 0, 4659, 4661, 4611, 0, 0, 0, 0, 0, 4665, 0, 0, 0, 576, 0,
578, 0, 158, 0, 107, 0, 4671, 0, 4675, 0, 188, 0, 4677, 0, 70, 0,
4679, 0, 606, 0, 4681, 0, 4683, 0, 2262, 0, 2265, 0, 160, 610, 0, 2277,
2280, 0, 222, 4695, 0, 626, 2289, 0, 638, 596, 0, 0, 0, 0, 4667, 4705,
4707, 4709, 4711, 0, 4713, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 6318, 5946, 6338, 6325, 6025, 5619, 5726, 6476,
5787, 976, 5745, 5786, 5892, 6108, 6194, 6267, 6282, 6295, 6354, 5971, 6004, 6043, 6078, 6253,
6363, 6432, 5627, 5716, 5976, 6051, 6266, 6452, 5824, 6031, 6262, 6298, 5901, 6217, 6285, 5850,
5949, 6010, 6068, 6357, 5637, 5670, 5694, 5922, 5974, 6050, 6114, 6200, 6264, 6270, 6335, 6400,
6444, 6451, 6127, 6141, 6180, 6247, 6373, 6454, 6307, 5773, 5855, 6165, 6209, 6063, 6129, 6324,
6398, 5772, 5815, 5972, 6015, 6026, 6178, 6186, 6384, 5693, 6212, 5673, 5672, 6151, 6181, 6252,
6386, 6314, 5902, 6310, 5622, 5804, 5873, 6073, 6102, 5702, 6131, 5641, 5867, 5615, 5999, 5927,
6177, 5721, 5769, 6117, 6254, 6305, 5987, 6347, 5997, 5906, 6238, 5912, 6101, 5631, 5657, 5671,
5963, 6172, 6228, 6306, 6367, 5696, 5734, 5789, 5852, 5933, 6032, 6132, 6380, 6434, 6455, 6461,
5688, 5944, 5982, 6344, 5842, 5886, 5893, 5920, 6028, 6045, 6087, 6148, 6183, 6207, 6340, 6256,
6350, 6374, 5680, 5689, 5739, 6042, 6290, 5849, 5871, 5910, 5985, 6164, 6070, 5635, 5757, 5829,
5874, 6077, 6084, 6197, 6205, 6368, 6397, 6401, 6415, 5638, 6145, 6364, 6391, 5878, 5629, 5647,
5805, 5813, 5930, 6048, 6107, 6259, 6353, 6475, 5940, 6383, 5687, 5955, 5958, 6008, 6021, 6080,
6100, 6126, 6176, 6418, 901, 5896, 6387, 5643, 5822, 6016, 6341, 5865, 5879, 5960, 6388, 5681,
5731, 5817, 5937, 5952, 5966, 6001, 6079, 6105, 6192, 6291, 6294, 6366, 6394, 5706, 6022, 5732,
6049, 6088, 6263, 6389, 6446, 6456, 5957, 6014, 6219, 6158, 6160, 6167, 6067, 6040, 6313, 5633,
6242, 5682, 5679, 5845, 5903, 6170, 5800, 6005, 5943, 6343, 6287, 6385, 6300, 5851, 5651, 5750,
5768, 5939, 5674, 6069, 6113, 6134, 6139, 6140, 6144, 6403, 6168, 6198, 6265, 6309, 6351, 6359,
6423, 6424, 6425, 6450, 5639, 5648, 5652, 5692, 5695, 5710, 5747, 5752, 5754, 5767, 5770, 5816,
5818, 5876, 5883, 5885, 5891, 5925, 5935, 5941, 5964, 6011, 6018, 6027, 6046, 6054, 6081, 6128,
955, 6136, 6135, 6137, 6138, 958, 6142, 6143, 6152, 6156, 6161, 6185, 6187, 6191, 6201, 6220,
6231, 6255, 6297, 6301, 6311, 6312, 6326, 6327, 6349, 6395, 6411, 6417, 7431, 7578, 7464, 7404,
5669, 7408, 7406, 7407, 7409, 5691, 5698, 7415, 5746, 7416, 7417, 7419, 7420, 7421, 7422, 7425,
7426, 7428, 7430, 7432, 5882, 7433, 7434, 7435, 7439, 7440, 7441, 7442, 5950, 7445, 5983, 7446,
6024, 6034, 7456, 6055, 7449, 6085, 7450, 7451, 7452, 7453, 7454, 6116, 6120, 7455, 6130, 7457,
7460, 7462, 7463, 7465, 7466, 6280, 7467, 7468, 7470, 7471, 6308, 6315, 6342, 7474, 7475, 7476,
7477, 7478, 6414, 6438, 7576, 7575, 7577, 5566, 7402, 5576, 7580, 7581, 7582, 7479, 7480, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3779, 0, 3815, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 3809, 3811, 1842, 1845, 3753, 3755, 3757, 3761,
3765, 3767, 3769, 3773, 3775, 3777, 3781, 3783, 3785, 3789, 3791, 3793, 3795, 3797, 3799, 3803,
3805, 3807, 1845, 3813, 3771, 3763, 3787, 3801, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
7078, 0, 7080, 0, 7082, 0, 4727, 2352, 2340, 2343, 2346, 2349, 2352, 0, 2358, 2364,
2355, 2361, 2358, 2364, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 5623, 5621, 5625, 6543, 5636, 5640, 5642, 5644, 5645, 5646, 5546, 6547,
5653, 5654, 5658, 6544, 5547, 5656, 5660, 6546, 5664, 5666, 5634, 5668, 6634, 5676, 5678, 5549,
5683, 5684, 5685, 5686, 5550, 5699, 5700, 5709, 5711, 5715, 5717, 5718, 6550, 6037, 5723, 5724,
6551, 5727, 5728, 5730, 5737, 5733, 5735, 5736, 5738, 5740, 5741, 5742, 5743, 5744, 5748, 5749,
5751, 5758, 5759, 5753, 5755, 5775, 5762, 5763, 5764, 5761, 5766, 5765, 5771, 6553, 5776, 5777,
5779, 5782, 5784, 5788, 6554, 6555, 5791, 5792, 5793, 5790, 5794, 5551, 7401, 5796, 5797, 6556,
5802, 5803, 5806, 6557, 5808, 5809, 7427, 5811, 5552, 5814, 5821, 5820, 6559, 5823, 6560, 5826,
5825, 5827, 5831, 5832, 5553, 5836, 5838, 5839, 5840, 5554, 6561, 5555, 5846, 5847, 5848, 6644,
5854, 6563, 6222, 5858, 5556, 6568, 6605, 5862, 5863, 5557, 5866, 5869, 5870, 5872, 5875, 5559,
5558, 6564, 5877, 5880, 5881, 5884, 5889, 5887, 5888, 5890, 4718, 5895, 5899, 5900, 5904, 5908,
6565, 5907, 5905, 5909, 5911, 5915, 6566, 5916, 5914, 5913, 5560, 5917, 5919, 5921, 5918, 5561,
5926, 6567, 5936, 5947, 5938, 5564, 5563, 5562, 5661, 5662, 5948, 5942, 6213, 5589, 5951, 5954,
5953, 6572, 5565, 5959, 5956, 5962, 6573, 5965, 5961, 5967, 5968, 5969, 5970, 5973, 6574, 5975,
5567, 5978, 6575, 5979, 5568, 5981, 5984, 5988, 6576, 6558, 6577, 5995, 6578, 5998, 6000, 5996,
6003, 6007, 6009, 6012, 6013, 6579, 6006, 6019, 6020, 5569, 6023, 6580, 6017, 6029, 6581, 6582,
6030, 6035, 6033, 5570, 6036, 6039, 6038, 6041, 6545, 6044, 6583, 6047, 7579, 6052, 6060, 6584,
6064, 6065, 6585, 6586, 6071, 6075, 5571, 6076, 5572, 6082, 6083, 6086, 6089, 5573, 6094, 6587,
6099, 6588, 6562, 6106, 6589, 6590, 6591, 5574, 5575, 6593, 6592, 6594, 6595, 6118, 6119, 6121,
5577, 5578, 6596, 6125, 5579, 6597, 6598, 6599, 6150, 5580, 6153, 6154, 6600, 6601, 7458, 5581,
6602, 6162, 6163, 5582, 6603, 6169, 5583, 6173, 6171, 6175, 6604, 6179, 5584, 6182, 6184, 6188,
5585, 6606, 6607, 5586, 6608, 6193, 6609, 6196, 6199, 6610, 6611, 6206, 6612, 6208, 6569, 5588,
6214, 6215, 5590, 6216, 5795, 6613, 6614, 6570, 6571, 6223, 6346, 5591, 6233, 6232, 6234, 5690,
6235, 6236, 6237, 6239, 6615, 6240, 6244, 6245, 6241, 6246, 6251, 6243, 6248, 6249, 6250, 6616,
6618, 6617, 5592, 6257, 6258, 6260, 6622, 6261, 6619, 5593, 5594, 6620, 6621, 5595, 6269, 6271,
6272, 6275, 6274, 6277, 6276, 6278, 6279, 6281, 7403, 6283, 6284, 5596, 6288, 6289, 6623, 6292,
6293, 5597, 6296, 5548, 6624, 6625, 5598, 5599, 6304, 6319, 6626, 6322, 6323, 6328, 6331, 6627,
6548, 6334, 6333, 6336, 6549, 6339, 6628, 6629, 6356, 6358, 6360, 6630, 6361, 6369, 6371, 6372,
6370, 6375, 6376, 6631, 6379, 5600, 6381, 6632, 5601, 6393, 5828, 6399, 6633, 6635, 5602, 5603,
6408, 6636, 5604, 6637, 6416, 6638, 6422, 5605, 6426, 6429, 6431, 6433, 5606, 6639, 6445, 6448,
5607, 5608, 6449, 6640, 5609, 6641, 6642, 6643, 6458, 5610, 6463, 6465, 6466, 6468, 6470, 6472,
]
_lookup_composition_canon_decomp_middle = _all_ushort(_lookup_composition_canon_decomp_middle)
def lookup_composition_canon_decomp_middle(index): return intmask(_lookup_composition_canon_decomp_middle[index])

def lookup_composition_combining(index):
    if 364 <= index <= 4145:
        return lookup_composition_combining_middle(index - 364)
    if index < 364:
        return 0
    if index < 4821:
        return 0
    raise KeyError

_lookup_composition_combining_middle = (
'\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe6\xe8\xdc\xd8'
'\xca\xdc\xdc\xdc\xdc\xca\xca\xdc\xdc\xdc\xdc\x01\x01\xe6\xe6\xe6\xe6\xe6\xf0\xe9'
'\xea\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\xde\xe4\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1e\x1f'
' \x00\x00\x00\x00\x00\x00\x00\x00\x1b\x1c\x1d!"\xe6\xe6\xdc#\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00$\x00\x00\x00\x00\x00\x00\x07\t\x00\x00\x00'
'\x00\x00\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'T[\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t'
'\x00\x00\x00\x00\x00\x00\x00\x00gk\x00vz\x00\x00\x00\xd8\x00\x00\x00'
'\x00\x00\x00\x81\x82\x00\x84\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\xd6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\xda\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x08\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00'
'\x00\xe2'
)
def lookup_composition_combining_middle(index): return ord(_lookup_composition_combining_middle[index])

def lookup_composition_left_index(index):
    if 1 <= index <= 4135:
        return lookup_composition_left_index_middle(index - 1)
    if index < 1:
        return -1
    if index < 4821:
        return -1
    raise KeyError

# estimated 8.09 KiB
_lookup_composition_left_index_middle = [
293, 290, 294, 0, 144, 1, 16, 2, 152, 18, 20, 3, 22, 24, 26, 158,
4, 5, 162, 28, 30, 32, 6, 176, 34, 178, 7, 36, 8, 145, 9, 17,
10, 153, 19, 21, 11, 23, 25, 27, 159, 12, 13, 163, 29, 31, 33, 14,
177, 35, 179, 15, 37, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, 181, -1, 40, 50, 44, 146, -1, -1, 187, -1, -1,
-1, -1, 154, -1, -1, -1, 191, 56, 54, 52, -1, -1, -1, 38, -1, -1,
-1, 182, -1, 41, 51, 45, 147, -1, -1, 188, -1, -1, -1, -1, 155, -1,
-1, -1, 192, 57, 55, 53, -1, -1, -1, 39, -1, -1, -1, -1, 185, 186,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, 149, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 160, 161,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, 167, -1, -1, -1, -1,
168, 169, -1, -1, -1, -1, 172, 173, 174, 175, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 180, 195, 196,
197, 198, 48, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, 46, 47, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, 42, 43, 150, 151, -1, -1, -1, -1,
58, 59, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, 61, 62, 63, 64, 65, 271, 66, 67, -1, -1, 263, -1, 266, -1, -1,
69, 70, 71, 72, 75, 270, 74, 76, 68, 73, -1, -1, 273, -1, -1, 77,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1,
-1, -1, 94, 79, 78, 92, 98, 82, -1, 81, 100, 83, 106, 108, 104, 95,
86, 85, 93, 99, 84, -1, 88, 101, 89, 107, 109, 105, -1, -1, -1, 87,
-1, -1, -1, -1, 90, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
96, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, 103,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, 110, 111, 112, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 114, -1, 115, -1, 113, -1,
116, -1, 117, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
120, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, 122, 123, -1, -1, -1,
-1, 124, -1, -1, -1, 125, -1, -1, 126, -1, -1, 127, -1, -1, -1, -1,
128, 129, -1, -1, -1, -1, -1, -1, 130, -1, 131, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1,
-1, -1, 133, -1, 134, -1, 135, -1, 136, -1, 137, -1, 138, -1, -1, 139,
-1, 140, -1, 141, 142, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 156,
157, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, 164, 165, -1, -1, -1, -1, -1, -1, 170, 171, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, 183, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 189, 190, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, 193, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199,
200, 226, 227, 228, 229, 230, 231, 201, 202, 232, 233, 234, 235, 236, 237, 203,
204, -1, -1, -1, -1, 205, 206, -1, -1, -1, -1, 207, 208, 238, 239, 240,
241, 242, 243, 209, 210, 244, 245, 246, 247, 248, 249, 211, 212, -1, -1, -1,
-1, -1, -1, 213, 214, -1, -1, -1, -1, -1, -1, 215, 216, -1, -1, -1,
-1, 217, 218, -1, -1, -1, -1, 219, 220, -1, -1, -1, -1, -1, -1, 221,
-1, -1, -1, 222, 223, 250, 251, 252, 253, 254, 255, 224, 225, 256, 257, 258,
259, 260, 261, 262, -1, -1, -1, 265, -1, -1, -1, -1, -1, -1, -1, 272,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, 268,
-1, -1, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274,
-1, -1, -1, -1, -1, -1, -1, 269, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, 276, 277,
-1, -1, -1, -1, -1, -1, 278, 280, 279, 281, -1, 282, -1, 283, -1, 284,
-1, 285, -1, -1, -1, -1, -1, 286, -1, 287, -1, 288, -1, 289, -1, 292,
-1, 291, -1, 295, 296, -1, -1, -1, -1, -1, 297, 298, -1, -1, 299, 300,
-1, -1, 301, 302, 311, 312, -1, -1, 303, 304, -1, -1, 305, 306, -1, -1,
313, 314, 307, 308, 309, 310, -1, -1, -1, -1, 315, 316, 317, 318, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, 339, 319, -1, 320, -1, 321, -1,
322, -1, 323, -1, 324, -1, 325, -1, 326, -1, 327, -1, 328, -1, 329, -1,
330, -1, 331, -1, 332, -1, 333, -1, 334, -1, -1, 335, -1, -1, 336, -1,
-1, 337, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, 361,
341, -1, 342, -1, 343, -1, 344, -1, 345, -1, 346, -1, 347, -1, 348, -1,
349, -1, 350, -1, 351, -1, 352, -1, 353, -1, 354, -1, 355, -1, 356, -1,
-1, 357, -1, -1, 358, -1, -1, 359, -1, -1, 360, -1, -1, 362, 363, 364,
365, -1, -1, -1, -1, -1, 366, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
-1, -1, 367, -1, 368, -1, 369,
]
_lookup_composition_left_index_middle = _all_short(_lookup_composition_left_index_middle)
def lookup_composition_left_index_middle(index): return intmask(_lookup_composition_left_index_middle[index])

def lookup_composition_right_index(index):
    if 364 <= index <= 4137:
        return lookup_composition_right_index_middle(index - 364)
    if index < 364:
        return -1
    if index < 4821:
        return -1
    raise KeyError

_lookup_composition_right_index_middle = (
'\x00\x01\x02\x03\x07\xff\x08\n\x04.\x05\x0c\x0b\x0e\x0f/0\xff\xff\r'
"\xff(-'\x10\x06\t*,+)\xff3\xff\xff1\xff\xff2\xff"
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x11\x12\x13\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x14\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\x15\xff\xff\xff\x16\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\x18\xff\xff\xff\xff\x17\x19\xff\xff\xff\xff\x1b\xff\xff\xff\xff\xff\x1a\xff\xff'
'\xff\x1c\xff\xff\x1f\xff\xff\xff\xff\xff\x1d\x1e \xff\xff\xff\xff\xff!"'
'#\xff\xff\xff\xff\xff$\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff%\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff&\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff45\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff6'
)
def lookup_composition_right_index_middle(index): return signed_ord(_lookup_composition_right_index_middle[index])

def _composition_pgtbl(index):
    if 1 <= index <= 1524:
        return _composition_pgtbl_middle(index - 1)
    if index < 1:
        return 0
    if index < 8704:
        return 10
    raise KeyError

__composition_pgtbl_middle = (
'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\n\x11\x12\x13'
'\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f \n\n\n\n!\n\n'
'\n\n\n\n\n"#\n$%\n&\n\'()*+,-'
'./01234567\n89\n\n\n\n\n\n\n'
'\n\n\n:;\n\n<=>?\n@ABCDEFG'
'HIJ\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\nKLM\nNOPQ\n'
'R\nS\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nTUV'
'WXYZ[\\]^_`a\n\n\nb\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\nc\n\n\n\n\n\n\n\n'
'\n\n\n\nd\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\nefg\n\n\nhijkl'
'mno\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\npqr\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
'\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\ns'
'tuvw'
)
def _composition_pgtbl_middle(index): return ord(__composition_pgtbl_middle[index])

def _composition_pages(index):
    if 60 <= index <= 15261:
        return _composition_pages_middle(index - 60)
    if index < 60:
        return 0
    if index < 15360:
        return 0
    raise KeyError

# estimated 29.71 KiB
__composition_pages_middle = [
1, 2, 3, 0, 0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
15, 16, 17, 18, 19, 0, 20, 21, 22, 23, 24, 25, 26, 27, 28, 0,
0, 0, 0, 0, 0, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
40, 41, 42, 43, 44, 0, 45, 46, 47, 48, 49, 50, 51, 52, 53, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 54, 0, 0, 0, 0, 0, 0, 0, 55, 0, 56, 0,
0, 0, 0, 57, 0, 0, 58, 59, 60, 61, 0, 0, 62, 63, 64, 0,
65, 66, 67, 0, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
80, 81, 82, 83, 0, 84, 85, 86, 87, 88, 89, 0, 90, 91, 92, 93,
94, 95, 0, 0, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107,
108, 109, 110, 111, 0, 112, 113, 114, 115, 116, 117, 0, 118, 119, 120, 121,
122, 123, 0, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136,
137, 138, 139, 140, 0, 0, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150,
151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 0, 0, 161, 162, 163, 164,
165, 166, 167, 168, 169, 0, 170, 171, 172, 173, 174, 175, 0, 176, 177, 178,
179, 180, 181, 182, 183, 0, 0, 184, 185, 186, 187, 188, 189, 190, 0, 0,
191, 192, 193, 194, 195, 196, 0, 0, 197, 198, 199, 200, 201, 202, 203, 204,
205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 0, 0, 215, 216, 217, 218,
219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234,
235, 236, 237, 238, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 239, 240, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 241, 242, 0, 0, 0, 0, 0, 0, 243, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 244, 245, 246, 247, 248, 249, 250, 251,
252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267,
268, 0, 269, 270, 271, 272, 273, 274, 0, 0, 275, 276, 277, 278, 279, 280,
281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 0, 0, 291, 292, 293, 294,
295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310,
311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326,
0, 0, 327, 328, 0, 0, 0, 0, 0, 0, 329, 330, 331, 332, 333, 334,
335, 336, 337, 338, 339, 340, 341, 342, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 343, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 344, 345, 346, 347, 348, 349, 350, 351, 352, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 353, 354, 355, 356,
357, 358, 0, 0, 359, 360, 361, 362, 363, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375,
376, 369, 369, 377, 369, 378, 369, 379, 380, 381, 382, 382, 382, 382, 381, 383,
382, 382, 382, 382, 382, 384, 384, 385, 386, 387, 388, 389, 390, 382, 382, 382,
382, 391, 392, 382, 393, 394, 382, 382, 395, 395, 395, 395, 396, 382, 382, 382,
382, 369, 369, 369, 397, 398, 399, 400, 401, 402, 369, 382, 382, 382, 369, 369,
369, 382, 382, 0, 369, 369, 369, 382, 382, 382, 382, 369, 381, 382, 382, 369,
403, 404, 404, 403, 404, 404, 403, 369, 369, 369, 369, 369, 369, 369, 369, 369,
369, 369, 369, 369, 0, 0, 0, 0, 405, 0, 0, 0, 0, 0, 406, 0,
0, 0, 407, 0, 0, 0, 0, 0, 60, 408, 409, 410, 411, 412, 413, 0,
414, 0, 415, 416, 417, 418, 0, 0, 0, 419, 0, 420, 0, 421, 0, 0,
0, 0, 0, 422, 0, 423, 0, 0, 0, 424, 0, 0, 0, 425, 426, 427,
428, 429, 430, 431, 432, 433, 0, 0, 0, 434, 0, 435, 0, 436, 0, 0,
0, 0, 0, 437, 0, 438, 0, 0, 0, 439, 0, 0, 0, 440, 441, 442,
443, 444, 445, 0, 446, 447, 448, 449, 450, 451, 452, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 453, 454, 455, 0, 456, 457, 0, 0, 0, 458, 0, 0,
0, 0, 0, 0, 459, 460, 0, 461, 0, 0, 462, 463, 0, 0, 0, 0,
464, 465, 466, 0, 467, 0, 0, 468, 0, 469, 470, 471, 472, 473, 474, 0,
0, 0, 475, 0, 0, 0, 0, 476, 0, 0, 0, 477, 0, 0, 0, 478,
0, 479, 0, 0, 480, 0, 0, 481, 0, 482, 483, 484, 485, 486, 487, 0,
0, 0, 488, 0, 0, 0, 0, 489, 0, 0, 0, 490, 0, 0, 0, 491,
0, 492, 0, 0, 493, 494, 0, 495, 0, 0, 496, 497, 0, 0, 0, 0,
498, 499, 500, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 501, 502, 503, 504, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 369, 369, 369, 369, 369, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 505, 506, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 507, 508, 509, 510, 0, 0, 511, 512, 513, 514, 515, 516,
517, 518, 519, 520, 0, 0, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530,
531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 0, 0, 541, 542, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 543, 0, 0, 0, 0,
0, 0, 0, 0, 0, 382, 369, 369, 369, 369, 382, 369, 369, 369, 544, 382,
369, 369, 369, 369, 369, 369, 382, 382, 382, 382, 382, 382, 369, 369, 382, 369,
369, 544, 545, 369, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 555, 556,
557, 558, 0, 559, 0, 560, 561, 0, 369, 382, 0, 554, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 369, 369, 369, 369, 369, 369, 369, 562, 563, 564, 0,
0, 0, 0, 0, 0, 0, 565, 566, 567, 568, 569, 570, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 571, 0, 572, 573,
574, 575, 562, 563, 564, 576, 577, 578, 579, 580, 382, 369, 369, 369, 369, 369,
382, 369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 581, 0, 0, 0, 0, 582, 583, 584, 585, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 586, 587, 588, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 589, 590, 0, 591, 369, 369, 369, 369, 369, 369,
369, 0, 0, 369, 369, 369, 369, 382, 369, 0, 0, 369, 369, 0, 382, 369,
369, 382, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 592, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 382, 369, 369, 382, 369, 369, 382, 382, 382, 369, 382,
382, 369, 382, 369, 369, 369, 382, 369, 382, 369, 382, 369, 382, 369, 369, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 369,
369, 369, 369, 369, 369, 369, 382, 369, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 369, 369, 369, 369, 0, 369,
369, 369, 369, 369, 369, 369, 369, 369, 0, 369, 369, 369, 0, 369, 369, 369,
369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 593, 594, 0, 0,
0, 0, 0, 0, 595, 596, 0, 597, 598, 0, 0, 0, 0, 0, 0, 0,
599, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 600, 0, 0, 0, 369, 382, 369, 369, 0, 0, 0, 601, 602, 603, 604,
605, 606, 607, 608, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
609, 0, 610, 0, 0, 0, 0, 0, 0, 0, 0, 611, 0, 0, 0, 612,
613, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 614, 0, 0, 0, 0,
615, 616, 0, 617, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 618, 0, 0, 619, 0, 0, 0, 0, 0,
609, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 620, 621, 622,
0, 0, 623, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
609, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
609, 0, 624, 0, 0, 0, 0, 0, 0, 0, 0, 625, 626, 0, 0, 627,
628, 600, 0, 0, 0, 0, 0, 0, 0, 0, 629, 630, 0, 0, 0, 0,
631, 632, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 633, 0, 634, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 635, 0, 0, 0, 0, 0, 0, 0, 636, 637, 0, 0, 638, 639,
640, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 641, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 642, 0, 643, 0, 0, 0,
0, 600, 0, 0, 0, 0, 0, 0, 0, 644, 645, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
609, 0, 0, 646, 647, 0, 648, 0, 0, 0, 649, 650, 651, 0, 652, 653,
0, 600, 0, 0, 0, 0, 0, 0, 0, 654, 655, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 656, 0, 0, 0, 0, 0, 0, 0, 657, 658, 0, 0, 659, 660,
661, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 662, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 663, 0,
0, 0, 0, 664, 0, 0, 0, 0, 0, 0, 0, 0, 0, 665, 666, 0,
667, 668, 669, 670, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 671, 0, 0, 0, 0, 672, 672, 600, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 673, 673, 673, 673,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 674, 0, 0, 0, 0, 675, 675, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 676, 676, 676, 676,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
677, 678, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
679, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 382, 382, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 382, 0, 382, 0, 680, 0, 0,
0, 0, 0, 0, 0, 0, 0, 681, 0, 0, 0, 0, 0, 0, 0, 0,
0, 682, 0, 0, 0, 0, 683, 0, 0, 0, 0, 684, 0, 0, 0, 0,
685, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 686, 0, 0,
0, 0, 0, 0, 0, 687, 688, 689, 690, 691, 692, 693, 694, 695, 688, 688,
688, 688, 0, 0, 688, 696, 369, 369, 600, 0, 369, 369, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 697, 0, 0, 0, 0, 0, 0, 0, 0,
0, 698, 0, 0, 0, 0, 699, 0, 0, 0, 0, 700, 0, 0, 0, 0,
701, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 702, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 382, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 703, 704, 0, 0, 0, 0, 0,
0, 0, 705, 0, 0, 0, 0, 0, 0, 0, 0, 609, 0, 600, 600, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 382, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
706, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 545, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 544, 369, 382,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 369, 382, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 369, 369, 369, 369, 369, 369, 369,
369, 0, 0, 382, 0, 0, 0, 0, 0, 707, 708, 709, 710, 711, 712, 713,
714, 715, 716, 0, 0, 717, 718, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 609, 719, 0, 0, 0, 0, 720, 721,
722, 723, 724, 725, 726, 727, 728, 729, 600, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 369,
382, 369, 369, 369, 369, 369, 369, 369, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 600, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 609, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 369, 369, 0, 395, 382, 382, 382, 382, 382, 369, 369,
382, 382, 382, 382, 369, 0, 395, 395, 395, 395, 395, 395, 395, 0, 0, 0,
0, 382, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
730, 731, 732, 0, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 0,
744, 745, 746, 747, 748, 749, 750, 56, 751, 752, 753, 754, 755, 756, 757, 758,
759, 760, 0, 761, 762, 763, 64, 764, 765, 766, 767, 768, 769, 770, 771, 772,
773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 788, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 789,
790, 791, 792, 759, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804,
805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820,
821, 822, 823, 824, 369, 369, 382, 369, 369, 369, 369, 369, 369, 369, 382, 369,
369, 404, 825, 382, 384, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369,
369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 382, 369, 382, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837,
838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853,
854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869,
870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885,
886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901,
902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917,
918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933,
934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949,
950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965,
966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981,
0, 0, 0, 0, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993,
994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009,
1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025,
1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1041,
1042, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057,
1058, 1059, 1060, 1061, 1062, 1063, 1064, 1065, 1066, 1067, 1068, 1069, 1070, 1071, 0, 0,
0, 0, 0, 0, 1072, 1073, 1074, 1075, 1076, 1077, 1078, 1079, 1080, 1081, 1082, 1083,
1084, 1085, 1086, 1087, 1088, 1089, 1090, 1091, 1092, 1093, 0, 0, 1094, 1095, 1096, 1097,
1098, 1099, 0, 0, 1100, 1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110, 1111,
1112, 1113, 1114, 1115, 1116, 1117, 1118, 1119, 1120, 1121, 1122, 1123, 1124, 1125, 1126, 1127,
1128, 1129, 1130, 1131, 1132, 1133, 1134, 1135, 1136, 1137, 0, 0, 1138, 1139, 1140, 1141,
1142, 1143, 0, 0, 1144, 1145, 1146, 1147, 1148, 1149, 1150, 1151, 0, 1152, 0, 1153,
0, 1154, 0, 1155, 1156, 1157, 1158, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1166, 1167,
1168, 1169, 1170, 1171, 1172, 1173, 1174, 1175, 1176, 1177, 1178, 1179, 1180, 1181, 1182, 1183,
1184, 1185, 0, 0, 1186, 1187, 1188, 1189, 1190, 1191, 1192, 1193, 1194, 1195, 1196, 1197,
1198, 1199, 1200, 1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213,
1214, 1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, 1224, 1225, 1226, 1227, 1228, 1229,
1230, 1231, 1232, 1233, 1234, 1235, 1236, 1237, 1238, 0, 1239, 1240, 1241, 1242, 1243, 1244,
1245, 1246, 1247, 1248, 1249, 1250, 1251, 1252, 1253, 0, 1254, 1255, 1256, 1257, 1258, 1259,
1260, 1261, 1262, 1263, 1264, 1265, 1266, 1267, 0, 0, 1268, 1269, 1270, 1271, 1272, 1273,
0, 1274, 1275, 1276, 1277, 1278, 1279, 1280, 1281, 1282, 1283, 1284, 1285, 1286, 1287, 1288,
1289, 1290, 1291, 1292, 0, 0, 1293, 1294, 1295, 0, 1296, 1297, 1298, 1299, 1300, 1301,
1302, 1303, 1304, 0, 1305, 1306, 1307, 1307, 1307, 1307, 1307, 54, 1307, 1307, 1307, 0,
0, 0, 0, 0, 0, 1308, 0, 0, 0, 0, 0, 1309, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 1310, 1311, 1312, 0, 0, 0, 0, 0,
0, 0, 0, 54, 0, 0, 0, 1313, 1314, 0, 1315, 1316, 0, 0, 0, 0,
1317, 0, 1318, 0, 0, 0, 0, 0, 0, 0, 0, 1319, 1320, 1321, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1322, 0, 0, 0, 0,
0, 0, 0, 1307, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1323, 1324, 0, 0, 1325, 1326, 1327, 1328, 1329, 1330, 1331, 1332,
1333, 1334, 1335, 1336, 1337, 1338, 1339, 1340, 1341, 1342, 1343, 1344, 1345, 1346, 1347, 1348,
1349, 1350, 1351, 0, 1352, 1353, 1354, 1355, 1356, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1357, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 369, 395, 395, 369, 369, 369, 369, 395, 395, 395, 369,
369, 0, 0, 0, 0, 369, 0, 0, 0, 395, 395, 369, 382, 369, 395, 395,
382, 382, 382, 382, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1358, 1359, 1360, 1361, 0, 1362, 1363, 1364, 0, 1365, 1366, 1367,
1367, 1367, 1368, 1369, 1370, 1370, 1371, 1372, 0, 1373, 1374, 0, 0, 1375, 1376, 1377,
1377, 1377, 0, 0, 1378, 1379, 1380, 0, 1381, 0, 1382, 0, 1381, 0, 1383, 1384,
1385, 1360, 0, 1386, 1387, 1388, 0, 1389, 1390, 1391, 1392, 1393, 1394, 1395, 0, 1396,
1397, 1398, 1399, 1400, 1401, 0, 0, 0, 0, 1402, 1403, 1386, 1395, 1404, 0, 0,
0, 0, 0, 0, 1405, 1406, 1407, 1408, 1409, 1410, 1411, 1412, 1413, 1414, 1415, 1416,
1417, 1418, 1419, 1420, 1421, 1422, 1423, 1424, 1425, 1426, 1427, 1428, 1429, 1430, 1431, 1432,
1433, 1434, 1435, 1436, 1437, 1438, 1439, 1440, 1441, 1442, 1443, 1444, 1445, 1446, 1447, 1448,
1449, 1450, 1451, 1452, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1453, 0, 0,
0, 0, 0, 0, 1454, 0, 1455, 0, 1456, 0, 0, 0, 0, 0, 1457, 1458,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 1459, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 1460, 1461, 1462, 1463, 0, 1464, 0, 1465, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 1466, 1467, 0, 0, 0, 1468, 1469, 0, 1470,
1471, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 1472, 1473, 1474, 1475, 0, 0, 0, 0, 0,
1476, 1477, 0, 1478, 1479, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
1480, 0, 0, 0, 0, 1481, 0, 1482, 1483, 1484, 0, 1485, 1486, 1487, 0, 0,
0, 1488, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1489, 1490, 1491, 0, 1492, 1493, 0, 0, 0, 0, 0, 0,
0, 1494, 1495, 1496, 1497, 1498, 1499, 1500, 1501, 1502, 1503, 1504, 1505, 1506, 1507, 1508,
1509, 1510, 0, 0, 1511, 1512, 1513, 1514, 1515, 1516, 1517, 1518, 1519, 1520, 0, 0,
0, 0, 0, 0, 0, 1521, 1522, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 1523, 0, 0, 0, 0, 0, 1524, 1525, 0, 1526,
1527, 1528, 1529, 1530, 0, 0, 1531, 1532, 1533, 1534, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1535, 1536, 1537, 1538, 0, 0, 0, 0, 0, 0, 1539, 1540,
1541, 1542, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1543, 1544, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556,
1557, 1558, 1559, 1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572,
1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588,
1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604,
1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620,
1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636,
1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652,
1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668,
1669, 1670, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679, 1680, 1681, 1682, 1683, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
1684, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 1685, 1686, 1687, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
1688, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
1689, 1690, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 369, 369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 1691, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369,
369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369,
369, 369, 369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 1692, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 1693, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1694, 1695, 1696, 1697, 1698, 1699, 1700, 1701, 1702, 1703, 1704, 1705,
1706, 1707, 1708, 1709, 1710, 1711, 1712, 1713, 1714, 1715, 1716, 1717, 1718, 1719, 1720, 1721,
1722, 1723, 1724, 1725, 1726, 1727, 1728, 1729, 1730, 1731, 1732, 1733, 1734, 1735, 1736, 1737,
1738, 1739, 1740, 1741, 1742, 1743, 1744, 1745, 1746, 1747, 1748, 1749, 1750, 1751, 1752, 1753,
1754, 1755, 1756, 1757, 1758, 1759, 1760, 1761, 1762, 1763, 1764, 1765, 1766, 1767, 1768, 1769,
1770, 1771, 1772, 1773, 1774, 1775, 1776, 1777, 1778, 1779, 1780, 1781, 1782, 1783, 1784, 1785,
1786, 1787, 1788, 1789, 1790, 1791, 1792, 1793, 1794, 1795, 1796, 1797, 1798, 1799, 1800, 1801,
1802, 1803, 1804, 1805, 1806, 1807, 1808, 1809, 1810, 1811, 1812, 1813, 1814, 1815, 1816, 1817,
1818, 1819, 1820, 1821, 1822, 1823, 1824, 1825, 1826, 1827, 1828, 1829, 1830, 1831, 1832, 1833,
1834, 1835, 1836, 1837, 1838, 1839, 1840, 1841, 1842, 1843, 1844, 1845, 1846, 1847, 1848, 1849,
1850, 1851, 1852, 1853, 1854, 1855, 1856, 1857, 1858, 1859, 1860, 1861, 1862, 1863, 1864, 1865,
1866, 1867, 1868, 1869, 1870, 1871, 1872, 1873, 1874, 1875, 1876, 1877, 1878, 1879, 1880, 1881,
1882, 1883, 1884, 1885, 1886, 1887, 1888, 1889, 1890, 1891, 1892, 1893, 1894, 1895, 1896, 1897,
1898, 1899, 1900, 1901, 1902, 1903, 1904, 1905, 1906, 1907, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 1908, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1909, 545,
381, 544, 1910, 1910, 0, 0, 0, 0, 0, 0, 1911, 0, 1717, 1912, 1913, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1914, 0, 0, 0, 0, 1915,
1916, 1917, 1918, 1919, 1920, 1921, 1922, 1923, 1924, 1925, 1926, 1927, 1928, 1929, 1930, 1931,
1932, 1933, 1934, 1935, 1936, 1937, 1938, 0, 1939, 1940, 1941, 1942, 1943, 1944, 0, 0,
0, 0, 0, 1945, 1946, 1947, 1948, 1949, 1950, 1951, 1952, 1953, 1954, 1955, 1956, 1957,
1958, 1959, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 1960, 0, 0, 0, 0, 1961, 1962, 1963,
1964, 1965, 1966, 1967, 0, 0, 0, 0, 0, 0, 1968, 0, 0, 0, 0, 1969,
1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985,
1986, 1987, 1988, 1989, 1990, 1991, 1992, 0, 1993, 1994, 1995, 1996, 1997, 1998, 0, 0,
0, 0, 0, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011,
2012, 2013, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 2014, 2015, 2016, 2017, 0, 2018, 0, 0, 2019, 2020, 2021, 2022, 0,
0, 2023, 2024, 2025, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036,
2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2051, 2052,
2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060, 2061, 2062, 2063, 2064, 2065, 2066, 2067, 2068,
2069, 2070, 2071, 2072, 2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084,
2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100,
2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116,
2117, 2118, 2119, 0, 0, 0, 2120, 2121, 2122, 2123, 2124, 2125, 2126, 2127, 2128, 2129,
2130, 2131, 2132, 2133, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145,
2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161,
2162, 2163, 2164, 0, 2165, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176,
2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192,
2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 0, 0, 0, 0,
0, 0, 0, 0, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216,
2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232,
2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2244, 2245, 2246, 2247, 2248,
2249, 2250, 2251, 0, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263,
2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279,
2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295,
2296, 2297, 2298, 2299, 2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311,
2312, 2313, 2314, 2315, 2316, 2317, 2318, 2319, 2320, 2321, 2322, 2323, 2324, 2325, 2326, 2327,
2328, 2329, 2330, 2331, 2332, 2333, 2334, 2335, 2336, 2337, 2338, 2339, 2340, 2341, 2342, 2343,
2344, 2345, 2346, 2347, 2348, 2349, 2350, 2351, 2352, 2353, 2354, 2355, 2356, 2357, 2358, 2359,
2360, 2361, 2362, 2363, 2364, 2365, 2366, 2367, 2368, 2369, 2370, 2371, 2372, 2373, 2374, 2375,
2376, 2377, 2378, 0, 2379, 2380, 2381, 2382, 2383, 2384, 2385, 2386, 2387, 2388, 2389, 2390,
2391, 2392, 2393, 2394, 2395, 2396, 2397, 2398, 2399, 2400, 2401, 2402, 2403, 2404, 2405, 2406,
2407, 2408, 2409, 2410, 2411, 2412, 2413, 2414, 2415, 2416, 2417, 2418, 2419, 2420, 2421, 2422,
2423, 2424, 2425, 2426, 2427, 2428, 2429, 2430, 2431, 2432, 2433, 2434, 2435, 2436, 2437, 2438,
2439, 2440, 2441, 2442, 2443, 2444, 2445, 2446, 2447, 2448, 2449, 2450, 2451, 2452, 2453, 2454,
2455, 2456, 2457, 2458, 2459, 2460, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470,
2471, 2472, 2473, 2474, 2475, 2476, 2477, 2478, 2479, 2480, 2481, 2482, 2483, 2484, 2485, 2486,
2487, 2488, 2489, 2490, 2491, 2492, 2493, 2494, 2495, 2496, 2497, 2498, 2499, 2500, 2501, 2502,
2503, 2504, 2505, 2506, 2507, 2508, 2509, 2510, 2511, 2512, 2513, 2514, 2515, 2516, 2517, 2518,
2519, 2520, 2521, 2522, 2523, 2524, 2525, 2526, 2527, 2528, 2529, 2530, 2531, 2532, 2533, 2534,
2535, 2536, 2537, 2538, 2539, 2540, 2541, 2542, 2543, 2544, 2545, 2546, 2547, 2548, 2549, 2550,
2551, 2552, 2553, 2554, 2555, 2556, 2557, 2558, 2559, 2560, 2561, 2562, 2563, 2564, 2565, 2566,
2567, 2568, 2569, 2570, 2571, 2572, 2573, 2574, 2575, 2576, 2577, 2578, 2579, 2580, 2581, 2582,
2583, 2584, 2585, 2586, 2587, 2588, 2589, 2590, 2591, 2592, 2593, 2594, 2595, 2596, 2597, 2598,
2599, 2600, 2601, 2602, 2603, 2604, 2605, 2606, 2607, 2608, 2609, 2610, 2611, 2612, 2613, 2614,
2615, 2616, 2617, 2618, 2619, 2620, 2621, 2622, 2623, 2624, 2625, 2626, 2627, 2628, 2629, 2630,
2631, 2632, 2633, 2634, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 2635, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 600, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369, 369,
369, 369, 369, 369, 369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 382,
382, 382, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 609, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 369, 0, 369, 369, 382, 0, 0, 369, 369, 0, 0, 0,
0, 0, 369, 369, 0, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 2636, 2637, 2638, 2639, 2640, 2641, 2642, 2643, 2643, 2644, 2645, 2646,
2647, 2648, 2649, 2650, 2651, 2652, 2653, 2654, 2655, 2656, 2657, 2658, 2659, 2660, 2661, 2662,
2663, 2664, 2665, 2666, 2667, 2668, 2669, 2670, 2671, 2672, 2673, 2674, 2675, 2676, 2677, 2678,
2679, 2680, 2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694,
2695, 2696, 2697, 2698, 2699, 2700, 2701, 2702, 2703, 2704, 2705, 2706, 2707, 2708, 2709, 2710,
2711, 2712, 2713, 2714, 2715, 2716, 2717, 2718, 2719, 2720, 2721, 2722, 2723, 2724, 2725, 2726,
2655, 2727, 2728, 2729, 2730, 2731, 2732, 2733, 2734, 2735, 2736, 2737, 2738, 2739, 2740, 2741,
2742, 2743, 2744, 2745, 2746, 2747, 2748, 2749, 2750, 2751, 2752, 2753, 2754, 2755, 2756, 2757,
2758, 2759, 2760, 2761, 2762, 2763, 2764, 2765, 2766, 2767, 2768, 2769, 2770, 2771, 2772, 2773,
2774, 2775, 2776, 2777, 2778, 2779, 2780, 2781, 2782, 2783, 2784, 2785, 2786, 2787, 2788, 2789,
2790, 2791, 2792, 2793, 2794, 2745, 2795, 2796, 2797, 2798, 2799, 2800, 2801, 2802, 2729, 2803,
2804, 2805, 2806, 2807, 2808, 2809, 2810, 2811, 2812, 2813, 2814, 2815, 2816, 2817, 2818, 2819,
2820, 2821, 2822, 2655, 2823, 2824, 2825, 2826, 2827, 2828, 2829, 2830, 2831, 2832, 2833, 2834,
2835, 2836, 2837, 2838, 2839, 2840, 2841, 2842, 2843, 2844, 2845, 2846, 2847, 2848, 2849, 2731,
2850, 2851, 2852, 2853, 2854, 2855, 2856, 2857, 2858, 2859, 2860, 2861, 2862, 2863, 2864, 2865,
2866, 2867, 2868, 2869, 2870, 2871, 2872, 2873, 2874, 2875, 2876, 2877, 2878, 2879, 2880, 2881,
2882, 2883, 2884, 2885, 2886, 2887, 2888, 2889, 2890, 2891, 2892, 2893, 2894, 2895, 2896, 2897,
2898, 2899, 0, 0, 2900, 0, 2901, 0, 0, 2902, 2903, 2904, 2905, 2906, 2907, 2908,
2909, 2910, 2911, 0, 2912, 0, 2913, 0, 0, 2914, 2915, 0, 0, 0, 2916, 2917,
2918, 2919, 0, 0, 2920, 2921, 2922, 2923, 2924, 2925, 2926, 2927, 2928, 2929, 2930, 2931,
2932, 2933, 2934, 2935, 2936, 2937, 2938, 2939, 2940, 2941, 2942, 2943, 2944, 2945, 2946, 2947,
2948, 2949, 2950, 2951, 2952, 2953, 2954, 2955, 2956, 2957, 2958, 2784, 2959, 2960, 2961, 2962,
2963, 2964, 2964, 2965, 2966, 2967, 2968, 2969, 2970, 2971, 2972, 2914, 2973, 2974, 2975, 2976,
2977, 2978, 0, 0, 2979, 2980, 2981, 2982, 2983, 2984, 2985, 2986, 2926, 2987, 2988, 2989,
2900, 2990, 2991, 2992, 2993, 2994, 2995, 2996, 2997, 2998, 2999, 3000, 3001, 2935, 3002, 2936,
3003, 3004, 3005, 3006, 3007, 2901, 2676, 3008, 3009, 3010, 2746, 2833, 3011, 3012, 2943, 3013,
2944, 3014, 3015, 3016, 2903, 3017, 3018, 3019, 3020, 3021, 2904, 3022, 3023, 3024, 3025, 3026,
3027, 2958, 3028, 3029, 2784, 3030, 2962, 3031, 3032, 3033, 3034, 3035, 2967, 3036, 2913, 3037,
2968, 2727, 3038, 2969, 3039, 2971, 3040, 3041, 3042, 3043, 3044, 2973, 2909, 3045, 2974, 3046,
2975, 3047, 2643, 3048, 3049, 3050, 3051, 3052, 3053, 3054, 3055, 3056, 3057, 3058, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 3059, 3060, 3061, 3062, 3063, 3064, 3065, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 3066, 3067, 3068, 3069, 3070, 0, 0, 0, 0,
0, 3071, 3072, 3073, 3074, 3075, 3076, 3077, 3078, 3079, 3080, 3081, 3082, 3083, 3084, 3085,
3086, 3087, 3088, 3089, 3090, 3091, 3092, 3093, 3094, 3095, 3096, 0, 3097, 3098, 3099, 3100,
3101, 0, 3102, 0, 3103, 3104, 0, 3105, 3106, 0, 3107, 3108, 3109, 3110, 3111, 3112,
3113, 3114, 3115, 3116, 3117, 3118, 3119, 3120, 3121, 3122, 3123, 3124, 3125, 3126, 3127, 3128,
3129, 3130, 3131, 3132, 3133, 3134, 3135, 3136, 3137, 3138, 3139, 3140, 3141, 3142, 3143, 3144,
3145, 3146, 3147, 3148, 3149, 3150, 3151, 3152, 3153, 3154, 3155, 3156, 3157, 3158, 3159, 3160,
3161, 3162, 3163, 3164, 3165, 3166, 3167, 3168, 3169, 3170, 3171, 3172, 3173, 3174, 3175, 3176,
3177, 3178, 3179, 3180, 3181, 3182, 3183, 3184, 3185, 3186, 3187, 3188, 3189, 3190, 3191, 3192,
3193, 3194, 3195, 3196, 3197, 3198, 3199, 3200, 3201, 3202, 3203, 3204, 3205, 3206, 3207, 3208,
3209, 3210, 3211, 3212, 3213, 3214, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 3215, 3216, 3217, 3218, 3219, 3220, 3221, 3222, 3223,
3224, 3225, 3226, 3227, 3228, 3229, 3230, 3231, 3232, 3233, 3234, 3235, 3236, 3237, 3238, 3239,
3240, 3241, 3242, 3243, 3244, 3245, 3246, 3247, 3248, 3249, 3250, 3251, 3252, 3253, 3254, 3255,
3256, 3257, 3258, 3259, 3260, 3261, 3262, 3253, 3263, 3264, 3265, 3266, 3267, 3268, 3269, 3270,
3271, 3272, 3273, 3274, 3275, 3276, 3277, 3278, 3279, 3280, 3281, 3282, 3283, 3284, 3285, 3286,
3287, 3288, 3289, 3290, 3291, 3292, 3293, 3294, 3295, 3296, 3297, 3298, 3299, 3300, 3301, 3302,
3303, 3304, 3305, 3306, 3307, 3308, 3309, 3310, 3311, 3312, 3313, 3314, 3315, 3316, 3317, 3318,
3319, 3320, 3321, 3322, 3323, 3324, 3325, 3326, 3327, 3328, 3329, 3330, 3331, 3332, 3333, 3334,
3335, 3336, 3337, 3338, 3339, 3340, 3341, 3342, 3343, 3344, 3345, 3346, 3347, 3348, 3349, 3350,
3351, 3352, 3353, 3354, 3355, 3356, 3357, 3358, 3359, 3360, 3361, 3362, 3254, 3363, 3364, 3365,
3366, 3367, 3368, 3369, 3370, 3371, 3372, 3373, 3374, 3375, 3376, 3377, 3378, 3379, 3380, 3381,
3382, 3383, 3384, 3385, 3386, 3387, 3388, 3389, 3390, 3391, 3392, 3393, 3394, 3395, 3396, 3397,
3398, 3399, 3400, 3401, 3402, 3403, 3404, 3405, 3406, 3407, 3408, 3409, 3410, 3411, 3412, 3413,
3414, 3415, 3416, 3417, 3418, 3419, 3420, 3421, 3422, 3423, 3424, 3425, 3426, 3427, 3428, 3429,
3430, 3431, 3432, 3433, 3434, 3435, 3436, 3437, 3438, 3439, 3440, 3441, 3442, 3443, 3444, 3445,
3446, 3447, 3448, 3449, 3450, 3451, 3452, 3453, 3454, 3455, 3456, 3457, 3458, 3459, 3460, 3461,
3462, 3463, 3464, 3465, 3466, 3467, 3468, 3469, 3470, 3471, 3472, 3473, 3474, 3475, 3476, 3477,
3478, 3479, 3480, 3481, 3482, 3483, 3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3492, 3493,
3494, 3495, 3496, 3497, 3498, 3499, 3500, 3501, 3502, 3503, 3504, 3505, 3506, 3507, 3508, 3509,
3510, 3511, 3512, 3513, 3514, 3515, 3516, 3517, 3518, 3519, 3520, 3521, 3522, 3523, 3524, 3525,
3526, 3527, 3528, 3529, 3530, 3531, 3532, 3533, 3534, 3535, 3536, 3537, 3538, 3539, 3540, 3541,
3542, 3543, 3544, 3545, 3546, 3547, 3548, 3549, 3550, 3551, 3552, 3553, 3554, 3555, 3556, 3557,
3558, 3559, 3560, 3561, 3562, 3563, 3564, 3565, 3566, 3567, 3568, 3569, 3570, 3571, 3572, 3573,
3574, 3575, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 3576, 3577, 3578, 3579, 3580, 3581, 3582, 3583, 3584, 3585, 3586, 3587,
3588, 3589, 3590, 3591, 3592, 3593, 3594, 3595, 3596, 3597, 3598, 3599, 3600, 3601, 3602, 3603,
3604, 3605, 3606, 3607, 3608, 3609, 3610, 3611, 3612, 3613, 3614, 3615, 3616, 3617, 3618, 3619,
3620, 3621, 3622, 3623, 3624, 3625, 3626, 3627, 3628, 3629, 3630, 3631, 3632, 3633, 3634, 3635,
3636, 3637, 3638, 3639, 0, 0, 3640, 3641, 3642, 3643, 3644, 3645, 3646, 3647, 3648, 3649,
3650, 3651, 3652, 3653, 3654, 3655, 3656, 3657, 3658, 3659, 3660, 3661, 3662, 3663, 3664, 3665,
3666, 3667, 3668, 3669, 3670, 3671, 3672, 3673, 3674, 3675, 3676, 3677, 3678, 3679, 3680, 3681,
3682, 3683, 3684, 3685, 3686, 3687, 3688, 3689, 3690, 3691, 3692, 3693, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 3694, 3695, 3696, 3697, 3698, 3699, 3700, 3701, 3702, 3703, 3704, 3705,
3706, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 3707, 3708, 3709, 3710, 3711, 3712, 3713, 3714, 3715, 3716, 0, 0,
0, 0, 0, 0, 369, 369, 369, 369, 369, 369, 369, 0, 0, 0, 0, 0,
0, 0, 0, 0, 3717, 3718, 3719, 3720, 3720, 3721, 3722, 3723, 3724, 3725, 3726, 3727,
3728, 3729, 3730, 3731, 3732, 3733, 3734, 3735, 3736, 0, 0, 3737, 3738, 3739, 3739, 3739,
3739, 3740, 3740, 3740, 3741, 3742, 3743, 0, 3744, 3745, 3746, 3747, 3748, 3749, 3750, 3751,
3752, 3753, 3754, 3755, 3756, 3757, 3758, 3759, 3760, 3761, 3762, 0, 3763, 3764, 3765, 3766,
0, 0, 0, 0, 3767, 3768, 3769, 0, 3770, 0, 3771, 3772, 3773, 3774, 3775, 3776,
3777, 3778, 3779, 3780, 3781, 3782, 3783, 3784, 3785, 3786, 3787, 3788, 3789, 3790, 3791, 3792,
3793, 3794, 3795, 3796, 3797, 3798, 3799, 3800, 3801, 3802, 3803, 3804, 3805, 3806, 3807, 3808,
3809, 3810, 3811, 3812, 3813, 3814, 3815, 3816, 3817, 3818, 3819, 3820, 3821, 3822, 3823, 3824,
3825, 3826, 3827, 3828, 3829, 3830, 3831, 3832, 3833, 3834, 3835, 3836, 3837, 3838, 3839, 3840,
3841, 3842, 3843, 3844, 3845, 3846, 3847, 3848, 3849, 3850, 3851, 3852, 3853, 3854, 3855, 3856,
3857, 3858, 3859, 3860, 3861, 3862, 3863, 3864, 3865, 3866, 3867, 3868, 3869, 3870, 3871, 3872,
3873, 3874, 3875, 3876, 3877, 3878, 3879, 3880, 3881, 3882, 3883, 3884, 3885, 3886, 3887, 3888,
3889, 3890, 3891, 3892, 3893, 3894, 3895, 3896, 3897, 3898, 3899, 3900, 3901, 3902, 3903, 3904,
3905, 0, 0, 0, 0, 3906, 3907, 3908, 3909, 3910, 3911, 3912, 3913, 3914, 3915, 3916,
3917, 3918, 3919, 3920, 3921, 3922, 3923, 3924, 3925, 3926, 3927, 3928, 3929, 3930, 3931, 3932,
3933, 3934, 3935, 3936, 3937, 3938, 3939, 3940, 3941, 3942, 3943, 3944, 3945, 3946, 3947, 3948,
3949, 3950, 3951, 3952, 3953, 3954, 3955, 3956, 3957, 3958, 3959, 3960, 3961, 3962, 3963, 3964,
3965, 3966, 3967, 3968, 3969, 3970, 3971, 3972, 3973, 3974, 3975, 3976, 3977, 3978, 3979, 3980,
3981, 3982, 3983, 3984, 3985, 3986, 3987, 3988, 3989, 3990, 3991, 3992, 3993, 3994, 3995, 3996,
3997, 3998, 3999, 4000, 4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009, 4010, 4011, 4012,
4013, 4014, 4015, 4016, 4017, 4018, 4019, 4020, 4021, 4022, 4023, 4024, 4025, 4026, 4027, 4028,
4029, 4030, 4031, 4032, 4033, 4034, 4035, 4036, 4037, 4038, 4039, 4040, 4041, 4042, 4043, 4044,
4045, 4046, 4047, 4048, 4049, 4050, 4051, 4052, 4053, 4054, 4055, 4056, 4057, 4058, 4059, 4060,
4061, 4062, 4063, 4064, 4065, 4066, 4067, 4068, 4069, 4070, 4071, 4072, 4073, 4074, 4075, 4076,
4077, 4078, 4079, 4080, 4081, 4082, 4083, 4084, 4085, 4086, 4087, 4088, 4089, 4090, 4091, 4092,
4093, 4094, 4095, 0, 0, 0, 4096, 4097, 4098, 4099, 4100, 4101, 0, 0, 4102, 4103,
4104, 4105, 4106, 4107, 0, 0, 4108, 4109, 4110, 4111, 4112, 4113, 0, 0, 4114, 4115,
4116, 0, 0, 0, 4117, 4118, 4119, 4120, 4121, 4122, 4123, 0, 4124, 4125, 4126, 4127,
4128, 4129, 4130, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 382, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 382, 0, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 369, 395, 382, 0,
0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4131, 4132, 4133,
4134, 0, 0, 0, 0, 0, 0, 0, 0, 4135, 0, 0, 0, 0, 0, 4136,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 600, 4137, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 4138, 4139, 4140, 4141, 4142, 4143, 4144, 680, 680, 395, 395, 395, 0, 0,
0, 4145, 680, 680, 680, 680, 680, 0, 0, 0, 0, 0, 0, 0, 0, 382,
382, 382, 382, 382, 382, 382, 382, 0, 0, 369, 369, 369, 369, 369, 382, 382,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 369, 369,
369, 369, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4146,
4147, 4148, 4149, 4150, 4151, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 369, 369, 369, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371,
1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165,
4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173,
4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367,
1370, 4154, 4155, 1371, 1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162,
4163, 1381, 4164, 4165, 4166, 1403, 1386, 4167, 1366, 0, 1395, 1404, 4168, 1372, 4169, 4170,
1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402,
1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371, 1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158,
4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165, 4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404,
4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181,
4152, 0, 1360, 1402, 0, 0, 4153, 0, 0, 4154, 4155, 0, 0, 1373, 4156, 1375,
1376, 0, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165, 4166, 1403, 0, 4167,
0, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 0, 4171, 4172, 4173, 4174, 4175, 4176, 4177,
4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371,
1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165,
4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173,
4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4152, 1385, 0, 1402, 1387, 1388, 4153, 0,
0, 4154, 4155, 1371, 1389, 1373, 4156, 1375, 1376, 0, 4157, 4158, 4159, 4160, 4161, 4162,
4163, 0, 4164, 4165, 4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170,
1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4152, 1385, 0, 1402,
1387, 1388, 4153, 0, 1370, 4154, 4155, 1371, 1389, 0, 4156, 0, 0, 0, 4157, 4158,
4159, 4160, 4161, 4162, 4163, 0, 4164, 4165, 4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404,
4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181,
4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371, 1389, 1373, 4156, 1375,
1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165, 4166, 1403, 1386, 4167,
1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177,
4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371,
1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165,
4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173,
4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367,
1370, 4154, 4155, 1371, 1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162,
4163, 1381, 4164, 4165, 4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170,
1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402,
1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371, 1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158,
4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165, 4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404,
4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181,
4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371, 1389, 1373, 4156, 1375,
1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165, 4166, 1403, 1386, 4167,
1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173, 4174, 4175, 4176, 4177,
4178, 4179, 4180, 4181, 4152, 1385, 1360, 1402, 1387, 1388, 4153, 1367, 1370, 4154, 4155, 1371,
1389, 1373, 4156, 1375, 1376, 1377, 4157, 4158, 4159, 4160, 4161, 4162, 4163, 1381, 4164, 4165,
4166, 1403, 1386, 4167, 1366, 1368, 1395, 1404, 4168, 1372, 4169, 4170, 1390, 4171, 4172, 4173,
4174, 4175, 4176, 4177, 4178, 4179, 4180, 4181, 4182, 4183, 0, 0, 4184, 4185, 1399, 4186,
4187, 4188, 4189, 4190, 4191, 4192, 4193, 4194, 4195, 4196, 4197, 1400, 4198, 4199, 4200, 4201,
4202, 4203, 4204, 4205, 4206, 4207, 4208, 4209, 1398, 4210, 4211, 4212, 4213, 4214, 4215, 4216,
4217, 4218, 4219, 4220, 4221, 1397, 4222, 4223, 4224, 4225, 4226, 4227, 4228, 4229, 4230, 4231,
4232, 4233, 4234, 4235, 4236, 4237, 4184, 4185, 1399, 4186, 4187, 4188, 4189, 4190, 4191, 4192,
4193, 4194, 4195, 4196, 4197, 1400, 4198, 4199, 4200, 4201, 4202, 4203, 4204, 4205, 4206, 4207,
4208, 4209, 1398, 4210, 4211, 4212, 4213, 4214, 4215, 4216, 4217, 4218, 4219, 4220, 4221, 1397,
4222, 4223, 4224, 4225, 4226, 4227, 4228, 4229, 4230, 4231, 4232, 4233, 4234, 4235, 4236, 4237,
4184, 4185, 1399, 4186, 4187, 4188, 4189, 4190, 4191, 4192, 4193, 4194, 4195, 4196, 4197, 1400,
4198, 4199, 4200, 4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208, 4209, 1398, 4210, 4211, 4212,
4213, 4214, 4215, 4216, 4217, 4218, 4219, 4220, 4221, 1397, 4222, 4223, 4224, 4225, 4226, 4227,
4228, 4229, 4230, 4231, 4232, 4233, 4234, 4235, 4236, 4237, 4184, 4185, 1399, 4186, 4187, 4188,
4189, 4190, 4191, 4192, 4193, 4194, 4195, 4196, 4197, 1400, 4198, 4199, 4200, 4201, 4202, 4203,
4204, 4205, 4206, 4207, 4208, 4209, 1398, 4210, 4211, 4212, 4213, 4214, 4215, 4216, 4217, 4218,
4219, 4220, 4221, 1397, 4222, 4223, 4224, 4225, 4226, 4227, 4228, 4229, 4230, 4231, 4232, 4233,
4234, 4235, 4236, 4237, 4184, 4185, 1399, 4186, 4187, 4188, 4189, 4190, 4191, 4192, 4193, 4194,
4195, 4196, 4197, 1400, 4198, 4199, 4200, 4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208, 4209,
1398, 4210, 4211, 4212, 4213, 4214, 4215, 4216, 4217, 4218, 4219, 4220, 4221, 1397, 4222, 4223,
4224, 4225, 4226, 4227, 4228, 4229, 4230, 4231, 4232, 4233, 4234, 4235, 4236, 4237, 4238, 4239,
0, 0, 4240, 4241, 4242, 4243, 4244, 4245, 4246, 4247, 4248, 4249, 4240, 4241, 4242, 4243,
4244, 4245, 4246, 4247, 4248, 4249, 4240, 4241, 4242, 4243, 4244, 4245, 4246, 4247, 4248, 4249,
4240, 4241, 4242, 4243, 4244, 4245, 4246, 4247, 4248, 4249, 4240, 4241, 4242, 4243, 4244, 4245,
4246, 4247, 4248, 4249, 4250, 4251, 4252, 4253, 4254, 4255, 4256, 4257, 4258, 4259, 4260, 0,
0, 0, 0, 0, 4261, 4262, 4263, 4264, 4265, 4266, 4267, 4268, 4269, 4270, 4271, 4272,
4273, 4274, 4275, 4276, 4277, 4278, 4279, 4280, 4281, 4282, 4283, 4284, 4285, 4286, 4287, 1633,
1648, 4288, 4289, 0, 0, 4290, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 4291, 0, 4292, 0, 0, 4293, 0, 0, 0, 4294, 0, 0, 0, 4295, 2564,
4296, 4297, 4298, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4299, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4300, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4301, 4302, 4303, 4304, 4305, 4306, 4307, 4308, 4309, 4310, 4311, 4312,
4313, 4314, 4315, 4316, 4317, 4318, 4319, 4320, 4321, 4322, 4323, 4324, 4325, 4326, 4327, 4328,
4329, 4330, 4331, 4332, 4333, 4334, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4335, 4336, 4337, 4338, 4339, 4340, 4341, 4342, 4343, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 4344, 4345, 4346, 4347, 4348, 2920, 4349, 4350, 4351, 4352, 2921, 4353,
4354, 4355, 2922, 4356, 4357, 4358, 4359, 4360, 4361, 4362, 4363, 4364, 4365, 4366, 4367, 2980,
4368, 4369, 4370, 4371, 4372, 4373, 4374, 4375, 4376, 2985, 2923, 2924, 2986, 4377, 4378, 2733,
4379, 2925, 4380, 4381, 4382, 4383, 4383, 4383, 4384, 4385, 4386, 4387, 4388, 4389, 4390, 4391,
4392, 4393, 4394, 4395, 4396, 4397, 4398, 4399, 4400, 4401, 4401, 2988, 4402, 4403, 4404, 4405,
2927, 4406, 4407, 4408, 2886, 4409, 4410, 4411, 4412, 4413, 4414, 4415, 4416, 4417, 4418, 4419,
4420, 4421, 4422, 4423, 4424, 4425, 4426, 4427, 4428, 4429, 4430, 4431, 4432, 4433, 4434, 4434,
4435, 4436, 4437, 2729, 4438, 4439, 4440, 4441, 4442, 4443, 4444, 4445, 2932, 4446, 4447, 4448,
4449, 4450, 4451, 4452, 4453, 4454, 4455, 4456, 4457, 4458, 4459, 4460, 4461, 4462, 4463, 4464,
4465, 4466, 2675, 4467, 4468, 4469, 4469, 4470, 4471, 4471, 4472, 4473, 4474, 4475, 4476, 4477,
4478, 4479, 4480, 4481, 4482, 4483, 4484, 2933, 4485, 4486, 4487, 4488, 3000, 4488, 4489, 2935,
4490, 4491, 4492, 4493, 2936, 2648, 4494, 4495, 4496, 4497, 4498, 4499, 4500, 4501, 4502, 4503,
4504, 4505, 4506, 4507, 4508, 4509, 4510, 4511, 4512, 4513, 4514, 4515, 2937, 4516, 4517, 4518,
4519, 4520, 4521, 2939, 4522, 4523, 4524, 4525, 4526, 4527, 4528, 4529, 2676, 3008, 4530, 4531,
4532, 4533, 4534, 4535, 4536, 4537, 2940, 4538, 4539, 4540, 4541, 3051, 4542, 4543, 4544, 4545,
4546, 4547, 4548, 4549, 4550, 4551, 4552, 4553, 4554, 2746, 4555, 4556, 4557, 4558, 4559, 4560,
4561, 4562, 4563, 4564, 4565, 2941, 2833, 4566, 4567, 4568, 4569, 4570, 4571, 4572, 4573, 3012,
4574, 4575, 4576, 4577, 4578, 4579, 4580, 4581, 3013, 4582, 4583, 4584, 4585, 4586, 4587, 4588,
4589, 4590, 4591, 4592, 4593, 3015, 4594, 4595, 4596, 4597, 4598, 4599, 4600, 4601, 4602, 4603,
4604, 4604, 4605, 4606, 3017, 4607, 4608, 4609, 4610, 4611, 4612, 4613, 2732, 4614, 4615, 4616,
4617, 4618, 4619, 4620, 3023, 4621, 4622, 4623, 4624, 4625, 4626, 4626, 3024, 3053, 4627, 4628,
4629, 4630, 4631, 2694, 3026, 4632, 4633, 2952, 4634, 4635, 2908, 4636, 4637, 2956, 4638, 4639,
4640, 4641, 4641, 4642, 4643, 4644, 4645, 4646, 4647, 4648, 4649, 4650, 4651, 4652, 4653, 4654,
4655, 4656, 4657, 4658, 4659, 4660, 4661, 4662, 4663, 4664, 4665, 4666, 4667, 4668, 2962, 4669,
4670, 4671, 4672, 4673, 4674, 4675, 4676, 4677, 4678, 4679, 4680, 4681, 4682, 4683, 4684, 4470,
4685, 4686, 4687, 4688, 4689, 4690, 4691, 4692, 4693, 4694, 4695, 4696, 2750, 4697, 4698, 4699,
4700, 4701, 4702, 2965, 4703, 4704, 4705, 4706, 4707, 4708, 4709, 4710, 4711, 4712, 4713, 4714,
4715, 4716, 4717, 4718, 4719, 4720, 4721, 4722, 2689, 4723, 4724, 4725, 4726, 4727, 4728, 3033,
4729, 4730, 4731, 4732, 4733, 4734, 4735, 4736, 4737, 4738, 4739, 4740, 4741, 4742, 4743, 4744,
4745, 4746, 4747, 4748, 3038, 3039, 4749, 4750, 4751, 4752, 4753, 4754, 4755, 4756, 4757, 4758,
4759, 4760, 4761, 3040, 4762, 4763, 4764, 4765, 4766, 4767, 4768, 4769, 4770, 4771, 4772, 4773,
4774, 4775, 4776, 4777, 4778, 4779, 4780, 4781, 4782, 4783, 4784, 4785, 4786, 4787, 4788, 4789,
4790, 4791, 3046, 3046, 4792, 4793, 4794, 4795, 4796, 4797, 4798, 4799, 4800, 4801, 3047, 4802,
4803, 4804, 4805, 4806, 4807, 4808, 4809, 4810, 4811, 4812, 4813, 4814, 4815, 4816, 4817, 4818,
4819, 4820,
]
__composition_pages_middle = _all_ushort(__composition_pages_middle)
def _composition_pages_middle(index): return intmask(__composition_pages_middle[index])

def _composition_index(code):
    return _composition_pages((_composition_pgtbl(code >> 7) << 7) + (code & 127))


def composition(current, next):
    l = lookup_composition_left_index(_composition_index(current))
    if l < 0:
        raise KeyError
    r = lookup_composition_right_index(_composition_index(next))
    if r < 0:
        raise KeyError
    key = l * 55 + r
    result = _composition(key)
    if result == 0:
        raise KeyError
    return result

__composition_prefixes = [
'',
'<noBreak>',
'<compat>',
'<super>',
'<fraction>',
'<sub>',
'<font>',
'<circle>',
'<wide>',
'<vertical>',
'<square>',
'<isolated>',
'<final>',
'<initial>',
'<medial>',
'<small>',
'<narrow>',
]

def _composition_prefixes(index): return __composition_prefixes[index]

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


def lookup_special_casing_lower_len(index):
    if 1 <= index <= 24:
        return lookup_special_casing_lower_len_middle(index - 1)
    if index < 1:
        return 0
    if index < 89:
        return 1
    raise KeyError

_lookup_special_casing_lower_len_middle = (
'\x01\x02\x01\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x01\x01'
'\x01\x01\x00\x00'
)
def lookup_special_casing_lower_len_middle(index): return ord(_lookup_special_casing_lower_len_middle[index])
# estimated 0.19 KiB
_lookup_special_casing_lower = [
0, 7084, 2981, 7087, 0, 7092, 0, 4947, 4966, 0, 0, 0, 0, 0, 0, 0,
0, 7155, 7167, 7168, 7169, 7170, 7171, 0, 0, 4411, 7175, 7176, 7177, 7178, 7179, 7180,
7181, 7182, 7183, 7184, 7185, 7194, 7195, 7196, 7197, 7198, 7199, 7200, 7201, 7210, 7211, 7212,
7213, 7214, 7215, 7216, 7217, 7226, 7227, 7228, 4509, 7229, 7231, 7232, 7233, 4517, 7234, 7236,
7237, 7238, 7239, 7240, 7241, 7242, 7243, 7244, 7245, 7246, 7247, 4519, 7248, 7561, 7562, 7563,
7564, 7565, 7566, 7567, 7568, 7569, 7570, 7571, 7572,
]
_lookup_special_casing_lower = _all_ushort(_lookup_special_casing_lower)
def lookup_special_casing_lower(index): return intmask(_lookup_special_casing_lower[index])
_lookup_special_casing_title_len = (
'\x00\x02\x01\x02\x00\x02\x00\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02'
'\x02\x02\x02\x00\x00\x02\x03\x03\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x02\x01\x02\x02\x03\x02\x01'
'\x02\x02\x03\x03\x03\x02\x03\x03\x03\x02\x02\x03\x02\x01\x02\x02\x03\x02\x02\x02'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02'
)
def lookup_special_casing_title_len(index): return ord(_lookup_special_casing_title_len[index])
# estimated 0.19 KiB
_lookup_special_casing_title = [
0, 6928, 7085, 6942, 0, 6920, 0, 6822, 6831, 0, 0, 0, 0, 0, 0, 0,
0, 6970, 6916, 6932, 6936, 6938, 6902, 0, 0, 6843, 6837, 6840, 6843, 7186, 7187, 7188,
7189, 7190, 7191, 7192, 7193, 7202, 7203, 7204, 7205, 7206, 7207, 7208, 7209, 7218, 7219, 7220,
7221, 7222, 7223, 7224, 7225, 7064, 7230, 6944, 6810, 6807, 7068, 7235, 6948, 6816, 6813, 6819,
6822, 6960, 6825, 6828, 6831, 6962, 6964, 6834, 7072, 7249, 6952, 6849, 6846, 6774, 6908, 6910,
6771, 6774, 6930, 6930, 6986, 6980, 6982, 6990, 6984,
]
_lookup_special_casing_title = _all_ushort(_lookup_special_casing_title)
def lookup_special_casing_title(index): return intmask(_lookup_special_casing_title[index])
_lookup_special_casing_upper_len = (
'\x00\x02\x01\x02\x00\x02\x00\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x02\x02\x02'
'\x02\x02\x02\x00\x00\x02\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x02\x02'
'\x02\x02\x03\x03\x03\x02\x03\x03\x03\x02\x02\x03\x02\x02\x02\x02\x03\x02\x02\x02'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02'
)
def lookup_special_casing_upper_len(index): return ord(_lookup_special_casing_upper_len[index])
# estimated 0.19 KiB
_lookup_special_casing_upper = [
0, 6924, 7085, 6942, 0, 6920, 0, 6822, 6831, 0, 0, 0, 0, 0, 0, 0,
0, 6968, 6916, 6932, 6936, 6938, 6902, 0, 0, 6843, 6837, 6840, 6843, 7016, 7018, 7020,
7022, 7024, 7026, 7028, 7030, 7032, 7034, 7036, 7038, 7040, 7042, 7044, 7046, 7048, 7050, 7052,
7054, 7056, 7058, 7060, 7062, 7066, 6956, 6946, 6810, 6810, 7070, 6958, 6950, 6816, 6816, 6819,
6822, 6960, 6825, 6828, 6831, 6962, 6964, 6834, 7074, 6966, 6954, 6849, 6849, 6768, 6766, 6769,
6765, 6768, 6926, 6926, 6978, 6972, 6974, 6988, 6976,
]
_lookup_special_casing_upper = _all_ushort(_lookup_special_casing_upper)
def lookup_special_casing_upper(index): return intmask(_lookup_special_casing_upper[index])
_lookup_special_casing_casefold_len = (
'\x01\x02\x00\x02\x01\x02\x01\x03\x03\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02'
'\x02\x02\x02\x01\x02\x02\x03\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x03\x02\x02'
'\x02\x02\x03\x03\x03\x02\x03\x03\x03\x02\x02\x03\x02\x02\x02\x02\x03\x02\x02\x02'
'\x03\x03\x02\x02\x02\x02\x02\x02\x02'
)
def lookup_special_casing_casefold_len(index): return ord(_lookup_special_casing_casefold_len[index])
# estimated 0.19 KiB
_lookup_special_casing_casefold = [
3593, 3150, 0, 3489, 6929, 2999, 4508, 1761, 1800, 4978, 4967, 4971, 4980, 4976, 4972, 3601,
3561, 3741, 2959, 3163, 3221, 3245, 2837, 5309, 3150, 1812, 1806, 1809, 1812, 4215, 4225, 4229,
4233, 4237, 4241, 4245, 4249, 4303, 4313, 4317, 4321, 4325, 4329, 4333, 4337, 4433, 4443, 4447,
4451, 4455, 4459, 4463, 4467, 4499, 3557, 3545, 1725, 1725, 4503, 3565, 3549, 1755, 1755, 1758,
1761, 3575, 1764, 1797, 1800, 3599, 3611, 1803, 4507, 3615, 3631, 1839, 1839, 1488, 6772, 6775,
1485, 1488, 3151, 3151, 3749, 3743, 3745, 3751, 3747,
]
_lookup_special_casing_casefold = _all_ushort(_lookup_special_casing_casefold)
def lookup_special_casing_casefold(index): return intmask(_lookup_special_casing_casefold[index])
_lookup_db_category = [
'Cc',
'Cc',
'Cc',
'Cc',
'Cc',
'Zs',
'Po',
'Po',
'Sc',
'Po',
'Ps',
'Pe',
'Sm',
'Po',
'Pd',
'Po',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Sm',
'Sm',
'Lu',
'Sk',
'Pc',
'Ll',
'Zs',
'Po',
'Sc',
'So',
'So',
'Sk',
'So',
'Ll',
'Pi',
'Cf',
'So',
'Sm',
'No',
'No',
'Ll',
'Po',
'No',
'Pf',
'No',
'No',
'No',
'Lu',
'Lu',
'Sm',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Ll',
'Ll',
'Lu',
'Lu',
'Ll',
'Ll',
'Lu',
'Ll',
'Ll',
'Lu',
'Lu',
'Lu',
'Ll',
'Lu',
'Lu',
'Lu',
'Lu',
'Ll',
'Lu',
'Lu',
'Ll',
'Lu',
'Ll',
'Lu',
'Lu',
'Lu',
'Lu',
'Lo',
'Ll',
'Lu',
'Lt',
'Ll',
'Ll',
'Ll',
'Lu',
'Lu',
'Lu',
'Lu',
'Lu',
'Lu',
'Ll',
'Lu',
'Lu',
'Lu',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lm',
'Lm',
'Sk',
'Lm',
'Lm',
'Mn',
'Mn',
'Cn',
'Lm',
'Po',
'Lu',
'Po',
'Lu',
'Lu',
'Lu',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Ll',
'Ll',
'Lu',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Ll',
'Sm',
'Lu',
'Lu',
'Lu',
'Ll',
'Ll',
'So',
'Mn',
'Me',
'Lu',
'Ll',
'Lu',
'Po',
'Ll',
'Ll',
'Pd',
'Pd',
'Po',
'Lo',
'Po',
'Cf',
'Sm',
'Po',
'Sc',
'Po',
'Po',
'Lo',
'Lm',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Po',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'So',
'Cf',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Lm',
'Mc',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Sc',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Mn',
'No',
'No',
'No',
'Lo',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Ps',
'Pe',
'Lu',
'Lo',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Zs',
'Nl',
'Nl',
'Nl',
'Cf',
'No',
'No',
'No',
'No',
'No',
'No',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Ll',
'Lu',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Lt',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Lt',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Lt',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lu',
'Lu',
'Lt',
'Cf',
'Pd',
'Pi',
'Pf',
'Ps',
'Pi',
'Pi',
'Pf',
'Po',
'Zl',
'Zp',
'Cf',
'Cf',
'Cf',
'Cf',
'Cf',
'Po',
'Pc',
'Sm',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Sm',
'Sc',
'So',
'Lu',
'Lu',
'Lu',
'So',
'Lu',
'Sm',
'Ll',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'No',
'Sm',
'Sm',
'Ps',
'Pe',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'So',
'So',
'So',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Lu',
'Lu',
'Lu',
'Ll',
'Ll',
'Lu',
'Lu',
'Lu',
'Lu',
'Lu',
'No',
'Ll',
'Lm',
'So',
'Zs',
'Po',
'Lm',
'Nl',
'Pd',
'Ps',
'Pe',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Mn',
'Nl',
'Nl',
'Nl',
'Sk',
'So',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Lo',
'Lo',
'Lo',
'Cn',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Lo',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Lu',
'Sk',
'No',
'No',
'No',
'No',
'No',
'No',
'So',
'Cs',
'Co',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Ll',
'Lo',
'Pe',
'Po',
'Pc',
'Po',
'Po',
'Po',
'Sm',
'Pd',
'Sm',
'Sm',
'Sc',
'Po',
'Po',
'Sc',
'Po',
'Ps',
'Pe',
'Sm',
'Po',
'Pd',
'Po',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Nd',
'Sm',
'Sm',
'Lu',
'Sk',
'Pc',
'Ll',
'Po',
'Ps',
'Pe',
'Lo',
'Lm',
'Lm',
'So',
'So',
'Sm',
'Cf',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'No',
'No',
'No',
'No',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Lu',
'Ll',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'No',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Nl',
'Sm',
'No',
]

def lookup_db_category(index): return _lookup_db_category[index]
_lookup_db_bidirectional = [
'BN',
'S',
'B',
'S',
'WS',
'WS',
'ON',
'ET',
'ET',
'ON',
'ON',
'ON',
'ES',
'CS',
'ES',
'CS',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'ON',
'ON',
'L',
'ON',
'ON',
'L',
'CS',
'ON',
'ET',
'ON',
'ON',
'ON',
'ON',
'L',
'ON',
'BN',
'ET',
'ET',
'EN',
'EN',
'L',
'ON',
'EN',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'L',
'NSM',
'NSM',
'',
'L',
'ON',
'L',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'NSM',
'NSM',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'R',
'R',
'R',
'R',
'AN',
'AL',
'ET',
'AL',
'CS',
'AL',
'AL',
'AL',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'AL',
'BN',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ET',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'WS',
'L',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'R',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'WS',
'B',
'LRE',
'RLE',
'PDF',
'LRO',
'RLO',
'ET',
'ON',
'CS',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'ES',
'ET',
'ON',
'L',
'L',
'L',
'ET',
'L',
'ON',
'L',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'ON',
'ET',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'L',
'ON',
'ON',
'WS',
'ON',
'L',
'L',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'NSM',
'L',
'L',
'L',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ET',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'AL',
'ON',
'ON',
'ON',
'CS',
'CS',
'ET',
'ES',
'ES',
'ON',
'ON',
'ET',
'ON',
'ET',
'ET',
'ON',
'ON',
'ON',
'ES',
'CS',
'ES',
'CS',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'EN',
'ON',
'ON',
'L',
'ON',
'ON',
'L',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'ON',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'R',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'AN',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'L',
'EN',
]

def lookup_db_bidirectional(index): return _lookup_db_bidirectional[index]
_lookup_db_east_asian_width = [
'N',
'N',
'N',
'N',
'N',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'Na',
'N',
'A',
'A',
'Na',
'A',
'A',
'N',
'A',
'N',
'A',
'A',
'A',
'A',
'A',
'N',
'A',
'A',
'N',
'A',
'A',
'A',
'N',
'A',
'A',
'A',
'A',
'N',
'N',
'N',
'A',
'N',
'A',
'N',
'A',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'A',
'A',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'N',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'W',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'A',
'A',
'N',
'N',
'A',
'A',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'N',
'N',
'N',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'H',
'N',
'A',
'N',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'N',
'N',
'N',
'N',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'A',
'N',
'W',
'W',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'A',
'N',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'W',
'F',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'W',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'F',
'H',
'H',
'H',
'H',
'H',
'H',
'F',
'H',
'H',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'N',
'A',
]

def lookup_db_east_asian_width(index): return _lookup_db_east_asian_width[index]
_lookup_db_numeric = [
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
2.0,
3.0,
0.0,
0.0,
1.0,
0.0,
1.0 / 4.0,
1.0 / 2.0,
3.0 / 4.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
1.0 / 16.0,
1.0 / 8.0,
3.0 / 16.0,
1.0 / 4.0,
3.0 / 4.0,
16.0,
10.0,
100.0,
1000.0,
0.0,
1.0,
2.0,
3.0,
0.0,
1.0 / 4.0,
1.0 / 2.0,
3.0 / 4.0,
0.0,
1.0 / 2.0,
3.0 / 2.0,
5.0 / 2.0,
7.0 / 2.0,
9.0 / 2.0,
11.0 / 2.0,
13.0 / 2.0,
15.0 / 2.0,
17.0 / 2.0,
-1.0 / 2.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
20.0,
30.0,
40.0,
50.0,
60.0,
70.0,
80.0,
90.0,
10000.0,
0.0,
17.0,
18.0,
19.0,
0.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0 / 7.0,
1.0 / 9.0,
1.0 / 10.0,
1.0 / 3.0,
2.0 / 3.0,
1.0 / 5.0,
2.0 / 5.0,
3.0 / 5.0,
4.0 / 5.0,
1.0 / 6.0,
5.0 / 6.0,
1.0 / 8.0,
3.0 / 8.0,
5.0 / 8.0,
7.0 / 8.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
11.0,
12.0,
50.0,
100.0,
500.0,
1000.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
11.0,
12.0,
50.0,
100.0,
500.0,
1000.0,
1000.0,
5000.0,
10000.0,
6.0,
50.0,
50000.0,
100000.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
11.0,
12.0,
13.0,
14.0,
15.0,
16.0,
17.0,
18.0,
19.0,
20.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
11.0,
12.0,
13.0,
14.0,
15.0,
16.0,
17.0,
18.0,
19.0,
20.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0 / 2.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
10.0,
20.0,
30.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
21.0,
22.0,
23.0,
24.0,
25.0,
26.0,
27.0,
28.0,
29.0,
30.0,
31.0,
32.0,
33.0,
34.0,
35.0,
36.0,
37.0,
38.0,
39.0,
40.0,
41.0,
42.0,
43.0,
44.0,
45.0,
46.0,
47.0,
48.0,
49.0,
50.0,
5.0,
2.0,
7.0,
0.0,
1.0,
10000.0,
3.0,
9.0,
4.0,
100000000.0,
10.0,
1000.0,
100.0,
1000000000000.0,
8.0,
6.0,
20.0,
30.0,
40.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
1.0 / 4.0,
1.0 / 2.0,
3.0 / 4.0,
1.0 / 16.0,
1.0 / 8.0,
3.0 / 16.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
0.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
200.0,
300.0,
400.0,
500.0,
600.0,
700.0,
800.0,
900.0,
2000.0,
3000.0,
4000.0,
5000.0,
6000.0,
7000.0,
8000.0,
9000.0,
20000.0,
30000.0,
40000.0,
50000.0,
60000.0,
70000.0,
80000.0,
90000.0,
1.0 / 4.0,
1.0 / 2.0,
1.0,
5.0,
50.0,
500.0,
5000.0,
50000.0,
10.0,
100.0,
1000.0,
10000.0,
2.0,
30.0,
300.0,
1.0 / 2.0,
1.0 / 2.0,
2.0 / 3.0,
3.0 / 4.0,
90.0,
900.0,
10.0,
20.0,
100.0,
0.0,
0.0,
1.0,
2.0,
3.0,
10.0,
20.0,
100.0,
1000.0,
10000.0,
1.0,
2.0,
3.0,
4.0,
50.0,
4.0,
1.0,
2.0,
3.0,
4.0,
5.0,
6.0,
7.0,
8.0,
9.0,
10.0,
20.0,
30.0,
40.0,
50.0,
60.0,
70.0,
80.0,
90.0,
100.0,
200.0,
300.0,
400.0,
500.0,
600.0,
700.0,
800.0,
900.0,
1.0 / 2.0,
1.0 / 4.0,
1.0 / 3.0,
2.0 / 3.0,
0.0,
1.0 / 3.0,
2.0 / 3.0,
5.0 / 6.0,
1.0 / 3.0,
2.0 / 3.0,
1.0 / 8.0,
1.0 / 4.0,
1.0 / 6.0,
1.0 / 4.0,
0.0,
0.0,
]

def lookup_db_numeric(index): return _lookup_db_numeric[index]

def lookup_db_decimal(index):
    if 17 <= index <= 703:
        return lookup_db_decimal_middle(index - 17)
    if index < 17:
        return 0
    if index < 836:
        return 0
    raise KeyError

_lookup_db_decimal_middle = (
'\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
'\t\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x01\x02\x03\x04\x05'
'\x06\x07\x08\t\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02'
'\x03\x04\x05\x06\x07\x08\t'
)
def lookup_db_decimal_middle(index): return ord(_lookup_db_decimal_middle[index])

def lookup_db_digit(index):
    if 17 <= index <= 801:
        return lookup_db_digit_middle(index - 17)
    if index < 17:
        return 0
    if index < 836:
        return 0
    raise KeyError

_lookup_db_digit_middle = (
'\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x02\x03\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
'\t\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x01\x02\x03\x04\x05'
'\x06\x07\x08\t\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x04\x05\x06\x07\x08\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04'
'\x05\x06\x07\x08\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x07\x08'
'\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03'
'\x04\x05\x06\x07\x08\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02'
'\x03\x04\x05\x06\x07\x08\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x00\x00\x01\x02\x03\x04'
'\x05\x06\x07\x08\t'
)
def lookup_db_digit_middle(index): return ord(_lookup_db_digit_middle[index])

def lookup_db_upperdist(index):
    if 46 <= index <= 778:
        return lookup_db_upperdist_middle(index - 46)
    if index < 46:
        return 0
    if index < 836:
        return 0
    raise KeyError

# estimated 2.88 KiB
_lookup_db_upperdist_middle = [
-743, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 32, -121, 0, 1,
1, 0, 0, 232, 0, 0, 300, -195, 0, 0, 0, 0, 0, 0, 0, 0,
-97, 0, 0, -163, 0, -130, 0, 0, 0, 0, 0, -56, 0, 1, 2, 79,
0, 0, 0, 0, 0, 0, 0, -10815, 0, 0, 0, -10783, -10780, -10782, 210, 206,
205, 202, 203, 207, 209, 211, -10743, -10749, 213, 214, -10727, 218, 69, 217, 71, 219,
0, 0, 0, 0, 0, 0, -84, 0, 0, 0, 0, 0, 0, 0, 0, 0,
38, 37, 0, 31, 64, 63, 0, 62, 57, 0, 47, 54, 8, 86, 80, -7,
0, 96, 0, 0, 0, 0, 80, 80, 0, 0, 0, 0, 15, 0, 0, 48,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, -35332, -3814, 0, 0, 0, 0, 0,
59, 0, -8, 0, 0, 0, 0, 0, -74, -86, -100, -128, -112, -126, -8, -8,
-8, -8, -8, -8, -8, -8, 0, 0, 0, 0, 0, 0, 0, 0, -8, -8,
-8, -8, -8, -8, -8, -8, 0, 0, 0, 0, 0, 0, 0, 0, -8, -8,
-8, -8, -8, -8, -8, -8, 0, 0, 0, 0, 0, 0, 0, 0, 0, -9,
0, 0, 0, 0, 0, 7205, 0, -9, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, -9, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
16, 16, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 10795, 10792, 0, 0, 0, 0, 0, 0, 7264, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40,
]
_lookup_db_upperdist_middle = _all_int32(_lookup_db_upperdist_middle)
def lookup_db_upperdist_middle(index): return intmask(_lookup_db_upperdist_middle[index])

def lookup_db_lowerdist(index):
    if 53 <= index <= 777:
        return lookup_db_lowerdist_middle(index - 53)
    if index < 53:
        return 0
    if index < 836:
        return 0
    raise KeyError

# estimated 2.85 KiB
_lookup_db_lowerdist_middle = [
-32, -32, 0, 0, 0, 0, 0, -1, 0, 0, -1, 199, 0, 0, 121, 0,
0, -210, -206, -205, 0, -79, -202, -203, -207, 0, -211, -209, 0, -213, 0, -214,
-218, -217, -219, 0, 0, -2, -1, 0, 0, 0, 97, 56, 130, -10795, 163, -10792,
0, 195, -69, -71, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, -38, 0, -37, -64, -63, 0, 0, 0, 0, 0, 0, 0, -8,
0, 0, 0, 0, 0, 0, 0, 0, 0, 60, 0, 0, 7, -80, -80, 0,
0, 0, 0, 0, -15, 0, -48, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, -7264, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7615, 0, 8, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8,
8, 8, 8, 8, 8, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 8,
8, 8, 8, 8, 8, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 8,
8, 8, 8, 8, 8, 8, 8, 0, 0, 0, 0, 0, 74, 9, 0, 0,
0, 0, 0, 0, 86, 9, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0,
112, 0, 0, 0, 0, 0, 128, 126, 9, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 7517, 8383, 8262, 0, -28, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -16, -16, -16, -16,
-16, -16, -16, -16, -16, -16, -16, -16, -16, -16, -16, -16, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -26, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10743, 3814, 10727, 0, 0,
10780, 10749, 10783, 10782, 10815, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 35332, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -32, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, -40,
]
_lookup_db_lowerdist_middle = _all_int32(_lookup_db_lowerdist_middle)
def lookup_db_lowerdist_middle(index): return intmask(_lookup_db_lowerdist_middle[index])

def lookup_db_titledist(index):
    if 31 <= index <= 778:
        return lookup_db_titledist_middle(index - 31)
    if index < 31:
        return 0
    if index < 836:
        return 0
    raise KeyError

# estimated 2.94 KiB
_lookup_db_titledist_middle = [
32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -743,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 32, -121, 0, 1, 1,
0, 0, 232, 0, 0, 300, -195, 0, 0, 0, 0, 0, 0, 0, 0, -97,
0, 0, -163, 0, -130, 0, 0, 0, 0, 0, -56, -1, 0, 1, 79, 0,
0, 0, 0, 0, 0, 0, -10815, 0, 0, 0, -10783, -10780, -10782, 210, 206, 205,
202, 203, 207, 209, 211, -10743, -10749, 213, 214, -10727, 218, 69, 217, 71, 219, 0,
0, 0, 0, 0, 0, -84, 0, 0, 0, 0, 0, 0, 0, 0, 0, 38,
37, 0, 31, 64, 63, 0, 62, 57, 0, 47, 54, 8, 86, 80, -7, 0,
96, 0, 0, 0, 0, 80, 80, 0, 0, 0, 0, 15, 0, 0, 48, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, -35332, -3814, 0, 0, 0, 0, 0, 59,
0, -8, 0, 0, 0, 0, 0, -74, -86, -100, -128, -112, -126, -8, -8, -8,
-8, -8, -8, -8, -8, 0, 0, 0, 0, 0, 0, 0, 0, -8, -8, -8,
-8, -8, -8, -8, -8, 0, 0, 0, 0, 0, 0, 0, 0, -8, -8, -8,
-8, -8, -8, -8, -8, 0, 0, 0, 0, 0, 0, 0, 0, 0, -9, 0,
0, 0, 0, 0, 7205, 0, -9, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, -9, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
16, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 10795, 10792, 0, 0, 0, 0, 0, 0, 7264, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40,
]
_lookup_db_titledist_middle = _all_int32(_lookup_db_titledist_middle)
def lookup_db_titledist_middle(index): return intmask(_lookup_db_titledist_middle[index])

def lookup_db_special_casing_index(index):
    if 46 <= index <= 671:
        return lookup_db_special_casing_index_middle(index - 46)
    if index < 46:
        return -1
    if index < 836:
        return -1
    raise KeyError

_lookup_db_special_casing_index_middle = (
'\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\xff\xff\xff\xff\xff\xff\xff\x02\xff'
'\x03\xff\x04\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\x05\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\x06\xff\xff\xff\xff\xff\xff\xff\xff\x07\xff\xff\x08\t'
'\xff\xff\xff\n\x0b\xff\x0c\r\xff\x0e\x0f\xff\xff\x10\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\x11\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x12\x13\x14\x15\x16\x17\x18\xff\xff'
'\x19\x1a\x1b\x1c\xff\xff\xff\xff\xff\xff\x1d\x1e\x1f !"#$\x1d\x1e'
'\x1f !"#$%&\'()*+,%&\'()*'
'+,-./01234-./0123456'
'789\xff6\x06:;<=>\xff;?@AB\xffCD'
'EFG\xffHIJKL\xff\xffI\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xffMNOPQR'
'STUVWX'
)
def lookup_db_special_casing_index_middle(index): return signed_ord(_lookup_db_special_casing_index_middle[index])
# estimated 1.65 KiB
_lookup_db_flags = [
0, 1, 5, 5, 5, 4097, 4096, 4096, 4096, 12288, 4608, 4608, 4096, 4096, 4096, 12288,
6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 4608, 4096, 7178, 12288, 6144, 7202,
1, 4096, 4096, 4096, 4096, 12288, 4096, 7202, 4608, 8192, 4096, 4096, 4288, 4288, 7202, 14336,
4288, 4608, 4160, 4160, 4160, 7178, 7178, 4096, 7202, 7202, 7202, 7202, 7178, 7202, 7202, 7178,
7178, 7202, 7202, 7178, 7202, 7202, 7178, 7178, 7178, 7202, 7178, 7178, 7178, 7178, 7202, 7178,
7178, 7202, 7178, 7202, 7178, 7178, 7178, 7178, 7170, 7202, 7178, 7186, 7202, 7202, 7202, 7178,
7178, 7178, 7178, 7178, 7178, 7202, 7178, 7178, 7178, 7202, 7202, 7202, 7202, 7202, 7202, 7202,
7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 15362, 15362,
12288, 15362, 15362, 14336, 14336, 0, 12290, 4096, 7178, 14336, 7178, 7178, 7178, 7202, 7202, 7202,
7202, 7202, 7202, 7202, 7178, 7202, 7202, 7178, 7202, 7202, 7202, 7202, 7202, 7202, 7178, 7202,
4096, 7178, 7178, 7178, 7202, 7202, 4096, 14336, 12288, 7178, 7202, 7178, 4096, 7202, 7202, 4096,
4096, 4096, 7170, 12288, 8192, 4096, 4096, 4096, 4096, 4096, 7170, 15362, 6592, 6592, 6592, 6592,
6592, 6592, 6592, 6592, 6592, 6592, 4096, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592,
6592, 4096, 8192, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 15362, 6144, 6592,
6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 4096, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4160, 4160, 4160, 4160, 14336, 4160, 4160, 4160, 6146, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4160, 4160, 4160, 4608, 4608, 7178, 7170, 6336, 6336, 6336, 6336, 6336, 6336,
6336, 6336, 6336, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 1, 7232, 7232, 7232,
8192, 4160, 4160, 4160, 4160, 4160, 4160, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7178,
7202, 7178, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202,
7202, 7202, 7202, 7202, 7186, 7186, 7186, 7186, 7186, 7186, 7186, 7186, 7202, 7202, 7202, 7202,
7202, 7202, 7202, 7202, 7186, 7186, 7186, 7186, 7186, 7186, 7186, 7186, 7202, 7202, 7202, 7202,
7202, 7202, 7202, 7202, 7186, 7186, 7186, 7186, 7186, 7186, 7186, 7186, 7202, 7202, 7202, 7202,
7202, 7178, 7186, 7202, 7202, 7202, 7202, 7202, 7202, 7178, 7186, 7202, 7202, 7202, 7202, 7178,
7202, 7202, 7202, 7202, 7202, 7178, 7202, 7202, 7202, 7202, 7202, 7178, 7178, 7186, 8192, 4096,
12288, 12288, 4096, 4096, 4096, 4096, 12288, 5, 5, 8192, 8192, 8192, 8192, 8192, 4096, 6144,
4096, 4288, 4288, 4288, 4288, 4288, 4288, 4288, 4096, 4096, 7168, 7178, 7178, 7178, 7168, 7178,
4608, 7202, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232,
7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232,
7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 4160, 4608, 4096, 4608, 4608, 4288, 4288, 4288,
4288, 4288, 4288, 4288, 4288, 4288, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4288, 4288, 4288, 4288, 4288, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4096, 4096, 4096, 4288, 4288, 4288, 4288, 4288, 4288, 4288, 4288, 4288, 4288, 4288, 4160,
7178, 7178, 7178, 7202, 7202, 7178, 7178, 7178, 7178, 7178, 4160, 7202, 12290, 4096, 1, 4096,
15362, 7232, 4096, 4096, 4096, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 14336, 7232,
7232, 7232, 12288, 4096, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 7234, 7234, 7234, 0,
7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234, 7234,
7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7178, 12288, 4160, 4160, 4160, 4160, 4160,
4160, 4096, 0, 0, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202, 7202,
4098, 4096, 12288, 6144, 4096, 12288, 4096, 4096, 4096, 4608, 4096, 4096, 4096, 4096, 4096, 12288,
4608, 4608, 4096, 4096, 4096, 12288, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592, 6592,
4608, 4096, 7178, 12288, 6144, 7202, 4096, 4608, 4608, 7170, 15362, 14338, 4096, 4096, 4096, 8192,
4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232, 7232,
4160, 4160, 4160, 4160, 7232, 7232, 7232, 7232, 7232, 7178, 7202, 4160, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4288, 4288, 4288, 4288, 4160, 4160, 4288, 4288, 4288, 4288, 4288, 4288, 4288,
4288, 4288, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160,
4160, 4160, 4160, 4160, 4160, 4160, 4160, 4160, 7168, 7232, 7232, 7232, 7232, 7232, 7232, 7232,
7232, 7232, 4096, 4288,
]
_lookup_db_flags = _all_ushort(_lookup_db_flags)
def lookup_db_flags(index): return intmask(_lookup_db_flags[index])
__db_pgtbl = (
'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13'
'\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\''
'()))*+,-./0123456789'
':;<=>?@ABCDEFGHIJKLM'
'NNOPQRS\x11TUVWXYZ[\\]^_'
'`abcdeffffffgfffffhf'
'ffffffffffffffffffff'
'fffffffffffffffijklf'
'ffmfffnofffffpfffqff'
'ffffffffrstffffffuvf'
'fffffffwffffffffffff'
'ffxffffffffyffffzfff'
'fffffffffffffffff{ff'
'ffff|fffffffffffffff'
'f}~fffffffffffffffff'
'\x7f\x80fffffffffffffffff\x81'
'\x82ffffffff\x83))\x84\x85\x86\x87\x88\x89\x8a\x8b'
'\x8c\x8d\x11\x8effffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'fffffffffff\x8f\x90\x90\x90\x90\x90\x90\x90\x90'
'\x90\x90\x90\x90\x90\x90\x90\x90\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x92\x93'
'\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\x11\xa4\xa5\xa6'
'\xa7\xa8\x11\x11\x11\x11\x11\x11\xa9\x11\xaa\x11\xab\x11\xac\x11\xad\x11\x11\x11'
'\xae\x11\x11\x11\x11\xaf\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11))))'
'))\xb0\x11\xb1\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11))))))))\xb2\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11N\xb3\xb4\xb5\xb6\x11\xb7\x11\xb8\xb9\xba\xbb'
'\xbc\xbd\xbe\xbf\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\xc0\xc1\xc2\xc3\xc4\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\xc5\xc6\xc7fffffffffffff'
'ff\xc8\xc9f\xca\xcbfffffffffffff'
'ffffffffffffffffffff'
'fffffffffffffff\xccffff'
'fffffff\xcdffffffffffff'
'ffffffffffffffffffff'
'ff\xcefffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'\xcffffffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'ffffffffffffffffffff'
'fffffffffffffffff\xd0ff'
'ffffffffffffffffffff'
'ffffffffff\xd1\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'f\xd3ff\xd4\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd5\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd2'
'\xd2\xd2\xd2\xd2\xd2\xd2\xd2\xd5\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\xd6\x11\xd7\xd8\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11\x11'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\xd9\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91\x91'
'\x91\x91\x91\xd9'
)
def _db_pgtbl(index): return ord(__db_pgtbl[index])
# estimated 54.52 KiB
__db_pages = [
0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 2, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 1,
5, 6, 6, 7, 8, 7, 6, 9, 10, 11, 6, 12, 13, 14, 15, 13,
16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 15, 6, 26, 27, 26, 6,
6, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28,
28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 10, 6, 11, 29, 30,
29, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31,
31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 10, 27, 11, 27, 0,
0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
32, 33, 8, 8, 34, 8, 35, 36, 37, 38, 39, 40, 27, 41, 36, 29,
42, 43, 44, 45, 37, 46, 36, 47, 37, 48, 39, 49, 50, 51, 52, 33,
53, 53, 53, 53, 53, 53, 54, 53, 53, 53, 53, 53, 53, 53, 53, 53,
54, 53, 53, 53, 53, 53, 53, 55, 54, 53, 53, 53, 53, 53, 54, 56,
57, 57, 58, 58, 58, 58, 57, 58, 57, 57, 57, 58, 57, 57, 58, 58,
57, 58, 57, 57, 58, 58, 58, 55, 57, 57, 57, 58, 57, 58, 57, 59,
60, 61, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 61, 60, 61, 60, 62, 60, 62, 60, 62, 60, 61, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 63, 61, 60, 62, 60, 61, 60, 62, 60, 62,
64, 65, 63, 61, 60, 62, 60, 62, 39, 60, 62, 60, 62, 60, 62, 63,
61, 63, 61, 60, 61, 60, 62, 60, 61, 66, 63, 61, 60, 61, 60, 62,
60, 62, 63, 61, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 63, 61, 60, 62, 60, 61, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 67, 60, 62, 60, 62, 60, 62, 68,
69, 70, 60, 62, 60, 62, 71, 60, 62, 72, 72, 60, 62, 73, 74, 75,
76, 60, 62, 72, 77, 78, 79, 80, 60, 62, 81, 73, 79, 82, 83, 84,
60, 62, 60, 62, 60, 62, 85, 60, 62, 85, 73, 73, 60, 62, 85, 60,
62, 86, 86, 60, 62, 60, 62, 87, 60, 62, 73, 88, 60, 62, 73, 89,
88, 88, 88, 88, 90, 91, 92, 90, 91, 92, 90, 91, 92, 60, 61, 60,
61, 60, 61, 60, 61, 60, 61, 60, 61, 60, 61, 60, 61, 93, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
94, 90, 91, 92, 60, 62, 95, 96, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
97, 73, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 73, 73, 73, 73, 73, 73, 98, 60, 62, 99, 100, 101,
101, 60, 62, 102, 103, 104, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
105, 106, 107, 108, 109, 73, 110, 110, 73, 111, 73, 112, 73, 73, 73, 73,
110, 39, 73, 113, 73, 73, 73, 73, 114, 115, 73, 116, 73, 73, 73, 115,
73, 117, 118, 73, 73, 119, 73, 73, 73, 73, 73, 73, 73, 120, 73, 73,
121, 73, 73, 121, 73, 73, 73, 73, 121, 122, 123, 123, 124, 73, 73, 73,
73, 73, 125, 73, 88, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
126, 126, 126, 126, 126, 126, 126, 126, 126, 127, 127, 126, 126, 126, 126, 126,
126, 126, 128, 128, 37, 128, 127, 129, 127, 129, 129, 129, 127, 129, 127, 127,
130, 126, 128, 128, 128, 128, 128, 128, 37, 37, 37, 37, 128, 37, 128, 37,
126, 126, 126, 126, 126, 128, 128, 128, 128, 128, 128, 128, 127, 128, 126, 128,
128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 132, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
60, 62, 60, 62, 127, 128, 60, 62, 133, 133, 134, 83, 83, 83, 135, 133,
133, 133, 133, 133, 128, 128, 136, 137, 138, 138, 138, 133, 139, 133, 140, 140,
141, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54,
54, 54, 133, 54, 54, 54, 54, 54, 54, 54, 53, 53, 142, 143, 143, 143,
144, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57,
57, 57, 145, 57, 57, 57, 57, 57, 57, 57, 58, 58, 146, 147, 147, 148,
149, 150, 151, 151, 151, 152, 153, 154, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
155, 156, 157, 73, 158, 159, 160, 60, 62, 161, 60, 62, 73, 97, 97, 97,
162, 163, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162,
54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54,
54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54, 54,
57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57,
57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57, 57,
164, 165, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 166, 167, 167, 167, 167, 167, 168, 168, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
169, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 170,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171,
171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171,
171, 171, 171, 171, 171, 171, 171, 133, 133, 126, 172, 172, 172, 172, 172, 172,
133, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173,
173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173,
173, 173, 173, 173, 173, 173, 173, 174, 133, 172, 175, 133, 133, 133, 133, 133,
133, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 176, 167,
177, 167, 167, 177, 167, 167, 177, 167, 133, 133, 133, 133, 133, 133, 133, 133,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 133, 133, 133, 133, 133,
178, 178, 178, 177, 179, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
180, 180, 180, 180, 133, 133, 160, 160, 181, 182, 182, 183, 184, 185, 38, 38,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 185, 133, 133, 185, 185,
133, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
187, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 133,
188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 182, 198, 198, 185, 186, 186,
167, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 185, 186, 167, 167, 167, 167, 167, 167, 167, 180, 168, 167,
167, 167, 167, 167, 167, 187, 187, 167, 167, 38, 167, 167, 167, 167, 186, 186,
199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 186, 186, 186, 209, 209, 186,
185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 133, 210,
186, 167, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 133, 133, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 186, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 167, 167, 167, 167, 167,
167, 167, 167, 167, 221, 221, 38, 135, 135, 135, 221, 133, 133, 133, 133, 133,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 167, 167, 167, 167, 221, 167, 167, 167, 167, 167,
167, 167, 167, 167, 221, 167, 167, 167, 221, 167, 167, 167, 167, 167, 133, 133,
177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
167, 167, 167, 222, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 167, 88, 222, 222,
222, 167, 167, 167, 167, 167, 167, 167, 167, 222, 222, 222, 222, 167, 222, 133,
88, 167, 167, 167, 167, 167, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 167, 167, 172, 172, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
172, 126, 88, 133, 133, 133, 133, 133, 133, 88, 88, 88, 88, 88, 88, 88,
133, 167, 222, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 88,
88, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 133, 88, 133, 133, 133, 88, 88, 88, 88, 133, 133, 167, 88, 222, 222,
222, 167, 167, 167, 167, 133, 133, 222, 222, 133, 133, 222, 222, 167, 88, 133,
133, 133, 133, 133, 133, 133, 133, 222, 133, 133, 133, 133, 88, 88, 133, 88,
88, 88, 167, 167, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
88, 88, 233, 233, 234, 235, 236, 237, 238, 239, 166, 233, 133, 133, 133, 133,
133, 167, 167, 222, 133, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 88,
88, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 133, 88, 88, 133, 88, 88, 133, 88, 88, 133, 133, 167, 133, 222, 222,
222, 167, 167, 133, 133, 133, 133, 167, 167, 133, 133, 167, 167, 167, 133, 133,
133, 167, 133, 133, 133, 133, 133, 133, 133, 88, 88, 88, 88, 133, 88, 133,
133, 133, 133, 133, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
167, 167, 88, 88, 88, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 167, 167, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88,
88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 133, 88, 88, 133, 88, 88, 88, 88, 88, 133, 133, 167, 88, 222, 222,
222, 167, 167, 167, 167, 167, 133, 167, 167, 222, 133, 222, 222, 167, 133, 133,
88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 167, 167, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
133, 233, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 167, 222, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 88,
88, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 133, 88, 88, 133, 88, 88, 88, 88, 88, 133, 133, 167, 88, 222, 167,
222, 167, 167, 167, 167, 133, 133, 222, 222, 133, 133, 222, 222, 167, 133, 133,
133, 133, 133, 133, 133, 133, 167, 222, 133, 133, 133, 133, 88, 88, 133, 88,
88, 88, 167, 167, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
166, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 167, 88, 133, 88, 88, 88, 88, 88, 88, 133, 133, 133, 88, 88,
88, 133, 88, 88, 88, 88, 133, 133, 133, 88, 88, 133, 88, 133, 88, 88,
133, 133, 133, 88, 88, 133, 133, 133, 88, 88, 88, 133, 133, 133, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 222, 222,
167, 222, 222, 133, 133, 133, 222, 222, 222, 133, 222, 222, 222, 167, 133, 133,
88, 133, 133, 133, 133, 133, 133, 222, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
240, 241, 242, 38, 38, 38, 38, 38, 38, 233, 38, 133, 133, 133, 133, 133,
133, 222, 222, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88,
88, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 133, 133, 133, 88, 167, 167,
167, 222, 222, 222, 222, 133, 167, 167, 167, 133, 167, 167, 167, 167, 133, 133,
133, 133, 133, 133, 133, 167, 167, 133, 88, 88, 133, 133, 133, 133, 133, 133,
88, 88, 167, 167, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
133, 133, 133, 133, 133, 133, 133, 133, 243, 244, 245, 246, 244, 245, 246, 166,
133, 133, 222, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88,
88, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 133, 133, 167, 88, 222, 247,
222, 222, 222, 222, 222, 133, 247, 222, 222, 133, 222, 222, 167, 167, 133, 133,
133, 133, 133, 133, 133, 222, 222, 133, 133, 133, 133, 133, 133, 133, 88, 133,
88, 88, 167, 167, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
133, 38, 38, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 222, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88,
88, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 88, 222, 222,
222, 167, 167, 167, 167, 133, 222, 222, 222, 133, 222, 222, 222, 167, 133, 133,
133, 133, 133, 133, 133, 133, 133, 222, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 167, 167, 133, 133, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
240, 241, 242, 248, 249, 250, 133, 133, 133, 166, 88, 88, 88, 88, 88, 88,
133, 133, 222, 222, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 133, 133,
88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 167, 133, 133, 133, 133, 222,
222, 222, 167, 167, 167, 133, 167, 133, 222, 222, 222, 222, 222, 222, 222, 222,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 222, 222, 172, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 167, 88, 251, 167, 167, 167, 167, 167, 167, 167, 133, 133, 133, 133, 233,
88, 88, 88, 88, 88, 88, 126, 167, 167, 167, 167, 167, 167, 167, 167, 172,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 172, 172, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 88, 88, 133, 88, 133, 133, 88, 88, 133, 88, 133, 133, 88, 133, 133,
133, 133, 133, 133, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88,
133, 88, 88, 88, 133, 88, 133, 88, 133, 133, 88, 88, 133, 88, 88, 88,
88, 167, 88, 251, 167, 167, 167, 167, 167, 167, 133, 167, 167, 88, 133, 133,
88, 88, 88, 88, 88, 133, 126, 133, 167, 167, 167, 167, 167, 167, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 88, 88, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 166, 166, 166, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172,
172, 172, 172, 166, 166, 166, 166, 166, 167, 167, 166, 166, 166, 166, 166, 166,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 252, 253, 254, 255, 256, 257,
258, 259, 260, 261, 166, 167, 166, 167, 166, 167, 262, 263, 262, 263, 222, 222,
88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133,
133, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 222,
167, 167, 167, 167, 167, 172, 167, 167, 88, 88, 88, 88, 133, 133, 133, 133,
167, 167, 167, 167, 167, 167, 167, 167, 133, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 133, 166, 166,
166, 166, 166, 166, 166, 166, 167, 166, 166, 166, 166, 166, 166, 133, 166, 166,
172, 172, 172, 172, 172, 166, 166, 166, 166, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 222, 222, 167, 167, 167,
167, 222, 167, 167, 167, 167, 167, 167, 222, 167, 167, 222, 222, 167, 167, 88,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 172, 172, 172, 172, 172, 172,
88, 88, 88, 88, 88, 88, 222, 222, 167, 167, 88, 88, 88, 88, 167, 167,
167, 88, 222, 222, 222, 88, 88, 222, 222, 222, 222, 222, 222, 222, 88, 88,
88, 167, 167, 167, 167, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 167, 222, 222, 167, 167, 222, 222, 222, 222, 222, 222, 167, 88, 222,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 222, 222, 222, 167, 166, 166,
264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264,
264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264, 264,
264, 264, 264, 264, 264, 264, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 172, 126, 133, 133, 133,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 265, 265, 265, 265, 265, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 265, 265, 265, 265, 265, 265,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 133, 133,
88, 88, 88, 88, 88, 88, 88, 133, 88, 133, 88, 88, 88, 88, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 133, 88, 88, 88, 88, 133, 133, 88, 88, 88, 88, 88, 88, 88, 133,
88, 133, 88, 88, 88, 88, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 133, 88, 88, 88, 88, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 167,
166, 172, 172, 172, 172, 172, 172, 172, 172, 266, 267, 268, 269, 270, 271, 272,
273, 274, 240, 275, 276, 277, 278, 279, 280, 281, 282, 241, 283, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
175, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 172, 172, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
284, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 262, 263, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 172, 172, 172, 285, 286,
287, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88,
88, 88, 167, 167, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 167, 167, 167, 172, 172, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 167, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88,
88, 133, 167, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 288, 288, 222, 167, 167, 167, 167, 167, 167, 167, 222, 222,
222, 222, 222, 222, 222, 222, 167, 222, 222, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 172, 172, 172, 126, 172, 172, 172, 233, 88, 167, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
243, 244, 245, 246, 289, 290, 291, 292, 293, 294, 133, 133, 133, 133, 133, 133,
135, 135, 135, 135, 135, 135, 175, 135, 135, 135, 135, 167, 167, 167, 284, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 126, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 167, 88, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133,
167, 167, 167, 222, 222, 222, 222, 167, 167, 222, 222, 222, 133, 133, 133, 133,
222, 222, 167, 222, 222, 222, 222, 222, 222, 167, 167, 167, 133, 133, 133, 133,
38, 133, 133, 133, 135, 135, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133,
88, 88, 88, 88, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133,
222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222,
222, 88, 88, 88, 88, 88, 88, 88, 222, 222, 133, 133, 133, 133, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 224, 133, 133, 133, 135, 135,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 167, 167, 222, 222, 222, 133, 133, 172, 172,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 222, 167, 222, 167, 167, 167, 167, 167, 167, 167, 133,
167, 222, 167, 222, 222, 167, 167, 167, 167, 167, 167, 167, 167, 222, 222, 222,
222, 222, 222, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 133, 133, 167,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
172, 172, 172, 172, 172, 172, 172, 126, 172, 172, 172, 172, 172, 172, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
167, 167, 167, 167, 222, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 167, 222, 167, 167, 167, 167, 167, 222, 167, 222, 222, 222,
222, 222, 167, 222, 222, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 172, 172, 172, 172, 172, 172,
172, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 167, 167, 167, 167, 167,
167, 167, 167, 167, 166, 166, 166, 166, 166, 166, 166, 166, 166, 133, 133, 133,
167, 167, 222, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 222, 167, 167, 167, 167, 222, 222, 167, 167, 222, 133, 133, 133, 88, 88,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 222, 222, 222, 222, 222, 222, 222, 222, 167, 167, 167, 167,
167, 167, 167, 167, 222, 222, 167, 167, 133, 133, 133, 172, 172, 172, 172, 172,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 88, 88, 88,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 126, 126, 126, 126, 126, 126, 172, 172,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
167, 167, 167, 172, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 222, 167, 167, 167, 167, 167, 167, 167, 88, 88, 88, 88, 167, 88, 88,
88, 88, 222, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 126, 126, 126, 126,
126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126,
126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126,
126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126,
126, 126, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 126, 295, 73, 73, 73, 296, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 126, 126, 126, 126, 126,
126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126,
126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 167, 167, 167,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 297, 298, 299, 300, 301, 302, 73, 73, 303, 73,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
304, 304, 304, 304, 304, 304, 304, 304, 305, 305, 305, 305, 305, 305, 305, 305,
304, 304, 304, 304, 304, 304, 133, 133, 305, 305, 305, 305, 305, 305, 133, 133,
304, 304, 304, 304, 304, 304, 304, 304, 305, 305, 305, 305, 305, 305, 305, 305,
304, 304, 304, 304, 304, 304, 304, 304, 305, 305, 305, 305, 305, 305, 305, 305,
304, 304, 304, 304, 304, 304, 133, 133, 305, 305, 305, 305, 305, 305, 133, 133,
306, 304, 307, 304, 308, 304, 309, 304, 133, 305, 133, 305, 133, 305, 133, 305,
304, 304, 304, 304, 304, 304, 304, 304, 305, 305, 305, 305, 305, 305, 305, 305,
310, 310, 311, 311, 311, 311, 312, 312, 313, 313, 314, 314, 315, 315, 133, 133,
316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331,
332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347,
348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363,
304, 304, 364, 365, 366, 133, 367, 368, 305, 305, 369, 369, 370, 128, 371, 128,
128, 128, 372, 373, 374, 133, 375, 376, 377, 377, 377, 377, 378, 128, 128, 128,
304, 304, 379, 380, 133, 133, 381, 382, 305, 305, 383, 383, 133, 128, 128, 128,
304, 304, 384, 385, 386, 157, 387, 388, 305, 305, 389, 389, 161, 128, 128, 128,
133, 133, 390, 391, 392, 133, 393, 394, 395, 395, 396, 396, 397, 128, 128, 133,
284, 284, 284, 284, 284, 284, 284, 284, 284, 284, 284, 210, 210, 210, 288, 398,
399, 175, 175, 399, 399, 399, 33, 135, 400, 401, 402, 403, 404, 405, 402, 403,
33, 33, 33, 135, 406, 33, 33, 406, 407, 408, 409, 410, 411, 412, 413, 32,
414, 182, 414, 414, 182, 33, 135, 135, 135, 40, 49, 33, 135, 135, 33, 415,
415, 135, 135, 135, 416, 262, 263, 135, 135, 135, 135, 135, 135, 135, 135, 135,
135, 135, 160, 135, 415, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 284,
210, 210, 210, 210, 210, 133, 133, 133, 133, 133, 210, 210, 210, 210, 210, 210,
417, 126, 133, 133, 418, 419, 420, 421, 422, 423, 424, 424, 160, 262, 263, 130,
417, 48, 44, 45, 418, 419, 420, 421, 422, 423, 424, 424, 160, 262, 263, 133,
126, 126, 126, 126, 126, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
233, 233, 233, 233, 233, 233, 233, 233, 233, 425, 233, 233, 34, 233, 233, 233,
233, 233, 233, 233, 233, 233, 233, 233, 233, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 168, 168, 168,
168, 167, 168, 168, 168, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
38, 38, 151, 36, 38, 36, 38, 151, 38, 36, 73, 151, 151, 151, 73, 73,
151, 151, 151, 39, 38, 151, 36, 38, 426, 151, 151, 151, 151, 151, 38, 38,
38, 36, 36, 38, 151, 38, 427, 38, 151, 38, 428, 429, 151, 151, 430, 73,
151, 151, 431, 151, 73, 88, 88, 88, 88, 73, 38, 38, 73, 73, 151, 151,
432, 160, 160, 160, 160, 151, 73, 73, 73, 73, 38, 160, 38, 38, 433, 166,
434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 244,
449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464,
465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480,
481, 482, 483, 60, 62, 484, 485, 486, 487, 488, 133, 133, 133, 133, 133, 133,
55, 55, 55, 55, 55, 36, 36, 36, 36, 36, 160, 160, 38, 38, 38, 38,
160, 38, 38, 160, 38, 38, 160, 38, 38, 38, 38, 38, 38, 38, 160, 38,
38, 38, 38, 38, 38, 38, 38, 38, 36, 36, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 160, 160,
38, 38, 55, 38, 55, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 36, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
55, 432, 489, 489, 432, 160, 160, 55, 489, 432, 432, 489, 432, 432, 160, 55,
160, 489, 424, 490, 160, 489, 432, 160, 160, 160, 489, 432, 432, 489, 55, 489,
489, 432, 432, 55, 432, 55, 432, 55, 55, 55, 55, 489, 489, 432, 489, 432,
432, 432, 432, 432, 55, 55, 55, 55, 160, 432, 160, 432, 489, 489, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 489, 432, 432, 432, 489, 160, 160, 160,
160, 160, 489, 432, 432, 432, 160, 160, 160, 160, 160, 160, 160, 160, 160, 432,
489, 55, 432, 160, 489, 489, 489, 489, 432, 432, 489, 489, 160, 160, 489, 489,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 489, 489, 432, 432, 489, 489, 432, 432, 432, 432, 432, 160, 160, 432,
432, 432, 432, 160, 160, 55, 160, 160, 432, 55, 160, 160, 160, 160, 160, 160,
160, 160, 432, 432, 160, 55, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 160, 160, 160, 160, 160, 432, 489,
160, 160, 160, 160, 160, 160, 160, 160, 160, 432, 432, 432, 432, 432, 160, 160,
432, 432, 160, 160, 160, 160, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 160, 160,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
38, 38, 38, 38, 38, 38, 38, 38, 432, 432, 432, 432, 38, 38, 38, 38,
38, 38, 36, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
432, 432, 38, 38, 38, 38, 38, 38, 38, 491, 492, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 38, 160, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 166, 38, 38, 38, 38, 38, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 160, 160, 160, 160,
160, 160, 38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508,
509, 510, 511, 512, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504,
505, 506, 507, 508, 509, 510, 511, 512, 48, 44, 45, 418, 513, 514, 515, 516,
517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 529, 529, 529,
529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529,
529, 529, 529, 529, 529, 529, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530,
530, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530, 530,
531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 531,
531, 531, 531, 531, 531, 531, 531, 531, 531, 531, 532, 503, 504, 505, 506, 507,
508, 509, 510, 511, 512, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 533,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 38, 38, 38, 38,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
38, 38, 36, 36, 36, 36, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
36, 36, 38, 36, 36, 36, 36, 36, 36, 36, 38, 38, 38, 38, 38, 38,
38, 38, 36, 36, 38, 38, 36, 55, 38, 38, 38, 38, 36, 36, 38, 38,
36, 55, 38, 38, 38, 38, 36, 36, 36, 38, 38, 36, 38, 38, 36, 36,
36, 36, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 36, 36, 36, 36, 38, 38, 38, 38, 38, 38, 38, 38, 38, 36,
38, 38, 38, 38, 38, 38, 38, 38, 160, 160, 160, 160, 160, 160, 160, 160,
38, 38, 38, 38, 38, 36, 36, 38, 38, 36, 38, 38, 38, 38, 36, 36,
38, 38, 38, 38, 36, 36, 38, 38, 38, 38, 38, 38, 36, 38, 36, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
36, 38, 36, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
36, 36, 38, 36, 36, 36, 38, 36, 36, 36, 36, 38, 36, 36, 38, 55,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 36, 36,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 166, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 36, 36,
38, 38, 38, 38, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 133, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 133, 36, 133, 133, 133, 133, 36, 36, 36, 36, 36, 36, 36, 36,
36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36,
133, 38, 38, 38, 38, 133, 38, 38, 38, 38, 133, 133, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 133, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 36, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 133, 38, 133, 38,
38, 38, 38, 133, 133, 133, 38, 36, 38, 38, 38, 38, 38, 38, 38, 133,
133, 38, 38, 38, 38, 38, 38, 38, 262, 263, 262, 263, 262, 263, 262, 263,
262, 263, 262, 263, 262, 263, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502,
534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 534, 535, 536, 537, 538, 539,
540, 541, 542, 543, 38, 133, 133, 133, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
133, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 133,
432, 160, 160, 432, 432, 262, 263, 160, 432, 432, 160, 133, 432, 133, 133, 133,
160, 160, 160, 432, 432, 432, 432, 160, 160, 160, 160, 160, 432, 432, 432, 160,
160, 160, 432, 432, 432, 432, 10, 11, 10, 11, 10, 11, 10, 11, 262, 263,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 262, 263, 10, 11, 262, 263, 262, 263, 262, 263, 262, 263, 262,
263, 262, 263, 262, 263, 262, 263, 262, 263, 160, 160, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
160, 160, 160, 160, 160, 160, 160, 160, 432, 160, 160, 160, 160, 160, 160, 160,
432, 432, 432, 432, 432, 432, 160, 160, 160, 432, 160, 160, 160, 160, 432, 432,
432, 432, 432, 160, 432, 432, 160, 160, 262, 263, 262, 263, 432, 160, 160, 160,
160, 432, 160, 432, 432, 432, 160, 160, 432, 432, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 432, 432, 432, 432, 432, 432, 160, 160, 262, 263, 160, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 160, 432, 432,
432, 432, 160, 160, 432, 160, 432, 160, 160, 432, 160, 432, 432, 432, 432, 160,
160, 160, 160, 160, 432, 432, 160, 160, 160, 160, 160, 160, 432, 432, 432, 160,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 160, 160, 432, 432, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 432, 432, 160, 160, 160, 160, 432, 432, 432, 432, 160, 432,
432, 160, 160, 432, 432, 160, 160, 160, 160, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 160, 160, 432, 432, 432, 432, 432, 432, 432, 432, 160, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432, 432,
432, 432, 432, 432, 432, 432, 432, 160, 160, 160, 160, 160, 432, 160, 432, 160,
160, 160, 432, 432, 432, 432, 432, 160, 160, 160, 160, 160, 432, 432, 432, 160,
160, 160, 160, 432, 160, 160, 160, 432, 432, 432, 432, 432, 160, 432, 160, 160,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160,
160, 160, 160, 160, 160, 38, 38, 160, 160, 160, 160, 160, 160, 133, 133, 133,
38, 38, 38, 38, 38, 36, 36, 36, 36, 36, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171,
171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171,
171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 133,
173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173,
173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173,
173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 133,
60, 62, 544, 545, 546, 547, 548, 60, 62, 60, 62, 60, 62, 549, 550, 551,
552, 73, 60, 62, 73, 60, 62, 73, 73, 73, 73, 73, 73, 126, 553, 553,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 73, 38, 38, 38, 38, 38, 38, 60, 62, 60, 62, 167,
167, 167, 133, 133, 133, 133, 133, 133, 133, 135, 135, 135, 135, 554, 135, 135,
555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555,
555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555, 555,
555, 555, 555, 555, 555, 555, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 126,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 133,
88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 133,
88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 133,
88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 133,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
135, 135, 40, 49, 40, 49, 135, 135, 135, 40, 49, 135, 40, 49, 135, 135,
135, 135, 135, 135, 135, 135, 135, 175, 135, 135, 175, 135, 40, 49, 135, 135,
40, 49, 262, 263, 262, 263, 262, 263, 262, 263, 135, 135, 135, 135, 135, 556,
135, 135, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 133, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 133, 133, 133, 133,
558, 559, 559, 559, 557, 560, 265, 561, 491, 492, 491, 492, 491, 492, 491, 492,
491, 492, 557, 557, 491, 492, 491, 492, 491, 492, 491, 492, 562, 563, 564, 564,
557, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 574, 574, 574, 574, 574,
562, 560, 560, 560, 560, 560, 557, 557, 575, 576, 577, 560, 265, 559, 557, 38,
133, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 133, 133, 574, 574, 578, 578, 560, 560, 265,
562, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 559, 560, 560, 560, 265,
133, 133, 133, 133, 133, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 133, 133,
133, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 133,
579, 579, 580, 581, 582, 583, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 133, 133, 133, 133, 133, 133, 133, 133,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 557, 557, 133,
580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 529, 529, 529, 529, 529, 529, 529, 529,
557, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 557, 557, 557, 579,
580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 557, 557, 557, 557,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 133,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 557, 557, 557, 557, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 557, 557,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 557,
265, 265, 265, 265, 265, 620, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 621, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 620, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 622, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
624, 265, 265, 622, 265, 265, 265, 625, 265, 626, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 627, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 621, 265, 265, 265,
265, 265, 265, 265, 620, 265, 628, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 629,
630, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 631,
265, 265, 265, 265, 265, 265, 265, 265, 626, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 620, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
632, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 629, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 633, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 621, 265, 634, 265, 635, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 630, 265, 631, 636, 637, 265, 265, 265, 265, 265, 265, 638, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 626, 626, 626, 626, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 628, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 624, 265, 265, 265, 265, 265, 265, 265, 624, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 624, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 627, 636,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 624, 621, 626, 265,
621, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 630, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 634, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 622, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 622, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 627, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 632, 265,
265, 265, 265, 265, 265, 265, 628, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 625, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 621, 265,
265, 265, 265, 621, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
621, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 631, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 635, 265, 265, 265, 265, 265, 632, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 635, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 639, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 560, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 133, 133, 133,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557, 557,
557, 557, 557, 557, 557, 557, 557, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 126, 126, 126, 126, 126, 126, 172, 172,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 126, 135, 135, 135,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 88, 88, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
133, 133, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 88, 167,
168, 168, 168, 135, 133, 133, 133, 133, 133, 133, 133, 133, 167, 167, 135, 127,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 640, 641, 642, 643, 644, 484, 645, 646, 647, 648,
167, 167, 172, 172, 172, 172, 172, 172, 133, 133, 133, 133, 133, 133, 133, 133,
128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
128, 128, 128, 128, 128, 128, 128, 127, 127, 127, 127, 127, 127, 127, 127, 127,
128, 128, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
73, 73, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62, 60, 62,
126, 73, 73, 73, 73, 73, 73, 73, 73, 60, 62, 60, 62, 649, 60, 62,
60, 62, 60, 62, 60, 62, 60, 62, 127, 650, 650, 60, 62, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 88, 88, 88, 88, 88,
88, 88, 167, 88, 88, 88, 167, 88, 88, 88, 88, 167, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 222, 222, 167, 167, 222, 38, 38, 38, 38, 133, 133, 133, 133,
651, 652, 653, 654, 655, 656, 166, 166, 233, 657, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 135, 135, 135, 135, 133, 133, 133, 133, 133, 133, 133, 133,
222, 222, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222,
222, 222, 222, 222, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133, 172, 172,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 88, 88, 88, 88, 88, 88, 172, 172, 172, 88, 133, 133, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 167, 167, 167, 167, 167, 167, 167, 167, 172, 172,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 167, 167, 167, 167, 167, 167, 167, 167, 167,
167, 167, 222, 222, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 172,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 133, 133, 133,
167, 167, 167, 222, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 167, 222, 222, 167, 167, 167, 167, 222, 222, 167, 222, 222, 222,
222, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 133, 126,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 172, 172,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 167, 167, 167, 167, 167, 167, 222,
222, 167, 167, 222, 222, 167, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 167, 88, 88, 88, 88, 88, 88, 88, 88, 167, 222, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 172, 172, 172, 172,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
126, 88, 88, 88, 88, 88, 88, 166, 166, 166, 88, 222, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
167, 88, 167, 167, 167, 88, 88, 167, 167, 88, 88, 88, 88, 88, 167, 167,
88, 167, 88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 88, 88, 126, 172, 172,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 222, 222, 167, 222, 222, 167, 222, 222, 172, 222, 167, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 133, 133, 133, 133, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 133, 133, 133, 133,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658, 658,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 626, 265, 265, 265, 265,
265, 265, 265, 630, 265, 265, 265, 265, 621, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 639, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 635, 265, 635, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 630, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 623, 623,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 623, 623,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
660, 661, 662, 663, 664, 665, 666, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 667, 668, 669, 670, 671, 133, 133, 133, 133, 133, 178, 167, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 424, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 133, 178, 178, 178, 178, 178, 133, 178, 133,
178, 178, 133, 178, 178, 133, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 672, 672,
672, 672, 672, 672, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 402, 673,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
133, 133, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 672, 672, 183, 38, 133, 133,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
559, 559, 559, 674, 559, 559, 559, 563, 564, 559, 133, 133, 133, 133, 133, 133,
167, 167, 167, 167, 167, 167, 167, 133, 133, 133, 133, 133, 133, 133, 133, 133,
559, 562, 562, 675, 675, 563, 564, 563, 564, 563, 564, 563, 564, 563, 564, 563,
564, 563, 564, 563, 564, 559, 559, 563, 564, 559, 559, 559, 559, 675, 675, 675,
676, 559, 677, 133, 559, 677, 559, 559, 562, 491, 492, 491, 492, 491, 492, 678,
559, 559, 679, 680, 681, 681, 682, 133, 559, 683, 678, 559, 133, 133, 133, 133,
672, 186, 672, 186, 672, 133, 672, 186, 672, 186, 672, 186, 672, 186, 672, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186,
186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 133, 133, 210,
133, 684, 684, 685, 686, 685, 684, 687, 688, 689, 684, 690, 691, 692, 693, 691,
694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 693, 684, 704, 705, 704, 684,
684, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706,
706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 706, 688, 684, 689, 707, 708,
707, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709,
709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 709, 688, 705, 689, 705, 688,
689, 710, 711, 712, 710, 710, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713,
714, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713,
713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713,
713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 715, 715,
713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713,
713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 713, 133,
133, 133, 713, 713, 713, 713, 713, 713, 133, 133, 713, 713, 713, 713, 713, 713,
133, 133, 713, 713, 713, 713, 713, 713, 133, 133, 713, 713, 713, 133, 133, 133,
686, 686, 705, 707, 716, 686, 686, 133, 717, 718, 718, 718, 718, 717, 717, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 719, 719, 719, 38, 36, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 88, 88, 133, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133, 133, 133,
172, 135, 166, 133, 133, 133, 133, 720, 721, 722, 723, 724, 725, 726, 727, 728,
240, 275, 276, 277, 278, 279, 280, 281, 282, 241, 729, 730, 731, 732, 733, 734,
735, 736, 242, 737, 738, 739, 740, 741, 742, 743, 744, 283, 745, 746, 747, 748,
749, 750, 751, 752, 133, 133, 133, 166, 166, 166, 166, 166, 166, 166, 166, 166,
753, 754, 755, 756, 757, 758, 759, 760, 756, 761, 757, 762, 758, 763, 759, 756,
761, 757, 762, 758, 763, 764, 760, 761, 755, 755, 755, 765, 765, 765, 765, 756,
761, 761, 761, 761, 761, 766, 757, 757, 757, 757, 762, 767, 758, 758, 758, 758,
758, 763, 759, 756, 757, 768, 769, 770, 771, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 243, 133, 133, 133, 133, 133,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 167, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133,
720, 724, 240, 278, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 772, 88, 88, 88, 88, 88, 88, 88, 88, 773, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 172,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 133, 133, 133, 133, 88, 88, 88, 88, 88, 88, 88, 88,
172, 640, 641, 774, 775, 776, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777,
777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777, 777,
777, 777, 777, 777, 777, 777, 777, 777, 778, 778, 778, 778, 778, 778, 778, 778,
778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778,
778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778, 778,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133, 133,
223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
178, 178, 178, 178, 178, 178, 133, 133, 178, 133, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 133, 178, 178, 133, 133, 133, 178, 133, 133, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 133, 177, 779, 780, 781, 782, 783, 784, 785, 786,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 779, 782, 783, 784, 780, 781, 133, 133, 133, 135,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 133, 133, 133, 133, 133, 177,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
178, 167, 167, 167, 133, 167, 167, 133, 133, 133, 133, 133, 167, 167, 167, 167,
178, 178, 178, 178, 133, 178, 178, 178, 133, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 133, 133, 133, 133, 167, 167, 167, 133, 133, 133, 133, 167,
787, 788, 789, 790, 782, 783, 784, 785, 133, 133, 133, 133, 133, 133, 133, 133,
177, 177, 177, 177, 177, 177, 177, 177, 177, 133, 133, 133, 133, 133, 133, 133,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 779, 791, 177,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 133, 133, 133, 135, 135, 135, 135, 135, 135, 135,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 133, 133, 779, 780, 781, 792, 782, 783, 784, 785,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 133, 133, 133, 133, 133, 779, 780, 781, 792, 782, 783, 784, 785,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178,
178, 178, 178, 178, 178, 178, 178, 178, 178, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808,
809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 133,
167, 167, 222, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
222, 222, 222, 167, 167, 167, 167, 222, 222, 167, 167, 172, 172, 288, 172, 172,
172, 172, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
641, 642, 643, 644, 484, 645, 646, 647, 642, 643, 644, 484, 645, 646, 647, 643,
644, 484, 645, 646, 647, 640, 641, 642, 643, 644, 484, 645, 646, 647, 640, 641,
642, 643, 644, 641, 642, 642, 643, 644, 484, 645, 646, 647, 640, 641, 642, 642,
643, 644, 824, 824, 640, 641, 642, 642, 643, 644, 642, 642, 643, 643, 643, 643,
484, 645, 645, 645, 646, 646, 647, 647, 647, 647, 641, 642, 643, 644, 484, 640,
641, 642, 643, 643, 644, 644, 824, 824, 640, 641, 825, 826, 827, 828, 829, 830,
831, 832, 833, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
172, 172, 172, 172, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 133, 133, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 222, 222, 167, 167, 167, 166, 166, 166, 222, 222, 222,
222, 222, 222, 210, 210, 210, 210, 210, 210, 210, 210, 167, 167, 167, 167, 167,
167, 167, 167, 166, 166, 167, 167, 167, 167, 167, 167, 167, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 167, 167, 167, 167, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166,
166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 167, 167, 167, 38, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133, 133, 133, 133, 133, 133,
720, 721, 722, 723, 724, 725, 726, 727, 728, 240, 275, 276, 277, 278, 279, 280,
281, 282, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 73, 73,
73, 73, 73, 73, 73, 133, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 151, 133, 151, 151,
133, 133, 151, 133, 133, 151, 151, 133, 133, 151, 151, 151, 151, 133, 151, 151,
151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 133, 73, 133, 73, 73, 73,
73, 73, 73, 73, 133, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 151, 151, 133, 151, 151, 151, 151, 133, 133, 151, 151, 151,
151, 151, 151, 151, 151, 133, 151, 151, 151, 151, 151, 151, 151, 133, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 151, 151, 133, 151, 151, 151, 151, 133,
151, 151, 151, 151, 151, 133, 151, 133, 133, 133, 151, 151, 151, 151, 151, 151,
151, 133, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 133, 133, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 834, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 432, 73, 73, 73, 73,
73, 73, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 834, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 432, 73, 73, 73, 73, 73, 73, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 834, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 432,
73, 73, 73, 73, 73, 73, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 834,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 432, 73, 73, 73, 73, 73, 73,
151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151,
151, 151, 151, 151, 151, 151, 151, 151, 151, 834, 73, 73, 73, 73, 73, 73,
73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73, 73,
73, 73, 73, 432, 73, 73, 73, 73, 73, 73, 151, 73, 133, 133, 199, 200,
201, 202, 203, 204, 205, 206, 207, 208, 199, 200, 201, 202, 203, 204, 205, 206,
207, 208, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 199, 200, 201, 202,
203, 204, 205, 206, 207, 208, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 133, 133, 133, 133,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
38, 38, 38, 38, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
835, 835, 48, 44, 45, 418, 513, 514, 515, 516, 517, 133, 133, 133, 133, 133,
529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529,
529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 529, 166, 133,
133, 529, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 529, 133, 529,
133, 133, 529, 133, 133, 133, 529, 133, 133, 133, 529, 529, 529, 529, 529, 133,
133, 133, 133, 133, 133, 133, 133, 529, 133, 133, 133, 133, 133, 133, 133, 529,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 529, 133, 529, 529, 133, 133, 529,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 529, 529, 529, 529, 133, 133,
529, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
579, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579, 579,
579, 579, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
579, 579, 579, 579, 579, 579, 579, 579, 579, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
265, 622, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 628, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 628, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 620, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 624, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 637, 265, 265, 265, 265, 265, 265, 265, 265, 638, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 638, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 635, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 626, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 626, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
621, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 626, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 626, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 628, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
627, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265,
265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 265, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623,
623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 623, 133, 133,
133, 210, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210,
210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210,
210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210,
210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210,
210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210,
210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131,
133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659,
659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 659, 133, 133,
]
__db_pages = _all_ushort(__db_pages)
def _db_pages(index): return intmask(__db_pages[index])

def _db_index(code):
    return _db_pages((_db_pgtbl(code >> 7) << 7) + (code & 127))

def category(code): return lookup_db_category(_db_index(code))
def bidirectional(code): return lookup_db_bidirectional(_db_index(code))
def east_asian_width(code): return lookup_db_east_asian_width(_db_index(code))
def isspace(code): return lookup_db_flags(_db_index(code)) & 1 != 0
def isalpha(code): return lookup_db_flags(_db_index(code)) & 2 != 0
def islinebreak(code): return lookup_db_flags(_db_index(code)) & 4 != 0
def isnumeric(code): return lookup_db_flags(_db_index(code)) & 64 != 0
def isdigit(code): return lookup_db_flags(_db_index(code)) & 128 != 0
def isdecimal(code): return lookup_db_flags(_db_index(code)) & 256 != 0
def isalnum(code): return lookup_db_flags(_db_index(code)) & 66 != 0
def isupper(code): return lookup_db_flags(_db_index(code)) & 8 != 0
def istitle(code): return lookup_db_flags(_db_index(code)) & 16 != 0
def islower(code): return lookup_db_flags(_db_index(code)) & 32 != 0
def iscased(code): return lookup_db_flags(_db_index(code)) & 56 != 0
def isxidstart(code): return lookup_db_flags(_db_index(code)) & 1024 != 0
def isxidcontinue(code): return lookup_db_flags(_db_index(code)) & 2048 != 0
def isprintable(code): return lookup_db_flags(_db_index(code)) & 4096 != 0
def mirrored(code): return lookup_db_flags(_db_index(code)) & 512 != 0
def iscaseignorable(code): return lookup_db_flags(_db_index(code)) & 8192 != 0

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


__named_sequences = [
'\xc4\x80\xcc\x80',
'\xc4\x81\xcc\x80',
'E\xcc\xa9',
'e\xcc\xa9',
'\xc3\x88\xcc\xa9',
'\xc3\xa8\xcc\xa9',
'\xc3\x89\xcc\xa9',
'\xc3\xa9\xcc\xa9',
'\xc3\x8a\xcc\x84',
'\xc3\xaa\xcc\x84',
'\xc3\x8a\xcc\x8c',
'\xc3\xaa\xcc\x8c',
'\xc4\xaa\xcc\x80',
'\xc4\xab\xcc\x80',
'i\xcc\x87\xcc\x81',
'n\xcd\xa0g',
'O\xcc\xa9',
'o\xcc\xa9',
'\xc3\x92\xcc\xa9',
'\xc3\xb2\xcc\xa9',
'\xc3\x93\xcc\xa9',
'\xc3\xb3\xcc\xa9',
'S\xcc\xa9',
's\xcc\xa9',
'\xc5\xaa\xcc\x80',
'\xc5\xab\xcc\x80',
'\xc4\x84\xcc\x81',
'\xc4\x85\xcc\x81',
'\xc4\x84\xcc\x83',
'\xc4\x85\xcc\x83',
'\xc4\x98\xcc\x81',
'\xc4\x99\xcc\x81',
'\xc4\x98\xcc\x83',
'\xc4\x99\xcc\x83',
'\xc4\x96\xcc\x81',
'\xc4\x97\xcc\x81',
'\xc4\x96\xcc\x83',
'\xc4\x97\xcc\x83',
'i\xcc\x87\xcc\x80',
'i\xcc\x87\xcc\x83',
'\xc4\xae\xcc\x81',
'\xc4\xaf\xcc\x87\xcc\x81',
'\xc4\xae\xcc\x83',
'\xc4\xaf\xcc\x87\xcc\x83',
'J\xcc\x83',
'j\xcc\x87\xcc\x83',
'L\xcc\x83',
'l\xcc\x83',
'M\xcc\x83',
'm\xcc\x83',
'R\xcc\x83',
'r\xcc\x83',
'\xc5\xb2\xcc\x81',
'\xc5\xb3\xcc\x81',
'\xc5\xb2\xcc\x83',
'\xc5\xb3\xcc\x83',
'\xc5\xaa\xcc\x81',
'\xc5\xab\xcc\x81',
'\xc5\xaa\xcc\x83',
'\xc5\xab\xcc\x83',
'\xe0\xae\x95\xe0\xaf\x8d',
'\xe0\xae\x99\xe0\xaf\x8d',
'\xe0\xae\x9a\xe0\xaf\x8d',
'\xe0\xae\x9e\xe0\xaf\x8d',
'\xe0\xae\x9f\xe0\xaf\x8d',
'\xe0\xae\xa3\xe0\xaf\x8d',
'\xe0\xae\xa4\xe0\xaf\x8d',
'\xe0\xae\xa8\xe0\xaf\x8d',
'\xe0\xae\xaa\xe0\xaf\x8d',
'\xe0\xae\xae\xe0\xaf\x8d',
'\xe0\xae\xaf\xe0\xaf\x8d',
'\xe0\xae\xb0\xe0\xaf\x8d',
'\xe0\xae\xb2\xe0\xaf\x8d',
'\xe0\xae\xb5\xe0\xaf\x8d',
'\xe0\xae\xb4\xe0\xaf\x8d',
'\xe0\xae\xb3\xe0\xaf\x8d',
'\xe0\xae\xb1\xe0\xaf\x8d',
'\xe0\xae\xa9\xe0\xaf\x8d',
'\xe0\xae\x9c\xe0\xaf\x8d',
'\xe0\xae\xb6\xe0\xaf\x8d',
'\xe0\xae\xb7\xe0\xaf\x8d',
'\xe0\xae\xb8\xe0\xaf\x8d',
'\xe0\xae\xb9\xe0\xaf\x8d',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x8d',
'\xe0\xae\x95\xe0\xae\xbe',
'\xe0\xae\x95\xe0\xae\xbf',
'\xe0\xae\x95\xe0\xaf\x80',
'\xe0\xae\x95\xe0\xaf\x81',
'\xe0\xae\x95\xe0\xaf\x82',
'\xe0\xae\x95\xe0\xaf\x86',
'\xe0\xae\x95\xe0\xaf\x87',
'\xe0\xae\x95\xe0\xaf\x88',
'\xe0\xae\x95\xe0\xaf\x8a',
'\xe0\xae\x95\xe0\xaf\x8b',
'\xe0\xae\x95\xe0\xaf\x8c',
'\xe0\xae\x99\xe0\xae\xbe',
'\xe0\xae\x99\xe0\xae\xbf',
'\xe0\xae\x99\xe0\xaf\x80',
'\xe0\xae\x99\xe0\xaf\x81',
'\xe0\xae\x99\xe0\xaf\x82',
'\xe0\xae\x99\xe0\xaf\x86',
'\xe0\xae\x99\xe0\xaf\x87',
'\xe0\xae\x99\xe0\xaf\x88',
'\xe0\xae\x99\xe0\xaf\x8a',
'\xe0\xae\x99\xe0\xaf\x8b',
'\xe0\xae\x99\xe0\xaf\x8c',
'\xe0\xae\x9a\xe0\xae\xbe',
'\xe0\xae\x9a\xe0\xae\xbf',
'\xe0\xae\x9a\xe0\xaf\x80',
'\xe0\xae\x9a\xe0\xaf\x81',
'\xe0\xae\x9a\xe0\xaf\x82',
'\xe0\xae\x9a\xe0\xaf\x86',
'\xe0\xae\x9a\xe0\xaf\x87',
'\xe0\xae\x9a\xe0\xaf\x88',
'\xe0\xae\x9a\xe0\xaf\x8a',
'\xe0\xae\x9a\xe0\xaf\x8b',
'\xe0\xae\x9a\xe0\xaf\x8c',
'\xe0\xae\x9e\xe0\xae\xbe',
'\xe0\xae\x9e\xe0\xae\xbf',
'\xe0\xae\x9e\xe0\xaf\x80',
'\xe0\xae\x9e\xe0\xaf\x81',
'\xe0\xae\x9e\xe0\xaf\x82',
'\xe0\xae\x9e\xe0\xaf\x86',
'\xe0\xae\x9e\xe0\xaf\x87',
'\xe0\xae\x9e\xe0\xaf\x88',
'\xe0\xae\x9e\xe0\xaf\x8a',
'\xe0\xae\x9e\xe0\xaf\x8b',
'\xe0\xae\x9e\xe0\xaf\x8c',
'\xe0\xae\x9f\xe0\xae\xbe',
'\xe0\xae\x9f\xe0\xae\xbf',
'\xe0\xae\x9f\xe0\xaf\x80',
'\xe0\xae\x9f\xe0\xaf\x81',
'\xe0\xae\x9f\xe0\xaf\x82',
'\xe0\xae\x9f\xe0\xaf\x86',
'\xe0\xae\x9f\xe0\xaf\x87',
'\xe0\xae\x9f\xe0\xaf\x88',
'\xe0\xae\x9f\xe0\xaf\x8a',
'\xe0\xae\x9f\xe0\xaf\x8b',
'\xe0\xae\x9f\xe0\xaf\x8c',
'\xe0\xae\xa3\xe0\xae\xbe',
'\xe0\xae\xa3\xe0\xae\xbf',
'\xe0\xae\xa3\xe0\xaf\x80',
'\xe0\xae\xa3\xe0\xaf\x81',
'\xe0\xae\xa3\xe0\xaf\x82',
'\xe0\xae\xa3\xe0\xaf\x86',
'\xe0\xae\xa3\xe0\xaf\x87',
'\xe0\xae\xa3\xe0\xaf\x88',
'\xe0\xae\xa3\xe0\xaf\x8a',
'\xe0\xae\xa3\xe0\xaf\x8b',
'\xe0\xae\xa3\xe0\xaf\x8c',
'\xe0\xae\xa4\xe0\xae\xbe',
'\xe0\xae\xa4\xe0\xae\xbf',
'\xe0\xae\xa4\xe0\xaf\x80',
'\xe0\xae\xa4\xe0\xaf\x81',
'\xe0\xae\xa4\xe0\xaf\x82',
'\xe0\xae\xa4\xe0\xaf\x86',
'\xe0\xae\xa4\xe0\xaf\x87',
'\xe0\xae\xa4\xe0\xaf\x88',
'\xe0\xae\xa4\xe0\xaf\x8a',
'\xe0\xae\xa4\xe0\xaf\x8b',
'\xe0\xae\xa4\xe0\xaf\x8c',
'\xe0\xae\xa8\xe0\xae\xbe',
'\xe0\xae\xa8\xe0\xae\xbf',
'\xe0\xae\xa8\xe0\xaf\x80',
'\xe0\xae\xa8\xe0\xaf\x81',
'\xe0\xae\xa8\xe0\xaf\x82',
'\xe0\xae\xa8\xe0\xaf\x86',
'\xe0\xae\xa8\xe0\xaf\x87',
'\xe0\xae\xa8\xe0\xaf\x88',
'\xe0\xae\xa8\xe0\xaf\x8a',
'\xe0\xae\xa8\xe0\xaf\x8b',
'\xe0\xae\xa8\xe0\xaf\x8c',
'\xe0\xae\xaa\xe0\xae\xbe',
'\xe0\xae\xaa\xe0\xae\xbf',
'\xe0\xae\xaa\xe0\xaf\x80',
'\xe0\xae\xaa\xe0\xaf\x81',
'\xe0\xae\xaa\xe0\xaf\x82',
'\xe0\xae\xaa\xe0\xaf\x86',
'\xe0\xae\xaa\xe0\xaf\x87',
'\xe0\xae\xaa\xe0\xaf\x88',
'\xe0\xae\xaa\xe0\xaf\x8a',
'\xe0\xae\xaa\xe0\xaf\x8b',
'\xe0\xae\xaa\xe0\xaf\x8c',
'\xe0\xae\xae\xe0\xae\xbe',
'\xe0\xae\xae\xe0\xae\xbf',
'\xe0\xae\xae\xe0\xaf\x80',
'\xe0\xae\xae\xe0\xaf\x81',
'\xe0\xae\xae\xe0\xaf\x82',
'\xe0\xae\xae\xe0\xaf\x86',
'\xe0\xae\xae\xe0\xaf\x87',
'\xe0\xae\xae\xe0\xaf\x88',
'\xe0\xae\xae\xe0\xaf\x8a',
'\xe0\xae\xae\xe0\xaf\x8b',
'\xe0\xae\xae\xe0\xaf\x8c',
'\xe0\xae\xaf\xe0\xae\xbe',
'\xe0\xae\xaf\xe0\xae\xbf',
'\xe0\xae\xaf\xe0\xaf\x80',
'\xe0\xae\xaf\xe0\xaf\x81',
'\xe0\xae\xaf\xe0\xaf\x82',
'\xe0\xae\xaf\xe0\xaf\x86',
'\xe0\xae\xaf\xe0\xaf\x87',
'\xe0\xae\xaf\xe0\xaf\x88',
'\xe0\xae\xaf\xe0\xaf\x8a',
'\xe0\xae\xaf\xe0\xaf\x8b',
'\xe0\xae\xaf\xe0\xaf\x8c',
'\xe0\xae\xb0\xe0\xae\xbe',
'\xe0\xae\xb0\xe0\xae\xbf',
'\xe0\xae\xb0\xe0\xaf\x80',
'\xe0\xae\xb0\xe0\xaf\x81',
'\xe0\xae\xb0\xe0\xaf\x82',
'\xe0\xae\xb0\xe0\xaf\x86',
'\xe0\xae\xb0\xe0\xaf\x87',
'\xe0\xae\xb0\xe0\xaf\x88',
'\xe0\xae\xb0\xe0\xaf\x8a',
'\xe0\xae\xb0\xe0\xaf\x8b',
'\xe0\xae\xb0\xe0\xaf\x8c',
'\xe0\xae\xb2\xe0\xae\xbe',
'\xe0\xae\xb2\xe0\xae\xbf',
'\xe0\xae\xb2\xe0\xaf\x80',
'\xe0\xae\xb2\xe0\xaf\x81',
'\xe0\xae\xb2\xe0\xaf\x82',
'\xe0\xae\xb2\xe0\xaf\x86',
'\xe0\xae\xb2\xe0\xaf\x87',
'\xe0\xae\xb2\xe0\xaf\x88',
'\xe0\xae\xb2\xe0\xaf\x8a',
'\xe0\xae\xb2\xe0\xaf\x8b',
'\xe0\xae\xb2\xe0\xaf\x8c',
'\xe0\xae\xb5\xe0\xae\xbe',
'\xe0\xae\xb5\xe0\xae\xbf',
'\xe0\xae\xb5\xe0\xaf\x80',
'\xe0\xae\xb5\xe0\xaf\x81',
'\xe0\xae\xb5\xe0\xaf\x82',
'\xe0\xae\xb5\xe0\xaf\x86',
'\xe0\xae\xb5\xe0\xaf\x87',
'\xe0\xae\xb5\xe0\xaf\x88',
'\xe0\xae\xb5\xe0\xaf\x8a',
'\xe0\xae\xb5\xe0\xaf\x8b',
'\xe0\xae\xb5\xe0\xaf\x8c',
'\xe0\xae\xb4\xe0\xae\xbe',
'\xe0\xae\xb4\xe0\xae\xbf',
'\xe0\xae\xb4\xe0\xaf\x80',
'\xe0\xae\xb4\xe0\xaf\x81',
'\xe0\xae\xb4\xe0\xaf\x82',
'\xe0\xae\xb4\xe0\xaf\x86',
'\xe0\xae\xb4\xe0\xaf\x87',
'\xe0\xae\xb4\xe0\xaf\x88',
'\xe0\xae\xb4\xe0\xaf\x8a',
'\xe0\xae\xb4\xe0\xaf\x8b',
'\xe0\xae\xb4\xe0\xaf\x8c',
'\xe0\xae\xb3\xe0\xae\xbe',
'\xe0\xae\xb3\xe0\xae\xbf',
'\xe0\xae\xb3\xe0\xaf\x80',
'\xe0\xae\xb3\xe0\xaf\x81',
'\xe0\xae\xb3\xe0\xaf\x82',
'\xe0\xae\xb3\xe0\xaf\x86',
'\xe0\xae\xb3\xe0\xaf\x87',
'\xe0\xae\xb3\xe0\xaf\x88',
'\xe0\xae\xb3\xe0\xaf\x8a',
'\xe0\xae\xb3\xe0\xaf\x8b',
'\xe0\xae\xb3\xe0\xaf\x8c',
'\xe0\xae\xb1\xe0\xae\xbe',
'\xe0\xae\xb1\xe0\xae\xbf',
'\xe0\xae\xb1\xe0\xaf\x80',
'\xe0\xae\xb1\xe0\xaf\x81',
'\xe0\xae\xb1\xe0\xaf\x82',
'\xe0\xae\xb1\xe0\xaf\x86',
'\xe0\xae\xb1\xe0\xaf\x87',
'\xe0\xae\xb1\xe0\xaf\x88',
'\xe0\xae\xb1\xe0\xaf\x8a',
'\xe0\xae\xb1\xe0\xaf\x8b',
'\xe0\xae\xb1\xe0\xaf\x8c',
'\xe0\xae\xa9\xe0\xae\xbe',
'\xe0\xae\xa9\xe0\xae\xbf',
'\xe0\xae\xa9\xe0\xaf\x80',
'\xe0\xae\xa9\xe0\xaf\x81',
'\xe0\xae\xa9\xe0\xaf\x82',
'\xe0\xae\xa9\xe0\xaf\x86',
'\xe0\xae\xa9\xe0\xaf\x87',
'\xe0\xae\xa9\xe0\xaf\x88',
'\xe0\xae\xa9\xe0\xaf\x8a',
'\xe0\xae\xa9\xe0\xaf\x8b',
'\xe0\xae\xa9\xe0\xaf\x8c',
'\xe0\xae\x9c\xe0\xae\xbe',
'\xe0\xae\x9c\xe0\xae\xbf',
'\xe0\xae\x9c\xe0\xaf\x80',
'\xe0\xae\x9c\xe0\xaf\x81',
'\xe0\xae\x9c\xe0\xaf\x82',
'\xe0\xae\x9c\xe0\xaf\x86',
'\xe0\xae\x9c\xe0\xaf\x87',
'\xe0\xae\x9c\xe0\xaf\x88',
'\xe0\xae\x9c\xe0\xaf\x8a',
'\xe0\xae\x9c\xe0\xaf\x8b',
'\xe0\xae\x9c\xe0\xaf\x8c',
'\xe0\xae\xb6\xe0\xae\xbe',
'\xe0\xae\xb6\xe0\xae\xbf',
'\xe0\xae\xb6\xe0\xaf\x80',
'\xe0\xae\xb6\xe0\xaf\x81',
'\xe0\xae\xb6\xe0\xaf\x82',
'\xe0\xae\xb6\xe0\xaf\x86',
'\xe0\xae\xb6\xe0\xaf\x87',
'\xe0\xae\xb6\xe0\xaf\x88',
'\xe0\xae\xb6\xe0\xaf\x8a',
'\xe0\xae\xb6\xe0\xaf\x8b',
'\xe0\xae\xb6\xe0\xaf\x8c',
'\xe0\xae\xb7\xe0\xae\xbe',
'\xe0\xae\xb7\xe0\xae\xbf',
'\xe0\xae\xb7\xe0\xaf\x80',
'\xe0\xae\xb7\xe0\xaf\x81',
'\xe0\xae\xb7\xe0\xaf\x82',
'\xe0\xae\xb7\xe0\xaf\x86',
'\xe0\xae\xb7\xe0\xaf\x87',
'\xe0\xae\xb7\xe0\xaf\x88',
'\xe0\xae\xb7\xe0\xaf\x8a',
'\xe0\xae\xb7\xe0\xaf\x8b',
'\xe0\xae\xb7\xe0\xaf\x8c',
'\xe0\xae\xb8\xe0\xae\xbe',
'\xe0\xae\xb8\xe0\xae\xbf',
'\xe0\xae\xb8\xe0\xaf\x80',
'\xe0\xae\xb8\xe0\xaf\x81',
'\xe0\xae\xb8\xe0\xaf\x82',
'\xe0\xae\xb8\xe0\xaf\x86',
'\xe0\xae\xb8\xe0\xaf\x87',
'\xe0\xae\xb8\xe0\xaf\x88',
'\xe0\xae\xb8\xe0\xaf\x8a',
'\xe0\xae\xb8\xe0\xaf\x8b',
'\xe0\xae\xb8\xe0\xaf\x8c',
'\xe0\xae\xb9\xe0\xae\xbe',
'\xe0\xae\xb9\xe0\xae\xbf',
'\xe0\xae\xb9\xe0\xaf\x80',
'\xe0\xae\xb9\xe0\xaf\x81',
'\xe0\xae\xb9\xe0\xaf\x82',
'\xe0\xae\xb9\xe0\xaf\x86',
'\xe0\xae\xb9\xe0\xaf\x87',
'\xe0\xae\xb9\xe0\xaf\x88',
'\xe0\xae\xb9\xe0\xaf\x8a',
'\xe0\xae\xb9\xe0\xaf\x8b',
'\xe0\xae\xb9\xe0\xaf\x8c',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xae\xbe',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xae\xbf',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x80',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x81',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x82',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x86',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x87',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x88',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x8a',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x8b',
'\xe0\xae\x95\xe0\xaf\x8d\xe0\xae\xb7\xe0\xaf\x8c',
'\xe0\xae\xb6\xe0\xaf\x8d\xe0\xae\xb0\xe0\xaf\x80',
'\xe1\x83\xa3\xcc\x82',
'\xe1\x9f\x92\xe1\x9e\x80',
'\xe1\x9f\x92\xe1\x9e\x81',
'\xe1\x9f\x92\xe1\x9e\x82',
'\xe1\x9f\x92\xe1\x9e\x83',
'\xe1\x9f\x92\xe1\x9e\x84',
'\xe1\x9f\x92\xe1\x9e\x85',
'\xe1\x9f\x92\xe1\x9e\x86',
'\xe1\x9f\x92\xe1\x9e\x87',
'\xe1\x9f\x92\xe1\x9e\x88',
'\xe1\x9f\x92\xe1\x9e\x89',
'\xe1\x9f\x92\xe1\x9e\x8a',
'\xe1\x9f\x92\xe1\x9e\x8b',
'\xe1\x9f\x92\xe1\x9e\x8c',
'\xe1\x9f\x92\xe1\x9e\x8d',
'\xe1\x9f\x92\xe1\x9e\x8e',
'\xe1\x9f\x92\xe1\x9e\x8f',
'\xe1\x9f\x92\xe1\x9e\x90',
'\xe1\x9f\x92\xe1\x9e\x91',
'\xe1\x9f\x92\xe1\x9e\x92',
'\xe1\x9f\x92\xe1\x9e\x93',
'\xe1\x9f\x92\xe1\x9e\x94',
'\xe1\x9f\x92\xe1\x9e\x95',
'\xe1\x9f\x92\xe1\x9e\x96',
'\xe1\x9f\x92\xe1\x9e\x97',
'\xe1\x9f\x92\xe1\x9e\x98',
'\xe1\x9f\x92\xe1\x9e\x99',
'\xe1\x9f\x92\xe1\x9e\x9a',
'\xe1\x9f\x92\xe1\x9e\x9b',
'\xe1\x9f\x92\xe1\x9e\x9c',
'\xe1\x9f\x92\xe1\x9e\x9d',
'\xe1\x9f\x92\xe1\x9e\x9e',
'\xe1\x9f\x92\xe1\x9e\x9f',
'\xe1\x9f\x92\xe1\x9e\xa0',
'\xe1\x9f\x92\xe1\x9e\xa1',
'\xe1\x9f\x92\xe1\x9e\xa2',
'\xe1\x9f\x92\xe1\x9e\xa7',
'\xe1\x9f\x92\xe1\x9e\xab',
'\xe1\x9f\x92\xe1\x9e\xac',
'\xe1\x9f\x92\xe1\x9e\xaf',
'\xe1\x9e\xbb\xe1\x9f\x86',
'\xe1\x9e\xb6\xe1\x9f\x86',
'\xe3\x87\xb7\xe3\x82\x9a',
'\xcb\xa5\xcb\xa9',
]

def _named_sequences(index): return __named_sequences[index]

def _named_sequence_lengths(index):
    if 14 <= index <= 349:
        return _named_sequence_lengths_middle(index - 14)
    if index < 14:
        return 2
    if index < 394:
        return 2
    raise KeyError

__named_sequence_lengths_middle = (
'\x03\x03\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x03\x03\x02\x03\x02\x03\x02\x03\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x04\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02'
'\x02\x02\x02\x03\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04'
)
def _named_sequence_lengths_middle(index): return ord(__named_sequence_lengths_middle[index])


def lookup_named_sequence(code):
    if 0 <= code - 983552 < 394:
        return _named_sequences(code - 983552)
    else:
        return None

def lookup_named_sequence_length(code):
    if 0 <= code - 983552 < 394:
        return _named_sequence_lengths(code - 983552)
    else:
        return -1

# estimated 0.06 KiB
__name_aliases = [
418, 419, 3294, 3741, 3743, 3747, 3749, 4048, 40981, 65048, 118981,
]
__name_aliases = _all_uint32(__name_aliases)
def _name_aliases(index): return intmask(__name_aliases[index])


def lookup_with_alias(name, with_named_sequence=False):
    code = lookup(name, with_named_sequence=with_named_sequence, with_alias=True)
    if 0 <= code - 983040 < 11:
        return _name_aliases(code - 983040)
    else:
        return code

