import sqlite3

class Schema:
    def __init__(self):
        self.conn = sqlite3.connect('users.db')
        self.create_user_table()
    def create_user_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS "Users" (
        _id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Email TEXT,
        Birthday Date,
        Password TEXT
        );
        """
        self.conn.execute(query)
class UserModel:
    TABLENAME = "Users"
    def __init__(self):
        self.conn = sqlite3.connect('users.db')
        self.conn.row_factory = sqlite3.Row

    def create(self, params):
        print(params)
        print(type(params))
        #assume these are all mandatory fields for now
        # name     = kwargs.get("Name")
        # email    = kwargs.get("Email")
        # birthday = kwargs.get("Birthday")
        # password = kwargs.get("Password")

        query = f'insert into {self.TABLENAME} ' \
                f'(Name, Email, Birthday, Password) ' \
                f'values ("{params.get("Name")}","{params.get("Email")}","{params.get("Birthday")}","{params.get("Password")}")'
        result = self.conn.execute(query)
        return self.get_by_id(result.lastrowid)
    
    def get_by_id(self, _id):
        where_clause = f"AND id={_id}"
        return self.list_items(where_clause)
    
    def list_items(self, where_clause=""):
        query = f"SELECT id, Name, Email, Birthday, Password " \
                f"from {self.TABLENAME} WHERE _is_deleted != {1} " + where_clause
        print (query)
        result_set = self.conn.execute(query).fetchall()
        result = [{column: row[i]
                  for i, column in enumerate(result_set[0].keys())}
                  for row in result_set]
        return result
                
