# db = {
#     'user': 'root',
#     'password': 'rlawjdgns',
#     'host': 'localhost',
#     'port': 3306,
#     'database': 'miniter',
# }
db = {
    'user': 'root',
    'password': 'rlawjdgns',
    'host': 'localhost',
    'port': 3306,
    'database': 'miniter',
}

DB_URL = (
    f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:{db['port']}/"
    f"{db['database']}?charset=utf8"
)
JWT_SECRET_KEY = 'difficult secret key'
JWT_EXP_DELTA_SECONDS = 7 * 24 * 60 * 60
UPLOAD_DIRECTORY = './profile_pictures'

test_db = {
    'user': 'root',
    'password': 'rlawjdgns',
    'host': 'localhost',
    'port': 3306,
    'database': 'miniter_test',
}
test_config = {
    'DB_URL' : (
        f"mysql+mysqlconnector://{test_db['user']}:{test_db['password']}"
        f"@{test_db['host']}:{test_db['port']}/{test_db['database']}?charset=utf8"
    ),
    'JWT_SECRET_KEY': 'some dificult secret key'
}
            
