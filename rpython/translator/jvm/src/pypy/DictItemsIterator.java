package pypy;

import java.util.Map;
import java.util.Iterator;

public class DictItemsIterator
{
    private Iterator<Map.Entry> iterator;
    private Map.Entry current;

    public DictItemsIterator(Map map) {
        this.iterator = map.entrySet().iterator();
    }

    public boolean ll_go_next() {
        if (!this.iterator.hasNext())
            return false;
        this.current = this.iterator.next();
        return true;
    }

    public Object ll_current_key() {
        return this.current.getKey();
    }

    public Object ll_current_value() {
        return this.current.getValue();
    }
}