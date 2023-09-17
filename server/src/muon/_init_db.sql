CREATE SCHEMA IF NOT EXISTS muon;

CREATE TABLE IF NOT EXISTS muon.experiments (
	id SERIAL PRIMARY KEY,
	name TEXT NOT NULL UNIQUE,
	lat REAL NOT NULL,
	lon REAL NOT NULL,
	elevation_m REAL NOT NULL,
	operational_since timestamptz NOT NULL,
	operational_until timestamptz
);

CREATE TABLE IF NOT EXISTS muon.channels (
	id SERIAL PRIMARY KEY,
	channel_name TEXT NOT NULL,
	station_name TEXT NOT NULL REFERENCES muon.experiments.name ON DELETE CASCADE,
	angle_vertical REAL DEFAULT 0,
	angle_azimuthal REAL DEFAULT 0,
	coef_pressure REAL,
	coef_tm REAL,
	mean_pressure REAL,
	mean_tm REAL,
	coef_per_len INT,
	UNIQUE(station, name)
);

CREATE TABLE IF NOT EXISTS muon.conditions_data (
	station INTEGER NOT NULL REFERENCES muon.stations.id ON DELETE CASCADE
	time timestamptz NOT NULL,
	t_mass_average REAL,
	pressure REAL,
);

CREATE TABLE IF NOT EXISTS muon.counts_data (
	channel INTEGER NOT NULL REFERENCES muon.channels.id ON DELETE CASCADE
	time timestamptz NOT NULL,
	original REAL,
	corrected REAL,
	revised REAL,
);

INSERT INTO muon.experiments(lat, lon, elevation_m, name, operational_since) VALUES
(55.47, 37.32, 190, 'Moscow-pioneer', '2020-08-26'),
(55.47, 37.32, 190, 'Moscow-CUBE',    '2007-10-23'),
(67.57, 33.39, 181, 'Apatity',        '2020-11-26'),
(78.06, 14.22, 70,  'Barentsburg',    '2021-10-03'),
ON CONFLICT(name) DO NOTHING;

INSERT INTO muon.channels(station_name, channel_name, angle_vertical, angle_azimuthal) VALUES
('Moscow-pioneer', 'V' , 0, 0),
('Moscow-CUBE', 'V' , 0, 0),
('Apatity', 'V' , 0, 0),
('Barentsburg', 'V' , 0, 0)
ON CONFLICT(station_name, channel_name) DO NOTHING;