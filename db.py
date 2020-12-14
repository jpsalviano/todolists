import psycopg2
from psycopg2.extras import NamedTupleCursor


conn = psycopg2.connect(dbname="todolists", user="postgres", 
                        password="todolists", host="localhost",
                        cursor_factory=NamedTupleCursor)