import json
import config
import pytest
import bcrypt
from sqlalchemy import create_engine, text
from app import create_app, CustomJsonEncoder
database = create_engine(config.test_config['DB_URL'], encoding='utf-8', max_overflow=0)


@pytest.fixture
def api():
    app = create_app(config.test_config)
    app.config['TESTING'] = True
    api = app.test_client()

    return api


def setup_function():
    ## Create  a test user
    hashed_password = bcrypt.hashpw(b'rlawjdgns', bcrypt.gensalt())
    new_users = [{
            'id': 1,
            'name': 'testName',
            'email': 'test@email.com',
            'hashed_password': hashed_password,
            'profile': 'test profile'
        }, {
            'id': 2,
            'name': 'test2Name',
            'email': 'test2@email.com',
            'hashed_password': hashed_password,
            'profile': 'test2 profile'
        }]
    database.execute(text("""
        INSERT INTO users (
            id,
            name,
            email,
            hashed_password,
            profile
        ) VALUES (
            :id,
            :name,
            :email,
            :hashed_password,
            :profile
        )
    """), new_users)

    database.execute(text("""
        INSERT INTO tweets (
            user_id,
            tweet
        ) VALUE (
            2,
            "test tweet!"
        )
    """))
    
def test_ping(api):
    res = api.get('/ping')
    assert b'pong' in res.data

def test_login(api):
    res = api.post(
        '/login',
        data=json.dumps({
            'email': 'test@email.com',
            'password': 'rlawjdgns'
            }),
        content_type='application/json')

    assert b'access_token' in res.data
    
def test_unauthorization(api):
    res = api.post(
        '/tweet',
        data=json.dumps({'tweet': 'tweet test'}),
        content_type='application/json'
    )
    assert res.status_code == 401

    res = api.post(
        '/follow',
        data=json.dumps({'follow': 2}),
        content_type='application/json'
    )
    assert res.status_code == 401

    res = api.post(
        '/unfollow',
        data=json.dumps({'unfollow': 2}),
        content_type='application/json'
    )
    assert res.status_code == 401

def test_tweet(api):
    
    # Login
    res = api.post(
        '/login',
       data=json.dumps({
           'email': 'test@email.com',
           'password': 'rlawjdgns'
       }),
       content_type='application/json')
    res_json = json.loads(res.data.decode('utf-8'))
    access_token = res_json['access_token']
    user_id = res_json['user_id']

    # Tweet
    res = api.post('/tweet',
        data=json.dumps({'tweet': 'test_tweet!!'}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )


    assert res.status_code == 200
        

    # Check tweet
    res = api.get('/timeline',
            data=json.dumps({'user_id': user_id}),
            content_type='application/json',
            headers={'Authorization': access_token})
    tweets = json.loads(res.data.decode('utf-8'))

    assert res.status_code == 200

    assert tweets == {
        'user_id': user_id,
        'tweet': [
            {
                'user_id': user_id,
                'tweet': 'test_tweet!!'
            }
        ]
    }


def test_follow(api):
    # Login
    res = api.post(
        '/login',
        data=json.dumps({'email': 'test@email.com', 'password': 'rlawjdgns'}),
        content_type='application/json'
    )
    res_json = json.loads(res.data.decode('utf-8'))
    access_token = res_json['access_token']
    user_id = res_json['user_id']

    # check if authenticated user's timeline is empty.
    res = api.get(
        '/timeline',
        data=json.dumps({'user_id': user_id}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )
    tweets = json.loads(res.data.decode('utf-8'))
    assert res.status_code == 200
    assert tweets == {
        'user_id': 1,
        'tweet': []
    }

    # follow second user
    res = api.post(
        '/follow',
        data=json.dumps({'follow': 2}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )
    assert res.status_code == 200

    # get user's timeline and check if user 2's tweet exists.
    res = api.get(
        '/timeline',
        data=json.dumps({'user_id': user_id}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )
    tweets = json.loads(res.data.decode('utf-8'))
    
    assert res.status_code == 200
    assert tweets == {
        'user_id': 1,
        'tweet': [
            {
            'user_id': 2,
            'tweet': 'test tweet!'
            }
        ]
    }
        

def test_unfollow(api):
    # repeat follow steps and then proceed unfollow..
    res = api.post(
            '/login',
            data=json.dumps({'email': 'test@email.com', 'password': 'rlawjdgns'}),
            content_type='application/json'
        )
    res_json = json.loads(res.data.decode('utf-8'))
    access_token = res_json['access_token']
    user_id = res_json['user_id']

    # follow second user
    res = api.post(
        '/follow',
        data=json.dumps({'follow': 2}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )
    assert res.status_code == 200

    # get user's timeline and check if user 2's tweet exists.
    res = api.get(
        '/timeline',
        data=json.dumps({'user_id': user_id}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )
    tweets = json.loads(res.data.decode('utf-8'))
    
    assert res.status_code == 200
    assert tweets == {
        'user_id': 1,
        'tweet': [
            {
            'user_id': 2,
            'tweet': 'test tweet!'
            }
        ]
    }
     
    # Unfollow user 2
    res = api.post(
        '/unfollow',
        data=json.dumps({'unfollow': 2}),
        content_type='application/json',
        headers={'Authorization': access_token}
    )
    assert res.status_code == 200

    # Check user 1's timeline is empty
    res = api.get(
            '/timeline',
            data=json.dumps({'user_id': user_id}),
            content_type='application/json',
            headers={'Authorization': access_token}
        )
    tweets = json.loads(res.data.decode('utf-8'))
    assert res.status_code == 200
    assert tweets == {
        'user_id': 1,
        'tweet': []
    }






def teardown_function():
    database.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    database.execute(text("TRUNCATE users"))
    database.execute(text("TRUNCATE tweets"))
    database.execute(text("TRUNCATE users_follow_list"))
    database.execute(text("SET FOREIGN_KEY_CHECKS=1"))


