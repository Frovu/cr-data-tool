## Required tables

```sql
CREATE TABLE IF NOT EXISTS muon_stations (
	id SERIAL PRIMARY KEY,
	name TEXT UNIQUE,
	lat NUMERIC,
	lon NUMERIC,
	since TIMESTAMP,
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
INSERT INTO muon_stations(lat, lon, name, since, elevation_m) VALUES
(55.47, 37.32, 'Moscow-pioneer', '2020-08-26', 190),
(55.47, 37.32, 'Moscow-CUBE', '2007-10-23', 190),
(55.47, 37.32, 'Moscow-CARPET', '2019-01-01', 190),
(67.57, 33.39, 'Apatity', '2020-11-26', 181),
(78.06, 14.22, 'Barentsburg', '2021-10-03', 70),
(35.2, 137.0, 'Nagoya', '1986-04-22', 77),
(61.59, 129.41, 'Yakutsk', '1972-01-01', 95),
(61.59, 129.41, 'Yakutsk_00', '2008-01-01', 95),
(61.59, 129.41, 'Yakutsk_07', '2009-01-01', 95),
(61.59, 129.41, 'Yakutsk_20', '2009-01-01', 95),
(61.59, 129.41, 'Yakutsk_40', '2009-01-01', 95)
ON CONFLICT(name) DO NOTHING;
INSERT INTO muon_channels(station_name, channel_name, dir_vertical, dir_azimuthal) VALUES
('Moscow-pioneer', 'V' , 0, 0),
('Moscow-CARPET', 'V' , 0, 0),
('Moscow-CUBE', 'V' , 0, 0),
('Apatity', 'V' , 0, 0),
('Barentsburg', 'V' , 0, 0),
('Yakutsk', 'V' , 0, 0),
('Yakutsk', 'N' , 30, 0),
('Yakutsk', 'S' , 30, 180),
('Yakutsk', 'N2' , 60, 0),
('Yakutsk', 'S2' , 60, 180),
('Yakutsk_00', 'V' , 0, 0),
('Yakutsk_00', 'N30' , 30, 0),
('Yakutsk_00', 'S30' , 30, 180),
('Yakutsk_00', 'N60' , 60, 0),
('Yakutsk_00', 'S60' , 60, 180),
('Yakutsk_07', 'V' , 0, 0),
('Yakutsk_07', 'N30' , 30, 0),
('Yakutsk_07', 'S30' , 30, 180),
('Yakutsk_07', 'N60' , 60, 0),
('Yakutsk_07', 'S60' , 60, 180),
('Yakutsk_20', 'V' , 0, 0),
('Yakutsk_20', 'N30' , 30, 0),
('Yakutsk_20', 'S30' , 30, 180),
('Yakutsk_20', 'N60' , 60, 0),
('Yakutsk_20', 'S60' , 60, 180),
('Yakutsk_40', 'V' , 0, 0),
('Yakutsk_40', 'N30' , 30, 0),
('Yakutsk_40', 'S30' , 30, 180),
('Yakutsk_40', 'N60' , 60, 0),
('Yakutsk_40', 'S60' , 60, 180),
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
