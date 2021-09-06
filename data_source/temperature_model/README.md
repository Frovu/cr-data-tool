## Psql tables

```sql
CREATE TABLE index (
	id SERIAL PRIMARY KEY,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP,
	lat REAL NOT NULL,
	lon REAL NOT NULL,
	name TEXT,
	description TEXT
);
```

### New station manual insertion
Requires application restart
```sql
INSERT INTO index(lat, lon, name, description)
values(55.47, 37.32, 'Moscow', 'Moscow Neutron Monitor');
```
