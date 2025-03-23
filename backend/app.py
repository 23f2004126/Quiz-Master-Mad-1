from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from model import db, User, Subject, Chapter, Quiz, Question, Score
from datetime import datetime

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_master.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'  # Secret key for session management
db.init_app(app)

# Helper Functions
def is_admin():
    return 'role' in session and session['role'] == 'admin'

def is_user():
    return 'role' in session and session['role'] == 'user'

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        qualification = request.form['qualification']
        dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()

        new_user = User(username=username, password=password, full_name=full_name, qualification=qualification, dob=dob)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin@quizmaster.com" and password == "admin123":
            session['user_id'] = 1
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('user_dashboard'))

        flash("Invalid credentials")
        return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# User Dashboard
@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    available_quizzes = Quiz.query.all()  # You can filter quizzes based on user preferences or criteria.
    completed_quizzes = Score.query.filter_by(user_id=user_id).all()

    return render_template(
        'user_dashboard.html',
        user=user,
        available_quizzes=available_quizzes,
        completed_quizzes=completed_quizzes
    )
@app.route('/user/quiz/<int:quiz_id>/take', methods=['GET'])
def take_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    quiz = Quiz.query.get_or_404(quiz_id)

    return render_template('take_quiz.html', quiz=quiz)
@app.route('/user/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    quiz = Quiz.query.get_or_404(quiz_id)

    # Evaluate the user's answers
    score = 0
    for question in quiz.questions:
        user_answer = request.form.get(f"question_{question.id}")
        if user_answer and int(user_answer) == question.correct_option:
            score += 1

    # Save the user's score
    new_score = Score(
        user_id=user_id,
        quiz_id=quiz.id,
        score=score,
        date=datetime.utcnow()
    )
    db.session.add(new_score)
    db.session.commit()

    flash(f"You completed the quiz! Your score: {score}/{len(quiz.questions)}", "success")
    return redirect(url_for('user_dashboard'))

@app.route('/user/profile', methods=['GET', 'POST'])
def edit_profile():
    current_user=session['user_id']
    if not current_user:
        return redirect(url_for('login'))

    user = User.query.get(current_user)  # Assuming `current_user` provides the logged-in user info

    if request.method == 'POST':
        # Retrieve data from the form
        user.full_name = request.form.get('full_name')
        user.qualification = request.form.get('qualification')
        user.dob = datetime.strptime(request.form.get('dob'), "%Y-%m-%d").date() if request.form.get('dob') else None

        # Save changes to the database
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('edit_profile.html', user=user)


# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

# Entity Routes

@app.route('/admin/subjects')
def admin_subjects():
    if not is_admin():
        return redirect(url_for('login'))

    subjects = Subject.query.all()
    headers = ["ID", "Name", "Description"]
    return render_template('admin_subjects.html', title="Subjects", entities=subjects, headers=headers)


@app.route('/admin/users')
def admin_users():
    if not is_admin():
        return redirect(url_for('login'))

    users = User.query.all()
    headers = ["ID", "Username", "Full Name", "Role"]  # Include Role in headers
    return render_template('admin_list.html', title="Users", users=users, headers=headers)

@app.route('/admin/users/<int:user_id>/quizzes')
def view_user_quizzes(user_id):
    if not is_admin():
        return redirect(url_for('login'))
    
    # Fetch the user
    user = User.query.get_or_404(user_id)

    # Fetch quizzes and scores associated with the user
    quizzes = Score.query.filter_by(user_id=user.id).join(Quiz).all()
    
    # Handle case when no quizzes are found
    if not quizzes:
        user_quizzes = []  # No quizzes taken
    else:
        # Process quizzes into a list of dictionaries
        user_quizzes = [
            {"title": quiz.quiz.title, "score": quiz.score, "date": quiz.date}
            for quiz in quizzes
        ]

    # Render the template
    return render_template(
        'admin_list.html',
        title=f"Quizzes Taken by {user.full_name}",
        users=[],  # Empty because we're not showing the user list here
        headers=[],  # No headers for the user quizzes
        user_quizzes=user_quizzes,  # List of quizzes
        user_full_name=user.full_name
    )

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} has been deleted.", "success")
    return redirect(url_for('admin_users'))




@app.route('/admin/subjects/<int:subject_id>/chapters')
def view_chapters(subject_id):
    if not is_admin():
        return redirect(url_for('login'))
    subject = Subject.query.get_or_404(subject_id)
    chapters = Chapter.query.filter_by(subject_id=subject.id).all()
    headers = ["ID", "Name", "Description"]
    return render_template('admin_list.html', title=f"Chapters for {subject.name}", entities=chapters, headers=headers)

