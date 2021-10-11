## Required tables

```sql
CREATE TABLE stations (
	name TEXT,
	lat NUMERIC,
	lon NUMERIC
);

INSERT INTO stations(lat, lon, name)
values(55.47, 37.32, 'Moscow');
INSERT INTO stations(lat, lon, name)
values(61.59, 129.41, 'Yakutsk');
```
