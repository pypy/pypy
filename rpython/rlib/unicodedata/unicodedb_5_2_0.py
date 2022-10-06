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
 '\x86\x03A'
 '\xb6<B'
 '\xae2C'
 '\x86\xbd\x02D'
 '\xaa\x17E'
 '\xaaQF'
 '\xda\x05G'
 '\x96:H'
 '\xfeAI'
 '\xa2\x0cJ'
 '\xb2\x12K'
 '\xd6%L'
 '\xc2\x9b\x01M'
 '\xfaaN'
 '\xfa\x1aO'
 '\xea$P'
 '\xc6(R'
 "\x9e'S"
 '\xd6JT'
 '\xc8^\x10YI SYLLABLE ITER'
 '\xd2\rU'
 '\xb2\nV'
 '\xb0\x04\x07QUINCUN'
 '\x93+W'
'\xa4\x03'
 '\xbc\x02\x06EGEAN '
 '\xc6\x08L'
 'T\x05RABIC'
 '\x94,\x07VESTAN '
 '\xe0\xd5\x02\tKTIESELSK'
 '\xf4\xc4\x01\x03FGH'
 '\xb4\x85\x04\x03NCH'
 '\xb8\x03\x04USTR'
 '\xe4\x96\x01\x06C CURR'
 '\x9di\x03TOM'
'r'
 '\xb4\x01\x03DRY'
 '\x00\x06LIQUID'
 '<\x08MEASURE '
 '\x18\x07NUMBER '
 '\xc2\x03W'
 '\xe1\xa6\n\x05CHECK'
'\x02'
 '\xd9\x05\x0b MEASURE FI'
'\x04'
 '\xb6\x05S'
 '\x1fT'
'Z'
 '\\\x05EIGHT'
 '&F'
 '^S'
 ',\x04NINE'
 '"T'
 '\xd3\x99\x05O'
'\x0b'
 '\x86\x93\x05Y'
 '\xbb\xec\x01 '
'\x14'
 '\x12I'
 '#O'
'\n'
 '\x86\x02F'
 '\xeb\x98\x05V'
'\n'
 '\xe6\x01R'
 '\xf5\x98\x05\x02UR'
'\x14'
 '(\x04EVEN'
 '\x01\x02IX'
'\x0b'
 '\x9e\x01T'
 '\xf7\xfc\x06 '
'\x18'
 '"H'
 '.W'
 '\xe3\x90\x05E'
'\n'
 'L\x02IR'
 '\xe9\x98\x05\x02RE'
'\n'
 ' \x02EN'
 '\xf7\x98\x05O'
'\x04'
 '\x0bT'
'\x04'
 '\xbb\x90\x05Y'
'\x0e'
 'd\x06EIGHT '
 '\xf1\x01\x0eORD SEPARATOR '
'\n'
 '6F'
 'BS'
 '\x1eT'
 'A\x05BASE '
'\x04'
 '&I'
 'Y\x05OURTH'
'\x02'
 'U\x03RST'
'\x02'
 '1\x04ECON'
'\x02'
 '\x15\x03HIR'
'\x02'
 '\x0bD'
'\x02'
 '\x19\x04 SUB'
'\x02'
 '\xc9\xc4\t\x02UN'
'\x04'
 '\xce\xa1\nL'
 '\xdb<D'
'\x04'
 '\xa8\xdb\n\x0bTERNATE ONE'
 'Y\x03EMB'
'\xb4\x01'
 '2 '
 '\x89*\x07-INDIC '
'\xac\x01'
 '\x82\x03F'
 'bL'
 '\x9e\x1eR'
 '0\x06INVERT'
 '&S'
 '\xac\x06\x0bVOWEL SIGN '
 '\xf0\xe2\x03\x0bTRIPLE DOT '
 '\xe07\nPOETIC VER'
 '\x80\xeb\x03\x04DATE'
 '\x9cL\x06ZWARAK'
 '\x96PN'
 '\x81N\rMARK NOON GHU'
'\x04'
 '\xec\x1d\tATHA WITH'
 '\xc9\xa1\x08\x07OOTNOTE'
'r'
 '\xc0\x01\x06ETTER '
 '\x9d\x92\n#IGATURE BISMILLAH AR-RAHMAN AR-RAHE'
'p'
 '\xd6\x03A'
 '\x94\x02\x03WAW'
 '\x00\nYEH BARREE'
 '\x9c\x01\tBEH WITH '
 '\xf8\x03\tDAL WITH '
 '\x9e\x02F'
 '\xb6\x03H'
 '\x82\x04K'
 '\xb4\x02\nNOON WITH '
 '\\\tREH WITH '
 'd\nSEEN WITH '
 '\xc0\xfe\x06\x08LAM WITH'
 '\xe5\xe9\x02\x0bMEEM WITH D'
'\n'
 'D\tIN WITH T'
 '\xcd\x01\x03LEF'
'\x06'
 '\xa8\x01\x08WO DOTS '
 '\xd5\xe1\x04\x1bHREE DOTS POINTING DOWNWARD'
'\x04'
 '\xd2\x16V'
 '\xb3\xe5\tA'
'\x04'
 '\xcd\t# WITH EXTENDED ARABIC-INDIC DIGIT T'
'\x0e'
 '\xae\x01T'
 '\xb8\x04\nINVERTED S'
 '\xa0\x03\x10DOT BELOW AND TH'
 '\xb1\n\x05SMALL'
'\x08'
 '\x88\x01\nHREE DOTS '
 '\x8d\xcb\x07\x11WO DOTS BELOW AND'
'\x06'
 '\xa4\x01\x16POINTING UPWARDS BELOW'
 '\xe9\xb2\n\x0cHORIZONTALLY'
'\x05'
 '\xdb\xdb\x04 '
'\x06'
 '\xd0\x01\tINVERTED '
 '\xa55%TWO DOTS VERTICALLY BELOW AND SMALL T'
'\x04'
 '\x1aS'
 '\xfb\xca\nV'
'\x02'
 '\xe1\xb0\n\x06MALL V'
'\x10'
 'p\x0eARSI YEH WITH '
 '\xa1\x02\tEH WITH T'
'\x0c'
 '\x90\x01\x1cEXTENDED ARABIC-INDIC DIGIT '
 'RT'
 '\xa7\nI'
'\x06'
 '\x16T'
 '\xe7\x03F'
'\x04'
 '\x80\xee\x05\x03HRE'
 '\xf9\x83\x04\x02WO'
'\x04'
 '\x1aH'
 '\xeb\xd6\x04W'
'\x02'
 '\xf1\xd6\x04\x03REE'
'\x04'
 '\xe6\x03H'
 '\x8b\xa9\nW'
'\x0e'
 'X\x08AH WITH '
 '\xed\x08\tEH WITH I'
'\x0c'
 '\xf0\x01\x1dEXTENDED ARABIC-INDIC DIGIT F'
 ' \x18SMALL ARABIC LETTER TAH '
 '?T'
'\x02'
 '\xb1\xaa\n\x03OUR'
'\x06'
 '\x1aA'
 '\x93\xaa\nB'
'\x04'
 '\xe2\x07N'
 '\x9f\xe6\tB'
'\x04'
 '\x1aH'
 '\xe3\xd2\x04W'
'\x02'
 '\x9d\x02\nREE DOTS P'
'\x0c'
 '\\\nEHEH WITH '
 '\xb1\xd1\x04\x07AF WITH'
'\n'
 '\x1aT'
 '\x9b\xbf\x07D'
'\x08'
 '@\nHREE DOTS '
 '\xeb\xd0\x04W'
'\x06'
 '&P'
 '\x9a\xeb\tA'
 '\x9f<B'
'\x02'
 '\x8d\xa7\n\x0eOINTING UPWARD'
'\x06'
 '8\x06SMALL '
 '\xe1\xa5\n\x02TW'
'\x04'
 '\xb6*T'
 '\xf3\x95\nV'
'\n'
 'BS'
 '\xf6\x01I'
 '\xda\x01T'
 '\xed\x83\x01\x04HAMZ'
'\x04'
 '\xae\x02M'
 '\xc7\xa8\nT'
'\n'
 '\xd2\x01I'
 '<\x02SM'
 '\x9e\x01T'
 '\x94\xcb\x04\x04FOUR'
 '\xadS\x1fEXTENDED ARABIC-INDIC DIGIT FOU'
'\x02'
 '%\x07NVERTED'
'\x02'
 '\xfb\xef\x08 '
'\x02'
 'i\x18ALL ARABIC LETTER TAH AN'
'\x02'
 '\x0bD'
'\x02'
 '\xed\xa7\n\x04 TWO'
'\x02'
 '-\tWO DOTS V'
'\x02'
 '\x95\xe5\t\tERTICALLY'
'\x04'
 ',\x05EVERS'
 '\xe3\xe1\tA'
'\x02'
 '\xf9\x83\x07\x04ED D'
'\x1e'
 'p\x04IGN '
 '\xb0\x03\x05MALL '
 '\xa9\x8f\x01\nUBSCRIPT A'
'\x10'
 '\x88\x01\x02RA'
 '\x8c\x01\x02SA'
 'p\x07ALAYHE '
 '\x9c\x02\x02MI'
 '\xb5\xf8\x05\x06TAKHAL'
'\x04'
 '\xbc\xd6\x07\x0eHMATULLAH ALAY'
 '\x9d\x15\rDI ALLAHOU AN'
'\x06'
 'l\x12LLALLAHOU ALAYHE W'
 '\xd2 N'
 '\xab\xfa\tF'
'\x02'
 '\xa9\x98\x05\x05ASSAL'
'\x0c'
 'P\x05HIGH '
 '\xa0\x01\x02KA'
 '\xc2\xfd\x06D'
 '\x87\x8f\x02F'
'\x06'
 '\xd2\x1fT'
 '\xb0\xd2\x08\x1dLIGATURE ALEF WITH LAM WITH Y'
 '\x8b}Z'
'\x02'
 '\xf7\x98\nS'
'\x06'
 'T\nINVERTED S'
 '\x02S'
 '\xa5\x99\n\x03DOT'
'\x02'
 '\x85\xdd\t\x06MALL V'
'\x08'
 'P\x04CUBE'
 '\x00\x06FOURTH'
 '!\x04PER '
'\x02'
 '\x9d\xb2\n\x03 RO'
'\x04'
 '\xec\xcf\x06\x03MIL'
 '\xa5\xd3\x03\x0cTEN THOUSAND'
'n'
 '4\x07LETTER '
 '\xbb\xb4\x08A'
'l'
 '\xda\x01A'
 '6G'
 '&H'
 '\x1eN'
 '.X'
 '&S'
 '.Y'
 '\x1eT'
 '\x96iB'
 '\x02D'
 '\x02Z'
 '\x9a\xb9\x08I'
 '\x16U'
 '\xe2ZE'
 '\x12O'
 '\xb2/C'
 '\x02F'
 '\x02J'
 '\x02K'
 '\x02L'
 '\x02M'
 '\x02P'
 '\x02R'
 '\x03V'
'\x11'
 '\xce\xf9\tA'
 '\xde\x05E'
 '\xfa/N'
 '\x03O'
'\x06'
 '\xb6\xae\nG'
 '\x02H'
 ';E'
'\x04'
 '\x92\xae\nM'
 ';E'
'\x0c'
 '*G'
 '\xce\xad\nN'
 '\x02Y'
 ';E'
'\x06'
 '\xca\xad\nV'
 '\x02Y'
 ';E'
'\x08'
 '*H'
 '\xba\xcb\x07S'
 '\xff\xe1\x02E'
'\x04'
 '\xfa\xac\nY'
 ';E'
'\x06'
 '\xde\xac\nH'
 '\x02T'
 ';E'
'\xa2\x04'
 '\xc6\x02A'
 '\x8c%\x02EN'
 '\xe0\x01\x05LACK '
 '\xee\x03O'
 'l\x08UGINESE '
 '\xdd\xab\t0YZANTINE MUSICAL SYMBOL FTHORA SKLIRON CHROMA VA'
'\xa4\x03'
 'X\x07LINESE '
 '\xc0\x17\x04MUM '
 '\x8d\xb5\x08\x02SE'
'\xf2\x01'
 '\xbc\x02\x06CARIK '
 'l\x07LETTER '
 '\xbc\x08\x0fMUSICAL SYMBOL '
 '\xbc\x06\x02PA'
 'D\x05SIGN '
 '\xd0\x01\x0bVOWEL SIGN '
 '\xbc\xdb\x04\x05ADEG '
 '\xfe\xf5\x02W'
 '\xb3\x85\x02D'
'\x06'
 '(\x02PA'
 '\x89\xa4\x06\x02SI'
'\x04'
 '\xe4\x10\x05MUNGK'
 '\xbd\xd9\t\x03RER'
'l'
 '\xa2\x02A'
 'H\x02BA'
 '$\x02CA'
 '$\x02DA'
 'nE'
 ' \x02GA'
 '\x1eI'
 '\x02O'
 '\x02U'
 '$\x02JA'
 '"K'
 'D\x02LA'
 '\x12N'
 'H\x02PA'
 '$\x02RA'
 '\x10\x02SA'
 '6T'
 '|\x02VE'
 '\x00\x03ZAL'
 '\xf2\x86\nH'
 '\x02M'
 '\x02W'
 '\x03Y'
'\x08'
 '\xc2\x02K'
 '\xb8\x03\x05SYURA'
 '\xc1\x82\n\x02IK'
'\x05'
 '\x89\xdc\x04\x04 KEM'
'\x05'
 '\xfd\x8b\n\x04 LAC'
'\t'
 '\x11\x02 M'
'\x06'
 ',\x05URDA '
 '\xe3\xde\x07A'
'\x04'
 '\x8a\xe6\x04M'
 '\x19\x03ALP'
'\x04'
 '\xfe\x03F'
 '\xc3\x82\nK'
'\x05'
 '\xa9\xe0\t\x02 G'
'\x04'
 '\x0bK'
'\x04'
 '\xc5\x0e\x02AR'
'\x05'
 '\xe9\x85\n\x03 JE'
'\x08'
 '"A'
 '\xdd\x02\x03HOT'
'\x07'
 '\xda\x02F'
 '\xdb\xe1\x04 '
'\x07'
 '\xa3\x0c '
'\x08'
 '"A'
 '\xfa\x88\nG'
 '\x03Y'
'\x05'
 '\x8d\xa6\x08\x04 RAM'
'\x05'
 '\xe5\xd8\t\x04 KAP'
'\x07'
 '\xc7\x0b '
'\x07'
 '\x15\x03 SA'
'\x04'
 '\x86\x88\nG'
 '\x03P'
'\n'
 '\x1eA'
 ']\x03ZIR'
'\t'
 '\x0b '
'\x06'
 '\xb6#T'
 '\xf0\xbe\x04\x06MURDA '
 '\xd1\x07\x03LAT'
'\x02'
 '\xd1\xde\x04\x02 S'
'8'
 '\xa8\x01\nCOMBINING '
 '\xf2\x01D'
 '\xa8\x01\nLEFT-HAND '
 'u\x0bRIGHT-HAND '
'\x12'
 '\x80\x01\x04KEMP'
 'NJ'
 '\xbc\xbb\x08\x03END'
 '\xe4\x1b\x03TEG'
 '\xfa\x95\x01G'
 '\xcd\x1a\x03BEN'
'\x08'
 ' \x02LI'
 '\x01\x02UL'
'\x05'
 '%\x07 WITH J'
'\x02'
 '\xd9\xd8\x04\x03EGO'
'\x14'
 '2A'
 'ZE'
 '\xa2\x8e\nI'
 '\x02O'
 '\x03U'
'\n'
 '(\x02NG'
 '\xce\x8e\nE'
 '\x03I'
'\x07'
 '\x0b '
'\x04'
 '\xf6\x03S'
 '\xef\xd8\x03G'
'\x04'
 '\x9e\x8e\nU'
 '\x0fN'
'\n'
 'L\x06OPEN P'
 'q\tCLOSED PL'
'\x06'
 '\xb2\x8d\nA'
 '\x02I'
 '\x03U'
'\x08'
 'H\x08CLOSED T'
 '\x1d\x06OPEN D'
'\x04'
 '\xda\xf6\tA'
 '\x03U'
'\x04'
 '\xb2\x8c\nA'
 '\x03U'
'\x06'
 '\x1aM'
 '\xdf\x8e\x06N'
'\x04'
 '\xa6\xd1\tA'
 '\xbd\x18\x02EN'
'\x0c'
 'h\x03BIS'
 '\x16S'
 '\x14\x04ULU '
 '\x82\xd3\x08C'
 '\xd1\xb7\x01\x05REREK'
'\x02'
 '\x87\x84\nA'
'\x02'
 '\xbb\xd9\x07U'
'\x04'
 '\xf8\xcf\t\x03RIC'
 '\xa1*\x04CAND'
'\x1e'
 'x\x03LA '
 ' \x03RA '
 '\x0c\x04SUKU'
 '"T'
 'h\x05PEPET'
 '5\x03ULU'
'\x04'
 '\xa5\x01\x04LENG'
'\x04'
 'sR'
'\x05'
 '\xc5\x94\t\x03 IL'
'\n'
 '$\x05ALING'
 'cE'
'\t'
 '\x0b '
'\x06'
 '\x12R'
 '7T'
'\x04'
 '\x11\x02EP'
'\x04'
 '\x0bA'
'\x05'
 '\x11\x02 T'
'\x02'
 '\x0bE'
'\x02'
 '\xb7\xd1\x08D'
'\x05'
 '\xd5\x8d\x06\x03 SA'
'\xb0\x01'
 '\x88\x01\x02CO'
 '\xb8\x01\x07LETTER '
 '\x80\xcd\x03\x05NJAEM'
 '\x9a\x99\x04S'
 '\xe6\xed\x01F'
 'SQ'
'\x08'
 '\x1aM'
 '\xab\x8a\nL'
'\x06'
 'H\x0cBINING MARK '
 '\x8b\xf9\tM'
'\x04'
 '\x90\xbd\t\x07TUKWENT'
 '\xc9L\x05KOQND'
'\xa0\x01'
 '\x9e\x01F'
 'FK'
 '\xa6\x01L'
 'JM'
 '~N'
 '\xfe\x01P'
 'jR'
 'rS'
 '\x8e\x01T'
 'JY'
 '\xfe%W'
 '\x96\xdf\tE'
 ':A'
 '\x02I'
 '\x02O'
 '\x03U'
'\x08'
 '\xc4\xc6\x03\x03AAM'
 '\xfa\xc3\x06O'
 '\xa6\x03E'
 ';U'
'\x16'
 'JE'
 '*O'
 '\xf6\xd0\tY'
 '\xea$P'
 '\x8a\x17A'
 '\x02I'
 '\x03U'
'\x06'
 '\xe6\xd0\tU'
 '\xa6<N'
 '\x03T'
'\x07'
 '\xb6\xeb\x08V'
 '\xd1\x9d\x01\x03GHO'
'\n'
 '\x9e\x98\x08O'
 '\xa4\xb8\x01\x02EE'
 '\xf2;A'
 '\x02I'
 '\x03U'
'\x13'
 ':B'
 '"E'
 '\x92\x8b\nA'
 '\x02I'
 '\x02O'
 '\x03U'
'\x04'
 '\xa6\xf4\tA'
 '\xe3\x10E'
'\x04'
 '\x9e\xcf\tE'
 '\xf3;N'
'\x1e'
 '^G'
 ':J'
 '2T'
 '"U'
 '\xaa\xea\x08D'
 '\xdeqY'
 '\xbe\x11S'
 '\xca\x1bA'
 '\x03I'
'\x06'
 '\xd8\xcd\t\x03KWA'
 '\xae%G'
 '\x8b\x17A'
'\x06'
 '\x82\xc2\x03U'
 '\x8a\x82\x06A'
 '\x97EE'
'\x04'
 '\xde\xc4\tU'
 '\x93DE'
'\x05'
 '\xcf\x88\nA'
'\x0c'
 '*E'
 '"U'
 '\xaa\x88\nA'
 '\x03I'
'\x04'
 '\xa2\xcc\tU'
 '\xa7<E'
'\x04'
 '\xee\x87\nA'
 ';E'
'\x0e'
 '*E'
 '*I'
 '\x82\x87\nA'
 ';U'
'\x06'
 '\xba\xcb\tU'
 '\xa6<E'
 '\x03N'
'\x04'
 '\xfe\x86\nE'
 ';I'
'\x10'
 'FH'
 '2E'
 '\xf8\x87\x07\x02AM'
 '\xe6\xb9\x02U'
 '\xcbDI'
'\x08'
 '.E'
 '\xa2\xd9\tI'
 '\x86-O'
 '\x03U'
'\x02'
 '\xff\xc9\tU'
'\n'
 '*E'
 '\xba\xe5\x06A'
 '\xaf\xa0\x03I'
'\x04'
 '\xe2\x85\nN'
 '\x03T'
'\x06'
 '\xb2\x91\x08O'
 '\x02U'
 '\x97\xf4\x01A'
'\x08'
 'd\x05GALI '
 '\xa1\xa8\x06\x0eZENE RING WITH'
'\x06'
 '\xa4\x80\x06\rLETTER KHANDA'
 '\xf6\x1fS'
 '\xe1\xa9\x03\x05GANDA'
','
 '\xbe\x01L'
 'RM'
 'vS'
 'BT'
 '\xca\x8f\x01F'
 '\xe4\xbb\x06\rCROSS ON SHIE'
 '\xf0\xa8\x02\x02DR'
 '\x9e\x02H'
 '\x9a\x02R'
 'JP'
 '\xe3\x04V'
'\x06'
 ',\x05ARGE '
 '\xfb\xf8\tE'
'\x04'
 '\x9a\x8c\tC'
 '\xcftS'
'\x06'
 'P\x06EDIUM '
 '\xe5\xee\t\x08OON LILI'
'\x04'
 '\xf6\xf8\tD'
 '\xdf\x01L'
'\x08'
 '\xfc\x85\x08\x03NOW'
 '\xad\xf2\x01\x04MALL'
'\x04'
 '\xa8\x8d\t\x02RU'
 '\xcfoW'
'\x0c'
 '\x84\xab\t\x04TTOM'
 '\xe1B\x0fPOMOFO LETTER I'
'<'
 '\xa4\x01\x07LETTER '
 '\xac\x02\x04PALL'
 '\x14\x0bVOWEL SIGN '
 '\xe9\x9a\x03\x07END OF '
'.'
 '\x9a\x01M'
 '"N'
 '\xfa\xe4\tB'
 '\x02C'
 '\x02D'
 '\x02G'
 '\x02H'
 '\x02J'
 '\x02K'
 '\x02L'
 '\x02P'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x02V'
 '\x02Y'
 '\x8b\x17A'
'\x04'
 '\x96\xe5\tP'
 '\x8b\x17A'
'\x0c'
 '.G'
 '"Y'
 '\xaa\xe4\tR'
 '\x8b\x17A'
'\x04'
 '\xc6\xe4\tK'
 '\x8b\x17A'
'\x04'
 '\xa6\xe4\tC'
 '\x8b\x17A'
'\x02'
 '\xeb\xdc\x06A'
'\n'
 '\xc2\xfa\tA'
 ':E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x86\x1c'
 '\xa6\x01A'
 '\x96\x12E'
 '&H'
 '\xc8\t\x07IRCLED '
 '\x88\x07\x03JK '
 '\xce\x06O'
 '\xfc/\x04ROSS'
 '\x92\x02U'
 '\xbb\xca\x01Y'
'\x86\x02'
 'p\x11NADIAN SYLLABICS '
 '\xfe\x0cR'
 '\x99\xe8\t\x02ST'
'\xa0\x01'
 '\xfe\x01A'
 '"B'
 'l\x08CARRIER '
 '\x8c\x01\x06FINAL '
 'RK'
 '&N'
 '*O'
 '\xae\x01R'
 '~S'
 'vP'
 '*T'
 '\x9e\x01W'
 '\xa8\x01\x05EASTE'
 '\xa2\x01Y'
 '\xee\xc4\x02H'
 '\xb6\xc4\x05L'
 '\x03M'
'\x04'
 '\x9e\x9d\tA'
 '\x83YY'
'\x06'
 '\xac\t\x08LACKFOOT'
 '\xd1\x96\x01\x0bEAVER DENE '
'\x0c'
 ',\x03DEN'
 ':G'
 '\x8b\xd6\x06J'
'\x04'
 '\xb8\xa6\t\x03TAL'
 '\xb9\x12\x03E G'
'\x06'
 '\xd2\x8c\x07W'
 '\xd3\xd0\x02A'
'\x04'
 '\xd8\x83\t\x06SMALL '
 '\x81p\x06RAISED'
'\x04'
 '\x92\x91\x08W'
 '\xa7\x89\x01A'
'\x0c'
 '\xb2\x01W'
 '\xe2\x98\tA'
 '\x03O'
'\x1a'
 '4\x07JIBWAY '
 '\xb7\xf2\tY'
'\x18'
 'FN'
 '\x86\x98\tS'
 '\xeaYC'
 '\x02K'
 '\x02M'
 '\x02P'
 '\x03T'
'\x0b'
 '\x0bW'
'\x08'
 '\xf2\xe6\x08I'
 '\x87[O'
'\x10'
 'FW'
 '\xb0\xf1\x05\x07-CREE R'
 '\xcb\xa6\x03A'
'\x0c'
 '\x8a\xe6\x08I'
 '\x86[O'
 '\xb2/E'
 ';A'
'\x12'
 '(\x02AY'
 'JH'
 '\xd3\x96\tO'
'\x0b'
 '\x19\x04ISI '
'\x08'
 '\x96\x01S'
 '\xba\xcd\x08J'
 '\x87pH'
'\x06'
 '\xba\xfd\x08W'
 '\x96\x19A'
 '\x03O'
'\x10'
 'BL'
 ',\x02TH'
 '\x8c\xce\x06\x02HW'
 '\xaf\xc7\x02A'
'\x04'
 '\x0bH'
'\x04'
 '\xe6\xc0\tO'
 '\xbb-W'
'\x06'
 '\xc6\xc0\tO'
 '\xea\x16A'
 '\xd3\x16W'
'\x18'
 'T\x03EST'
 'x\nOODS-CREE '
 '\xbf\x93\tA'
'\x06'
 ',\x07-CREE L'
 '#E'
'\x04'
 '\x92\xbf\tO'
 '\xeb\x16A'
'\x02'
 '\x11\x02RN'
'\x02'
 '\xf3\xd2\t '
'\x10'
 '<\x03THW'
 '\x89\xda\t\x06FINAL '
'\x0e'
 '\xd6\xd4\x08A'
 '\xba\x0cI'
 '\x86[O'
 '\xb3/E'
'\x04'
 '\xc2\x92\tA'
 '\x03O'
'd'
 'T\x0bIAN LETTER '
 '\xb9\x93\x04\x04 SLI'
'b'
 '\xbc\x01\x02C-'
 '&L'
 '\x16M'
 '2N'
 '&S'
 '.T'
 '\x16U'
 '\xda\xf5\x01A'
 '\x02D'
 '\x02E'
 '\x02G'
 '\x02K'
 '\x02P'
 '\x82\xe7\x06I'
 '\x961R'
 '\xdaYB'
 '\x02O'
 '\x02Q'
 '\x03X'
'\x04'
 '\xa2\xb9\x011'
 '\xa7\xe1\x073'
'\x07'
 '\xff\xf6\x01D'
'\x0b'
 '\x0bB'
'\t'
 '\xca\xe8\t2'
 '\x023'
 '\x034'
'\t'
 '\xa6\xe8\tD'
 '\x02G'
 '\x03N'
'\r'
 '\x96\xf6\x01H'
 '\x02T'
 '\xef\xf1\x07S'
'\x07'
 '\xeb\xf5\x01T'
'\r'
 '\x0bU'
'\x0b'
 '\x0bU'
'\t'
 '\xaa\xe7\t2'
 '\x023'
 '\x03U'
'\x04'
 '\xb6\xd0\x03D'
 '\xfb\x9c\x05R'
'\xac\x01'
 '*A'
 '\xfa\xff\x04I'
 '\xbf\x84\x03U'
'\xa8\x01'
 '(\x02M '
 '\xe1\xd4\t\x02IN'
'\xa6\x01'
 '\xec\x01\x0fCONSONANT SIGN '
 't\x07LETTER '
 '\xdc\x04\x0cPUNCTUATION '
 'h\x0bVOWEL SIGN '
 '\xb7\x9f\tD'
'\x0e'
 'H\x06FINAL '
 '\xbe\xcc\tL'
 '\x02R'
 '\x02W'
 '\x03Y'
'\x06'
 '\xba\xd8\tN'
 '\x8a\x0bH'
 '\x03M'
'h'
 '\xea\x01B'
 '*D'
 '(\x06FINAL '
 'jN'
 '.M'
 'FP'
 '*S'
 '\xb8\xb6\x08\x02CH'
 '\x02G'
 '\x02J'
 '\x02K'
 '\x02T'
 '\xbe\x1dA'
 '\xe6sH'
 '\x02L'
 '\x02R'
 '\x02V'
 '\x02Y'
 '\x8a\x17E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x06'
 '\xa6\xca\tB'
 '\x02H'
 '\x8b\x17A'
'\x06'
 '\xfe\xc9\tD'
 '\x02H'
 '\x8b\x17A'
'\x16'
 '\xa2\xbc\x07N'
 '\xd6\x92\x02C'
 'FS'
 '\xa6\x11G'
 '\x02K'
 '\x02L'
 '\x02P'
 '\x02R'
 '\x02T'
 '\x03Y'
'\x0e'
 '*G'
 '\x1eH'
 '\xfa\xde\tU'
 ';A'
'\x04'
 '\x92\xdf\tU'
 ';A'
'\x06'
 '\xa6\xc8\tJ'
 '\xd2\x16U'
 ';A'
'\x06'
 '\xfe\xc7\tH'
 '\x02P'
 '\x8b\x17A'
'\x04'
 '\xd6\xc7\tS'
 '\x8b\x17A'
'\x08'
 'JD'
 '\xe8\xf0\x07\x04TRIP'
 '\x99\xa6\x01\x04SPIR'
'\x04'
 '\xce\xf0\x07O'
 'CA'
'\x14'
 '\xc6\xd2\x08A'
 '&I'
 '\xf6ZO'
 '\x02U'
 '\xf7\x02E'
'('
 '\xda\x01C'
 '6I'
 '\xd0\x02\x11KOREAN CHARACTER '
 'D\x07NUMBER '
 '\xdc\xa4\x06\x0cHANGUL IEUNG'
 '\xc3\xd6\x02W'
'\x04'
 '\xd8=\x05ROSSI'
 '\xe7\x9d\tD'
'\x0c'
 '\xa8\x01\tDEOGRAPH '
 '\x89\x01\x1bTALIC LATIN CAPITAL LETTER '
'\x08'
 'BK'
 '\x8c\xc2\x05\x03SCH'
 '\xa9\xa0\x03\x03QUE'
'\x04'
 '\xb4\xae\x03\x08INDERGAR'
 '\x83\x99\x04O'
'\x04'
 '\xd6\xd8\tC'
 '\x03R'
'\x04'
 '\xe4\xd7\x05\x04CHAM'
 '\xd1\xd3\x03\x04JUEU'
'\x10'
 '2F'
 '\x1eS'
 '&T'
 'U\x04EIGH'
'\x04'
 'rO'
 '!\x02IF'
'\x04'
 '`\x02EV'
 '\x15\x02IX'
'\x06'
 '0\x02HI'
 '\x0eW'
 '\xa5\x83\x02\x02EN'
'\x02'
 '\x1fR'
'\x02'
 '\x11\x02EN'
'\x02'
 '\x8d\x83\x02\x02TY'
'\xa2\x02'
 '\x9c\x01\x1aCOMPATIBILITY IDEOGRAPH-FA'
 '\x81\x02\x07STROKE '
'\xda\x01'
 'J6'
 '&7'
 '\x028'
 '\x029'
 '\x02A'
 '\x02B'
 '\x02C'
 '\xdb\xa8\tD'
'\x06'
 '\x9e\xd4\tB'
 '\x02C'
 '\x03D'
' '
 '\xfa\xd3\t0'
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
'H'
 'nH'
 '\xa6\x01P'
 '&S'
 '\xbe\xa1\tT'
 '\xf4#\x02BX'
 '\x02W'
 '\x02X'
 '\x8a\x0bD'
 '\x02N'
 '\x03Q'
'\x1d'
 '6P'
 '\x16Z'
 '\xac\xc6\t\x02XW'
 '\x8b\x0bG'
'\x05'
 '\xbf\xc6\tW'
'\x13'
 '2Z'
 '\xc6\xac\x07W'
 '\xbe\xa4\x02G'
 '\x03T'
'\t'
 '\xc2\xac\x07Z'
 '\xbf\xa4\x02P'
'\t'
 '\xda\xd0\tD'
 '\x02G'
 '\x03Z'
'\x15'
 '2W'
 '\x1eZ'
 '\xea\xcf\tG'
 '\x02P'
 '\x03T'
'\x07'
 '\x82\xd0\tG'
 '\x03Z'
'\x07'
 '\xde\xc4\tW'
 '\x8b\x0bZ'
'\x96\x04'
 '\x9c\x01\x08MBINING '
 '\x80\x1d\x05PTIC '
 '\x88\x11\x0bUNTING ROD '
 '\xc5\xdb\x08\x02FF'
'\xfe\x01'
 '\xb2\x02A'
 '\xd2\x01C'
 '\\\x06BREVE-'
 '\xfe\x06D'
 '\xec\x03\x02GR'
 '\xc6\x01L'
 '\xd4\x06\x06MACRON'
 '|\x05RIGHT'
 '\xbe\x03S'
 'JU'
 '\xc8\x0f\x04FERM'
 '\x8c\xcb\x08\x06ZIGZAG'
 '<\x06OGONEK'
 '\x92<I'
 '\x0fX'
'\n'
 '\x90\x01\x05CUTE-'
 '\xec\xf3\x08\x07STERISK'
 '\xd9<\x0eLMOST EQUAL TO'
'\x04'
 '\x86\xe4\x04M'
 '\xed"\x07GRAVE-A'
'P'
 'X\nONJOINING '
 '\x15\x08YRILLIC '
'\x02'
 '\xef\xe2\x04M'
'N'
 '\x84\x01\x07LETTER '
 '\xbe\x04P'
 '6T'
 '4\x06HUNDRE'
 '\x8a\xf6\x01K'
 '\xdd\x94\x05\x02VZ'
'@'
 '\xd6\x01B'
 '&D'
 '&E'
 'JI'
 '`\x02SH'
 '"T'
 '\x1eY'
 '\x1eZ'
 '\xa2\x80\x02L'
 'x\x05MONOG'
 '\xf2\xe0\x04C'
 '\x02G'
 '\xde\xca\x02F'
 '\x1aH'
 '\x02K'
 '\xd2\x16P'
 '\x02V'
 ':A'
 '\x03O'
'\x04'
 '\xbe\x85\x03I'
 '\x8f\xc1\x06E'
'\x04'
 '\x8e\xfe\x01J'
 '\x9b\xc8\x07E'
'\x0c'
 '2S'
 '\xd2\xc5\tL'
 '\x02M'
 '\x02N'
 '\x03R'
'\x05'
 '\xf7\xde\x07-'
'\x06'
 '8\x08OTIFIED '
 '\x83\xc5\tE'
'\x04'
 '\xe6\x83\x03B'
 '\x9b\xc1\x06A'
'\x04'
 '\x92\xa9\tC'
 '\xcb\x1bA'
'\x04'
 '\x82\xc4\tS'
 ';E'
'\x04'
 '\x92\xc4\tA'
 '\x0fU'
'\x04'
 '\xca\xc3\tH'
 ';E'
'\x04'
 '\xfa\xf7\x01A'
 '\xe1\x84\x02\x04OKRY'
'\x04'
 '0\x06HOUSAN'
 '\r\x02EN'
'\x02'
 '\x0bD'
'\x02'
 '\xe5\xb9\x07\x07 MILLIO'
'6'
 '<\nEVANAGARI '
 '\x97\x01O'
'$'
 'D\x07LETTER '
 '\xa6\xdd\x05S'
 '\xf7\xa5\x03D'
'\x0e'
 '\xb6\x94\tV'
 '\xfe\x15K'
 '\x02N'
 '\x02P'
 '\x02R'
 '\x8a\x17A'
 '\x03U'
'\x12'
 '&T'
 'Q\x05UBLE '
'\x06'
 '\x9c\x80\x06\x03TED'
 '\xe9\x82\x03\x08 ABOVE R'
'\x0c'
 '\x88\x01\x05BREVE'
 '\x00\x06MACRON'
 '\x9e\xa2\x04R'
 '\xa1\xc6\x04\nCIRCUMFLEX'
'\x05'
 '\xe3\xa4\t '
'\n'
 'P\x04AVE-'
 '9\x0cEEK MUSICAL '
'\x04'
 '\xb2\xd7\x04M'
 '\xc9\x04\x06ACUTE-'
'\x06'
 '\x1aT'
 '\xef\xea\x05P'
'\x04'
 '\xc6\xeb\x05E'
 '#R'
'6'
 '\x90\x01\x05ATIN '
 '\xcc\x04\x03EFT'
 '\x81\xdf\x04\x12ONG DOUBLE SOLIDUS'
'*'
 '\x9c\x01\x15LETTER SMALL CAPITAL '
 '5\rSMALL LETTER '
'\n'
 '\xde\xba\tG'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x03R'
' '
 '\xfa\x01A'
 '$\x0fFLATTENED OPEN '
 '\x16L'
 ' \x02R '
 '\x88\x8c\x04\x06C CEDI'
 '\xde\x99\x05E'
 '\xbc\n\x08INSULAR '
 '\xba\x07G'
 '\x02K'
 '\x02N'
 '\x02S'
 '\x03Z'
'\x06'
 '\xae\xb8\tE'
 '\x02O'
 '\x03V'
'\x02'
 '\xdb\xe1\x08A'
'\x05'
 '\xcd\xe9\x08\x03ONG'
'\x04'
 '\xa6\xe6\x04R'
 '\xb7\xb7\x04B'
'\n'
 '\x16 '
 '\xa3\x04W'
'\x08'
 '(\x05ARROW'
 '\xcf\x03H'
'\x06'
 '\x80\xe0\x08\x04HEAD'
 '\xe7< '
'\n'
 '\x12 '
 'C-'
'\x04'
 ',\x03LEF'
 '\x01\x04RIGH'
'\x02'
 '\x93\x08T'
'\x06'
 '\x8e\xf1\x04G'
 'zA'
 '\xabpB'
'\x0e'
 '\x16 '
 '\xb3\x02W'
'\x0c'
 '(\x05ARROW'
 '\xdf\x01H'
'\n'
 ',\x05HEAD '
 '\xcb\x9a\t '
'\x08'
 '\x1aA'
 '\xbb\x9a\tB'
'\x06'
 '$\x03ND '
 '\x83\xde\x08B'
'\x04'
 '(\x04DOWN'
 '\x01\x02UP'
'\x02'
 '\xc9\x99\t\n ARROWHEAD'
'\x02'
 '\xd9\xdc\x08\x05ALF R'
'\x02'
 '\x8d\xa3\x07\x18ARDS HARPOON WITH BARB D'
'\x04'
 '\xc4\xe2\x04\x03NAK'
 '\xf1\x94\x04\x06USPENS'
'\x04'
 '\x8e\xdb\x08R'
 '\x03S'
'\xf2\x01'
 '\x9e\x01C'
 '\xd2\x01F'
 'd\x0bOLD NUBIAN '
 '\x82\x01S'
 '\x91\xe9\x08\rMORPHOLOGICAL'
'n'
 'L\tOMBINING '
 '\xa1\x03\x05APITA'
'\x06'
 'D\tSPIRITUS '
 '\xb9\xd8\x08\x02NI'
'\x04'
 '\xbc\x8b\x02\x02LE'
 '\xe5\x8c\x07\x03ASP'
'\x04'
 'D\x0bRACTION ONE'
 '\xb3\xf2\x08U'
'\x02'
 '\xb1\xa7\x07\x02 H'
'\x08'
 'ND'
 '\x00\x03IND'
 '\xc0\xe9\x08\x05VERSE'
 '\xfb\x07F'
'\x02'
 '\x85\xf2\x08\x07IRECT Q'
'v'
 '8\x03MAL'
 '\xad\n\x06YMBOL '
'h'
 '-\tL LETTER '
'h'
 '\xf2\x01A'
 'D\x02CR'
 '\xaa\x01D'
 '\xa6\x01K'
 '*L'
 'JO'
 '\x96\x03S'
 '2T'
 '2Z'
 '\xa6\xff\x02P'
 '\xd6[E'
 '\xde)I'
 '\xc2\xe6\x01G'
 '\x82\xd0\x01H'
 '\x88\xa1\x01\x02VI'
 '\xee\x17R'
 'nF'
 '\x02M'
 '\x02N'
 '\xff\x15U'
'\x04'
 '\xf0\xce\x05\x08KHMIMIC '
 '\xcf\x96\x01L'
'\n'
 'd\x0cYPTOGRAMMIC '
 '\xd5\xcd\x05\x07OSSED S'
'\x08'
 '\xa6\x04G'
 '\x9a\xdd\x03E'
 '\x96\xec\x01S'
 '\xeb\xad\x03N'
'\n'
 'D\tIALECT-P '
 '\xdd\xe1\x08\x02AL'
'\x08'
 'FA'
 '\xa0\xa2\x05\x02HO'
 '\x98\xbd\x03\x02KA'
 '\xb7\x1aN'
'\x02'
 '\x8b\xb5\x07L'
'\x06'
 '\xa2\xdf\x08A'
 '\xb6\x1aH'
 '\x03S'
'\x04'
 '\xcc\xe4\x06\x07-SHAPED'
 '\x9d\xfb\x01\x02AU'
'#'
 '$\x03LD '
 '\xff\xe0\x08O'
'\x1e'
 'L\x07COPTIC '
 '\xd1\x01\x07NUBIAN '
'\x16'
 'ZG'
 '&H'
 '0\x02SH'
 '\x8a\x9f\x05D'
 '\x9a.O'
 '\x8a\x96\x02E'
 '\xc7{A'
'\x02'
 '\x8d\x8d\t\x04ANGI'
'\x08'
 '\xa2\x9f\x05O'
 '\xa2\xf1\x02A'
 '\xaffE'
'\x04'
 '\x8e\xe5\x08I'
 '\xb3\x11E'
'\x08'
 '.N'
 '\xc4\x02\x02SH'
 '\xdb\xac\x07W'
'\x04'
 '\xee\xf5\x08G'
 '\x03Y'
'\x06'
 '\xa2\x85\x03A'
 '\xee\xd8\x05O'
 '\x97\x06I'
'\x04'
 '\xa8\xc0\x06\x03HET'
 '\xb7\x9d\x02A'
'\x02'
 '\xe3\x8a\tA'
'\x0e'
 '>K'
 '\x1eM'
 '\x02P'
 '\x16S'
 '\xc5\x93\x05\x03TAU'
'\x04'
 '\x1aH'
 '\x87\xf4\x08A'
'\x02'
 '\xd7\x93\x05I'
'\x04'
 '@\x06HIMA S'
 '\xf5\x82\x07\x04TAUR'
'\x02'
 '\xfb\xe1\x08I'
'$'
 '0\x04TENS'
 '\x01\x04UNIT'
'\x12'
 '\xf9\x97\x07\x02 D'
'\x06'
 ' \x03ED '
 '\xc7\x01I'
'\x04'
 '\xe0\xf4\x03%NEGATIVE SQUARED LATIN CAPITAL LETTER'
 '\x8d\x99\x05\x03SWO'
'\x02'
 '\xb9\xff\x03\x05NG LA'
'\xae\x0f'
 '8\x08NEIFORM '
 '\xdf\xc9\x01P'
'\xac\x0f'
 '\xb0\x01\rNUMERIC SIGN '
 '\x94\x13\x11PUNCTUATION SIGN '
 '\xd1\x01\x05SIGN '
'\xc6\x01'
 'd\x06EIGHT '
 '\x9a\x01F'
 '\xa0\x03\x02NI'
 '\x9a\x02O'
 '\xb6\x02S'
 '\xaf\x04T'
'\x0e'
 '\x9e\rS'
 '\xc24G'
 '\xa4{\x11VARIANT FORM USSU'
 '\x8a\xe4\x05D'
 '\xb29A'
 '\x9f\xc0\x01U'
'6'
 '4\x04IVE '
 '\x81\x01\x04OUR '
'\x18'
 'JS'
 '\xd2\x01B'
 '\xc2\x0cA'
 'NG'
 '\x96\x90\x07D'
 '\xcf\xf9\x01U'
'\x06'
 '\xfe\x0eH'
 '\xf9\x9a\x01\x05IXTHS'
'\x1e'
 '\x9a\x01B'
 ',\x12VARIANT FORM LIMMU'
 '\x96\x0cA'
 'NG'
 '\x1aS'
 '\xfe\x8f\x07D'
 '\xcf\xf9\x01U'
'\x06'
 '\x94f\x03AN2'
 '\xfb\xc2\x06U'
'\t'
 '\xb2\x07 '
 '\x8f\x8f\t4'
'\x16'
 ',\x04GIDA'
 '!\x03NE '
'\x04'
 '\xd2\xd5\x07E'
 '\xc7{M'
'\x12'
 '\x9c\x01\x13VARIANT FORM ILIMMU'
 '\xfa\x06S'
 '\xc24G'
 '\xae\xdf\x06D'
 '\xb29A'
 '\x9f\xc0\x01U'
'\t'
 '\xa6\xfd\x08 '
 '\x8a\x173'
 '\x034'
'\x18'
 '\\\x10LD ASSYRIAN ONE '
 '1\x03NE '
'\x04'
 '\x92\x8d\x07Q'
 '\xa1\xf4\x01\x03SIX'
'\x14'
 'rE'
 '\xf2\x07B'
 '6G'
 'T\x05THIRD'
 '\xe8\x11\x05QUART'
 '\xbd\x89\x07\x02SH'
'\x04'
 '\x8e\x08S'
 '\x91~\x05IGHTH'
'"'
 '\x90\x01\x05EVEN '
 '\xd0\x01\x14HAR2 TIMES GAL PLUS '
 '%\x03IX '
'\x10'
 '\x94\x01\x11VARIANT FORM IMIN'
 '\xf2\x01S'
 '\xc24G'
 '\xae\xdf\x06D'
 '\xb29A'
 '\x9f\xc0\x01U'
'\x06'
 '\x1a '
 '\x8f\x8f\t3'
'\x04'
 '\x8a\x8f\tA'
 '\x03B'
'\x04'
 '\xa2\x95\x07D'
 '\xf7\xb4\x01M'
'\x0e'
 '\x92\x01S'
 '\x8e\x03A'
 '\xb61G'
 '\xae\xdf\x06D'
 '\x84\xab\x01\x10VARIANT FORM ASH'
 '\xcbNU'
'\x02'
 '\x83\x17H'
'2'
 '4\x05HREE '
 '\xf1\x01\x03WO '
'\x1c'
 '\x8e\x01B'
 '(\x04SHAR'
 '\x18\x10VARIANT FORM ESH'
 'vA'
 'NG'
 '\x97\x90\x07D'
'\x06'
 '\x88[\x03URU'
 '\x83\nA'
'\x08'
 '\xe2Z2'
 '\x03U'
'\x04'
 '\xce\xba\x071'
 '\xab\x022'
'\x16'
 'RA'
 '\x1aB'
 ' \x02ES'
 '\x16G'
 '\x1aS'
 '=\x06THIRDS'
'\x04'
 '\xcdm\x02SH'
'\x04'
 '\xbecA'
 '\xfb\xb8\x06U'
'\x02'
 '\xa3\xbc\x07H'
'\x04'
 '5\x03ESH'
'\x04'
 '\x0bH'
'\x04'
 '\x11\x02AR'
'\x04'
 '\xa6\x89\t2'
 '\x03U'
'\x04'
 '\x0b '
'\x04'
 '\xb2\x8f\x07D'
 '\xf9\t\x0cVARIANT FORM'
'\x08'
 '\xa8\x01\tDIAGONAL '
 '\xf8\xb8\x08\tVERTICAL '
 '\xb9\n\x0eOLD ASSYRIAN W'
'\x04'
 '\xe8\xb8\x08\x02TR'
 '\x1bC'
'\xde\r'
 '\xca\x01A'
 '\x86\x0eB'
 '\xea\x03D'
 '\xf6\x08E'
 '\xaa\x08G'
 '\x8a\x18H'
 '\xfe\x02I'
 '\xee\x04K'
 '\xc2\x12L'
 '\xc6\x16M'
 '\xb2\x05N'
 '\x86\x0fP'
 '\x9a\x03R'
 '*S'
 '\xf2\x0fT'
 '\x9a\x07U'
 '\x8b\x13Z'
'\x81\x01'
 '\xa4\x01\x07 TIMES '
 '\x82\x01B'
 '\xaa\x03K'
 'nL'
 '\xd2\x01N'
 '\x82\x02R'
 '&S'
 '\xf0/\x03MAR'
 '\x96\x86\x08P'
 '\xdaD2'
 '\x03D'
'\x10'
 '\xb24I'
 '\xba9M'
 '\xbe\x08G'
 '\xa4\x08\x05LAGAR'
 '\xfe\xa3\x06S'
 '\xc2\x1eB'
 '\xd6\xab\x01H'
 '\x8b\x17A'
'%'
 '\x16 '
 '\xa3\x022'
'\x16'
 '0\x06TIMES '
 '\xf7\x9e\x01G'
'\x14'
 '\xa4\x01\x02GA'
 '&I'
 '\x94\\\x08U PLUS U'
 '\xa0\x1f\x04DUN3'
 '\xce\x08A'
 '\xbe\x1aL'
 '\x84\xeb\x05\x02SH'
 '\x87\xe0\x01H'
'\x04'
 '\xea\xa5\x01N'
 '\x87\xdb\x07L'
'\x04'
 '\xa6{G'
 '\xcf\xc0\x07M'
'\r'
 '%\x07 TIMES '
'\n'
 '\xd0\x0f\x02BA'
 '\xc6TM'
 '\xb2\x0eG'
 '\xe6+S'
 '\xcb\tT'
'\x07'
 '%\x07 TIMES '
'\x04'
 '\xa0C\nSHITA PLUS'
 '\x87\x15E'
'\x17'
 'D\x07 TIMES '
 '\xda\xc6\x07E'
 '\x8b\xb1\x01A'
'\x10'
 'fK'
 '\xa6\x9b\x06S'
 '\xb2hG'
 '\xb8+\x03DIM'
 '\xfa\rU'
 '\x96\xa9\x01H'
 '\xbf\tA'
'\x04'
 '\x96xA'
 '\x8b\x85\x08I'
'\r'
 '\x1a '
 '\xeb\x9a\x06S'
'\x08'
 '\x80\x01\nPLUS NAGA '
 '\xec$\x04OVER'
 '\xb5\x8c\x07\x08THREE TI'
'\x04'
 '\xf8i\x10OPPOSING AN PLUS'
 '\xbb\xb8\x06S'
'\x06'
 '\x90(\x02AD'
 '\x97wK'
'\x12'
 '"H'
 '\xa5\xac\x07\x02AL'
'\x11'
 '* '
 '\xb6\x9e\x01G'
 '\xdb\xdb\x072'
'\n'
 'D\tOVER ASH '
 '\xd6MZ'
 '\xabWK'
'\x06'
 '\xac\x01\x08OVER ASH'
 '\xc1\x0f\x1dTUG2 OVER TUG2 TUG2 OVER TUG2'
'\x05'
 'm\x19 CROSSING ASH OVER ASH OV'
'\x02'
 '\xbdk\x02ER'
'*'
 '\x1eA'
 '\x9a\x01I'
 'WU'
'\x13'
 '6H'
 '\x12L'
 '>R'
 '\xe2\xa6\x08G'
 '\x8bOD'
'\x02'
 '\xcb\x08A'
'\x07'
 '\xac\xaf\x08\x07 OVER B'
 '\xef;A'
'\x05'
 '\xd3\xa7\x07A'
'\t'
 '%\x07 TIMES '
'\x06'
 '\xfaoI'
 '\xee\xff\x07G'
 '\xc7\x05A'
'\x11'
 '. '
 '|\x03LUG'
 '\xeb\x81\x01R'
'\x06'
 'T\x08OVER BU '
 '\xfdX\x08CROSSING'
'\x04'
 '\x9e\xa4\x07A'
 '\xb3\xc9\x01U'
'\x05'
 '\xf9}\x08 OVER BU'
'j'
 '"A'
 '\xc2\x05I'
 '\x9b\x01U'
';'
 '&G'
 '\x86\x05R'
 '\xd7\xed\x08M'
'1'
 'A\x0e KISIM5 TIMES '
'.'
 '\xaa\x01A'
 '\x1eB'
 '2G'
 'p\x02IR'
 '.L'
 'ZU'
 '\xc8\x05\x07PAP PLU'
 '\xd2\x90\x01T'
 '\x8e\xab\x07S'
 '\xfe\x0bK'
 '\x82\nH'
 '\xd3\x16N'
'\x04'
 'z '
 '\xab\xea\x08M'
'\x04'
 '\x1aA'
 '\xb3\xf0\x08I'
'\x02'
 '\x93\x8f\x07L'
'\n'
 '"A'
 ':I'
 '\x8b\xe8\x08U'
'\x05'
 '\x0b '
'\x02'
 '\xc1\xaf\x07\x06PLUS M'
'\x05'
 '\xab\xa1\x07R'
'\x05'
 '\xb9\xae\x07\x06 PLUS '
'\x08'
 '\x1aU'
 '\xe7\xee\x08A'
'\x07'
 '\x88r\x07 PLUS M'
 '\xdb\xfc\x07M'
'\x04'
 '<\t2 PLUS GI'
 '\x83\xdc\x08S'
'\x02'
 '\xd3\x9f\x07R'
'\x07'
 '\xdb\xef\x04A'
'\x11'
 '.M'
 '"N'
 '\x8a\xdb\x08S'
 '\xeb\x11B'
'\x07'
 '\xae" '
 '\xe3\xca\x082'
'\x05'
 '\xa9~\x0e KASKAL U GUNU'
'!'
 'B '
 'BB'
 '6G'
 '\x16N'
 '\xca\x9c\x07R'
 '\x97\xce\x01H'
'\x06'
 '\xbe\x88\x01G'
 '\xa2\x03S'
 '\x8d\xdb\x03\x04OVER'
'\x07'
 '\x94\x12\x05 TIME'
 '\x8f\xd9\x082'
'\x05'
 '\xb7\xe3\x08U'
'\x0b'
 '\x1a3'
 '\xc3\xea\x084'
'\x07'
 '\xf3\x06 '
'W'
 'z '
 '~2'
 '\xb2\x01N'
 '\xc2\x01R'
 ' \x03ZEN'
 '\xeahS'
 '\xea\xb7\x07D'
 '\xa0?\x02GI'
 '\xbb\x05L'
'\x04'
 'P\x04TIME'
 '\xad\x12\x0bOVER E NUN '
'\x02'
 '\x0bS'
'\x02'
 '\x8d\x94\x05\x02 P'
'\x0f'
 '%\x07 TIMES '
'\x0c'
 'fS'
 '\xa8\x85\x01\tA PLUS HA'
 '\xfe\xb4\x07M'
 "\xc2'G"
 '\xc7\x05U'
'\x04'
 '\xda\xd9\x08A'
 '\x97\rH'
'\x0f'
 '\x0b '
'\x0c'
 '`\x04CROS'
 '\x00\x04OPPO'
 '$\x06TIMES '
 '\xcb\x8c\x07S'
'\x02'
 '\xad\x9d\x05\x04SING'
'\x06'
 '\x88I\x03GAN'
 '\xb3\x9c\x08M'
'\x04'
 '\xf2>I'
 '\xaf\xa0\x08E'
')'
 '%\x07 TIMES '
'&'
 'nA'
 'D\x05DUN3 '
 '"K'
 'NL'
 '>U'
 '\xf6\\I'
 '\xf4!\x02HA'
 '\xe3\xa0\x06B'
'\t'
 '\xe8A\t PLUS LAL'
 '\xa7\xa2\x08N'
'\x04'
 '\x81\x80\x01\x03GUN'
'\x06'
 ',\x05ASKAL'
 '\xf7\x93\x08U'
'\x05'
 '\xcd\x89\x07\x02 S'
'\x08'
 '"A'
 '\xbe\xe2\x08I'
 '\x03U'
'\x05'
 '\xa1@\x02L '
'\x04'
 '\xa2\xe2\x082'
 '\x03D'
'\xe8\x01'
 'BA'
 '\xd4\x0e\x06ESHTIN'
 '\x12I'
 '\xd3\x04U'
'\x93\x01'
 'n2'
 '\xe8\x0b\x02BA'
 'FD'
 '\x12L'
 '"N'
 '\xc2p '
 '\xde\x05R'
 '\xfe\xcc\x05S'
 '\xdb\x90\x02M'
'o'
 '\x0b '
'l'
 '@\x06TIMES '
 '\xd1c\x05OVER '
'j'
 '\xa6\x01A'
 '\xea\x01B'
 'rD'
 'FE'
 '*G'
 'rH'
 '\xe6\x01I'
 'FK'
 '\x9a\x01M'
 ' \x03NUN'
 '\x1eS'
 '\x8e\x01U'
 '\x8a}T'
 '\x8a\xc1\x07L'
 '\x03P'
'\x0e'
 '\x8c\x01\x06 PLUS '
 ',\x02SH'
 '\xc0\x81\x01\x0eB2 TENU PLUS T'
 '\xdb\xdb\x07N'
'\x06'
 '\x92\x0eI'
 '\x96#D'
 '\x97\x95\x08H'
'\x05'
 '\xadC\x072 PLUS '
'\x08'
 '\x1aA'
 '%\x02UR'
'\x04'
 ',\x02R '
 '\xa3\xdc\x08D'
'\x05'
 '\x0b '
'\x02'
 '\x99\x9d\x06\x04PLUS'
'\x08'
 '*I'
 '\xfa\x8b\x07U'
 '\xdb\xcf\x01A'
'\x05'
 '\xed\x10\x02M '
'\x08'
 '\x16N'
 '\xbb\x02L'
'\x05'
 '\xd3\x17 '
'\x0c'
 '\x12A'
 '#I'
'\x04'
 '\xf6\x7fN'
 '\x87\xdb\x07R'
'\t'
 '\xaa`4'
 '\x89\xf6\x03\x07R2 PLUS'
'\n'
 'NA'
 '\x90\x97\x02\x07I PLUS '
 '\xad\xf4\x04\x02UB'
'\x06'
 '@\x0c PLUS LU PLU'
 "'L"
'\x02'
 '\x11\x02S '
'\x02'
 '\xab\\E'
'\x05'
 '\x9d\x92\x08\x06 PLUS '
'\x04'
 '\xacL\nSH PLUS HU'
 '\xeb\x06G'
'\n'
 '>A'
 '$\x02ID'
 '!\x07U3 PLUS'
'\x04'
 '\x8e\x91\x07S'
 '\xab\xc6\x01K'
'\x05'
 '\x955\x04 PLU'
'\x02'
 '\xfb\xcb\x08 '
'\x04'
 '\xfe:E'
 '\xe3\x9b\x08I'
'\x05'
 '\x0b '
'\x02'
 '\xa7NO'
'\x0c'
 '"A'
 '\x1eH'
 '\x8b\xd2\x08U'
'\x04'
 '\xfe\xd5\x08L'
 '\x03R'
'\x06'
 '\x1aE'
 '\x93\xce\x08I'
'\x05'
 '\xc5\x98\x08\x07 PLUS T'
'\x07'
 '\x0bD'
'\x05'
 '\x91\xd0\x04\x05 PLUS'
'\x05'
 '\xb5\xd6\x05\x0c CROSSING GA'
'\x05'
 '\xa3h '
'\x07'
 '\xeeg '
 '\xc7\xe8\x07A'
'\x0b'
 '\x0b2'
'\t'
 '\x0b '
'\x06'
 'L\x08CROSSING'
 '\x00\x04OVER'
 '\xfb~T'
'\x02'
 '\xb1,\x03 GA'
'\x05'
 '\xef| '
'-'
 '6 '
 '^4'
 'rR'
 '\xbe\x01S'
 '\xbf\xd5\x06D'
'\x06'
 '\xf0\x02\tCROSSING '
 '\xe9\xb9\x03\x06TIMES '
'\x07'
 '\x0b '
'\x04'
 '@\x08CROSSING'
 '\x01\x04OVER'
'\x02'
 '\xfd\x81\x07\x03 GI'
'\x10'
 '\x163'
 '\x87m2'
'\r'
 '%\x07 TIMES '
'\n'
 '>A'
 '\x00\x02LU'
 '*I'
 '\xf6AG'
 '\xb7\xf6\x07P'
'\x02'
 '%\x07 PLUS I'
'\x02'
 '\xab\xa2\x08G'
'\x0c'
 '\x1aH'
 '\xb7\xc1\x08A'
'\x0b'
 '\x0b '
'\x08'
 '\x16T'
 '\xc7\x12C'
'\x06'
 ',\x05IMES '
 '\xeb\xda\x06E'
'\x04'
 '\x9avT'
 '\xb7\x95\x06B'
"'"
 'r2'
 '\x9e\x01D'
 '\x92\x01M'
 '2R'
 '\xf0\xfe\x01\n CROSSING '
 '\xcf\xcb\x06L'
'\r'
 '\x0b '
'\n'
 ',\x06TIMES '
 '\xbbiG'
'\x08'
 '\xe4\x15\x03KAK'
 '\xc4I\nSAL PLUS T'
 '\xf7\xa7\x07N'
'\t'
 '\x0b '
'\x06'
 'L\x06TIMES '
 '\xa11\x08OVER GUD'
'\x04'
 '\xbcu\x05A PLU'
 '\xe3\x98\x07K'
'\x05'
 '\x0b '
'\x02'
 "\xe9'\x05TIMES"
'\t'
 '\x1aU'
 '\xa3\xca\x087'
'\x04'
 '\xb6\xb8\x08S'
 '\xeb\x11N'
','
 '\x1eA'
 ':I'
 '\x93\x01U'
'\t'
 '\x1a '
 '\xc7\xc9\x08L'
'\x04'
 '\x9efG'
 '\x97\x0fT'
'\x15'
 '%\x07 TIMES '
'\x12'
 '\xec0\x02AS'
 '\x96\xb6\x05S'
 '\xb2hD'
 '\xf26B'
 '\x02G'
 '\xa2}N'
 'fK'
 '\xdbDU'
'\x11'
 ' \x02B2'
 '\xe3\xf9\x06L'
'\r'
 '%\x07 TIMES '
'\n'
 '\x9epK'
 '\xe2\xdd\x05L'
 '\xda\xb2\x01H'
 '\xbe?U'
 '\x93\x01A'
'1'
 'h\x03DIM'
 '^G'
 '\xd6\x01L'
 '>M'
 '\xa6\xac\x08 '
 '\xa2\x05S'
 '\xea\x11B'
 '\x02N'
 '\x03R'
'\x07'
 '5\x0b OVER IDIM '
'\x04'
 '\xb2\xec\x06S'
 '\xaf\x9c\x01B'
'\r'
 '\x0bI'
'\x0b'
 '\x0b '
'\x08'
 '\xfeaG'
 '\x96\x81\x06D'
 '\xac\x19 OVER IGI SHIR OVER SHIR UD OVER '
 '\xe3\x9b\x01R'
'\x07'
 '\x1a '
 '\xcf\xc3\x082'
'\x02'
 '\xf55\x04TIME'
'\r'
 '\x1a '
 '\xeb\xbc\x08I'
'\x08'
 'L\x04CROS'
 '\x00\x04OPPO'
 '\xf6VT'
 '\xa3\x92\x06S'
'\x02'
 '\xdd\xc8\x06\x05SING '
'\xc0\x01'
 'JA'
 '\xb6\rI'
 '\xee\x01U'
 '\xbc\x02\x04WU31'
 '\xa33E'
'\x91\x01'
 'x\x07 TIMES '
 '\xb2\x082'
 'BD'
 'fK'
 '2L'
 'RM'
 '\x1c\x04SKAL'
 '\xdb\xb5\x08B'
'j'
 '\xa2\x01A'
 'NB'
 'JE'
 '\x1eG'
 '\xb6\x02I'
 '"K'
 '"M'
 '\xa2\x01S'
 'nU'
 '\xd2+N'
 '\xae\xec\x05L'
 '\xb2\xdc\x01R'
 '\xc6\x17P'
 '\x02Z'
 "\xc3'T"
'\t'
 '\x16D'
 '\xcfBS'
'\x05'
 '\x81\xf0\x07\x08 PLUS KU'
'\x08'
 '\x1aA'
 '\xbf\xbe\x08I'
'\x06'
 '\x9e\xdd\x06L'
 '\x9e\xe1\x01D'
 '\x03R'
'\x04'
 '\xae\x17R'
 '\xa3*S'
'\x16'
 '\x1eA'
 'bI'
 '\xa3\x01U'
'\x0b'
 '&R'
 '\xaabN'
 '\x87\xdb\x07L'
'\x05'
 '\xa1\x14\n PLUS SHA3'
'\t'
 '$\x03SH '
 '\xbb\xee\x06R'
'\x04'
 '2C'
 '\xd5\xb6\x08\x06PLUS S'
'\x02'
 '%\x07ROSSING'
'\x02'
 '\xa1\xc2\x06\x02 G'
'\x05'
 '\x9b\xed\x07R'
'\x04'
 '\xba\x8e\x08G'
 '\x87-M'
'\x06'
 '\xee\x07I'
 '\xb7\x92\x08A'
'\x0c'
 '\x12E'
 'SI'
'\t'
 '!\x06 PLUS '
'\x06'
 '\xfe\xf5\x07D'
 '\xc6\x17G'
 '\xcf,T'
'\x05'
 '\xbd\xdd\x07\n PLUS NUNU'
'\x10'
 ':H'
 '\xce\xdf\x07A'
 '\xd8\x1c\x02UH'
 '\xfb1I'
'\x08'
 '\xea\xb1\x08I'
 '\xba\x07A'
 '\x02E'
 '\x03U'
'\x0b'
 '\xec\x8b\x07\tMUM TIMES'
 '\x9e\x9b\x01S'
 '\xea\x112'
 '\x03D'
'\x05'
 '\xd5\xb7\x04\x0b CROSSING K'
'\n'
 '*5'
 '\xae\xb7\x082'
 '\x023'
 '\x034'
'\x05'
 '\x81\xe8\x06\t OVER KAD'
'\x05'
 '\xc11\x08 TIMES I'
'\x07'
 '\x0b '
'\x04'
 '\xdeQT'
 '\xb1\x9e\x06\tCROSSING '
'\x04'
 '\xf2\xb5\x082'
 '\x034'
'\x07'
 '\x0b '
'\x04'
 'FL'
 '\x01\rOVER KASKAL L'
'\x02'
 '\xc9[\x18AGAB TIMES U OVER LAGAB '
'\x15'
 'D\x07 TIMES '
 '2S'
 '\x9e\xb3\x08D'
 '\x03N'
'\x06'
 '\x1aU'
 '\xd7\xf0\x06B'
'\x05'
 '\xaf\xb3\x08D'
'\x08'
 '0\x03IM5'
 '\x9e\xa5\x08A'
 '\xcf\rH'
'\x05'
 '\xbd\xe3\x06\x0b OVER KISIM'
'\x19'
 '\xd2\x014'
 '6R'
 '\xa03\x1e OVER HI TIMES ASH2 KU OVER HI'
 '\xfe\x17S'
 '\xca\x01L'
 '\xbe\xe3\x073'
 '\x027'
 '\x03N'
'\x05'
 '\xed\xa5\x06\x08 VARIANT'
'\x05'
 '\xc9Z\t OPPOSING'
'\x02'
 '\xeb\xaf\x088'
'\xd2\x01'
 '\x1eA'
 '\xb6\x0eI'
 ';U'
'\x81\x01'
 '0\x02GA'
 '\xda\x0cL'
 'JM'
 '\x87.H'
'r'
 '\x16B'
 '\xd3\nR'
'i'
 '\x0b '
'f'
 '0\x06TIMES '
 '\xfb\xd4\x06S'
'd'
 '\x8a\x01A'
 '\xc2\x01B'
 '"G'
 '6H'
 '>I'
 '^K'
 'vL'
 '.M'
 '.S'
 '\x86\x02T'
 '~U'
 '\xfa\x9e\x08E'
 'fD'
 '\x8f\x05N'
'\x0f'
 'P\x06 PLUS '
 'T\x04SH Z'
 '\xf2\xab\x08L'
 '\x03N'
'\x06'
 '&D'
 '\xaa\xe5\x07L'
 '\xb3AG'
'\x02'
 '\xb5\xea\x05\x06A PLUS'
'\x02'
 '\xb9W\x02ID'
'\x04'
 '\x9e\xa4\x08A'
 '\xbb\x07I'
'\x08'
 ' \x02UD'
 '\xbf\xd1\x07A'
'\x05'
 '\xa3Q '
'\x06'
 '\x8c#\x07I TIMES'
 '\xcf\x83\x07A'
'\x08'
 '\x16M'
 '\x8f%G'
'\x07'
 '!\x06 PLUS '
'\x04'
 '\xc2\xe5\x07L'
 '\xc3-H'
'\n'
 '\x1aU'
 '\xd7\xfa\x07I'
'\x06'
 '\x1aL'
 '\xb7\xa9\x083'
'\x05'
 ')\x08 PLUS HI'
'\x02'
 '\xe3. '
'\x08'
 '\x92MA'
 '\xca\x9b\x06I'
 '\xf7;U'
'\x06'
 '\x1aE'
 '\x97\xe8\x06U'
'\x05'
 '\xdb\x0c '
'\x0c'
 '\x1aH'
 '\xab\xa4\x08U'
'\n'
 'd\x0eITA PLUS GISH '
 '\\\x02U2'
 '\xf5\x03\x02E '
'\x04'
 ',\x06PLUS E'
 '\xdfRT'
'\x02'
 '\x0bR'
'\x02'
 '\x0bI'
'\x02'
 '\xbf\xd8\x06N'
'\x05'
 '\xf13\x05 PLUS'
'\x06'
 'VA'
 '\x8d\x10\x10E PLUS A PLUS SU'
'\x04'
 '\xca\xd6\x06K'
 '\xfb\xce\x01G'
'\r'
 'H\x06 PLUS '
 '\xca\x182'
 '\xa6\xfa\x07S'
 '\xeb\x11D'
'\x04'
 '\x1aU'
 '\xbb\xa4\x08A'
'\x02'
 '\x8d\xf1\x04\x04 PLU'
'\x0b'
 '\x0b '
'\x08'
 'D\x04GUNU'
 'i\tTIMES SHE'
'\x05'
 'I\x10 OVER LAGAR GUNU'
'\x02'
 '\xf5\xc0\x05\x02 S'
'\x05'
 '\x0b '
'\x02'
 '\xd5\xcc\x04\x05PLUS '
'\x05'
 '\x0b '
'\x02'
 '\x19\x04TIME'
'\x02'
 '\x85\xdb\x07\x03S L'
'\x07'
 '1\n TIMES KUR'
'\x05'
 '\xc1\x97\x04\x05 PLUS'
'\t'
 '\xac\x97\x04\x02MM'
 '\xea\xf7\x03S'
 '\xeb\x11L'
'K'
 'Z2'
 '\x8c\x05\x03GAL'
 '\x8e\x01M'
 '\xf24 '
 '\xe6\xe4\x073'
 '\x02H'
 '\x03L'
'3'
 '\x0b '
'0'
 '@\x04CROS'
 '\x00\x04OPPO'
 '.S'
 '#T'
'\x02'
 '\xc9\x95\x04\x06SING L'
'\x04'
 '\xf6>H'
 '\xdb\x86\x06Q'
'('
 ',\x05IMES '
 '\xdf\xaa\x06E'
'&'
 '\xb4\x01\x03ESH'
 '\x1eK'
 'D\x02LA'
 '\x1eM'
 '<\x02SI'
 '\xf6\rG'
 '\x8e T'
 '\xcc\x08\x03HI '
 '\x9e\xcf\x02N'
 '\xee\xd2\x03B'
 '\x92\xb5\x01A'
 '\xf3\tI'
'\x04'
 '\x0b2'
'\x05'
 '\xbfH '
'\x08'
 ' \x02AD'
 '\xab\x9c\x08I'
'\x06'
 '\xf2\x0f3'
 '\xb7\x8c\x082'
'\x04'
 '\x86\x10 '
 '\xab0G'
'\x02'
 '\x0bE'
'\x02'
 '\x0b '
'\x02'
 '\xe9\xd2\x04\x04PLUS'
'\x04'
 '0\x07K2 PLUS'
 '\xff\x0e '
'\x02'
 '\xb1\xd6\x07\x02 B'
'\t'
 '\x0b '
'\x06'
 '\x16O'
 '\xbb:S'
'\x04'
 '8\x07PPOSING'
 '\x01\x03VER'
'\x02'
 '\x15\x03 LU'
'\x02'
 '\xf3\xd2\x07G'
'\x07'
 '-\t OVER LUM'
'\x05'
 '\xcb2 '
'<'
 '2A'
 'bU'
 '\xc6\xa4\x04E'
 '\xc3\xc4\x03I'
'\x11'
 '2 '
 '\x1eS'
 '\x92\x98\x082'
 '\x02H'
 '\x03R'
'\x04'
 '\xde,T'
 '\xab\x08G'
'\x04'
 '\xa3&H'
'%'
 'h\x02SH'
 '\xda3G'
 '\xc4\xd9\x03\x05 OVER'
 '(\x02RG'
 '\x81\xcf\x01\x02NS'
'\x19'
 '\x16 '
 '\x9b\x023'
'\x0c'
 '\x80\x01\nCROSSING M'
 '\x14\tOVER MUSH'
 'U\x06TIMES '
'\x02'
 '\xdb\xd5\x06U'
'\x05'
 ')\x08 TIMES A'
'\x02'
 '\x99\x88\x04\x05 PLUS'
'\x06'
 '\x8e\xd8\x07K'
 '\xfa%Z'
 '\x8b\x17A'
'\x0b'
 '\x0b '
'\x08'
 ',\x06TIMES '
 '\x871G'
'\x06'
 '\x1aA'
 '\x8b\xe7\x07D'
'\x05'
 '\x81\x87\x04\x05 PLUS'
'x'
 '*A'
 '\x9e\x02E'
 '^I'
 '\xf3\x04U'
'\x15'
 ',\x02GA'
 '\xc6\x01M'
 '\xc7\x91\x082'
'\x0b'
 '\x1a '
 '\xef\x92\x08R'
'\x06'
 '\x84\x01\x08OPPOSING'
 '\xbc=\tTIMES SHU'
 '\xf9\xe4\x06\x06INVERT'
'\x02'
 '\xd9\xee\x07\x03 NA'
'\x07'
 '\xf0\x11\x02 N'
 '\xd3\xff\x072'
'\t'
 '\x0b '
'\x06'
 ',\x06TIMES '
 '\xdf0S'
'\x04'
 '\xa6\x89\x08U'
 '\xbb\x07A'
'+'
 'jM'
 'L\x04NDA2'
 '\x94\xdf\x04\x06 TIMES'
 '\xda\xce\x01S'
 '\x9f\xe1\x012'
'\x07'
 '-\t TIMES GA'
'\x04'
 '\xb2\x01R'
 '\xef2N'
'\x1d'
 '%\x07 TIMES '
'\x1a'
 'NA'
 ' \x02ME'
 'NN'
 ' \x03SHE'
 '^U'
 '\xc7\xc3\x06G'
'\x06'
 '\xce\x01S'
 '\xc3\x8c\x08N'
'\x02'
 '\x19\x04 PLU'
'\x02'
 '\x15\x03S G'
'\x02'
 '\xb52\x02AN'
'\x04'
 '\xfa\x86\x08U'
 '\xab\x06E'
'\t'
 '%\x07 PLUS A'
'\x06'
 '\x1aS'
 '\xcb\x81\x08 '
'\x04'
 '\x0bH'
'\x05'
 '3 '
'\x04'
 '\x1a2'
 '\xa7\xfa\x07S'
'\x02'
 '\x0b '
'\x02'
 '\x19\x04PLUS'
'\x02'
 '\xbb\xcb\x06 '
'3'
 '\x1aN'
 '\x8f\xbd\x061'
'/'
 '\x1e '
 '\xbd\x03\x02UZ'
'\x12'
 '\x8c\x01\x0cCROSSING NUN'
 'H\x0cLAGAR TIMES '
 '\xb2\x01O'
 '\xff3T'
'\x05'
 '\xd9#\x0e LAGAR OVER LA'
'\n'
 '<\x03SAL'
 '\xd6\xc8\x06M'
 '\x0eU'
 '\xdb\xba\x01G'
'\x05'
 '\x85\xc2\x07\x17 OVER NUN LAGAR TIMES S'
'\x02'
 '\x15\x03VER'
'\x02'
 '\xb5\xc2\x07\x02 N'
'\x1b'
 '\x0b '
'\x18'
 'x\nAB2 TIMES '
 '\xdd\x01\x0fKISIM5 TIMES BI'
'\x14'
 '\x9e\x01I'
 '(\x02KA'
 '\xbe\x0fD'
 '\xdc\x19\x02AS'
 '\xc0\xd5\x03\x03SIL'
 '\x9e\xb8\x02U'
 '\xb2\x05G'
 '\xe2\x9b\x01B'
 '\xfe\x15L'
 '\xd3\x16N'
'\x02'
 '\x0bG'
'\x02'
 '\x0bI'
'\x02'
 '\xe7! '
'\x02'
 '\xff\xb5\x07D'
'\x05'
 '\xab\xc0\x07 '
'*'
 '\x1eA'
 '&I'
 '\xd3\x07E'
'\t'
 '\xbe\x84\x08D'
 '\x02N'
 '\x03P'
'!'
 '" '
 '\x99\x01\x03RIG'
'\x14'
 'P\x06TIMES '
 '\x91\xfb\x03\x08CROSSING'
'\x12'
 '\xee\x04A'
 '\x02I'
 '\xca\x0cU'
 '\xf6\xd0\x05B'
 '\xfb\xa0\x02E'
'\x0b'
 '\x0b '
'\x08'
 '\\\x06TIMES '
 '\x95"\x0cOPPOSING PIR'
'\x06'
 '\xfe\xba\x07K'
 '\xee/Z'
 '\xd3\x0fU'
'\x08'
 '\x92\x03A'
 '\xb6\xfe\x07I'
 '\x03U'
'\xb0\x01'
 '.A'
 '\xd6\x04H'
 '\xd6\x08I'
 '\x8b\x01U'
'5'
 '.G'
 '\x9a\x03L'
 'zN'
 '\xaf\xfc\x07R'
'+'
 '\x0b '
'('
 '^N'
 '$\x06TIMES '
 '\x8a\x1cG'
 '\x89\x82\x06\x06OVER S'
'\x02'
 '\xdd\xbe\x06\x04UTIL'
'"'
 't\x02DU'
 '\x16K'
 '"S'
 '&U'
 '\x86"T'
 '\x9e\x96\x07N'
 '\xba\x18M'
 '\xfe\x15H'
 '\xa2\x13L'
 '\xeb\x03A'
'\x05'
 '\xb3\xfe\x07B'
'\x04'
 '\xa2\xdd\x07A'
 '\xc7\x1bU'
'\x04'
 '\x92\x92\x04H'
 '\xa3\xde\x03A'
'\n'
 '\xf2\xeb\x07S'
 '\xea\x112'
 '\x02B'
 '\x02M'
 '\x03R'
'\x05'
 '!\x06 LAGAB'
'\x02'
 '%\x07 TIMES '
'\x02'
 '\x0bA'
'\x02'
 '\x0bS'
'\x02'
 '\xab\xae\x06H'
'\x02'
 '\xeb\xfb\x03G'
'\\'
 '.A'
 '\xe2\x01E'
 '\xee\x01I'
 '\xe3\x03U'
'\x1b'
 '63'
 '\xe2\xaa\x06B'
 '\xbe\x02R'
 '\x97\xce\x016'
'\x13'
 '%\x07 TIMES '
'\x10'
 'VU'
 '\xae\x15S'
 '\xba\xeb\x05G'
 '\xf26B'
 '\xde\x85\x01T'
 '\xca<N'
 ';A'
'\x05'
 '\x0b '
'\x02'
 '\xed&\x03PLU'
'\x13'
 ': '
 '\x8c\x01\x02SH'
 '\xfa\xa9\x07G'
 '\xcbNN'
'\x06'
 '<\tOVER SHE '
 '\xc7\xb4\x07H'
'\x04'
 '\xf6\x0cG'
 '\xb1\x05\x0cTAB OVER TAB'
'\x07'
 '\xb6\xdf\x06L'
 '\x8b\x99\x012'
'('
 ':D'
 'JM'
 '\xe2\x01R'
 '\xda\x15N'
 '\xdb\xc8\x07T'
'\x07'
 '%\x07 TIMES '
'\x04'
 '\xda\xf3\x07I'
 '\xdf\x03A'
'\x19'
 '%\x07 TIMES '
'\x16'
 'zB'
 '*M'
 '\xb2\x10K'
 '\xe0\x01\x03IGI'
 '\xde\xdc\x01L'
 '\xee\xbf\x05S'
 '\x9e\x02D'
 '\x96?G'
 '\xc7\x05A'
'\x04'
 '\x1aU'
 '\x8f\xe8\x07A'
'\x02'
 '\x0bL'
'\x02'
 '\xc3\xea\x07U'
'\x07'
 '\x0b '
'\x04'
 '\x9a!T'
 '\x91\x97\x07\x14OVER SHIR BUR OVER B'
'\t'
 '`\x0f OVER INVERTED '
 '\xda\xb6\x07B'
 '\x83=2'
'\x02'
 '\xf7\xa6\x05S'
'\x0f'
 '6G'
 '\xde\x0f '
 '\x82\xdd\x03L'
 '\x9f\xb8\x02K'
'\x07'
 '\x0b4'
'\x05'
 '1\n OVER SIG4'
'\x02'
 '\xbb\r '
'\x13'
 'ND'
 '\x16M'
 '\x16R'
 '\x9c\xed\x03\x05 OVER'
 '\xab\xc7\x03H'
'\x05'
 '\xeb\xf1\x072'
'\x05'
 '\xbb\xb1\x06A'
'\x05'
 '\xc3\xf1\x079'
'@'
 '.A'
 '\xee\x03I'
 '\xf2\x01U'
 '\xeb\x07E'
'#'
 '> '
 '^B'
 '\xbe\x01G'
 '\xb2\x9f\x06K'
 '\xfb\xce\x01R'
'\x08'
 '<\x06TIMES '
 '\xde\x0cG'
 '\xbf\x85\x06A'
'\x04'
 '\xfa\xc2\x07H'
 '\x03M'
'\x07'
 '\x0b '
'\x04'
 '\x90\x01\x1dOVER TAB NI OVER NI DISH OVER'
 '\x9b\x95\x06S'
'\x02'
 '\xf5\xf4\x05\x02 D'
'\x0f'
 '%\x07 TIMES '
'\x0c'
 'NT'
 '\xe8\xd7\x02\x02SH'
 '\xe6\xcc\x03G'
 '\xe2\x9b\x01B'
 '\xcf%U'
'\x02'
 '\x99\x9f\x06\x02UG'
'\x0f'
 '&R'
 '\xd2\x18 '
 '\x9f\xd4\x07L'
'\t'
 '\x0b '
'\x06'
 '0\x08OVER TIR'
 'cT'
'\x05'
 '\x0b '
'\x02'
 '\x0bG'
'\x02'
 '\x15\x03AD '
'\x02'
 '\x95\x05\x08OVER GAD'
'\x02'
 '\xb9\x13\x06IMES T'
'\r'
 '2R'
 '\xde\x9c\x06G'
 '\x96\xce\x01K'
 '\x03M'
'\x05'
 '\xbd\xdf\x03\x11 OVER TUR ZA OVER'
'\xa5\x01'
 '\x8a\x01 '
 '\xf6\x02D'
 '\xda\x02N'
 '.M'
 '\x96\x02R'
 '\xe8\x07\x02SH'
 '\xa2\x01Z'
 '\xa4\xd5\x03\x02TU'
 '\xd2\x82\x042'
 '\x03B'
'\n'
 'D\x07OVER U '
 '\xa6\xb5\x04U'
 '\xbb\xea\x01G'
'\x06'
 '\xd8\x01\nPA OVER PA'
 '\xb4\xf7\x06\x18U REVERSED OVER U REVERS'
 '\xb12\nSUR OVER S'
'\x02'
 '\x0b '
'\x02'
 '-\tGAR OVER '
'\x02'
 '\xe3\xe0\x07G'
'\x15'
 '\x1a '
 '\xf3\xda\x07U'
'\x10'
 'ZK'
 ',\x07SHESHIG'
 'D\x06TIMES '
 '\x8b\x01G'
'\x02'
 '\x0bU'
'\x02'
 '\x0bS'
'\x02'
 '\xb3\xdb\x03H'
'\x05'
 '\x0b '
'\x02'
 '\x0bT'
'\x02'
 '\xf9\xa1\x06\x06IMES B'
'\x08'
 '`\x0eU PLUS U PLUS '
 '\xee\xa0\x06B'
 '\xdb\x95\x01M'
'\x04'
 '\x0bU'
'\x05'
 '\x0b '
'\x02'
 '\x0bG'
'\x02'
 '\xdf\xef\x05U'
'\x13'
 'H\x07 TIMES '
 '\x80\x01\x02UM'
 '\xef\x9c\x07B'
'\x08'
 '2L'
 '\x10\x02ME'
 '*S'
 '\xdb\xe1\x07U'
'\x02'
 '\xab\x06A'
'\x02'
 '\xb9\xd4\x03\x05 PLUS'
'\x02'
 '\xa7\xdb\x03H'
'\x07'
 '%\x07 TIMES '
'\x04'
 '\xee\tK'
 '\xa7\xc0\x07P'
'S'
 '6 '
 'z2'
 '\xfa\x01I'
 '\x16U'
 '\xc3\xdd\x074'
'\x04'
 '>S'
 '\x85\xa3\x07\tCROSSING '
'\x02'
 '\x0bH'
'\x02'
 '\x15\x03ESH'
'\x02'
 '\xd7\xd4\x07I'
'\x13'
 '%\x07 TIMES '
'\x10'
 '6A'
 'P\x02U2'
 '\xe2\x98\x07N'
 '\xb7.H'
'\x06'
 '0\x06 PLUS '
 '\xbb\xde\x07L'
'\x04'
 '\xae\xc7\x07H'
 '\x03N'
'\x07'
 '!\x06 PLUS '
'\x04'
 '\xda\x9d\x06A'
 '\x9b\x93\x01B'
'\x05'
 '\xd3\xdd\x073'
'5'
 '8\x07 TIMES '
 '\xc1\x03\x02DA'
'.'
 '\x86\x01A'
 ':G'
 'RI'
 '.S'
 '.U'
 '\xe2\x94\x07D'
 'fM'
 '\x12T'
 '\xc6\x17K'
 '\xfe\x15H'
 '\x02P'
 '\xc6\x11B'
 '\xdf\x01L'
'\x05'
 '\x0bS'
'\x02'
 '\x0bH'
'\x02'
 '\x0bG'
'\x02'
 '\xff\x8b\x06A'
'\n'
 '\x1aA'
 '\xab\xdb\x07U'
'\t'
 '"N'
 '\x86\xdb\x07L'
 '\x03R'
'\x02'
 '\xdb\x062'
'\x06'
 '\xee\xad\x07G'
 '\x9e\x1bS'
 '\xeb\x11M'
'\x04'
 '\xcc\x8b\x06\x02IG'
 '\xc3\xce\x01H'
'\x06'
 '* '
 '\xda\xbc\x02R'
 '\x9b\x9d\x05D'
'\x02'
 '\x89\x91\x06\x06PLUS G'
'\x05'
 '\x0b '
'\x02'
 '\x8d\xa6\x04\x04TIME'
'\x11'
 'P\x07 TIMES '
 '\x9c\x9c\x07\x02UM'
 '\xa6<2'
 '\x03X'
'\x08'
 '.T'
 '\xb8\xfe\x06\x02KU'
 '\xdbYA'
'\x02'
 '\x95\x89\x06\x02AK'
'\x06'
 '\x1a3'
 '\xdb\xd7\x07U'
'\x05'
 ')\x08 TIMES K'
'\x02'
 '\x81\x91\x06\x02AS'
'$'
 '2A'
 '\xa6\x01I'
 '\xbe\x01U'
 '\xeb\x85\x06E'
'\x0b'
 '& '
 '\x92\x9a\x07M'
 '\xa7<G'
'\x04'
 '4\x08SQUARED '
 '\xef\x01T'
'\x02'
 '\x19\x04TIME'
'\x02'
 '\x0bS'
'\x02'
 '\xd1\x98\x07\x02 K'
'\x0f'
 'ZB'
 '\xca\x86\x06Z'
 '\x90\xa1\x01\x07 OVER Z'
 '\x86-3'
 '\x03G'
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
 '\xcb\xe0\x05E'
'\x0b'
 '&5'
 '\xd6\x96\x07B'
 '\x83=M'
'\x05'
 '\x1d\x05 TIME'
'\x02'
 '\xdf\xe3\x05S'
'\x02'
 '\xb5\x80\x01\x02 O'
'\xbc\x02'
 'l\x0fPRIOT SYLLABLE '
 '\x89\x02\x07RILLIC '
'n'
 '\xa6\x01K'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x02P'
 '\x02R'
 '\x02S'
 '\x02T'
 '6W'
 '\xae\xba\x02J'
 '\x02Z'
 '\xde\xf5\x01X'
 '\xae\xa0\x03A'
 '\x02E'
 '\x02I'
 '\x02O'
 '\x03U'
'\n'
 '\xe6\xd0\x07A'
 '\x02E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x08'
 '\xb2\xd0\x07A'
 '\x02E'
 '\x02I'
 '\x03O'
'\xce\x01'
 '\xc4\x01\x0fCAPITAL LETTER '
 '\xc6\x01K'
 ' \x07LETTER '
 'l\x02PA'
 '!\rSMALL LETTER '
'b'
 '\xaa\x04A'
 '&B'
 'jC'
 '"D'
 '\xba\x01E'
 'VG'
 'zH'
 '^I'
 '\xca\x01M'
 'zN'
 'X\x02PE'
 '\x16R'
 'nS'
 'fT'
 '\xa2\x01Y'
 'vZ'
 '\xae\xa2\x07L'
 '\xc2\x04Q'
 '\xd3\x16W'
'\x02'
 '\x8d\x88\x07\x03AVY'
'\x04'
 '\xe4\x04\x05MULTI'
 '\xd5\xd7\x06\x0eSMALL CAPITAL '
'\x02'
 '\xd9\xa8\x06\x03YER'
'd'
 '\xba\x01A'
 '&B'
 'jC'
 '"D'
 '\xba\x01E'
 'VG'
 'zH'
 '^I'
 '\xca\x01M'
 'zN'
 '*P'
 'FR'
 'nS'
 'fT'
 '\xa2\x01Y'
 'vZ'
 '\xae\xa2\x07L'
 '\xc2\x04Q'
 '\xd3\x16W'
'\x02'
 '\xe1\xc9\x03\x04LEUT'
'\x06'
 '\xee\x01I'
 '\xfc\x86\x01\x06LENDED'
 '\xf9\x9d\x06\x08ROAD OME'
'\x04'
 '\xfa\x04L'
 '\x8f\xe2\x04C'
'\x0c'
 'JJ'
 '\x1c\x08OUBLE MO'
 '&Z'
 '\xa3\xc7\x07W'
'\x02'
 '\xe9\xfa\x05\x02ER'
'\x02'
 '\x0bN'
'\x02'
 '\xdd\x04\x02OC'
'\x06'
 '\xb2\xfe\x02E'
 '\xee\xc8\x04W'
 '\x03Z'
'\x06'
 '0\x07L WITH '
 '\xa7\x07N'
'\x04'
 '\xca\x07M'
 '\x9f\x91\x04H'
'\x04'
 ')\x08HE WITH '
'\x04'
 '\xda\x85\x03D'
 '\xad\x92\x01\nSTROKE AND'
'\x06'
 '4\x07A WITH '
 '\xf3\xc4\x07W'
'\x04'
 '\x96\x97\x04H'
 '\xb7\x99\x03S'
'\x08'
 '\x11\x02OT'
'\x08'
 '0\x06IFIED '
 '\xbf\xc4\x07A'
'\x06'
 '0\x02CL'
 '\xb6\xa4\x06Y'
 '\xd7\x9f\x01A'
'\x02'
 '!\x06OSED L'
'\x02'
 '\xe1\x82\x01\x05ITTLE'
'\x04'
 '\x15\x03ONO'
'\x04'
 '\x12C'
 "'G"
'\x02'
 '\xc1\x91\x04\x04ULAR'
'\x02'
 '\x99\xeb\x03\x05RAPH '
'\x02'
 '\xb1\x04\x06EUTRAL'
'\x04'
 '.E'
 '\x85\xfd\x06\x05ALOCH'
'\x02'
 '\xaf\xdd\x02 '
'\x08'
 '8\x08EVERSED '
 '\x97\xaa\x07H'
'\x06'
 '\xe2\xe1\x05D'
 '\xf2\x9a\x01Y'
 '\x93DZ'
'\x08'
 '(\x04OFT '
 '\xfb\xc0\x03H'
'\x06'
 '\x1aE'
 '\xef\xbf\x07D'
'\x04'
 '\xa2\xc0\x07L'
 '\x03M'
'\n'
 '2E'
 'RS'
 '\x8a\xdd\x04C'
 '\xc7\xe1\x02W'
'\x02'
 '%\x07 WITH M'
'\x02'
 '\x85\x91\x04\x05IDDLE'
'\x04'
 '\xca\xbe\x07S'
 '\x03W'
'\x06'
 'T\rERU WITH BACK'
 '\xda\xbd\x07A'
 ';N'
'\x02'
 '\xc9\xa7\x07\x02 Y'
'\x04'
 '\xaa\xbe\x03H'
 '\xfd\xba\x01\x03EML'
'\xcc\x02'
 'VE'
 '\xf2\tI'
 '\xee\x06O'
 '\x89\x9d\x07\tRIVE SLOW'
'8'
 '\x94\x01\x06SERET '
 '\x8c\x01\tVANAGARI '
 '\x9dZ\rCIMAL EXPONEN'
'\x08'
 '8\x06CAPITA'
 '\x01\x04SMAL'
'\x04'
 '-\tL LETTER '
'\x04'
 '\xde\x8d\x07O'
 '\xab\x13E'
'.'
 '\xe4\x01\x07LETTER '
 '\xc8\x01\x05SIGN '
 '\xa0\x03\x0bVOWEL SIGN '
 '\x88\xf1\x01\x02CA'
 '\xa8\xac\x05\x08GAP FILL'
 '\xdd\x01\x04HEAD'
'\x12'
 '\xa2\x01G'
 '\xfe\xb2\x03J'
 '\x92\x86\x01B'
 '\xd49\x05HEAVY'
 '\xf2NS'
 '\x94\x06\x06CANDRA'
 '\xf8\xa9\x01\x02DD'
 '\x97*Z'
'\x04'
 '\x9e\xd2\x02L'
 '\x93\xce\x04G'
'\x12'
 '\xc4\x02\x0cCANDRABINDU '
 '(\x14DOUBLE CANDRABINDU V'
 '\x14\x08INVERTED'
 '\x00\x07SPACING'
 '\xa8\xef\x06\x06PUSHPI'
 '\xbdD\x0cHIGH SPACING'
'\x08'
 '&V'
 '\xe6\xae\x06A'
 '\xafIT'
'\x02'
 '\xe7\x92\x05I'
'\x02'
 '\x8d\x87\x02\x02 C'
'\x04'
 '\xfc\x83\x04\x0bCANDRA LONG'
 '\x01\rPRISHTHAMATRA'
'4'
 '\x90\x01\x0bAMOND WITH '
 '^G'
 '\xf4\xce\x03\x04VORC'
 '\xd1\xdc\x03\x08SABLED C'
'\x08'
 'D\x03LEF'
 '\x00\x04RIGH'
 '\x92\xda\x05B'
 'WT'
'\x02'
 '\xf7\xda\x05T'
'('
 '@\x03IT '
 '\xb1\x02\x08RAM FOR '
'\x16'
 'vF'
 '4\x02NI'
 '\x02O'
 '\x0eS'
 '6T'
 '\xf4\xc3\x02\x05EIGHT'
 '\x89\xbf\x02\x04ZERO'
'\x04'
 '\xa0\x01\x02IV'
 '\xc5\xc3\x02\x03OUR'
'\x02'
 'oN'
'\x04'
 '\xa4\xc4\x02\x04EVEN'
 '\x01\x02IX'
'\x04'
 ',\x03HRE'
 '\xc5\xc3\x02\x02WO'
'\x02'
 '\xc3\xc3\x02E'
'\x12'
 'X\x05EARTH'
 '@\x05GREAT'
 '\x00\x04LESS'
 "'H"
'\x07'
 '\x19\x04LY H'
'\x04'
 '\x8a\xd5\x01E'
 '\xdb\xdd\x03U'
'\x04'
 '\x9d\x81\x04\x04ER Y'
'\x04'
 '\xe8\xd4\x01\x07EAVENLY'
 '\x01\x04UMAN'
'\xde\x01'
 '\x8c\x01\nMINO TILE '
 '\xdc\x01\x05TTED '
 '\xb8\x01\x04UBLE'
 '\xf9\xe5\x06\x03WNW'
'\xc8\x01'
 'H\x08HORIZONT'
 '\x01\x06VERTIC'
'd'
 '\x11\x02AL'
'd'
 ' \x02-0'
 '\x8f\xb7\x06 '
'b'
 ':0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'\x0e'
 '\xc97\x02-0'
'\n'
 '\x96\xbc\x01C'
 '\xc8\xcf\x03\x04OBEL'
 '\xcc\x02\tTRANSPOSI'
 '\xa0\xb2\x01\x0eRIGHT-POINTING'
 '\xefgS'
'\x08'
 '\x88\x01\n OBLIQUE H'
 ' \x02D '
 '\xa5\x9e\x03\r-STRUCK SMALL'
'\x02'
 '\xa1\xea\x06\x03YPH'
'\x04'
 '\xea\xc3\x03F'
 '\x1bM'
'\xd0\x12'
 '\xec\x02\rDITORIAL CORO'
 '\x14\x13GYPTIAN HIEROGLYPH '
 '\xecB\x03JEC'
 '\x14\x0fLECTRICAL INTER'
 '\x18\x08THIOPIC '
 '\x80\x88\x06\nQUALS SIGN'
 '\xbd\x15\x04ARTH'
'\x02'
 '\xab\xd0\x06N'
'\xde\x10'
 '\xea\x03A'
 '\xb0\x04\x02C0'
 '\xdc\x01\x02D0'
 '\xa8\x04\x02E0'
 '\xbc\x02\x02F0'
 '\xf4\x03\x02G0'
 '\xfc\x03\x03H00'
 'T\x02I0'
 '\xb4\x01\x03K00'
 'L\x03L00'
 'T\x02M0'
 '\x82\x04N'
 '\xd8\x02\x03B00'
 '\xc0\x03\x02O0'
 '\xb0\x04\x02P0'
 '\x8c\x01\x03Q00'
 'D\x02R0'
 '\xe8\x01\x02S0'
 '\xf8\x03\x02T0'
 '\xb8\x02\x02U0'
 '\xf8\x02\x02V0'
 '\xe0\x04\x02W0'
 '\xa0\x02\x03X00'
 'X\x03Y00'
 'U\x02Z0'
'\xe4\x01'
 '\x1e0'
 '\x85\x03\x02A0'
'\xa0\x01'
 'V0'
 'b1'
 'f4'
 '\xe6/3'
 '\xbe\x9f\x057'
 '\x9e\xa2\x012'
 '\x025'
 '\x036'
'\x18'
 '\xfa;6'
 '\x86\xcb\x055'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\x9e\x86\x064'
 '\x027'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x025'
 '\x026'
 '\x028'
 '\x039'
'\x1c'
 '\xba\x85\x060'
 '\x022'
 '\x023'
 '\x025'
 '\xa6\x97\x011'
 '\x024'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'D'
 '.0'
 '\xb6/3'
 '\xf6\xc0\x061'
 '\x032'
'\x16'
 '\xa297'
 '\xaa\xe2\x061'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x028'
 '\x039'
'8'
 '\x1e0'
 'Z1'
 '\x87\x0f2'
'\x18'
 '\xe602'
 '\xee\xe9\x061'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x16'
 '\xd6\x82\x060'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\xb8\x01'
 'F0'
 '^3'
 'f4'
 'f5'
 'j6'
 '\xda\x152'
 '\xc7\xd4\x061'
'\x14'
 '\xa6\x81\x068'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x18'
 '\xca\x80\x061'
 '\x024'
 '\xa6\x97\x010'
 '\x022'
 '\x023'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xe6\xff\x056'
 '\x028'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x039'
'*'
 '\xde40'
 '\xa6\xca\x052'
 '\x024'
 '\xa6\x97\x011'
 '\x023'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
' '
 '\xca47'
 '\xf6\xe0\x060'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'X'
 '&0'
 '^2'
 'f3'
 '\xcb\x061'
'\x16'
 '\xa2\xfd\x058'
 '\x029'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x037'
'\x18'
 '\xc6\xfc\x050'
 '\x028'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x12'
 '\xe2\xfb\x054'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x026'
 '\x027'
 '\x038'
'\x82\x01'
 '60'
 '^1'
 'f3'
 'f4'
 'f5'
 '\xcf\x012'
'\x14'
 '\xd2\xfa\x051'
 '\xa6\x97\x012'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x16'
 '\xf6\xf9\x053'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x1a'
 '\x92\xf9\x051'
 '\x027'
 '\x028'
 '\xa6\x97\x010'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x039'
'\x1a'
 '\xae\xf8\x055'
 '\x026'
 '\x027'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x028'
 '\x039'
'\x0e'
 '\x82%1'
 '\xee\xe9\x060'
 '\x022'
 '\x033'
'\x80\x01'
 '60'
 'b1'
 'f3'
 'f4'
 'f5'
 '\xfb\x142'
'\x18'
 '\xda+7'
 '\x86\xcb\x056'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x028'
 '\x039'
'\x16'
 '\xfe\xf5\x051'
 '\xa6\x97\x010'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\x9a\xf5\x056'
 '\x027'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x028'
 '\x039'
'\x18'
 '\xb6\xf4\x053'
 '\x025'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x024'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\n'
 '\xf6\x8a\x070'
 '\x021'
 '\x022'
 '\x023'
 '\x034'
'\x12'
 '\x9e\xf3\x056'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x038'
'&'
 '\x120'
 '_1'
'\x16'
 '\xb6\xf2\x055'
 '\x029'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x026'
 '\x027'
 '\x038'
'\x10'
 '\xda\xf1\x050'
 '\x021'
 '\xa6\x97\x012'
 '\x023'
 '\x024'
 '\x035'
'\x10'
 '\xba\x88\x071'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'\x14'
 '\xca\xf0\x052'
 '\x026'
 '\xa6\x97\x011'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x038'
'\x84\x01'
 '*0'
 'b1'
 'j2'
 'f3'
 'k4'
'\x18'
 '\xc2$1'
 '\x86\xcb\x053'
 '\xa6\x97\x012'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
','
 '\x96%2'
 '\xd2\xc9\x050'
 '\x025'
 '\x026'
 '\x027'
 '\xa6\x97\x011'
 '\x023'
 '\x024'
 '\x028'
 '\x039'
'\x1a'
 '\xfe\xed\x052'
 '\x024'
 '\x028'
 '\xa6\x97\x010'
 '\x021'
 '\x023'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x1a'
 '\x96"3'
 '\x86\xcb\x051'
 '\xa6\x97\x010'
 '\x022'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x0c'
 '\xb2\xec\x050'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x034'
'\xc2\x01'
 '20'
 '\xfc\x01\x02L0'
 '\xe5\x01\x02U0'
'b'
 '61'
 'b3'
 '\xe6\x020'
 '\x9e\x0c2'
 '\xb7\x064'
'\x18'
 '\x82 8'
 '\xaa\xe2\x060'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x1c'
 '\xa6\xea\x053'
 '\x024'
 '\x025'
 '\x027'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x026'
 '\x028'
 '\x039'
','
 '"0'
 '^1'
 '\xab\xb2\x052'
'\x14'
 '\x9e\xe9\x055'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x16'
 '\xc2\xe8\x057'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x028'
 '\x039'
'4'
 '\x1a0'
 'V1'
 'g2'
'\x12'
 '\xe6\xfe\x061'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x1a'
 '\xee\xe6\x050'
 '\x021'
 '\x028'
 '\xa6\x97\x012'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x08'
 '\x8a\xe6\x052'
 '\xa6\x97\x010'
 '\x031'
'\x96\x01'
 '>0'
 '\x9a\x011'
 'j2'
 'f3'
 'j5'
 '\xd3\xcd\x064'
'"'
 'Z6'
 '\xc2\xe4\x051'
 '\x025'
 '\xa6\x97\x012'
 '\x023'
 '\x024'
 '\x027'
 '\x028'
 '\x039'
'\x0f'
 '\xe2\xfb\x06A'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x03F'
'\x1c'
 '\xba\x110'
 '\xca\xd2\x059'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'\x1c'
 '\x9a\xe3\x050'
 '\x024'
 '\x025'
 '\x029'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x026'
 '\x027'
 '\x038'
' '
 '\x86\x176'
 '\xb2\xcb\x050'
 '\x023'
 '\xa6\x97\x011'
 '\x022'
 '\x024'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x08'
 '\xca\x160'
 '\xab\xe2\x061'
'\x1a'
 '\x120'
 '_1'
'\x16'
 '\x9a\xe1\x051'
 '\x023'
 '\xa6\x97\x012'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x04'
 '\xe2\xf7\x060'
 '\x031'
'\x0e'
 '\xc6\xf7\x061'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x037'
'D'
 '"0'
 'b1'
 '\xdf\xca\x062'
'\x18'
 '\xb6\x143'
 '\x86\xcb\x052'
 '\xa6\x97\x011'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xda\xde\x050'
 '\x026'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'l'
 '*0'
 '^1'
 'j2'
 'b3'
 'g4'
'\x16'
 '\xca\xdd\x052'
 '\x026'
 '\xa6\x97\x011'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x1a'
 '\xea\x114'
 '\x86\xcb\x057'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x025'
 '\x026'
 '\x028'
 '\x039'
'\x18'
 '\x82\x116'
 '\xaa\xe2\x060'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x16'
 '\xa6\xdb\x055'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x0e'
 '\xe6\xf1\x060'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'X'
 '*0'
 '^1'
 'f3'
 '\x97\xc4\x062'
'\x1a'
 '\xd2\xd9\x053'
 '\x027'
 '\x028'
 '\x029'
 '\xa6\x97\x011'
 '\x022'
 '\x024'
 '\x025'
 '\x036'
'\x18'
 '\xf6\xd8\x051'
 '\x026'
 '\xa6\x97\x010'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x12'
 '\x92\xd8\x052'
 '\x023'
 '\xa6\x97\x010'
 '\x021'
 '\x024'
 '\x025'
 '\x036'
'^'
 '20'
 'Z2'
 'f3'
 'f4'
 '\xf7\xc0\x061'
'\x16'
 '\x8e\x0c6'
 '\xaa\xe2\x061'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x18'
 '\xba\xd6\x053'
 '\x029'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'\x16'
 '\xd6\xd5\x052'
 '\xa6\x97\x010'
 '\x021'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x06'
 '\x96\xec\x060'
 '\x021'
 '\x032'
'\x9a\x01'
 'B0'
 'b1'
 '\x86\x012'
 '\xd2\x013'
 '\xd5\xd0\x05\x0240'
'*'
 '\x82\t7'
 'b1'
 '\xa6\xca\x052'
 '\xa6\x97\x013'
 '\x024'
 '\x025'
 '\x026'
 '\x028'
 '\x039'
'\x1e'
 '^1'
 '\xc6\x072'
 '\xaa\xe2\x060'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\t'
 '\xea\xe9\x06A'
 '\x02B'
 '\x03C'
'2'
 'b0'
 '\xc2\xd1\x053'
 '\x028'
 '\x029'
 '\xa6\x97\x011'
 '\x022'
 '\x024'
 '\x025'
 '\x026'
 '\x037'
'\x1b'
 '\xe2\xe8\x06A'
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
'\x1c'
 '\xd2\xd0\x050'
 '\x021'
 '\x023'
 '\x027'
 '\xa6\x97\x012'
 '\x024'
 '\x025'
 '\x026'
 '\x028'
 '\x039'
'@'
 '\x1a0'
 '^1'
 'g2'
'\x16'
 '\xd2\xcf\x053'
 '\x029'
 '\xa6\x97\x011'
 '\x022'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'\x1c'
 '\xf6\xce\x050'
 '\x024'
 '\x027'
 '\x028'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x025'
 '\x026'
 '\x039'
'\x0e'
 '\x92\xce\x054'
 '\xa6\x97\x010'
 '\x021'
 '\x022'
 '\x023'
 '\x035'
'\x18'
 '\xca\x024'
 '\x86\xcb\x056'
 '\x028'
 '\xa6\x97\x011'
 '\x022'
 '\x023'
 '\x025'
 '\x037'
'\x12'
 '\xf6\xcc\x051'
 '\xa6\x97\x012'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x038'
'R'
 '\x160'
 '\xa7\x011'
'"'
 'Z2'
 '.3'
 '\x86\xcb\x054'
 '\x025'
 '\xa6\x97\x011'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x0b'
 '\xd2\xe2\x06A'
 '\x02B'
 '\x02C'
 '\x03D'
'\x07'
 '\xa6\xe2\x06A'
 '\x03B'
'0'
 'B5'
 'V6'
 '\xf6\xe0\x060'
 '\x021'
 '\x022'
 '\x023'
 '\x034'
'\x15'
 '\xc6\xe1\x06A'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x03I'
'\x13'
 '\xf2\xe0\x06A'
 '\x02B'
 '\x02C'
 '\x02D'
 '\x02E'
 '\x02F'
 '\x02G'
 '\x03H'
'\x02'
 '\xaf\xd2\x06T'
'\x02'
 '\x81\x7f\x02SE'
'\xe8\x01'
 '\x92\x01S'
 '\xbc\x07\x0bTONAL MARK '
 '\xd5\xfe\x05\x0fCOMBINING GEMIN'
'\xd2\x01'
 '8\x08YLLABLE '
 '\x9b\xbc\x04E'
'\xd0\x01'
 '\xb2\x01B'
 '\x02M'
 '"C'
 'rD'
 '"G'
 '\x82\x01K'
 '\x02Q'
 '\x02X'
 '"N'
 '"P'
 '(\x02FW'
 '"S'
 '~T'
 '&H'
 '\x02J'
 '\x02L'
 '\x02R'
 '\x02W'
 '\x02Y'
 '\x17Z'
'\x08'
 '\x96\x03W'
 '\xcf\xc2\x06O'
' '
 '&C'
 '\x92\x04H'
 '\x8f\xc1\x06O'
'\x1c'
 '\xbe\x04H'
 '\xc2\xc0\x05A'
 '\xaegE'
 '\xfa/I'
 '\x02O'
 '\x03U'
'\x04'
 '\xc6\x03D'
 '\x8f\xc1\x06O'
'\x1c'
 'P\x02GW'
 '\xd4\x02\x07LOTTAL '
 '2Y'
 '\xdf\xc0\x06O'
'\n'
 '\xc2\xc3\x05A'
 '\xaegE'
 '\xfb/I'
'\x10'
 '\xd6\x02Y'
 '\xdf\xc0\x06O'
'\x04'
 '\x86\x02Y'
 '\x8f\xc1\x06O'
'\n'
 '&W'
 '\xc2\x01H'
 '\x8f\xc1\x06O'
'\x06'
 '\xda\xa9\x06E'
 '\xfb/I'
'\x1a'
 'L\tEBATBEIT '
 'RH'
 '2S'
 '\xdf\xc0\x06O'
'\x08'
 '\xbe\xba\x03B'
 '\x02F'
 '\x02M'
 '\x03P'
'\x06'
 '"H'
 '\x02Z'
 '\x8f\xc1\x06O'
'\x02'
 '\x8b\xc1\x06O'
'\x10'
 '\x1aZ'
 '\xdf\xc0\x06O'
'\x0e'
 '\xbe\xc0\x05A'
 '\xaegE'
 '\xfa/I'
 '\x02O'
 '\x03U'
'\x14'
 '\x82\x01D'
 'JH'
 '\x1eK'
 '.R'
 '\x00\x07SHORT R'
 '\xa8\x92\x01\x03CHI'
 '\xed\xf0\x04\x03YIZ'
'\x06'
 '0\x04ERET'
 '\x9d\xb6\x05\x02IF'
'\x05'
 '\x11\x02-H'
'\x02'
 '\xd9\x83\x06\x02ID'
'\x04'
 '\xe6\x82\x03U'
 '\x85\xb3\x02\x02EN'
'\x02'
 '\xc1\xa0\x01\x03IKR'
'"'
 'VA'
 '\xe6\x01L'
 '\xc6\x01O'
 '8\x03IVE'
 'BU'
 '\x89\xd5\x03\x02ER'
'\x04'
 '\xb0\x01 LLING DIAGONAL IN WHITE CIRCLE I'
 '\xc1\xf0\x02\x05CSIMI'
'\x02'
 '\xed\xd1\x06\x07N BLACK'
'\n'
 'RA'
 '8\x04OWER'
 '\xb1\xfe\x05\x08EUR-DE-L'
'\x04'
 '\xc0~\x06G IN H'
 '\x8b\xe0\x04T'
'\x05'
 '\x0b '
'\x02'
 '\xc9\xf8\x05\x06PUNCTU'
'\x08'
 '\x1aU'
 '\xd3\xb2\x04R'
'\x06'
 '\x1aR'
 '\x93\xa5\x03N'
'\x04'
 '\x1d\x05 DOT '
'\x04'
 '\xda\x84\x06P'
 '\x9f\x11M'
'\x06'
 '\x88\xe2\x05\x07NERAL U'
 '\xec2\x06EL PUM'
 '\xcf:S'
'\xfe\x04'
 'jE'
 '\xa8\x07\nLAGOLITIC '
 '\xc0\x0b\x05REEK '
 '\xf3#U'
'X'
 '4\x02AR'
 'i\x07ORGIAN '
'\x07'
 '\x1d\x05 WITH'
'\x04'
 '\x80\x93\x04\x05OUT H'
 '\xedR\x05 HAND'
'R'
 '`\x07LETTER '
 'q\rSMALL LETTER '
'\x06'
 'X\x05U-BRJ'
 '\xc8\x89\x01\x07TURNED '
 '\xaf\xfd\x04A'
'\x02'
 '\x83\x87\x06G'
'L'
 '\xf2\x01C'
 'FG'
 '"H'
 '6J'
 '"K'
 '\x1eP'
 '\x1eR'
 '\x16S'
 '"Z'
 '\xd4\xd2\x01\x02TA'
 '\x8e\xa5\x02L'
 '\xea\x8a\x02V'
 '\xe29B'
 '\x02M'
 '\x02X'
 '\xc6\x04D'
 '\x0eA'
 '\x02E'
 '\x02I'
 '\x02O'
 '\x02U'
 'fN'
 '\x02Q'
 '\x8f\x05W'
'\x08'
 '&H'
 '\xd2\xbb\x06I'
 '\xa7\x07A'
'\x04'
 '\xf2\xc2\x06I'
 'sA'
'\x04'
 '\x86\xbe\x06H'
 '\xd3\x04A'
'\n'
 '\xd2\xd4\x01A'
 '\xd6\xf3\x04I'
 '\x02O'
 ';E'
'\x04'
 '\xde\xba\x06I'
 '\xd7\x02H'
'\x04'
 '\xe2\xc1\x06A'
 'gH'
'\x04'
 '\xaa\xc2\x06H'
 '\x0fA'
'\x02'
 '\x9b\xc7\x06A'
'\x04'
 '\xe6\x82\x06H'
 '\xb3>A'
'\x04'
 '\xf6\xc0\x06E'
 'gH'
'\xbc\x01'
 '8\x06CAPITA'
 '\x01\x04SMAL'
'^'
 '-\tL LETTER '
'^'
 '\xa2\x02B'
 '*D'
 'H\x04CHRI'
 '\x16F'
 ',\x05GLAGO'
 '\x16I'
 '\xee\x01L'
 'RM'
 '\x1eO'
 '\x1eP'
 '2S'
 '\xb6\x01T'
 'fV'
 '\x16Y'
 'ZZ'
 '\xa2\xab\x02K'
 '\xa0\n\x03RIT'
 '\xbcp\x03NAS'
 '\xac\xa8\x01\x02HE'
 '\x92-U'
 '\x85|\x02AZ'
'\x04'
 '\xe2\x02I'
 '\x8d\xe8\x05\x02UK'
'\x06'
 'D\x03JER'
 '\xdc\xf9\x01\x02ZE'
 '\xd1\x8d\x04\x02OB'
'\x02'
 '\xfb\x95\x06V'
'\x04'
 '\xc8\xc0\x02\x02RI'
 '\x8f\xeb\x03I'
'\x02'
 '\xbb\x95\x06L'
'\r'
 'h\x07OTATED '
 '\\\x02ZH'
 '\xe9\xde\x03\tNITIAL IZ'
'\x04'
 '&B'
 '\x19\x05SMALL'
'\x02'
 '\x0bI'
'\x02'
 '\x0bG'
'\x02'
 '\xc1\x80\x05\x02 Y'
'\x04'
 '\xbe\xcd\x04I'
 '\xa7\xf3\x01E'
'\x04'
 'L\tATINATE M'
 '\xd5\xb9\x02\x04JUDI'
'\x02'
 '\xb1j\x03YSL'
'\x04'
 '\x8a\xfb\x05N'
 '\x03T'
'\x04'
 '\xb0\x92\x06\x04OKOJ'
 '\x87-E'
'\x0e'
 'zH'
 '\xa8\xfc\x03\x06PIDERY'
 '\xf4\x93\x02\x03LOV'
 '\xd9\r\x08MALL YUS'
'\x06'
 ' \x02TA'
 '\xeb\xbd\x06A'
'\x05'
 '\xcb\xbb\x06P'
'\x06'
 '\xf0\xb1\x02\x03VRI'
 '\x8c\x9c\x02\tROKUTASTI'
 '\xd3\xc2\x01S'
'\x02'
 '\xf3\xa9\x06E'
'\x0c'
 '2E'
 '\x82\xb4\x02A'
 '\xaa\x88\x04O'
 '\x03U'
'\x06'
 '\x86\xba\x02S'
 '\xab\xe1\x01R'
'\x04'
 '\xc4\xb7\x02\x03EML'
 '\xe5\x9d\x02\x04HIVE'
'\xd6\x02'
 '\xb6\x04A'
 '\x98\x0f\x08CAPITAL '
 'X\x05DRACH'
 '\x00\x04GRAM'
 '\x16F'
 'D\x1dINSTRUMENTAL NOTATION SYMBOL-'
 '\xca\x02L'
 '\xda\x01M'
 'T\x03XES'
 '\x1eO'
 '\xa6\x01S'
 '\x82\x05T'
 '\xb4\x01\x07KYATHOS'
 'x\x16VOCAL NOTATION SYMBOL-'
 '\xcc\xb6\x02\x0eRHO WITH STROK'
 '\xb4\x86\x02\x03ZER'
 '\x9fQY'
'n'
 '<\nCROPHONIC '
 '\xa7\x0eR'
'j'
 '\xc0\x02\x06ATTIC '
 '\xea\x05C'
 '\\\x03NAX'
 ' \x0cDELPHIC FIVE'
 '\x00\x0eSTRATIAN FIFTY'
 '(\x0bEPIDAUREAN '
 't\x03HER'
 '\xa0\x01\nMESSENIAN '
 '\x17T'
'0'
 'H\x02FI'
 '\xb4\x02\x04ONE '
 '\xcd\x01\x04TEN '
'\x1a'
 '$\x03FTY'
 'i\x02VE'
'\x0b'
 '\x0b '
'\x08'
 '\x16T'
 '\xb7\x04S'
'\x06'
 '0\x07HOUSAND'
 '\xd7\x03A'
'\x05'
 '\xf3\x03 '
'\x11'
 '\x0b '
'\x0e'
 '8\x07HUNDRED'
 '\x12T'
 '\x9b\x03S'
'\x07'
 '\x83\x02 '
'\x06'
 '0\x07HOUSAND'
 '\xbb\x02A'
'\x05'
 '\xd5\x01\x02 T'
'\x0e'
 'bH'
 '0\x07THOUSAN'
 '\xde\xa9\x04Q'
 '\xe1\xc7\x01\x05DRACH'
'\x06'
 ',\x05UNDRE'
 '\xcb\xa9\x04A'
'\x04'
 '\x11\x02D '
'\x04'
 '\x16T'
 '\x8f\x01S'
'\x02'
 '_A'
'\x08'
 '\x1eT'
 'bS'
 '\xaf\x01M'
'\x04'
 '2A'
 '!\x08HOUSAND '
'\x02'
 '\xcd\x9a\x06\x03LEN'
'\x02'
 '\x0bS'
'\x02'
 '\xe1\xb6\x05\x02TA'
'\x04'
 'X\x05ARYST'
 '\x91\x01\x0cYRENAIC TWO '
'\x02'
 'e\x05IAN F'
'\x02'
 '\x11\x02 M'
'\x02'
 '\xcb\xdd\x03N'
'\x06'
 '\x1eF'
 '\x1d\x03TWO'
'\x02'
 '\xf9\xa9\x04\x02IV'
'\x05'
 '\x0b '
'\x02'
 '\xed\xdc\x03\x06DRACHM'
'\x08'
 'p\x08MIONIAN '
 '\xd5\xc4\x01\x0eAEUM ONE PLETH'
'\x06'
 '\x9a\xcb\x03F'
 '\x92\xa3\x02O'
 '3T'
'\x02'
 '\xaf\xee\x05T'
' '
 'X\x08HESPIAN '
 '}\nROEZENIAN '
'\x14'
 '$\x02FI'
 '&T'
 '\xcf`O'
'\x06'
 '\xfe\xc4\x02V'
 '\x8b\xf7\x02F'
'\x08'
 '\x9e\xa6\x04H'
 '\x9a\xd5\x01W'
 "\xcb'E"
'\x0c'
 '$\x02FI'
 '\x89\x08\x02TE'
'\x08'
 '\x90\x08\x03FTY'
 '\x9b\xf1\x03V'
'\x04'
 '\xec\x05\x02OU'
 '\x91\x8f\x06\x03TAB'
'\x14'
 ':L'
 '\xb6\nR'
 'BD'
 '\xc9\x8e\x06\x03KAI'
'\x0c'
 '\xd6\x08E'
 '\xd3\x02U'
'\x02'
 '\xb7\x9e\x04M'
'\x04'
 '(\x03IVE'
 '\x01\x03OUR'
'\x02'
 '\xd9\r\x02 O'
'J'
 'F1'
 'F2'
 '>3'
 '>4'
 '\xb6\x0c5'
 '\x8a\x98\x067'
 '\x038'
'\x11'
 '\xf6\xa5\x061'
 '\x022'
 '\x023'
 '\x024'
 '\x027'
 '\x028'
 '\x039'
'\x0f'
 '\xb2\xa5\x063'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x039'
'\x0c'
 '\xf6\xa4\x060'
 '\x022'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x11'
 '\xba\xa4\x060'
 '\x022'
 '\x023'
 '\x025'
 '\x027'
 '\x028'
 '\x039'
'\x0c'
 'h\x14ETTER SMALL CAPITAL '
 'Y\x02IT'
'\n'
 '6P'
 '\xf2\xeb\x02G'
 '\xae\x9e\x02R'
 '\xcbRL'
'\x04'
 '\xce\xf5\x05S'
 '\x87-I'
'\x02'
 '\xd3\x99\x04R'
'\x04'
 'P\x04ETRE'
 '\x8d\xe3\x05\nUSICAL LEI'
'\x02'
 '\xc9\x98\x04\x02TE'
'\x08'
 'd\x0bNE HALF SIG'
 '\xdc\x92\x04\x02BO'
 '\xad\x04\x03UNK'
'\x04'
 '\x0bN'
'\x05'
 '\xbd\x95\x04\x07 ALTERN'
'\x1a'
 '\x84\x01\x05MALL '
 '\xb5\x03\x16UBSCRIPT SMALL LETTER '
'\x10'
 '$\x02LE'
 '\xde\x01R'
 'CD'
'\n'
 '\x1d\x05TTER '
'\n'
 '\x84\x01\nARCHAIC SA'
 '\x16S'
 '\xcc\xbd\x02\nPAMPHYLIAN'
 '\xaf\x98\x03H'
'\x02'
 '\xab\x95\x02M'
'\x04'
 '\xae\xef\x05H'
 "\xcb'A"
'\x04'
 ')\x08EVERSED '
'\x04'
 '\x12D'
 '+L'
'\x02'
 '%\x07OTTED L'
'\x02'
 '\x0bU'
'\x02'
 '\x91\x8e\x06\nNATE SIGMA'
'\n'
 '\xea\xe4\x02G'
 '\xde C'
 '\x02P'
 '\xd2\xfd\x01R'
 '\x93QB'
'\x0c'
 't\x05HREE '
 '<\x07RYBLION'
 ',\x03WO '
 '\xd5\x86\x05\x04ALEN'
'\x04'
 '\x96\x01O'
 '\xfd\x8f\x04\x07QUARTER'
'\x02'
 '\x15\x03 BA'
'\x02'
 '\x9b\x86\x06S'
'\x04'
 '.O'
 '\xfd\x8f\x04\x05THIRD'
'\x02'
 '\xe9\xdb\x02\x02BO'
':'
 'V2'
 '\x025'
 '\x9a\xee\x051'
 '\xf2)3'
 '\x024'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\r'
 '\x86\x98\x060'
 '\x021'
 '\x022'
 '\x023'
 '\x034'
'\x14'
 'l\x02AR'
 '(\x07JARATI '
 'A\x0cRMUKHI SIGN '
'\x02'
 '\x11\x02AN'
'\x02'
 '\xcb\x87\x06I'
'\n'
 '\xd2\x84\x05R'
 '\xde\x0cV'
 '1\x06LETTER'
'\x08'
 '\xfc\x88\x02\x08ADAK BIN'
 '\xe8\x9a\x02\x02UD'
 '\xec1\x03YAK'
 '\xfb\x9c\x01V'
'\x9a\x03'
 '^A'
 '\x9e\x1dE'
 '\xee I'
 'vO'
 '\x9c\x01\x02YP'
 '\xcd\xca\x03\x04RYVN'
'\xec\x01'
 'T\x05NGUL '
 '\x91\xb3\x04\nMMER AND P'
'\xea\x01'
 '8\tCHOSEONG '
 '\xeb\x06J'
'D'
 '\x94\x02\x06IEUNG-'
 '\x1c\x06MIEUM-'
 '(\x06NIEUN-'
 '*P'
 '|\x06RIEUL-'
 '\xb8\x01\x05SSANG'
 'p\x07TIKEUT-'
 '\xb8\x05\x05HIEUH'
 '\xe1\x02\x06KIYEOK'
'\x04'
 '\xfa\tR'
 '\xa3\x0bH'
'\x06'
 '\x9e\x10S'
 '\x8e\x02T'
 '\xfb\x01K'
'\x06'
 '\xf6\x0fS'
 '\xa6\x01C'
 '\xbf\x03H'
'\x08'
 '<\x05IEUP-'
 '\xa9\r\x05HIEUP'
'\x06'
 '\xde\x10K'
 '\xdc\x02\x06SIOS-T'
 '7H'
'\x16'
 '>K'
 '*S'
 '\x92\x0fC'
 'jT'
 '\xc2\x01P'
 '\xb7\x01M'
'\x06'
 '\xde\rA'
 '\x92\x02H'
 '\xb7\x02I'
'\x08'
 '(\x04SANG'
 '\xbb\xf0\x03I'
'\x06'
 '\xca\x0fT'
 '\xc2\x01P'
 ';K'
'\x08'
 '\xbc\x0b\x05CIEUC'
 '\x0c\x06YEORIN'
 '\x88\x04\x05SIOS-'
 '\xf7\x01T'
'\n'
 '\xea\x05R'
 '\xc2\x06S'
 '\xa6\x01C'
 '\xaa\x02P'
 '\xb7\x01M'
'\xa6\x01'
 '\\\tONGSEONG '
 '\xa5\x10\tUNGSEONG '
'n'
 '\x80\x02\x06CIEUC-'
 '2K'
 '\x8c\x01\x06MIEUM-'
 'd\x06NIEUN-'
 'NP'
 '\x9c\x02\x06RIEUL-'
 '\xbe\x02S'
 '\x88\x04\x07TIKEUT-'
 '\x85\x02\tYESIEUNG-'
'\x04'
 '\xb8\x0b\x05SSANG'
 '\x97\x01P'
'\x0c'
 'L\x06IYEOK-'
 '\xc5\x01\x08APYEOUNR'
'\n'
 '\xb2\x01C'
 '\x86\x08N'
 '\x1eK'
 '\xfe\x01P'
 '\x97\x01H'
'\x08'
 'P\x05PIEUP'
 '\x9a\x08C'
 '\x12N'
 '\x01\x06SSANGN'
'\x02'
 '\xe7\x06-'
'\x04'
 '\x12C'
 '\x13R'
'\x02'
 '\xdf\tH'
'\x02'
 '\x11\x02IE'
'\x02'
 '\x93\xf9\x05U'
'\x14'
 'd\x07ANSIOS-'
 '\x1c\x07HIEUPH-'
 '\x1d\x05IEUP-'
'\x04'
 '\xee\x04K'
 '\x8f\x04P'
'\x04'
 '\x92\x05S'
 '\xaf\x04T'
'\x0c'
 '`\x04SIOS'
 '\xc4\x01\x07RIEUL-P'
 '\xde\x04T'
 'rC'
 '\x87\x02M'
'\x02'
 '\x9d\x06\x02-T'
'\x0e'
 '\x90\x01\x06PIEUP-'
 '<\x02YE'
 'P\x06KIYEOK'
 '\x00\x05MIEUM'
 '\xd5\x05\x05SSANG'
'\x04'
 '\x16P'
 '\xdf\x04T'
'\x02'
 '\xd1\xcb\x04\x04HIEU'
'\x04'
 '@\x08ORINHIEU'
 '\x8d\xc1\x04\x02SI'
'\x02'
 '\x0bH'
'\x02'
 '\x0b-'
'\x02'
 '\xaf\x06H'
' '
 '4\x04IOS-'
 '\x9d\x01\x04SANG'
'\x0e'
 'FK'
 '4\x03PAN'
 '\x8a\x03C'
 '\xb2\x01T'
 '6H'
 '#M'
'\x02'
 '\x0bA'
'\x02'
 '\xe9\x02\x06PYEOUN'
'\x02'
 '\x0bS'
'\x02'
 '\xf7\xe2\x03I'
'\x12'
 '\x8e\x01C'
 '\x12N'
 '\x1c\x07RIEUL-K'
 '$\x05SIOS-'
 '8\x06TIKEUT'
 '\xa2\x01P'
 '\xb7\x01M'
'\x02'
 '\x8b\x02I'
'\x02'
 '\xc1\xb9\x05\x02IE'
'\x02'
 '\x0bH'
'\x02'
 '\xb1\x0f\x02IE'
'\x04'
 '\x16T'
 '\xfb\x01K'
'\x02'
 '\x89\xff\x04\x03IKE'
'\x05'
 '\x0b-'
'\x02'
 '\x93\x01P'
'\x0c'
 '2C'
 'RP'
 ' \x04SIOS'
 'CT'
'\x04'
 '\x12H'
 '#I'
'\x02'
 '\x81\x93\x05\x03IEU'
'\x02'
 '\xf1\xfa\x05\x02EU'
'\x02'
 '\xe1\xc1\x05\x03IEU'
'\x05'
 '\x0b-'
'\x02'
 '\x0bK'
'\x02'
 '\x0bI'
'\x02'
 '\x91\xd9\x04\x02YE'
'\x02'
 '\x85\xfe\x04\x03HIE'
'\x04'
 '\x12H'
 '#M'
'\x02'
 '\xe9\xe9\x05\x03IEU'
'\x02'
 '\xc9\xf7\x05\x02IE'
'8'
 'VA'
 '4\x03EU-'
 '(\x02I-'
 '|\x02O-'
 ' \x02U-'
 '/Y'
'\x06'
 '\x90\xda\x02\x05RAEA-'
 '\xf7\r-'
'\x08'
 '\xa2\xca\x05E'
 '\xea/A'
 '\x03O'
'\x10'
 '*Y'
 '\x96\xd2\x01O'
 '\xa7\xa7\x04I'
'\x0c'
 '.A'
 '\xa2\xc9\x05E'
 '\xea/O'
 '\x03U'
'\x04'
 '\x96\xcb\x05-'
 '\xf3-E'
'\x08'
 '\xa2\x01Y'
 '\xa3\xd0\x01O'
'\x04'
 '\xa2\xd1\x01I'
 '\xb5\xf9\x03\x02YE'
'\x0e'
 'T\x02O-'
 ' \x02U-'
 '\xd8\xb2\x03\x03EO-'
 '\x85\x80\x02\x02A-'
'\x06'
 '\xca\xc7\x05A'
 '\x8b\x02E'
'\x04'
 '\xea\xf6\x05A'
 ';O'
'\x9e\x01'
 '\xb2\x01A'
 '\x9c\x05\x05BREW '
 '\xb0\x03\x11LMET WITH WHITE C'
 '\x1d\x0bXAGRAM FOR '
'\x12'
 'd\x03VY '
 '\xf1\xe6\x05\x10DSTONE GRAVEYARD'
'\x10'
 '\xb0\x02\x06CIRCLE'
 '\xc4,\x0fEXCLAMATION MAR'
 '\xd0\xe9\x01\x04LARG'
 '\x84\x85\x01\x0eOVAL WITH OVAL'
 '\xd1\xd3\x02\x13WHITE DOWN-POINTING'
'\t'
 '@\x06 WITH '
 '\xf9\xa5\x04\x04D SA'
'\x04'
 'L\x07STROKE '
 '\x85\x9a\x03\x06CIRCLE'
'\x02'
 '\x15\x03AND'
'\x02'
 '\x15\x03 TW'
'\x02'
 '\x0bO'
'\x02'
 '\x19\x04 DOT'
'\x02'
 '\x97\x9a\x05S'
'\n'
 '\x8c\x01\x10ACCENT ATNAH HAF'
 '\x16P'
 '\xe5\xee\x05\nMARK LOWER'
'\x02'
 '\xc7\x8d\x03U'
'\x06'
 't\x05OINT '
 '\xd9\xca\x05\x12UNCTUATION NUN HAF'
'\x04'
 '\xe8\xa0\x04\x12HOLAM HASER FOR VA'
 '\xb5\xc2\x01\nQAMATS QAT'
'\x02'
 '\x81\xfa\x04\x02RO'
'\x80\x01'
 '\xce\x02A'
 'bB'
 '\x90\x01\x02CO'
 'ZD'
 '\xc2\x02F'
 '>G'
 '(\x04HOLD'
 '\xc0\x01\x02IN'
 'p\x02MO'
 ':O'
 '~P'
 't\x02RE'
 'BS'
 '\xea\x01T'
 '\xac\x05\x0cYOUTHFUL FOL'
 'zW'
 '\xe4\x8b\x05\x05LIMIT'
 '\xc5G\tENTHUSIAS'
'\x06'
 '\xbc\x01\x04FTER'
 '\x8c\xfd\x04\x04BUND'
 '\xa9\x01\x05PPROA'
'\x06'
 '\\\x05EFORE'
 '\xc4\x9d\x01\x06ITING '
 '\x01\x04REAK'
'\x02'
 '\xbd\x9d\x05\x07 COMPLE'
'\x06'
 '\x1aN'
 '\xf3\xf3\x04M'
'\x04'
 '\xb0\xe7\x04\x04TEMP'
 '\x8d\x04\x03FLI'
'\x0e'
 'rE'
 'JI'
 '\xb2\xf8\x04U'
 '\xa10\x11ARKENING OF THE L'
'\x06'
 '\xb4\xef\x04\x05VELOP'
 '\xfe\x04C'
 '\xbd\x06\x02LI'
'\x04'
 '\xa4\xea\x04\x15FFICULTY AT THE BEGIN'
 '\xe5g\x04SPER'
'\x04'
 '\x98\xef\x04\x02OL'
 '\xc9\x04\x05ELLOW'
'\x0c'
 '$\x05ATHER'
 '?R'
'\x02'
 '\xe1\xcd\x05\nING TOGETH'
'\n'
 '(\x04EAT '
 '\xf3\x96\x05A'
'\x08'
 '\x16P'
 '\xe7\x05T'
'\x06'
 '\x16O'
 '\xa7\x05R'
'\x04'
 '\xac\x02\x02SS'
 '\x9f\xca\x05W'
'\x08'
 '2N'
 '\x92\xf0\x04C'
 '\x8d\x06\x03FLU'
'\x04'
 '\xb0\xe4\x04\x05ER TR'
 '\xe9\x11\x02OC'
'\x04'
 '\x8c\x89\x04\x03UTH'
 '\xa5k\x03DES'
'\x06'
 ',\x05BSTRU'
 '\x15\x02PP'
'\x02'
 '\xfb\x95\x05C'
'\x04'
 '\x1aR'
 '\x83\xf2\x04O'
'\x02'
 '\xd9\xcc\x05\x02ES'
'\x06'
 '\xd8\xda\x03\x0bUSHING UPWA'
 '\xdc\x92\x01\x04ROGR'
 '\xbd&\x02EA'
'\x06'
 '\x1aT'
 '\xff\xdf\x04V'
'\x04'
 '\xea\xc1\x01R'
 '\xdb\xaf\x03U'
'\x08'
 '\x84\x01\x05MALL '
 '\xd0\xca\x01\x0bPLITTING AP'
 '\xf5\xfd\x01\x06TANDST'
'\x04'
 '\x18\x02PR'
 '+T'
'\x02'
 '\x8d\xf2\x04\x05EPOND'
'\x02'
 '\xa1\xd2\x05\x02AM'
'\x1e'
 ',\x03HE '
 '\xe1\x05\x03REA'
'\x1c'
 '\xd6\x02A'
 '\x8a\x01C'
 '\x9c\x01\x04FAMI'
 '\x14\tRECEPTIVE'
 '\x1eW'
 '\x80\xef\x01\x06GENTLE'
 '\x94=\x11KEEPING STILL MOU'
 '\x84\xef\x02\rMARRYING MAID'
 "\xf9'\tJOYOUS LA"
'\x06'
 ':R'
 '\x85\xa1\x03\x08BYSMAL W'
'\x04'
 '\xb4\x99\x01\nOUSING THU'
 '\xaf\xe7\x03M'
'\x06'
 '\x84\x01\nREATIVE HE'
 '\xd4q\x04AULD'
 '\xd9\x9a\x03\tLINGING F'
'\x02'
 '\xcf\x9b\x05A'
'\x02'
 '\xfb\xfe\x04L'
'\x02'
 '\xf1\xab\x02\x02 E'
'\x04'
 '\x92\xe6\x04E'
 '\xf5Z\x05ANDER'
'\x02'
 '\xf7\xcb\x05D'
'\x04'
 '\xd0\xe7\x04\x10ORK ON THE DECAY'
 '\x81\x05\x02AI'
'\x04'
 '\\\x08STORIC S'
 '\x99\xc2\x05\tGH VOLTAG'
'\x02'
 '\xe3\xee\x03I'
'\x06'
 'X\tRIZONTAL '
 '\xf9\xe9\x04\x07T BEVER'
'\x04'
 '\xe2\xc0\x05M'
 '\xdd\n\x08BLACK HE'
'\x04'
 'h\x06ODIAST'
 '\x8d\x80\x05\x0eHEN WITH DIAER'
'\x02'
 '\x8f\xd0\x05O'
'\xba\x01'
 'x\x10MPERIAL ARAMAIC '
 '\xb2\x01N'
 '\xf9\xe9\x03\x05CE SK'
'>'
 'H\x07NUMBER '
 '\x96\x05L'
 '\xad\x1b\x03SEC'
'\x10'
 '\x16T'
 '\xcf\x08O'
'\n'
 '*E'
 '\x9e\xa2\x03W'
 '\xe7\xf2\x01H'
'\x04'
 '\x0bN'
'\x05'
 '\xb7\xc5\x03 '
'z'
 '\xb4\x01\x0eSCRIPTIONAL PA'
 '\xf6\x06V'
 '\xf1\xe5\x01\x15TERLOCKED FEMALE AND '
'r'
 'H\x06HLAVI '
 '\x95\x02\x07RTHIAN '
'6'
 '0\x07LETTER '
 '\xfb\x04N'
'&'
 '\xe4\x03\x02AL'
 '\x16D'
 '\x16G'
 '\x16S'
 ':Z'
 '\xa2\xe6\x02H'
 '>L'
 '\x1c\x05MEM-Q'
 '\xb2\x01T'
 '"Y'
 '\xf4i\nWAW-AYIN-R'
 '\x8a?B'
 'JK'
 '\x82rN'
 '\x87EP'
'<'
 '\x16L'
 '\x83\x03N'
','
 '!\x06ETTER '
','
 '\xae\x01A'
 '2D'
 '\x16G'
 '\x16S'
 ':Z'
 '\xa2\xe6\x02H'
 '>L'
 '\x1eQ'
 '\xb2\x01T'
 '"Y'
 '\x9e\x0fW'
 '\xdaZR'
 '\x8a?B'
 'JK'
 '\xf2qM'
 '\x12N'
 '\x87EP'
'\x04'
 '\x1aL'
 '\xe7\x85\x05Y'
'\x02'
 '\x8b\x93\x04E'
'\x02'
 '\x9f\xe6\x02A'
'\x02'
 '\xd7\xe6\x02I'
'\x06'
 '\x1aA'
 '\x8f\x85\x05H'
'\x04'
 '\xe6\xe7\x02D'
 '\x17M'
'\x02'
 '\xed\x84\x05\x02AY'
'\x10'
 '!\x06UMBER '
'\x10'
 '*O'
 '\xd6\x99\x03T'
 '\xdb\xb7\x01F'
'\x06'
 '\x0bN'
'\x06'
 '\x0bE'
'\x07'
 '\x8b\xe4\x01 '
'\x06'
 'H\x06ERTED '
 '\xe1\x8b\x01\x06ISIBLE'
'\x04'
 '@\x07INTERRO'
 '\x15\x05UNDER'
'\x02'
 '\xef\x98\x05B'
'\x02'
 '\x0bT'
'\x02'
 '\xc7\xc6\x05I'
'\xba\x01'
 '\x1aA'
 '\xeb\xc1\x01U'
'\xb8\x01'
 'T\nPANESE BAN'
 '\x15\x07VANESE '
'\x02'
 '\xf7\xb7\x05K'
'\xb6\x01'
 '\xac\x02\x0fCONSONANT SIGN '
 'P\x02LE'
 '(\x04RIGH'
 '\xd0\x06\x02PA'
 '\xac\x03\x0eTURNED PADA PI'
 'X\x05SIGN '
 '\x94\x01\x0bVOWEL SIGN '
 '\xa7\xf8\x04D'
'\x06'
 '8\x02KE'
 '\xb0\xfc\x03\x02PE'
 '=\x02CA'
'\x02'
 '\xeb\xf0\x04R'
'`'
 '&F'
 'A\x05TTER '
'\x02'
 ')\x08T RERENG'
'\x02'
 '\x8b\xb7\x05G'
'^'
 '\xde\x01D'
 '\x1aI'
 '0\x02KA'
 'BN'
 'zB'
 '\x02C'
 '\x02G'
 '\x10\x02PA'
 '8\x02RA'
 ' \x02SA'
 '*T'
 'JJ'
 '\xce\xb1\x04A'
 '\xe6sH'
 '\x02L'
 '\x02M'
 '\x02W'
 '\x02Y'
 '\x8a\x17E'
 '\x02O'
 '\x03U'
'\x08'
 '\xd6\x03D'
 '\x0fA'
'\x07'
 '\x9c\xb9\x01\x03 KA'
 '\xdb\x86\x04I'
'\x07'
 '\x0b '
'\x04'
 '\x16S'
 '\xcf\x02M'
'\x02'
 '\x99\x9e\x05\x02AS'
'\x0e'
 '$\x02GA'
 'RY'
 '\xa7\x01A'
'\x07'
 '!\x06 LELET'
'\x05'
 '\xbd\xb1\x01\x06 RASWA'
'\x04'
 '\xa3\x01A'
'\x07'
 '\x0b '
'\x04'
 '\x9a\x01M'
 '\xa5\xfa\x03\x03CER'
'\x05'
 '\xc1\xfc\x03\x03 AG'
'\x07'
 '\x11\x02 M'
'\x04'
 'FU'
 'GA'
'\x08'
 '\x12A'
 '7T'
'\x05'
 '\x11\x02 M'
'\x02'
 '\x0bU'
'\x02'
 '\xef\xf6\x04R'
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
 '\xe5\x99\x04\x02AP'
'\x1c'
 '(\x03DA '
 '\xa1\x03\x02NG'
'\x18'
 '\xa6\x01A'
 'ZL'
 'VP'
 '\x94\xf4\x02\x03MAD'
 'zW'
 '\xfc\xc9\x01\x0bTIRTA TUMET'
 '\xa5=\x07ISEN-IS'
'\x06'
 ',\x03DEG'
 '\x99\xe5\x01\x02ND'
'\x05'
 '\x0b '
'\x02'
 '\x89\xd9\x04\x02AD'
'\x06'
 '&U'
 '\x95\x96\x05\x03ING'
'\x04'
 '\xc4\xb2\x01\x02NG'
 '\xc7\xc9\x03H'
'\x04'
 '*I'
 '\xe1\x98\x04\x04ANGK'
'\x02'
 '\xf1\xf4\x03\x03SEL'
'\x04'
 '\xec\xd8\x03\x05RANGK'
 '\xf3\xd8\x01K'
'\n'
 'p\x05CECAK'
 '\xf2\xf3\x03L'
 '\x94b\x04WIGN'
 '\xdd=\x07PANYANG'
'\x05'
 '\xf5\xf5\x03\x03 TE'
'\x12'
 'p\x04SUKU'
 '*T'
 '@\x04WULU'
 '\xe2\xf2\x03P'
 '\xc1R\x07DIRGA M'
'\x05'
 '\xb5\xb6\x04\x05 MEND'
'\x06'
 '\x1aA'
 '\xb3\xf4\x03O'
'\x04'
 '\x8a\xf4\x03R'
 '\xe7\xb5\x01L'
'\x05'
 '\x19\x04 MEL'
'\x02'
 '\xd3\x93\x05I'
'\x9e\x04'
 '\x16A'
 '\x9f\x0eH'
'\xf4\x01'
 '\xbc\x01\x05ITHI '
 '\xb4\x06\x06NNADA '
 '\xe4\x01\x12TAKANA LETTER AINU'
 '\x15\x07YAH LI '
'\x84\x01'
 '\xc8\x01\x07ABBREVI'
 '\x00\x06ENUMER'
 '2D'
 'T\x07LETTER '
 '\xa6\x02S'
 '\x80\x01\x0bVOWEL SIGN '
 '\xd7\x9a\x04N'
'\x02'
 '\x0bA'
'\x02'
 '\xf9\xa1\x05\x04TION'
'\x06'
 '0\x06OUBLE '
 '\xc7\xc3\x03A'
'\x04'
 '\x8e\x8e\x03S'
 '\xab5D'
'Z'
 '\xce\x01D'
 '\xfe\xc3\x03N'
 '2T'
 '\xae@S'
 '\xba\x01B'
 '\x02C'
 '\x02G'
 '\x02J'
 '\x02K'
 '\x02P'
 '\x02R'
 '\xd2\x18A'
 '\xee\x04I'
 '\x16U'
 '\xd2sH'
 '\x02L'
 '\x02M'
 '\x02V'
 '\x02Y'
 '\x8a\x17E'
 '\x03O'
'\n'
 '&D'
 '\x8a\x97\x05H'
 '\x8b\x17A'
'\x06'
 '\xc6\x92\x05D'
 '\xc2\x04H'
 '\x8b\x17A'
'\x0c'
 '(\x04IGN '
 '\xaf\x8b\x03E'
'\n'
 '6C'
 '\xee~N'
 '\xf2\xc4\x02V'
 '\xf3\xc7\x01A'
'\x02'
 '\x8d\xe9\x02\x02AN'
'\x12'
 '\xd2\xa1\x04A'
 '&I'
 '\x16U'
 '\xda\x8a\x01E'
 '\x03O'
'\x0e'
 'T\x08LETTER L'
 '\x14\x05SIGN '
 '\xb3\xa6\x04V'
'\x02'
 '\x87\xe5\x04L'
'\x08'
 '\xa6}N'
 '\xd8\xc7\x01\x08JIHVAMUL'
 '\x00\x08UPADHMAN'
 '\xff\xe0\x01A'
'\x02'
 '\xbf\xef\x04 '
'`'
 '\x94\x01\x07LETTER '
 '\xe4\x01\x05SIGN '
 ',\x05TONE '
 '\\\x06VOWEL '
 '\x8b\xe8\x04D'
'8'
 '\xc2\x01H'
 '\xee\xf2\x01O'
 '\xc2\x8c\x02K'
 '\x02P'
 '\x02S'
 '\x02T'
 'fN'
 '\xbe\x90\x01B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\x02L'
 '\x02M'
 '\x02R'
 '\x02V'
 '\x02W'
 '\x02Y'
 '\x02Z'
 '\x8a\x17A'
 '\x03I'
'\x04'
 '\xca\x90\x05T'
 '\x8b\x17A'
'\x04'
 '\xda\xa0\x01C'
 '\x8d\xc2\x01\x02SH'
'\x06'
 '$\x05CALYA'
 '\x17P'
'\x05'
 '\x11\x02 P'
'\x02'
 '\xe9\xd9\x02\x03LOP'
'\n'
 '\xb2\xf6\x04E'
 '\x02U'
 '\xfb/O'
'\xaa\x02'
 'H\tAROSHTHI '
 '\xd5\n\x04MER '
'\x82\x01'
 '\xd4\x01\x06DIGIT '
 '(\x07LETTER '
 '\xd8\x02\x07NUMBER '
 'H\x0cPUNCTUATION '
 '\x90\x02\x05SIGN '
 '\xd3\x01V'
'\x08'
 '\xa6\xac\x04F'
 '\xce:O'
 'ST'
'F'
 '\xb2\x01K'
 '*N'
 '*T'
 '\xa6\xb6\x03D'
 '\xaaAS'
 '\xba\x01B'
 '\x02C'
 '\x02G'
 '\x02P'
 '\xa2\x91\x01H'
 '\x02J'
 '\x02L'
 '\x02M'
 '\x02R'
 '\x02V'
 '\x02Y'
 '\x02Z'
 '\x8b\x17A'
'\x06'
 '\xf2\x8a\x05H'
 '\x02K'
 '\x8b\x17A'
'\x06'
 '\xca\x8a\x05N'
 '\x02Y'
 '\x8b\x17A'
'\n'
 '&T'
 '\xfe\x89\x05H'
 '\x8b\x17A'
'\x06'
 '\xba\x85\x05T'
 '\xc2\x04H'
 '\x8b\x17A'
'\x08'
 '\x1aT'
 '\xe7\xbb\x01O'
'\x04'
 '\xfc\x9d\x03\x02WE'
 '\x97\xfc\x01E'
'\x12'
 'BC'
 'BD'
 'BL'
 '8\x05MANGA'
 '\xbbbS'
'\x04'
 '\xe4\xde\x01\x07RESCENT'
 '\xc3\xcb\x02I'
'\x06'
 '\x1aO'
 '\x8f\xb2\x03A'
'\x04'
 '\xd6\xb1\x03U'
 '\x9b\xed\x01T'
'\x04'
 '"I'
 '\xed\xdd\x03\x02OT'
'\x02'
 '\xcf\xa4\x04N'
'\x02'
 '\x8b\x85\x04L'
'\x0c'
 'D\x02BA'
 '\x16C'
 ' \x02DO'
 '\xd6\xf9\x04V'
 '\xff\x01A'
'\x02'
 '\x87\xc7\x04R'
'\x02'
 '\x0bA'
'\x02'
 '\xbb\xd7\x04U'
'\x04'
 '0\x06UBLE R'
 '\xbf\x82\x05T'
'\x02'
 '\xb9\x82\x05\x03ING'
'\x0e'
 ',\x05OWEL '
 '\xc7\xfa\x02I'
'\x0c'
 'D\x05SIGN '
 '\x81\xe1\x04\x06LENGTH'
'\n'
 '\xfc\x95\x05\x08VOCALIC '
 '\xba\x05E'
 '\x02I'
 '\x02O'
 '\x03U'
'\xa8\x01'
 '\xa0\x02\x15CONSONANT SIGN COENG '
 '\xcc\x02\x1dINDEPENDENT VOWEL SIGN COENG '
 'BS'
 '\xfd\x05\x0bVOWEL SIGN '
'D'
 '\x86\x01C'
 '\x02K'
 '*N'
 '2P'
 '\x1eT'
 '6D'
 '\x02L'
 '\xaa\xec\x03S'
 '\xf2{M'
 '\x02R'
 '\x02V'
 '\x02Y'
 '\xea\x16B'
 '\x03H'
'\x08'
 '\xa6\x01H'
 '\x8a\x96\x05A'
 '\x03O'
'\x08'
 '\x96\xe9\x04G'
 '\x02Y'
 '\xf2-A'
 '\x03O'
'\x06'
 'NH'
 '\x8b\x96\x05O'
'\x0c'
 '2H'
 '\x00\x02TH'
 '\x8a\x96\x05A'
 '\x03O'
'\x04'
 '\x86\x96\x05A'
 '\x03O'
'\x08'
 '"Q'
 '\xe5\x8f\x02\x02RY'
'\x04'
 '\xc6\x95\x05E'
 '\x03U'
'V'
 'X\x06YMBOL '
 '\xd9\x89\x05\nIGN ATTHAC'
'T'
 '\x80\x01\x03DAP'
 '\\\nLEK ATTAK '
 '\xba\x01P'
 '<\x05TUTEY'
 'NB'
 '/M'
'\x18'
 '\x16-'
 '\xd7\x03 '
'\x14'
 '\x1eP'
 '\xe6\x02B'
 '/M'
'\x08'
 '\x82\x03I'
 '%\x03RAM'
'\x14'
 '*P'
 'ZB'
 '"M'
 '\x9b\x8b\x05S'
'\x0c'
 '$\x03RAM'
 '\x9b\xe5\x04I'
'\x0b'
 '\x0b-'
'\x08'
 '"B'
 '"M'
 '\xbf\xe4\x04P'
'\x04'
 '\xe6\xe4\x04E'
 '\xd3&U'
'\x02'
 '\xb7\x9f\x04U'
'\x1a'
 '8\x05ATHAM'
 '\x14\x03RAM'
 '[I'
'\x02'
 '\x9b\xf1\x03A'
'\x14'
 '\x12-'
 'w '
'\x10'
 '"B'
 ' \x02PI'
 '\x0fM'
'\x08'
 '\x1eE'
 '%\x03UON'
'\x04'
 '#I'
'\x04'
 '\x15\x03UOY'
'\x04'
 '\x0b '
'\x04'
 '\xdc\xbd\x04\x02KO'
 '\xf1O\x02RO'
'\x06'
 '\xe0\x83\x01\x05COENG'
 '\xc6\xf2\x02A'
 '\xaf\x95\x01O'
'\x8c\r'
 'FA'
 '\xceOE'
 '\xb6\x11I'
 '\xa04\x04ONG '
 'wY'
'\xb2\x05'
 '`\tO LETTER '
 'T\x04RGE '
 '\x85\x02\x04TIN '
'\x08'
 '0\x04FO F'
 '\x92\xdf\x04L'
 '\x03R'
'\x04'
 '\xfe\xb3\x04A'
 '\xdbRO'
'\x08'
 '0\x04ONE '
 'e\x04TWO '
'\x04'
 '\xd2\xb3\x02D'
 'I\x12RING OVER TWO RING'
'\x04'
 '\xee\xb5\x04D'
 '\x81\n\x13RINGS OVER ONE RING'
'\xa2\x05'
 '\xd0\x01\x0fCAPITAL LETTER '
 '\x84\x0f\x12EPIGRAPHIC LETTER '
 '\xc0\x01\x07LETTER '
 '\xd3\x04S'
'\xd8\x01'
 '\x86\x03A'
 '\x96\x01B'
 '"E'
 '\x86\x01G'
 '"I'
 '\\\x07J WITH '
 ' \x07K WITH '
 '\x18\x07L WITH '
 'BM'
 'VO'
 't\x07P WITH '
 '\x18\x07Q WITH '
 '\x1eR'
 '\xbe\x01S'
 '\xb2\x01T'
 '\xac\x01\x02U '
 'NV'
 'T\x07Z WITH '
 '\xca\x0eC'
 '\xde\x06H'
 '\x9a#W'
 '\x17Y'
'\x16'
 'd\x06 WITH '
 '\x8a\x18V'
 '\xaa\xbc\x01L'
 '\xe2\xb0\x03A'
 '\x02O'
 '\x02U'
 '\x03Y'
'\x08'
 '\xd2"M'
 '\xfe\x1dO'
 '\xe7\xaf\x04S'
'\x04'
 '\xee\x18R'
 '\xc3\xb5\x01 '
'\x1a'
 '<\x06 WITH '
 '\xde\x1dG'
 '\xab\xe6\x04T'
'\x14'
 '\xd2\x1cC'
 '\xba\x05D'
 '\xf2\tV'
 '\xca\x13O'
 '\xe7\xaf\x04S'
'\x04'
 '\xa6\x1eL'
 '\x93\xce\x04H'
'\x14'
 '<\x06 WITH '
 '\x9a!N'
 '\xcb\xe1\x04S'
'\x06'
 '\xa2 M'
 '\xff\x1dO'
'\x04'
 '\xe6\xed\x04S'
 '\xcb\x01T'
'\x08'
 '\xb2"D'
 '\x1fS'
'\n'
 '\xb2$D'
 '>H'
 '\x86\x1dM'
 '\x86\xad\x04T'
 '\xd3\rB'
'\x08'
 ',\x06 WITH '
 '\x8b%I'
'\x04'
 '\x8a\xd3\x01H'
 '\xff\x9a\x03T'
'\x0c'
 '0\x06 WITH '
 '\xc7\x80\x05O'
'\n'
 '\x1c\x02LO'
 '\x9f(V'
'\x04'
 "\xc2'N"
 '\xdf\x9d\x04O'
'\x08'
 '\xce)F'
 "'S"
'\x04'
 '\x82+S'
 '\xa7\x12D'
'\x0c'
 'R '
 '\x90-\nEVERSED C '
 '1\x03UM '
'\x08'
 '(\x05WITH '
 '\xa3-R'
'\x06'
 '\x1aT'
 '\xdb\xe9\x04S'
'\x04'
 '\xea\xde\x04A'
 '\xc3\x0cI'
'\n'
 '\x90\x01\x06 WITH '
 "\xf8'\rMALL Q WITH H"
 '\xde\x05A'
 '\x85\x81\x04\x04HARP'
'\x04'
 '\x86-V'
 '\x9f\x10S'
'\x14'
 '\\\x06URNED '
 '\xce\x01 '
 '\xd0/\x02HO'
 '\x9e\x01R'
 '\xcf\xc9\x04Z'
'\n'
 '6A'
 '\xb44\x02IN'
 '\x9a\xc7\x04L'
 '\x03V'
'\x05'
 '\xeb\xca\x01L'
'\x0c'
 ',\x05WITH '
 '\xc7\xf5\x04B'
'\n'
 '\xc65M'
 '\x83\x01O'
'\x08'
 '2 '
 '\xa68I'
 '\xd2\xba\x04E'
 '\xc7\x07Y'
'\x02'
 '\x9d\x1b\x04WITH'
'\x04'
 '\xc69D'
 'wS'
'\n'
 'bI'
 '@\tREVERSED '
 '\xd1\x9e\x03\x07ARCHAIC'
'\x04'
 '\xe8+\x05NVERT'
 '\xd9\x9f\x03\x03 LO'
'\x04'
 '\xda\xf8\x04F'
 '\x03P'
'<'
 '\xb8\x01\x0eSMALL CAPITAL '
 '\xfc\xff\x03\x16VOICED LARYNGEAL SPIRA'
 '\xb32A'
'8'
 '\xbe\x01E'
 '\x1eO'
 '"R'
 'ZT'
 '\xe8\xa9\x01\x02BA'
 '\xee\x12L'
 '\xe6\x87\x03A'
 '\xfa/C'
 '\x02D'
 '\x02F'
 '\x02J'
 '\x02K'
 '\x02M'
 '\x02P'
 '\x02S'
 '\x02U'
 '\x02V'
 '\x02W'
 '\x03Z'
'\x07'
 '\xda\xe3\x04T'
 '\x03Z'
'\x07'
 "\xda'P"
 '\xcf\xcd\x04U'
'\x06'
 '8\x08EVERSED '
 '\xf3\xf0\x04U'
'\x04'
 '\xca\xf4\x04N'
 '\x03R'
'\x07'
 '!\x06URNED '
'\x04'
 '\x8a\xf4\x04E'
 '\x03R'
'\x84\x03'
 '\x84\x01\x05MALL '
 '\xa93\x16UBSCRIPT SMALL LETTER '
'\xf0\x02'
 'h\x0fCAPITAL LETTER '
 '\x1d\x07LETTER '
'\x04'
 '\x96\xba\x01I'
 '\x03U'
'\xec\x02'
 '\xa2\x03A'
 '\xda\x01B'
 '$\x02F '
 'fC'
 '\x8a\x01D'
 '\xc6\x01E'
 '\xc2\x03G'
 'RH'
 'VI'
 '\xb8\x03\x07J WITH '
 'T\x07K WITH '
 '\x96\x01L'
 '\x82\x02M'
 '\xc6\x01N'
 '\xaa\x01O'
 '\xb0\x03\x07P WITH '
 '\x92\x01Q'
 '\xbe\x01R'
 '\x8a\x03S'
 '\xfe\x03T'
 '\xca\x06U'
 '\xfe\x02V'
 '\xf6\x01W'
 '\x16Y'
 'L\x07Z WITH '
 '\xb9\x8e\x01\x02X '
'\x18'
 'h\x06 WITH '
 '>V'
 '\xf4\x1d\x03LPH'
 '\x96\xcf\x04A'
 '\x02O'
 '\x02U'
 '\x03Y'
'\n'
 '\x86\x0bM'
 '\xfe\x1dO'
 '\xf2\x95\x01R'
 '\xf7\x99\x03S'
'\x05'
 '\xf5\xa4\x01\x07 WITH H'
'\x08'
 '" '
 'BR'
 '\xa3\xb2\x01O'
'\x04'
 '\x1d\x05WITH '
'\x04'
 '\xfa+M'
 '\xfb\x8d\x01P'
'\x02'
 '\xd1\x8d\x01\x04OKEN'
'\x08'
 'H\x08UATRILLO'
 '\xd2\xb4\x01 '
 '\x8f\xb0\x03O'
'\x05'
 '\x1d\x05 WITH'
'\x02'
 '\x95\xac\x04\x02 C'
'\x10'
 't\x06 WITH '
 '\x92\x15B'
 '\xbe\x8d\x04E'
 '\xaaCU'
 '\xdd\x03\x08OTLESS J'
'\x08'
 '\x88"\x05HOOK '
 '\xae\x07M'
 '\xfa\x8d\x01P'
 '\xb7\x03C'
'$'
 'h\x06 WITH '
 '\xf2\x01G'
 '\xa0\x17\x02ZH'
 '\x80\x99\x01\x02SH'
 '\x8b\xb6\x03T'
'\x18'
 'fC'
 '\xba\x05D'
 '\xf2\tV'
 '\xca\x13O'
 '\xf2\x95\x01R'
 '\xb0\xc4\x02\x03NOT'
 '\xc7US'
'\x04'
 'A\x0eIRCUMFLEX AND '
'\x04'
 '\x1aM'
 '\x15\x02CA'
'\x02'
 '\x11\x02AC'
'\x02'
 '\x87\xe0\x04R'
'\x04'
 '=\rYPTOLOGICAL A'
'\x04'
 '\x82\xf4\x02L'
 '\xbf\xeb\x01I'
'\x06'
 '*L'
 '\xd6\xb2\x01 '
 '\xbf\x9b\x03H'
'\x02'
 '\xe9\xa9\x04\x04OTTA'
'\x06'
 '6 '
 '\xd4\xd2\x04\x04ALF '
 '\xd7\x06E'
'\x02'
 '\xd1\x1a\x03WIT'
'\x1e'
 'X\x06 WITH '
 '\xfe\x01N'
 '\xec\xa9\x01\x03OTA'
 '\xdf\xb7\x03S'
'\x0e'
 '\x86\x01M'
 'D\x0cOGONEK AND D'
 '\xd8\x1c\tDOT ABOVE'
 '\xd3\x96\x01R'
'\x02'
 '1\nACRON AND '
'\x02'
 '\xab\x1dG'
'\x04'
 '\xd5\x1d\x08OT ABOVE'
'\x0c'
 '!\x06SULAR '
'\x0c'
 '\xa2\xe1\x04D'
 '\x02F'
 '\x02G'
 '\x02R'
 '\x02S'
 '\x03T'
'\x04'
 '\xec \rDOT ABOVE AND'
 '\x9f\xab\x04S'
'\n'
 '"D'
 '\x1eS'
 '\xb7\xad\x01P'
'\x04'
 '\xb6\x1dI'
 '\xf7\x01E'
'\x04'
 '\x1d\x05TROKE'
'\x05'
 '\x19\x04 AND'
'\x02'
 '\xd1\x1c\x02 D'
'\x10'
 'd\x06 WITH '
 'd\x0bONG S WITH '
 '\xdb\xd9\x04U'
'\n'
 '>D'
 '>H'
 '\xfe\xaa\x01P'
 '\xb6\x03C'
 '\xdb\x9b\x03T'
'\x02'
 '\xe5\x9c\x01\x04OUBL'
'\x04'
 '\x16H'
 '\xdb\x1aD'
'\x02'
 '\xfd\xa6\x01\x02IG'
'\x0c'
 '8\x06 WITH '
 '2I'
 '\xbb\xd8\x04U'
'\x06'
 '\xaa\x1cM'
 '\xfa\x8d\x01P'
 '\x8f\x9f\x03T'
'\x04'
 '5\x0bDDLE-WELSH '
'\x04'
 '\x8e\xce\x04L'
 '\xcf\rV'
'\n'
 'd\x06 WITH '
 ',\x0bG WITH TILD'
 '\xcf\xd6\x04U'
'\x06'
 '\xba\x1aM'
 '\xfa\x8d\x01P'
 '\xb7\x03C'
'\x02'
 '\xf7\x83\x04E'
'\x12'
 'L\x06 WITH '
 '\xc8\x02\x04PEN '
 '\xff\xd6\x04O'
'\x0c'
 '\x1c\x02LO'
 '\x9f\x01V'
'\x06'
 'BN'
 '\xc4\x81\x02\x06W RING'
 '\x9b\x9c\x02O'
'\x02'
 ')\x08G STROKE'
'\x02'
 '\x8d\xf6\x02\x06 OVERL'
'\x06'
 'Q\x12ERTICAL LINE BELOW'
'\x07'
 '\x1d\x05 AND '
'\x04'
 '\xb6\x12G'
 '{A'
'\x04'
 '\xf2\x07E'
 '\x03O'
'\x0c'
 '.F'
 '&S'
 '\xfa\x15M'
 '\xfb\x8d\x01P'
'\x02'
 '\xe5\xdc\x02\x04LOUR'
'\x06'
 '\xda\x0bT'
 '\xcd\xaa\x04\x07QUIRREL'
'\x08'
 '(\x06 WITH '
 'kP'
'\x06'
 '\x1eH'
 '"S'
 '\xa7\x12D'
'\x02'
 '\x9d\xb5\x04\x03OOK'
'\x02'
 '\xd9\n\x06TROKE '
'\x02'
 '\x81\x9d\x03\x05 DIGR'
'\x16'
 'F '
 '\xa8\x01\x08EVERSED '
 'a\x02UM'
'\x0c'
 '(\x05WITH '
 '\xf7\x01R'
'\n'
 '\x88\x13\x0eFISHHOOK AND M'
 '\x02M'
 '\xfa\x8d\x01P'
 '\xc6\x9d\x03S'
 '\xcb\x01T'
'\x06'
 '.C'
 '\xf1\x02\x06OPEN E'
'\x05'
 '\x0b '
'\x02'
 '\xbd\xd1\x04\x04WITH'
'\x05'
 '\x0b '
'\x02'
 '\x0bR'
'\x02'
 '\xc9\xe4\x02\x03OTU'
'\x18'
 'd\x06 WITH '
 '~A'
 '\x18\x03CHW'
 '=\x08IDEWAYS '
'\x08'
 '.V'
 '\xe2\x0fM'
 '>S'
 '\xbf\x8d\x01P'
'\x02'
 '5\x0bERTICAL LIN'
'\x02'
 '\xab\xb5\x04E'
'\x02'
 '\xf1\x05\x02LT'
'\x02'
 '\x0bA'
'\x02'
 '\xb5\xa0\x01\x07 WITH R'
'\x0c'
 'nO'
 '8\x04TURN'
 '\x94\x9a\x01\x0bDIAERESIZED'
 '\x9f\xb3\x03U'
'\x07'
 '\x1aP'
 '\x9b\x97\x01 '
'\x02'
 '\xfd\x9b\x01\x02EN'
'\x02'
 '\xa1\xf3\x02\x02ED'
'*'
 '\x90\x01\x06 WITH '
 '.H'
 '\x8a\x02R'
 '>U'
 '\x9a\x97\x01O'
 '\xf0\x1b\tAILLESS P'
 '\x8b\x96\x03Z'
'\x06'
 '\xba\tD'
 '\xae\x02M'
 '\xaf\x91\x01C'
'\x06'
 '@\x0c WITH STRIKE'
 '+O'
'\x02'
 '\xa5\xed\x03\x05THROU'
'\x04'
 '1\nRN WITH ST'
'\x04'
 '\x19\x04ROKE'
'\x05'
 '\x0b '
'\x02'
 '!\x06THROUG'
'\x02'
 '\x95\t\x03H D'
'\x02'
 '\x11\x02ES'
'\x02'
 '\x11\x02IL'
'\x02'
 '\xb3\x9b\x04L'
'\x16'
 ',\x05RNED '
 '\xe3\xc8\x04M'
'\x14'
 '\x8c\x01\x0fH WITH FISHHOOK'
 '.I'
 '6O'
 '\xe4\xa6\x04\x02R '
 '\xd6\x1fA'
 ':G'
 '\x03L'
'\x05'
 '\x0b '
'\x02'
 '\xd9\xa7\x04\x03AND'
'\x05'
 '\x0bN'
'\x02'
 '\xd9\x93\x01\x05SULAR'
'\x04'
 '\xe6\x96\x01P'
 '\x8b\xb0\x03E'
'\x12'
 '`\x06 WITH '
 '\x8c\x8e\x01\x06PSILON'
 '\xde\xb7\x03E'
 '\x03M'
'\x0c'
 '&M'
 '\x82\x01O'
 '\xf3\x95\x01R'
'\x06'
 '\x1d\x05ACRON'
'\x06'
 '\x1d\x05 AND '
'\x06'
 '"G'
 'zA'
 '\xd3\xb0\x04T'
'\x02'
 '\xc9\x87\x04\x02RA'
'\x04'
 '\x1d\x05GONEK'
'\x04'
 '\x1d\x05 AND '
'\x04'
 '\x1aA'
 '\xd3\xb0\x04T'
'\x02'
 '\xc3\x8a\x02C'
'\x0e'
 'D\x06 WITH '
 'vI'
 '\xd2\xba\x04E'
 '\xc7\x07Y'
'\x08'
 'BD'
 '\xb0\x8d\x01\x04RIGH'
 '\xf6\x02P'
 '\xb7\x03C'
'\x02'
 '\x0bI'
'\x02'
 '\xad\xad\x04\x04AGON'
'\x02'
 '\xb5\xe5\x03\tSIGOTHIC '
'\x02'
 '\xd7\x8d\x01 '
'\x04'
 '!\x06 WITH '
'\x04'
 '\x90\x86\x04\x02LO'
 '\xb7&S'
'\x08'
 '*D'
 ':M'
 '>S'
 '\xbf\x8d\x01P'
'\x02'
 '\x0bE'
'\x02'
 '\x15\x03SCE'
'\x02'
 '\xdb\xa9\x04N'
'\x02'
 '\x1d\x05IDDLE'
'\x02'
 '\xe1\xac\x04\x02 T'
'\x02'
 '\xe5\x9f\x04\x03WAS'
'\x14'
 '\x98\x9d\x01\x02SC'
 '\xa2\xa2\x03A'
 '\x02E'
 '\x02I'
 '\x02J'
 '\x02O'
 '\x02R'
 '\x02U'
 '\x02V'
 '\x03X'
'\xd8\x01'
 '0\x02FT'
 '\xd9\x08\x05PCHA '
'D'
 '> '
 '\xc8\x02\x06WARDS '
 '\xe3\xa5\x02-'
'\x1c'
 '\xa0\x01\x0bARROW WITH '
 'zR'
 '\xb0\xc0\x01\x07CLOSED '
 '\xea`D'
 'nL'
 '\x8a\x01S'
 '\xbe\x01T'
 '[V'
'\x04'
 ',\x07CIRCLED'
 '+S'
'\x02'
 '\x11\x02 P'
'\x02'
 '\xb3\xfb\x02L'
'\x02'
 '\xc5_\x04MALL'
'\x06'
 '\xd2\xa2\x02A'
 '\xb5<\x03IGH'
'$'
 'x\x06ARROW '
 '\xfc\x01\x0bTWO-HEADED '
 '\xe2\xa8\x02Q'
 '\x9f\xce\x01B'
'\x12'
 'l\x06ABOVE '
 '\x1c\x05WITH '
 '\xe5\xfc\x03\x08THROUGH '
'\x06'
 '\x9a\xa6\x02R'
 'cA'
'\n'
 '>T'
 '\xfd\xf2\x03\tDOTTED ST'
'\x08'
 '\x80\x02\x04AIL '
 '\xab\xa6\x02I'
'\x0e'
 '\\\x06ARROW '
 '\xb9\xf6\x03\x0bTRIPLE DASH'
'\x0c'
 '8\x05WITH '
 '\x99v\x04FROM'
'\n'
 '(\x04TAIL'
 'BD'
 '+V'
'\x07'
 '\x0b '
'\x04'
 '\x1d\x05WITH '
'\x04'
 '\x12D'
 '+V'
'\x02'
 '%\x07OUBLE V'
'\x02'
 '\xdd\xa0\x04\x05ERTIC'
'\x94\x01'
 '\xfc\x01\x0fCONSONANT SIGN '
 'x\x07LETTER '
 '\xe4\x01\x0cPUNCTUATION '
 '\xce\x01S'
 '\xb8\x01\x0bVOWEL SIGN '
 '\xbb\xef\x03D'
'\x12'
 'BK'
 '\x16N'
 '\xe6\xb2\x04L'
 '\x02M'
 '\x02P'
 '\x02R'
 '\x03T'
'\x05'
 '\xe3\xa7\x04A'
'\x05'
 "\x81'\x04YIN-"
'N'
 '\xba\x01K'
 '\x02P'
 '\xde\xed\x01D'
 'fT'
 '\xeeWB'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02M'
 '\xb6BC'
 '\x02S'
 'fN'
 '\xbe\x90\x01J'
 '\x02L'
 '\x02R'
 '\x02V'
 '\x02W'
 '\x02Y'
 '\x8b\x17A'
'\x06'
 '\xfe\x99\x04H'
 '\x02L'
 '\x8b\x17A'
'\n'
 'RT'
 '(\x0eNYET THYOOM TA'
 '3C'
'\x06'
 '&A'
 '\x1d\x05SHOOK'
'\x02'
 '\x89\xa2\x04\x02-R'
'\x05'
 '\x11\x02 C'
'\x02'
 '\x8d\x91\x01\x03ER-'
'\x08'
 '`\x04IGN '
 '9\x10UBJOINED LETTER '
'\x04'
 '\x1aN'
 '\x9f\xa3\x04R'
'\x02'
 '\xfd\x96\x04\x02UK'
'\x04'
 '\xee\x96\x04R'
 '\x03Y'
'\x0e'
 '\x82\xa3\x03U'
 '\xf2ZO'
 '\xe2\x18A'
 '\x8a\x17E'
 '\x03I'
'\x8e\x05'
 '\x8a\x01M'
 '\x8c\x07\x07NEAR B '
 "\xd0'\x03SU "
 '\xb1\xf4\x01\x0bVRE TOURNOI'
'\x86\x01'
 'X\x03BU '
 '\xb5\x98\x03\rITED LIABILIT'
'\x84\x01'
 '\x80\x01\x07LETTER '
 '\xa6\x01S'
 '\xc8\x02\x05VOWEL'
 '\xb6\xfa\x01E'
 '\xe2\xed\x01D'
 '\xb3\x03Q'
'8'
 '\xa6\xf7\x02N'
 '\x9e\tS'
 '\xba\x01B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\x02J'
 '\x02K'
 '\x02P'
 '\x02T'
 '\xacy\x02YA'
 '\xf6\x17H'
 '\x02L'
 '\x02M'
 '\x02R'
 '\x03W'
' '
 'l\x04IGN '
 '\x80\x01\x0cMALL LETTER '
 '\xa5\xe7\x01\x02UB'
'\x08'
 'H\x03KEM'
 '\x00\x03MUK'
 ' \x02SA'
 '\xff\xf5\x03L'
'\x02'
 '\xa1\xfa\x03\x03PHR'
'\x02'
 '\x9f\xfa\x03-'
'\x12'
 '\x92\xf4\x02N'
 '\xca\x91\x01A'
 '\xae\nK'
 '\x02L'
 '\x02M'
 '\x02P'
 '\x02R'
 '\x03T'
'\x14'
 '`\x06 SIGN '
 '\xd9\x9f\x02\x0c-CARRIER LET'
'\x12'
 '6A'
 '\xa6\xf5\x03E'
 '\x12O'
 '\xea/I'
 '\x03U'
'\x07'
 '\x9a\xa5\x04I'
 '\x03U'
'\xa6\x03'
 't\tIDEOGRAM '
 '\x80\x12\nMONOGRAM B'
 '\xf5\x01\x02SY'
'\xea\x01'
 '6B'
 '\xa1\x10\x08VESSEL B'
'\xb0\x01'
 '\x161'
 '\x9f\x0b2'
'~'
 'V0'
 '\xde\x032'
 '\xc6\x013'
 'F4'
 'z5'
 'z6'
 '\x8a\x017'
 'r8'
 'G9'
'\x1c'
 'z5'
 'f6'
 ':7'
 'N8'
 '>9'
 '\xfc\xa4\x02\x020 '
 '\x00\x042 WO'
 '\xf5\xe3\x01\x044 DE'
'\x06'
 '\xe85\x04 EQU'
 '\xf4\xd7\x03\x07M STALL'
 '\xa9\x13\x03F M'
'\x04'
 '\xa8!\x03F E'
 '\xc1\xe6\x02\x03M R'
'\x04'
 '$\x03F S'
 '\x01\x02M '
'\x02'
 '\x85\xa2\x02\x04HE-G'
'\x04'
 '\xdc\xc0\x02\x03M B'
 '\xa9\xc5\x01\x03F S'
'\x04'
 '\xf8\xad\x03\x04M BU'
 '\xd1W\x03F C'
'\n'
 '\xac\x01\x040 WH'
 '\xe4\xe2\x01\x042 OL'
 '\x80\x04\x065 CYPE'
 '\xe4\xdd\x01\x071 BARLE'
 '\xb1\x0c\x053 SPI'
'\x02'
 '\xf3\xfd\x02E'
'\x06'
 '\xc0\xe0\x03\x031 W'
 '\xa8\x1d\x030 O'
 '\xcb\x1f2'
'\n'
 '\xdc\x05\x035 W'
 '\xc4\xe2\x01\x041 GO'
 '\x94U\x060 BRON'
 '\xba\xdf\x012'
 '\x036'
'\x10'
 '\x84\xae\x03\x041 HO'
 '\xfc[\x059 CLO'
 '\xf6\x110'
 '\x022'
 '\x023'
 '\x024'
 '\x027'
 '\x038'
'\x14'
 '\xcc\xa3\x03\x053 ARM'
 '\x10\x052 GAR'
 '\xa2w0'
 '\x021'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x12'
 '\xce\xe3\x016'
 '\xa8\xa4\x02\x043 MO'
 '\x82\x120'
 '\x021'
 '\x022'
 '\x024'
 '\x027'
 '\x028'
 '\x039'
'\x0e'
 '\x86\x99\x040'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x039'
'\x04'
 '\x98\xe0\x01\x041 HE'
 '\xab\xb8\x020'
'2'
 '&2'
 'n3'
 'v4'
 '\xf3\x015'
'\x04'
 'T\x080 FOOTST'
 '\xc1\xdc\x01\x075 BATHT'
'\x02'
 '\xb7\x89\x04O'
'\x0c'
 '\x90\x91\x02\x053 SWO'
 '\xea\xc4\x011'
 '\xbc;\x050 SPE'
 '\xc6\x052'
 '\x024'
 '\x036'
'\x10'
 '\xc0\x01\t0 WHEELED'
 '\x021'
 '\xb4\xb4\x02\r2 CHARIOT FRA'
 '\xf4o\x053 WHE'
 '\x9ep5'
 '\x026'
 '\x028'
 '\x039'
'\x02'
 '\xa9\x94\x04\x06 CHARI'
'\x12'
 '\\\x034 D'
 '\xba\x93\x041'
 '\x022'
 '\x023'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x02'
 '\xdf@A'
':'
 '22'
 '\xcc\xc3\x02\x0215'
 '\x01\x0230'
'6'
 '22'
 '\x82\xc5\x025'
 '\x9e\xa2\x010'
 '\x031'
'\x0c'
 '\xbe\x92\x041'
 '\x022'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x0c'
 '.1'
 '\xf1\x0e\x06247 DI'
'\n'
 '22'
 'N3'
 '\x99\x0e\x0556 TU'
'\x04'
 '8\x058 KAN'
 '\xd5\x17\x047 KA'
'\x02'
 '\x8f\x10A'
'\x04'
 '\x80\x0c\x045 ME'
 '\x99\xbd\x03\x053 ARE'
'\xb0\x01'
 'T\tLLABLE B0'
 '\xb1\x10\x07MBOL B0'
'\x94\x01'
 'r0'
 '\xd6\x011'
 '\xce\x012'
 '\xe2\x013'
 '\xca\x014'
 '\xee\x015'
 '\x92\x026'
 '\xee\x017'
 '\xf6\x018'
 'g9'
'\x12'
 'v1'
 '\x162'
 '\x166'
 '\x167'
 '\x9a\xfb\x015'
 '\x9e"8'
 '\xfc\x08\x024 '
 '\xd693'
 '\x81\xac\x01\x029 '
'\x02'
 '\xe7\xc7\x03 '
'\x02'
 '\xdb\xd1\x03 '
'\x02'
 '\x87\xf1\x03 '
'\x02'
 '\x0b '
'\x02'
 '\xf7\xdf\x03D'
'\x10'
 '\x84\x01\x024 '
 '\x166'
 '\x1e7'
 '\x96\x121'
 '\x82F0'
 '\x946\x022 '
 '\xf8\x9c\x01\x023 '
 '\xa1\xb2\x01\x035 M'
'\x02'
 '\xef\xdd\x03D'
'\x02'
 '\xc1\xf4\x03\x02 Q'
'\x02'
 '\xbf\x85\x03 '
'\x12'
 '\xa2\x013'
 '\x166'
 '\x14\x039 P'
 '\x90\t\x025 '
 '\xe6l8'
 '\xf8\xd6\x02\x024 '
 '\xf4\x0e\x030 Z'
 'l\x031 Q'
 '\xc1,\x027 '
'\x02'
 '\xdb\x84\x03 '
'\x02'
 '\x87\x9c\x02 '
'\x02'
 '\xbb\xbb\x02U'
'\x10'
 '\x90\x01\x027 '
 '\x169'
 '\xe4\x01\x033 R'
 '\xbeV8'
 '\xaa\x85\x021'
 '\xdc|\x032 Q'
 '\x00\x036 J'
 'm\x030 N'
'\x02'
 '\xa3\xdb\x03T'
'\x02'
 '\x0b '
'\x02'
 '\x83\xdb\x03P'
'\x10'
 '\x98\x01\x020 '
 '\x14\x021 '
 '\x14\x023 '
 '\x14\x026 '
 '\xf8g\x038 N'
 '\x8c\x07\x022 '
 '\xb6\xca\x015'
 '\xa9\xb8\x01\x024 '
'\x02'
 '\xd3\xd9\x03W'
'\x02'
 '\xbf\xd9\x03S'
'\x02'
 '\xa7\xb7\x03A'
'\x02'
 '\xe3\x85\x04J'
'\x12'
 '\x8e\x011'
 '\x14\x022 '
 '\x14\x023 '
 '\x14\x027 '
 '\x168'
 '\x1e9'
 '\xe6]4'
 '\xe4\xb2\x01\x025 '
 '\xfd\xae\x01\x030 P'
'\x02'
 '\xb7\xc1\x01 '
'\x02'
 '\xf3\xd6\x03N'
'\x02'
 '\xcb\xd7\x03R'
'\x02'
 '\xb3\xed\x03J'
'\x02'
 '\xdd\xbf\x03\x02 S'
'\x02'
 '\xf7\xec\x03 '
'\x10'
 '\x90\x01\x022 '
 '\x14\x027 '
 '\x14\x028 '
 '\x1c\x029 '
 '\xe0\x01\x036 T'
 '\xf6N1'
 '\xcar0'
 '\xbd\xfa\x01\x035 J'
'\x02'
 '\x8b\x9c\x02P'
'\x02'
 '\xcb\xd5\x03K'
'\x02'
 '\xa5\xb4\x02\x02RO'
'\x02'
 '\xd7\xbd\x03T'
'\x12'
 '\xb4\x01\x020 '
 '\x14\x036 R'
 '\x167'
 'd\x031 D'
 '\x00\x025 '
 '\x90\xa0\x02\x024 '
 '\xb4\xb2\x01\x033 M'
 '\xb4#\x022 '
 '\x99\t\x038 Q'
'\x02'
 '\xe3\xd2\x03K'
'\x02'
 '\xab\xb2\x02A'
'\x02'
 '\xc3\xbb\x03 '
'\x08'
 'L\x037 T'
 '\xf0\x8b\x02\x025 '
 '\x8c3\x021 '
 '\xfb_0'
'\x02'
 '\x8f\xff\x03W'
'\x04'
 '\x98h\x030 D'
 '\x01\x031 T'
'\x1c'
 'R1'
 '\x1e4'
 '\x1e6'
 '\x1e8'
 '\x8e\xad\x025'
 '\xda\x013'
 'f2'
 '\xcf\x7f7'
'\x04'
 '\xae\xfe\x038'
 '\x039'
'\x04'
 '\x92\xfe\x037'
 '\x039'
'\x04'
 '\xf6\xfd\x033'
 '\x034'
'\x08'
 '\xda\xfd\x032'
 '\x023'
 '\x026'
 '\x039'
'`'
 '`\x07LETTER '
 '\xf1\xd0\x01\x0bPUNCTUATION'
'\\'
 '\xda\x01D'
 '"T'
 '\xba\xc7\x02U'
 '\x1eN'
 '\xd6\nC'
 '\x02G'
 '\x02H'
 '\x02K'
 '\x02P'
 '\x02S'
 '\x02Z'
 '\xd2\x1dE'
 '\xe2ZA'
 '\x02O'
 '\xf2\x18B'
 '\x02F'
 '\x02J'
 '\x02L'
 '\x02M'
 '\x02W'
 '\x02X'
 '\x02Y'
 '\x8b\x17I'
'\x04'
 '\xe6\xe3\x03Z'
 '\x8b\x17A'
'\x14'
 'D\x04ONE '
 '\xe2\xd1\x02S'
 '\xa2\x91\x01H'
 '\x8b\x17A'
'\x0c'
 '(\x04MYA '
 'A\x02NA'
'\n'
 '\xa2gJ'
 '\xeeMC'
 '\xde\x96\x02B'
 'nT'
 '\xff\x15N'
'\x02'
 '\x0b '
'\x02'
 '\x9f\xcb\x03P'
'\x04'
 '\xe4\xe9\x01\x10LEFTWARDS SQUIGG'
 '\x91\xfb\x01\x04DIVI'
'p'
 'X\x0cCIAN LETTER '
 '\xdd\x01\x05DIAN '
':'
 '\xc6\x01M'
 '\xfa\x9c\x01K'
 '\x86\xff\x01B'
 ':T'
 '\xb6*A'
 '\x02E'
 '\x02N'
 '\xfe.D'
 '\x02G'
 '\x02H'
 '\x02I'
 '\x02J'
 '\x02L'
 '\x02P'
 '\x02Q'
 '\x02R'
 '\x02S'
 '\x02U'
 '\x02W'
 '\x02X'
 '\x03Z'
'\x05'
 '\xe3\xf5\x03M'
'6'
 'T\x07LETTER '
 '\x99~\tTRIANGULA'
'4'
 '\xba\x01S'
 '\xdamL'
 '\xb6\xf2\x01T'
 '\xb6dA'
 '\x02E'
 '\x02N'
 '\xfe.B'
 '\x02C'
 '\x02D'
 '\x02F'
 '\x02G'
 '\x02I'
 '\x02K'
 '\x02M'
 '\x02O'
 '\x02Q'
 '\x02R'
 '\x02U'
 '\x02V'
 '\x03Y'
'\x05'
 '\xbb\xf3\x03S'
'\xb2\x06'
 '\xe6\x01A'
 '\xb2\x13E'
 '\xbe\rO'
 '\xb8%\x07YANMAR '
 '\x8d\xab\x03"USICAL SYMBOL MULTIPLE MEASURE RES'
'\x96\x01'
 '\xfc\x01\x0bHJONG TILE '
 '\xae\x07L'
 '\xf8\x05\x05RRIAG'
 '\x14\x0bTHEMATICAL '
 '\xfd\xe0\x03\x15P SYMBOL FOR LIGHTHOU'
'X'
 '\xfc\x01\x02BA'
 '*E'
 '.F'
 '.N'
 '*O'
 ':S'
 '~T'
 '\xc2\x01W'
 'p\x05GREEN'
 '\x00\x03RED'
 '\x88\xae\x01\x03AUT'
 '\xec\x1f\x02JO'
 '\xd0\x96\x02\x0bCHRYSANTHEM'
 '\x01\x02PL'
'\x04'
 '\x8c\xbc\x03\x02MB'
 '\xaf\x10C'
'\x08'
 '\xe4\x02\x04IGHT'
 '\xcb\x01A'
'\x0c'
 '\xac\x02\x02IV'
 '\r\x03OUR'
'\x08'
 '\xc0\x01\x02OR'
 'A\x02IN'
'\x08'
 ' \x03RCH'
 '\xbb\x01N'
'\x02'
 '\xb3\xe4\x03I'
'\x12'
 '`\x02OU'
 'L\x04EVEN'
 '\x00\x02IX'
 '\xfe\xf9\x02P'
 '\xe9Y\x03UMM'
'\x02'
 '\xa5\x02\x02TH'
'\x0c'
 '$\x03HRE'
 '\r\x02WO'
'\x06'
 '\x0bE'
'\x06'
 '\x19\x04 OF '
'\x06'
 '.C'
 '\xa1\xcc\x01\x05BAMBO'
'\x04'
 '\x98\xb2\x01\x02IR'
 '\xed\xbf\x01\x05HARAC'
'\x06'
 ':E'
 '4\x04HITE'
 '\xb1\xe2\x01\x02IN'
'\x02'
 '\x11\x02ST'
'\x02'
 '\x85\xe1\x03\x03 WI'
'\x02'
 '\xe1\xe1\x03\x03 DR'
'('
 '8\x07AYALAM '
 '\xe1\x03\x02E '
'"'
 '\xc0\x01\tFRACTION '
 '`\x0eLETTER CHILLU '
 '8\x07NUMBER '
 '^S'
 '\xccm\x03DAT'
 '\xa7 V'
'\x06'
 '@\x04ONE '
 '\x85n\x07THREE Q'
'\x04'
 '\x92\xdf\x01H'
 '#Q'
'\x0c'
 '\x82\xe1\x02L'
 '\xaeUN'
 '\xc6)R'
 '\xbb\x05K'
'\x06'
 '\x1aO'
 '\xa7\xa8\x03T'
'\x04'
 '\x0bN'
'\x04'
 '\x11\x02E '
'\x04'
 '\x8a\xd9\x01T'
 '\x9f\tH'
'\x02'
 '\xd5\xde\x02\x05IGN A'
'\x06'
 '@\x0cWITH STROKE '
 'GA'
'\x04'
 '@\nAND MALE A'
 '\xff\xd3\x03S'
'\x02'
 '\x19\x04ND F'
'\x02'
 '\x0bE'
'\x02'
 '\x0bM'
'\x02'
 '\x0bA'
'\x02'
 '\x83\xcf\x03L'
'\x02'
 '\x9b\xd4\x03E'
'\x12'
 '\xe0\x01\x05BOLD '
 'h\x15ITALIC SMALL DOTLESS '
 '\x1c\x03LEF'
 '\x00\x04RIGH'
 'y\x0cSCRIPT SMALL'
'\x04'
 '8\x06CAPITA'
 '\x01\x04SMAL'
'\x02'
 '\x0bL'
'\x02'
 '\xed(\x04 DIG'
'\x04'
 '\xb2\xdf\x03I'
 '\x03J'
'\x04'
 '\x11\x02T '
'\x04'
 '\xac\xc5\x01\tFLATTENED'
 '\xe9\xc6\x01\x07WHITE T'
'\x02'
 '\xd3\xd0\x03 '
'\x88\x01'
 '\x80\x01\x05DIUM '
 '\x84\x01\x0bETEI MAYEK '
 '\xd1\x07\x07TRICAL '
'\x06'
 'H\x07SMALL W'
 '\x02W'
 '%\x05BLACK'
'\x02'
 '\x15\x03HIT'
'\x02'
 '\x0bE'
'\x02'
 '\xd7\xe6\x02 '
'p'
 '\x84\x01\x04CHEI'
 '*L'
 '\xf0\x04\x04APUN'
 ' \x0bVOWEL SIGN '
 '\x9f\x97\x03D'
'\x02'
 '\x0bK'
'\x02'
 '\xe5\xad\x03\x02HE'
'H'
 '4\x06ETTER '
 '\xb9\x04\x02UM'
'F'
 '\xe2\x01B'
 '&D'
 '"G'
 '"H'
 '\x16J'
 '&K'
 '\x1eN'
 '"P'
 '\x1eT'
 '2I'
 '\x00\x03LAI'
 '\x00\x03MIT'
 '\xd4o\x02AT'
 '\xf2\xc7\x01R'
 '\x02W'
 '\xc6\x05S'
 '\xdajY'
 '\xe8\x0e\x02CH'
 '\xa3\x19U'
'\x04'
 '\xaa\xbf\x02H'
 '\x8b\x99\x01A'
'\x04'
 '\xea\x01H'
 '\xdb\xc8\x03I'
'\x04'
 '\xca\x01H'
 '\xab\xb5\x03O'
'\x02'
 '\xd3\xb6\x03U'
'\x04'
 '\xb2\xbe\x02H'
 '\xbf\x8b\x01I'
'\x06'
 'rH'
 '\x15\x02OK'
'\x08'
 'jA'
 '\x01\x03GOU'
'\x06'
 'JA'
 '\x8b\xbd\x02H'
'\x06'
 '\x1aH'
 '\x15\x02IL'
'\x02'
 '\xdb\x91\x03O'
'\x05'
 '\x19\x04 LON'
'\x02'
 '\x8b\xd2\x03S'
'\x02'
 '\xa9\x93\x02\x03 IY'
'\x10'
 'nA'
 '\x00\x04CHEI'
 '\x02I'
 '\x02O'
 '\x00\x03SOU'
 '\x02U'
 '\x00\x02YE'
 '\xcf\x93\x02N'
'\x02'
 '\x0bN'
'\x02'
 '\xbf\x99\x03A'
'\x12'
 'rB'
 '\x1c\nLONG OVER '
 '^P'
 '\x1aT'
 '\xb9\x01\x07SHORT O'
'\x02'
 '\xa9\x96\x03\x02RE'
'\x04'
 'D\x03SHO'
 '\xc5\xbe\x03\x08TWO SHOR'
'\x02'
 '\xcb\xd2\x03R'
'\x02'
 'm\x03ENT'
'\x08'
 'BE'
 '"R'
 ')\nWO SHORTS '
'\x02'
 '\x11\x02TR'
'\x02'
 '\x17A'
'\x02'
 '\x0bI'
'\x02'
 '\xa9\xf1\x01\x02SE'
'\x04'
 '*O'
 '\xc5\xe1\x02\x04JOIN'
'\x02'
 '\x91\x90\x02\x04VER '
'\xb6\x02'
 'X\x0eDIFIER LETTER '
 '\xa6"N'
 '\x97\x02U'
'\xac\x02'
 '\xc6\x02C'
 '\xd0\x04\x04DOT '
 '\x86\x01E'
 '\xc4\x01\x04HIGH'
 '\x10\x03LOW'
 '\xac\x03\x03MID'
 '\x9c\x03\x07RAISED '
 '\x92\x01S'
 '\xb4\x10\x05BEGIN'
 '\xc8\xa7\x01\x08OPEN SHE'
 '\x86\xf5\x01U'
 '\xe1\x0b\nGEORGIAN N'
'D'
 '\x9c\x01\x07APITAL '
 '\xac\x02\rHINESE TONE Y'
 'p\x07YRILLIC'
 '\xf7\xfa\x02O'
'0'
 '\xae\x01B'
 '6R'
 '\xca\xbf\x02O'
 '\xe2ZA'
 '\xfa/D'
 '\x02E'
 '\x02G'
 '\x02H'
 '\x02I'
 '\x02J'
 '\x02K'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x02P'
 '\x02T'
 '\x02U'
 '\x02V'
 '\x03W'
'\x05'
 '\x0bA'
'\x02'
 '\xed\xfa\x01\x05RRED '
'\x07'
 ')\x08EVERSED '
'\x04'
 '\xf2\xc9\x03E'
 '\x03N'
'\x10'
 '$\x03ANG'
 '\x01\x02IN'
'\x08'
 '\x0b '
'\x08'
 '\xda\x84\x03Q'
 '\x02R'
 '\x98\x16\x02SH'
 '\x93#P'
'\x02'
 '\xb3\x8c\x03 '
'\x06'
 'BH'
 '(\x06VERTIC'
 '\xc1\x87\x02\x02SL'
'\x02'
 '%\x07ORIZONT'
'\x02'
 '\x81\x07\x02AL'
'\x12'
 '(\x05XTRA-'
 '\xab\x19N'
'\x0e'
 '0\x05HIGH '
 'e\x03LOW'
'\x08'
 '\xda\x04D'
 'FL'
 '9\x11EXTRA-LOW CONTOUR'
'\x06'
 '\xe3\x03 '
'\x1a'
 'V '
 '\xd5\xdc\x02\x0fER RIGHT CORNER'
'\x18'
 '\x98\x01\x02DO'
 ' \x04LEFT'
 'D\x02RI'
 '(\x02UP'
 '\xa8\x03\nCIRCUMFLEX'
 'zI'
 '\xcb\xab\x03T'
'\x06'
 '\x88\x01\x02WN'
 '\x7fT'
'\x06'
 ',\x06 ARROW'
 '\x87\x02-'
'\x05'
 '\xc7\xe1\x01H'
'\x04'
 '$\x03GHT'
 '\xf7\xb7\x03N'
'\x02'
 '\xa1\x8f\x01\x06 ARROW'
'\x0c'
 '& '
 '\xd5\x01\x04DLE '
'\x06'
 '\x12D'
 'GL'
'\x04'
 '\x11\x02OT'
'\x04'
 '\x19\x04TED '
'\x04'
 '\x12L'
 'OT'
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
 '\xab\x11 '
'\x06'
 '(\x06DOUBLE'
 '3G'
'\x04'
 '\x0b '
'\x04'
 '"G'
 '\x19\x04ACUT'
'\x02'
 '\x15\x03RAV'
'\x02'
 '\x0bE'
'\x02'
 '\x8d\xbf\x02\x03 AC'
'\n'
 'VI'
 '\xda\x92\x01E'
 '\x86\xde\x01C'
 '\x80\r\x04DOWN'
 '\x01\x02UP'
'\x02'
 '\xd5\x92\x01\tNVERTED E'
'\x90\x01'
 'RH'
 'P\x05MALL '
 '\x81\x0f\x08TRESS AN'
'\x04'
 '8\x08ORT EQUA'
 '\xeb\xb6\x01E'
'\x02'
 '\x8f\xb4\x01L'
'\x88\x01'
 '\xc6\x02A'
 '"B'
 '^C'
 '\x9e\x01D'
 'NE'
 '2G'
 'NI'
 'JL'
 'BM'
 '\x02V'
 '\x10\x07N WITH '
 '6O'
 ':P'
 '\x16S'
 '\xb2\x01T'
 '\xf4\x02\nREVERSED O'
 '6U'
 '>Z'
 '\xc8\x8f\x03\x0fJ WITH CROSSED-'
 '\xde\x1fF'
 '\x03K'
'\x07'
 '\xce\tL'
 '\xbb\xaa\x03I'
'\t'
 ':O'
 '\x88\x08\x05ARRED'
 '\xbb\x9a\x03E'
'\x02'
 '\xe5\x07\x04TTOM'
'\x11'
 '\\\x07APITAL '
 '\xe8\t\x07 WITH C'
 '\xeb\x81\x03H'
'\n'
 '*I'
 '\xaa\xb8\x03L'
 '\x02N'
 '\x03U'
'\x05'
 '\xf3\x01 '
'\x07'
 '8\x08OTLESS J'
 '\xdb\xf0\x02E'
'\x02'
 '\xa7\x01 '
'\x0b'
 '\xe2\xa5\x03S'
 '\x02T'
 '\x02Z'
 '\xe3\x06N'
'\x07'
 '\x1d\x05REEK '
'\x04'
 '\x16G'
 '\xdf P'
'\x02'
 '\xa3\xf8\x02A'
'\x04'
 '\x1a '
 '\xa3\x9f\x03O'
'\x02'
 '\x15\x03WIT'
'\x02'
 '\xa7\xa1\x03H'
'\x04'
 '!\x06 WITH '
'\x04'
 '\xc2\x03P'
 '\xd3\x03R'
'\x05'
 '\xc3\x01 '
'\x04'
 ' \x03LEF'
 '\xc7\x06R'
'\x02'
 '\xef\x06T'
'\x07'
 '\x19\x04PEN '
'\x04'
 '\xe6\xb4\x03E'
 '\x03O'
'\x05'
 '\xc7\x87\x03H'
'\x08'
 '2 '
 '"C'
 '=\x06IDEWAY'
'\x02'
 '\xdd\x05\x04WITH'
'\x04'
 '$\x04RIPT'
 '\x9b\x15H'
'\x02'
 '\xb3\xa8\x03 '
'\x02'
 '\x0bS'
'\x02'
 '\xd3\xee\x02 '
'\x1b'
 'B '
 'NO'
 '@\x06URNED '
 '\x93\xea\x02H'
'\x02'
 '!\x06WITH P'
'\x02'
 '\xf9\x03\x06ALATAL'
'\x02'
 '\x0bP'
'\x02'
 '\x1d\x05 HALF'
'\x02'
 '\xdb\x83\x03 '
'\x12'
 ':A'
 '2M'
 ':O'
 '\x96\xb0\x03H'
 '\x02I'
 '\x03V'
'\x07'
 '\x1aL'
 '\xe3\xb0\x03E'
'\x02'
 '\x97\x95\x03P'
'\x05'
 '\xbdt\n WITH LONG'
'\x02'
 '\x0bP'
'\x02'
 '\x11\x02EN'
'\x02'
 '\xbb\xaf\x03 '
'\x07'
 '& '
 '\xc5\xe1\x02\x03PSI'
'\x02'
 '\xf3\xa9\x03B'
'\x07'
 '!\x06 WITH '
'\x04'
 '\x12C'
 '\x1fR'
'\x02'
 '\x9d\xa1\x03\x02UR'
'\x02'
 ')\x08ETROFLEX'
'\x02'
 '\x11\x02 H'
'\x02'
 '\xff\x8a\x02O'
'\x04'
 '\x0bD'
'\x04'
 '\x0b '
'\x04'
 '\xd6+H'
 '\x1bL'
'\x08'
 '\xc0\x01\nOGRAM FOR '
 '\xc1\x90\x03\x1fGOLIAN LETTER MANCHU ALI GALI L'
'\x06'
 '\x12E'
 '\x1fY'
'\x02'
 '\xfd\x99\x03\x02AR'
'\x04'
 '\xc2\xa0\x03A'
 '\xef\x04I'
'\x02'
 '\x0bN'
'\x02'
 '\xf3\xe4\x02T'
'\xdc\x01'
 '\x80\x03\x0fCONSONANT SIGN '
 '\xfa\x01L'
 '\xba\x08S'
 '\xa0\x07\x15TONE MARK SGAW KAREN '
 'L\x0bVOWEL SIGN '
 '\xd5\xca\x02\x1fMODIFIER LETTER KHAMTI REDUPLIC'
'\x10'
 'BM'
 '\xa5\x01\x0bSHAN MEDIAL'
'\x0e'
 'P\x06EDIAL '
 '-\nON MEDIAL '
'\x08'
 '\xee\x8f\x03H'
 '\x02R'
 '\x02W'
 '\x03Y'
'\x06'
 '\xc2\x8f\x03L'
 '\x02M'
 '\x03N'
'\x02'
 '\x83\x08 '
'd'
 'h\x06ETTER '
 '\x9d\x07\x0fOGOGRAM KHAMTI '
'^'
 '\xe0\x02\x12EASTERN PWO KAREN '
 '8\x07KHAMTI '
 '\xa8\x01\x04MON '
 'ZS'
 '\xd0\x01\x12WESTERN PWO KAREN '
 '\x88Z\rRUMAI PALAUNG'
 '\xb4\x05\x05AITON'
 '\x9f\x94\x01G'
'\x06'
 '&G'
 '\xfe\x03Y'
 '\x93\x82\x03N'
'\x02'
 '\xfb\x03H'
'&'
 '\x82\x01D'
 '\x8e\xdd\x01N'
 '\xda\x1bC'
 '\x02H'
 '\x02J'
 '\x00\x02TT'
 '\xa2\x91\x01F'
 '\x02G'
 '\x02R'
 '\x02S'
 '\x02X'
 '\x03Z'
'\x06'
 '\xe2\xf8\x01D'
 '\xa3\x91\x01H'
'\n'
 '8\x02BB'
 '\xa6\xfd\x02N'
 '\xc2\x07J'
 '\xcb\x1bE'
'\x04'
 '\xaa\xa0\x03A'
 '\x03E'
'\x1e'
 'L\x04HAN '
 '\xa1\x8d\x02\tGAW KAREN'
'\x1c'
 '\xbe\xdb\x01N'
 '\xda\x1bK'
 '\xe2\x8c\x01P'
 '\x02T'
 '\xc2\x04B'
 '\x02C'
 '\x02D'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02Z'
 '\x8b\x17A'
'\x04'
 '\x1aP'
 '\xdf\x82\x03T'
'\x02'
 '\x9b\x87\x03W'
'\x06'
 '\xea\xbb\x01O'
 '\xfe\xdb\x01Q'
 '\xcf\x02H'
'@'
 'X\x04IGN '
 '\x88\x05\x06YMBOL '
 '\xd9\xeb\x01\x03HAN'
'"'
 '\xd8\x02\x0cKHAMTI TONE-'
 '\x1c\x05SHAN '
 '\xdc\x01\x17WESTERN PWO KAREN TONE-'
 '\xfc\x16\tPAO KAREN'
 '\x8c\xb2\x01\x13RUMAI PALAUNG TONE-'
 '\xcb/A'
'\x04'
 '\xa6\x9a\x031'
 '\x033'
'\x0e'
 'D\x08COUNCIL '
 'i\x05TONE-'
'\x06'
 'H\x05TONE-'
 '\xc5\x17\x08EMPHATIC'
'\x04'
 '\xf6\x98\x032'
 '\x033'
'\x08'
 '\xda\x98\x032'
 '\x023'
 '\x025'
 '\x036'
'\n'
 '\xae\x98\x031'
 '\x022'
 '\x023'
 '\x024'
 '\x035'
'\n'
 '<\x06AITON '
 '9\x05SHAN '
'\x06'
 '"T'
 '2E'
 '\x87\xda\x02O'
'\x02'
 '\xa7\xe9\x02W'
'\x04'
 '\x1aE'
 '\x87\xda\x02O'
'\x02'
 '\xc5\xcb\x02\x05XCLAM'
'\x04'
 '4\x03HAT'
 '\xd1\xfd\x01\x04KE P'
'\x02'
 '\x83\xe9\x02H'
'"'
 '\x94\x02\nGEBA KAREN'
 '\x14\x06KAYAH '
 '$\x04MON '
 '"S'
 '\xb4\x01\x12WESTERN PWO KAREN '
 '\xd8\xf2\x01\x02TA'
 '\x8c\x14\x07AITON A'
 '\xbf4E'
'\x02'
 '\xd7\xe6\x02 '
'\x06'
 '\x8e\x93\x03E'
 '\x02O'
 ';U'
'\x04'
 '\x9e\xe6\x02I'
 '\x87-O'
'\n'
 'H\nGAW KAREN '
 '\x15\x04HAN '
'\x02'
 '\xef\xcd\x02E'
'\x08'
 '>E'
 '\xe4\xb8\x02\x06FINAL '
 '\xfbAA'
'\x05'
 '\xbf\xbb\x02 '
'\x04'
 '\x86\xcd\x02E'
 '\x93DU'
'\xd0\x02'
 '.E'
 '\xac\x0b\x03KO '
 '\xa3\nO'
'\xbc\x01'
 'h\x07GATIVE '
 '\xa0\x03\nW TAI LUE '
 '\xf3\x86\x01U'
'\x14'
 'T\x08CIRCLED '
 '\x95\x01\x08SQUARED '
'\x06'
 't\x15LATIN CAPITAL LETTER '
 '\xf9\xfb\x01\x02DI'
'\x04'
 '\xba\x8e\x03H'
 '\x03P'
'\x0e'
 '\x84\x01\x15LATIN CAPITAL LETTER '
 '\x92\xf6\x02P'
 '\x02S'
 '\xfb\x14I'
'\x08'
 '\x96\x8d\x03J'
 '\x02L'
 '\x02M'
 '\x03P'
'\xa6\x01'
 '\xa0\x01\x07LETTER '
 '\xf4\x02\x08SIGN LAE'
 '\x16T'
 'h\x0bVOWEL SIGN '
 '\xb3\xc9\x02D'
'f'
 'L\x06FINAL '
 '@\x04HIGH'
 '\x01\x03LOW'
'\x0e'
 '\xb6fN'
 '\xbe\xa4\x02B'
 '\x02D'
 '\x02K'
 '\x02M'
 '\x03V'
','
 '\x0b '
','
 '\x96\x01K'
 '\x02X'
 '"S'
 '\xf6\xd5\x01N'
 '\x9e\tT'
 '\xba\x01P'
 '\xa2\x91\x01B'
 '\x02D'
 '\x02F'
 '\x02H'
 '\x02L'
 '\x02M'
 '\x02Q'
 '\x02V'
 '\x03Y'
'\x04'
 '\x86\xf2\x02V'
 '\x8b\x17A'
'\x04'
 '\xe6\xf1\x02U'
 '\x8b\x17A'
'\x05'
 '\xcf\x88\x03V'
'\x06'
 '\x98\x07\nHAM DIGIT '
 '\x85\xe0\x01\x08ONE MARK'
'"'
 'jA'
 '*I'
 '\x1eO'
 '\x1eU'
 '\x98\xd2\x02\x0bVOWEL SHORT'
 '\xf33E'
'\x08'
 '\x82\x01A'
 '\xe6\x85\x03E'
 '\x03Y'
'\x04'
 '\xbe\x86\x03I'
 '\x03Y'
'\t'
 '>A'
 '\xe7\x85\x03Y'
'\x0b'
 '"E'
 '\xe6\x85\x03U'
 '\x03Y'
'\x05'
 '\xe3\x85\x03Y'
'v'
 '\x80\x01\x03COM'
 '\xc2\x03L'
 '\xb8\x04\x04HIGH'
 'H\x07SYMBOL '
 '\x8aPE'
 '\xe3\xed\x01D'
'\x14'
 '4\x07BINING '
 '\x8f\xed\x02M'
'\x12'
 'x\x06DOUBLE'
 '0\x05LONG '
 '@\x06SHORT '
 '\xb9\xa9\x02\x03NAS'
'\x02'
 '\x11\x02 D'
'\x02'
 '\xd1\xac\x02\x02OT'
'\x08'
 'ZH'
 '\x1aL'
 '\x16R'
 '\x15\x07DESCEND'
'\x06'
 '\x1aH'
 '\x1aL'
 '\x17R'
'\x02'
 'U\x03IGH'
'\x02'
 '=\x02OW'
'\x02'
 '\x11\x02IS'
'\x02'
 '\x15\x03ING'
'\x02'
 '\x11\x02 T'
'\x02'
 '\xbb\xc4\x02O'
'F'
 '`\x06ETTER '
 '\xd4\x03\x02OW'
 '\xdd\xf1\x02\x07AJANYAL'
'B'
 '\xd0\x01\x02DA'
 '*G'
 '\x16J'
 'VN'
 'RR'
 '\xfe\xcc\x02E'
 '\x12O'
 '\xa2\x14C'
 '\xc2\x04B'
 '\x02F'
 '\x02H'
 '\x02K'
 '\x02L'
 '\x02M'
 '\x02P'
 '\x02S'
 '\x02T'
 '\x02W'
 '\x02Y'
 '\x8a\x17A'
 '\x02I'
 '\x03U'
'\x05'
 '\xc1\xba\x02\x05GBASI'
'\x02'
 '\xa3\xe7\x02B'
'\x08'
 '(\x04ONA '
 '\xef\xfd\x02A'
'\x06'
 '\xa2\xe2\x02C'
 '\xc2\x04J'
 '\x03R'
'\x0b'
 '\x1aA'
 '\x01\x02YA'
'\x05'
 '\x1d\x05 WOLO'
'\x02'
 '\x97\xcf\x02S'
'\x04'
 '\xea\xe5\x02R'
 '\x8b\x17A'
'\x02'
 '\xd5\x1a\x0e TONE APOSTROP'
'\x04'
 'D\x07GBAKURU'
 '\x01\x06OO DEN'
'\x02'
 '\x8f\xbf\x02N'
'\x1e'
 '" '
 '-\x04RTH '
'\x02'
 '\x15\x03ENT'
'\x02'
 '\xf3\xa1\x02R'
'\x1c'
 '8\x06INDIC '
 '\xce\x9d\x01E'
 '\x0fW'
'\x14'
 '\x8c\x01\tFRACTION '
 '\xf0\x01\x03QUA'
 '8\tPLACEHOLD'
 '!\x04RUPE'
'\x0c'
 '8\x04ONE '
 'U\x06THREE '
'\x08'
 '\xa2rH'
 '"Q'
 '\x88\xf4\x01\x05SIXTE'
 '\x19\x04EIGH'
'\x04'
 '>Q'
 '\xa1\xe6\x02\tSIXTEENTH'
'\x02'
 '\xed\xff\x01\x03UAR'
'\x04'
 '4\x02RT'
 '\xb5\xbc\x02\x05NTITY'
'\x02'
 '\x0bE'
'\x02'
 '\xa7\xbc\x02R'
'\x02'
 '\x93\xbc\x02E'
'\xfa\x03'
 '\xc6\x01L'
 '\x94\x1c\x04NE D'
 '\\\x06PEN SU'
 '\x1aR'
 '\xb0\x02\x07SMANYA '
 '\xe5\xcf\x02\x0fUTLINED WHITE S'
'\x96\x03'
 '8\x07 CHIKI '
 '\xc5\x06\x02D '
'`'
 'x\x07LETTER '
 '\x94\x03\x02MU'
 '>G'
 'JP'
 '\xfe-A'
 '\xf8N\x02RE'
 '\x83\xb4\x01D'
'<'
 '2A'
 'fE'
 '6I'
 '2L'
 '>O'
 '/U'
'\x10'
 '6A'
 '\xbe\xe7\x02N'
 '\x8a\x0bG'
 '\x02L'
 '\x03T'
'\x08'
 '\xc2\xf2\x02J'
 '\x02K'
 '\x02M'
 '\x03W'
'\x08'
 '\xde\xea\x02D'
 '\x82\x02R'
 '\xba\x05N'
 '\x03P'
'\x08'
 '\xe2\x98\x02N'
 '\x82YH'
 '\x02R'
 '\x03S'
'\x0c'
 '\x8e\xda\x01A'
 '\xa6\x97\x01E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x08'
 '\xea\xf0\x02T'
 '\x0eB'
 '\x02H'
 '\x03V'
'\x08'
 '\xa2\xea\x02N'
 '\xaa\x06C'
 '\x02D'
 '\x03Y'
'\x04'
 '8\x02-G'
 '\xc5\x8e\x01\x06 TTUDD'
'\x02'
 '\xc1\x8e\x01\rAAHLAA TTUDDA'
'\x06'
 'X\x0bUNCTUATION '
 '\xdd\xcf\x01\x05HAARK'
'\x04'
 '0\x08DOUBLE M'
 '\x03M'
'\x02'
 '\xa9\xab\x01\x03UCA'
'\xb6\x02'
 '\xb4\x01\x08PERSIAN '
 '\x80\x06\x0eSOUTH ARABIAN '
 '\xd5\x06\x0eTURKIC LETTER '
'd'
 'P\x07NUMBER '
 'H\x05SIGN '
 '\xbf\xa7\x02W'
'\n'
 '&T'
 '\xa2iH'
 '\xaf\xc5\x01O'
'\x06'
 '\xce<W'
 '\xbb\xa8\x02E'
'X'
 '\xca\x01A'
 'VB'
 ':D'
 'bG'
 '\x02K'
 '\x02N'
 '\x02R'
 '\x1eJ'
 '\x02V'
 '\x1eT'
 '*X'
 '\x9a\xbd\x01S'
 '\xd2\x1eM'
 '\x8atC'
 '\x02F'
 '\x02H'
 '\x02L'
 '\x02P'
 '\x02Y'
 '\x02Z'
 '\x8a\x17I'
 '\x03U'
'\t'
 '-\tURAMAZDAA'
'\x07'
 '\xfe\x9a\x01-'
 '\x8f\xb7\x01H'
'\x06'
 '"A'
 '\x81o\x03UUM'
'\x05'
 '\xc3\xd1\x02G'
'\n'
 '"A'
 '\x96\xe8\x02I'
 '\x03U'
'\x07'
 '%\x07HYAAUSH'
'\x05'
 '\xd7\x99\x01-'
'\x04'
 '\xd6\xe7\x02A'
 '\x03U'
'\x04'
 '\xba\xe7\x02A'
 '\x03I'
'\x06'
 '\x96\xd0\x02H'
 '\x8a\x17A'
 '\x03U'
'\x04'
 '8\x08SHAAYATH'
 '\xbf\xe6\x02A'
'\x02'
 '\xef!I'
'@'
 '<\x07LETTER '
 '\x8d\x05\x03NUM'
':'
 '\xa6\x01A'
 '"D'
 'RG'
 '.H'
 '"K'
 '\x1eL'
 '\x1eQ'
 '\x16S'
 'vT'
 'JY'
 '\x92\x0eZ'
 '\x8e\x01W'
 '\xdaZR'
 '\x8a?B'
 '\xbarM'
 '\x12N'
 '\x87EF'
'\x04'
 '\xderL'
 '\xbf\xeb\x01Y'
'\x06'
 '\x1aA'
 '\x15\x02HA'
'\x02'
 '\x83\xac\x01L'
'\x04'
 '\xf6\x01D'
 '\xfb\xa9\x01L'
'\x04'
 '\x16I'
 '\xcf\x10H'
'\x02'
 '\x9f\xf3\x01M'
'\x04'
 '\x0bE'
'\x05'
 '\xb3\xd1\x02T'
'\x04'
 '\x82\xab\x01H'
 'WA'
'\x02'
 '\xf5\x01\x03AME'
'\x02'
 '\x9f\xab\x01O'
'\x08'
 '\x1aA'
 '\xcb\x9d\x02H'
'\x06'
 '"D'
 '\x16M'
 '\xeb\xe1\x02T'
'\x02'
 '\xc3\xe1\x02H'
'\x02'
 '\x0bE'
'\x02'
 '\xf3\xcf\x02K'
'\x08'
 '&H'
 '\xc6\xc7\x02A'
 '\xeb\x07E'
'\x04'
 '\xc2\xc7\x02A'
 '\xeb\x07E'
'\x02'
 '\x0bO'
'\x02'
 '\x8b\xcf\x02D'
'\x06'
 'L\x04BER '
 '\xcdN\nERIC INDIC'
'\x04'
 '\x1aF'
 '\x93\xa3\x02O'
'\x02'
 '\xad\xf2\x01\x02IF'
'\x92\x01'
 'P\x07ORKHON '
 '\xbd\x03\x08YENISEI '
'T'
 '6A'
 '\xc6\x01E'
 'vI'
 '\x1eO'
 '\xcf\x9b\x01B'
'-'
 'fE'
 '\xfa\x83\x02S'
 '\xeaYB'
 '\x02D'
 '\x02G'
 '\x02L'
 '\x02N'
 '\x02Q'
 '\x02R'
 '\x02T'
 '\x03Y'
'\x14'
 '\xde\xdd\x02B'
 '\x02D'
 '\x02G'
 '\x02K'
 '\x02L'
 '\x02N'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x03Y'
'\x14'
 'FN'
 '\xd6\xca\x02S'
 '\xde\x11L'
 '\x0eC'
 '\x02M'
 '\x02P'
 '\x03Z'
'\x08'
 '\xba\xdc\x02C'
 '\x02G'
 '\x02T'
 '\x03Y'
'\x07'
 '\x8e\xdc\x02C'
 '\x03Q'
'\r'
 '\x86\x03E'
 '\xee\xd8\x02P'
 '\x02Q'
 '\x03T'
'>'
 '&A'
 '\xae\x01E'
 'VI'
 '\x17O'
"'"
 'jE'
 '\xca\xc8\x02S'
 '\xe2\x06N'
 '\x8a\x0bB'
 '\x02D'
 '\x02G'
 '\x02L'
 '\x02Q'
 '\x02R'
 '\x02T'
 '\x03Y'
'\x11'
 '\xf25N'
 '\xbe\xa4\x02B'
 '\x02G'
 '\x02K'
 '\x02T'
 '\x03Y'
'\x0f'
 '.N'
 '\xda\xc7\x02S'
 '\xea\x11C'
 '\x03Z'
'\x06'
 '\xbe\xd9\x02C'
 '\x02T'
 '\x03Y'
'\x05'
 '\x9b\xd9\x02Q'
'\x06'
 '\x1aE'
 '\xef\xd8\x02Q'
'\x05'
 '\xeb\xd8\x02K'
'\x02'
 'E\x0fOT OVER TWO DOT'
'\x02'
 '\xb7\x8c\x02S'
'\x04'
 '\xb6GP'
 '\x17B'
'\x0c'
 'D\t WITH DOT'
 ')\x04IYA '
'\x02'
 '\x9d\xc4\x02\x05 INSI'
'\n'
 ',\x07LETTER '
 '\x1fV'
'\x04'
 '\xba\xbf\x02V'
 '\x03W'
'\x06'
 'Q\x12OWEL SIGN VOCALIC '
'\x06'
 '\xaa\xd1\x01L'
 '\xf3~R'
'P'
 '4\x07LETTER '
 '\xdb\x96\x02D'
'<'
 '\xea\x01A'
 '"C'
 '\x1eD'
 '"K'
 '"S'
 '\x1eM'
 '\x16W'
 '\xe6WQ'
 '\xc4\xb4\x01\x02NU'
 '\xc6\x15E'
 '\x12O'
 '\xe2\x18B'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02J'
 '\x02R'
 '\x02T'
 '\x02X'
 '\x02Y'
 '\x90\x0c\x02LA'
 '\xfa\nI'
 '\x03U'
'\x07'
 '\xaaaL'
 '\xe7\xf1\x01A'
'\x02'
 '\xc5\xcc\x02\x02AY'
'\x04'
 '\xb6\xe2\x01E'
 '\x97YH'
'\x04'
 '\xd6[A'
 '\xd7\xdf\x01H'
'\x04'
 '\x1aH'
 '\xfb\xd1\x02A'
'\x02'
 '\x9f\x8d\x02I'
'\x02'
 '\x87\xb8\x02A'
'\xea\x02'
 '\xc2\x01A'
 '\x98\x05\x02ER'
 '\xa2\x01H'
 '\xb4\x1b\x1eRESENTATION FORM FOR VERTICAL '
 '\xd3\xbb\x01I'
'@'
 '\x12L'
 'KR'
'\x04'
 '2L'
 '\xa1\xe5\x01\x06M BRAN'
'\x02'
 '\x9b\xbe\x02A'
'<'
 'p\x0bENTHESIZED '
 '\xde0A'
 '\xd9\x8e\x02\x08TNERSHIP'
'8'
 '\xb0\x01\x12KOREAN CHARACTER O'
 '9\x15LATIN CAPITAL LETTER '
'\x04'
 '" '
 '\xad\xc6\x02\x02JE'
'\x02'
 '\x97\x88\x02H'
'4'
 '\xca\xcc\x02A'
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
'\x08'
 '\xe4m\x08SON WITH'
 '\x90K\nMANENT PAP'
 '\x82\x83\x01 '
 '\xb5\t\x08PENDICUL'
'\x86\x02'
 ':A'
 '\xf9\x15\tOENICIAN '
'\xcc\x01'
 'l\x06GS-PA '
 '\xad\t\x10ISTOS DISC SIGN '
'p'
 'd\x07LETTER '
 '\xe4\x05\x05MARK '
 'FS'
 '!\x04DOUB'
'`'
 '\x86\x02A'
 '\x96\x01C'
 'nD'
 '*S'
 '>T'
 '8\x05VOICE'
 '\xd6WN'
 '\xc27G'
 '\xd6\nK'
 '\x02P'
 '\x02Z'
 '\xb2xE'
 '\xf2\x18B'
 '\x02F'
 '\x02H'
 '\x02J'
 '\x02L'
 '\x02M'
 '\x02Q'
 '\x02R'
 '\x02W'
 '\x02X'
 '\x02Y'
 '\x8a\x17I'
 '\x02O'
 '\x03U'
'\x07'
 'P\x08LTERNATE'
 '!\x08SPIRATED'
'\x02'
 '\x0b '
'\x02'
 '\xc3\xad\x02Y'
'\x02'
 '\x0b '
'\x02'
 '\xa3\xad\x02F'
'\x06'
 '\x1aA'
 '\xf7\xac\x02H'
'\x05'
 '\x0bN'
'\x02'
 '\x19\x04DRAB'
'\x02'
 '\x11\x02IN'
'\x02'
 '\xf7\xfe\x01D'
'\x06'
 '\xa2\xac\x02D'
 '\x02Z'
 '\x8b\x17A'
'\x06'
 '\xacS\x04MALL'
 '\xce\xd8\x01H'
 '\x8b\x17A'
'\x0c'
 '\x9e\x9a\x01S'
 '\x02T'
 '\xa2\x91\x01H'
 '\x8b\x17A'
'\x04'
 '*D'
 '\xc5\xaf\x01\x04LESS'
'\x02'
 '\x9b\xa6\x02 '
'\x04'
 '0\x08DOUBLE S'
 '\x03S'
'\x02'
 '\xbf~H'
'\n'
 '\x1c\x03ING'
 '3U'
'\x02'
 '\xb1\x86\x02\x07LE HEAD'
'\x08'
 'NB'
 'i\x0fPERFIXED LETTER'
'\x06'
 'A\x0eJOINED LETTER '
'\x06'
 '\x9e\xa8\x02R'
 '\x02W'
 '\x03Y'
'\x02'
 '\xd7\xa3\x02 '
'\\'
 '\xe2\x01B'
 '\x9e\x01C'
 '\xb0\x02\x02DO'
 ' \x02FL'
 '\x12G'
 'BH'
 'H\x02LI'
 ' \x02MA'
 ':P'
 '\xa6\x01R'
 '2S'
 '\xa6\x01T'
 'rW'
 '\xd8\xc0\x01\x02OX'
 '\x862A'
 '\xfe\x03V'
 '\xd59\x02EA'
'\n'
 '0\x02EE'
 '\x12O'
 '=\x04ULLS'
'\x05'
 '\xf3\x01H'
'\x04'
 '$\x03OME'
 '\xa3\xbc\x02W'
'\x02'
 '\xef\x8d\x02R'
'\x02'
 '\xc5\xdb\x01\x02 L'
'\x10'
 '.A'
 'rL'
 '\x12O'
 '\xf5\x05\x02HI'
'\x06'
 'X\x02PT'
 '\x80\xfe\x01\x0bRPENTRY PLA'
 '\xe7<T'
'\x02'
 '\xd3\xfd\x01I'
'\x02'
 '\xf7jU'
'\x06'
 '\x1aL'
 '\x1d\x02MB'
'\x02'
 '\xf9\xb3\x02\x02UM'
'\x05'
 '\x91\xa5\x02\rINING OBLIQUE'
'\x04'
 '\xca\xb5\x02L'
 '\xbf\x03V'
'\x02'
 '\xc7RU'
'\x04'
 '.R'
 '\xe1\xe6\x01\x05AUNTL'
'\x02'
 '\xe32A'
'\x06'
 '&E'
 '\xba\xca\x01O'
 '\xf7ZI'
'\x02'
 '\x0bL'
'\x02'
 '\x9b\xe6\x01M'
'\x04'
 '\x86\xdf\x01L'
 '\x83YD'
'\x04'
 '$\x02NA'
 '\x85R\x02TT'
'\x02'
 '\xdbOC'
'\x08'
 'H\x03APY'
 '\x12L'
 '\xdd\xab\x02\x07EDESTRI'
'\x02'
 '\xa7vR'
'\x04'
 '(\x03ANE'
 '\xb9\x02\x02UM'
'\x02'
 '\xa9\xfa\x01\x02 T'
'\x04'
 '\xb0O\x04OSET'
 '\xff\xe2\x01A'
'\x0c'
 'p\x02HI'
 '\x84\x81\x02\x04TRAI'
 '\x8a\x1aA'
 '\xbe\x0eL'
 '\xe9\n\x07MALL AX'
'\x04'
 '\x1aE'
 '\xcf\xb4\x02P'
'\x02'
 '\x93\xad\x02L'
'\x06'
 'D\x05ATTOO'
 '\xf0\xda\x01\x03UNN'
 '\xcb=I'
'\x02'
 '\x15\x03ED '
'\x02'
 '\xe7QH'
'\x04'
 '\xb4(\x05AVY B'
 '\xdb\x10O'
':'
 'h\x07LETTER '
 '\xec\x02\x07NUMBER '
 '\x81\x01\x04WORD'
','
 '\xf6\x01A'
 '"S'
 '6T'
 '\x869K'
 '\x86\x03W'
 '\xbc3\x02RO'
 '\xd2!Z'
 '\x9c\x0b\x02HE'
 '\xb2AB'
 '\x80\x0c\x02QO'
 '6M'
 '\x12N'
 '\xbe\x01Y'
 '\xb46\x03GAM'
 '\x94\x06\x03LAM'
 '\x82\x07P'
 '-\x03DEL'
'\x04'
 '\xb2\xea\x01L'
 '\xdb?I'
'\x06'
 '\xba\xeb\x01H'
 '\xdc#\x02EM'
 '\x83\x0eA'
'\x04'
 '\x96\xeb\x01A'
 '\xbfDE'
'\x0c'
 '\x18\x02ON'
 '\x1fT'
'\x04'
 '\x0bE'
'\x05'
 '\xfb, '
'\x08'
 '&W'
 '\xe6\xf2\x01H'
 '\xd75E'
'\x04'
 '\xa2,E'
 '\xbf\x82\x02O'
'\x02'
 '\xed\x1c\x05 SEPA'
'\x1a'
 '\xf4\x01\x02CO'
 '"E'
 '(\x0bIDEOGRAPHIC'
 ',\x05LEFT '
 '`\x06RIGHT '
 '\xaa\x01S'
 '\xa0\xd6\x01\x10HORIZONTAL ELLIP'
 '\x97\x18Q'
'\x04'
 '\xee\xed\x01M'
 '\x838L'
'\x02'
 '\xad\xd3\x01\x05XCLAM'
'\x04'
 '\x0b '
'\x04'
 '\x82\xed\x01C'
 '\x8b\x03F'
'\x04'
 '\xc2\x01S'
 '\xc1\xd7\x01\x10WHITE LENTICULAR'
'\x06'
 'bS'
 '!\x14WHITE LENTICULAR BRA'
'\x02'
 '\xed\x10\x04QUAR'
'\x04'
 '\xbe\xd7\x01C'
 '\r\x02KC'
'\x02'
 '\x8d\xdb\x01\x02EM'
'\xe8\x01'
 'd\x02AI'
 '\xa2\x01E'
 '\xda\tI'
 '\xa4\x0e\x05OMAN '
 '\xb9\x06\x04UMI '
'\x08'
 '(\x04SED '
 '\xf7\xa7\x02N'
'\x06'
 '@\x08DOTTED I'
 '\x02I'
 '\xcf\xa6\x02S'
'\x02'
 '\xbd\x0c\x08NTERPOLA'
'X'
 '\x98\x01\x05JANG '
 '\xa4\x05\x05VERSE'
 '\xa5\x7f\x13STRICTED LEFT ENTRY'
'J'
 '\x80\x01\x0fCONSONANT SIGN '
 '8\x07LETTER '
 '\x92\x02S'
 '#V'
'\x08'
 '"N'
 '\xbe\xa4\x02H'
 '\x03R'
'\x05'
 '\xbb\xa4\x02G'
'.'
 '\x9a\x01M'
 '"N'
 '\xe6\x8b\x02B'
 '\x02C'
 '\x02D'
 '\x02G'
 '\x02H'
 '\x02J'
 '\x02K'
 '\x02L'
 '\x02P'
 '\x02R'
 '\x02S'
 '\x02T'
 '\x02W'
 '\x02Y'
 '\x8b\x17A'
'\x04'
 '\x82\x8c\x02B'
 '\x8b\x17A'
'\x0c'
 '2Y'
 '\xbeoG'
 '\xf6\x9b\x01D'
 '\x8b\x17A'
'\x04'
 '\xae\x8b\x02J'
 '\x8b\x17A'
'\x02'
 '\x0bE'
'\x02'
 '\xaf\xe7\x01C'
'\x12'
 ':I'
 '\x11\nOWEL SIGN '
'\x02'
 '\xbf8R'
'\x10'
 '2A'
 '\x1eE'
 '\xde\xa0\x02I'
 '\x02O'
 '\x03U'
'\x04'
 '\xf6\xa0\x02I'
 '\x03U'
'\x07'
 '\xda\xa0\x02A'
 '\x03U'
'\n'
 '\x1e '
 '\xf1\x01\x02D '
'\x06'
 '\xc0\x01\x15TILDE OPERATOR ABOVE '
 '\xad\x0e\x15SOLIDUS PRECEDING SUB'
'\x04'
 '\x8a\xc7\x01L'
 '\x15\x04RIGH'
'\x04'
 '$\x03FOR'
 '\x97\xe3\x01Q'
'\x02'
 ')\x08KED PARA'
'\x02'
 '\x1d\x05GRAPH'
'\x02'
 '\x97\x8c\x02O'
'*'
 '<\x03GHT'
 '\xe1\xa5\x01\x06NG POI'
'('
 '6 '
 '\x82\x07-'
 '}\x06WARDS '
'\x16'
 '`\x06ANGLE '
 '\xaa\x01D'
 'nL'
 'P\x02RA'
 ':S'
 '\xbe\x01T'
 '[V'
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
 '\xf3\x83\x02K'
'\x04'
 '\x0bO'
'\x04'
 '@\x04UBLE'
 '\xbd\x02\x07TTED SU'
'\x02'
 '\x99\xc6\x01\x02 P'
'\x02'
 '9\x0cOW PARAPHRAS'
'\x02'
 '\xcf\xc6\x01E'
'\x02'
 '\xa9\x02\nISED OMISS'
'\x06'
 '\x96\x01U'
 '\x9c\x11\x12-SHAPED BAG DELIMI'
 '\xd1\xb3\x01\tIDEWAYS U'
'\x02'
 'M\x06BSTITU'
'\x02'
 ')\x08RANSPOSI'
'\x02'
 '\x0bT'
'\x02'
 '\x8d\xc4\x01\x03ION'
'\x02'
 'U\x13ERTICAL BAR WITH QU'
'\x02'
 '\x8b\xa4\x01I'
'\x04'
 'Q\x12FACING SVASTI SIGN'
'\x05'
 '\xad\x80\x02\x05 WITH'
'\x0e'
 ',\x06ARROW '
 '\xcf\x04Q'
'\x0c'
 'x\x07ABOVE R'
 '\xec\x01\x08THROUGH '
 '\x81\x01\x07WITH TI'
'\x04'
 '%\x07EVERSE '
'\x04'
 '6A'
 'Y\tTILDE OPE'
'\x02'
 '5\x0bLMOST EQUAL'
'\x02'
 '\x0b '
'\x02'
 '\xf3\xe3\x01T'
'\x02'
 '\x0bR'
'\x02'
 '\x11\x02AT'
'\x02'
 '\xf7\x8b\x02O'
'\x04'
 '@\tGREATER-T'
 '\x15\x03SUP'
'\x02'
 '\xdf\x85\x02H'
'\x02'
 '\x11\x02ER'
'\x02'
 '\xaf\xbe\x01S'
'\x04'
 '\x11\x02P '
'\x04'
 '\x1aD'
 '\x19\x02UP'
'\x02'
 '\x15\x03OWN'
'\x02'
 '\x99\xfe\x01\x02WA'
'\x02'
 '!\x06UADRUP'
'\x02'
 '\x9f3L'
' '
 '\x88\x01\x07CENTURI'
 '"D'
 'd\x03QUI'
 '\x1c\x08NUMERAL '
 '\x9a\x02S'
 'nU'
 'WA'
'\x02'
 '\x0bA'
'\x02'
 '\xe7\xfe\x01L'
'\x06'
 'bE'
 '\xc0\x03\x05UPOND'
 'I\x0cIMIDIA SEXTU'
'\x02'
 '\xbd\x03\x03NAR'
'\x08'
 't\x06FIFTY '
 '(\x0cONE HUNDRED '
 '=\x05SIX L'
'\x04'
 '2T'
 'I\x05EARLY'
'\x02'
 '\x0bT'
'\x02'
 '\x19\x04HOUS'
'\x02'
 '\xcb\x83\x02A'
'\x02'
 '\x15\x03ATE'
'\x02'
 '\x85\x87\x02\x04 FOR'
'\n'
 '*E'
 '\xb5\x01\x05ILIQU'
'\x08'
 '<\x02MU'
 ' \x05STERT'
 '\x15\x02XT'
'\x02'
 '\x11\x02NC'
'\x02'
 '_I'
'\x02'
 '1\x02IU'
'\x04'
 '\x12A'
 '#U'
'\x02'
 '\x0bN'
'\x02'
 '\xfb\xf9\x01S'
'\x02'
 '\x0bL'
'\x02'
 '\xdb\xf9\x01A'
'>'
 '^D'
 '\\\tFRACTION '
 '\xbd\x01\x07NUMBER '
'\x12'
 '\x1d\x05IGIT '
'\x12'
 '\x8a\xca\x01E'
 '\x1eF'
 '6N'
 '\x0eO'
 '\x12S'
 'CT'
'\x08'
 '0\x04ONE '
 '\x85\xf5\x01\x02TW'
'\x06'
 '&H'
 '"Q'
 '-\x03THI'
'\x02'
 '\x0bA'
'\x02'
 '\xa7\xc0\x01L'
'\x02'
 '\x15\x03UAR'
'\x02'
 '\xb7\xef\x01T'
'\x02'
 '\xaf\xfe\x01R'
'$'
 '\\\x05EIGHT'
 '"F'
 '^S'
 ',\x04NINE'
 '"T'
 'Q\x02ON'
'\x04'
 '\xd6\x02 '
 '\x9f\x82\x02Y'
'\x08'
 '\x12I'
 '#O'
'\x04'
 '\xe2\x01V'
 '\x9b\x95\x01F'
'\x04'
 '\xf4\x01\x02UR'
 '\xe7\x94\x01R'
'\x08'
 '(\x04EVEN'
 '\x01\x02IX'
'\x04'
 '\xae\x01 '
 '\x9f\xa9\x01T'
'\n'
 '"H'
 ':W'
 '\xab\xfc\x01E'
'\x04'
 '(\x02RE'
 '\x99\x95\x01\x02IR'
'\x02'
 '3E'
'\x04'
 '\x12E'
 '\x17O'
'\x02'
 '\xf7\x94\x01N'
'\x02'
 '\x0b '
'\x02'
 '\x0bH'
'\x02'
 '\xd1\x92\x01\x03UND'
'\xfe\x05'
 '\xea\x02A'
 '\x9c\x17\x02CA'
 '\x12E'
 '\x92\x01H'
 '\xdc\x08\tLAVONIC A'
 '.O'
 '\xdc\x01\x06PESMIL'
 '\x14\x05QUARE'
 '\xfe\x0fT'
 '\xa2\x01U'
 '\x88\n\x06WUNG D'
 '"Y'
 '\xc2@K'
 '\xcc)\x04MALL'
 '\x95<\x11NOWMAN WITHOUT SN'
'\x9e\x02'
 'l\x03ILB'
 '\x10\x08MARITAN '
 '\xbd\x0e\tURASHTRA '
'\x02'
 '\xb7^O'
'z'
 '\xb2\x01A'
 ',\x07LETTER '
 '\xce\x03M'
 '\xf8\x02\x0cPUNCTUATION '
 '\x89\x04\x0bVOWEL SIGN '
'\x02'
 '\xf1\xa3\x01\x06BBREVI'
','
 '\xc2\x01B'
 ' \x02GA'
 '\x16I'
 '&K'
 '\x10\x02LA'
 '\x12M'
 '\x16R'
 '\x12S'
 '.T'
 '\xaa\x02A'
 '\x94W\x03DAL'
 '\xba Y'
 '\x9c9\x02QU'
 'FN'
 '\x8a\tZ'
 '\xb3\x0fF'
'\x04'
 '\xce\xe3\x01A'
 '\xff\x16I'
'\x02'
 '\xbf\xef\x01M'
'\x06'
 '\xa2\xfa\x01N'
 '\x02T'
 '\x03Y'
'\x02'
 '\xa3\x03A'
'\x02'
 '\x9bZB'
'\x02'
 '\x83\xf6\x01I'
'\x02'
 '\xaf9I'
'\x04'
 '\xa4\x07\x03ING'
 '\x9f\xe7\x01H'
'\x06'
 '\xb2\x02A'
 '\xdc\x9d\x01\x05SAADI'
 '\xf7XI'
'\x12'
 '`\x04ARK '
 '\xa5\x01\x0fODIFIER LETTER '
'\x0c'
 '\\\x03DAG'
 '\x10\x02IN'
 'ZE'
 '\x96\x03N'
 '\x8d\xdf\x01\x05OCCLU'
'\x02'
 '\xef6E'
'\x05'
 '\x11\x02-A'
'\x02'
 '\x0bL'
'\x02'
 '\xdb\xb0\x01A'
'\x06'
 '"E'
 '>S'
 '\xeb\xf5\x01I'
'\x02'
 '\x85w\x0bPENTHETIC Y'
'\x02'
 '\xfb\x05H'
'\x1c'
 'vA'
 '\x8a\x01B'
 '(\tMELODIC Q'
 '\x02Q'
 '"N'
 '"S'
 'nZ'
 '\xa9\x04\x02TU'
'\n'
 'H\x04FSAA'
 '\x16N'
 '\x1c\x02TM'
 '!\x04RKAA'
'\x02'
 '\x93\xf4\x01Q'
'\x04'
 '\x1aN'
 '\xb7\x84\x01G'
'\x02'
 '\x0bA'
'\x02'
 '\x8f\xaf\x01A'
'\x02'
 '\xfb\xae\x01N'
'\x02'
 '\x0bI'
'\x02'
 '\xab\xd0\x01T'
'\x02'
 '\xadT\x04EQUD'
'\x04'
 'H\x06HIYYAA'
 '\x11\x08OF MASHF'
'\x02'
 '\xc3SL'
'\x02'
 '\xbfRA'
'\x04'
 '\x1eA'
 '\x85S\x02IQ'
'\x02'
 '\xe3\xab\x01E'
'\x1e'
 'X\x05LONG '
 '2O'
 '6S'
 '\xeeXA'
 '\xa6\x97\x01E'
 '\x02I'
 '\x03U'
'\n'
 '\xceYA'
 '\xa6\x97\x01E'
 '\x02I'
 '\x03U'
'\x07'
 '\x9dY\tVERLONG A'
'\x04'
 '"H'
 '\xb1\xaa\x01\x02UK'
'\x02'
 '\x15\x03ORT'
'\x02'
 '\xcb\xd8\x01 '
'\xa2\x01'
 '\xd0\x01\x11CONSONANT SIGN HA'
 '"D'
 'x\x07LETTER '
 '\x90\x03\x05SIGN '
 'Y\x0bVOWEL SIGN '
'\x02'
 '\x0bA'
'\x02'
 '\x93\xa9\x01R'
'\x18'
 '"O'
 'BA'
 '\xcf\xae\x01I'
'\x02'
 '\x0bU'
'\x02'
 '\x0bB'
'\x02'
 '\x19\x04LE D'
'\x02'
 '\x0bA'
'\x02'
 '\x87\xa7\x01N'
'd'
 '\xc6\x01D'
 '.L'
 '"N'
 '2T'
 '.V'
 '\x82@S'
 '\xba\x01B'
 '\x02C'
 '\x02G'
 '\x02J'
 '\x02K'
 '\x02P'
 '\xd2\x18A'
 '\xee\x04I'
 '\x16U'
 '\xe2ZE'
 '\x12O'
 '\xe2\x18H'
 '\x02M'
 '\x02R'
 '\x03Y'
'\x08'
 '\xdeBD'
 '\xa2\x91\x01H'
 '\x8b\x17A'
'\x04'
 '\xd2\xd3\x01L'
 '\x8b\x17A'
'\x08'
 '\xb2\xd3\x01G'
 '\x02N'
 '\x02Y'
 '\x8b\x17A'
'\x08'
 '\xe2AT'
 '\xa2\x91\x01H'
 '\x8b\x17A'
'\n'
 '\xba\x01O'
 '\xa7\xe8\x01A'
'\x06'
 '\x1aV'
 '\xf3\xc7\x01A'
'\x04'
 '\x0bI'
'\x04'
 '\x1aR'
 '\xe3\xc5\x01S'
'\x02'
 '\xc7\xaa\x01A'
'\x1e'
 '@\x02VO'
 '\x96]A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'\x08'
 '!\x06CALIC '
'\x08'
 '\xd6cL'
 '\xd3*R'
'\x02'
 '\x8bnL'
'\x06'
 'P\x05MISEX'
 '\x02X'
 '\x1d\tSQUIQUADR'
'\x02'
 '\xed\xe3\x01\x02TI'
'\x02'
 '\x0bA'
'\x02'
 '\x9f\xe6\x01T'
'd'
 ':A'
 '\x99\xa9\x01\x08INTO SHR'
'b'
 'H\x02MR'
 '\x11\x0cVIAN LETTER '
'\x02'
 '\xefrO'
'`'
 '\x9a\x02A'
 '\x82\x01B'
 '\x10\x03CHU'
 '\x12D'
 '\x12E'
 'FG'
 '\x16H'
 '*I'
 '*K'
 '\x12M'
 '.O'
 'X\x02PE'
 '\x16R'
 '\x16S'
 '\x1eT'
 '<\x02WO'
 ' \x02YE'
 '\xccl\x02LO'
 '\xfe+N'
 '\xce\tF'
 'nU'
 '\xde\tZ'
 '\xc2\x17V'
 '\x89\x14\x03JUD'
'\x10'
 'NR'
 '\xd2\xb4\x01D'
 '\x8a\x1cS'
 '\xb2\x0cI'
 '\x82\x05G'
 '\x02W'
 ';H'
'\x04'
 '\x1aR'
 '\xa7\xe2\x01E'
'\x02'
 '\xa3\x89\x01A'
'\x02'
 '\xb7\x12I'
'\x02'
 '\xdfwR'
'\x02'
 '\x93\x1fE'
'\x08'
 '&A'
 '\xb2\xd6\x01G'
 '\xd3\x05R'
'\x04'
 '\xb6\xe1\x01R'
 '\x03T'
'\x02'
 '\x93\xd6\x01A'
'\x04'
 '\xbc\xc5\x01\x02A-'
 '\xb7\x10U'
'\x06'
 '\xb6\xda\x01A'
 '\xf2\x05C'
 ';F'
'\x02'
 '\xebmI'
'\x04'
 '\x16I'
 '\xb3pE'
'\x02'
 '\xd7\xdf\x01M'
'\x0c'
 'BO'
 '\xbe\xbe\x01A'
 '\xb2\x13I'
 '\xc2\rU'
 '\x0eN'
 '\x03R'
'\x02'
 '\xff\xde\x01Z'
'\x02'
 '\x9f\xa4\x01E'
'\x02'
 '\xcb\xd9\x01O'
'\x04'
 '\xb6\xde\x01U'
 'GO'
'\x06'
 '\x1aH'
 '\xbb\xde\x01O'
'\x04'
 '\xda\x80\x01I'
 '\xeb\x04E'
'\x04'
 '\xd6\xd0\x01O'
 '\xcf\rE'
'\x04'
 '\x82\xde\x01A'
 '\x03W'
'\x02'
 '\xe9\xbc\x01\x06STERIS'
'\n'
 '0\x04CCER'
 '\x1d\x04UTH '
'\x02'
 '\x0b '
'\x02'
 '\xb7kB'
'\x08'
 '\x12E'
 '\x0fW'
'\x04'
 '\x17A'
'\x04'
 '\x0bE'
'\x04'
 '\x0bS'
'\x04'
 '\x11\x02T '
'\x04'
 '(\x04WHIT'
 '\xdb\x9a\x01B'
'\x02'
 '\xf3\x9a\x01E'
'\x02'
 '\xdb\xcc\x01O'
'\x80\x01'
 '\x1e '
 '\xb5\x05\x02D '
'"'
 'zA'
 '\x02V'
 '6D'
 'rE'
 ' \x04FOUR'
 '&H'
 'H\x05WITH '
 '\x8a\x91\x01G'
 '\xaf\x02I'
'\x02'
 '\x1d\x05 OVER'
'\x02'
 '\xaf\xd6\x01 '
'\x08'
 '\x1aM'
 '\xdf\xd9\x01J'
'\x07'
 '\x0b '
'\x04'
 '"S'
 '\xfdi\x03CUB'
'\x02'
 '\x0bQ'
'\x02'
 '\xe1i\x02UA'
'\x04'
 '\xfe\xcd\x01R'
 '\x8b\x0bV'
'\x02'
 '\x9da\x05 CORN'
'\x04'
 '\xd8\x93\x01\nIRAGANA HO'
 '\xebDG'
'\x08'
 'nB'
 ' \tLOWER LEF'
 '\x00\nUPPER RIGH'
 '7T'
'\x02'
 'e\x05OTTOM'
'\x02'
 'E\nT DIAGONAL'
'\x02'
 '\x11\x02OP'
'\x02'
 '\xc9c\x08 HALF BL'
'^'
 '\x94\x02\x16CJK UNIFIED IDEOGRAPH-'
 '\xb2\x06H'
 '\x02M'
 '\x00\x02PP'
 '\x16K'
 'H\x15LATIN CAPITAL LETTER '
 '6S'
 '\xa1\x80\x01\x04FOUR'
'B'
 'T\x024E'
 'R5'
 '\xfa\x016'
 '\xda\x017'
 'f8'
 '\xf9\xb6\x01\x03904'
'\n'
 '20'
 '\xda\x03A'
 '\xc2\xc7\x012'
 '\xab\x058'
'\x04'
 '\xce\xd2\x010'
 '\x039'
'\x18'
 '\x86\x012'
 '\x1e3'
 '"9'
 ' \x02DE'
 '\x90\x03\x028F'
 '\xca~B'
 '0\x0243'
 '\x90G\x0218'
 '\xa9\x05\x02F8'
'\x04'
 '\xf2\xc9\x011'
 '\x034'
'\x04'
 '\x86\x82\x01F'
 '\xfbLC'
'\x04'
 '\xa6\x82\x012'
 '\xc371'
'\x02'
 '\xcf\xd0\x016'
'\x12'
 '>2'
 ':3'
 '25'
 '\x1c\x02F1'
 '\xb9\x01\x0262'
'\x06'
 '"4'
 '29'
 '\xa3\x80\x015'
'\x02'
 '\xd7\xcf\x01B'
'\x04'
 '\x1a5'
 '\xf3\x80\x010'
'\x02'
 '\xa7\xcf\x015'
'\x04'
 '\xd2\x01B'
 '\xfb~9'
'\x02'
 '\xf7\xce\x014'
'\x06'
 '8\x0212'
 '\x14\x02D4'
 '\x95\x88\x01\x0251'
'\x02'
 '\xa7\xce\x011'
'\x02'
 '\x93\xce\x012'
'\x06'
 '.9'
 '\x10\x02D7'
 '\xf9~\x02CA'
'\x02'
 '\xc7~E'
'\x02'
 '\xbf\xcd\x010'
'\x02'
 '\xab\xcd\x01V'
'\x04'
 '0\x07ATAKANA'
 '\xe7sE'
'\x02'
 '\xe7\xb9\x01 '
'\n'
 '\xce\xcc\x01B'
 '\x02N'
 '\x02P'
 '\x02S'
 '\x03W'
'\x06'
 '"A'
 '\xfa\xcb\x01D'
 '\x03S'
'\x02'
 '\x11\x02LT'
'\x02'
 '\x9f\xcb\x01I'
'\x06'
 'D\x07AFF OF '
 '\xa5W\x05RAIGH'
'\x04'
 'D\x03HER'
 '\x85\n\tAESCULAPI'
'\x02'
 '\xe7PM'
'r'
 'nN'
 '\x85\t\x16PERSET PRECEDING SOLID'
'p'
 'X\x0b BEHIND CLO'
 '\x15\x07DANESE '
'\x02'
 '\xab\xc1\x01U'
'n'
 '\xec\x01\x11CONSONANT SIGN PA'
 't\x07LETTER '
 '\x8c\x02\x07SIGN PA'
 '\xc0\x01\rVOWEL SIGN PA'
 '\xff\x83\x01D'
'\x06'
 ' \x02MI'
 '%\x02NY'
'\x02'
 '\x11\x02NG'
'\x02'
 '\xb3\x7fK'
'\x04'
 '\x16A'
 '\xb7\x05I'
'\x02'
 '\xd3\xaa\x01K'
'@'
 '\xea\x01S'
 '\xda\x1bK'
 'fN'
 '\xee\x1cE'
 '\xe2ZA'
 '\xf2\x18B'
 '\x02C'
 '\x02D'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02J'
 '\x02L'
 '\x02M'
 '\x02P'
 '\x02Q'
 '\x02R'
 '\x02T'
 '\x02V'
 '\x02W'
 '\x02X'
 '\x02Y'
 '\x02Z'
 '\x8a\x17I'
 '\x02O'
 '\x03U'
'\x04'
 '\xf6\xac\x01Y'
 '\x8b\x17A'
'\x08'
 '\x1c\x03MAA'
 '\x17N'
'\x02'
 '\xd7\xb1\x01E'
'\x06'
 '\x12G'
 'SY'
'\x04'
 '\x1eL'
 '\x1d\x03WIS'
'\x02'
 '\xb1\xbd\x01\x02AY'
'\x02'
 '\xa3\xbb\x01A'
'\x02'
 '\x11\x02EC'
'\x02'
 '\xb7\xa1\x01E'
'\x0c'
 '\x12M'
 '\x1bN'
'\x02'
 '\x89p\x02EP'
'\n'
 '`\x03EUL'
 ' \x03GHU'
 '\x12O'
 '\x14\x02YU'
 '\xad\x93\x01\x04AELA'
'\x02'
 '\x0bE'
'\x02'
 '\xef\xb5\x01U'
'\x02'
 '\xa7|L'
'\x02'
 '\x97\x93\x01L'
'\x02'
 '\x83|K'
'\x02'
 '\x97\xaf\x01U'
'\x02'
 '\x0bA'
'\x02'
 '\xb3\xae\x01S'
'f'
 '\xdc\x01\x0bLOTI NAGRI '
 '\x80\x05\x0cRIAC LETTER '
 '\xd9l\x17MBOL FOR SAMARITAN SOUR'
'X'
 '\xb4\x01\x07LETTER '
 '\x9c\x02\x0cPOETRY MARK-'
 ',\x05SIGN '
 'I\x0bVOWEL SIGN '
'@'
 '\xaa\x01D'
 '*R'
 '"T'
 '\x92 B'
 '\x02C'
 '\x02G'
 '\x02J'
 '\x02K'
 '\x02P'
 '\xfelH'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x02S'
 '\xf2-A'
 '\x02E'
 '\x02I'
 '\x02O'
 '\x03U'
'\x08'
 '\xd6 D'
 '\xfelH'
 '\xf3-O'
'\x04'
 '\xaa\x8d\x01R'
 '\xf3-O'
'\x08'
 '\x8e T'
 '\xfelH'
 '\xf3-O'
'\x08'
 '\xd2\xba\x011'
 '\x022'
 '\x023'
 '\x034'
'\x06'
 '\xf2\x98\x01A'
 '\x14\x03DVI'
 '\x8d\n\x05HASAN'
'\n'
 '\xee\x8b\x01O'
 '\xf2-A'
 '\x02E'
 '\x02I'
 '\x03U'
'\x0c'
 'P\x08PERSIAN '
 'e\x08SOGDIAN '
'\x06'
 'L\x02BH'
 '\x90q\x04GHAM'
 '\x815\x05DHALA'
'\x02'
 '\x8f\xa6\x01E'
'\x06'
 '0\x02KH'
 '\x84q\x02ZH'
 '\x83FF'
'\x02'
 '\x0bA'
'\x02'
 '\xc7\xa5\x01P'
'\xae\x0b'
 '\x8e\x01A'
 '\xea+E'
 '\x92 H'
 '\x82\x03I'
 '\xd6\x11O'
 '\xa6\x07R'
 '4\x06URNED '
 '\xa5\x01\x06WO DOT'
'\xae\x08'
 ',\x02I '
 '\xc5\x1e\x04MIL '
'\xd4\x03'
 'p\nLE LETTER '
 '\xf8\x02\x05THAM '
 '\xc5\x13\x05VIET '
'F'
 '\xa6\x01A'
 '\x1eE'
 '\x1eN'
 '"T'
 '\xb6\nK'
 '\x02P'
 '\xb2xU'
 '\x12O'
 '\xe2\x18F'
 '\x02H'
 '\x02L'
 '\x02M'
 '\x02Q'
 '\x02S'
 '\x02V'
 '\x02X'
 '\x02Y'
 '\x8b\x17I'
'\x07'
 '\xfa\xb2\x01U'
 ';I'
'\x07'
 '\x96\xb3\x01E'
 '\x03H'
'\x04'
 '\xf2\x9b\x01G'
 '\x8b\x17A'
'\x12'
 '@\x04ONE-'
 '\xf2\tS'
 '\xa2\x91\x01H'
 '\x8b\x17A'
'\n'
 '\x96\xb2\x012'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'\xfe\x01'
 '\xc4\x01\x02CO'
 '\xf4\x03\x04HORA'
 '\x00\x04THAM'
 '\x18\x07LETTER '
 '\xa8\x05\x05SIGN '
 '\x89\x06\x0bVOWEL SIGN '
'\x14'
 '\xa4\x01\rNSONANT SIGN '
 '\xc5\xae\x01\x15MBINING CRYPTOGRAMMIC'
'\x12'
 '\x94\x01\x06FINAL '
 '\x16L'
 '4\x10HIGH RATHA OR LO'
 '\x1eM'
 '\xee\x95\x01B'
 '\x03S'
'\x02'
 '\xcf\x8a\x01N'
'\x04'
 '2O'
 '\xf1\t\x07A TANG '
'\x02'
 '\x0bW'
'\x02'
 '\xcbe '
'\x06'
 '0\x06EDIAL '
 '\xc3\xac\x01A'
'\x04'
 '\xb6\x95\x01L'
 '\x03R'
'\x14'
 '\xfdm\x02 D'
'j'
 '\xa2\x01G'
 '0\x05HIGH '
 '\x82\x01L'
 '\xf6\x01N'
 '*R'
 '\xb2\x1cI'
 '\x16U'
 '\xea\\O'
 '\xea\x16B'
 '\x02D'
 '\x02M'
 '\x02W'
 '\xd2\x16E'
 ';A'
'\x02'
 '\x19\x04REAT'
'\x02'
 '\xd3\x87\x01 '
' '
 'VS'
 '\xba\x01C'
 '\x02P'
 '\x02T'
 '"K'
 '*R'
 '\xda\x90\x01F'
 '\x02H'
 '\x03Y'
'\x06'
 '\xd6\x92\x01H'
 '\x02S'
 '\x8b\x17A'
'$'
 '8\x03OW '
 '\x86yA'
 '\xf2\x18L'
 '\xd3\x16U'
'\x1c'
 'RC'
 '\x02P'
 '\x02T'
 '"K'
 '*R'
 '\xda\x90\x01F'
 '\x02H'
 '\x02S'
 '\x03Y'
'\x04'
 '\x9e\x91\x01H'
 '\x8b\x17A'
'\x06'
 '\xfe\x90\x01H'
 '\x02X'
 '\x8b\x17A'
'\x02'
 '\x95\x8c\x01\x02AT'
'\x06'
 '\xba\x90\x01G'
 '\x02Y'
 '\x8b\x17A'
'\x08'
 '\x1aA'
 '\xcb\xa6\x01U'
'\x07'
 '\xf6\x8f\x01N'
 '\x03T'
'2'
 '\xae\x01H'
 '\x1eK'
 '\xb0\x01\x04MAI '
 'nR'
 '|\x02SA'
 'd\x04TONE'
 '(\x05WIANG'
 '\xa8\x02\x04DOKM'
 '\x9dp\x02CA'
'\x04'
 '\xb2LO'
 '\xefMA'
'\x0e'
 '4\x04HUEN'
 '\x96\x03A'
 '\xe7\x87\x01E'
'\x08'
 'P\x06 TONE-'
 '\x95\x99\x01\x08-LUE KAR'
'\x06'
 '\x8a\xa4\x013'
 '\x024'
 '\x035'
'\x08'
 '8\x04KANG'
 '\x1c\x03YAM'
 '\x8b\nS'
'\x05'
 '\x0b '
'\x02'
 '\xd3\x04L'
'\x02'
 '\x93\x82\x01O'
'\x04'
 'd\x10EVERSED ROTATED '
 '\x8d\t\x04A HA'
'\x02'
 '\xf3\x85\x01R'
'\x08'
 '0\x03TKA'
 '\xd6\x96\x01W'
 '\xe3\nK'
'\x04'
 '\x11\x02AN'
'\x05'
 '\x0bK'
'\x02'
 '\xe3\\U'
'\x04'
 '\x0b-'
'\x04'
 '\x8e\xa1\x011'
 '\x032'
'\x05'
 '\xe9\x7f\x02WA'
'&'
 'VA'
 '$\x04MAI '
 '"O'
 '&T'
 'bU'
 '\xd2\x13I'
 '\xef\x8a\x01E'
'\t'
 '\x82\xa0\x01A'
 '\x02E'
 '\x03I'
'\x02'
 '\x0bS'
'\x02'
 '\xc7\x9f\x01A'
'\x0b'
 '\xd2HA'
 '\xeeVO'
 '\x03Y'
'\x04'
 '"A'
 '-\x04HAM '
'\x02'
 '\x15\x03LL '
'\x02'
 '\xd7\x87\x01A'
'\x02'
 '\xc7qA'
'\t'
 '\xc2nU'
 '\xfb/E'
'\x90\x01'
 '\xbc\x01\x07LETTER '
 '\xb0\x02\x05MAI K'
 '0\x07SYMBOL '
 '\x88\x01\tTONE MAI '
 'M\x06VOWEL '
'`'
 ',\x04HIGH'
 '\x01\x03LOW'
'0'
 '\x0b '
'0'
 '\x96\x01K'
 '\x1eC'
 '\x02P'
 '\x02T'
 '\x1eN'
 '\xe2lB'
 '\x02D'
 '\x02F'
 '\x02G'
 '\x02H'
 '\x02L'
 '\x02M'
 '\x02R'
 '\x02S'
 '\x02V'
 '\x02Y'
 '\xf3-O'
'\x06'
 '\x1aH'
 '\xef\x9a\x01O'
'\x04'
 '\xfalH'
 '\xf3-O'
'\x06'
 '\xdelG'
 '\x02Y'
 '\xf3-O'
'\x04'
 '\x1aH'
 '\xff\x8e\x01A'
'\x02'
 '\x83\x9a\x01I'
'\n'
 '8\x02KO'
 '(\x04HO H'
 '\x12S'
 'CN'
'\x04'
 '$\x03I K'
 '\x9b\x99\x01N'
'\x02'
 '\x93lO'
'\x02'
 '\xab\x95\x01A'
'\x08'
 '*N'
 '\x12T'
 '\xf2jS'
 '\xcf\x0cE'
'\x02'
 '\xa7kU'
'\x02'
 '\xc7jH'
'\x1a'
 '2A'
 '6U'
 '\x1eI'
 '\xa6\x97\x01E'
 '\x03O'
'\n'
 '\xba\x97\x01U'
 ':A'
 '\x02M'
 '\x02N'
 '\x03Y'
'\t'
 '\x1aE'
 '\xa7\x97\x01A'
'\x05'
 '\xa3\x97\x01A'
'\xda\x04'
 '\xd6\x01C'
 '\x9a\x02D'
 '|\x06LETTER'
 '\x12N'
 '*R'
 '\x1c\tSYLLABLE '
 '\x8a\x07Y'
 '\xa0w\x07AS ABOV'
 '\xa0\x04\x05MONTH'
 '\xab\x0bO'
'2'
 'D\tONSONANT '
 '\x89\x02\x03RED'
'0'
 'rK'
 '\x16L'
 '\x12N'
 '&T'
 '\xda9R'
 '\x12S'
 '\xcaYC'
 '\x02H'
 '\x02J'
 '\x02M'
 '\x02P'
 '\x02V'
 '\x03Y'
'\x05'
 '\xd3\x82\x01S'
'\x07'
 '\xbb\x0fL'
'\x0b'
 '\xd6dN'
 '\xfe.G'
 '\x03Y'
'\x05'
 '\xaf\x93\x01T'
'\x06'
 '"A'
 '\x14\x02EB'
 '#I'
'\x02'
 '\xf3\x83\x01Y'
'\x02'
 '\x0bI'
'\x02'
 '\xd3\x83\x01T'
'\x02'
 '\xe1V\x05GIT Z'
'\x02'
 '\xf3L '
'\x02'
 '\x15\x03UMB'
'\x02'
 '\xc7\x07E'
'\x02'
 '\xc1~\x03UPE'
'\x94\x04'
 'vK'
 '\x9e\x01L'
 'zN'
 '\x8a\x01R'
 '>S'
 '\x82\x01T'
 ':C'
 '\x02H'
 '\x02J'
 '\x02M'
 '\x02P'
 '\x02V'
 '\x03Y'
'.'
 '@\x02SS'
 '\xfe\x04A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'\x18'
 '2A'
 '\xee\x04I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'\t'
 '\xd6\x8f\x01A'
 '\x02I'
 '\x03U'
'B'
 ':L'
 '\xea\x03A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
','
 '\xb6\x03L'
 '2A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'n'
 'JN'
 '\xb2\x02G'
 '\x02Y'
 '2A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
','
 '\xae\x02N'
 '2A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
','
 '\xf2\x01R'
 '2A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'D'
 '>H'
 'zS'
 '2A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'\x18'
 '\xa6\x01A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x12O'
 '\xdb\x02R'
','
 '6T'
 '2A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'\x16'
 '.A'
 '&I'
 '\x16U'
 '\xe2ZE'
 '\x13O'
'\x06'
 '\x8e\x8b\x01A'
 '\x02I'
 '\x03U'
'\x05'
 '\xeb\x8a\x01I'
'\x05'
 '\xd7\x8a\x01U'
'\x02'
 '\x11\x02EA'
'\x02'
 '\xab{R'
'\xc0\x01'
 '`\x05LUGU '
 '\xa6\x05N'
 '\x1d\x0cTRAGRAM FOR '
'\x1a'
 '\x94\x01\x0fFRACTION DIGIT '
 '\x98\x02\x07LETTER '
 '(\x05SIGN '
 'WV'
'\x0e'
 'JT'
 '(\x02ON'
 'Q\nZERO FOR O'
'\x08'
 '$\x03HRE'
 '\r\x02WO'
'\x04'
 '\x0bE'
'\x04'
 '\x1d\x05 FOR '
'\x04'
 '"O'
 '\x15\x04EVEN'
'\x02'
 '\x11\x02DD'
'\x02'
 '\x95\x0f\x0c POWERS OF F'
'\x04'
 '\x16D'
 '\xfbbT'
'\x02'
 '\xe7nZ'
'\x04'
 '\x1eA'
 '%\x03TUU'
'\x02'
 '\xf5i\x05VAGRA'
'\x02'
 '\xd3@M'
'\x04'
 '-\tOWEL SIGN'
'\x04'
 '1\n VOCALIC L'
'\x05'
 '\xa7\x84\x01L'
'\x04'
 '\xeepG'
 '\xa7\x13T'
'\xa2\x01'
 '\xc2\x02A'
 '~B'
 '\xaa\x01C'
 '\xd6\x02D'
 '\x96\x03E'
 '\xae\x02U'
 '"F'
 '\xce\x01G'
 '\xb6\x01H'
 '@\x08YOUTHFUL'
 '\\\x02IN'
 '*J'
 '\x12K'
 'zL'
 '\x82\x01M'
 'nO'
 'ZP'
 '\x96\x01R'
 '\xaa\x01S'
 '\xc8\x01\x02WA'
 '\x15\x0fVASTNESS OR WAS'
'\x08'
 'X\x05CCUMU'
 '\x12S'
 '\xfc\x14\x02DV'
 '\xa9 \x05GGRAV'
'\x02'
 '\xb35L'
'\x02'
 '\xaf\tC'
'\x06'
 'h\x03ARR'
 '\x10\x07OLD RES'
 '\x1d\nRANCHING O'
'\x02'
 '\x83iI'
'\x02'
 '\xa14\x03OLU'
'\x02'
 '\x8f\x7fU'
'\x16'
 'H\x03LOS'
 'RO'
 '\x84x\x02HA'
 '\xa9\x05\x03ENT'
'\x06'
 '\x16E'
 '\xe7}U'
'\x04'
 '$\x04D MO'
 '\xf7\nN'
'\x02'
 '\x8blU'
'\x0c'
 '\x1c\x03MPL'
 '\x1fN'
'\x04'
 '\x86\x12I'
 '\xb7 E'
'\x08'
 '*T'
 '\x89$\x05STANC'
'\x06'
 '>A'
 '\x84\x0f\x05RARIE'
 '\xb1"\x02EN'
'\x02'
 '\xbb|C'
'\x14'
 'L\x04ARKE'
 '\x12E'
 '\xa6\x01I'
 'JU'
 '\xe1y\x03OUB'
'\x02'
 '\xc7pN'
'\x06'
 '\xbc\x08\x06CISIVE'
 '\xcc\x03\x04PART'
 '\xb9$\x15FECTIVENESS OR DISTOR'
'\x08'
 'D\x06FFICUL'
 '&M'
 '\xb1\r\x04VERG'
'\x02'
 '\x11\x02TI'
'\x02'
 '\xb3hE'
'\x04'
 '\x84\x01\x02IN'
 '\xa3mM'
'\x0e'
 '`\x05MBELL'
 '\x1eN'
 '\xac\x01\x03TER'
 '\x10\x04XHAU'
 '\xe7uA'
'\x02'
 '\x9d\x01\x03ISH'
'\x06'
 'L\x04COUN'
 '$\x04DEAV'
 '\x11\x05LARGE'
'\x02'
 '\x0bT'
'\x02'
 '\xa1f\x02ER'
'\x02'
 '\xaf:O'
'\x02'
 '\x0bM'
'\x02'
 '\x0bE'
'\x02'
 '\xfbvN'
'\x02'
 '\xa7\tN'
'\x02'
 '\xd3+S'
'\x0c'
 'BO'
 '@\x03ULL'
 '\x88\x06\x03AIL'
 '\x8f2L'
'\x04'
 '"L'
 '\xc5\x05\x03STE'
'\x02'
 '\xcdj\x03LOW'
'\x04'
 '\x16 '
 '\xb3\x02N'
'\x02'
 '\x0bC'
'\x02'
 '\x0bI'
'\x02'
 '\x91r\x02RC'
'\n'
 '`\x08ATHERING'
 '\x12O'
 '4\x03REA'
 'A\x05UARDE'
'\x05'
 '\xcf/ '
'\x02'
 '\x95"\tING TO ME'
'\x02'
 'KT'
'\x04'
 '0\x02AR'
 '5\x06OLDING'
'\x02'
 '\x0bD'
'\x02'
 '\x0bN'
'\x02'
 '\x0bE'
'\x02'
 '\xdbaS'
'\x02'
 '\x0b '
'\x02'
 '\x0bB'
'\x02'
 '\x0bA'
'\x02'
 '\xcfQC'
'\x04'
 '\x16C'
 '\xe3[N'
'\x02'
 '\xb3\x05R'
'\x02'
 '\x93\x19O'
'\x04'
 '<\tEEPING SM'
 '\x1d\x02IN'
'\x02'
 '\x0bA'
'\x02'
 '\xebcL'
'\x02'
 '\xa16\x03SHI'
'\x06'
 '\x1eA'
 '\xf5\\\x02EG'
'\x04'
 '<\x03BOU'
 '\x11\x08W OR MOD'
'\x02'
 '\x8beR'
'\x02'
 '\xcfbE'
'\x06'
 '*E'
 '&I'
 '\x9dd\x03ASS'
'\x02'
 '\x11\x02AS'
'\x02'
 '\x87oU'
'\x02'
 '\x0bR'
'\x02'
 '\xf7gE'
'\x04'
 '<\x03PPO'
 '\xbdf\x07N THE V'
'\x02'
 '\xc9#\x02SI'
'\x08'
 '2A'
 '4\x04ENET'
 '\x11\x02UR'
'\x04'
 ' \x03TTE'
 '\xc7\x02C'
'\x02'
 '\xc7gR'
'\x02'
 '\xbf"R'
'\x02'
 '\x0bI'
'\x02'
 '\xc3\x14T'
'\x0c'
 '"E'
 '\x9d&\x03ITU'
'\n'
 '\x1eL'
 '\x1aS'
 '\xbb\x02A'
'\x02'
 '\xe9k\x02EA'
'\x06'
 '"I'
 '\xb1k\x03PON'
'\x04'
 '\x1aD'
 'Q\x02ST'
'\x02'
 '[E'
'\n'
 '"E'
 '<\x02IN'
 '\x13T'
'\x02'
 '\x0bV'
'\x02'
 '\x11\x02ER'
'\x02'
 '\x0bA'
'\x02'
 '\xeb\x1eN'
'\x02'
 '\x8b`K'
'\x06'
 '&O'
 '\x81Y\x04RENG'
'\x04'
 '\x1c\x02PP'
 '\x9fjV'
'\x02'
 '\xf3dA'
'\x04'
 '\x12I'
 '\x13T'
'\x02'
 '\x8f_T'
'\x02'
 '\xb7XC'
'\x0c'
 'h\x04REE '
 '\xed"\x11UNDER CLOUD AND R'
'\n'
 '\x12D'
 'SL'
'\x04'
 '<\nIMENSIONAL'
 '\xef\x1cO'
'\x02'
 '\x9fe '
'\x06'
 '\x90\x01\x10INES CONVERGING '
 '\x89V\x0eEFTWARDS ARROW'
'\x04'
 '\xea)R'
 '\xef.L'
'\x8a\x01'
 'x\x06BETAN '
 '\xdc\x05\x07FINAGH '
 '\xf0\x07\x04LDE '
 '\xc9\x02\x02NY'
'\x12'
 '\xa4\x01\x07LETTER '
 '\x1c\x05MARK '
 '\x89_\x15SIGN RDEL NAG RDEL DK'
'\x04'
 '\xfe\x1fK'
 '\xbf)R'
'\x0c'
 '\xee\x02B'
 '@\x08MNYAM YI'
 'H CLOSING BRDA RNYING YIG MGO SGAB'
 '\x00 INITIAL BRDA RNYING YIG MGO MDUN'
 '\x11\x08NYIS TSH'
'\x04'
 '\x1aK'
 '\x01\x02SK'
'\x02'
 '!\x06A- SHO'
'\x02'
 '5\x0bG GI MGO RG'
'\x02'
 '\xebUY'
'\x02'
 '\x9f" '
'\x02'
 '\xbbUE'
'n'
 '\x84\x01\x07LETTER '
 '\xbd\x06\x14MODIFIER LETTER LABI'
'l'
 'jA'
 'h\x11BERBER ACADEMY YA'
 '\x1aT'
 '\xd3\x01Y'
'\x04'
 'T\x06YER YA'
 '\x81L\nHAGGAR YAZ'
'\x02'
 '\xffKG'
'\x04'
 '\xd6]H'
 '\x03J'
'\x12'
 '`\x0cAWELLEMET YA'
 '\x11\x08UAREG YA'
'\x02'
 '\xdb\\Z'
'\x10'
 'BG'
 '\xa2\x02K'
 '\x82HZ'
 '\xe2\x06N'
 '\x8a\x0bH'
 '\x03Q'
'\x04'
 '\x86\\H'
 '\x03N'
'R'
 '*A'
 '\xc6\x02E'
 '\x82YI'
 '\x03U'
'M'
 '\xb6\x01D'
 '\x1aG'
 '\x02K'
 '\x0eB'
 '\x02H'
 '\x12R'
 '\x12S'
 '\x1aT'
 '\x1aZ'
 '\xb2GC'
 '\xea\x11A'
 '\x02F'
 '\x02J'
 '\x02L'
 '\x02M'
 '\x02N'
 '\x02P'
 '\x02Q'
 '\x02V'
 '\x02W'
 '\x03Y'
'\t'
 '"D'
 '\xebYH'
'\x07'
 '\x0bH'
'\x05'
 '\xe7YH'
'\x05'
 '\xd7YR'
'\x07'
 '\xc6YH'
 '\x03S'
'\x07'
 '\xaeYH'
 '\x03T'
'\x07'
 '\x96YH'
 '\x03Z'
'\x02'
 '\xffXY'
'\x02'
 '\x19\x04ALIZ'
'\x02'
 '\xf7\x1dA'
'\x08'
 'D\x08OPERATOR'
 'i\x05WITH '
'\x02'
 ')\x08 ABOVE L'
'\x02'
 '\x11\x02EF'
'\x02'
 '\xb9\x16\x06TWARDS'
'\x06'
 '\x12D'
 ';R'
'\x04'
 '\x11\x02OT'
'\x04'
 '\x0b '
'\x04'
 'FA'
 '\x9f<B'
'\x02'
 '\x15\x03ING'
'\x02'
 '\x0b '
'\x02'
 '\x0bA'
'\x02'
 '\x0bB'
'\x02'
 '\xfb\x18O'
'\x02'
 '!\x06 TWO D'
'\x02'
 '\xa9\t\x03OTS'
'\x1e'
 'rP'
 '\xd9\x02\x17RTOISE SHELL BRACKETED '
'\n'
 '\x0b '
'\n'
 'X\x03LEF'
 '\x00\x04RIGH'
 '*P'
 'NT'
 'A\x05CURLY'
'\x02'
 '\xb1\x01\x06T HALF'
'\x02'
 '!\x06ARENTH'
'\x02'
 '\x0bE'
'\x02'
 '\x0bS'
'\x02'
 '\xd7AI'
'\x02'
 '=\rORTOISE SHELL'
'\x02'
 '\x1d\x05 BRAC'
'\x02'
 '\x0bK'
'\x02'
 '\xf3QE'
'\x14'
 '\xc0\x01\x16CJK UNIFIED IDEOGRAPH-'
 '\x85\x02\x14LATIN CAPITAL LETTER'
'\x12'
 '(\x024E'
 '\x1e5'
 '.6'
 'O7'
'\x04'
 '\xb6\x010'
 '\xbbL8'
'\x04'
 '\x98\x01\x02B8'
 '\x91G\x022D'
'\x06'
 ',\x0225'
 '\x125'
 '\xe9L\x0272'
'\x02'
 '\x87O3'
'\x02'
 '?5'
'\x04'
 ' \x020B'
 '\x11\x026D'
'\x02'
 '\xc7N9'
'\x02'
 '\xb7N7'
'\x02'
 '\x83= '
'\x02'
 '\x0bI'
'\x02'
 '\x0bC'
'\x02'
 '\x0bO'
'\x02'
 '\xbfGL'
'\x06'
 '\\\x05BLACK'
 '\x00\x05WHITE'
 '\x85\x07\x06SMALL '
'\x02'
 '1\n SHOGI PIE'
'\x02'
 '\x97LC'
'\x04'
 '\x12S'
 'c '
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
 '\x9b7T'
'J'
 '\xbc\x01\x08GARITIC '
 '\xac\x06\x08MBRELLA '
 '~P'
 '\xa54\x14NMARRIED PARTNERSHIP'
'>'
 '0\x07LETTER '
 '\xbf\x05W'
'<'
 '\xbe\x01A'
 '\x18\x02QO'
 '\x12B'
 '\x12D'
 '6G'
 '<\x02HO'
 '\x12K'
 '*L'
 '&M'
 '\x12N'
 '\x10\x02RA'
 '\x12S'
 'VP'
 '\x12T'
 ':Y'
 '\x12Z'
 '\x82\x16W'
 '\xf2-I'
 '\x03U'
'\x04'
 '\x16L'
 '\x93AI'
'\x02'
 '\xaf0P'
'\x02'
 '\x930E'
'\x04'
 '\x12E'
 '\x13H'
'\x02'
 '\xef/L'
'\x02'
 '\xa79A'
'\x04'
 '\x18\x02AM'
 '\x13H'
'\x02'
 '\xbf/L'
'\x02'
 '\xdf\x01A'
'\x05'
 '\x9f/T'
'\x04'
 '\x16A'
 '\xfb.H'
'\x02'
 '\xffEF'
'\x02'
 '\x11\x02AM'
'\x02'
 '\xd3.D'
'\x02'
 '\xefAE'
'\x02'
 '\x93?U'
'\x02'
 '\xe3)S'
'\x08'
 '\x1aA'
 '*H'
 '\x13S'
'\x04'
 '\x16M'
 '\xb3DD'
'\x02'
 '\xdf-K'
'\x02'
 '\xaf>I'
'\x02'
 '\xc7DU'
'\x06'
 '$\x02HA'
 '\x86DE'
 '\x0fO'
'\x02'
 "\xfb'N"
'\x02'
 '\xc7<O'
'\x04'
 '\xda,E'
 '\x97\x17U'
'\x02'
 '\x15\x03ORD'
'\x02'
 '\xe9,\x05 DIVI'
'\x04'
 'T\x02ON'
 '\x9d1\x0eWITH RAIN DROP'
'\x02'
 '\xf9:\x05 GROU'
'\x06'
 '.W'
 'Q\x07 DOWN B'
'\x04'
 '\x1d\x05ARDS '
'\x04'
 '\x1c\x03ANC'
 '\x13B'
'\x02'
 '\xff%O'
'\x02'
 '\x19\x04LACK'
'\x02'
 '\x11\x02 A'
'\x02'
 "\x81'\x02RR"
'\x92\t'
 '^A'
 '\x9a\x17E'
 '\xed\x15\x0fULGAR FRACTION '
'\xb8\x08'
 '`\x02I '
 '\xb9\x12\x11RIATION SELECTOR-'
'\xd8\x04'
 '6C'
 '*D'
 '\xe2\x02F'
 'RQ'
 'i\x02SY'
'\x02'
 '\x0bO'
'\x02'
 '\x0bM'
'\x02'
 "\xab'M"
'\x14'
 '\x0bI'
'\x14'
 '\x19\x04GIT '
'\x14'
 ':E'
 '\x1eF'
 '6N'
 '\x0eO'
 '\x12S'
 'BT'
 '7Z'
'\x02'
 '\xb1=\x03IGH'
'\x04'
 '\x12I'
 '\x13O'
'\x02'
 '\xd7<V'
'\x02'
 '\xc77U'
'\x02'
 '\x0bI'
'\x02'
 '\xab<N'
'\x04'
 '\x12E'
 '\x1fI'
'\x02'
 '\x0bV'
'\x02'
 '\x8b6E'
'\x02'
 '\xa3<X'
'\x04'
 '\x16H'
 '\x8f\x0eW'
'\x02'
 '\x0bR'
'\x02'
 '\xb7;E'
'\x02'
 '\x0bE'
'\x02'
 '\xe3\rR'
'\x02'
 '\x0bU'
'\x02'
 '\x0bL'
'\x02'
 '\x19\x04L ST'
'\x02'
 '\x0bO'
'\x02'
 '\x83;P'
'\x02'
 '\x15\x03UES'
'\x02'
 '\x0bT'
'\x02'
 '\x15\x03ION'
'\x02'
 '\x11\x02 M'
'\x02'
 '\xa5\x19\x02AR'
'\xbe\x04'
 'D\x07LLABLE '
 '\xd5\n\x05MBOL '
'\xa4\x04'
 '\xca\x01D'
 '>B'
 '\x02S'
 '\x02T'
 '\x02Z'
 '>G'
 'rH'
 'NK'
 'rL'
 'zM'
 'NN'
 '\xe2\x02C'
 '\x02F'
 '\x02J'
 '\x02P'
 '\x02R'
 '\x02V'
 '\x02Y'
 'RW'
 '.E'
 '\x1aO'
 '\x1aA'
 '\x02I'
 '\x03U'
'*'
 ':H'
 '\xbe\x07E'
 '\x12O'
 '\xea/A'
 '\x02I'
 '\x03U'
'\x1c'
 '\x8a\x07H'
 '2E'
 '\x12O'
 '\xea/A'
 '\x02I'
 '\x03U'
'"'
 ':B'
 '\xfe\x05E'
 'ZO'
 '\xea/A'
 '\x02I'
 '\x03U'
'\x12'
 'fO'
 '\x96\x05E'
 '\xc20A'
 '\x02I'
 '\x03U'
'\x18'
 '2O'
 '\x96\x05E'
 '\xc6\x01A'
 '\x02I'
 '\x03U'
'\x07'
 '\xd25N'
 '\x03O'
'"'
 ':P'
 '\x8a\x05E'
 '\x12O'
 'nA'
 '\xfe.I'
 '\x03U'
'\x12'
 '\xbe\x04E'
 'ZO'
 'nA'
 '\xfe.I'
 '\x03U'
'\x10'
 '2E'
 '\xb2\x04O'
 '\xea/A'
 '\x02I'
 '\x03U'
'\x07'
 '$\x04NGTH'
 '\xf33E'
'\x02'
 '\x0bE'
'\x02'
 '\x9f\x1dN'
'*'
 '\xaa\x03B'
 '\x00\x02GB'
 '2E'
 '\x12O'
 '\xea/A'
 '\x02I'
 '\x03U'
'Z'
 'RD'
 '\x9e\x01G'
 'rJ'
 '\x02Y'
 '2E'
 '\x12O'
 '\xea/A'
 '\x02I'
 '\x03U'
'\x18'
 '2O'
 '\x8a\x02E'
 '\xfa/A'
 '\x02I'
 '\x03U'
'\x0f'
 ' \x03LE '
 '\xdf1O'
'\n'
 '2S'
 '\xba\x03D'
 '\xea\x16F'
 '\x02K'
 '\x03M'
'\x02'
 '\xb7\x03O'
'\x19'
 '&G'
 '\xca*A'
 '\x02E'
 '\x03O'
'\x10'
 '.E'
 'ZO'
 '\xea/A'
 '\x02I'
 '\x03U'
'\x07'
 '\xbe0E'
 '\x03N'
'\x0e'
 '.E'
 '\x12O'
 '\xea/A'
 '\x02I'
 '\x03U'
'\x05'
 '\xf7/E'
'\x05'
 '\xe7/O'
'\x1c'
 '*E'
 '\x1aO'
 '\x1aA'
 '\x02I'
 '\x03U'
'\t'
 '.E'
 '\xff.N'
'\t'
 '\x16O'
 '\xff.N'
'\x05'
 '\xfb.N'
'\x1a'
 ':B'
 '\x12D'
 'BF'
 '\x1aJ'
 '\x12K'
 '*N'
 '\x1fT'
'\x02'
 '\x9b#A'
'\x06'
 '\x16O'
 '\xf7"A'
'\x04'
 '\x16-'
 '\xdf"O'
'\x02'
 '\xef-O'
'\x04'
 '>E'
 '\x9b\x16A'
'\x02'
 '\xb3"O'
'\x04'
 '\x16E'
 '\x8f"U'
'\x02'
 '\x8b"E'
'\x02'
 '\x0bI'
'\x02'
 '\x83-I'
'\x06'
 '\xea\x15A'
 '\xf6\x0bI'
 '\x03O'
'\xe0\x03'
 'J1'
 '^3'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x029'
 '[2'
'\xce\x01'
 'V0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\xb6\x017'
 '\x028'
 '\x039'
'\x14'
 '\xa2+0'
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
 'V0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 'Z5'
 '\x9a)6'
 '\x027'
 '\x028'
 '\x039'
'\x17'
 '\xee)0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x026'
 '\x027'
 '\x028'
 '\x039'
'\x11'
 '\x96)0'
 '\x021'
 '\x022'
 '\x023'
 '\x024'
 '\x025'
 '\x036'
'R'
 'H\x04DIC '
 '\xfa\x10S'
 'a\x07RTICAL '
'F'
 '<\x05SIGN '
 '\x95\x08\x05TONE '
'&'
 '\x82\x02A'
 '\xd0\x02\x07NIHSHVA'
 '\x12R'
 '\x80\x01\x08HEXIFORM'
 '\x16L'
 'L\x04TIRY'
 '\x1c\x08VISARGA '
 '\x95\x06\x11YAJURVEDIC MIDLIN'
'\x0c'
 'H\x08NUSVARA '
 '\xcd\x01\x05RDHAV'
'\n'
 '\x94\x01\x04ANTA'
 '\x00\x04BAHI'
 '\x18\tUBHAYATO '
 '\xa9\x03\nVAMAGOMUKH'
'\x02'
 '\x15\x03RGO'
'\x02'
 '\x0bM'
'\x02'
 '\xeb\x07U'
'\x02'
 '\x11\x02IS'
'\x02'
 '\x11\x02AR'
'\x02'
 '\xff\x0bG'
'\x02'
 '\xef\x0bS'
'\x06'
 'd\x10EVERSED VISARGA '
 '\x19\x05THANG'
'\x04'
 '\xfa\x05A'
 '\x17U'
'\x02'
 '\x11\x02 L'
'\x02'
 '\x1d\x05ONG A'
'\x02'
 '\x11\x02NU'
'\x02'
 '\xe5\x05\x02SV'
'\x02'
 '\x0bA'
'\x02'
 '\xfb K'
'\n'
 '(\x03ANU'
 '\x02U'
 '\x8b\tS'
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
 '\xfb\x11I'
' '
 '\xb8\x02\x02DO'
 ' \x02KA'
 '\x88\x01\x04PREN'
 '\x1c\x02SH'
 '\x1eT'
 '\x88\x01\x06CANDRA'
 'H\x0bYAJURVEDIC '
 '\xb8\x01\x0cATHARVAVEDIC'
 '\x01\x11RIGVEDIC KASHMIRI'
'\x04'
 '\x94\x02\x02UB'
 'ST'
'\x04'
 '8\x03RSH'
 '\x1d\x07THAKA A'
'\x02'
 '\x0bA'
'\x02'
 '\x8b\x05N'
'\x02'
 '\x11\x02NU'
'\x02'
 '\xd9\x04\x03DAT'
'\x02'
 '\x0bK'
'\x02'
 '\xbf\x04H'
'\x02'
 '\x0bA'
'\x02'
 '\xa3\x04R'
'\x06'
 '4\x03RIP'
 '\x1eW'
 '\r\x04HREE'
'\x02'
 '\x0bL'
'\x02'
 '\x8b\x03E'
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
 '\xdb\x19W'
'\x08'
 '\xb4\x01\nAGGRAVATED'
 '\x16I'
 '\x89\x01\x1bKATHAKA INDEPENDENT SVARITA'
'\x02'
 '\x11\x02 I'
'\x02'
 '1\nNDEPENDENT'
'\x02'
 '\x11\x02 S'
'\x02'
 '\x15\x03VAR'
'\x02'
 '\x0bI'
'\x02'
 '\x0bT'
'\x02'
 '\x87\x17A'
'\x05'
 '%\x07 SCHROE'
'\x02'
 '\x0bD'
'\x02'
 '\x8b\x11E'
'\n'
 '\xa8\x01\x11BAR WITH HORIZONT'
 '\\\x04FOUR'
 '(\nLINE EXTEN'
 '\x1eM'
 'WT'
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
 '\x83\x14K'
'\x02'
 '\x15\x03 DO'
'\x02'
 '\xef\x02T'
'\x02'
 '\x0bS'
'\x02'
 '\xc3\rI'
'\x02'
 'A\x0eALE WITH STROK'
'\x02'
 '\x9f\x04E'
'\x02'
 '\x0bI'
'\x02'
 '\x0bL'
'\x02'
 '\xc3\x12D'
'\x08'
 ',\x04ONE '
 'e\x03ZER'
'\x06'
 ',\x03SEV'
 '\x02T'
 '\r\x02NI'
'\x02'
 '\x0bE'
'\x02'
 '\x0bN'
'\x02'
 '\x0bT'
'\x02'
 '\xe7\x11H'
'\x02'
 '\x1d\x05O THI'
'\x02'
 '\x11\x02RD'
'\x02'
 '\xa3\x11S'
'2'
 'rA'
 '\xe6\x01H'
 '\x91\x0e\x14ORD SEPARATOR MIDDLE'
'\x04'
 '\x98\x01\x05RNING'
 '1\x1cVE ARROW POINTING DIRECTLY L'
'\x02'
 '\x0b '
'\x02'
 '\x0bS'
'\x02'
 '\xc1\x08\x02IG'
'\x02'
 '\xc5\x0e\x02EF'
','
 '@\x08EELCHAIR'
 '=\x04ITE '
'\x02'
 '\x1d\x05 SYMB'
'\x02'
 '\x0bO'
'\x02'
 '\xcb\rL'
'*'
 '\xa2\x01D'
 '\xb0\x01\x04FLAG'
 '\xaa\x01H'
 'FL'
 'p\x06MEDIUM'
 'fR'
 'JP'
 'H\x06SMALL '
 'rT'
 '\xab\x03V'
'\x06'
 ':R'
 '\xe5\n\tIAMOND IN'
'\x04'
 '%\x07AUGHTS '
'\x04'
 '\x12K'
 '+M'
'\x02'
 '\x0bI'
'\x02'
 '\x0bN'
'\x02'
 '\x87\x0bG'
'\x02'
 '\xcf\x04A'
'\x05'
 '\x95\x01" WITH HORIZONTAL MIDDLE BLACK STRI'
'\x02'
 '\x97\tP'
'\x04'
 '2E'
 '\xdd\x07\x07ORIZONT'
'\x02'
 '\xc3\x02X'
'\x04'
 '&E'
 '\xdd\x07\x04ARGE'
'\x02'
 '-\tFT LANE M'
'\x02'
 '\xc1\x02\x02ER'
'\x06'
 '\x0b '
'\x06'
 '\x1eD'
 '\xde\x01L'
 '7S'
'\x02'
 '\x19\x04IAMO'
'\x02'
 '\x0bN'
'\x02'
 '\xb7\x07D'
'\x02'
 'E\x0fIGHT-POINTING P'
'\x02'
 '\x15\x03ENT'
'\x02'
 '\x11\x02AG'
'\x02'
 '\x0bO'
'\x02'
 '\xa7\x06N'
'\x04'
 '\x12L'
 '7S'
'\x02'
 '\x15\x03OZE'
'\x02'
 '\x0bN'
'\x02'
 '\xa7\x05G'
'\x02'
 '\x0bT'
'\x02'
 '\x0bA'
'\x02'
 '\xb7\x05R'
'\x06'
 '\x16R'
 '\x93\x02W'
'\x04'
 '\x98\x01\x04APEZ'
 ')\x1dIANGLE CONTAINING SMALL WHITE'
'\x02'
 '\x0bI'
'\x02'
 '\x0bU'
'\x02'
 '\xdb\x03M'
'\x02'
 '\x19\x04 TRI'
'\x02'
 '\x11\x02AN'
'\x02'
 '\x0bG'
'\x02'
 '\xd7\x02L'
'\x02'
 '\x0bO'
'\x02'
 'U\x13-WAY LEFT WAY TRAFF'
'\x02'
 '\x0bI'
'\x02'
 '\x8f\x02C'
'\x04'
 '\x11\x02ER'
'\x04'
 '8\x03TIC'
 '9\x07Y SMALL'
'\x02'
 ')\x08AL ELLIP'
'\x02'
 'KS'
'\x02'
 '\x11\x02 S'
'\x02'
 '\x11\x02QU'
'\x02'
 '\x0bA'
'\x02'
 '\x0bR'
'\x02'
 '7E'
'\x02'
 '\x11\x02 D'
'\x02'
 '\x0bO'
'\x02'
 '\x0bT'
'\x03\x00'

)
# estimated 32.66 KiB
_pos_to_code = [
65852, 65853, 65854, 65855, 65806, 65815, 65842, 65833, 65824, 65812, 65839, 65803, 65830, 65821, 65811, 65838,
65802, 65829, 65820, 65805, 65814, 65841, 65832, 65823, 65804, 65813, 65840, 65831, 65822, 65807, 65816, 65843,
65834, 65825, 65810, 65837, 65801, 65828, 65819, 65809, 65836, 65800, 65827, 65818, 65808, 65835, 65799, 65826,
65817, 65848, 65851, 65849, 65850, 65847, 65792, 65793, 65794, 9941, 9879, 1630, 1538, 1887, 1885, 1886,
1908, 1907, 1913, 1912, 1915, 1914, 1874, 1875, 1872, 1876, 1877, 1873, 1878, 1882, 1774, 1881,
1910, 1909, 1911, 1599, 1598, 1597, 1889, 1888, 1916, 1903, 1906, 1902, 1880, 1879, 1791, 1892,
1891, 1596, 1595, 1890, 1919, 1896, 1897, 1895, 1905, 1883, 1775, 1899, 1900, 1918, 1904, 1901,
1884, 1917, 1898, 1893, 1894, 65021, 1629, 1544, 1623, 1554, 1555, 1552, 1537, 1539, 1553, 1551,
1556, 1557, 1558, 1559, 1562, 1561, 1560, 1622, 1627, 1626, 1628, 1566, 1550, 1549, 1625, 1536,
1624, 1542, 1543, 1545, 1546, 68352, 68353, 68357, 68355, 68358, 68359, 68356, 68354, 68373, 68374, 68372,
68393, 68405, 68388, 68387, 68386, 68391, 68390, 68389, 68371, 68370, 68369, 68403, 68401, 68404, 68399, 68394,
68395, 68378, 68381, 68377, 68385, 68384, 68380, 68379, 68402, 68400, 68364, 68365, 68366, 68367, 68360, 68361,
68362, 68363, 68375, 68383, 68376, 68368, 68398, 68392, 68382, 68397, 68396, 68409, 8525, 1547, 9875, 8371,
9190, 9883, 7005, 7007, 7006, 6917, 6918, 6987, 6928, 6953, 6954, 6936, 6937, 6948, 6944, 6943,
6949, 6984, 6927, 6933, 6934, 6919, 6920, 6929, 6930, 6921, 6922, 6938, 6939, 6931, 6981, 6932,
6982, 6958, 6925, 6926, 6950, 6945, 6935, 6940, 6951, 6952, 6957, 6923, 6924, 6962, 6960, 6961,
6946, 6947, 6942, 6941, 6983, 6985, 6986, 6963, 6955, 6959, 6956, 7022, 7025, 7021, 7024, 7023,
7020, 7019, 7027, 7026, 7012, 7013, 7018, 7015, 7017, 7016, 7010, 7014, 7009, 7011, 7032, 7036,
7033, 7034, 7035, 7031, 7030, 7029, 7028, 7003, 7008, 7002, 6916, 6915, 6912, 6913, 6914, 6964,
6972, 6973, 6970, 6971, 6968, 6969, 6974, 6975, 6977, 6976, 6965, 6978, 6979, 6966, 6967, 6980,
7004, 7000, 6997, 6996, 7001, 6993, 6999, 6998, 6995, 6994, 6992, 42737, 42736, 42741, 42740, 42733,
42713, 42699, 42712, 42692, 42706, 42683, 42719, 42734, 42735, 42682, 42729, 42657, 42725, 42659, 42718, 42670,
42666, 42716, 42701, 42675, 42727, 42720, 42671, 42722, 42723, 42702, 42726, 42677, 42707, 42708, 42709, 42686,
42674, 42694, 42731, 42695, 42685, 42684, 42673, 42664, 42691, 42715, 42703, 42693, 42698, 42711, 42696, 42667,
42717, 42704, 42661, 42721, 42669, 42668, 42705, 42700, 42680, 42678, 42710, 42688, 42681, 42732, 42676, 42679,
42730, 42728, 42672, 42662, 42724, 42687, 42689, 42690, 42697, 42714, 42660, 42656, 42665, 42663, 42658, 42738,
42742, 42739, 42743, 9918, 2510, 2493, 2555, 9187, 11044, 11035, 9944, 11045, 11047, 9912, 9927, 11049,
11050, 11089, 9951, 9942, 9873, 9960, 9923, 9922, 11042, 11052, 11091, 11039, 11054, 11037, 11812, 11813,
9181, 9185, 9183, 12589, 6663, 6662, 6659, 6658, 6671, 6670, 6667, 6666, 6661, 6668, 6665, 6657,
6678, 6669, 6656, 6674, 6660, 6673, 6676, 6664, 6675, 6672, 6677, 6686, 6683, 6681, 6679, 6682,
6680, 6687, 983050, 6322, 6321, 5759, 6387, 6388, 6389, 6382, 6384, 6381, 6383, 6386, 6366, 6367,
6329, 6328, 6342, 6344, 6346, 6348, 6332, 6331, 6361, 6343, 6345, 6347, 6349, 6362, 6363, 6359,
6358, 6360, 6356, 6357, 6320, 6351, 6352, 6353, 6354, 6350, 6355, 6368, 6341, 6335, 6379, 6378,
6385, 6380, 6338, 6337, 6336, 6334, 6326, 6325, 6324, 6377, 6376, 6374, 6375, 6373, 6372, 6371,
6327, 6369, 6370, 6365, 5756, 5757, 5752, 5753, 5754, 5755, 5751, 5758, 6323, 6364, 6340, 6339,
5120, 6333, 6330, 66225, 66246, 66211, 66214, 66254, 66218, 66250, 66251, 66252, 66253, 66229, 66238, 66244,
66227, 66224, 66222, 66223, 66242, 66243, 66232, 66221, 66247, 66230, 66226, 66239, 66212, 66248, 66256, 66235,
66208, 66215, 66210, 66220, 66234, 66255, 66240, 66241, 66236, 66237, 66231, 66209, 66233, 66245, 66213, 66249,
66217, 66219, 66216, 66228, 9936, 9963, 8373, 9907, 43587, 43597, 43596, 43573, 43572, 43574, 43571, 43553,
43550, 43549, 43545, 43542, 43541, 43590, 43586, 43588, 43595, 43585, 43584, 43594, 43591, 43593, 43589, 43592,
43530, 43531, 43538, 43536, 43537, 43543, 43544, 43551, 43552, 43548, 43547, 43546, 43558, 43559, 43533, 43532,
43529, 43528, 43535, 43534, 43527, 43526, 43540, 43539, 43520, 43524, 43560, 43556, 43555, 43557, 43554, 43523,
43521, 43525, 43522, 43614, 43613, 43615, 43612, 43561, 43568, 43569, 43562, 43563, 43567, 43566, 43565, 43570,
43564, 43608, 43605, 43604, 43609, 43601, 43607, 43606, 43603, 43602, 43600, 9939, 9911, 9962, 9938, 127277,
12869, 12871, 12870, 12868, 127275, 127276, 12924, 12925, 12875, 12876, 12878, 12877, 12874, 12873, 12872, 12879,
12926, 127278, 64107, 64108, 64109, 64112, 64113, 64114, 64115, 64116, 64117, 64118, 64119, 64120, 64121, 64122,
64123, 64124, 64125, 64126, 64127, 64128, 64129, 64130, 64131, 64132, 64133, 64134, 64135, 64136, 64137, 64138,
64139, 64140, 64141, 64142, 64143, 64144, 64145, 64146, 64147, 64148, 64149, 64150, 64151, 64152, 64153, 64154,
64155, 64156, 64157, 64158, 64159, 64160, 64161, 64162, 64163, 64164, 64165, 64166, 64167, 64168, 64169, 64170,
64171, 64172, 64173, 64174, 64175, 64176, 64177, 64178, 64179, 64180, 64181, 64182, 64183, 64184, 64185, 64186,
64187, 64188, 64189, 64190, 64191, 64192, 64193, 64194, 64195, 64196, 64197, 64198, 64199, 64200, 64201, 64202,
64203, 64204, 64205, 64206, 64207, 64208, 64209, 64210, 64211, 64212, 64213, 64214, 64215, 64216, 64217, 12752,
12743, 12748, 12757, 12741, 12750, 12769, 12747, 12749, 12744, 12742, 12746, 12768, 12758, 12754, 12763, 12770,
12764, 12753, 12740, 12767, 12760, 12759, 12745, 12766, 12762, 12755, 12761, 12736, 12765, 12739, 12737, 12738,
12756, 12751, 12771, 7623, 7625, 8432, 857, 7677, 65062, 11774, 11744, 11768, 11747, 11757, 11765, 11751,
11752, 11753, 11756, 11775, 11772, 11767, 11763, 11762, 11760, 11758, 11770, 11771, 11748, 11749, 11773, 11769,
11761, 11746, 11764, 11759, 11750, 11755, 11745, 11766, 11754, 42621, 1159, 42610, 42608, 42609, 42620, 42607,
7627, 43248, 43244, 43245, 43246, 43247, 43242, 43243, 43249, 43240, 43237, 43236, 43241, 43233, 43239, 43238,
43235, 43234, 43232, 7616, 7617, 856, 861, 860, 862, 863, 858, 7629, 7621, 7624, 119363, 119362,
119364, 7643, 7646, 7647, 7649, 7650, 7636, 7637, 7638, 7635, 7645, 7653, 7651, 7626, 7639, 7641,
7640, 7642, 7644, 7648, 7652, 7654, 7678, 852, 8430, 849, 8429, 8427, 65060, 65061, 7622, 7620,
7628, 7679, 854, 848, 853, 8431, 855, 8428, 7618, 7619, 7633, 7634, 850, 859, 7631, 7630,
7632, 851, 11505, 11504, 11503, 11464, 11392, 11501, 11446, 11499, 11452, 11458, 11442, 11466, 11448, 11450,
11398, 11412, 11436, 11420, 11472, 11414, 11422, 11478, 11468, 11470, 11476, 11474, 11482, 11460, 11480, 11454,
11462, 11444, 11486, 11488, 11484, 11490, 11440, 11456, 11402, 11428, 11408, 11430, 11404, 11438, 11424, 11400,
11410, 11396, 11406, 11394, 11426, 11434, 11416, 11418, 11432, 11517, 11518, 11514, 11515, 11516, 11513, 11465,
11393, 11502, 11447, 11500, 11453, 11459, 11443, 11467, 11449, 11451, 11399, 11413, 11437, 11421, 11473, 11415,
11423, 11479, 11469, 11471, 11477, 11475, 11483, 11461, 11481, 11455, 11463, 11445, 11487, 11489, 11485, 11491,
11441, 11457, 11403, 11429, 11409, 11431, 11405, 11439, 11425, 11401, 11411, 11397, 11407, 11395, 11427, 11435,
11417, 11419, 11433, 11497, 11492, 11493, 11494, 11498, 11495, 11496, 11519, 119664, 119661, 119660, 119665, 119657,
119663, 119662, 119659, 119658, 119655, 119652, 119651, 119656, 119648, 119654, 119653, 119650, 119649, 9904, 127370, 9876,
9932, 74794, 74780, 74820, 74821, 74765, 74758, 74771, 74791, 74801, 74844, 74836, 74837, 74809, 74755, 74829,
74777, 74786, 74762, 74768, 74834, 74835, 74808, 74812, 74814, 74815, 74813, 74754, 74828, 74776, 74785, 74790,
74800, 74761, 74767, 74839, 74838, 74822, 74825, 74823, 74824, 74795, 74781, 74766, 74759, 74772, 74850, 74849,
74840, 74847, 74831, 74804, 74773, 74782, 74842, 74845, 74848, 74796, 74818, 74819, 74817, 74793, 74779, 74764,
74757, 74770, 74802, 74803, 74792, 74756, 74830, 74778, 74763, 74816, 74769, 74806, 74807, 74833, 74788, 74789,
74798, 74799, 74810, 74811, 74753, 74827, 74775, 74784, 74760, 74752, 74826, 74832, 74805, 74841, 74774, 74783,
74787, 74797, 74843, 74846, 74867, 74866, 74865, 74864, 73728, 73733, 73735, 73731, 73734, 73736, 73730, 73732,
73729, 73738, 73742, 73741, 73744, 73745, 73748, 73740, 73739, 73746, 73747, 73743, 73749, 73750, 73751, 73753,
73752, 73754, 73755, 73757, 73759, 73758, 73760, 73765, 73766, 73767, 73763, 73762, 73768, 73764, 73761, 73770,
73769, 73773, 73776, 73777, 73774, 73775, 73778, 73780, 73781, 73782, 73784, 73788, 73789, 73787, 73785, 73786,
73791, 73790, 73783, 73771, 73772, 73779, 73737, 73756, 73792, 73795, 73796, 73797, 73798, 73799, 73800, 73794,
73793, 73801, 73804, 73803, 73802, 73805, 73806, 73807, 73808, 73809, 73810, 73811, 73812, 73813, 73814, 73815,
73816, 73817, 73818, 73819, 73820, 73821, 73822, 73823, 73825, 73826, 73829, 73830, 73831, 73828, 73836, 73837,
73833, 73835, 73834, 73827, 73824, 73832, 73839, 73840, 73841, 73838, 73842, 73844, 73845, 73846, 73847, 73848,
73849, 73843, 73850, 73852, 73853, 73851, 73854, 73855, 73856, 73857, 73858, 73860, 73861, 73862, 73863, 73864,
73865, 73859, 73866, 73867, 73868, 73869, 73873, 73874, 73870, 73872, 73871, 73875, 73879, 73883, 73884, 73880,
73881, 73882, 73885, 73887, 73886, 73889, 73890, 73891, 73892, 73893, 73895, 73896, 73900, 73901, 73902, 73903,
73904, 73905, 73906, 73907, 73908, 73899, 73897, 73898, 73894, 73888, 73876, 73877, 73878, 73909, 73911, 73914,
73912, 73913, 73917, 73918, 73915, 73916, 73920, 73919, 73921, 73922, 73924, 73925, 73926, 73923, 73929, 73930,
73927, 73928, 73931, 73932, 73933, 73934, 73935, 73936, 73937, 73938, 73939, 73940, 73941, 73943, 73942, 73945,
73944, 73946, 73947, 73948, 73950, 73951, 73952, 73953, 73955, 73956, 73957, 73958, 73959, 73960, 73962, 73963,
73964, 73961, 73949, 73954, 73965, 73966, 73967, 73968, 73969, 73970, 73971, 73972, 73974, 73975, 73978, 73977,
73976, 73910, 73979, 73980, 73981, 73973, 73982, 73983, 73984, 73987, 73985, 73986, 73988, 73990, 73989, 73994,
73995, 73998, 73997, 73996, 73999, 73992, 73993, 74001, 74004, 74003, 74005, 74002, 74000, 73991, 74006, 74008,
74009, 74010, 74012, 74011, 74013, 74014, 74015, 74016, 74017, 74019, 74020, 74021, 74024, 74023, 74022, 74007,
74018, 74025, 74027, 74026, 74028, 74029, 74030, 74031, 74037, 74033, 74032, 74034, 74036, 74035, 74038, 74039,
74040, 74043, 74044, 74042, 74045, 74041, 74046, 74047, 74050, 74052, 74051, 74053, 74054, 74058, 74055, 74057,
74056, 74059, 74060, 74061, 74062, 74064, 74065, 74063, 74066, 74067, 74048, 74070, 74049, 74068, 74069, 74071,
74072, 74073, 74074, 74075, 74077, 74076, 74078, 74079, 74080, 74081, 74082, 74085, 74086, 74084, 74083, 74087,
74090, 74089, 74088, 74091, 74092, 74093, 74094, 74096, 74097, 74095, 74100, 74101, 74102, 74103, 74104, 74105,
74114, 74112, 74113, 74115, 74110, 74111, 74117, 74116, 74119, 74122, 74123, 74120, 74121, 74107, 74106, 74098,
74099, 74109, 74108, 74124, 74118, 74125, 74126, 74131, 74132, 74128, 74129, 74130, 74133, 74134, 74135, 74136,
74137, 74138, 74139, 74140, 74141, 74142, 74127, 74144, 74146, 74147, 74145, 74152, 74153, 74150, 74151, 74148,
74149, 74154, 74157, 74158, 74163, 74164, 74155, 74165, 74160, 74161, 74156, 74159, 74162, 74166, 74143, 74167,
74168, 74169, 74170, 74172, 74171, 74175, 74173, 74174, 74176, 74177, 74182, 74183, 74180, 74181, 74186, 74184,
74185, 74188, 74190, 74189, 74187, 74194, 74195, 74193, 74191, 74192, 74196, 74197, 74198, 74199, 74200, 74201,
74202, 74205, 74206, 74207, 74208, 74204, 74209, 74211, 74210, 74212, 74213, 74215, 74214, 74216, 74218, 74217,
74179, 74178, 74203, 74219, 74220, 74223, 74224, 74221, 74222, 74226, 74227, 74228, 74229, 74230, 74225, 74231,
74233, 74234, 74232, 74235, 74237, 74258, 74259, 74261, 74260, 74240, 74241, 74246, 74247, 74245, 74248, 74249,
74250, 74251, 74255, 74254, 74242, 74256, 74243, 74252, 74253, 74239, 74238, 74244, 74257, 74263, 74265, 74264,
74266, 74269, 74270, 74271, 74236, 74262, 74267, 74268, 74272, 74273, 74274, 74278, 74279, 74275, 74276, 74277,
74284, 74290, 74296, 74294, 74295, 74292, 74293, 74291, 74297, 74298, 74299, 74300, 74301, 74286, 74287, 74285,
74289, 74288, 74280, 74281, 74282, 74283, 74302, 74304, 74307, 74306, 74305, 74308, 74310, 74309, 74311, 74303,
74312, 74314, 74313, 74315, 74316, 74319, 74321, 74320, 74322, 74324, 74325, 74323, 74327, 74329, 74328, 74330,
74332, 74333, 74331, 74334, 74335, 74326, 74317, 74336, 74318, 74337, 74339, 74347, 74348, 74342, 74343, 74341,
74344, 74340, 74346, 74345, 74349, 74354, 74355, 74352, 74350, 74358, 74359, 74353, 74351, 74356, 74357, 74360,
74361, 74338, 74362, 74363, 74364, 74365, 74367, 74368, 74369, 74373, 74374, 74375, 74376, 74370, 74371, 74372,
74377, 74378, 74379, 74381, 74380, 74382, 74366, 74383, 74384, 74385, 74386, 74387, 74389, 74388, 74391, 74392,
74394, 74395, 74400, 74399, 74406, 74402, 74403, 74404, 74405, 74401, 74398, 74397, 74393, 74396, 74390, 74408,
74407, 74409, 74410, 74411, 74412, 74413, 74414, 74421, 74422, 74419, 74417, 74416, 74420, 74418, 74415, 74424,
74425, 74423, 74426, 74428, 74429, 74427, 74432, 74434, 74433, 74430, 74431, 74435, 74437, 74436, 74438, 74441,
74440, 74448, 74446, 74444, 74445, 74447, 74449, 74442, 74443, 74439, 74451, 74452, 74453, 74450, 74454, 74455,
74456, 74458, 74457, 74459, 74461, 74462, 74463, 74460, 74465, 74464, 74466, 74468, 74469, 74471, 74472, 74473,
74474, 74467, 74470, 74475, 74477, 74478, 74479, 74476, 74480, 74481, 74482, 74483, 74488, 74486, 74487, 74485,
74484, 74489, 74490, 74491, 74494, 74497, 74499, 74500, 74498, 74495, 74496, 74501, 74505, 74506, 74502, 74503,
74504, 74492, 74493, 74507, 74510, 74512, 74511, 74509, 74508, 74515, 74516, 74522, 74523, 74519, 74520, 74517,
74518, 74521, 74524, 74534, 74535, 74525, 74526, 74527, 74528, 74529, 74531, 74532, 74533, 74530, 74536, 74538,
74537, 74539, 74540, 74541, 74542, 74545, 74546, 74547, 74544, 74543, 74549, 74550, 74551, 74552, 74553, 74556,
74558, 74557, 74559, 74560, 74562, 74564, 74563, 74570, 74569, 74572, 74574, 74573, 74555, 74567, 74571, 74565,
74561, 74568, 74554, 74566, 74575, 74576, 74548, 74577, 74581, 74579, 74580, 74578, 74584, 74583, 74582, 74586,
74587, 74588, 74585, 74513, 74514, 74589, 74591, 74590, 74593, 74592, 74595, 74598, 74599, 74601, 74596, 74597,
74600, 74602, 74603, 74604, 74605, 74606, 74594, 9982, 67594, 67595, 67596, 67597, 67598, 67599, 67600, 67601,
67602, 67603, 67604, 67605, 67606, 67607, 67608, 67609, 67610, 67611, 67612, 67613, 67614, 67615, 67616, 67617,
67618, 67619, 67620, 67621, 67622, 67623, 67624, 67625, 67626, 67627, 67628, 67629, 67630, 67631, 67632, 67633,
67634, 67635, 67636, 67637, 67589, 67592, 67644, 67647, 67639, 67640, 67584, 67585, 67586, 67587, 67588, 1310,
42602, 42586, 42572, 42584, 42630, 42568, 42604, 42562, 42626, 42632, 42624, 1312, 1298, 1314, 1270, 1274,
1276, 1278, 42644, 42588, 42578, 42582, 42566, 42600, 42570, 42574, 1316, 42564, 42580, 1296, 1302, 42596,
42598, 42594, 42646, 42634, 42640, 42638, 42642, 42636, 42576, 1304, 42590, 42628, 42560, 1300, 1306, 1308,
42622, 42606, 7467, 42623, 1311, 42603, 42587, 42573, 42585, 42631, 42569, 42605, 42563, 42627, 42633, 42625,
1313, 1299, 1315, 1271, 1275, 1277, 1279, 42645, 42589, 42579, 42583, 42567, 42601, 42571, 42575, 1317,
1231, 42565, 42581, 1297, 1303, 42597, 42599, 42595, 42647, 42635, 42641, 42639, 42643, 42637, 42577, 1305,
42591, 42629, 42561, 1301, 1307, 1309, 66598, 66599, 66638, 66639, 2429, 2427, 2428, 2431, 2426, 2308,
2418, 2430, 2425, 43251, 43255, 43254, 43253, 43252, 2304, 43250, 43256, 2417, 2389, 2382, 43258, 43257,
43259, 9192, 11030, 11031, 11033, 11032, 127238, 127237, 127242, 127234, 127240, 127239, 127236, 127235, 127241, 127233,
127232, 119557, 119555, 119556, 9868, 9871, 9870, 9869, 119553, 119554, 9902, 9933, 127025, 127026, 127027, 127028,
127029, 127030, 127031, 127032, 127033, 127034, 127035, 127036, 127037, 127038, 127039, 127040, 127041, 127042, 127043, 127044,
127045, 127046, 127047, 127048, 127049, 127050, 127051, 127052, 127053, 127054, 127055, 127056, 127057, 127058, 127059, 127060,
127061, 127062, 127063, 127064, 127065, 127066, 127067, 127068, 127069, 127070, 127071, 127072, 127073, 127024, 127075, 127076,
127077, 127078, 127079, 127080, 127081, 127082, 127083, 127084, 127085, 127086, 127087, 127088, 127089, 127090, 127091, 127092,
127093, 127094, 127095, 127096, 127097, 127098, 127099, 127100, 127101, 127102, 127103, 127104, 127105, 127106, 127107, 127108,
127109, 127110, 127111, 127112, 127113, 127114, 127115, 127116, 127117, 127118, 127119, 127120, 127121, 127122, 127123, 127074,
8284, 11795, 11784, 11798, 11034, 11799, 9890, 9891, 8508, 11796, 11015, 9946, 11790, 77830, 77831, 77832,
77828, 77829, 77824, 77825, 77826, 77827, 77833, 77834, 77835, 77840, 77841, 77844, 77845, 77836, 77837, 77838,
77839, 77842, 77843, 77846, 77847, 77869, 77870, 77872, 77873, 77874, 77875, 77877, 77878, 77871, 77876, 77879,
77880, 77881, 77882, 77860, 77861, 77858, 77859, 77862, 77863, 77864, 77865, 77866, 77867, 77868, 77903, 77848,
77849, 77850, 77851, 77852, 77853, 77854, 77855, 77856, 77857, 77883, 77884, 77885, 77886, 77887, 77888, 77889,
77890, 77891, 77892, 77893, 77894, 77895, 77896, 77897, 77898, 77899, 77900, 77901, 77902, 78867, 78868, 78869,
78861, 78862, 78863, 78864, 78865, 78866, 78870, 78871, 78892, 78893, 78894, 78872, 78873, 78874, 78875, 78876,
78877, 78878, 78879, 78880, 78881, 78882, 78883, 78884, 78885, 78886, 78887, 78888, 78889, 78890, 78891, 77915,
77916, 77917, 77918, 77914, 77919, 77920, 77921, 77922, 77923, 77924, 77925, 77926, 77927, 77928, 77929, 77930,
77931, 77932, 77933, 77934, 77935, 77936, 77937, 77938, 77939, 77940, 77941, 77949, 77950, 77942, 77943, 77944,
77945, 77946, 77947, 77948, 77951, 77974, 77975, 77978, 77979, 77973, 77976, 77977, 77980, 77981, 77982, 77983,
77984, 77991, 77992, 77994, 77995, 77985, 77986, 77987, 77988, 77989, 77990, 77993, 77996, 77997, 77998, 77999,
78000, 78001, 78002, 78003, 78004, 78005, 78006, 78008, 78009, 78011, 78012, 78007, 78010, 78013, 78014, 78015,
78016, 78017, 78025, 78026, 78027, 78028, 78029, 78030, 78031, 78032, 78033, 78018, 78019, 78020, 78021, 78022,
78023, 78024, 77969, 77970, 77962, 77963, 77964, 77965, 77966, 77967, 77968, 77971, 77972, 77952, 77953, 77954,
77955, 77956, 77957, 77958, 77959, 77960, 77961, 78041, 78042, 78043, 78044, 78034, 78035, 78036, 78037, 78038,
78039, 78040, 78057, 78058, 78066, 78067, 78059, 78060, 78061, 78062, 78063, 78064, 78065, 78068, 78073, 78074,
78069, 78070, 78071, 78072, 78075, 78076, 78077, 78051, 78052, 78053, 78054, 78045, 78046, 78047, 78048, 78049,
78050, 78055, 78056, 78078, 78079, 78080, 78081, 78082, 78083, 78084, 78085, 78086, 78087, 78091, 78092, 78088,
78089, 78090, 78093, 78094, 78095, 78096, 78097, 78098, 78111, 78112, 78118, 78119, 78120, 78121, 78110, 78113,
78114, 78115, 78116, 78117, 78122, 78128, 78129, 78130, 78131, 78132, 78133, 78123, 78124, 78125, 78126, 78127,
78134, 78135, 78137, 78138, 78139, 78140, 78136, 78141, 78142, 78100, 78101, 78099, 78102, 78103, 78104, 78105,
78106, 78107, 78108, 78109, 78150, 78151, 78152, 78148, 78149, 78143, 78144, 78145, 78146, 78147, 78153, 78154,
78156, 78157, 78155, 78158, 78159, 78160, 78161, 78162, 78163, 78164, 78165, 78184, 78185, 78186, 78187, 78178,
78179, 78180, 78181, 78182, 78183, 78188, 78189, 78193, 78194, 78196, 78197, 78190, 78191, 78192, 78195, 78198,
78199, 78200, 78201, 78202, 78203, 78204, 78205, 78206, 78166, 78167, 78173, 78174, 78168, 78169, 78170, 78171,
78172, 78175, 78176, 78177, 78212, 78213, 78207, 78208, 78209, 78210, 78211, 78214, 78215, 78220, 78221, 78225,
78226, 78216, 78217, 78218, 78219, 78222, 78223, 78224, 78227, 78228, 78229, 78230, 78231, 78232, 78233, 78234,
78235, 78236, 78237, 78238, 78239, 78240, 78241, 78242, 78244, 78245, 78249, 78250, 78243, 78246, 78247, 78248,
78251, 78252, 78253, 78254, 78255, 78257, 78258, 78256, 78259, 78260, 78261, 78262, 78263, 78264, 78268, 78269,
78270, 78271, 78272, 78273, 78274, 78275, 78276, 78265, 78266, 78279, 78280, 78281, 78282, 78283, 78284, 78267,
78277, 78278, 78285, 78286, 78289, 78290, 78292, 78293, 78297, 78298, 78287, 78288, 78291, 78294, 78295, 78296,
78299, 78304, 78305, 78306, 78301, 78302, 78300, 78303, 78307, 78308, 78309, 78310, 78311, 78312, 78313, 78314,
78315, 78316, 78317, 78318, 78336, 78337, 78338, 78328, 78329, 78330, 78331, 78332, 78333, 78334, 78335, 78339,
78354, 78355, 78356, 78357, 78358, 78359, 78361, 78362, 78351, 78352, 78353, 78360, 78363, 78364, 78319, 78320,
78321, 78322, 78323, 78324, 78325, 78326, 78327, 78345, 78346, 78340, 78341, 78342, 78343, 78344, 78347, 78348,
78349, 78350, 78365, 78366, 78367, 78372, 78373, 78368, 78369, 78370, 78371, 78374, 78375, 78376, 78377, 78385,
78386, 78378, 78379, 78380, 78381, 78382, 78383, 78384, 78387, 78388, 78389, 78390, 78391, 78392, 78393, 78394,
78395, 78396, 78397, 78398, 78399, 78400, 78401, 78402, 78409, 78410, 78403, 78404, 78405, 78406, 78407, 78408,
78411, 78414, 78415, 78412, 78413, 77908, 77909, 77904, 77905, 77906, 77907, 77910, 77911, 77912, 77913, 78423,
78424, 78425, 78426, 78427, 78428, 78429, 78416, 78417, 78421, 78422, 78418, 78419, 78420, 78430, 78431, 78432,
78433, 78434, 78435, 78436, 78445, 78446, 78437, 78438, 78439, 78440, 78441, 78442, 78443, 78444, 78447, 78448,
78452, 78453, 78454, 78455, 78459, 78460, 78449, 78450, 78451, 78456, 78457, 78458, 78469, 78470, 78471, 78472,
78473, 78461, 78462, 78465, 78466, 78463, 78464, 78467, 78468, 78474, 78475, 78476, 78487, 78488, 78489, 78490,
78477, 78478, 78479, 78480, 78481, 78482, 78483, 78484, 78485, 78486, 78491, 78492, 78494, 78495, 78493, 78496,
78497, 78498, 78499, 78500, 78501, 78502, 78503, 78504, 78505, 78506, 78507, 78508, 78509, 78510, 78514, 78515,
78516, 78512, 78513, 78511, 78517, 78518, 78519, 78520, 78521, 78522, 78523, 78524, 78530, 78531, 78525, 78526,
78527, 78528, 78529, 78532, 78533, 78534, 78535, 78536, 78537, 78538, 78539, 78540, 78541, 78542, 78543, 78544,
78546, 78547, 78551, 78552, 78545, 78548, 78549, 78550, 78553, 78554, 78555, 78560, 78561, 78562, 78565, 78566,
78556, 78557, 78558, 78559, 78563, 78564, 78567, 78568, 78575, 78576, 78577, 78569, 78570, 78571, 78572, 78573,
78574, 78578, 78579, 78580, 78586, 78587, 78581, 78582, 78583, 78584, 78585, 78588, 78589, 78590, 78591, 78592,
78593, 78594, 78595, 78596, 78597, 78598, 78601, 78602, 78606, 78607, 78608, 78609, 78610, 78611, 78599, 78600,
78603, 78604, 78605, 78613, 78614, 78619, 78620, 78612, 78615, 78616, 78617, 78618, 78621, 78622, 78623, 78636,
78637, 78638, 78639, 78634, 78635, 78640, 78641, 78642, 78624, 78625, 78626, 78627, 78628, 78629, 78630, 78631,
78632, 78633, 78648, 78649, 78650, 78643, 78644, 78645, 78646, 78647, 78651, 78652, 78653, 78667, 78668, 78674,
78675, 78664, 78665, 78666, 78669, 78670, 78671, 78672, 78673, 78678, 78679, 78676, 78677, 78680, 78681, 78682,
78683, 78684, 78685, 78686, 78687, 78688, 78689, 78654, 78655, 78656, 78657, 78658, 78659, 78660, 78661, 78662,
78663, 78706, 78707, 78708, 78690, 78691, 78692, 78693, 78694, 78695, 78696, 78697, 78698, 78699, 78700, 78701,
78702, 78703, 78704, 78705, 78709, 78710, 78712, 78713, 78714, 78715, 78716, 78717, 78718, 78711, 78719, 78720,
78721, 78722, 78723, 78724, 78725, 78726, 78727, 78728, 78729, 78730, 78731, 78732, 78733, 78734, 78735, 78736,
78737, 78738, 78741, 78742, 78747, 78748, 78749, 78750, 78739, 78740, 78743, 78744, 78745, 78746, 78751, 78752,
78753, 78754, 78756, 78757, 78761, 78762, 78755, 78758, 78759, 78760, 78763, 78764, 78765, 78766, 78769, 78770,
78776, 78777, 78767, 78768, 78771, 78772, 78773, 78774, 78775, 78778, 78779, 78783, 78784, 78787, 78788, 78789,
78790, 78780, 78781, 78782, 78785, 78786, 78791, 78796, 78797, 78792, 78793, 78794, 78795, 78798, 78802, 78803,
78804, 78806, 78807, 78809, 78810, 78799, 78800, 78801, 78805, 78808, 78811, 78812, 78813, 78814, 78815, 78816,
78817, 78818, 78819, 78821, 78822, 78823, 78824, 78825, 78826, 78827, 78828, 78829, 78830, 78831, 78832, 78820,
78833, 78834, 78835, 78836, 78842, 78843, 78844, 78845, 78846, 78847, 78848, 78849, 78850, 78851, 78852, 78853,
78854, 78855, 78856, 78857, 78858, 78859, 78860, 78837, 78838, 78839, 78840, 78841, 9167, 9191, 4999, 4998,
4997, 11653, 4995, 4994, 4993, 11649, 11704, 11707, 11709, 11708, 11706, 11710, 11705, 11688, 11691, 11693,
11692, 11690, 11694, 11689, 11664, 11655, 11661, 11660, 11667, 4895, 11670, 11669, 11668, 11658, 11736, 11739,
11741, 11740, 11738, 11742, 11737, 4879, 11720, 11723, 11725, 11724, 11722, 11726, 11721, 4783, 11712, 11715,
11717, 11716, 11714, 11718, 11713, 4679, 11728, 11731, 11733, 11732, 11730, 11734, 11729, 4743, 11657, 11656,
5007, 5006, 5005, 11665, 11666, 5003, 5002, 5001, 4996, 5000, 4992, 5004, 11652, 11680, 11683, 11685,
11684, 11682, 11686, 11681, 11651, 11663, 4935, 11654, 4615, 11662, 11648, 11650, 4815, 4847, 11696, 11699,
11701, 11700, 11698, 11702, 11697, 11659, 4960, 5009, 5016, 5012, 5015, 5017, 5013, 5010, 5011, 5014,
5008, 4959, 11072, 9178, 9950, 8507, 9971, 9189, 9880, 8277, 9884, 8280, 8283, 9970, 11792, 8281,
11821, 9905, 9981, 9179, 9972, 9881, 9965, 9966, 983902, 4345, 4346, 11545, 11549, 11548, 11546, 11542,
11522, 11552, 11556, 11554, 11557, 11553, 11547, 11551, 11529, 11541, 11540, 11534, 11536, 11544, 11537, 11526,
11535, 11527, 11538, 11530, 11525, 11521, 11531, 11550, 11523, 11520, 11524, 11528, 11533, 11539, 11532, 11543,
11555, 11304, 11265, 11276, 11271, 11268, 11293, 11287, 11306, 11267, 11275, 11305, 11303, 11307, 11273, 11274,
11310, 11278, 11279, 11281, 11289, 11282, 11290, 11291, 11308, 11294, 11298, 11284, 11300, 11301, 11285, 11309,
11292, 11266, 11269, 11296, 11295, 11297, 11302, 11299, 11272, 11270, 11277, 11283, 11280, 11288, 11286, 11264,
11352, 11313, 11324, 11319, 11316, 11341, 11335, 11354, 11315, 11323, 11353, 11351, 11355, 11321, 11322, 11358,
11326, 11327, 11329, 11337, 11330, 11338, 11339, 11356, 11342, 11346, 11332, 11348, 11349, 11333, 11357, 11340,
11314, 11317, 11344, 11343, 11345, 11350, 11347, 11320, 11318, 11325, 11331, 11328, 11336, 11334, 11312, 65860,
65863, 65878, 65866, 65873, 65859, 65861, 65868, 65875, 65862, 65870, 65864, 65871, 65867, 65874, 65857, 65869,
65876, 65856, 65858, 65865, 65877, 65872, 65879, 65903, 65885, 65904, 65907, 65908, 65900, 65883, 65886, 65896,
65882, 65890, 65880, 65891, 65906, 65902, 65897, 65899, 65893, 65884, 65892, 65881, 65905, 65898, 65894, 65895,
65887, 65901, 65888, 65889, 65927, 65926, 882, 1015, 1018, 886, 880, 1017, 1023, 1021, 1022, 975,
65915, 65928, 65920, 65919, 119325, 119331, 119332, 119333, 119334, 119335, 119336, 119337, 119326, 119338, 119339, 119340,
119341, 119342, 119343, 119344, 119345, 119346, 119347, 119348, 119349, 119327, 119350, 119351, 119352, 119353, 119354, 119355,
119356, 119328, 119357, 119358, 119359, 119360, 119361, 119329, 119330, 7466, 7464, 7462, 7465, 7463, 65923, 65921,
119365, 65925, 65909, 65910, 65916, 65924, 883, 1016, 1019, 887, 881, 893, 891, 892, 7527, 7530,
7529, 7528, 7526, 65918, 65912, 65929, 65917, 65911, 65914, 65922, 119297, 119315, 119316, 119317, 119318, 119319,
119300, 119320, 119321, 119322, 119323, 119324, 119296, 119305, 119306, 119307, 119308, 119309, 119310, 119311, 119312, 119313,
119314, 119298, 119299, 119301, 119302, 119303, 119304, 1020, 65930, 65913, 8370, 2801, 2786, 2787, 2700, 2785,
2561, 2641, 2677, 2563, 43382, 43383, 43377, 43376, 43375, 4443, 4444, 4445, 43379, 43378, 43380, 43386,
43371, 43374, 43364, 43367, 43370, 43365, 43372, 43373, 43366, 43369, 43368, 43384, 43388, 43381, 43385, 4446,
43362, 43363, 43361, 43360, 43387, 4442, 55288, 55287, 4604, 4602, 4605, 4603, 4606, 55261, 55265, 55266,
55262, 55263, 55244, 55243, 55284, 55283, 55290, 55291, 55271, 55268, 55267, 55273, 55272, 55269, 55258, 55257,
55260, 55259, 55254, 55256, 55253, 55275, 55278, 55280, 55279, 55281, 55282, 55274, 55289, 4607, 55255, 55277,
55276, 55245, 55246, 55270, 55264, 55251, 55250, 55247, 55248, 55249, 55252, 55286, 55285, 55237, 55238, 4515,
55227, 55226, 55225, 55228, 55229, 55230, 55232, 55231, 55234, 55235, 55233, 55236, 4518, 4519, 55216, 55217,
55222, 55221, 55218, 55219, 55220, 55223, 55224, 4517, 4516, 9874, 11096, 9955, 11095, 11097, 10071, 11093,
11094, 9947, 9980, 1442, 1466, 1479, 1478, 1477, 9937, 19966, 19958, 19922, 19967, 19924, 19946, 19923,
19909, 19947, 19956, 19944, 19943, 19906, 19962, 19935, 19939, 19920, 19916, 19948, 19917, 19937, 19931, 19929,
19925, 19911, 19964, 19928, 19945, 19934, 19930, 19918, 19942, 19950, 19941, 19949, 19938, 19914, 19936, 19927,
19952, 19965, 19912, 19926, 19915, 19954, 19910, 19932, 19904, 19953, 19933, 19940, 19905, 19951, 19959, 19960,
19955, 19957, 19961, 19913, 19907, 19921, 19908, 19963, 19919, 9964, 9889, 9897, 11043, 9749, 11794, 11802,
8372, 67675, 67679, 67676, 67673, 67674, 67672, 67678, 67677, 67648, 67663, 67651, 67650, 67665, 67662, 67668,
67654, 67652, 67655, 67659, 67666, 67669, 67656, 67657, 67653, 67667, 67649, 67658, 67660, 67661, 67664, 67671,
68448, 68451, 68450, 68464, 68462, 68465, 68454, 68452, 68455, 68459, 68460, 68466, 68456, 68457, 68453, 68449,
68458, 68461, 68463, 68472, 68479, 68478, 68477, 68473, 68474, 68476, 68475, 68416, 68431, 68419, 68418, 68433,
68430, 68436, 68422, 68420, 68423, 68427, 68434, 68437, 68424, 68425, 68421, 68435, 68417, 68426, 68428, 68429,
68432, 68440, 68447, 68446, 68445, 68441, 68442, 68444, 68443, 11800, 8276, 8292, 9892, 9976, 9979, 43453,
43454, 43455, 43457, 43421, 43422, 43426, 43427, 43398, 43397, 43399, 43407, 43408, 43409, 43412, 43402, 43403,
43418, 43416, 43428, 43423, 43431, 43432, 43413, 43414, 43410, 43411, 43429, 43430, 43401, 43435, 43436, 43441,
43439, 43440, 43424, 43425, 43419, 43420, 43415, 43417, 43396, 43405, 43442, 43437, 43433, 43438, 43434, 43404,
43406, 43400, 43458, 43466, 43467, 43459, 43465, 43461, 43464, 43468, 43463, 43460, 43462, 43486, 43487, 43471,
43456, 43469, 43393, 43443, 43394, 43395, 43392, 43448, 43449, 43444, 43450, 43445, 43446, 43447, 43452, 43451,
43480, 43477, 43476, 43481, 43473, 43479, 43478, 43475, 43474, 43472, 9909, 69819, 69820, 69823, 69825, 69824,
69786, 69787, 69785, 69793, 69792, 69777, 69789, 69782, 69794, 69784, 69783, 69791, 69790, 69804, 69805, 69806,
69798, 69797, 69779, 69778, 69776, 69775, 69781, 69780, 69774, 69773, 69796, 69795, 69788, 69801, 69763, 69764,
69770, 69772, 69765, 69766, 69767, 69768, 69807, 69802, 69799, 69803, 69800, 69769, 69771, 69760, 69818, 69817,
69762, 69761, 69822, 69808, 69814, 69816, 69809, 69810, 69811, 69812, 69813, 69815, 69821, 983042, 3260, 3313,
3314, 3261, 3298, 3299, 983944, 43283, 43295, 43299, 43301, 43275, 43274, 43286, 43285, 43279, 43278, 43294,
43282, 43277, 43281, 43284, 43289, 43297, 43288, 43276, 43292, 43287, 43290, 43296, 43293, 43291, 43280, 43298,
43300, 43310, 43311, 43308, 43309, 43307, 43303, 43305, 43304, 43302, 43306, 43272, 43269, 43268, 43273, 43265,
43271, 43270, 43267, 43266, 43264, 68163, 68160, 68162, 68161, 68113, 68146, 68112, 68126, 68121, 68131, 68147,
68123, 68122, 68128, 68127, 68125, 68124, 68130, 68129, 68141, 68142, 68143, 68135, 68134, 68118, 68117, 68115,
68114, 68133, 68132, 68145, 68119, 68139, 68136, 68138, 68140, 68137, 68144, 68096, 68165, 68164, 68167, 68166,
68179, 68178, 68183, 68176, 68182, 68184, 68181, 68180, 68177, 68152, 68153, 68109, 68154, 68111, 68110, 68099,
68101, 68097, 68102, 68098, 68108, 68159, 983909, 983911, 983908, 983910, 983904, 983906, 983903, 983905, 983907, 983912,
983917, 983922, 983924, 983926, 983925, 983919, 983921, 983914, 983916, 983918, 983920, 983913, 983915, 983936, 983930, 983932,
983933, 983934, 983927, 983929, 983931, 983928, 983923, 983935, 983941, 983938, 983939, 983940, 6636, 6652, 6639, 6655,
6637, 6653, 6638, 6654, 6635, 6651, 6634, 6650, 6133, 6136, 6137, 6134, 6135, 6130, 6131, 6132,
6129, 6128, 6624, 6632, 6648, 6633, 6649, 6631, 6647, 6630, 6646, 6629, 6645, 6626, 6642, 6640,
6627, 6643, 6628, 6644, 6625, 6641, 6109, 983937, 983943, 983942, 983044, 983043, 983046, 983045, 68413, 68415,
68412, 68414, 983552, 983578, 983580, 570, 42808, 42810, 11373, 42802, 42804, 42806, 42812, 42822, 579, 983560,
983562, 983586, 983588, 983554, 983556, 983558, 983582, 983584, 582, 42786, 42788, 42858, 577, 983040, 983564, 983592,
983594, 42873, 42875, 42877, 42882, 42884, 42886, 42860, 584, 983596, 42818, 11369, 42816, 42820, 11360, 42824,
11362, 983598, 573, 11374, 983600, 7930, 7932, 42826, 42828, 983568, 983570, 983572, 42830, 42834, 11363, 42832,
42836, 42838, 42840, 11364, 983602, 588, 42842, 42814, 42844, 983574, 11390, 586, 42891, 7838, 11375, 11376,
42878, 42880, 581, 574, 42852, 42854, 42794, 42792, 983576, 983608, 983610, 983604, 983606, 580, 42846, 42850,
42856, 42848, 11371, 11391, 42796, 42798, 571, 42862, 11367, 11381, 42790, 11378, 7934, 590, 43005, 43006,
43003, 43004, 43007, 7431, 7430, 7459, 7439, 7440, 7445, 7438, 7449, 42870, 7451, 11387, 7450, 7427,
7436, 7424, 7425, 7428, 7429, 42800, 7434, 7435, 7437, 7448, 42801, 7452, 7456, 7457, 7458, 7460,
7461, 7547, 7550, 983553, 983579, 983581, 7567, 11365, 42809, 42811, 7568, 42803, 42805, 42807, 42813, 7532,
7552, 42823, 7447, 7534, 7554, 42797, 42799, 572, 42863, 7569, 7533, 7553, 545, 568, 7839, 42865,
567, 983561, 983563, 983587, 983589, 983555, 983557, 983559, 983583, 983585, 7570, 11384, 583, 42787, 42789, 7578,
7563, 7576, 42859, 578, 7555, 983041, 11368, 11382, 42791, 983565, 983593, 983595, 983590, 983566, 983591, 7574,
42874, 42876, 7545, 42883, 42885, 42887, 7548, 42861, 983597, 585, 42819, 11370, 42817, 42821, 7556, 11361,
42825, 7557, 564, 983599, 7837, 7836, 42866, 7535, 7558, 983601, 7931, 7933, 42867, 7536, 7559, 565,
983567, 42868, 42827, 11386, 42829, 983569, 983571, 983573, 7571, 7575, 42831, 42835, 7549, 42833, 42837, 7537,
7560, 587, 42839, 42841, 569, 7539, 7538, 7561, 589, 983603, 42843, 8580, 42815, 7572, 42869, 42845,
983575, 7540, 575, 7562, 42892, 7573, 7441, 7442, 7443, 7455, 7454, 7453, 11366, 7541, 566, 7546,
42853, 42855, 42795, 686, 687, 7433, 42879, 7432, 7444, 11385, 7426, 7543, 42881, 42871, 7446, 11383,
42793, 983577, 983609, 983611, 983605, 983607, 7577, 7551, 7531, 42872, 42847, 11377, 7564, 11380, 42851, 42857,
42849, 11379, 7935, 591, 11372, 7542, 576, 7566, 7565, 8340, 8336, 8337, 7522, 11388, 8338, 7523,
7524, 7525, 8339, 11058, 11056, 11788, 11012, 11020, 9948, 11816, 11780, 11804, 11778, 10181, 11814, 11785,
11808, 11074, 11083, 11082, 11066, 11065, 11024, 11025, 11064, 11070, 11067, 11069, 11068, 11061, 11060, 11062,
11063, 11077, 11013, 4054, 4056, 7213, 7221, 7216, 7220, 7215, 7214, 7217, 7218, 7219, 7170, 7169,
7168, 7184, 7183, 7182, 7247, 7193, 7180, 7192, 7191, 7246, 7245, 7179, 7178, 7188, 7187, 7186,
7185, 7172, 7171, 7198, 7197, 7190, 7189, 7175, 7174, 7201, 7200, 7173, 7177, 7181, 7176, 7196,
7195, 7199, 7202, 7194, 7203, 7227, 7231, 7230, 7228, 7229, 7223, 7222, 7205, 7204, 7210, 7211,
7208, 7209, 7206, 7212, 7207, 7240, 7237, 7236, 7241, 7233, 7239, 7238, 7235, 7234, 7232, 6405,
6415, 6425, 6426, 6427, 6419, 6418, 6407, 6406, 6414, 6413, 6404, 6403, 6409, 6408, 6402, 6401,
6417, 6416, 6412, 6411, 6421, 6410, 6428, 6423, 6420, 6422, 6424, 6458, 6457, 6459, 6464, 6449,
6452, 6450, 6448, 6456, 6454, 6453, 6455, 6451, 6442, 6443, 6441, 6432, 6436, 6438, 6439, 6435,
6440, 6437, 6433, 6434, 6400, 6468, 6478, 6475, 6474, 6479, 6471, 6477, 6476, 6473, 6472, 6470,
6469, 13007, 65667, 65669, 65668, 65670, 65671, 65672, 65673, 65675, 65674, 65677, 65676, 65664, 65665, 65666,
65678, 65680, 65682, 65679, 65681, 65686, 65685, 65687, 65693, 65691, 65690, 65692, 65694, 65696, 65703, 65695,
65697, 65698, 65699, 65701, 65702, 65707, 65706, 65704, 65705, 65708, 65709, 65710, 65711, 65712, 65713, 65719,
65717, 65714, 65715, 65716, 65718, 65720, 65721, 65722, 65723, 65724, 65725, 65726, 65727, 65728, 65729, 65731,
65730, 65732, 65733, 65737, 65735, 65734, 65736, 65738, 65739, 65740, 65741, 65742, 65743, 65744, 65745, 65747,
65748, 65752, 65749, 65750, 65751, 65753, 65754, 65755, 65756, 65757, 65779, 65780, 65781, 65782, 65783, 65784,
65785, 65759, 65760, 65761, 65762, 65763, 65764, 65765, 65766, 65767, 65768, 65769, 65770, 65771, 65772, 65773,
65774, 65775, 65776, 65777, 65778, 65758, 65786, 65684, 65683, 65689, 65688, 65700, 65746, 65541, 65579, 65561,
65543, 65589, 65536, 65587, 65566, 65582, 65544, 65571, 65596, 65569, 65540, 65584, 65557, 65559, 65560, 65580,
65606, 65600, 65538, 65562, 65599, 65573, 65577, 65588, 65568, 65609, 65537, 65581, 65574, 65549, 65563, 65593,
65583, 65601, 65547, 65605, 65594, 65542, 65552, 65545, 65564, 65578, 65546, 65585, 65586, 65591, 65565, 65570,
65607, 65553, 65610, 65590, 65611, 65539, 65576, 65550, 65554, 65608, 65551, 65603, 65592, 65597, 65558, 65567,
65572, 65612, 65602, 65555, 65556, 65604, 65613, 65616, 65617, 65620, 65621, 65623, 65624, 65626, 65627, 65628,
65629, 65622, 65619, 65618, 65625, 42204, 42195, 42237, 42234, 42235, 42232, 42236, 42233, 42206, 42205, 42197,
42196, 42228, 42229, 42230, 42213, 42208, 42203, 42202, 42221, 42198, 42216, 42214, 42200, 42199, 42194, 42193,
42219, 42210, 42211, 42212, 42224, 42225, 42222, 42223, 42227, 42231, 42192, 42217, 42201, 42209, 42207, 42218,
42215, 42220, 42226, 42238, 42239, 8374, 11059, 10188, 66190, 66192, 66187, 66196, 66178, 66179, 66199, 66185,
66200, 66176, 66201, 66177, 66202, 66191, 66193, 66181, 66180, 66203, 66182, 66186, 66189, 66195, 66188, 66197,
66198, 66194, 66183, 66204, 66184, 67891, 67886, 67881, 67895, 67887, 67892, 67872, 67893, 67876, 67894, 67883,
67896, 67873, 67897, 67875, 67889, 67874, 67878, 67880, 67882, 67884, 67890, 67885, 67888, 67877, 67879, 67903,
127012, 127019, 127008, 126990, 126999, 126976, 127005, 126987, 126996, 127004, 126986, 126995, 126979, 127009, 126991, 127000,
127011, 127001, 126983, 126992, 126977, 127007, 126989, 126998, 127006, 126988, 126997, 127014, 127015, 127003, 126985, 126994,
127002, 126984, 126993, 126978, 126982, 127017, 126981, 126980, 127016, 127018, 127013, 127010, 3444, 3443, 3445, 3453,
3454, 3451, 3450, 3452, 3455, 3442, 3441, 3440, 3389, 3449, 3426, 3427, 3396, 9895, 9894, 9893,
9901, 120778, 120779, 120484, 120485, 10222, 10220, 10223, 10221, 120001, 9967, 9900, 9898, 9899, 44011, 43994,
43989, 43993, 43991, 43992, 43986, 43981, 43987, 43990, 43976, 43968, 43995, 43973, 43999, 43977, 44001, 43972,
43998, 43984, 43978, 43975, 44000, 43983, 44002, 43970, 43996, 43971, 43997, 43985, 43988, 43979, 43969, 43980,
43974, 43982, 44012, 44013, 44005, 44009, 44004, 44003, 44007, 44008, 44006, 44010, 44024, 44021, 44020, 44025,
44017, 44023, 44022, 44019, 44018, 44016, 9169, 9170, 9172, 9177, 9176, 9175, 9173, 9174, 9171, 7470,
7471, 7487, 7474, 7483, 7484, 7485, 7468, 7469, 7472, 7473, 7475, 7476, 7477, 7478, 7479, 7480,
7481, 7482, 7486, 7488, 7489, 11389, 7490, 42757, 42759, 42755, 42753, 42756, 42758, 42754, 42752, 7544,
42889, 42777, 42775, 42776, 42765, 42760, 42770, 983945, 42769, 42764, 42774, 762, 764, 42766, 42761, 42771,
751, 42768, 42763, 767, 753, 42773, 754, 755, 752, 42888, 42783, 759, 42778, 42767, 42762, 42772,
757, 758, 756, 42782, 42781, 760, 42780, 42779, 42890, 765, 7491, 7493, 7516, 7495, 7509, 7601,
7517, 7580, 7590, 7591, 7595, 7600, 7608, 7581, 7521, 7496, 7585, 7519, 7497, 7604, 7582, 7614,
7505, 7501, 7518, 7520, 7588, 7589, 7594, 7593, 7504, 7596, 7515, 7609, 7598, 7599, 7506, 7499,
7507, 7510, 7602, 7603, 7586, 7498, 7513, 7511, 7605, 7508, 7492, 7579, 7494, 7514, 7597, 7500,
7587, 7502, 7610, 7615, 7583, 7512, 7606, 7607, 7611, 7613, 7612, 7592, 7584, 7503, 42784, 42785,
761, 763, 766, 42864, 4348, 119552, 9866, 9867, 6314, 9968, 4158, 4156, 4157, 4155, 4192, 4191,
4190, 4226, 4208, 4207, 4206, 43625, 43624, 43626, 43621, 43627, 43618, 43617, 43630, 43629, 43620, 43619,
43623, 43622, 43631, 43616, 43635, 43628, 43633, 43634, 4188, 4189, 4186, 4187, 4136, 4218, 4220, 4214,
4213, 4221, 4224, 4223, 4216, 4219, 4222, 4215, 4225, 4217, 4130, 4193, 4198, 4197, 4238, 43642,
4159, 43636, 43637, 43638, 4250, 4251, 4235, 4236, 4237, 4231, 4232, 4233, 4234, 4201, 4202, 4203,
4204, 4205, 43643, 4239, 4154, 43641, 43639, 43640, 4255, 4254, 4248, 4245, 4244, 4249, 4241, 4247,
4246, 4243, 4242, 4240, 4195, 4196, 4209, 4212, 4210, 4211, 4147, 4148, 4194, 4228, 4229, 4230,
4227, 4199, 4200, 4139, 4252, 4253, 4149, 43632, 119081, 127319, 127327, 9471, 127353, 127355, 127356, 127359,
127372, 127373, 127371, 6595, 6594, 6599, 6598, 6597, 6596, 6593, 6566, 6530, 6567, 6531, 6570, 6537,
6532, 6544, 6543, 6536, 6542, 6549, 6548, 6562, 6561, 6554, 6560, 6556, 6550, 6528, 6555, 6538,
6568, 6533, 6569, 6534, 6571, 6540, 6535, 6547, 6546, 6539, 6545, 6552, 6551, 6565, 6564, 6557,
6563, 6559, 6553, 6529, 6558, 6541, 6622, 6623, 6618, 6600, 6601, 6577, 6587, 6582, 6586, 6578,
6592, 6583, 6584, 6590, 6589, 6579, 6585, 6591, 6580, 6588, 6576, 6581, 6616, 6613, 6612, 6617,
6609, 6615, 6614, 6611, 6610, 6608, 9906, 2035, 2031, 2032, 2033, 2030, 2027, 2028, 2029, 2034,
2040, 2008, 2001, 2012, 2025, 2024, 2026, 2006, 2002, 2019, 2016, 2018, 2023, 2010, 2009, 1997,
1995, 2000, 1999, 2007, 2003, 2013, 2020, 2014, 2015, 2017, 2004, 2011, 2005, 2021, 2022, 1994,
1996, 1998, 2037, 2042, 2036, 2039, 2038, 2041, 1992, 1989, 1988, 1993, 1985, 1991, 1990, 1987,
1986, 1984, 9940, 43057, 43056, 43059, 43060, 43058, 43061, 43062, 43065, 43063, 43064, 11008, 11016, 11009,
11017, 7265, 7264, 7266, 7267, 7261, 7260, 7262, 7259, 7280, 7282, 7281, 7279, 7271, 7270, 7272,
7269, 7258, 7263, 7278, 7268, 7283, 7273, 7284, 7285, 7287, 7286, 7276, 7274, 7275, 7277, 7290,
7288, 7289, 7295, 7294, 7292, 7293, 7291, 7256, 7253, 7252, 7257, 7249, 7255, 7254, 7251, 7250,
7248, 66516, 66514, 66515, 66517, 66513, 66464, 66504, 66505, 66506, 66482, 66510, 66511, 66477, 66508, 66509,
66478, 66479, 66469, 66470, 66467, 66468, 66484, 66485, 66492, 66493, 66473, 66474, 66490, 66491, 66480, 66475,
66476, 66507, 66471, 66497, 66498, 66495, 66486, 66487, 66488, 66472, 66483, 66499, 66494, 66481, 66489, 66496,
66465, 66466, 66512, 68209, 68210, 68213, 68211, 68217, 68212, 68214, 68192, 68194, 68205, 68203, 68193, 68196,
68206, 68207, 68202, 68198, 68219, 68220, 68201, 68215, 68218, 68216, 68197, 68199, 68200, 68195, 68204, 68208,
68222, 68221, 68223, 68608, 68619, 68627, 68623, 68634, 68640, 68644, 68668, 68670, 68677, 68632, 68669, 68671,
68617, 68625, 68621, 68638, 68643, 68660, 68666, 68675, 68630, 68648, 68653, 68646, 68650, 68673, 68641, 68658,
68642, 68655, 68628, 68611, 68657, 68662, 68614, 68615, 68636, 68656, 68664, 68679, 68680, 68609, 68610, 68645,
68654, 68620, 68624, 68635, 68678, 68633, 68672, 68652, 68618, 68626, 68622, 68639, 68661, 68667, 68676, 68631,
68613, 68649, 68647, 68651, 68674, 68659, 68629, 68612, 68663, 68616, 68637, 68665, 11819, 10180, 10179, 10183,
2869, 2929, 2914, 2915, 2884, 66710, 66688, 66715, 66699, 66694, 66698, 66703, 66693, 66697, 66696, 66705,
66707, 66702, 66706, 66711, 66716, 66713, 66717, 66689, 66701, 66700, 66708, 66691, 66695, 66690, 66692, 66709,
66704, 66712, 66714, 66728, 66725, 66724, 66729, 66721, 66727, 66726, 66723, 66722, 66720, 9885, 9908, 11801,
12830, 12829, 127248, 127249, 127250, 127251, 127252, 127253, 127254, 127255, 127256, 127257, 127258, 127259, 127260, 127261,
127262, 127263, 127264, 127265, 127266, 127267, 127268, 127269, 127270, 127271, 127272, 127273, 11791, 12880, 9977, 9854,
8524, 10178, 43101, 43117, 43120, 43076, 43123, 43077, 43115, 43090, 43082, 43094, 43098, 43099, 43089, 43088,
43114, 43113, 43081, 43080, 43119, 43118, 43075, 43116, 43079, 43083, 43109, 43074, 43073, 43072, 43085, 43084,
43092, 43093, 43104, 43110, 43086, 43108, 43100, 43078, 43097, 43087, 43106, 43096, 43091, 43107, 43095, 43102,
43105, 43103, 43127, 43126, 43124, 43121, 43111, 43112, 43122, 43125, 66033, 66023, 66017, 66010, 66027, 66003,
66018, 66028, 66012, 66022, 66020, 66045, 66004, 66019, 66031, 66040, 66041, 66007, 66006, 66025, 66026, 66038,
66016, 66013, 66014, 66036, 66034, 66001, 66000, 66037, 66029, 66011, 66024, 66042, 66015, 66021, 66043, 66002,
66032, 66008, 66044, 66005, 66039, 66009, 66035, 66030, 67840, 67855, 67860, 67854, 67857, 67861, 67848, 67850,
67845, 67859, 67846, 67844, 67847, 67841, 67858, 67852, 67853, 67849, 67842, 67851, 67856, 67843, 67862, 67865,
67864, 67866, 67867, 67863, 67871, 65040, 65043, 65045, 65041, 65042, 65095, 65047, 65096, 983049, 65048, 65044,
65049, 65046, 9935, 11783, 11782, 11787, 9926, 43344, 43343, 43346, 43345, 43330, 43320, 43333, 43323, 43331,
43314, 43332, 43317, 43319, 43321, 43316, 43313, 43329, 43322, 43312, 43326, 43318, 43325, 43324, 43315, 43328,
43327, 43334, 43359, 43347, 43338, 43340, 43337, 43342, 43341, 43335, 43339, 43336, 11073, 11079, 10184, 11793,
11822, 9952, 9953, 11777, 11776, 11817, 11781, 11805, 11789, 11779, 10182, 11815, 11786, 11809, 4053, 4055,
11080, 11084, 11075, 11076, 11022, 11023, 11078, 11824, 65947, 65942, 65945, 65940, 65943, 8583, 8582, 8584,
8581, 65938, 65944, 65936, 65939, 65941, 65937, 65946, 69223, 69220, 69219, 69224, 69216, 69222, 69221, 69218,
69217, 69243, 69244, 69245, 69246, 69241, 69232, 69238, 69229, 69237, 69228, 69240, 69231, 69239, 69230, 69242,
69233, 69236, 69227, 69226, 69235, 69225, 69234, 9973, 2102, 2053, 2049, 2050, 2063, 2055, 2052, 2058,
2059, 2060, 2067, 2062, 2068, 2069, 2065, 2056, 2048, 2051, 2057, 2066, 2061, 2054, 2064, 2073,
2070, 2071, 2075, 2093, 2072, 2074, 2084, 2088, 2097, 2110, 2098, 2100, 2108, 2099, 2103, 2105,
2096, 2101, 2109, 2106, 2104, 2107, 2082, 2079, 2076, 2089, 2086, 2091, 2081, 2078, 2085, 2092,
2083, 2080, 2077, 2090, 2087, 43188, 43215, 43214, 43224, 43221, 43220, 43225, 43217, 43223, 43222, 43219,
43218, 43216, 43167, 43166, 43172, 43171, 43187, 43181, 43158, 43168, 43163, 43173, 43165, 43164, 43170, 43169,
43146, 43147, 43144, 43145, 43182, 43183, 43184, 43185, 43177, 43176, 43160, 43159, 43157, 43156, 43162, 43161,
43155, 43154, 43175, 43174, 43138, 43139, 43150, 43153, 43140, 43141, 43142, 43143, 43148, 43149, 43151, 43152,
43186, 43178, 43180, 43179, 43204, 43137, 43136, 43196, 43197, 43194, 43195, 43189, 43200, 43203, 43190, 43191,
43192, 43193, 43198, 43199, 43201, 43202, 9878, 9914, 9913, 9916, 9752, 66684, 66680, 66665, 66664, 66682,
66673, 66679, 66669, 66650, 66647, 66651, 66685, 66672, 66663, 66683, 66652, 66659, 66649, 66686, 66674, 66662,
66642, 66661, 66656, 66677, 66676, 66678, 66668, 66666, 66681, 66640, 66670, 66646, 66645, 66644, 66654, 66641,
66667, 66658, 66648, 66687, 66660, 66671, 66643, 66675, 66655, 66653, 66657, 9961, 42611, 9917, 11010, 11018,
11011, 11019, 8375, 13279, 13278, 13175, 13176, 13177, 127376, 13005, 13006, 9974, 127488, 13004, 11027, 11029,
11028, 11026, 13311, 13178, 127529, 127530, 127512, 127533, 127508, 127520, 127516, 127534, 127506, 127511, 127509, 127532,
127524, 127505, 127525, 127518, 127517, 127504, 127527, 127537, 127528, 127535, 127519, 127515, 127526, 127513, 127514, 127521,
127522, 127510, 127536, 127523, 127531, 127306, 127307, 127310, 127507, 9919, 127281, 127293, 127295, 127298, 127302, 9949,
127308, 127309, 11820, 9882, 9877, 9188, 9925, 7073, 7074, 7075, 7087, 7070, 7086, 7050, 7053, 7057,
7060, 7048, 7049, 7043, 7046, 7064, 7054, 7059, 7062, 7052, 7072, 7055, 7068, 7065, 7061, 7051,
7067, 7058, 7063, 7069, 7071, 7066, 7056, 7044, 7047, 7045, 7082, 7041, 7042, 7040, 7080, 7081,
7076, 7079, 7077, 7078, 7096, 7093, 7092, 7097, 7089, 7095, 7094, 7091, 7090, 7088, 10185, 8275,
43027, 43026, 43031, 43030, 43040, 43038, 43025, 43024, 43029, 43028, 43036, 43035, 43021, 43020, 43018, 43017,
43023, 43022, 43016, 43015, 43034, 43033, 43042, 43039, 43037, 43032, 43041, 43008, 43012, 43009, 43013, 43011,
43048, 43049, 43050, 43051, 43019, 43010, 43014, 43047, 43043, 43046, 43044, 43045, 1837, 1838, 1839, 1870,
1869, 1871, 8527, 9975, 68411, 9924, 6499, 6508, 6509, 6507, 6501, 6502, 6482, 6498, 6512, 6513,
6514, 6515, 6516, 6497, 6483, 6487, 6486, 6496, 6480, 6490, 6489, 6503, 6506, 6505, 6504, 6492,
6494, 6488, 6491, 6495, 6484, 6493, 6481, 6485, 6500, 6745, 6746, 6743, 6747, 6742, 6741, 6748,
6749, 6750, 6783, 6792, 6789, 6788, 6793, 6785, 6791, 6790, 6787, 6786, 6784, 6808, 6805, 6804,
6809, 6801, 6807, 6806, 6803, 6802, 6800, 6740, 6726, 6727, 6728, 6696, 6695, 6713, 6712, 6707,
6706, 6689, 6690, 6688, 6702, 6714, 6729, 6720, 6699, 6697, 6717, 6715, 6709, 6708, 6693, 6692,
6691, 6704, 6716, 6732, 6698, 6719, 6723, 6739, 6730, 6724, 6694, 6700, 6710, 6721, 6705, 6701,
6722, 6733, 6734, 6735, 6736, 6738, 6711, 6703, 6718, 6725, 6737, 6731, 6820, 6828, 6775, 6776,
6777, 6780, 6824, 6825, 6819, 6772, 6744, 6823, 6779, 6822, 6778, 6826, 6827, 6818, 6752, 6773,
6774, 6816, 6817, 6821, 6829, 6753, 6755, 6767, 6769, 6754, 6763, 6771, 6764, 6768, 6765, 6756,
6770, 6761, 6762, 6760, 6759, 6757, 6758, 6766, 43653, 43651, 43649, 43661, 43659, 43679, 43677, 43671,
43669, 43657, 43665, 43673, 43675, 43667, 43681, 43655, 43693, 43689, 43683, 43687, 43663, 43691, 43685, 43695,
43652, 43650, 43648, 43660, 43658, 43678, 43676, 43670, 43668, 43656, 43664, 43672, 43674, 43666, 43680, 43654,
43692, 43688, 43682, 43686, 43662, 43690, 43684, 43694, 43703, 43696, 43743, 43739, 43742, 43741, 43740, 43712,
43713, 43714, 43711, 43707, 43697, 43710, 43709, 43708, 43700, 43699, 43705, 43706, 43698, 43704, 43701, 43702,
983612, 983635, 983624, 983627, 983626, 983619, 983617, 983629, 983613, 983615, 983618, 983616, 983623, 983628, 983633, 983631,
983632, 983614, 983634, 983630, 983621, 983620, 983625, 983622, 3063, 3059, 3062, 3046, 2998, 3066, 3065, 983889,
983890, 983897, 983900, 983891, 983892, 983893, 983894, 983895, 983896, 983898, 983899, 983636, 983643, 983646, 983637, 983638,
983639, 983640, 983641, 983642, 983644, 983645, 983790, 983797, 983800, 983791, 983792, 983793, 983794, 983795, 983796, 983798,
983799, 983801, 983808, 983811, 983802, 983803, 983804, 983805, 983806, 983807, 983809, 983810, 983768, 983775, 983778, 983769,
983770, 983771, 983772, 983773, 983774, 983776, 983777, 983823, 983830, 983833, 983824, 983825, 983826, 983827, 983828, 983829,
983831, 983832, 983691, 983698, 983701, 983692, 983693, 983694, 983695, 983696, 983697, 983699, 983700, 983647, 983654, 983657,
983648, 983649, 983650, 983651, 983652, 983653, 983655, 983656, 983669, 983676, 983679, 983670, 983671, 983672, 983673, 983674,
983675, 983677, 983678, 983713, 983720, 983723, 983714, 983715, 983716, 983717, 983718, 983719, 983721, 983722, 983812, 983819,
983822, 983813, 983814, 983815, 983816, 983817, 983818, 983820, 983821, 983757, 983764, 983767, 983758, 983759, 983760, 983761,
983762, 983763, 983765, 983766, 983845, 983852, 983855, 983846, 983847, 983848, 983849, 983850, 983851, 983853, 983854, 983901,
983856, 983863, 983866, 983857, 983858, 983859, 983860, 983861, 983862, 983864, 983865, 983867, 983874, 983877, 983868, 983869,
983870, 983871, 983872, 983873, 983875, 983876, 983680, 983687, 983690, 983681, 983682, 983683, 983684, 983685, 983686, 983688,
983689, 983702, 983709, 983712, 983703, 983704, 983705, 983706, 983707, 983708, 983710, 983711, 983658, 983665, 983668, 983659,
983660, 983661, 983662, 983663, 983664, 983666, 983667, 983878, 983885, 983888, 983879, 983880, 983881, 983882, 983883, 983884,
983886, 983887, 983834, 983841, 983844, 983835, 983836, 983837, 983838, 983839, 983840, 983842, 983843, 983735, 983742, 983745,
983736, 983737, 983738, 983739, 983740, 983741, 983743, 983744, 983724, 983731, 983734, 983725, 983726, 983727, 983728, 983729,
983730, 983732, 983733, 983779, 983786, 983789, 983780, 983781, 983782, 983783, 983784, 983785, 983787, 983788, 983746, 983753,
983756, 983747, 983748, 983749, 983750, 983751, 983752, 983754, 983755, 3061, 3064, 3060, 3024, 3195, 3198, 3194,
3197, 3193, 3196, 3192, 3161, 3160, 3133, 3199, 3170, 3171, 8376, 9978, 119617, 119564, 119577, 119633,
119561, 119587, 119566, 119613, 119590, 119631, 119634, 119630, 119573, 119563, 119582, 119608, 119585, 119558, 119624, 119586,
119623, 119567, 119636, 119612, 119625, 119568, 119584, 119619, 119618, 119600, 119583, 119603, 119610, 119626, 119580, 119611,
119576, 119638, 119559, 119595, 119632, 119606, 119592, 119615, 119599, 119602, 119614, 119629, 119574, 119569, 119570, 119622,
119581, 119562, 119591, 119637, 119597, 119589, 119609, 119560, 119616, 119565, 119635, 119604, 119588, 119571, 119594, 119578,
119596, 119579, 119598, 119572, 119605, 119627, 119621, 119628, 119601, 119593, 119575, 119620, 119607, 10176, 8278, 9886,
9887, 11057, 9928, 3947, 3948, 983047, 4048, 4049, 4052, 4051, 4050, 4046, 11608, 11595, 11585, 11573,
11620, 11607, 11600, 11582, 11590, 11596, 11601, 11586, 11592, 11568, 11575, 11577, 11578, 11576, 11571, 11606,
11572, 11581, 11589, 11583, 11569, 11570, 11584, 11587, 11604, 11605, 11609, 11611, 11610, 11612, 11613, 11615,
11619, 11594, 11621, 11614, 11588, 11580, 11574, 11597, 11598, 11599, 11602, 11591, 11616, 11617, 11618, 11579,
11593, 11603, 11631, 11081, 11806, 11807, 11803, 68410, 11810, 11811, 9180, 9184, 9182, 127553, 127554, 127555,
127559, 127557, 127560, 127552, 127556, 127558, 127274, 8285, 9930, 9929, 8526, 11818, 8282, 983048, 66432, 66451,
66454, 66433, 66436, 66447, 66434, 66457, 66437, 66440, 66443, 66435, 66445, 66446, 66448, 66455, 66450, 66453,
66444, 66461, 66452, 66456, 66441, 66458, 66442, 66439, 66449, 66438, 66459, 66460, 66463, 9969, 9748, 11797,
11014, 11021, 9903, 42509, 42536, 42533, 42532, 42537, 42529, 42535, 42534, 42531, 42530, 42528, 42510, 42511,
42486, 42257, 42446, 42370, 42333, 42294, 42407, 42485, 42256, 42445, 42369, 42332, 42293, 42406, 42489, 42260,
42449, 42373, 42336, 42297, 42410, 42473, 42246, 42434, 42359, 42321, 42283, 42396, 42474, 42247, 42435, 42360,
42322, 42284, 42397, 42492, 42263, 42452, 42376, 42339, 42300, 42413, 42491, 42262, 42451, 42375, 42338, 42299,
42412, 42484, 42255, 42444, 42368, 42331, 42292, 42405, 42483, 42254, 42443, 42367, 42330, 42291, 42404, 42494,
42265, 42454, 42378, 42341, 42302, 42415, 42493, 42264, 42453, 42377, 42340, 42301, 42414, 42439, 42440, 42364,
42479, 42251, 42480, 42327, 42288, 42401, 42502, 42272, 42503, 42461, 42385, 42349, 42309, 42422, 42429, 42430,
42355, 42468, 42242, 42469, 42316, 42317, 42278, 42279, 42391, 42392, 42476, 42249, 42477, 42437, 42362, 42324,
42325, 42286, 42399, 42499, 42270, 42459, 42383, 42346, 42347, 42307, 42420, 42487, 42508, 42258, 42447, 42371,
42334, 42295, 42408, 42475, 42248, 42436, 42361, 42323, 42285, 42398, 42478, 42250, 42438, 42363, 42326, 42287,
42400, 42504, 42273, 42462, 42386, 42350, 42310, 42423, 42450, 42514, 42539, 42512, 42513, 42538, 42374, 42490,
42261, 42337, 42298, 42411, 42507, 42500, 42271, 42501, 42460, 42384, 42348, 42308, 42421, 42315, 42467, 42428,
42497, 42268, 42457, 42381, 42344, 42305, 42418, 42506, 42275, 42464, 42388, 42352, 42312, 42425, 42505, 42274,
42463, 42387, 42351, 42311, 42424, 42495, 42266, 42455, 42379, 42342, 42303, 42416, 42481, 42252, 42441, 42365,
42328, 42289, 42402, 42496, 42267, 42456, 42380, 42343, 42304, 42417, 42472, 42245, 42433, 42358, 42320, 42282,
42395, 42488, 42259, 42448, 42372, 42335, 42296, 42409, 42482, 42253, 42442, 42366, 42329, 42290, 42403, 42498,
42269, 42458, 42382, 42345, 42306, 42419, 42470, 42243, 42244, 42471, 42431, 42356, 42357, 42432, 42318, 42319,
42280, 42281, 42393, 42394, 42465, 42240, 42241, 42466, 42426, 42353, 42354, 42427, 42313, 42314, 42276, 42277,
42389, 42390, 42519, 42526, 42523, 42522, 42515, 42520, 42527, 42516, 42524, 42518, 42521, 42517, 42525, 917843,
917844, 917845, 917846, 917847, 917848, 917849, 917850, 917851, 917852, 917853, 917854, 917855, 917856, 917857, 917858, 917859,
917860, 917861, 917862, 917863, 917864, 917865, 917866, 917867, 917868, 917869, 917870, 917871, 917872, 917873, 917874, 917875,
917876, 917877, 917878, 917879, 917880, 917881, 917882, 917883, 917884, 917885, 917886, 917887, 917888, 917889, 917890, 917891,
917892, 917893, 917894, 917895, 917896, 917897, 917898, 917899, 917900, 917901, 917902, 917903, 917904, 917905, 917906, 917907,
917908, 917909, 917910, 917911, 917912, 917760, 917913, 917914, 917915, 917916, 917917, 917918, 917919, 917920, 917921, 917922,
917761, 917923, 917924, 917925, 917926, 917927, 917928, 917929, 917930, 917931, 917932, 917762, 917933, 917934, 917935, 917936,
917937, 917938, 917939, 917940, 917941, 917942, 917773, 917774, 917775, 917776, 917777, 917778, 917779, 917780, 917781, 917782,
917783, 917784, 917785, 917786, 917787, 917788, 917789, 917790, 917791, 917792, 917793, 917794, 917795, 917796, 917797, 917798,
917799, 917800, 917801, 917802, 917803, 917804, 917805, 917806, 917807, 917808, 917809, 917810, 917811, 917812, 917813, 917814,
917815, 917816, 917817, 917818, 917819, 917820, 917821, 917822, 917823, 917824, 917825, 917826, 917827, 917828, 917829, 917830,
917831, 917832, 917833, 917834, 917835, 917836, 917837, 917838, 917839, 917840, 917841, 917842, 917763, 917943, 917944, 917945,
917946, 917947, 917948, 917949, 917950, 917951, 917952, 917764, 917953, 917954, 917955, 917956, 917957, 917958, 917959, 917960,
917961, 917962, 917765, 917963, 917964, 917965, 917966, 917967, 917968, 917969, 917970, 917971, 917972, 917766, 917973, 917974,
917975, 917976, 917977, 917978, 917979, 917980, 917981, 917982, 917767, 917983, 917984, 917985, 917986, 917987, 917988, 917989,
917990, 917991, 917992, 917768, 917993, 917994, 917995, 917996, 917997, 917998, 917999, 917769, 917770, 917771, 917772, 7401,
7402, 7409, 7403, 7404, 7410, 7379, 7398, 7396, 7408, 7406, 7407, 7405, 7397, 7400, 7395, 7399,
7394, 7380, 7386, 7389, 7376, 7388, 7378, 7377, 7387, 7390, 7391, 7384, 7381, 7382, 7383, 7385,
7393, 7392, 9910, 10186, 8286, 9168, 9896, 11823, 8528, 8530, 8529, 8585, 9915, 9888, 11071, 9855,
9921, 9920, 9931, 9872, 9983, 11041, 11053, 9945, 11036, 11046, 11048, 11088, 11092, 11040, 11051, 11090,
9186, 10177, 9943, 11055, 11038, 11825,
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
4866, 4879, 4926, 4816, 4813, 4900, 4645, 4742, 4807, 4690, 4723, 4914, 4966, 4668, 4835, 4654,
4733, 4722, 4664, 4828, 4680, 4857, 4715, 4897, 4709, 4904, 4749, 4963,
]
__charcode_to_pos_564 = _all_ushort(__charcode_to_pos_564)
def _charcode_to_pos_564(index): return intmask(__charcode_to_pos_564[index])
# estimated 0.05 KiB
__charcode_to_pos_751 = [
5664, 5672, 5668, 5670, 5671, 5682, 5680, 5681, 5675, 5685, 5760, 5659, 5761, 5660, 5689, 5762,
5667,
]
__charcode_to_pos_751 = _all_ushort(__charcode_to_pos_751)
def _charcode_to_pos_751(index): return intmask(__charcode_to_pos_751[index])
# estimated 0.05 KiB
__charcode_to_pos_848 = [
979, 969, 988, 993, 967, 980, 978, 982, 933, 870, 938, 989, 935, 934, 936, 937,
]
__charcode_to_pos_848 = _all_ushort(__charcode_to_pos_848)
def _charcode_to_pos_848(index): return intmask(__charcode_to_pos_848[index])
# estimated 0.04 KiB
__charcode_to_pos_880 = [
3850, 3914, 3846, 3910, -1, -1, 3849, 3913, -1, -1, -1, 3916, 3917, 3915,
]
__charcode_to_pos_880 = _all_short(__charcode_to_pos_880)
def _charcode_to_pos_880(index): return intmask(__charcode_to_pos_880[index])
# estimated 0.03 KiB
__charcode_to_pos_1015 = [
3847, 3911, 3851, 3848, 3912, 3959, 3853, 3854, 3852,
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
2205, 2259, 2188, 2241, 2221, 2275, 2206, 2260, 2217, 2271, 2222, 2276, 2223, 2277, 2175, 2228,
2187, 2240, 2189, 2242, 2202, 2255,
]
__charcode_to_pos_1296 = _all_ushort(__charcode_to_pos_1296)
def _charcode_to_pos_1296(index): return intmask(__charcode_to_pos_1296[index])
# estimated 0.08 KiB
__charcode_to_pos_1536 = [
143, 124, 60, 125, -1, -1, 145, 146, 119, 147, 148, 205, -1, 141, 140, 127,
123, 126, 121, 122, 128, 129, 130, 131, 134, 133, 132, -1, -1, -1, 139,
]
__charcode_to_pos_1536 = _all_short(__charcode_to_pos_1536)
def _charcode_to_pos_1536(index): return intmask(__charcode_to_pos_1536[index])
__charcode_to_pos_1622 = (
'\x87x\x90\x8e\x89\x88\x8av;'
)
def _charcode_to_pos_1622(index): return ord(__charcode_to_pos_1622[index])
# estimated 0.12 KiB
__charcode_to_pos_1869 = [
6976, 6975, 6977, 72, 75, 70, 71, 73, 74, 76, 93, 92, 79, 77, 105, 112,
62, 63, 61, 87, 86, 99, 96, 95, 115, 116, 103, 101, 102, 114, 107, 108,
111, 91, 89, 110, 104, 90, 65, 64, 81, 80, 82, 67, 66, 69, 68, 88,
113, 109, 100,
]
__charcode_to_pos_1869 = _all_ushort(__charcode_to_pos_1869)
def _charcode_to_pos_1869(index): return intmask(__charcode_to_pos_1869[index])
# estimated 0.26 KiB
__charcode_to_pos_1984 = [
6033, 6028, 6032, 6031, 6026, 6025, 6030, 6029, 6024, 6027, 6015, 6000, 6016, 5999, 6017, 6002,
6001, 5986, 5992, 6004, 6010, 6012, 5991, 6003, 5985, 5998, 5997, 6011, 5987, 6005, 6007, 6008,
5994, 6009, 5995, 5993, 6006, 6013, 6014, 5996, 5989, 5988, 5990, 5980, 5981, 5982, 5979, 5976,
5977, 5978, 5983, 5975, 6020, 6018, 6022, 6021, 5984, 6023, 6019, -1, -1, -1, -1, -1,
6616, 6602, 6603, 6617, 6606, 6601, 6621, 6605, 6615, 6618, 6607, 6608, 6609, 6620, 6611, 6604,
6622, 6614, 6619, 6610, 6612, 6613, 6624, 6625, 6628, 6623, 6629, 6626, 6648, 6658, 6653, 6647,
6657, 6652, 6646, 6656, 6630, 6654, 6650, 6660, 6631, 6649, 6659, 6651, 6655, 6627, -1, -1,
6640, 6632, 6634, 6637, 6635, 6641, 6600, 6638, 6644, 6639, 6643, 6645, 6636, 6642, 6633,
]
__charcode_to_pos_1984 = _all_short(__charcode_to_pos_1984)
def _charcode_to_pos_1984(index): return intmask(__charcode_to_pos_1984[index])
# estimated 0.03 KiB
__charcode_to_pos_2382 = [
2301, -1, -1, -1, -1, -1, -1, 2300,
]
__charcode_to_pos_2382 = _all_short(__charcode_to_pos_2382)
def _charcode_to_pos_2382(index): return intmask(__charcode_to_pos_2382[index])
# estimated 0.04 KiB
__charcode_to_pos_2417 = [
2299, 2288, -1, -1, -1, -1, -1, -1, 2290, 2286, 2283, 2284, 2282, 2289, 2285,
]
__charcode_to_pos_2417 = _all_short(__charcode_to_pos_2417)
def _charcode_to_pos_2417(index): return intmask(__charcode_to_pos_2417[index])
# estimated 0.03 KiB
__charcode_to_pos_2555 = [
422, -1, -1, -1, -1, -1, 3968, -1, 3971,
]
__charcode_to_pos_2555 = _all_short(__charcode_to_pos_2555)
def _charcode_to_pos_2555(index): return intmask(__charcode_to_pos_2555[index])
# estimated 0.03 KiB
__charcode_to_pos_3059 = [
7241, 7515, 7513, 7242, 7240, 7514, 7246, 7245,
]
__charcode_to_pos_3059 = _all_ushort(__charcode_to_pos_3059)
def _charcode_to_pos_3059(index): return intmask(__charcode_to_pos_3059[index])
# estimated 0.03 KiB
__charcode_to_pos_3192 = [
7523, 7521, 7519, 7517, 7522, 7520, 7518, 7527,
]
__charcode_to_pos_3192 = _all_ushort(__charcode_to_pos_3192)
def _charcode_to_pos_3192(index): return intmask(__charcode_to_pos_3192[index])
# estimated 0.03 KiB
__charcode_to_pos_3389 = [
5528, -1, -1, -1, -1, -1, -1, 5532,
]
__charcode_to_pos_3389 = _all_short(__charcode_to_pos_3389)
def _charcode_to_pos_3389(index): return intmask(__charcode_to_pos_3389[index])
# estimated 0.05 KiB
__charcode_to_pos_3440 = [
5527, 5526, 5525, 5517, 5516, 5518, -1, -1, -1, 5529, 5522, 5521, 5523, 5519, 5520, 5524,
]
__charcode_to_pos_3440 = _all_short(__charcode_to_pos_3440)
def _charcode_to_pos_3440(index): return intmask(__charcode_to_pos_3440[index])
# estimated 0.04 KiB
__charcode_to_pos_4046 = [
7627, -1, 7622, 7623, 7626, 7625, 7624, 6542, 5011, 6543, 5012,
]
__charcode_to_pos_4046 = _all_short(__charcode_to_pos_4046)
def _charcode_to_pos_4046(index): return intmask(__charcode_to_pos_4046[index])
# estimated 0.04 KiB
__charcode_to_pos_4130 = [
5818, -1, -1, -1, -1, -1, 5804, -1, -1, 5875,
]
__charcode_to_pos_4130 = _all_short(__charcode_to_pos_4130)
def _charcode_to_pos_4130(index): return intmask(__charcode_to_pos_4130[index])
# estimated 0.04 KiB
__charcode_to_pos_4147 = [
5866, 5867, 5878, -1, -1, -1, -1, 5844, 5773, 5771, 5772, 5770, 5824,
]
__charcode_to_pos_4147 = _all_short(__charcode_to_pos_4147)
def _charcode_to_pos_4147(index): return intmask(__charcode_to_pos_4147[index])
# estimated 0.15 KiB
__charcode_to_pos_4186 = [
5802, 5803, 5800, 5801, 5776, 5775, 5774, 5819, 5868, 5860, 5861, 5821, 5820, 5873, 5874, 5837,
5838, 5839, 5840, 5841, 5780, 5779, 5778, 5862, 5864, 5865, 5863, 5808, 5807, 5815, 5812, 5817,
5805, 5813, 5806, 5809, 5814, 5811, 5810, 5816, 5777, 5872, 5869, 5870, 5871, 5833, 5834, 5835,
5836, 5830, 5831, 5832, 5822, 5843, 5859, 5854, 5858, 5857, 5852, 5851, 5856, 5855, 5850, 5853,
5828, 5829, 5876, 5877, 5849, 5848,
]
__charcode_to_pos_4186 = _all_ushort(__charcode_to_pos_4186)
def _charcode_to_pos_4186(index): return intmask(__charcode_to_pos_4186[index])
# estimated 0.07 KiB
__charcode_to_pos_4992 = [
3594, 3524, 3523, 3522, 3592, 3520, 3519, 3518, 3593, 3591, 3590, 3589, 3595, 3586, 3585, 3584,
3632, 3623, 3629, 3630, 3625, 3628, 3631, 3626, 3624, 3627,
]
__charcode_to_pos_4992 = _all_ushort(__charcode_to_pos_4992)
def _charcode_to_pos_4992(index): return intmask(__charcode_to_pos_4992[index])
# estimated 0.03 KiB
__charcode_to_pos_5751 = [
554, 550, 551, 552, 553, 548, 549, 555, 485,
]
__charcode_to_pos_5751 = _all_ushort(__charcode_to_pos_5751)
def _charcode_to_pos_5751(index): return intmask(__charcode_to_pos_5751[index])
# estimated 0.04 KiB
__charcode_to_pos_6128 = [
4609, 4608, 4605, 4606, 4607, 4600, 4603, 4604, 4601, 4602,
]
__charcode_to_pos_6128 = _all_ushort(__charcode_to_pos_6128)
def _charcode_to_pos_6128(index): return intmask(__charcode_to_pos_6128[index])
# estimated 0.16 KiB
__charcode_to_pos_6314 = [
5768, -1, -1, -1, -1, -1, 516, 484, 483, 556, 536, 535, 534, 544, 497, 496,
562, 503, 502, 561, 533, 525, 532, 531, 530, 559, 558, 524, 498, 505, 499, 506,
500, 507, 501, 508, 521, 517, 518, 519, 520, 522, 514, 515, 512, 511, 513, 504,
509, 510, 557, 547, 494, 495, 523, 545, 546, 543, 542, 541, 539, 540, 538, 537,
527, 526, 529, 491, 489, 492, 490, 528, 493, 486, 487, 488,
]
__charcode_to_pos_6314 = _all_short(__charcode_to_pos_6314)
def _charcode_to_pos_6314(index): return intmask(__charcode_to_pos_6314[index])
# estimated 0.24 KiB
__charcode_to_pos_6400 = [
5140, 5103, 5102, 5099, 5098, 5087, 5095, 5094, 5101, 5100, 5109, 5107, 5106, 5097, 5096, 5088,
5105, 5104, 5093, 5092, 5112, 5108, 5113, 5111, 5114, 5089, 5090, 5091, 5110, -1, -1, -1,
5131, 5138, 5139, 5135, 5132, 5137, 5133, 5134, 5136, 5130, 5128, 5129, -1, -1, -1, -1,
5122, 5119, 5121, 5127, 5120, 5125, 5124, 5126, 5123, 5116, 5115, 5117, -1, -1, -1, -1,
5118, -1, -1, -1, 5141, 5152, 5151, 5146, 5150, 5149, 5144, 5143, 5148, 5147, 5142, 5145,
7000, 7014, 6988, 6996, 7012, 7015, 6998, 6997, 7009, 7002, 7001, 7010, 7007, 7013, 7008, 7011,
6999, 6995, 6989, 6982, 7016, 6986, 6987, 7003, 7006, 7005, 7004, 6985, 6983, 6984, -1, -1,
6990, 6991, 6992, 6993, 6994,
]
__charcode_to_pos_6400 = _all_short(__charcode_to_pos_6400)
def _charcode_to_pos_6400(index): return intmask(__charcode_to_pos_6400[index])
# estimated 0.61 KiB
__charcode_to_pos_6528 = [
5917, 5939, 5899, 5901, 5904, 5921, 5923, 5926, 5907, 5903, 5919, 5929, 5925, 5941, 5908, 5906,
5905, 5930, 5928, 5927, 5910, 5909, 5916, 5932, 5931, 5938, 5913, 5918, 5915, 5935, 5940, 5937,
5914, 5912, 5911, 5936, 5934, 5933, 5898, 5900, 5920, 5922, 5902, 5924, -1, -1, -1, -1,
5962, 5947, 5951, 5957, 5960, 5963, 5949, 5953, 5954, 5958, 5950, 5948, 5961, 5956, 5955, 5959,
5952, 5897, 5892, 5891, 5896, 5895, 5894, 5893, 5945, 5946, -1, -1, -1, -1, -1, -1,
5973, 5968, 5972, 5971, 5966, 5965, 5970, 5969, 5964, 5967, 5944, -1, -1, -1, 5942, 5943,
4610, 4628, 4621, 4624, 4626, 4619, 4617, 4615, 4611, 4613, 4598, 4596, 4588, 4592, 4594, 4590,
4623, 4629, 4622, 4625, 4627, 4620, 4618, 4616, 4612, 4614, 4599, 4597, 4589, 4593, 4595, 4591,
466, 463, 455, 454, 468, 460, 453, 452, 471, 462, 459, 458, 461, 465, 457, 456,
473, 469, 467, 472, 470, 474, 464, 478, 480, 477, 479, 476, -1, -1, 475, 481,
7059, 7057, 7058, 7072, 7071, 7070, 7082, 7052, 7051, 7065, 7076, 7064, 7083, 7087, 7060, 7095,
7073, 7086, 7056, 7055, 7069, 7068, 7084, 7094, 7054, 7053, 7061, 7067, 7074, 7066, 7096, 7077,
7063, 7085, 7088, 7078, 7081, 7097, 7048, 7049, 7050, 7062, 7080, 7099, 7075, 7089, 7090, 7091,
7092, 7098, 7093, 7079, 7047, 7022, 7021, 7019, 7110, 7017, 7018, 7020, 7023, 7024, 7025, -1,
7118, 7125, 7129, 7126, 7135, 7141, 7142, 7140, 7139, 7137, 7138, 7130, 7132, 7134, 7143, 7127,
7133, 7128, 7136, 7131, 7109, 7119, 7120, 7102, 7103, 7104, 7114, 7112, 7105, -1, -1, 7026,
7036, 7031, 7035, 7034, 7029, 7028, 7033, 7032, 7027, 7030, -1, -1, -1, -1, -1, -1,
7046, 7041, 7045, 7044, 7039, 7038, 7043, 7042, 7037, 7040, -1, -1, -1, -1, -1, -1,
7121, 7122, 7117, 7108, 7100, 7123, 7113, 7111, 7106, 7107, 7115, 7116, 7101, 7124,
]
__charcode_to_pos_6528 = _all_short(__charcode_to_pos_6528)
def _charcode_to_pos_6528(index): return intmask(__charcode_to_pos_6528[index])
# estimated 0.38 KiB
__charcode_to_pos_6912 = [
300, 301, 302, 299, 298, 213, 214, 229, 230, 233, 234, 251, 252, 242, 243, 226,
216, 231, 232, 237, 239, 227, 228, 246, 219, 220, 235, 236, 247, 259, 258, 223,
222, 245, 256, 257, 221, 224, 244, 248, 249, 217, 218, 264, 266, 250, 241, 265,
254, 255, 253, 263, 303, 314, 317, 318, 308, 309, 306, 307, 304, 305, 310, 311,
313, 312, 315, 316, 319, 238, 240, 260, 225, 261, 262, 215, -1, -1, -1, -1,
330, 325, 329, 328, 323, 322, 327, 326, 321, 324, 297, 295, 320, 210, 212, 211,
296, 284, 282, 285, 276, 277, 283, 279, 281, 280, 278, 273, 272, 269, 267, 271,
270, 268, 275, 274, 294, 293, 292, 291, 286, 288, 289, 290, 287, -1, -1, -1,
6909, 6907, 6908, 6883, 6903, 6905, 6884, 6904, 6881, 6882, 6877, 6895, 6889, 6878, 6886, 6891,
6902, 6879, 6897, 6887, 6880, 6894, 6888, 6898, 6885, 6893, 6901, 6896, 6892, 6899, 6875, 6900,
6890, 6871, 6872, 6873, 6912, 6914, 6915, 6913, 6910, 6911, 6906, -1, -1, -1, 6876, 6874,
6925, 6920, 6924, 6923, 6918, 6917, 6922, 6921, 6916, 6919,
]
__charcode_to_pos_6912 = _all_short(__charcode_to_pos_6912)
def _charcode_to_pos_6912(index): return intmask(__charcode_to_pos_6912[index])
# estimated 0.27 KiB
__charcode_to_pos_7168 = [
5024, 5023, 5022, 5042, 5041, 5051, 5048, 5047, 5054, 5052, 5036, 5035, 5030, 5053, 5027, 5026,
5025, 5040, 5039, 5038, 5037, 5046, 5045, 5032, 5031, 5029, 5059, 5056, 5055, 5044, 5043, 5057,
5050, 5049, 5058, 5060, 5069, 5068, 5074, 5076, 5072, 5073, 5070, 5071, 5075, 5013, 5018, 5017,
5015, 5019, 5020, 5021, 5016, 5014, 5067, 5066, -1, -1, -1, 5061, 5064, 5065, 5063, 5062,
5086, 5081, 5085, 5084, 5079, 5078, 5083, 5082, 5077, 5080, -1, -1, -1, 5034, 5033, 5028,
6096, 6091, 6095, 6094, 6089, 6088, 6093, 6092, 6087, 6090, 6065, 6056, 6054, 6053, 6055, 6066,
6050, 6049, 6051, 6052, 6068, 6064, 6062, 6061, 6063, 6070, 6076, 6077, 6075, 6078, 6067, 6060,
6057, 6059, 6058, 6069, 6071, 6072, 6074, 6073, 6080, 6081, 6079, 6086, 6084, 6085, 6083, 6082,
]
__charcode_to_pos_7168 = _all_short(__charcode_to_pos_7168)
def _charcode_to_pos_7168(index): return intmask(__charcode_to_pos_7168[index])
# estimated 0.08 KiB
__charcode_to_pos_7376 = [
8308, 8311, 8310, 8293, 8305, 8316, 8317, 8318, 8315, 8319, 8306, 8312, 8309, 8307, 8313, 8314,
8321, 8320, 8304, 8302, 8295, 8300, 8294, 8303, 8301, 8287, 8288, 8290, 8291, 8299, 8297, 8298,
8296, 8289, 8292,
]
__charcode_to_pos_7376 = _all_ushort(__charcode_to_pos_7376)
def _charcode_to_pos_7376(index): return intmask(__charcode_to_pos_7376[index])
# estimated 0.47 KiB
__charcode_to_pos_7424 = [
4769, 4770, 4938, 4767, 4771, 4772, 4756, 4755, 4935, 4933, 4774, 4775, 4768, 4776, 4761, 4758,
4759, 4918, 4919, 4920, 4936, 4760, 4942, 4802, 4777, 4762, 4766, 4764, 4779, 4923, 4922, 4921,
4780, 4781, 4782, 4757, 4783, 4784, 3899, 3901, 3898, 3900, 3897, 2226, 5622, 5623, 5615, 5616,
5624, 5625, 5618, 5626, 5627, 5628, 5629, 5630, 5631, 5632, 5633, 5619, 5620, 5621, 5634, 5617,
5635, 5636, 5638, 5690, 5738, 5691, 5740, 5693, 5705, 5708, 5733, 5727, 5743, 5713, 5745, 5757,
5720, 5712, 5726, 5728, 5737, 5694, 5729, 5735, 5749, 5734, 5741, 5722, 5692, 5696, 5714, 5707,
5715, 5704, 4972, 4975, 4976, 4977, 3922, 3918, 3921, 3920, 3919, 4952, 4799, 4810, 4803, 4871,
4877, 4895, 4902, 4901, 4913, 4925, 4965, 4939, 5647, 4850, 4927, 4785, 4854, 4892, 4786, 4951,
4800, 4811, 4804, 4836, 4862, 4865, 4872, 4878, 4896, 4903, 4915, 4832, 4956, 4968, 4967, 4790,
4794, 4809, 4826, 4888, 4909, 4917, 4847, 4889, 4833, 4950, 4831, 5739, 5697, 5703, 5710, 5748,
5756, 5706, 5732, 5744, 5716, 5717, 5698, 5699, 5755, 5719, 5718, 5700, 5721, 5742, 5724, 5725,
5701, 5695, 5730, 5731, 5709, 5736, 5750, 5751, 5702, 5723, 5746, 5752, 5754, 5753, 5711, 5747,
931, 932, 984, 985, 975, 940, 974, 867, 941, 868, 957, 912, 976, 939, 991, 990,
992, 986, 987, 953, 950, 951, 952, 958, 960, 959, 961, 945, 962, 954, 946, 947,
963, 948, 949, 956, 964, 955, 965,
]
__charcode_to_pos_7424 = _all_ushort(__charcode_to_pos_7424)
def _charcode_to_pos_7424(index): return intmask(__charcode_to_pos_7424[index])
# estimated 0.05 KiB
__charcode_to_pos_8275 = [
6927, 4266, 3641, 7614, -1, 3643, 3647, 7708, 3644, 2432, 7703, 8324, -1, -1, -1, -1,
-1, 4267,
]
__charcode_to_pos_8275 = _all_short(__charcode_to_pos_8275)
def _charcode_to_pos_8275(index): return intmask(__charcode_to_pos_8275[index])
# estimated 0.03 KiB
__charcode_to_pos_8370 = [
3962, 207, 4176, 614, 5413, 6802, 7530,
]
__charcode_to_pos_8370 = _all_ushort(__charcode_to_pos_8370)
def _charcode_to_pos_8370(index): return intmask(__charcode_to_pos_8370[index])
# estimated 0.03 KiB
__charcode_to_pos_8524 = [
6336, 204, 7706, 6978, 8328, 8330, 8329,
]
__charcode_to_pos_8524 = _all_ushort(__charcode_to_pos_8524)
def _charcode_to_pos_8524(index): return intmask(__charcode_to_pos_8524[index])
# estimated 0.07 KiB
__charcode_to_pos_9167 = [
3516, 8325, 5606, 5607, 5614, 5608, 5612, 5613, 5611, 5610, 5609, 3635, 3651, 7690, 448, 7692,
450, 7691, 449, 8352, 423, 6869, 3639, 208, 3517, 2305,
]
__charcode_to_pos_9167 = _all_ushort(__charcode_to_pos_9167)
def _charcode_to_pos_9167(index): return intmask(__charcode_to_pos_9167[index])
# estimated 0.25 KiB
__charcode_to_pos_9866 = [
5766, 5767, 2324, 2327, 2326, 2325, 8339, 436, 4089, 206, 1135, 6868, 6742, 58, 3640, 3653,
6867, 209, 3642, 6301, 7615, 7616, 8333, 4170, 2438, 2439, 4268, 5535, 5534, 5533, 8326, 4171,
5548, 5549, 5547, 5536, 2330, 7746, 1133, 3649, 5974, 615, 6302, 4362, 8322, 700, 429, 6744,
6743, 8332, 6745, 6797, 419, 6857, 8337, 8336, 439, 438, 6981, 6870, 6486, 430, 7618, 7705,
7704, 8338, 1136, 2331, -1, 6482, 612, 4104, 702, 699, 6034, 57, 435, 8354, 426, 8343,
2443, 4097, 4984, 6863, 3636, 434, 6529, 6530, -1, 4091, -1, -1, -1, -1, 437, 6795,
701, 613, 4169, 3654, 3655, 5546, 5769, 7741, 3645, 3638, 3652, 6599, 6811, 6979, 4269, 6334,
7531, 4270, 4098, 3650, 2119, 8340,
]
__charcode_to_pos_9866 = _all_short(__charcode_to_pos_9866)
def _charcode_to_pos_9866(index): return intmask(__charcode_to_pos_9866[index])
# estimated 0.04 KiB
__charcode_to_pos_10176 = [
7613, 8353, 6337, 6254, 6253, 4989, 6538, 6255, 6526, 6926, 8323, -1, 5415,
]
__charcode_to_pos_10176 = _all_short(__charcode_to_pos_10176)
def _charcode_to_pos_10176(index): return intmask(__charcode_to_pos_10176[index])
# estimated 0.19 KiB
__charcode_to_pos_11008 = [
6045, 6047, 6798, 6800, 4982, 5010, 7744, 2442, 6046, 6048, 6799, 6801, 4983, 7745, 6548, 6549,
4998, 4999, 6817, 6814, 6816, 6815, 2306, 2307, 2309, 2308, 2436, 425, 8344, 445, 8356, 443,
8349, 8341, 440, 4172, 424, 427, 8345, 428, 8346, 431, 432, 8350, 441, 8342, 444, 8355,
4980, 7617, 4979, 5414, 5006, 5005, 5007, 5008, 5000, 4997, 4996, 5002, 5004, 5003, 5001, 8334,
3634, 6524, 4993, 6546, 6547, 5009, 6550, 6525, 6544, 7683, 4995, 4994, 6545, -1, -1, -1,
8347, 433, 8351, 442, 8348, 4095, 4096, 4092, 4090, 4093,
]
__charcode_to_pos_11008 = _all_short(__charcode_to_pos_11008)
def _charcode_to_pos_11008(index): return intmask(__charcode_to_pos_11008[index])
# estimated 0.49 KiB
__charcode_to_pos_11264 = [
3743, 3698, 3729, 3705, 3701, 3730, 3737, 3700, 3736, 3710, 3711, 3706, 3699, 3738, 3713, 3714,
3740, 3715, 3717, 3739, 3723, 3726, 3742, 3703, 3741, 3716, 3718, 3719, 3728, 3702, 3721, 3732,
3731, 3733, 3722, 3735, 3724, 3725, 3734, 3708, 3697, 3707, 3704, 3709, 3720, 3727, 3712, -1,
3790, 3745, 3776, 3752, 3748, 3777, 3784, 3747, 3783, 3757, 3758, 3753, 3746, 3785, 3760, 3761,
3787, 3762, 3764, 3786, 3770, 3773, 3789, 3750, 3788, 3763, 3765, 3766, 3775, 3749, 3768, 3779,
3778, 3780, 3769, 3782, 3771, 3772, 3781, 3755, 3744, 3754, 3751, 3756, 3767, 3774, 3759, -1,
4686, 4863, 4688, 4702, 4707, 4791, 4924, 4744, 4838, 4683, 4859, 4738, 4964, 4648, 4691, 4718,
4719, 4955, 4747, 4961, 4957, 4745, 4839, 4943, 4827, 4937, 4883, 4765, 4973, 5637, 4714, 4739,
998, 1056, 1043, 1101, 1041, 1099, 1008, 1066, 1039, 1097, 1032, 1090, 1036, 1094, 1042, 1100,
1034, 1092, 1040, 1098, 1009, 1067, 1013, 1071, 1046, 1104, 1047, 1105, 1011, 1069, 1014, 1072,
1038, 1096, 1044, 1102, 1033, 1091, 1035, 1093, 1048, 1106, 1045, 1103, 1010, 1068, 1037, 1095,
1030, 1088, 1004, 1062, 1025, 1083, 1000, 1058, 1006, 1064, 1007, 1065, 1002, 1060, 1023, 1081,
1031, 1089, 1003, 1061, 1021, 1079, 1024, 1082, 997, 1055, 1005, 1063, 1016, 1074, 1017, 1075,
1012, 1070, 1019, 1077, 1018, 1076, 1015, 1073, 1022, 1080, 1020, 1078, 1028, 1086, 1026, 1084,
1027, 1085, 1029, 1087, 1108, 1109, 1110, 1112, 1113, 1107, 1111, 1001, 1059, 999, 1057, 996,
995, 994,
]
__charcode_to_pos_11264 = _all_short(__charcode_to_pos_11264)
def _charcode_to_pos_11264(index): return intmask(__charcode_to_pos_11264[index])
# estimated 0.1 KiB
__charcode_to_pos_11513 = [
1054, 1051, 1052, 1053, 1049, 1050, 1114, 3689, 3685, 3664, 3688, 3690, 3684, 3679, 3681, 3691,
3672, 3683, 3686, 3694, 3692, 3675, 3680, 3676, 3678, 3682, 3693, 3674, 3673, 3663, 3695, 3677,
3659, 3662, 3670, 3661, 3660, 3687, 3671, 3665, 3669, 3667, 3696, 3666, 3668,
]
__charcode_to_pos_11513 = _all_ushort(__charcode_to_pos_11513)
def _charcode_to_pos_11513(index): return intmask(__charcode_to_pos_11513[index])
# estimated 0.12 KiB
__charcode_to_pos_11568 = [
7641, 7652, 7653, 7646, 7648, 7631, 7670, 7642, 7645, 7643, 7644, 7679, 7669, 7649, 7635, 7651,
7654, 7630, 7639, 7655, 7668, 7650, 7636, 7675, 7640, 7680, 7665, 7629, 7637, 7671, 7672, 7673,
7634, 7638, 7674, 7681, 7656, 7657, 7647, 7633, 7628, 7658, 7660, 7659, 7661, 7662, 7667, 7663,
7676, 7677, 7678, 7664, 7632, 7666,
]
__charcode_to_pos_11568 = _all_ushort(__charcode_to_pos_11568)
def _charcode_to_pos_11568(index): return intmask(__charcode_to_pos_11568[index])
# estimated 0.06 KiB
__charcode_to_pos_11648 = [
3610, 3525, 3611, 3604, 3596, 3521, 3607, 3541, 3583, 3582, 3549, 3621, 3543, 3542, 3609, 3605,
3540, 3587, 3588, 3544, 3548, 3547, 3546,
]
__charcode_to_pos_11648 = _all_ushort(__charcode_to_pos_11648)
def _charcode_to_pos_11648(index): return intmask(__charcode_to_pos_11648[index])
# estimated 0.3 KiB
__charcode_to_pos_11680 = [
3597, 3603, 3601, 3598, 3600, 3599, 3602, -1, 3533, 3539, 3537, 3534, 3536, 3535, 3538, -1,
3614, 3620, 3618, 3615, 3617, 3616, 3619, -1, 3526, 3532, 3530, 3527, 3529, 3528, 3531, -1,
3566, 3572, 3570, 3567, 3569, 3568, 3571, -1, 3558, 3564, 3562, 3559, 3561, 3560, 3563, -1,
3574, 3580, 3578, 3575, 3577, 3576, 3579, -1, 3550, 3556, 3554, 3551, 3553, 3552, 3555, -1,
874, 902, 897, 876, 892, 893, 900, 879, 880, 881, 904, 901, 882, 877, 889, 899,
888, 896, 887, 886, 898, 878, 903, 885, 875, 895, 890, 891, 884, 894, 873, 883,
6532, 6531, 4988, 6537, 4986, 6534, 6484, 6483, 2434, 4991, 6540, 6485, 4981, 6536, 2444, 6332,
3646, 6527, 4174, 2433, 2441, 7743, 2435, 2437, 4265, 6303, 4175, 7686, 4987, 6535, 7684, 7685,
4992, 6541, 7688, 7689, 446, 447, 4990, 6539, 4985, 6533, 7707, 6252, 6866, 3648, 6528, 8327,
6551, 8357,
]
__charcode_to_pos_11680 = _all_short(__charcode_to_pos_11680)
def _charcode_to_pos_11680(index): return intmask(__charcode_to_pos_11680[index])
# estimated 0.09 KiB
__charcode_to_pos_12736 = [
859, 862, 863, 861, 850, 835, 841, 832, 840, 854, 842, 838, 833, 839, 836, 865,
831, 849, 845, 857, 864, 834, 844, 853, 852, 858, 856, 846, 848, 860, 855, 851,
843, 837, 847, 866,
]
__charcode_to_pos_12736 = _all_ushort(__charcode_to_pos_12736)
def _charcode_to_pos_12736(index): return intmask(__charcode_to_pos_12736[index])
# estimated 0.04 KiB
__charcode_to_pos_12868 = [
707, 704, 706, 705, 718, 717, 716, 712, 713, 715, 714, 719, 6333,
]
__charcode_to_pos_12868 = _all_ushort(__charcode_to_pos_12868)
def _charcode_to_pos_12868(index): return intmask(__charcode_to_pos_12868[index])
# estimated 0.14 KiB
__charcode_to_pos_19904 = [
4152, 4156, 4117, 4164, 4166, 4112, 4150, 4129, 4146, 4163, 4141, 4148, 4122, 4124, 4135, 4168,
4121, 4165, 4107, 4111, 4109, 4128, 4147, 4143, 4131, 4127, 4134, 4126, 4151, 4154, 4133, 4119,
4142, 4125, 4140, 4120, 4155, 4138, 4136, 4116, 4115, 4132, 4110, 4113, 4123, 4139, 4137, 4157,
4144, 4153, 4149, 4160, 4114, 4161, 4106, 4158, 4159, 4162, 4118, 4167, 4130, 4145, 4105, 4108,
]
__charcode_to_pos_19904 = _all_ushort(__charcode_to_pos_19904)
def _charcode_to_pos_19904(index): return intmask(__charcode_to_pos_19904[index])
# estimated 0.7 KiB
__charcode_to_pos_42192 = [
5402, 5391, 5390, 5366, 5376, 5375, 5385, 5389, 5388, 5404, 5383, 5382, 5365, 5374, 5373, 5406,
5381, 5405, 5393, 5394, 5395, 5380, 5387, 5408, 5386, 5403, 5407, 5392, 5409, 5384, 5398, 5399,
5396, 5397, 5410, 5400, 5377, 5378, 5379, 5401, 5370, 5372, 5368, 5369, 5371, 5367, 5411, 5412,
8021, 8022, 7858, 8007, 8008, 7979, 7782, 7789, 7892, 7867, 7899, 7841, 7965, 7993, 7817, 7810,
7768, 7761, 7885, 7986, 7775, 7920, 7803, 7796, 7831, 7824, 7958, 7972, 7937, 8000, 7876, 7926,
7847, 7906, 7951, 7944, 8030, 8031, 7862, 7863, 8016, 8017, 7983, 7786, 7793, 7896, 7873, 7903,
7844, 7969, 7997, 7821, 7814, 7772, 7765, 7889, 7990, 7779, 7922, 7807, 7800, 7835, 7828, 7962,
7976, 7941, 8004, 7881, 7931, 7852, 7910, 7955, 7948, 8028, 8029, 7933, 7860, 7861, 8014, 8015,
7982, 7785, 7792, 7895, 7871, 7872, 7902, 7843, 7968, 7996, 7820, 7813, 7771, 7764, 7888, 7989,
7778, 7921, 7806, 7799, 7834, 7827, 7961, 7975, 7940, 8003, 7879, 7880, 7930, 7851, 7909, 7954,
7947, 8025, 8026, 7856, 8011, 8012, 7981, 7784, 7791, 7894, 7870, 7901, 7839, 7967, 7995, 7819,
7812, 7770, 7763, 7887, 7988, 7777, 7918, 7805, 7798, 7833, 7826, 7960, 7974, 7939, 8002, 7878,
7929, 7850, 7908, 7953, 7946, 8032, 8033, 7864, 7865, 8018, 8019, 7984, 7787, 7794, 7897, 7874,
7904, 7845, 7970, 7998, 7822, 7815, 7773, 7766, 7890, 7991, 7780, 7923, 7808, 7801, 7836, 7829,
7963, 7977, 7942, 8005, 7882, 7932, 7853, 7911, 7956, 7949, 8024, 8027, 7935, 7854, 7855, 8010,
8013, 7980, 7783, 7790, 7893, 7869, 7900, 7837, 7838, 7966, 7994, 7818, 7811, 7769, 7762, 7886,
7987, 7776, 7912, 7804, 7797, 7832, 7825, 7959, 7973, 7938, 8001, 7877, 7928, 7849, 7907, 7952,
7945, 8020, 8023, 7934, 7857, 7859, 8006, 8009, 7978, 7781, 7788, 7891, 7866, 7868, 7898, 7840,
7842, 7964, 7992, 7816, 7809, 7767, 7760, 7883, 7985, 7774, 7919, 7802, 7795, 7830, 7823, 7957,
7971, 7936, 7999, 7875, 7925, 7927, 7846, 7848, 7905, 7950, 7943, 7924, 7884, 7747, 7758, 7759,
7915, 7916, 7913, 8038, 8041, 8045, 8043, 8034, 8039, 8044, 8037, 8036, 8042, 8046, 8035, 8040,
7757, 7752, 7756, 7755, 7750, 7749, 7754, 7753, 7748, 7751, 7917, 7914,
]
__charcode_to_pos_42192 = _all_ushort(__charcode_to_pos_42192)
def _charcode_to_pos_42192(index): return intmask(__charcode_to_pos_42192[index])
# estimated 0.12 KiB
__charcode_to_pos_42560 = [
2220, 2274, 2183, 2236, 2203, 2257, 2198, 2251, 2181, 2234, 2200, 2253, 2178, 2231, 2201, 2254,
2216, 2270, 2196, 2249, 2204, 2258, 2197, 2250, 2179, 2232, 2177, 2230, 2195, 2248, 2218, 2272,
-1, -1, 2209, 2263, 2207, 2261, 2208, 2262, 2199, 2252, 2176, 2229, 2182, 2235, 2225, 911,
908, 909, 907, 6796,
]
__charcode_to_pos_42560 = _all_short(__charcode_to_pos_42560)
def _charcode_to_pos_42560(index): return intmask(__charcode_to_pos_42560[index])
# estimated 0.07 KiB
__charcode_to_pos_42620 = [
910, 905, 2224, 2227, 2186, 2239, 2184, 2237, 2219, 2273, 2180, 2233, 2185, 2238, 2211, 2265,
2215, 2269, 2213, 2267, 2212, 2266, 2214, 2268, 2194, 2247, 2210, 2264,
]
__charcode_to_pos_42620 = _all_ushort(__charcode_to_pos_42620)
def _charcode_to_pos_42620(index): return intmask(__charcode_to_pos_42620[index])
# estimated 0.19 KiB
__charcode_to_pos_42656 = [
411, 347, 414, 349, 410, 386, 403, 413, 375, 412, 352, 383, 389, 388, 351, 358,
402, 374, 368, 355, 398, 363, 393, 399, 392, 396, 345, 341, 373, 372, 367, 405,
395, 406, 407, 376, 339, 379, 369, 371, 382, 408, 380, 337, 391, 354, 361, 378,
385, 390, 340, 364, 365, 366, 394, 381, 338, 336, 409, 377, 353, 384, 350, 342,
357, 387, 359, 360, 404, 348, 362, 356, 401, 346, 400, 370, 397, 335, 343, 344,
332, 331, 415, 417, 334, 333, 416, 418,
]
__charcode_to_pos_42656 = _all_ushort(__charcode_to_pos_42656)
def _charcode_to_pos_42656(index): return intmask(__charcode_to_pos_42656[index])
# estimated 0.29 KiB
__charcode_to_pos_42752 = [
5646, 5642, 5645, 5641, 5643, 5639, 5644, 5640, 5653, 5662, 5678, 5666, 5657, 5652, 5661, 5677,
5665, 5656, 5654, 5663, 5679, 5669, 5658, 5650, 5651, 5649, 5676, 5687, 5686, 5684, 5683, 5674,
5758, 5759, 4665, 4829, 4666, 4830, 4746, 4840, 4727, 4944, 4726, 4930, 4740, 4805, 4741, 4806,
4773, 4778, 4649, 4795, 4650, 4796, 4651, 4797, 4646, 4792, 4647, 4793, 4652, 4798, 4711, 4908,
4684, 4860, 4682, 4858, 4685, 4861, 4653, 4801, 4687, 4864, 4695, 4882, 4696, 4884, 4700, 4890,
4703, 4893, 4701, 4891, 4704, 4894, 4705, 4898, 4706, 4899, 4710, 4906, 4712, 4911, 4734, 4954,
4737, 4960, 4735, 4958, 4724, 4928, 4725, 4929, 4736, 4959, 4667, 4834, 4679, 4855, 4743, 4808,
5763, 4815, 4870, 4876, 4881, 4910, 4763, 4941, 4953, 4673, 4848, 4674, 4849, 4675, 4720, 4934,
4721, 4940, 4676, 4851, 4677, 4852, 4678, 4853, 5673, 5648, 5688, 4716, 4916,
]
__charcode_to_pos_42752 = _all_ushort(__charcode_to_pos_42752)
def _charcode_to_pos_42752(index): return intmask(__charcode_to_pos_42752[index])
# estimated 0.26 KiB
__charcode_to_pos_43003 = [
4752, 4753, 4750, 4751, 4754, 6955, 6957, 6965, 6959, 6956, 6958, 6966, 6947, 6946, 6943, 6942,
6964, 6941, 6940, 6945, 6944, 6935, 6934, 6929, 6928, 6937, 6936, 6931, 6930, 6953, 6949, 6948,
6939, 6938, 6952, 6933, 6951, 6932, 6954, 6950, 6968, 6970, 6971, 6969, 6967, 6960, 6961, 6962,
6963, -1, -1, -1, -1, 6036, 6035, 6039, 6037, 6038, 6040, 6041, 6043, 6044, 6042, -1,
-1, -1, -1, -1, -1, 6365, 6364, 6363, 6358, 6341, 6343, 6375, 6360, 6355, 6354, 6346,
6361, 6367, 6366, 6372, 6377, 6351, 6350, 6345, 6380, 6368, 6369, 6347, 6382, 6379, 6376, 6348,
6349, 6374, 6338, 6383, 6385, 6370, 6384, 6378, 6381, 6373, 6362, 6371, 6390, 6391, 6353, 6352,
6344, 6359, 6339, 6357, 6356, 6340, 6389, 6392, 6342, 6388, 6393, 6387, 6386,
]
__charcode_to_pos_43003 = _all_short(__charcode_to_pos_43003)
def _charcode_to_pos_43003(index): return intmask(__charcode_to_pos_43003[index])
# estimated 0.15 KiB
__charcode_to_pos_43136 = [
6726, 6725, 6708, 6709, 6712, 6713, 6714, 6715, 6690, 6691, 6688, 6689, 6716, 6717, 6710, 6718,
6719, 6711, 6705, 6704, 6701, 6700, 6680, 6699, 6698, 6703, 6702, 6682, 6685, 6684, 6675, 6674,
6681, 6687, 6686, 6677, 6676, 6683, 6707, 6706, 6697, 6696, 6721, 6723, 6722, 6679, 6692, 6693,
6694, 6695, 6720, 6678, 6661, 6731, 6734, 6735, 6736, 6737, 6729, 6730, 6727, 6728, 6738, 6739,
6732, 6740, 6741, 6733, 6724,
]
__charcode_to_pos_43136 = _all_ushort(__charcode_to_pos_43136)
def _charcode_to_pos_43136(index): return intmask(__charcode_to_pos_43136[index])
# estimated 0.28 KiB
__charcode_to_pos_43214 = [
6663, 6662, 6673, 6668, 6672, 6671, 6666, 6665, 6670, 6669, 6664, 6667, -1, -1, -1, -1,
-1, -1, 930, 925, 929, 928, 923, 922, 927, 926, 921, 924, 918, 919, 914, 915,
916, 917, 913, 920, 2297, 2291, 2295, 2294, 2293, 2292, 2298, 2303, 2302, 2304, -1, -1,
-1, -1, 4484, 4479, 4483, 4482, 4477, 4476, 4481, 4480, 4475, 4478, 4442, 4441, 4455, 4449,
4446, 4445, 4462, 4450, 4448, 4437, 4451, 4444, 4443, 4457, 4454, 4452, 4458, 4461, 4456, 4460,
4447, 4438, 4459, 4453, 4463, 4439, 4464, 4440, 4473, 4470, 4472, 4471, 4474, 4469, 4467, 4468,
4465, 4466, 6505, 6502, 6496, 6510, 6501, 6498, 6507, 6499, 6492, 6500, 6504, 6494, 6509, 6508,
6506, 6512, 6511, 6503, 6491, 6495, 6497, 6493, 6513, 6521, 6523, 6518, 6516, 6522, 6517, 6520,
6519, 6488, 6487, 6490, 6489, 6515,
]
__charcode_to_pos_43214 = _all_short(__charcode_to_pos_43214)
def _charcode_to_pos_43214(index): return intmask(__charcode_to_pos_43214[index])
# estimated 0.27 KiB
__charcode_to_pos_43359 = [
6514, 4003, 4002, 4000, 4001, 3986, 3989, 3992, 3987, 3994, 3993, 3988, 3984, 3990, 3991, 3985,
3976, 3975, 3974, 3981, 3980, 3982, 3997, 3972, 3973, 3995, 3998, 3983, 4004, 3996, -1, -1,
-1, 4342, 4338, 4340, 4341, 4312, 4280, 4279, 4281, 4321, 4300, 4286, 4287, 4319, 4313, 4320,
4282, 4283, 4284, 4296, 4297, 4285, 4294, 4295, 4310, 4289, 4311, 4288, 4308, 4309, 4275, 4276,
4291, 4306, 4307, 4277, 4278, 4290, 4298, 4299, 4292, 4293, 4316, 4318, 4301, 4302, 4315, 4317,
4304, 4305, 4303, 4314, 4339, 4345, 4347, 4348, 4349, 4343, 4344, 4346, 4351, 4350, 4271, 4272,
4273, 4336, 4274, 4322, 4325, 4331, 4327, 4332, 4330, 4328, 4326, 4323, 4324, 4329, 4337, -1,
4335, 4361, 4356, 4360, 4359, 4354, 4353, 4358, 4357, 4352, 4355, -1, -1, -1, -1, 4333,
4334,
]
__charcode_to_pos_43359 = _all_short(__charcode_to_pos_43359)
def _charcode_to_pos_43359(index): return intmask(__charcode_to_pos_43359[index])
# estimated 0.12 KiB
__charcode_to_pos_43520 = [
664, 672, 674, 671, 665, 673, 661, 660, 657, 656, 640, 641, 655, 654, 659, 658,
643, 644, 642, 663, 662, 628, 627, 645, 646, 626, 651, 650, 649, 625, 624, 647,
648, 623, 670, 668, 667, 669, 652, 653, 666, 679, 682, 683, 688, 686, 685, 684,
680, 681, 687, 622, 620, 619, 621,
]
__charcode_to_pos_43520 = _all_ushort(__charcode_to_pos_43520)
def _charcode_to_pos_43520(index): return intmask(__charcode_to_pos_43520[index])
# estimated 0.27 KiB
__charcode_to_pos_43584 = [
634, 633, 630, 616, 631, 638, 629, 636, 639, 637, 635, 632, 618, 617, -1, -1,
698, 693, 697, 696, 691, 690, 695, 694, 689, 692, -1, -1, 678, 676, 675, 677,
5795, 5787, 5786, 5791, 5790, 5784, 5793, 5792, 5782, 5781, 5783, 5785, 5797, 5789, 5788, 5794,
5879, 5798, 5799, 5796, 5825, 5826, 5827, 5846, 5847, 5845, 5823, 5842, -1, -1, -1, -1,
7170, 7146, 7169, 7145, 7168, 7144, 7183, 7159, 7177, 7153, 7172, 7148, 7171, 7147, 7188, 7164,
7178, 7154, 7181, 7157, 7176, 7152, 7175, 7151, 7179, 7155, 7180, 7156, 7174, 7150, 7173, 7149,
7182, 7158, 7186, 7162, 7190, 7166, 7187, 7163, 7185, 7161, 7189, 7165, 7184, 7160, 7191, 7167,
7193, 7204, 7212, 7209, 7208, 7214, 7215, 7192, 7213, 7210, 7211, 7203, 7207, 7206, 7205, 7202,
7199, 7200, 7201,
]
__charcode_to_pos_43584 = _all_short(__charcode_to_pos_43584)
def _charcode_to_pos_43584(index): return intmask(__charcode_to_pos_43584[index])
# estimated 0.13 KiB
__charcode_to_pos_43968 = [
5561, 5582, 5575, 5577, 5567, 5563, 5584, 5571, 5560, 5565, 5570, 5581, 5583, 5557, 5585, 5573,
5569, 5579, 5556, 5558, 5580, 5552, 5559, 5554, 5555, 5553, 5551, 5562, 5576, 5578, 5568, 5564,
5572, 5566, 5574, 5591, 5590, 5588, 5594, 5592, 5593, 5589, 5595, 5550, 5586, 5587, -1, -1,
5605, 5600, 5604, 5603, 5598, 5597, 5602, 5601, 5596, 5599,
]
__charcode_to_pos_43968 = _all_short(__charcode_to_pos_43968)
def _charcode_to_pos_43968(index): return intmask(__charcode_to_pos_43968[index])
# estimated 0.16 KiB
__charcode_to_pos_55216 = [
4078, 4079, 4082, 4083, 4084, 4081, 4080, 4085, 4086, 4066, 4065, 4064, 4067, 4068, 4069, 4071,
4070, 4074, 4072, 4073, 4075, 4061, 4062, -1, -1, -1, -1, 4019, 4018, 4049, 4050, 4055,
4056, 4057, 4054, 4053, 4058, 4036, 4034, 4046, 4035, 4031, 4030, 4033, 4032, 4013, 4016, 4017,
4052, 4014, 4015, 4026, 4025, 4029, 4051, 4024, 4028, 4027, 4043, 4037, 4048, 4047, 4038, 4040,
4039, 4041, 4042, 4021, 4020, 4060, 4059, 4007, 4006, 4044, 4022, 4023,
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
6469, 6472, 6473, 6470, 6479, 6471, 6481, 6475, 6478, 6480,
]
__charcode_to_pos_65040 = _all_ushort(__charcode_to_pos_65040)
def _charcode_to_pos_65040(index): return intmask(__charcode_to_pos_65040[index])
# estimated 0.2 KiB
__charcode_to_pos_65536 = [
5282, 5306, 5298, 5333, 5290, 5277, 5317, 5280, 5286, 5319, 5322, 5314, -1, 5309, 5335, 5338,
5318, 5329, 5336, 5347, 5348, 5292, 5342, 5293, 5294, 5279, 5299, 5310, 5320, 5326, 5284, 5343,
5304, 5289, 5327, 5287, 5344, 5301, 5308, -1, 5334, 5302, 5321, 5278, 5295, 5307, 5285, 5312,
5291, 5323, 5324, 5283, 5303, 5281, 5331, 5325, 5340, 5311, 5316, -1, 5288, 5341, -1, 5300,
5297, 5313, 5346, 5339, 5349, 5315, 5296, 5328, 5337, 5305, 5330, 5332, 5345, 5350, -1, -1,
5351, 5352, 5363, 5362, 5353, 5354, 5361, 5355, 5356, 5364, 5357, 5358, 5359, 5360,
]
__charcode_to_pos_65536 = _all_short(__charcode_to_pos_65536)
def _charcode_to_pos_65536(index): return intmask(__charcode_to_pos_65536[index])
# estimated 0.57 KiB
__charcode_to_pos_65664 = [
5165, 5166, 5167, 5154, 5156, 5155, 5157, 5158, 5159, 5160, 5162, 5161, 5164, 5163, 5168, 5171,
5169, 5172, 5170, 5272, 5271, 5174, 5173, 5175, 5274, 5273, 5178, 5177, 5179, 5176, 5180, 5183,
5181, 5184, 5185, 5186, 5275, 5187, 5188, 5182, 5191, 5192, 5190, 5189, 5193, 5194, 5195, 5196,
5197, 5198, 5201, 5202, 5203, 5200, 5204, 5199, 5205, 5206, 5207, 5208, 5209, 5210, 5211, 5212,
5213, 5214, 5216, 5215, 5217, 5218, 5221, 5220, 5222, 5219, 5223, 5224, 5225, 5226, 5227, 5228,
5229, 5230, 5276, 5231, 5232, 5234, 5235, 5236, 5233, 5237, 5238, 5239, 5240, 5241, 5269, 5249,
5250, 5251, 5252, 5253, 5254, 5255, 5256, 5257, 5258, 5259, 5260, 5261, 5262, 5263, 5264, 5265,
5266, 5267, 5268, 5242, 5243, 5244, 5245, 5246, 5247, 5248, 5270, -1, -1, -1, -1, -1,
54, 55, 56, -1, -1, -1, -1, 46, 41, 36, 16, 11, 24, 19, 4, 29,
44, 39, 34, 14, 9, 25, 20, 5, 30, 48, 43, 38, 18, 13, 28, 23,
8, 33, 47, 42, 37, 17, 12, 27, 22, 7, 32, 45, 40, 35, 15, 10,
26, 21, 6, 31, -1, -1, -1, 53, 49, 51, 52, 50, 0, 1, 2, 3,
3809, 3806, 3810, 3796, 3791, 3797, 3800, 3792, 3802, 3811, 3794, 3804, 3798, 3807, 3801, 3803,
3813, 3795, 3805, 3799, 3808, 3812, 3793, 3814, 3826, 3835, 3824, 3821, 3833, 3816, 3822, 3840,
3842, 3843, 3825, 3827, 3834, 3832, 3838, 3839, 3823, 3830, 3837, 3831, 3820, 3841, 3829, 3815,
3817, 3836, 3828, 3818, 3819, 3906, 3907, 3927, 3924, 3961, 3928, 3856, 3908, 3926, 3923, 3859,
3858, 3903, 3929, 3902, 3909, 3905, 3845, 3844, 3857, 3925, 3960, -1, -1, -1, -1, -1,
6563, 6566, 6561, 6564, 6555, 6565, 6553, 6556, 6562, 6554, 6567, 6552,
]
__charcode_to_pos_65664 = _all_short(__charcode_to_pos_65664)
def _charcode_to_pos_65664(index): return intmask(__charcode_to_pos_65664[index])
# estimated 0.11 KiB
__charcode_to_pos_66000 = [
6422, 6421, 6431, 6399, 6406, 6435, 6412, 6411, 6433, 6437, 6397, 6425, 6402, 6417, 6418, 6428,
6416, 6396, 6400, 6407, 6404, 6429, 6403, 6395, 6426, 6413, 6414, 6398, 6401, 6424, 6439, 6408,
6432, 6394, 6420, 6438, 6419, 6423, 6415, 6436, 6409, 6410, 6427, 6430, 6434, 6405,
]
__charcode_to_pos_66000 = _all_ushort(__charcode_to_pos_66000)
def _charcode_to_pos_66000(index): return intmask(__charcode_to_pos_66000[index])
# estimated 0.17 KiB
__charcode_to_pos_66176 = [
5425, 5427, 5420, 5421, 5432, 5431, 5434, 5442, 5444, 5423, 5435, 5418, 5438, 5436, 5416, 5429,
5417, 5430, 5441, 5437, 5419, 5439, 5440, 5422, 5424, 5426, 5428, 5433, 5443, -1, -1, -1,
592, 603, 594, 565, 588, 606, 566, 593, 610, 608, 568, 609, 595, 583, 578, 579,
577, 563, 586, 576, 611, 573, 585, 602, 582, 604, 596, 591, 600, 601, 574, 587,
598, 599, 580, 581, 575, 605, 564, 584, 589, 607, 569, 570, 571, 572, 567, 597,
590,
]
__charcode_to_pos_66176 = _all_short(__charcode_to_pos_66176)
def _charcode_to_pos_66176(index): return intmask(__charcode_to_pos_66176[index])
# estimated 0.18 KiB
__charcode_to_pos_66432 = [
7710, 7713, 7716, 7721, 7714, 7718, 7737, 7735, 7719, 7732, 7734, 7720, 7728, 7722, 7723, 7715,
7724, 7736, 7726, 7711, 7730, 7727, 7712, 7725, 7731, 7717, 7733, 7738, 7739, 7729, -1, 7740,
6102, 6144, 6145, 6116, 6117, 6114, 6115, 6130, 6137, 6122, 6123, 6127, 6128, 6109, 6112, 6113,
6126, 6141, 6106, 6138, 6118, 6119, 6134, 6135, 6136, 6142, 6124, 6125, 6120, 6121, 6140, 6133,
6143, 6131, 6132, 6139, -1, -1, -1, -1, 6103, 6104, 6105, 6129, 6110, 6111, 6107, 6108,
6146, 6101, 6098, 6099, 6097, 6100,
]
__charcode_to_pos_66432 = _all_short(__charcode_to_pos_66432)
def _charcode_to_pos_66432(index): return intmask(__charcode_to_pos_66432[index])
# estimated 0.2 KiB
__charcode_to_pos_66638 = [
2280, 2281, 6777, 6783, 6768, 6790, 6781, 6780, 6779, 6756, 6786, 6764, 6755, 6757, 6762, 6793,
6782, 6792, 6770, 6794, 6785, 6763, 6788, 6769, 6767, 6760, 6750, 6749, 6775, 6784, 6774, 6754,
6778, 6789, 6759, 6752, 6766, 6791, 6772, 6771, 6773, 6753, 6748, 6776, 6751, 6761, 6747, 6758,
6765, 6787, 6262, 6279, 6285, 6283, 6286, 6268, 6265, 6284, 6270, 6269, 6266, 6264, 6281, 6280,
6273, 6267, 6288, 6271, 6274, 6272, 6282, 6287, 6261, 6275, 6289, 6277, 6290, 6263, 6276, 6278,
-1, -1, 6300, 6295, 6299, 6298, 6293, 6292, 6297, 6296, 6291, 6294,
]
__charcode_to_pos_66638 = _all_short(__charcode_to_pos_66638)
def _charcode_to_pos_66638(index): return intmask(__charcode_to_pos_66638[index])
# estimated 0.2 KiB
__charcode_to_pos_67584 = [
2170, 2171, 2172, 2173, 2174, 2164, -1, -1, 2165, -1, 2120, 2121, 2122, 2123, 2124, 2125,
2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141,
2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157,
2158, 2159, 2160, 2161, 2162, 2163, -1, 2168, 2169, -1, -1, -1, 2166, -1, -1, 2167,
4185, 4202, 4188, 4187, 4193, 4200, 4192, 4194, 4198, 4199, 4203, 4195, 4204, 4205, 4190, 4186,
4206, 4189, 4196, 4201, 4191, 4197, -1, 4207, 4182, 4180, 4181, 4177, 4179, 4184, 4183, 4178,
]
__charcode_to_pos_67584 = _all_short(__charcode_to_pos_67584)
def _charcode_to_pos_67584(index): return intmask(__charcode_to_pos_67584[index])
# estimated 0.14 KiB
__charcode_to_pos_67840 = [
6440, 6453, 6458, 6461, 6451, 6448, 6450, 6452, 6446, 6457, 6447, 6459, 6455, 6456, 6443, 6441,
6460, 6444, 6454, 6449, 6442, 6445, 6462, 6467, 6464, 6463, 6465, 6466, -1, -1, -1, 6468,
5451, 5457, 5461, 5459, 5453, 5469, 5462, 5470, 5463, 5447, 5464, 5455, 5465, 5467, 5446, 5449,
5468, 5460, 5466, 5445, 5450, 5452, 5454, 5448, 5456, 5458, -1, -1, -1, -1, -1, 5471,
]
__charcode_to_pos_67840 = _all_short(__charcode_to_pos_67840)
def _charcode_to_pos_67840(index): return intmask(__charcode_to_pos_67840[index])
# estimated 0.16 KiB
__charcode_to_pos_68096 = [
4523, 4545, 4547, 4543, -1, 4544, 4546, -1, -1, -1, -1, -1, 4548, 4539, 4542, 4541,
4491, 4489, 4512, 4511, -1, 4510, 4509, 4516, -1, 4493, 4497, 4496, 4501, 4500, 4492, 4499,
4498, 4503, 4502, 4494, 4514, 4513, 4508, 4507, 4518, 4521, 4519, 4517, 4520, 4504, 4505, 4506,
4522, 4515, 4490, 4495, -1, -1, -1, -1, 4537, 4538, 4540, -1, -1, -1, -1, 4549,
4486, 4488, 4487, 4485, 4525, 4524, 4527, 4526,
]
__charcode_to_pos_68096 = _all_short(__charcode_to_pos_68096)
def _charcode_to_pos_68096(index): return intmask(__charcode_to_pos_68096[index])
# estimated 0.03 KiB
__charcode_to_pos_68176 = [
4531, 4536, 4529, 4528, 4535, 4534, 4532, 4530, 4533,
]
__charcode_to_pos_68176 = _all_ushort(__charcode_to_pos_68176)
def _charcode_to_pos_68176(index): return intmask(__charcode_to_pos_68176[index])
# estimated 0.08 KiB
__charcode_to_pos_68192 = [
6154, 6158, 6155, 6173, 6159, 6170, 6163, 6171, 6172, 6166, 6162, 6157, 6174, 6156, 6160, 6161,
6175, 6147, 6148, 6150, 6152, 6149, 6153, 6167, 6169, 6151, 6168, 6164, 6165, 6177, 6176, 6178,
]
__charcode_to_pos_68192 = _all_ushort(__charcode_to_pos_68192)
def _charcode_to_pos_68192(index): return intmask(__charcode_to_pos_68192[index])
# estimated 0.27 KiB
__charcode_to_pos_68352 = [
149, 150, 156, 152, 155, 151, 153, 154, 190, 191, 192, 193, 186, 187, 188, 189,
197, 170, 169, 168, 159, 157, 158, 194, 196, 179, 177, 183, 182, 178, 200, 195,
181, 180, 164, 163, 162, 167, 166, 165, 199, 160, 175, 176, 202, 201, 198, 174,
185, 172, 184, 171, 173, 161, -1, -1, -1, 203, 7687, 6980, 4640, 4638, 4641, 4639,
4235, 4252, 4238, 4237, 4243, 4250, 4242, 4244, 4248, 4249, 4253, 4245, 4254, 4255, 4240, 4236,
4256, 4239, 4246, 4251, 4241, 4247, -1, -1, 4257, 4261, 4262, 4264, 4263, 4260, 4259, 4258,
4208, 4223, 4210, 4209, 4215, 4222, 4214, 4216, 4220, 4221, 4224, 4217, 4218, 4225, 4212, 4226,
4211, 4213, 4219, -1, -1, -1, -1, -1, 4227, 4231, 4232, 4234, 4233, 4230, 4229, 4228,
]
__charcode_to_pos_68352 = _all_short(__charcode_to_pos_68352)
def _charcode_to_pos_68352(index): return intmask(__charcode_to_pos_68352[index])
# estimated 0.16 KiB
__charcode_to_pos_68608 = [
6179, 6221, 6222, 6211, 6247, 6240, 6214, 6215, 6249, 6192, 6232, 6180, 6225, 6194, 6234, 6182,
6226, 6193, 6233, 6181, 6210, 6246, 6200, 6239, 6189, 6229, 6183, 6227, 6216, 6250, 6195, 6235,
6184, 6206, 6208, 6196, 6185, 6223, 6203, 6242, 6201, 6241, 6204, 6243, 6231, 6202, 6224, 6209,
6217, 6212, 6207, 6245, 6197, 6236, 6213, 6248, 6218, 6251, 6198, 6237, 6186, 6190, 6187, 6191,
6230, 6205, 6244, 6199, 6238, 6188, 6228, 6219, 6220,
]
__charcode_to_pos_68608 = _all_ushort(__charcode_to_pos_68608)
def _charcode_to_pos_68608(index): return intmask(__charcode_to_pos_68608[index])
# estimated 0.08 KiB
__charcode_to_pos_69216 = [
6572, 6576, 6575, 6570, 6569, 6574, 6573, 6568, 6571, 6597, 6595, 6594, 6586, 6584, 6590, 6588,
6582, 6592, 6598, 6596, 6593, 6585, 6583, 6589, 6587, 6581, 6591, 6577, 6578, 6579, 6580,
]
__charcode_to_pos_69216 = _all_ushort(__charcode_to_pos_69216)
def _charcode_to_pos_69216(index): return intmask(__charcode_to_pos_69216[index])
# estimated 0.14 KiB
__charcode_to_pos_69760 = [
4413, 4417, 4416, 4398, 4399, 4402, 4403, 4404, 4405, 4411, 4400, 4412, 4401, 4393, 4392, 4389,
4388, 4373, 4387, 4386, 4391, 4390, 4375, 4378, 4377, 4370, 4368, 4369, 4396, 4374, 4380, 4379,
4372, 4371, 4376, 4395, 4394, 4385, 4384, 4408, 4410, 4397, 4407, 4409, 4381, 4382, 4383, 4406,
4419, 4422, 4423, 4424, 4425, 4426, 4420, 4427, 4421, 4415, 4414, 4363, 4364, 4428, 4418, 4365,
4367, 4366,
]
__charcode_to_pos_69760 = _all_ushort(__charcode_to_pos_69760)
def _charcode_to_pos_69760(index): return intmask(__charcode_to_pos_69760[index])
# estimated 1.73 KiB
__charcode_to_pos_73728 = [
1240, 1248, 1246, 1243, 1247, 1241, 1244, 1242, 1245, 1302, 1249, 1256, 1255, 1251, 1250, 1259,
1252, 1253, 1257, 1258, 1254, 1260, 1261, 1262, 1264, 1263, 1265, 1266, 1303, 1267, 1269, 1268,
1270, 1278, 1275, 1274, 1277, 1271, 1272, 1273, 1276, 1280, 1279, 1299, 1300, 1281, 1284, 1285,
1282, 1283, 1286, 1301, 1287, 1288, 1289, 1298, 1290, 1294, 1295, 1293, 1291, 1292, 1297, 1296,
1304, 1312, 1311, 1305, 1306, 1307, 1308, 1309, 1310, 1313, 1316, 1315, 1314, 1317, 1318, 1319,
1320, 1321, 1322, 1323, 1324, 1325, 1326, 1327, 1328, 1329, 1330, 1331, 1332, 1333, 1334, 1335,
1348, 1336, 1337, 1347, 1341, 1338, 1339, 1340, 1349, 1344, 1346, 1345, 1342, 1343, 1353, 1350,
1351, 1352, 1354, 1361, 1355, 1356, 1357, 1358, 1359, 1360, 1362, 1365, 1363, 1364, 1366, 1367,
1368, 1369, 1370, 1377, 1371, 1372, 1373, 1374, 1375, 1376, 1378, 1379, 1380, 1381, 1384, 1386,
1385, 1382, 1383, 1387, 1418, 1419, 1420, 1388, 1391, 1392, 1393, 1389, 1390, 1394, 1396, 1395,
1417, 1397, 1398, 1399, 1400, 1401, 1416, 1402, 1403, 1414, 1415, 1413, 1404, 1405, 1406, 1407,
1408, 1409, 1410, 1411, 1412, 1421, 1489, 1422, 1424, 1425, 1423, 1428, 1429, 1426, 1427, 1431,
1430, 1432, 1433, 1437, 1434, 1435, 1436, 1440, 1441, 1438, 1439, 1442, 1443, 1444, 1445, 1446,
1447, 1448, 1449, 1450, 1451, 1452, 1454, 1453, 1456, 1455, 1457, 1458, 1459, 1474, 1460, 1461,
1462, 1463, 1475, 1464, 1465, 1466, 1467, 1468, 1469, 1473, 1470, 1471, 1472, 1476, 1477, 1478,
1479, 1480, 1481, 1482, 1483, 1493, 1484, 1485, 1488, 1487, 1486, 1490, 1491, 1492, 1494, 1495,
1496, 1498, 1499, 1497, 1500, 1502, 1501, 1517, 1509, 1510, 1503, 1504, 1507, 1506, 1505, 1508,
1516, 1511, 1515, 1513, 1512, 1514, 1518, 1535, 1519, 1520, 1521, 1523, 1522, 1524, 1525, 1526,
1527, 1528, 1536, 1529, 1530, 1531, 1534, 1533, 1532, 1537, 1539, 1538, 1540, 1541, 1542, 1543,
1546, 1545, 1547, 1549, 1548, 1544, 1550, 1551, 1552, 1557, 1555, 1553, 1554, 1556, 1558, 1559,
1578, 1580, 1560, 1562, 1561, 1563, 1564, 1566, 1568, 1567, 1565, 1569, 1570, 1571, 1572, 1575,
1573, 1574, 1576, 1577, 1581, 1582, 1579, 1583, 1584, 1585, 1586, 1587, 1589, 1588, 1590, 1591,
1592, 1593, 1594, 1598, 1597, 1595, 1596, 1599, 1602, 1601, 1600, 1603, 1604, 1605, 1606, 1609,
1607, 1608, 1631, 1632, 1610, 1611, 1612, 1613, 1614, 1615, 1630, 1629, 1634, 1633, 1620, 1621,
1617, 1618, 1616, 1619, 1623, 1622, 1636, 1624, 1627, 1628, 1625, 1626, 1635, 1637, 1638, 1654,
1641, 1642, 1643, 1639, 1640, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1678,
1655, 1658, 1656, 1657, 1663, 1664, 1661, 1662, 1659, 1660, 1665, 1670, 1674, 1666, 1667, 1675,
1672, 1673, 1676, 1668, 1669, 1671, 1677, 1679, 1680, 1681, 1682, 1684, 1683, 1686, 1687, 1685,
1688, 1689, 1729, 1728, 1692, 1693, 1690, 1691, 1695, 1696, 1694, 1700, 1697, 1699, 1698, 1704,
1705, 1703, 1701, 1702, 1706, 1707, 1708, 1709, 1710, 1711, 1712, 1730, 1717, 1713, 1714, 1715,
1716, 1718, 1720, 1719, 1721, 1722, 1724, 1723, 1725, 1727, 1726, 1731, 1732, 1735, 1736, 1733,
1734, 1742, 1737, 1738, 1739, 1740, 1741, 1743, 1746, 1744, 1745, 1747, 1780, 1748, 1770, 1769,
1753, 1754, 1764, 1766, 1771, 1757, 1755, 1756, 1758, 1759, 1760, 1761, 1767, 1768, 1763, 1762,
1765, 1772, 1749, 1750, 1752, 1751, 1781, 1773, 1775, 1774, 1776, 1782, 1783, 1777, 1778, 1779,
1784, 1785, 1786, 1789, 1790, 1791, 1787, 1788, 1810, 1811, 1812, 1813, 1792, 1807, 1805, 1806,
1809, 1808, 1793, 1799, 1797, 1798, 1795, 1796, 1794, 1800, 1801, 1802, 1803, 1804, 1814, 1823,
1815, 1818, 1817, 1816, 1819, 1821, 1820, 1822, 1824, 1826, 1825, 1827, 1828, 1846, 1848, 1829,
1831, 1830, 1832, 1835, 1833, 1834, 1845, 1836, 1838, 1837, 1839, 1842, 1840, 1841, 1843, 1844,
1847, 1849, 1873, 1850, 1857, 1855, 1853, 1854, 1856, 1859, 1858, 1851, 1852, 1860, 1864, 1868,
1863, 1867, 1861, 1862, 1869, 1870, 1865, 1866, 1871, 1872, 1874, 1875, 1876, 1877, 1894, 1878,
1879, 1880, 1885, 1886, 1887, 1881, 1882, 1883, 1884, 1888, 1889, 1890, 1892, 1891, 1893, 1895,
1896, 1897, 1898, 1899, 1901, 1900, 1918, 1902, 1903, 1916, 1904, 1905, 1917, 1915, 1914, 1907,
1906, 1913, 1909, 1910, 1911, 1912, 1908, 1920, 1919, 1921, 1922, 1923, 1924, 1925, 1926, 1934,
1931, 1930, 1933, 1929, 1932, 1927, 1928, 1937, 1935, 1936, 1938, 1941, 1939, 1940, 1945, 1946,
1942, 1944, 1943, 1947, 1949, 1948, 1950, 1961, 1952, 1951, 1959, 1960, 1955, 1956, 1954, 1957,
1953, 1958, 1965, 1962, 1963, 1964, 1966, 1967, 1968, 1970, 1969, 1971, 1975, 1972, 1973, 1974,
1977, 1976, 1978, 1985, 1979, 1980, 1986, 1981, 1982, 1983, 1984, 1987, 1991, 1988, 1989, 1990,
1992, 1993, 1994, 1995, 2000, 1999, 1997, 1998, 1996, 2001, 2002, 2003, 2017, 2018, 2004, 2009,
2010, 2005, 2008, 2006, 2007, 2011, 2014, 2015, 2016, 2012, 2013, 2019, 2024, 2023, 2020, 2022,
2021, 2099, 2100, 2025, 2026, 2031, 2032, 2029, 2030, 2033, 2027, 2028, 2034, 2037, 2038, 2039,
2040, 2041, 2045, 2042, 2043, 2044, 2035, 2036, 2046, 2048, 2047, 2049, 2050, 2051, 2052, 2057,
2056, 2053, 2054, 2055, 2086, 2058, 2059, 2060, 2061, 2062, 2082, 2076, 2063, 2065, 2064, 2066,
2067, 2080, 2068, 2070, 2069, 2079, 2083, 2077, 2081, 2072, 2071, 2078, 2073, 2075, 2074, 2084,
2085, 2087, 2091, 2089, 2090, 2088, 2094, 2093, 2092, 2098, 2095, 2096, 2097, 2101, 2103, 2102,
2105, 2104, 2118, 2106, 2110, 2111, 2107, 2108, 2112, 2109, 2113, 2114, 2115, 2116, 2117,
]
__charcode_to_pos_73728 = _all_ushort(__charcode_to_pos_73728)
def _charcode_to_pos_73728(index): return intmask(__charcode_to_pos_73728[index])
# estimated 0.21 KiB
__charcode_to_pos_74752 = [
1225, 1220, 1163, 1150, 1205, 1200, 1142, 1180, 1224, 1169, 1154, 1208, 1199, 1141, 1179, 1170,
1155, 1210, 1201, 1143, 1181, 1188, 1230, 1222, 1165, 1152, 1207, 1198, 1138, 1178, 1189, 1231,
1223, 1166, 1153, 1232, 1214, 1215, 1167, 1144, 1204, 1197, 1137, 1177, 1193, 1233, 1216, 1217,
1168, 1145, 1202, 1203, 1187, 1228, 1211, 1212, 1158, 1149, 1218, 1219, 1159, 1162, 1160, 1161,
1209, 1196, 1194, 1195, 1139, 1140, 1173, 1175, 1176, 1174, 1226, 1221, 1164, 1151, 1206, 1186,
1227, 1213, 1156, 1157, 1147, 1148, 1172, 1171, 1184, 1229, 1190, 1234, 1146, 1191, 1235, 1185,
1192, 1183, 1182,
]
__charcode_to_pos_74752 = _all_ushort(__charcode_to_pos_74752)
def _charcode_to_pos_74752(index): return intmask(__charcode_to_pos_74752[index])
# estimated 2.11 KiB
__charcode_to_pos_77824 = [
2450, 2451, 2452, 2453, 2448, 2449, 2445, 2446, 2447, 2454, 2455, 2456, 2461, 2462, 2463, 2464,
2457, 2458, 2465, 2466, 2459, 2460, 2467, 2468, 2495, 2496, 2497, 2498, 2499, 2500, 2501, 2502,
2503, 2504, 2485, 2486, 2483, 2484, 2487, 2488, 2489, 2490, 2491, 2492, 2493, 2469, 2470, 2477,
2471, 2472, 2473, 2474, 2478, 2475, 2476, 2479, 2480, 2481, 2482, 2505, 2506, 2507, 2508, 2509,
2510, 2511, 2512, 2513, 2514, 2515, 2516, 2517, 2518, 2519, 2520, 2521, 2522, 2523, 2524, 2494,
3063, 3064, 3065, 3066, 3061, 3062, 3067, 3068, 3069, 3070, 2563, 2559, 2560, 2561, 2562, 2564,
2565, 2566, 2567, 2568, 2569, 2570, 2571, 2572, 2573, 2574, 2575, 2576, 2577, 2578, 2579, 2580,
2581, 2582, 2583, 2584, 2585, 2586, 2589, 2590, 2591, 2592, 2593, 2594, 2595, 2587, 2588, 2596,
2669, 2670, 2671, 2672, 2673, 2674, 2675, 2676, 2677, 2678, 2660, 2661, 2662, 2663, 2664, 2665,
2666, 2658, 2659, 2667, 2668, 2601, 2597, 2598, 2602, 2603, 2599, 2600, 2604, 2605, 2606, 2607,
2608, 2613, 2614, 2615, 2616, 2617, 2618, 2609, 2610, 2619, 2611, 2612, 2620, 2621, 2622, 2623,
2624, 2625, 2626, 2627, 2628, 2629, 2630, 2635, 2631, 2632, 2636, 2633, 2634, 2637, 2638, 2639,
2640, 2641, 2651, 2652, 2653, 2654, 2655, 2656, 2657, 2642, 2643, 2644, 2645, 2646, 2647, 2648,
2649, 2650, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2679, 2680, 2681, 2682, 2715, 2716, 2717,
2718, 2719, 2720, 2711, 2712, 2713, 2714, 2721, 2722, 2690, 2691, 2694, 2695, 2696, 2697, 2698,
2699, 2700, 2692, 2693, 2701, 2704, 2705, 2706, 2707, 2702, 2703, 2708, 2709, 2710, 2723, 2724,
2725, 2726, 2727, 2728, 2729, 2730, 2731, 2732, 2735, 2736, 2737, 2733, 2734, 2738, 2739, 2740,
2741, 2742, 2743, 2779, 2777, 2778, 2780, 2781, 2782, 2783, 2784, 2785, 2786, 2787, 2750, 2744,
2745, 2751, 2752, 2753, 2754, 2755, 2746, 2747, 2748, 2749, 2756, 2763, 2764, 2765, 2766, 2767,
2757, 2758, 2759, 2760, 2761, 2762, 2768, 2769, 2774, 2770, 2771, 2772, 2773, 2775, 2776, 2793,
2794, 2795, 2796, 2797, 2791, 2792, 2788, 2789, 2790, 2798, 2799, 2802, 2800, 2801, 2803, 2804,
2805, 2806, 2807, 2808, 2809, 2810, 2840, 2841, 2844, 2845, 2846, 2847, 2848, 2842, 2843, 2849,
2850, 2851, 2815, 2816, 2817, 2818, 2819, 2820, 2811, 2812, 2813, 2814, 2821, 2822, 2827, 2828,
2829, 2823, 2824, 2830, 2825, 2826, 2831, 2832, 2833, 2834, 2835, 2836, 2837, 2838, 2839, 2854,
2855, 2856, 2857, 2858, 2852, 2853, 2859, 2860, 2865, 2866, 2867, 2868, 2861, 2862, 2869, 2870,
2871, 2863, 2864, 2872, 2873, 2874, 2875, 2876, 2877, 2878, 2879, 2880, 2881, 2882, 2883, 2884,
2885, 2886, 2887, 2892, 2888, 2889, 2893, 2894, 2895, 2890, 2891, 2896, 2897, 2898, 2899, 2900,
2903, 2901, 2902, 2904, 2905, 2906, 2907, 2908, 2909, 2919, 2920, 2927, 2910, 2911, 2912, 2913,
2914, 2915, 2916, 2917, 2918, 2928, 2929, 2921, 2922, 2923, 2924, 2925, 2926, 2930, 2931, 2938,
2939, 2932, 2933, 2940, 2934, 2935, 2941, 2942, 2943, 2936, 2937, 2944, 2950, 2948, 2949, 2951,
2945, 2946, 2947, 2952, 2953, 2954, 2955, 2956, 2957, 2958, 2959, 2960, 2961, 2962, 2963, 2990,
2991, 2992, 2993, 2994, 2995, 2996, 2997, 2998, 2967, 2968, 2969, 2970, 2971, 2972, 2973, 2974,
2964, 2965, 2966, 2975, 3001, 3002, 3003, 3004, 3005, 2999, 3000, 3006, 3007, 3008, 3009, 2984,
2985, 2986, 2976, 2977, 2978, 2979, 2980, 2981, 2987, 2982, 2983, 2988, 2989, 3010, 3011, 3012,
3015, 3016, 3017, 3018, 3013, 3014, 3019, 3020, 3021, 3022, 3025, 3026, 3027, 3028, 3029, 3030,
3031, 3023, 3024, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3039, 3040, 3041, 3042, 3043, 3044,
3045, 3046, 3047, 3050, 3051, 3052, 3053, 3054, 3055, 3048, 3049, 3056, 3059, 3060, 3057, 3058,
3078, 3079, 3082, 3083, 3084, 3080, 3081, 3071, 3072, 3073, 3074, 3075, 3076, 3077, 3085, 3086,
3087, 3088, 3089, 3090, 3091, 3094, 3095, 3096, 3097, 3098, 3099, 3100, 3101, 3092, 3093, 3102,
3103, 3110, 3111, 3112, 3104, 3105, 3106, 3107, 3113, 3114, 3115, 3108, 3109, 3121, 3122, 3125,
3126, 3123, 3124, 3127, 3128, 3116, 3117, 3118, 3119, 3120, 3129, 3130, 3131, 3136, 3137, 3138,
3139, 3140, 3141, 3142, 3143, 3144, 3145, 3132, 3133, 3134, 3135, 3146, 3147, 3150, 3148, 3149,
3151, 3152, 3153, 3154, 3155, 3156, 3157, 3158, 3159, 3160, 3161, 3162, 3163, 3164, 3165, 3171,
3169, 3170, 3166, 3167, 3168, 3172, 3173, 3174, 3175, 3176, 3177, 3178, 3179, 3182, 3183, 3184,
3185, 3186, 3180, 3181, 3187, 3188, 3189, 3190, 3191, 3192, 3193, 3194, 3195, 3196, 3197, 3198,
3199, 3204, 3200, 3201, 3205, 3206, 3207, 3202, 3203, 3208, 3209, 3210, 3216, 3217, 3218, 3219,
3211, 3212, 3213, 3220, 3221, 3214, 3215, 3222, 3223, 3227, 3228, 3229, 3230, 3231, 3232, 3224,
3225, 3226, 3233, 3234, 3235, 3238, 3239, 3240, 3241, 3242, 3236, 3237, 3243, 3244, 3245, 3246,
3247, 3248, 3249, 3250, 3251, 3252, 3253, 3262, 3263, 3254, 3255, 3264, 3265, 3266, 3256, 3257,
3258, 3259, 3260, 3261, 3271, 3267, 3268, 3272, 3273, 3274, 3275, 3269, 3270, 3276, 3277, 3278,
3288, 3289, 3290, 3291, 3292, 3293, 3294, 3295, 3296, 3297, 3283, 3284, 3279, 3280, 3281, 3282,
3285, 3286, 3287, 3301, 3302, 3303, 3304, 3305, 3298, 3299, 3300, 3306, 3307, 3308, 3335, 3336,
3337, 3338, 3339, 3340, 3341, 3342, 3343, 3344, 3313, 3314, 3315, 3309, 3310, 3316, 3317, 3318,
3319, 3320, 3311, 3312, 3323, 3324, 3321, 3322, 3325, 3326, 3327, 3328, 3329, 3330, 3331, 3332,
3333, 3334, 3348, 3349, 3350, 3351, 3352, 3353, 3354, 3355, 3356, 3357, 3358, 3359, 3360, 3361,
3362, 3363, 3345, 3346, 3347, 3364, 3365, 3373, 3366, 3367, 3368, 3369, 3370, 3371, 3372, 3374,
3375, 3376, 3377, 3378, 3379, 3380, 3381, 3382, 3383, 3384, 3385, 3386, 3387, 3388, 3389, 3390,
3391, 3392, 3393, 3400, 3401, 3394, 3395, 3402, 3403, 3404, 3405, 3396, 3397, 3398, 3399, 3406,
3407, 3408, 3409, 3414, 3410, 3411, 3415, 3416, 3417, 3412, 3413, 3418, 3419, 3420, 3421, 3426,
3427, 3422, 3423, 3428, 3429, 3430, 3431, 3432, 3424, 3425, 3433, 3434, 3441, 3442, 3443, 3435,
3436, 3444, 3445, 3437, 3438, 3439, 3440, 3446, 3449, 3450, 3451, 3452, 3447, 3448, 3453, 3461,
3462, 3463, 3454, 3455, 3456, 3464, 3457, 3458, 3465, 3459, 3460, 3466, 3467, 3468, 3469, 3470,
3471, 3472, 3473, 3474, 3487, 3475, 3476, 3477, 3478, 3479, 3480, 3481, 3482, 3483, 3484, 3485,
3486, 3488, 3489, 3490, 3491, 3511, 3512, 3513, 3514, 3515, 3492, 3493, 3494, 3495, 3496, 3497,
3498, 3499, 3500, 3501, 3502, 3503, 3504, 3505, 3506, 3507, 3508, 3509, 3510, 2528, 2529, 2530,
2531, 2532, 2533, 2525, 2526, 2527, 2534, 2535, 2539, 2540, 2541, 2542, 2543, 2544, 2545, 2546,
2547, 2548, 2549, 2550, 2551, 2552, 2553, 2554, 2555, 2556, 2557, 2558, 2536, 2537, 2538,
]
__charcode_to_pos_77824 = _all_ushort(__charcode_to_pos_77824)
def _charcode_to_pos_77824(index): return intmask(__charcode_to_pos_77824[index])
# estimated 0.15 KiB
__charcode_to_pos_119296 = [
3942, 3930, 3953, 3954, 3936, 3955, 3956, 3957, 3958, 3943, 3944, 3945, 3946, 3947, 3948, 3949,
3950, 3951, 3952, 3931, 3932, 3933, 3934, 3935, 3937, 3938, 3939, 3940, 3941, 3860, 3868, 3881,
3889, 3895, 3896, 3861, 3862, 3863, 3864, 3865, 3866, 3867, 3869, 3870, 3871, 3872, 3873, 3874,
3875, 3876, 3877, 3878, 3879, 3880, 3882, 3883, 3884, 3885, 3886, 3887, 3888, 3890, 3891, 3892,
3893, 3894, 943, 942, 944, 3904,
]
__charcode_to_pos_119296 = _all_ushort(__charcode_to_pos_119296)
def _charcode_to_pos_119296(index): return intmask(__charcode_to_pos_119296[index])
# estimated 0.19 KiB
__charcode_to_pos_119552 = [
5765, 2328, 2329, 2322, 2323, 2321, 7549, 7570, 7591, 7536, 7585, 7545, 7533, 7593, 7538, 7553,
7557, 7581, 7582, 7597, 7603, 7544, 7580, 7610, 7568, 7534, 7599, 7601, 7566, 7584, 7546, 7562,
7558, 7548, 7551, 7537, 7596, 7589, 7540, 7586, 7574, 7609, 7598, 7571, 7600, 7588, 7602, 7576,
7561, 7608, 7577, 7563, 7595, 7604, 7573, 7612, 7547, 7590, 7564, 7567, 7555, 7539, 7578, 7575,
7592, 7532, 7560, 7559, 7611, 7606, 7583, 7552, 7550, 7556, 7565, 7605, 7607, 7579, 7543, 7541,
7572, 7535, 7542, 7594, 7554, 7587, 7569,
]
__charcode_to_pos_119552 = _all_ushort(__charcode_to_pos_119552)
def _charcode_to_pos_119552(index): return intmask(__charcode_to_pos_119552[index])
# estimated 0.05 KiB
__charcode_to_pos_119648 = [
1128, 1132, 1131, 1126, 1125, 1130, 1129, 1124, 1127, 1119, 1123, 1122, 1117, 1116, 1121, 1120,
1115, 1118,
]
__charcode_to_pos_119648 = _all_ushort(__charcode_to_pos_119648)
def _charcode_to_pos_119648(index): return intmask(__charcode_to_pos_119648[index])
# estimated 0.3 KiB
__charcode_to_pos_126976 = [
5477, 5492, 5507, 5484, 5511, 5510, 5508, 5490, 5505, 5502, 5482, 5479, 5497, 5494, 5475, 5486,
5491, 5506, 5503, 5483, 5480, 5498, 5495, 5476, 5487, 5489, 5504, 5501, 5481, 5478, 5496, 5493,
5474, 5485, 5515, 5488, 5472, 5514, 5499, 5500, 5512, 5509, 5513, 5473, -1, -1, -1, -1,
2381, 2332, 2333, 2334, 2335, 2336, 2337, 2338, 2339, 2340, 2341, 2342, 2343, 2344, 2345, 2346,
2347, 2348, 2349, 2350, 2351, 2352, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362,
2363, 2364, 2365, 2366, 2367, 2368, 2369, 2370, 2371, 2372, 2373, 2374, 2375, 2376, 2377, 2378,
2379, 2380, 2431, 2382, 2383, 2384, 2385, 2386, 2387, 2388, 2389, 2390, 2391, 2392, 2393, 2394,
2395, 2396, 2397, 2398, 2399, 2400, 2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410,
2411, 2412, 2413, 2414, 2415, 2416, 2417, 2418, 2419, 2420, 2421, 2422, 2423, 2424, 2425, 2426,
2427, 2428, 2429, 2430,
]
__charcode_to_pos_126976 = _all_short(__charcode_to_pos_126976)
def _charcode_to_pos_126976(index): return intmask(__charcode_to_pos_126976[index])
# estimated 0.11 KiB
__charcode_to_pos_127232 = [
2320, 2319, 2313, 2317, 2316, 2311, 2310, 2315, 2314, 2318, 2312, -1, -1, -1, -1, -1,
6306, 6307, 6308, 6309, 6310, 6311, 6312, 6313, 6314, 6315, 6316, 6317, 6318, 6319, 6320, 6321,
6322, 6323, 6324, 6325, 6326, 6327, 6328, 6329, 6330, 6331, 7702, 708, 709, 703, 721, -1,
-1, 6858,
]
__charcode_to_pos_127232 = _all_short(__charcode_to_pos_127232)
def _charcode_to_pos_127232(index): return intmask(__charcode_to_pos_127232[index])
# estimated 0.05 KiB
__charcode_to_pos_127293 = [
6859, -1, 6860, -1, -1, 6861, -1, -1, -1, 6862, -1, -1, -1, 6853, 6854, 6864,
6865, 6855,
]
__charcode_to_pos_127293 = _all_short(__charcode_to_pos_127293)
def _charcode_to_pos_127293(index): return intmask(__charcode_to_pos_127293[index])
# estimated 0.03 KiB
__charcode_to_pos_127353 = [
5884, -1, 5885, 5886, -1, -1, 5887,
]
__charcode_to_pos_127353 = _all_short(__charcode_to_pos_127353)
def _charcode_to_pos_127353(index): return intmask(__charcode_to_pos_127353[index])
# estimated 0.03 KiB
__charcode_to_pos_127370 = [
1134, 5890, 5888, 5889, -1, -1, 6808,
]
__charcode_to_pos_127370 = _all_short(__charcode_to_pos_127370)
def _charcode_to_pos_127370(index): return intmask(__charcode_to_pos_127370[index])
# estimated 0.08 KiB
__charcode_to_pos_127504 = [
6837, 6833, 6828, 6856, 6824, 6830, 6849, 6829, 6822, 6845, 6846, 6843, 6826, 6836, 6835, 6842,
6825, 6847, 6848, 6851, 6832, 6834, 6844, 6838, 6840, 6820, 6821, 6852, 6831, 6823, 6827, 6841,
6850, 6839,
]
__charcode_to_pos_127504 = _all_ushort(__charcode_to_pos_127504)
def _charcode_to_pos_127504(index): return intmask(__charcode_to_pos_127504[index])
# estimated 0.03 KiB
__charcode_to_pos_127552 = [
7699, 7693, 7694, 7695, 7700, 7697, 7701, 7696, 7698,
]
__charcode_to_pos_127552 = _all_ushort(__charcode_to_pos_127552)
def _charcode_to_pos_127552(index): return intmask(__charcode_to_pos_127552[index])
# estimated 0.48 KiB
__charcode_to_pos_917760 = [
8117, 8128, 8139, 8220, 8231, 8242, 8253, 8264, 8275, 8283, 8284, 8285, 8286, 8150, 8151, 8152,
8153, 8154, 8155, 8156, 8157, 8158, 8159, 8160, 8161, 8162, 8163, 8164, 8165, 8166, 8167, 8168,
8169, 8170, 8171, 8172, 8173, 8174, 8175, 8176, 8177, 8178, 8179, 8180, 8181, 8182, 8183, 8184,
8185, 8186, 8187, 8188, 8189, 8190, 8191, 8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
8201, 8202, 8203, 8204, 8205, 8206, 8207, 8208, 8209, 8210, 8211, 8212, 8213, 8214, 8215, 8216,
8217, 8218, 8219, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8054, 8055, 8056, 8057, 8058, 8059,
8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067, 8068, 8069, 8070, 8071, 8072, 8073, 8074, 8075,
8076, 8077, 8078, 8079, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091,
8092, 8093, 8094, 8095, 8096, 8097, 8098, 8099, 8100, 8101, 8102, 8103, 8104, 8105, 8106, 8107,
8108, 8109, 8110, 8111, 8112, 8113, 8114, 8115, 8116, 8118, 8119, 8120, 8121, 8122, 8123, 8124,
8125, 8126, 8127, 8129, 8130, 8131, 8132, 8133, 8134, 8135, 8136, 8137, 8138, 8140, 8141, 8142,
8143, 8144, 8145, 8146, 8147, 8148, 8149, 8221, 8222, 8223, 8224, 8225, 8226, 8227, 8228, 8229,
8230, 8232, 8233, 8234, 8235, 8236, 8237, 8238, 8239, 8240, 8241, 8243, 8244, 8245, 8246, 8247,
8248, 8249, 8250, 8251, 8252, 8254, 8255, 8256, 8257, 8258, 8259, 8260, 8261, 8262, 8263, 8265,
8266, 8267, 8268, 8269, 8270, 8271, 8272, 8273, 8274, 8276, 8277, 8278, 8279, 8280, 8281, 8282,
]
__charcode_to_pos_917760 = _all_ushort(__charcode_to_pos_917760)
def _charcode_to_pos_917760(index): return intmask(__charcode_to_pos_917760[index])
# estimated 0.04 KiB
__charcode_to_pos_983040 = [
4669, 4837, 4429, 4635, 4634, 4637, 4636, 7621, 7709, 6477, 482,
]
__charcode_to_pos_983040 = _all_ushort(__charcode_to_pos_983040)
def _charcode_to_pos_983040(index): return intmask(__charcode_to_pos_983040[index])
# estimated 0.79 KiB
__charcode_to_pos_983552 = [
4642, 4787, 4659, 4821, 4660, 4822, 4661, 4823, 4655, 4817, 4656, 4818, 4670, 4841, 4845, 4880,
4697, 4885, 4698, 4886, 4699, 4887, 4713, 4912, 4728, 4945, 4643, 4788, 4644, 4789, 4662, 4824,
4663, 4825, 4657, 4819, 4658, 4820, 4844, 4846, 4671, 4842, 4672, 4843, 4681, 4856, 4689, 4867,
4692, 4873, 4708, 4905, 4731, 4948, 4732, 4949, 4729, 4946, 4730, 4947, 7216, 7224, 7233, 7225,
7227, 7222, 7226, 7221, 7237, 7236, 7239, 7228, 7218, 7238, 7220, 7219, 7229, 7223, 7235, 7231,
7232, 7230, 7234, 7217, 7259, 7262, 7263, 7264, 7265, 7266, 7267, 7260, 7268, 7269, 7261, 7325,
7328, 7329, 7330, 7331, 7332, 7333, 7326, 7334, 7335, 7327, 7436, 7439, 7440, 7441, 7442, 7443,
7444, 7437, 7445, 7446, 7438, 7336, 7339, 7340, 7341, 7342, 7343, 7344, 7337, 7345, 7346, 7338,
7414, 7417, 7418, 7419, 7420, 7421, 7422, 7415, 7423, 7424, 7416, 7314, 7317, 7318, 7319, 7320,
7321, 7322, 7315, 7323, 7324, 7316, 7425, 7428, 7429, 7430, 7431, 7432, 7433, 7426, 7434, 7435,
7427, 7347, 7350, 7351, 7352, 7353, 7354, 7355, 7348, 7356, 7357, 7349, 7480, 7483, 7484, 7485,
7486, 7487, 7488, 7481, 7489, 7490, 7482, 7469, 7472, 7473, 7474, 7475, 7476, 7477, 7470, 7478,
7479, 7471, 7502, 7505, 7506, 7507, 7508, 7509, 7510, 7503, 7511, 7512, 7504, 7369, 7372, 7373,
7374, 7375, 7376, 7377, 7370, 7378, 7379, 7371, 7292, 7295, 7296, 7297, 7298, 7299, 7300, 7293,
7301, 7302, 7294, 7491, 7494, 7495, 7496, 7497, 7498, 7499, 7492, 7500, 7501, 7493, 7270, 7273,
7274, 7275, 7276, 7277, 7278, 7271, 7279, 7280, 7272, 7281, 7284, 7285, 7286, 7287, 7288, 7289,
7282, 7290, 7291, 7283, 7358, 7361, 7362, 7363, 7364, 7365, 7366, 7359, 7367, 7368, 7360, 7303,
7306, 7307, 7308, 7309, 7310, 7311, 7304, 7312, 7313, 7305, 7458, 7461, 7462, 7463, 7464, 7465,
7466, 7459, 7467, 7468, 7460, 7380, 7383, 7384, 7385, 7386, 7387, 7388, 7381, 7389, 7390, 7382,
7392, 7395, 7396, 7397, 7398, 7399, 7400, 7393, 7401, 7402, 7394, 7403, 7406, 7407, 7408, 7409,
7410, 7411, 7404, 7412, 7413, 7405, 7447, 7450, 7451, 7452, 7453, 7454, 7455, 7448, 7456, 7457,
7449, 7247, 7248, 7251, 7252, 7253, 7254, 7255, 7256, 7249, 7257, 7258, 7250, 7391, 3656, 4556,
4554, 4557, 4555, 4558, 4552, 4550, 4553, 4551, 4559, 4571, 4567, 4572, 4568, 4560, 4569, 4565,
4570, 4566, 4561, 4582, 4562, 4564, 4563, 4578, 4581, 4579, 4574, 4580, 4575, 4576, 4577, 4583,
4573, 4631, 4585, 4586, 4587, 4584, 4633, 4632, 4436, 5655,
]
__charcode_to_pos_983552 = _all_ushort(__charcode_to_pos_983552)
def _charcode_to_pos_983552(index): return intmask(__charcode_to_pos_983552[index])
def _charcode_to_pos(code):
    res = -1
    if code == 545: res = 4812
    elif 564 <= code <= 591: res = _charcode_to_pos_564(code-564)
    elif code == 686: res = 4931
    elif code == 687: res = 4932
    elif 751 <= code <= 767: res = _charcode_to_pos_751(code-751)
    elif 848 <= code <= 863: res = _charcode_to_pos_848(code-848)
    elif 880 <= code <= 893: res = _charcode_to_pos_880(code-880)
    elif code == 975: res = 3855
    elif 1015 <= code <= 1023: res = _charcode_to_pos_1015(code-1015)
    elif code == 1159: res = 906
    elif code == 1231: res = 2256
    elif 1270 <= code <= 1279: res = _charcode_to_pos_1270(code-1270)
    elif 1296 <= code <= 1317: res = _charcode_to_pos_1296(code-1296)
    elif code == 1442: res = 4099
    elif code == 1466: res = 4100
    elif code == 1477: res = 4103
    elif code == 1478: res = 4102
    elif code == 1479: res = 4101
    elif 1536 <= code <= 1566: res = _charcode_to_pos_1536(code-1536)
    elif code == 1595: res = 98
    elif code == 1596: res = 97
    elif code == 1597: res = 85
    elif code == 1598: res = 84
    elif code == 1599: res = 83
    elif 1622 <= code <= 1630: res = _charcode_to_pos_1622(code-1622)
    elif code == 1774: res = 78
    elif code == 1775: res = 106
    elif code == 1791: res = 94
    elif code == 1837: res = 6972
    elif code == 1838: res = 6973
    elif code == 1839: res = 6974
    elif 1869 <= code <= 1919: res = _charcode_to_pos_1869(code-1869)
    elif 1984 <= code <= 2110: res = _charcode_to_pos_1984(code-1984)
    elif code == 2304: res = 2296
    elif code == 2308: res = 2287
    elif 2382 <= code <= 2389: res = _charcode_to_pos_2382(code-2382)
    elif 2417 <= code <= 2431: res = _charcode_to_pos_2417(code-2417)
    elif code == 2493: res = 421
    elif code == 2510: res = 420
    elif 2555 <= code <= 2563: res = _charcode_to_pos_2555(code-2555)
    elif code == 2641: res = 3969
    elif code == 2677: res = 3970
    elif code == 2700: res = 3966
    elif code == 2785: res = 3967
    elif code == 2786: res = 3964
    elif code == 2787: res = 3965
    elif code == 2801: res = 3963
    elif code == 2869: res = 6256
    elif code == 2884: res = 6260
    elif code == 2914: res = 6258
    elif code == 2915: res = 6259
    elif code == 2929: res = 6257
    elif code == 2998: res = 7244
    elif code == 3024: res = 7516
    elif code == 3046: res = 7243
    elif 3059 <= code <= 3066: res = _charcode_to_pos_3059(code-3059)
    elif code == 3133: res = 7526
    elif code == 3160: res = 7525
    elif code == 3161: res = 7524
    elif code == 3170: res = 7528
    elif code == 3171: res = 7529
    elif 3192 <= code <= 3199: res = _charcode_to_pos_3192(code-3192)
    elif code == 3260: res = 4430
    elif code == 3261: res = 4433
    elif code == 3298: res = 4434
    elif code == 3299: res = 4435
    elif code == 3313: res = 4431
    elif code == 3314: res = 4432
    elif 3389 <= code <= 3396: res = _charcode_to_pos_3389(code-3389)
    elif code == 3426: res = 5530
    elif code == 3427: res = 5531
    elif 3440 <= code <= 3455: res = _charcode_to_pos_3440(code-3440)
    elif code == 3947: res = 7619
    elif code == 3948: res = 7620
    elif 4046 <= code <= 4056: res = _charcode_to_pos_4046(code-4046)
    elif 4130 <= code <= 4139: res = _charcode_to_pos_4130(code-4130)
    elif 4147 <= code <= 4159: res = _charcode_to_pos_4147(code-4147)
    elif 4186 <= code <= 4255: res = _charcode_to_pos_4186(code-4186)
    elif code == 4345: res = 3657
    elif code == 4346: res = 3658
    elif code == 4348: res = 5764
    elif code == 4442: res = 4005
    elif code == 4443: res = 3977
    elif code == 4444: res = 3978
    elif code == 4445: res = 3979
    elif code == 4446: res = 3999
    elif code == 4515: res = 4063
    elif code == 4516: res = 4088
    elif code == 4517: res = 4087
    elif code == 4518: res = 4076
    elif code == 4519: res = 4077
    elif code == 4602: res = 4009
    elif code == 4603: res = 4011
    elif code == 4604: res = 4008
    elif code == 4605: res = 4010
    elif code == 4606: res = 4012
    elif code == 4607: res = 4045
    elif code == 4615: res = 3608
    elif code == 4679: res = 3573
    elif code == 4743: res = 3581
    elif code == 4783: res = 3565
    elif code == 4815: res = 3612
    elif code == 4847: res = 3613
    elif code == 4879: res = 3557
    elif code == 4895: res = 3545
    elif code == 4935: res = 3606
    elif code == 4959: res = 3633
    elif code == 4960: res = 3622
    elif 4992 <= code <= 5017: res = _charcode_to_pos_4992(code-4992)
    elif code == 5120: res = 560
    elif 5751 <= code <= 5759: res = _charcode_to_pos_5751(code-5751)
    elif code == 6109: res = 4630
    elif 6128 <= code <= 6137: res = _charcode_to_pos_6128(code-6128)
    elif 6314 <= code <= 6389: res = _charcode_to_pos_6314(code-6314)
    elif 6400 <= code <= 6516: res = _charcode_to_pos_6400(code-6400)
    elif 6528 <= code <= 6829: res = _charcode_to_pos_6528(code-6528)
    elif 6912 <= code <= 7097: res = _charcode_to_pos_6912(code-6912)
    elif 7168 <= code <= 7295: res = _charcode_to_pos_7168(code-7168)
    elif 7376 <= code <= 7410: res = _charcode_to_pos_7376(code-7376)
    elif 7424 <= code <= 7654: res = _charcode_to_pos_7424(code-7424)
    elif code == 7677: res = 871
    elif code == 7678: res = 966
    elif code == 7679: res = 977
    elif code == 7836: res = 4869
    elif code == 7837: res = 4868
    elif code == 7838: res = 4717
    elif code == 7839: res = 4814
    elif code == 7930: res = 4693
    elif code == 7931: res = 4874
    elif code == 7932: res = 4694
    elif code == 7933: res = 4875
    elif code == 7934: res = 4748
    elif code == 7935: res = 4962
    elif 8275 <= code <= 8292: res = _charcode_to_pos_8275(code-8275)
    elif code == 8336: res = 4970
    elif code == 8337: res = 4971
    elif code == 8338: res = 4974
    elif code == 8339: res = 4978
    elif code == 8340: res = 4969
    elif 8370 <= code <= 8376: res = _charcode_to_pos_8370(code-8370)
    elif code == 8427: res = 971
    elif code == 8428: res = 983
    elif code == 8429: res = 970
    elif code == 8430: res = 968
    elif code == 8431: res = 981
    elif code == 8432: res = 869
    elif code == 8507: res = 3637
    elif code == 8508: res = 2440
    elif 8524 <= code <= 8530: res = _charcode_to_pos_8524(code-8524)
    elif code == 8580: res = 4907
    elif code == 8581: res = 6560
    elif code == 8582: res = 6558
    elif code == 8583: res = 6557
    elif code == 8584: res = 6559
    elif code == 8585: res = 8331
    elif 9167 <= code <= 9192: res = _charcode_to_pos_9167(code-9167)
    elif code == 9471: res = 5883
    elif code == 9748: res = 7742
    elif code == 9749: res = 4173
    elif code == 9752: res = 6746
    elif code == 9854: res = 6335
    elif code == 9855: res = 8335
    elif 9866 <= code <= 9983: res = _charcode_to_pos_9866(code-9866)
    elif code == 10071: res = 4094
    elif 10176 <= code <= 10188: res = _charcode_to_pos_10176(code-10176)
    elif code == 10220: res = 5542
    elif code == 10221: res = 5544
    elif code == 10222: res = 5541
    elif code == 10223: res = 5543
    elif 11008 <= code <= 11097: res = _charcode_to_pos_11008(code-11008)
    elif 11264 <= code <= 11505: res = _charcode_to_pos_11264(code-11264)
    elif 11513 <= code <= 11557: res = _charcode_to_pos_11513(code-11513)
    elif 11568 <= code <= 11621: res = _charcode_to_pos_11568(code-11568)
    elif code == 11631: res = 7682
    elif 11648 <= code <= 11670: res = _charcode_to_pos_11648(code-11648)
    elif 11680 <= code <= 11825: res = _charcode_to_pos_11680(code-11680)
    elif code == 12589: res = 451
    elif 12736 <= code <= 12771: res = _charcode_to_pos_12736(code-12736)
    elif code == 12829: res = 6305
    elif code == 12830: res = 6304
    elif 12868 <= code <= 12880: res = _charcode_to_pos_12868(code-12868)
    elif code == 12924: res = 710
    elif code == 12925: res = 711
    elif code == 12926: res = 720
    elif code == 13004: res = 6813
    elif code == 13005: res = 6809
    elif code == 13006: res = 6810
    elif code == 13007: res = 5153
    elif code == 13175: res = 6805
    elif code == 13176: res = 6806
    elif code == 13177: res = 6807
    elif code == 13178: res = 6819
    elif code == 13278: res = 6804
    elif code == 13279: res = 6803
    elif code == 13311: res = 6818
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
    elif code == 43739: res = 7195
    elif code == 43740: res = 7198
    elif code == 43741: res = 7197
    elif code == 43742: res = 7196
    elif code == 43743: res = 7194
    elif 43968 <= code <= 44025: res = _charcode_to_pos_43968(code-43968)
    elif 55216 <= code <= 55291: res = _charcode_to_pos_55216(code-55216)
    elif 64107 <= code <= 64217: res = _charcode_to_pos_64107(code-64107)
    elif code == 65021: res = 117
    elif 65040 <= code <= 65049: res = _charcode_to_pos_65040(code-65040)
    elif code == 65060: res = 972
    elif code == 65061: res = 973
    elif code == 65062: res = 872
    elif code == 65095: res = 6474
    elif code == 65096: res = 6476
    elif 65536 <= code <= 65629: res = _charcode_to_pos_65536(code-65536)
    elif 65664 <= code <= 65947: res = _charcode_to_pos_65664(code-65664)
    elif 66000 <= code <= 66045: res = _charcode_to_pos_66000(code-66000)
    elif 66176 <= code <= 66256: res = _charcode_to_pos_66176(code-66176)
    elif 66432 <= code <= 66517: res = _charcode_to_pos_66432(code-66432)
    elif code == 66598: res = 2278
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
    elif code == 74864: res = 1239
    elif code == 74865: res = 1238
    elif code == 74866: res = 1237
    elif code == 74867: res = 1236
    elif 77824 <= code <= 78894: res = _charcode_to_pos_77824(code-77824)
    elif code == 119081: res = 5880
    elif 119296 <= code <= 119365: res = _charcode_to_pos_119296(code-119296)
    elif 119552 <= code <= 119638: res = _charcode_to_pos_119552(code-119552)
    elif 119648 <= code <= 119665: res = _charcode_to_pos_119648(code-119648)
    elif code == 120001: res = 5545
    elif code == 120484: res = 5539
    elif code == 120485: res = 5540
    elif code == 120778: res = 5537
    elif code == 120779: res = 5538
    elif 126976 <= code <= 127123: res = _charcode_to_pos_126976(code-126976)
    elif 127232 <= code <= 127281: res = _charcode_to_pos_127232(code-127232)
    elif 127293 <= code <= 127310: res = _charcode_to_pos_127293(code-127293)
    elif code == 127319: res = 5881
    elif code == 127327: res = 5882
    elif 127353 <= code <= 127359: res = _charcode_to_pos_127353(code-127353)
    elif 127370 <= code <= 127376: res = _charcode_to_pos_127370(code-127370)
    elif code == 127488: res = 6812
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

