from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Show

app = Flask(__name__)
app.secret_key = "showscout-dev-secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///showscout.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    shows = Show.query.order_by(Show.created_at.desc(), Show.id.desc()).all()
    return render_template("home.html", shows=shows)


@app.route("/create-show", methods=["GET", "POST"])
def create_show():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        venue = (request.form.get("venue") or "").strip() or None
        show_date = request.form.get("show_date") or None
        notes = (request.form.get("notes") or "").strip() or None

        if not name:
            flash("Show name is required.")
            return redirect(url_for("create_show"))

        new_show = Show(
            name=name,
            venue=venue,
            show_date=show_date,
            notes=notes,
        )

        db.session.add(new_show)
        db.session.commit()

        flash(f"Created show: {new_show.name}")
        return redirect(url_for("home"))

    return render_template("create_show.html")


if __name__ == "__main__":
    app.run(debug=True)
