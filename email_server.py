from smtplib import SMTP


def get_credentials():
    credentials = open("todolists/EMAIL_", "r")
    return credentials.read().split("\n")

def connect_server():
    credentials = get_credentials()
    server_connection = SMTP('smtp.gmail.com', 587)
    server_connection.starttls()
    server_connection.login(credentials[0], credentials[1])
    return server_connection

def send_mail(to_email, email_message, server_connection):
    server_connection.sendmail("TodoLists", to_email, email_message)
    server_connection.quit()


class SendingEmailError(Exception):
    def __init__(self, message):
        self.message = message