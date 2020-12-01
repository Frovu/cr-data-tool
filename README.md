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
