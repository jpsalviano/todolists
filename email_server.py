from smtplib import SMTP


def get_info():
    info = open("todolists/EMAIL_", "r")
    return info.read().split("\n")

def connect_server():
    try:
        info = get_info()
        server = SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(info[0], info[1])
        return True
    except:
        return False

def send_mail(to_email, email_message):
    server.sendmail(info[0], to_email, email_message)
    server.quit()