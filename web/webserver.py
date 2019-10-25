from flask import Flask, g, jsonify, send_from_directory
import sqlite3
import os

DATABASE = "../helios.db"

# Create app
app = Flask(__name__, static_folder=os.path.join("public", "static"))
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


# helper to close
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route("/scans")
def projects():
    cur = get_db().cursor()
    res = cur.execute("select * from scans order by started DESC")
    return jsonify([dict(ix) for ix in cur.fetchall()])


@app.route("/results/<int:scan>")
def results(scan):
    cur = get_db().cursor()
    res = cur.execute("select * from results where scan = ? order by detected DESC", (str(scan),))
    return jsonify([dict(ix) for ix in cur.fetchall()])


@app.route("/")
def index():
    urlpath = os.path.join(os.path.dirname(__file__), "public")
    return send_from_directory(urlpath, "index.html")


if __name__ == "__main__":
    app.run()
