
void instrument_setup();

#ifdef INSTRUMENT

void instrument_count(long);

#ifndef PYPY_NOT_MAIN_FILE
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#ifndef WIN32
#include <sys/mman.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#else
#include <windows.h>
#endif

typedef unsigned long instrument_count_t;

instrument_count_t *_instrument_counters = NULL;

void instrument_setup() {
	char *fname = getenv("_INSTRUMENT_COUNTERS");
	if (fname) {
		int fd;
#ifdef WIN32
        HANDLE map_handle;
        HANDLE file_handle;
#endif
		void *buf;
		size_t sz = sizeof(instrument_count_t)*INSTRUMENT_NCOUNTER;
		fd = open(fname, O_CREAT|O_TRUNC|O_RDWR, 0744);
		if (sz > 0) {
			lseek(fd, sz-1, SEEK_SET);
			write(fd, "", 1);
#ifndef WIN32
			buf = mmap(NULL, sz, PROT_WRITE|PROT_READ, MAP_SHARED,
				   fd, 0);
			if (buf == MAP_FAILED) {
				fprintf(stderr, "mapping instrument counters file failed\n");
				abort();
			}
#else
            file_handle = (HANDLE)_get_osfhandle(fd);
            map_handle = CreateFileMapping(file_handle, NULL, PAGE_READWRITE,
                                           0, sz, "");
            buf = MapViewOfFile(map_handle, FILE_MAP_WRITE, 0, 0, 0);
			if (buf == 0) {
				fprintf(stderr, "mapping instrument counters file failed\n");
				abort();
			}
#endif
			_instrument_counters = (instrument_count_t *)buf;
		}
	}
}

void instrument_count(long label) {
	if(_instrument_counters) {
		_instrument_counters[label]++;
	}
}
#endif


#define INSTRUMENT_COUNT(label) instrument_count(label)

#else

#ifndef PYPY_NOT_MAIN_FILE
void instrument_setup() {
}
#endif

#define INSTRUMENT_COUNT

#endif
