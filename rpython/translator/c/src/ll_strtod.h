/* string <-> float conversions.
   Implementation uses sprintf and strtod.
   Not used in modern Python, where dtoa.c is preferred.
 */

#ifndef _PYPY_LL_STRTOD_H
#define _PYPY_LL_STRTOD_H

double LL_strtod_parts_to_float(char *sign, char *beforept,
				char *afterpt, char *exponent);
char *LL_strtod_formatd(double x, char code, int precision);

#endif
