from falcon import testing


class TestEmailVerification(testing.TestCase):
    def setUp(self):
        super().setUp()
        self.app = app.create()
        self.templates_env = Environment(
                             loader=FileSystemLoader('todolists/templates'),
                             autoescape=True,
                             trim_blocks=True,
                             lstrip_blocks=True)