from model import UserModel, Schema
class NewUserService:
    def __init__(self):
        self.model = UserModel()

    def createNewUser(self, params):
        return self.model.create(params)
