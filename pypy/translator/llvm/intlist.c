#include <stdio.h>

struct list_int {
    unsigned int length;
    int* data;
};

struct list_int* range(int length) {
    int i = 0;
    if (length <= 0) {
	struct list_int* nlist = malloc(sizeof(struct list_int));
	nlist->length = 0;
	nlist->data = NULL;
	return nlist;
    }
    struct list_int* nlist = malloc(sizeof(struct list_int));
    nlist->length = length;
    nlist->data = malloc(sizeof(int) * length);
    while (i < length) {
	nlist->data[i] = i;
	i += 1;
    }
    return nlist;
}

