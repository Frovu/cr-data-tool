# dependencies

`pip install Flask flask-session flask-bcrypt "psycopg[binary,pool]" pymysql numpy scipy`

# database 

```
CREATE DATABASE crdt;
CREATE USER crdt;
ALTER DATABASE crdt OWNER TO crdt;
ALTER DATABASE crdt SET timezone TO 'UTC';
ALTER ROLE crdt SET timezone TO 'UTC';
```