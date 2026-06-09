from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    venue = db.Column(db.String(150))
    show_date = db.Column(db.String(20))
    notes = db.Column(db.Text)
    is_archived = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    archived_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Find(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
    show = db.relationship("Show", backref="finds")

    image_filename = db.Column(db.String(200))
    table_number = db.Column(db.String(50))
    dealer_name = db.Column(db.String(150))
    price_seen = db.Column(db.Float)
    card_type = db.Column(db.String(30), default="Raw")
    grading_company = db.Column(db.String(50))
    grade = db.Column(db.String(20))
    notes = db.Column(db.Text)

    status = db.Column(db.String(30), default="Interested")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
