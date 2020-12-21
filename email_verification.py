from secrets import randbelow
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from todolists import app, redis_conn, email_server, db
from todolists.user_registration import ValidationError


def create_token():
        token = randbelow(1000000)
        return "{:06d}".format(token)

def save_token_to_redis(token, email):
    with redis_conn.conn as conn:
        conn.set(token, email)
        conn.expire(token, 600)

def build_email_message_sending_token_html_body(token):
    return app.templates_env.get_template("email_message_sending_code.html").render(token=token)

def build_email_message_sending_token(token, email):
    message = MIMEMultipart()
    message['Subject'] = "Finish your registration on TodoLists!"
    message['From'] = "TodoLists"
    message['To'] = email
    body = build_email_message_sending_token_html_body(token)
    message.attach(MIMEText(body, "html"))
    return message.as_string()

def send_email_with_token(email):
    token = create_token()
    save_token_to_redis(token, email)
    email_message = build_email_message_sending_token(token, email)
    server_connection = email_server.connect_server()
    email_server.send_mail(email, email_message, server_connection)

def get_email_by_token(token):
    with redis_conn.conn as conn:
        email = conn.get(token)
    if email:
        return email.decode()
    else:
        raise ValidationError("The code entered is either wrong or expired.")

def update_user_verified_in_db(email):
    with db.conn as conn:
        with conn.cursor() as curs:
            curs.execute(f"UPDATE users SET verified=true WHERE email=%s", (email,))