#include <stdio.h>

struct item {
    char* dummy;
};

struct list {
    unsigned int length;
    struct item** data;
};

void copy(struct item** from, struct item** to, unsigned int length) {
    unsigned int i = 0;
    while(i < length) {
	to[i] = from[i];
	i += 1;
    }
}

int len(struct list* l) {
    return (int) l->length;
}

struct list* newlist() {
    struct list* nlist = malloc(sizeof(struct list));
    nlist->length = 0;
    nlist->data = NULL;
    return nlist;
}

struct list* newlist_ALTERNATIVE1(struct item* value) {
    struct list* nlist = malloc(sizeof(struct list));
    nlist->length = 1;
    nlist->data = malloc(sizeof(struct item*));
    nlist->data[0] = value;
    return nlist;
}

struct list* newlist_ALTERNATIVE2(struct item* v1, struct item* v2) {
    struct list* nlist = malloc(sizeof(struct list));
    nlist->length = 2;
    nlist->data = malloc(sizeof(struct item*) * 2);
    nlist->data[0] = v1;
    nlist->data[1] = v2;
    return nlist;
}
struct list* newlist_ALTERNATIVE3(struct item* v1, struct item* v2,
				  struct item* v3) {
    struct list* nlist = malloc(sizeof(struct list));
    nlist->length = 3;
    nlist->data = malloc(sizeof(struct item*) * 3);
    nlist->data[0] = v1;
    nlist->data[1] = v2;
    nlist->data[2] = v3;
    return nlist;
}

struct list* alloc_and_set(int length, struct item* init) {
    unsigned int i = 0;
    struct list* nlist = malloc(sizeof(struct list));
    nlist->length = (unsigned int)length;
    nlist->data = malloc(sizeof(struct item*) * length);
    while (i < length) {
	nlist->data[i] = init;
	i += 1;
    }
    return nlist;
}

struct item* getitem(struct list* l, int index) {
    if (index < 0)
	index = l->length + index;
    return l->data[index];
}

void setitem(struct list* l, int index, struct item* value) {
    if (index < 0)
	index = l->length + index;
    l->data[index] = value;
}

struct list* add(struct list* a, struct list* b) {
    struct list* nlist = malloc(sizeof(struct list));
    unsigned int newlength = a->length + b->length;
    nlist->length = newlength;
    nlist->data = malloc(sizeof(struct item*) * newlength);
    copy(a->data, nlist->data, a->length);
    copy(b->data, nlist->data + a->length, newlength - a->length);
    return nlist;
}

struct list* mul(struct list* a, int times) {
    struct list* nlist = malloc(sizeof(struct list));
    unsigned int newlength = a->length * times;
    int i = 0;
    nlist->length = newlength;
    nlist->data = malloc(sizeof(struct item*) * newlength);
    while (i < times) {
	copy(a->data, nlist->data + i * a->length, a->length);
	i += 1;
    }
    return nlist;
}

void inplace_add(struct list* a, struct list* b) {
    struct item** newdata = malloc(sizeof(struct item*) * (a->length + b->length));
    copy(a->data, newdata, a->length);
    copy(b->data, newdata + a->length, b->length);
    a->length +=  b->length;
    free(a->data);
    a->data = newdata;
}

void append(struct list* a, struct item* value) {
    struct item** newdata = malloc(sizeof(struct item*) * (a->length + 1));
    newdata[a->length] = value;
    copy(a->data, newdata, a->length);
    a->length += 1;
    free(a->data);
    a->data = newdata;
}

void reverse(struct list* a) {
    unsigned int lo = 0;
    unsigned int hi = a->length - 1;
    struct item* temp;
    while (lo < hi) {
	temp = a->data[lo];	    
	a->data[lo] = a->data[hi];
	a->data[hi] = temp;
	lo += 1;
	hi -= 1;
    }
}


