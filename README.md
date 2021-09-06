## Install

- `pip install flask`
- `pip install numpy`
- `pip install scipy`
- `pip install psycopg2`
- `pip install netCDF4`
- `pip install progressbar2`

## Run

`export $(cat .env | xargs) && flask run`

## .env file template
```
NCEP_DB_NAME=
NCEP_DB_USER=
NCEP_DB_PASS=
NCEP_DB_HOST=localhost
```
