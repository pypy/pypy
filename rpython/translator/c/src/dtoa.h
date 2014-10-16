/* Exported functions from dtoa.c */

double _PyPy_dg_strtod(const char *str, char **ptr);
char * _PyPy_dg_dtoa(double d, int mode, int ndigits,
		     int *decpt, int *sign, char **rve);
void _PyPy_dg_freedtoa(char *s);

