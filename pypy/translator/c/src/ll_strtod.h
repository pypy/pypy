#include <locale.h>

double LL_strtod_parts_to_float(
	RPyString *sign, 
	RPyString *beforept, 
        RPyString *afterpt, 
        RPyString *exponent)
{
	char *fail_pos;
	struct lconv *locale_data;
        const char *decimal_point;
        int decimal_point_len;
        double x;
	char *last;
	char *expo = RPyString_AsString(exponent);

        if (*expo == '\0') {
		expo = "0";
        }

	locale_data = localeconv();
	decimal_point = locale_data->decimal_point;
	decimal_point_len = strlen(decimal_point);

	int buf_size = RPyString_Size(sign) + 
		RPyString_Size(beforept) +
		decimal_point_len +
		RPyString_Size(afterpt) +
		1 /* e */ +
		strlen(expo) + 
		1 /*  asciiz  */ ;

        char *s = malloc(buf_size);
        strcpy(s, RPyString_AsString(sign));
	strcat(s, RPyString_AsString(beforept));
	strcat(s, decimal_point);
	strcat(s, RPyString_AsString(afterpt));
	strcat(s, "e");
	strcat(s, expo);

        last = s + (buf_size-1);
        x = strtod(s, &fail_pos);
	errno = 0;
	free(s);
	if (fail_pos > last)
		fail_pos = last;
        if (fail_pos == s || *fail_pos != '\0' || fail_pos != last) {
		RPyRaiseSimpleException(PyExc_ValueError, "invalid float literal");
		return -1.0;
        }
        if (x == 0.0) { /* maybe a denormal value, ask for atof behavior */
		x = strtod(s, NULL);
		errno = 0;
        }
        return x;
}
