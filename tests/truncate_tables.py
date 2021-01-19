from todolists import db

def truncate_tables():
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute("TRUNCATE users CASCADE")
            curs.execute("TRUNCATE tasks CASCADE")


truncate_tables()