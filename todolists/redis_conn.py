import redis

session_conn = redis.Redis(host='localhost', port=6379, db=0)

conn = redis.Redis(host='localhost', port=6379, db=1)