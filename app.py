import os
import uuid
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import inspect, text
from sqlalchemy.sql import func
from werkzeug.utils import secure_filename

from models import db, Show, Find


app = Flask(__name__)
app.secret_key = os.environ.get("SHOWSCOUT_SECRET_KEY", "showscout-dev-secret")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SHOWSCOUT_DATABASE_URL",
    "sqlite:///showscout.db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

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


def allowed_image(filename):
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_find_photo(uploaded_file):
    """Save uploaded find photo and return filename, or None if no file."""
    if not uploaded_file or not uploaded_file.filename:
        return None

    if not allowed_image(uploaded_file.filename):
        flash("Photo must be JPG, PNG, WEBP, or GIF.")
        return None

    original_name = secure_filename(uploaded_file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    filename = f"find-{uuid.uuid4().hex}.{extension}"
    save_path = UPLOAD_FOLDER / filename
    uploaded_file.save(save_path)
    return filename


def ensure_database_columns():
    """Add newer columns to an existing local SQLite database without wiping data."""
    inspector = inspect(db.engine)

    table_names = inspector.get_table_names()

    if "show" in table_names:
        existing_show_columns = {
            column["name"]
            for column in inspector.get_columns("show")
        }

        if "is_archived" not in existing_show_columns:
            db.session.execute(
                text("ALTER TABLE show ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL")
            )
            db.session.commit()

        if "archived_at" not in existing_show_columns:
            db.session.execute(
                text("ALTER TABLE show ADD COLUMN archived_at DATETIME")
            )
            db.session.commit()

    if "find" not in table_names:
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

    if "image_filename" not in existing_columns:
        db.session.execute(
            text("ALTER TABLE find ADD COLUMN image_filename VARCHAR(200)")
        )
        db.session.commit()

    if "grading_company" not in existing_columns:
        db.session.execute(
            text("ALTER TABLE find ADD COLUMN grading_company VARCHAR(50)")
        )
        db.session.commit()

    if "grade" not in existing_columns:
        db.session.execute(
            text("ALTER TABLE find ADD COLUMN grade VARCHAR(20)")
        )
        db.session.commit()


with app.app_context():
    db.create_all()
    ensure_database_columns()


@app.route("/")
def home():
    view = request.args.get("view", "active")
    show_archived = view == "archived"

    shows = (
        Show.query
        .filter(Show.is_archived.is_(show_archived))
        .order_by(Show.created_at.desc(), Show.id.desc())
        .all()
    )
    active_count = Show.query.filter(Show.is_archived.is_(False)).count()
    archived_count = Show.query.filter(Show.is_archived.is_(True)).count()

    return render_template(
        "home.html",
        shows=shows,
        view=view,
        active_count=active_count,
        archived_count=archived_count,
    )


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

    if show.is_archived:
        flash("This show is archived. Restore it before adding new finds.")
        return redirect(url_for("show_detail", show_id=show.id))

    if request.method == "POST":
        table_number = (request.form.get("table_number") or "").strip() or None
        dealer_name = (request.form.get("dealer_name") or "").strip() or None
        price_seen = money_value(request.form.get("price_seen"))
        card_type = request.form.get("card_type") or "Raw"
        status = request.form.get("status") or "Interested"
        grading_company = (request.form.get("grading_company") or "").strip() or None
        grade = (request.form.get("grade") or "").strip() or None
        if card_type != "Graded":
            grading_company = None
            grade = None
        notes = (request.form.get("notes") or "").strip() or None
        image_filename = save_find_photo(request.files.get("photo"))

        new_find = Find(
            show_id=show.id,
            image_filename=image_filename,
            table_number=table_number,
            dealer_name=dealer_name,
            price_seen=price_seen,
            card_type=card_type,
            grading_company=grading_company,
            grade=grade,
            status=status,
            notes=notes,
        )

        db.session.add(new_find)
        db.session.commit()

        flash("Find saved.")
        return redirect(url_for("show_detail", show_id=show.id))

    return render_template("add_find.html", show=show)


@app.route("/show/<int:show_id>/archive", methods=["POST"])
def archive_show(show_id):
    show = Show.query.get_or_404(show_id)
    show.is_archived = True
    show.archived_at = func.now()
    db.session.commit()
    flash(f"Archived show: {show.name}")
    return redirect(url_for("home"))


@app.route("/show/<int:show_id>/restore", methods=["POST"])
def restore_show(show_id):
    show = Show.query.get_or_404(show_id)
    show.is_archived = False
    show.archived_at = None
    db.session.commit()
    flash(f"Restored show: {show.name}")
    return redirect(url_for("show_detail", show_id=show.id))


@app.route("/find/<int:find_id>")
def find_detail(find_id):
    find = Find.query.get_or_404(find_id)
    return render_template("find_detail.html", find=find, show=find.show)


if __name__ == "__main__":
    app.run(debug=True)
