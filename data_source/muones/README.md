## Required tables

```sql
CREATE TABLE muon_stations (
	name TEXT PRIMARY KEY,
	lat NUMERIC,
	lon NUMERIC,
	description TEXT
);
CREATE TABLE muon_telescopes (
	station_name TEXT NOT NULL,
	channel_name TEXT NOT NULL,
	elevation_m REAL,
	dir_vertical REAL DEFAULT 0,
	dir_azimuthal REAL DEFAULT 0,
	coef_pressure REAL,
	coef_tm REAL,
	UNIQUE(station_name, channel)
);

INSERT INTO stations(lat, lon, name) VALUES
(55.47, 37.32, 'Moscow'),
(61.59, 129.41, 'Yakutsk'),
(35.2, 137.0, 'Nagoya');
INSERT INTO channels(station_name, channel_name) VALUES
('Moscow', 'V'),
('Yakutsk', 'V'),
('Nagoya', 'V');

```
