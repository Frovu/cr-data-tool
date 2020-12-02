## Install

- `pip install numpy`
- `pip install psycopg2`
- `pip install netCDF4`

## Run

`export $(cat .env | xargs) && python3 server.py`

## .env file template
```
DB_NAME=ncep_temp
DB_USER=ncep_temp
DB_PASS=1n2c3e4p
DB_HOST=localhost
```

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
