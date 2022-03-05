## Required Postgresql tables

```sql
CREATE TABLE stations (
	id SERIAL PRIMARY KEY,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	lat REAL NOT NULL,
	lon REAL NOT NULL,
	name TEXT UNIQUE,
	description TEXT
);
```

### New station manual insertion
Requires application restart
```sql
INSERT INTO stations(lat, lon, name, description)
values(55.47, 37.32, 'Moscow', 'Moscow Neutron Monitor');
INSERT INTO stations(lat, lon, name, description)
values(61.59, 129.41, 'Yakutsk', 'Yakutsk station');
INSERT INTO stations(lat, lon, name, description)
values(35.2, 137.0, 'Nagoya', 'Nagoya muon telescope');

```
