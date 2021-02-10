import os

import psycopg2
from psycopg2.extras import NamedTupleCursor


conn = psycopg2.connect(dbname="todolists", user="postgres", 
                        password=os.environ["todolists_db_password"], host="localhost",
                        cursor_factory=NamedTupleCursor)
