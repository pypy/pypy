#pragma once


#include "config.h"
#include <stdint.h>

#define QCGC_GRAY_FLAG (1<<0)
#define QCGC_PREBUILT_OBJECT (1<<1)
#define QCGC_PREBUILT_REGISTERED (1<<2)
#define QCGC_FIRST_AVAILABLE_FLAG (1<<3)	// The first flag clients may use

typedef struct object_s {
	uint32_t flags;
} object_t;
