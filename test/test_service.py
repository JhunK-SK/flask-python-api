import bcrypt
import config
import jwt
import pytest
from model import TweetDao, UserDao
from service import TweetService, UserService
from sqlalchemy import create_engine, text

database = create_engine(config.test_config['DB_URL'], encoding='utf-8',
                         max_overflow=0)

@pytest.fixture
def user_service():
    return UserService(UserDao(database), config.test_config)

@pytest.fixture
def tweet_service():
    return TweetService(TweetDao(database))

def setup_function():
    ## Create a test user
    hashed_password = bcrypt.hashpw(b"test_password", bcrypt.gensalt())
    new_users = [
        {
            'id': 1,
            'name': 'testName1',
            'email': 'test1@email.com',
            'profile': 'test1 profile',
            'hashed_password': hashed_password
        },
        {
            'id': 2,
            'name': 'testName2',
            'email': 'test2@email.com',
            'profile': 'test2 profile',
            'hashed_password': hashed_password
        },
    ]

    database.execute(text("""
        INSERT INTO users (
            id,
            name,
            email,
            profile,
            hashed_password
        ) VALUES (
            :id,
            :name,
            :email,
            :profile,
            :hashed_password
        )
        """), new_users)
    
    ## create tweet of test user 2
    database.execute(text("""
        INSERT INTO tweets (
            user_id,
            tweet
        ) VALUES (
            2,
            "Hello World"
        )
        """))
    
def teardown_function():
    database.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    database.execute(text("TRUNCATE users"))
    database.execute(text("TRUNCATE tweets"))
    database.execute(text("TRUNCATE users_follow_list"))
    database.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    
def get_user(user_id):
    row = database.execute(text("""
        SELECT
            id,
            name,
            email,
            profile
        FROM users
        WHERE id = :user_id
    """), {
        'user_id': user_id
    }).fetchone()
    
    return {
        'id': row['id'],
        'name': row['name'],
        'email': row['email'],
        'profile': row['profile']
    } if row else None
    
def get_follow_list(user_id):
    rows = database.execute(text("""
        SELECT follow_user_id as id
        FROM users_follow_list
        WHERE user_id = :user_id
        """), {
            'user_id': user_id
        }).fetchall()
    
    return [int(row['id']) for row in rows]    

def test_create_new_user(user_service):
    new_user = {
        'name': 'new_user',
        'email': 'new_user@email.com',
        'profile': 'new user profile',
        'password': 'rlawjdgns'
    }
    
    new_user_id = user_service.create_new_user(new_user)
    created_user = get_user(new_user_id)
    
    assert created_user == {
        'id': new_user_id,
        'name': new_user['name'],
        'email': new_user['email'],
        'profile': new_user['profile'],
    }

def test_login(user_service):
    assert user_service.login({
        'email': 'test1@email.com',
        'password': 'test_password'
    })
    
    # check if it returns False, when logging in with wrong password.
    assert not user_service.login({
        'email': 'test1@email.com',
        'password': 'wrong_password'
    })
    
def test_generate_access_token(user_service):
    # check if the user_id is the same as the decoded token's user_id
    token = user_service.generate_access_token(1)
    payload = jwt.decode(token, config.test_config['JWT_SECRET_KEY'], 'HS256')
    
    assert payload['user_id'] == 1
    
def test_follow(user_service):
    user_service.follow(1, 2)
    follow_list = get_follow_list(1)
    
    assert follow_list == [2]
    
def test_unfollow(user_service):
    user_service.follow(1, 2)
    user_service.unfollow(1, 2)
    follow_list = get_follow_list(1)
    
    assert follow_list == []
    
def test_tweet(tweet_service):
    tweet_service.tweet(1, 'test tweet')
    timeline = tweet_service.timeline(1)
    
    assert timeline == [
        {
            'user_id': 1,
            'tweet': 'test tweet'
        }
    ]

def test_timeline(user_service, tweet_service):
    tweet_service.tweet(1, 'test tweet 1')
    tweet_service.tweet(2, 'test tweet 2')
    user_service.follow(1, 2)
    
    timeline = tweet_service.timeline(1)
    
    assert timeline == [
        {
            'user_id': 2,
            'tweet': 'Hello World'
        },
        {
            'user_id': 1,
            'tweet': 'test tweet 1'
        },
        {
            'user_id': 2,
            'tweet': 'test tweet 2'
        }
    ]
