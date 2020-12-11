import falcon


class UserRegistration:
    def on_get(self, req, resp):
        pass

    def on_post(self, req, resp):
        try:
            validate_user_info(req.params)
            resp.media = req.params
        except ValidationError as err:
            resp.body = err


class ValidationError(Exception):
    def __init__(self, message):
        self.message = message


def validate_username(username):
    if len(username) not in range(6, 31):
        raise ValidationError("Username must be 6-30 characters long.")
    for char in username:
        if not char.isalnum():
            raise ValidationError("Username must contain letters and numbers only.")

def validate_password(password_1, password_2):
    if password_1 != password_2:
        raise ValidationError("Passwords do not match!")
    if len(password_1) not in range(6, 31):
        raise ValidationError("Password must be 6-30 characters long.")

def validate_user_info(user_info_dict):
    validate_username(user_info_dict["username"])
    validate_password(user_info_dict["password_1"], user_info_dict["password_2"])

def create():
    app = falcon.API()
    app.add_route("/register", UserRegistration())
    return app

app = create()