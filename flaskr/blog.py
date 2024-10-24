import markdown
from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db

bp = Blueprint("blog", __name__)


@bp.route("/")
def index():
    """Show all the posts, most recent first."""
    db = get_db()
    posts = db.execute(
        "SELECT p.id, title, tags, SUBSTRING(body, 1, 150) AS body_excerpt, created, author_id, username"
        " FROM post p JOIN user u ON p.author_id = u.id"
        " ORDER BY created DESC"
    ).fetchall()
    # 将 sqlite3.Row 转换为字典，并处理 Markdown 转换
    posts = [dict(post) for post in posts]

    # 将每篇文章的摘要转换为 Markdown 格式
    for post in posts:
        post['body_excerpt'] = markdown.markdown(post['body_excerpt'])

    return render_template("blog/index.html", posts=posts)


def get_post(id, check_author=True):
    post = (
        get_db()
        .execute(
            "SELECT p.id, title, tags, body, created, author_id, username"
            " FROM post p JOIN user u ON p.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
    )

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    # if check_author and post["author_id"] != g.user["id"]:
        # abort(403)

    return post


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        tags = request.form["tags"]
        body = request.form["body"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO post (title, tags, body, author_id) VALUES (?, ?, ?, ?)",
                (title, tags, body, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/create.html", post=None)


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    post = get_post(id)

    if request.method == "POST":
        title = request.form["title"]
        tags = request.form["tags"]
        body = request.form["body"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE post SET title = ?, tags = ?, body = ? WHERE id = ?", (title, tags, body, id)
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    get_post(id)
    db = get_db()
    db.execute("DELETE FROM post WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("blog.index"))


# 查看文章详情
@bp.route('/post/<int:id>')
# @login_required
def post(id):
    post = get_post(id)  # get_post 函数已经返回单个帖子
    # 使用 markdown 库将文章内容渲染为 HTML
    post_body_html = markdown.markdown(post['body'])
    if post:
        return render_template('/blog/post.html', post=post, post_body_html=post_body_html)  # 直接传递 post
    return "Post not found", 404