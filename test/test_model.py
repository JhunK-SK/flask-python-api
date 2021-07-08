import bcrypt
import pytest
from sqlalchemy.sql.functions import user
import config

from model import UserDao, TweetDao
from sqlalchemy import create_engine, text

database = create_engine(config.test_config['DB_URL'], encoding='utf-8',
                         max_overflow=0)

@pytest.fixture
def user_dao():
    return UserDao(database)

@pytest.fixture
def tweet_dao():
    return TweetDao(database)

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
    
def test_insert_user(user_dao):
    new_user = {
        'name': 'new_user',
        'email': 'new_user@email.com',
        'profile': 'new user profile',
        'password': 'rlawjdgns'
    }
    
    new_user_id = user_dao.insert_user(new_user)
    user = get_user(new_user_id)
    
    assert user == {
        'id': new_user_id,
        'name': new_user['name'],
        'email': new_user['email'],
        'profile': new_user['profile'],
    }
    

def get_follow_list(user_id):
    rows = database.execute(text("""
        SELECT follow_user_id as id
        FROM users_follow_list
        WHERE user_id = :user_id
        """), {
            'user_id': user_id
        }).fetchall()
    
    return [int(row['id']) for row in rows]

def test_get_user_id_and_password(user_dao):
    ## get a user id and password(hashed) by using user_dao's method
    user_credential = user_dao.get_user_id_and_password(email='test1@email.com')
    
    # chceck user id and password
    assert user_credential['id'] == 1
    assert bcrypt.checkpw('test_password'.encode('UTF-8'),
                          user_credential['hashed_password'].encode('UTF-8'))
    

def test_insert_follow(user_dao):
    # make user 1 follow user 2 by using insert_follow method
    user_dao.insert_follow(user_id=1, follow_id=2)
    
    follow_list = get_follow_list(1)
    
    assert follow_list == [2]
    

def test_insert_unfollow(user_dao):
    # make user 1 follow user 2 by using insert_follow method
    # make user 1 unfollow user 2 by using insert_unfollow method
    user_dao.insert_follow(user_id=1, follow_id=2)
    user_dao.insert_unfollow(user_id=1, unfollow_id=2)
    
    follow_list = get_follow_list(1)
    assert follow_list == []
    
def test_insert_tweet(tweet_dao):
    tweet_dao.insert_tweet(1, 'test tweet')
    timeline = tweet_dao.get_timeline(1)
    
    assert timeline == [
        {
            'user_id': 1,
            'tweet': 'test tweet'
        }
    ]
    
def test_timeline(user_dao, tweet_dao):
    tweet_dao.insert_tweet(1, 'test_tweet 1')
    tweet_dao.insert_tweet(2, 'test_tweet 2')
    user_dao.insert_follow(1, 2)
    
    timeline = tweet_dao.get_timeline(1)
    
    assert timeline == [
        {
            'user_id': 2,
            'tweet': 'Hello World'
        },
        {
            'user_id': 1,
            'tweet': 'test_tweet 1'
        },
        {
            'user_id': 2,
            'tweet': 'test_tweet 2'
        }
    ]
    