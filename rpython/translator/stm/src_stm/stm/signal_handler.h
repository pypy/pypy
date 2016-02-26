/* Imported by rpython/translator/stm/import_stmgc.py */
static void copy_bk_objs_in_page_from(int from_segnum, uintptr_t pagenum,
                                      bool only_if_not_modified);

static void handle_segfault_in_page(uintptr_t pagenum);


static void setup_signal_handler(void);
