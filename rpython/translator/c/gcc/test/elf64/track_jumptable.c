#include <stdio.h>

int foobar(int n) {
	switch(n) {
		case 0:
			return 1;
		case 1:
			return 12;
		case 2:
			return 123;
		case 3:
			return 1234;
		case 4:
			return 12345;
		default:
			return 42;
	}
}
