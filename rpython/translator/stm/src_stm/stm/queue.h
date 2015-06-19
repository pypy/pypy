/* Imported by rpython/translator/stm/import_stmgc.py */
static void queues_deactivate_all(bool at_commit);
static void collect_active_queues(void);           /* minor collections */
static void mark_visit_from_active_queues(void);   /* major collections */
