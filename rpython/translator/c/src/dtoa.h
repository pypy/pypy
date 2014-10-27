/* Exported functions from dtoa.c */

RPY_EXPORTED_FOR_TESTS
double _PyPy_dg_strtod(const char *str, char **ptr);

RPY_EXPORTED_FOR_TESTS
char * _PyPy_dg_dtoa(double d, int mode, int ndigits,
		     int *decpt, int *sign, char **rve);

RPY_EXPORTED_FOR_TESTS
void _PyPy_dg_freedtoa(char *s);
