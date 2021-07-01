from datetime import datetime, timedelta
from functools import wraps
from flask_cors import CORS
import bcrypt
import jwt
from flask import Flask, Response, current_app, g, jsonify, request
from flask.json import JSONEncoder
from sqlalchemy import create_engine, text


class CustomJsonEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return JSONEncoder.default(self, obj)
    

def get_user(user_id):
    user = current_app.database.execute(text("""
                SELECT
                    id,
                    name,
                    email,
                    profile
                FROM users
                WHERE id = :user_id
            """), {
                'user_id' : user_id
            }).fetchone()
    
    return {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'profile': user['profile'],
        } if user else None

def insert_user(new_user):
    return current_app.database.execute(text("""
                INSERT INTO users (
                    name,
                    email,
                    profile,
                    hashed_password
                ) VALUE (
                    :name,
                    :email,
                    :profile,
                    :password
                )
            """), new_user).lastrowid

def insert_tweet(user_tweet):
    return current_app.database.execute(text("""
            INSERT INTO tweets (
                user_id,
                tweet
            ) VALUE (
                :id,
                :tweet
            )
        """), user_tweet).rowcount
    
def get_timeline(user_id):
    rows = current_app.database.execute(text("""
            SELECT
                t.user_id,
                t.tweet
            FROM tweets t
            LEFT JOIN users_follow_list ufl ON ufl.user_id = :user_id
            WHERE t.user_id =:user_id
            OR t.user_id = ufl.follow_user_id
        """), {
            'user_id': user_id
        }).fetchall()
    
    return [{
            'user_id': row['user_id'],
            'tweet': row['tweet']
        } for row in rows]
    
def insert_follow(user_follow):
    return current_app.database.execute(text("""
            INSERT INTO users_follow_list (
                user_id,
                follow_user_id
            ) VALUE (
                :id,
                :follow
            )
        """), user_follow).rowcount
    
def insert_unfollow(user_unfollow):
    return current_app.database.execute(text("""
            DELETE
            FROM users_follow_list
            WHERE user_id = :id AND follow_user_id = :unfollow
        """), user_unfollow)


##########################
### Decorator ############
##########################
def login_required(f):
    @wraps(f)
    def wrapper_login_required(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], 'HS256')
            except jwt.InvalidTokenError:
                payload = None
            
            if payload is None: return Response(status=401)
            
            user_id = payload['user_id']
            g.user_id = user_id
            g.user = get_user(user_id) if user_id else None
        
        else:
            return Response(status=401)
        
        return f(*args, **kwargs)
        
        
    return wrapper_login_required

##########################
### Decorator Ends #######
##########################

def create_app(test_config=None):
    app = Flask(__name__)
    
    CORS(app)
    
    app.json_encoder = CustomJsonEncoder
    
    if test_config == None:
        app.config.from_pyfile('config.py')
    else:
        app.config.update(test_config)
    
    # connect to database by using create_engine func.
    # it returns Engin object.
    database = create_engine(app.config['DB_URL'], encoding='utf-8',
                             max_overflow=0)
    app.database = database
    
    @app.route("/sign-up", methods=['POST'])
    def sign_up():
        new_user = request.json
        new_user['password'] = bcrypt.hashpw(new_user['password'].encode('UTF-8'), bcrypt.gensalt())
        new_user_id = insert_user(new_user)
        new_user = get_user(new_user_id)
        
        return jsonify(new_user)
    
    @app.route("/login", methods=['POST'])
    def login():
        credential = request.json
        email = credential['email']
        password = credential['password']
        
        row = app.database.execute(text("""
            SELECT
                id,
                hashed_password
            FROM users
            WHERE email = :email
        """), {'email': email}).fetchone()
        
        
        if row and bcrypt.checkpw(password.encode('UTF-8'),
                                row['hashed_password'].encode('UTF-8')):
            user_id = row['id']
            payload = {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(seconds=60*60*24)
            }
            token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], 'HS256')

            return jsonify({
                'user_id': user_id,
                'access_token': token
            })
        else:
            return '', 401
    
    @app.route("/tweet", methods=['POST'])
    @login_required
    def tweet():
        user_tweet = request.json
        user_tweet['id'] = g.user_id
        tweet = user_tweet['tweet']
        
        if len(tweet) > 300:
            return 'Your tweet exceeds over 300', 400
        
        insert_tweet(user_tweet)
        
        return '', 200
    
    @app.route("/timeline", methods=['GET'])
    @login_required
    def timeline():
        user_id = g.user_id
        
        return jsonify({
            'user_id': user_id,
            'tweet': get_timeline(user_id)
        })
        
    @app.route("/follow", methods=['POST'])
    @login_required
    def follow():
        payload = request.json
        payload['id'] = g.user_id
        insert_follow(payload)

        return '', 200
    
    @app.route("/unfollow", methods=['POST'])
    @login_required
    def unfollow():
        payload = request.json
        payload['id'] = g.user_id        
        insert_unfollow(payload)
        
        return '', 200
    

    @app.route("/ping", methods=['GET'])
    def ping():
        return 'pong'

    return app

# app.users = {}
# app.id_count = 1
# app.tweets = []




# @app.route("/timeline/<int:user_id>", methods=['GET'])
# def timeline(user_id):
#     if user_id not in app.users:
#         return 'there is no such user', 400
    
#     follow_list = app.users[user_id].get('follow', set())
#     follow_list.add(user_id)
#     timeline = [tweet for tweet in app.tweets if tweet['user_id'] in follow_list]
    
#     return jsonify({
#         'user_id': user_id,
#         'timeline': timeline,
#     })


# @app.route("/unfollow", methods=['POST'])
# def unfollow():
#     payload = request.json
#     follower  = int(payload['id'])
#     followed_id = int(payload['unfollow'])

#     if followed_id not in app.users or follower not in app.users:
#         return 'there\'s such user to follow', 400
    
#     user = app.users[follower]
#     user.setdefault('follow', set()).discard(followed_id)

#     return jsonify(user)

# @app.route("/follow", methods=['POST'])
# def follow():
#     payload = request.json
#     follow_id = int(payload['follow'])
#     follower = int(payload['id'])
    
#     if follow_id not in app.users or follower not in app.users:
#         return 'there\'s no user to follow', 400
    
#     user = app.users[follower]
#     user.setdefault('follow', set()).add(follow_id)
    
#     return jsonify(user)

# @app.route("/tweet", methods=['POST'])
# def tweet():
#     payload = request.json
#     user_id = int(payload['id'])
#     tweet = payload['tweet']

#     if user_id not in app.users:
#         return f'there is no user id {user_id}', 400

#     if len(tweet) > 300:
#         return 'tweet length is over 300', 400
    
#     app.tweets.append({
#         'user_id': user_id,
#         'tweet': tweet,
#     })      
#     return '', 200

# @app.route("/ping", methods=['GET'])
# def ping():
#     return "pong"

# @app.route("/sign-up", methods=['POST'])
# def sign_up():
#     new_user                = request.json
#     new_user["id"]          = app.id_count
#     app.users[app.id_count] = new_user 
#     app.id_count            += 1

#     return jsonify(new_user)
