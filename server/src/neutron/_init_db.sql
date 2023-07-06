CREATE SCHEMA IF NOT EXISTS neutron;
CREATE SCHEMA IF NOT EXISTS nm;

CREATE TABLE IF NOT EXISTS neutron.stations (
	id TEXT PRIMARY KEY,
	provides_1min BOOLEAN NOT NULL DEFAULT true,
	prefer_nmdb BOOLEAN NOT NULL DEFAULT true,
	closed_at TIMESTAMPTZ,

	drift_longitude REAL
);

CREATE TABLE IF NOT EXISTS neutron.result (
	time TIMESTAMPTZ PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS neutron.integrity_state (
	id INT PRIMARY KEY,
	full_from TIMESTAMPTZ,
	full_to TIMESTAMPTZ,
	partial_from TIMESTAMPTZ,
	partial_to TIMESTAMPTZ,
);
INSERT INTO neutron.integrity_state(id) VALUES(1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS neutron.obtain_log (
	id SERIAL PRIMARY KEY,
	time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
	stations TEXT[],
	source TEXT NOT NULL,
	interval_start TIMESTAMPTZ NOT NULL,
	interval_end TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS neutron.revision_log (
	id SERIAL PRIMARY KEY,
	time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
	author TEXT,
	comment TEXT,
	change_count INTEGER NOT NULL,
	interval_start TIMESTAMPTZ NOT NULL,
	interval_end TIMESTAMPTZ NOT NULL,
	is_reverted BOOLEAN NOT NULL DEFAULT false
);

INSERT INTO neutron.stations(id, drift_longitude, closed_at) VALUES
('APTY',  73.05, NULL),
('CALG', 270.9,  NULL),
('CAPS', 213.5, '2014-11-01'),
('DRBS',  65.17, NULL),
('FSMT', 293.07, NULL),
('GSBY', 338.6, '2000-01-01'),
('INVK', 234.85, NULL),
('IRKT', 163.58, NULL),
('KERG',  89.71, NULL),
('KIEL2', 65.34, NULL),
('KGSN', 197.30, '2016-11-01'),
('LARC', 356.00, '2008-08-01'),
('MGDN', 196.00, '2018-02-01'),
('NAIN',  18.32, NULL),
('NEWK', 331.49, NULL),
('NRLK', 124.48, NULL),
('NVBK', 136.0,  NULL),
('OULU',  67.42, NULL),
('PWNK', 349.56, NULL),
('SNAE', 17.2,   NULL),
('TXBY', 161.9,  NULL),
('YKTK', 174.02, NULL)
ON CONFLICT(id) DO NOTHING;