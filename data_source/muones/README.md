## Required tables

```sql
CREATE TABLE IF NOT EXISTS muon_stations (
	id SERIAL PRIMARY KEY,
	name TEXT UNIQUE,
	lat NUMERIC,
	lon NUMERIC,
	elevation_m REAL,
	description TEXT
);
CREATE TABLE IF NOT EXISTS muon_channels (
	id SERIAL PRIMARY KEY,
	station_name TEXT NOT NULL,
	channel_name TEXT NOT NULL,
	dir_vertical REAL DEFAULT 0,
	dir_azimuthal REAL DEFAULT 0,
	coef_pressure REAL,
	coef_tm REAL,
	mean_pressure REAL,
	mean_tm REAL,
	coef_per_len INT,
	UNIQUE(station_name, channel_name)
);
INSERT INTO muon_stations(lat, lon, name, elevation_m) VALUES
(55.47, 37.32, 'Moscow', 190),
(67.57, 33.39, 'Apatity', 181),
(78.06, 14.22, 'Barentsburg', 70),
(35.2, 137.0, 'Nagoya', 77)
ON CONFLICT(name) DO NOTHING;
INSERT INTO muon_channels(station_name, channel_name, dir_vertical, dir_azimuthal) VALUES
('Moscow', 'V' , 0, 0),
('Apatity', 'V' , 0, 0),
('Barentsburg', 'V' , 0, 0),
('Nagoya', 'V' , 0, 0),
('Nagoya', 'NE', 39, 45),
('Nagoya', 'SE', 39, 135),
('Nagoya', 'NW', 39, 315),
('Nagoya', 'SW', 39, 225),
('Nagoya', 'N' , 30, 0),
('Nagoya', 'N2', 49, 0),
('Nagoya', 'N3', 64, 0),
('Nagoya', 'E' , 30, 90),
('Nagoya', 'E2', 49, 90),
('Nagoya', 'E3', 64, 90),
('Nagoya', 'S' , 30, 180),
('Nagoya', 'S2', 49, 180),
('Nagoya', 'S3', 64, 180),
('Nagoya', 'W' , 30, 270),
('Nagoya', 'W2', 49, 270),
('Nagoya', 'W3', 64, 270)
ON CONFLICT(station_name, channel_name) DO NOTHING;

```
