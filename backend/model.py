from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_master.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)  # Email
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120))
    qualification = db.Column(db.String(120))
    dob = db.Column(db.Date)
    role = db.Column(db.String(10), nullable=False, default='user')  # Admin or User
    scores = db.relationship('Score', backref='user', cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<User {self.username}>"

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    chapters = db.relationship('Chapter', backref='subject', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subject {self.name}>"

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id', ondelete="CASCADE"), nullable=False)
    quizzes = db.relationship('Quiz', backref='chapter', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chapter {self.name}>"

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id', ondelete="CASCADE"), nullable=False)
    questions = db.relationship('Question', backref='quiz', cascade="all, delete-orphan")
    scores = db.relationship('Score', backref='quiz', cascade="all, delete-orphan")
    date = db.Column(db.Date)
    duration = db.Column(db.Integer)  # Duration in minutes

    def __repr__(self):
        return f"<Quiz {self.title}>"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    statement = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(120), nullable=False)
    option2 = db.Column(db.String(120), nullable=False)
    option3 = db.Column(db.String(120), nullable=False)
    option4 = db.Column(db.String(120), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return f"<Question {self.statement[:20]}>"

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date)

    def __repr__(self):
        return f"<Score {self.score}>"

# Create the database
with app.app_context():
    db.create_all()

    # Create the admin if it does not exist
    admin = User.query.filter_by(username="admin@quizmaster.com").first()
    if not admin:
        admin_dob = datetime.strptime("1980-01-01", "%Y-%m-%d").date()  # Convert string to date object
        admin = User(
            username="admin@quizmaster.com",
            password="admin123",
            full_name="Quiz Master",
            qualification="N/A",
            dob=admin_dob,  # Assign the date object here
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
