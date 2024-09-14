# pytest-opentelemetry-exporter

To merge the resulting databases, use:

```bash
sqlite3 merged_traces.sqlite3 ".databases"
for db in otel_test_traces/traces_*.sqlite3; do
    sqlite3 $db .dump | sqlite3 merged_traces.sqlite3
done
```
