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
INSERT INTO stations(lat, lon, name, description) VALUES
(55.47, 37.32, 'Moscow', 'Moscow Neutron Monitor'),
(61.59, 129.41, 'Yakutsk', 'Yakutsk station'),
(67.57, 33.39, 'Apatity', 'Apatity station'),
(78.06, 14.22, 'Barentsburg', 'Barentsburg station'),
(23.6 , 113.18, 'Guangzhou', 'Guangzhou station'),
(35.2, 137.0, 'Nagoya', 'Nagoya muon telescope')
ON CONFLICT(name) DO NOTHING;
```