@app.route('/admin/subjects/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    if not is_admin():
        return redirect(url_for('login'))
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted successfully!", "success")
    return redirect(url_for('admin_subjects'))

@app.route('/admin/chapters')
def admin_chapters():
    if not is_admin():
        return redirect(url_for('login'))

    chapters = Chapter.query.all()
    headers = ["ID", "Name", "Subject"]
    return render_template('admin_chapters.html', title="Chapters", entities=chapters, headers=headers)

@app.route('/admin/chapters/<int:chapter_id>')
def view_chapter_details(chapter_id):
    if not is_admin():
        return redirect(url_for('login'))

    chapter = Chapter.query.get_or_404(chapter_id)
    return render_template('chapter_details.html', chapter=chapter)


@app.route('/admin/chapters/delete/<int:chapter_id>', methods=['POST'])
def delete_chapter(chapter_id):
    if not is_admin():
        return redirect(url_for('login'))

    chapter = Chapter.query.get_or_404(chapter_id)
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted successfully.', 'success')
    return redirect(url_for('admin_chapters'))


@app.route('/admin/quizzes')
def admin_quizzes():
    if not is_admin():
        return redirect(url_for('login'))

    quizzes = Quiz.query.all()
    headers = ["ID", "Title", "Chapter", "Date", "Duration"]
    return render_template('admin_quizzes.html', title="Quizzes", quizzes=quizzes, headers=headers)

@app.route('/admin/quizzes/<int:quiz_id>')
def view_quiz_details(quiz_id):
    if not is_admin():
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_details.html', quiz=quiz)
@app.route('/admin/quizzes/delete/<int:quiz_id>', methods=['POST'])

def delete_quiz(quiz_id):
    if not is_admin():
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully.', 'success')
    return redirect(url_for('admin_quizzes'))


@app.route('/admin/questions')
def admin_questions():
    if not is_admin():
        return redirect(url_for('login'))

    questions = Question.query.all()
    print(questions)
    headers = ["ID", "Statement", "Quiz", "Correct Option"]
    return render_template('admin_questions.html', title="Questions", questions=questions, headers=headers)


@app.route('/admin/questions/delete/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    if not is_admin():
        return redirect(url_for('login'))

    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully.', 'success')
    return redirect(url_for('admin_questions'))


@app.route('/admin/questions/view/<int:question_id>')
def view_question(question_id):
    if not is_admin():
        return redirect(url_for('login'))

    question = Question.query.get_or_404(question_id)
    return render_template(
        'view_question.html',
        title=f"View Question {question.id}",
        question=question
    )

# Add Routes
@app.route('/admin/add_subject', methods=['GET', 'POST'])
def add_subject():
    if not is_admin():
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        new_subject = Subject(name=name, description=description)
        db.session.add(new_subject)
        db.session.commit()
        return redirect(url_for('admin_subjects'))

    return render_template('add_subject.html')

@app.route('/admin/add_chapter', methods=['GET', 'POST'])
def add_chapter():
    if not is_admin():
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        subject_id = request.form['subject_id']

        new_chapter = Chapter(name=name, description=description, subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        return redirect(url_for('admin_chapters'))

    subjects = Subject.query.all()
    return render_template('add_chapter.html', subjects=subjects)

@app.route('/admin/add_quiz', methods=['GET', 'POST'])
def add_quiz():
    if not is_admin():
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        chapter_id = request.form['chapter_id']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        duration = request.form['duration']

        new_quiz = Quiz(title=title, chapter_id=chapter_id, date=date, duration=duration)
        db.session.add(new_quiz)
        db.session.commit()
        return redirect(url_for('admin_quizzes'))

    chapters = Chapter.query.all()
    return render_template('add_quiz.html', chapters=chapters)

@app.route('/admin/add_question', methods=['GET', 'POST'])
def add_question():
    if not is_admin():
        return redirect(url_for('login'))

    if request.method == 'POST':
        statement = request.form['statement']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct_option = int(request.form['correct_option'])
        quiz_id = int(request.form['quiz_id'])

        new_question = Question(
            statement=statement, option1=option1, option2=option2,
            option3=option3, option4=option4, correct_option=correct_option, quiz_id=quiz_id
        )
        db.session.add(new_question)
        db.session.commit()
        return redirect(url_for('admin_questions'))

    quizzes = Quiz.query.all()
    return render_template('add_question.html', quizzes=quizzes)

if __name__ == '__main__':
    app.run(debug=True)



    from flask import jsonify
from models import db, Scores, Quiz, Subject  # Adjust imports based on your project
from sqlalchemy.sql import func

@app.route('/quiz-data')
def get_quiz_data():
    # Get the number of attempts per subject
    attempts_per_subject = db.session.query(
        Subject.name, func.count(Scores.id)
    ).join(Quiz).join(Scores).group_by(Subject.name).all()

    # Get average scores per subject
    avg_scores_per_subject = db.session.query(
        Subject.name, func.avg(Scores.total_scored)
    ).join(Quiz).join(Scores).group_by(Subject.name).all()

    # Convert data to JSON format
    return jsonify({
        "attempts_per_subject": dict(attempts_per_subject),
        "avg_scores_per_subject": dict(avg_scores_per_subject)
    })








