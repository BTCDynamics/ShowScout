from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import inspect, text

from models import db, Show, Find


app = Flask(__name__)
app.secret_key = "showscout-dev-secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///showscout.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def money_value(value):
    """Convert a form money field to float or None."""
    if value is None:
        return None

    clean_value = str(value).replace("$", "").replace(",", "").strip()
    if not clean_value:
        return None

    try:
        return float(clean_value)
    except ValueError:
        return None


def ensure_database_columns():
    """Add newer columns to an existing local SQLite database without wiping data."""
    inspector = inspect(db.engine)

    if "find" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("find")
    }

    if "card_type" not in existing_columns:
        db.session.execute(
            text("ALTER TABLE find ADD COLUMN card_type VARCHAR(30) DEFAULT 'Raw'")
        )
        db.session.commit()


with app.app_context():
    db.create_all()
    ensure_database_columns()


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
        return redirect(url_for("show_detail", show_id=new_show.id))

    return render_template("create_show.html")


@app.route("/show/<int:show_id>")
def show_detail(show_id):
    show = Show.query.get_or_404(show_id)
    finds = (
        Find.query
        .filter(Find.show_id == show.id)
        .order_by(Find.created_at.desc(), Find.id.desc())
        .all()
    )

    return render_template(
        "show_detail.html",
        show=show,
        finds=finds,
    )


@app.route("/show/<int:show_id>/add-find", methods=["GET", "POST"])
def add_find(show_id):
    show = Show.query.get_or_404(show_id)

    if request.method == "POST":
        table_number = (request.form.get("table_number") or "").strip() or None
        dealer_name = (request.form.get("dealer_name") or "").strip() or None
        price_seen = money_value(request.form.get("price_seen"))
        card_type = request.form.get("card_type") or "Raw"
        status = request.form.get("status") or "Interested"
        notes = (request.form.get("notes") or "").strip() or None

        new_find = Find(
            show_id=show.id,
            table_number=table_number,
            dealer_name=dealer_name,
            price_seen=price_seen,
            card_type=card_type,
            status=status,
            notes=notes,
        )

        db.session.add(new_find)
        db.session.commit()

        flash("Find saved.")
        return redirect(url_for("show_detail", show_id=show.id))

    return render_template("add_find.html", show=show)


@app.route("/find/<int:find_id>")
def find_detail(find_id):
    find = Find.query.get_or_404(find_id)
    return render_template("find_detail.html", find=find, show=find.show)


if __name__ == "__main__":
    app.run(debug=True)
