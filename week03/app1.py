from flask import Flask, jsonify, request
app = Flask(__name__)

@app.get("/users")
def get_user():
    return jsonify({"message":"get all user"})

@app.get("/user/<int:uid>")
def get_user(uid):
    return jsonify({"message":"get user {uid}"})

@app.get("/post")
def get_post():
    return jsonify({"message":"get all post"})

@app.get("/post/<int:pid")
def get_post(pid):
    return jsonify({"message":"get post {pid}"})

@app.post("/posts")
def create_post():
    data = request.get_json()
    return jsonify({
        "message": "Create post",
        "data": data
    }), 201

@app.put("/posts/<int:post_id>")
def update_post(post_id):
    data = request.get_json()
    return jsonify({
        "message": f"Update post {post_id}",
        "data": data
    })


@app.delete("/posts/<int:post_id>")
def delete_post(post_id):
    return jsonify({"message": f"Delete post {post_id}"})

@app.get("/posts/<int:post_id>/comments")
def get_comments(post_id):
    return jsonify({
        "message": f"Get comments of post {post_id}"
    })


@app.post("/posts/<int:post_id>/comments")
def create_comment(post_id):
    data = request.get_json()
    return jsonify({
        "message": f"Create comment for post {post_id}",
        "data": data
    }), 201

@app.get("/posts/<int:post_id>/comments/<int:comment_id>")
def get_comment(post_id, comment_id):
    return jsonify({
        "message": f"Get comment {comment_id} of post {post_id}"
    })

@app.delete("/posts/<int:post_id>/comments/<int:comment_id>")
def delete_comment(post_id, comment_id):
    return jsonify({
        "message": f"Delete comment {comment_id}"
    })

@app.post("/users/<int:user_id>/follows")
def follow_user(user_id):
    return jsonify({
        "message": f"Follow user {user_id}"
    }), 201


@app.delete("/users/<int:user_id>/follows")
def unfollow_user(user_id):
    return jsonify({
        "message": f"Unfollow user {user_id}"
    })

