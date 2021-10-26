## Install

- `pip install numpy scipy flask psycopg2 netCDF4 requests`

## Run

`export $(cat .env | xargs) && flask run`

## .env file template
```
NCEP_DB_NAME=
NCEP_DB_USER=
NCEP_DB_PASS=
NCEP_DB_HOST=localhost
```
