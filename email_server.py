from smtplib import SMTP


def get_credentials():
    credentials = open("todolists/EMAIL_", "r")
    return credentials.read().split("\n")

def connect_server():
    credentials = get_credentials()
    server = SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(credentials[0], credentials[1])
    return server

def send_mail(to_email, email_message):
    server = connect_server()
    server.sendmail("TodoLists", to_email, email_message)
    server.quit()


class SendingEmailError(Exception):
    def __init__(self, message):
        self.message = message