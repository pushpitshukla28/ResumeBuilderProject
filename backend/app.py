from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import pdfkit
import os
from flask import make_response
pdfkit_config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')



app = Flask(__name__)
app.secret_key = 'pushpit_secret_key'  # keep this secret in production

# ---------------- MySQL Configuration ---------------- #
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '15Aug2003'  # change this in production
app.config['MYSQL_DB'] = 'resume_builder'

mysql = MySQL(app)

# ------------------ Routes Start --------------------- #

@app.route('/')
def home():
    return render_template('index.html')  # ✅ Show landing page

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()

        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['name'] = user['name']
            return redirect(url_for('resume_form'))
        else:
            msg = 'Incorrect email or password!'
    
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user:
            msg = 'Email already registered!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        else:
            cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', (name, email, password))
            mysql.connection.commit()
            msg = 'Registered successfully! Please login.'
            return redirect(url_for('login'))
    
    return render_template('register.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- Resume Form ---------------- #

@app.route('/resume_form')
def resume_form():
    if 'loggedin' in session:
        return render_template('resume_form.html', message=None)
    return redirect(url_for('login'))

@app.route('/submit_resume', methods=['POST'])
def submit_resume():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    phone = request.form['phone']
    address = request.form['address']
    summary = request.form['summary']
    education = request.form['education']
    experience = request.form['experience']
    skills = request.form['skills']
    projects = request.form['projects']

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO resumes (user_id, phone, address, summary, education, experience, skills, projects)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, phone, address, summary, education, experience, skills, projects))
        mysql.connection.commit()
        return render_template('resume_form.html', message="✅ Resume submitted successfully!")
    except Exception as e:
        mysql.connection.rollback()
        print("Error:", e)
        return render_template('resume_form.html', message="❌ Failed to submit resume. Please try again.")
    
@app.route('/my_resume')
def my_resume():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM resumes WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
    resume = cursor.fetchone()

    if resume:
        return render_template('my_resume.html', resume=resume)
    else:
        return render_template('my_resume.html', message="No resume submitted yet.")


@app.route('/download_resume')
def download_resume():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM resumes WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
    resume = cursor.fetchone()

    if resume:
        rendered = render_template('my_resume.html', resume=resume)
        pdf = pdfkit.from_string(rendered, False, configuration=pdfkit_config)

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=resume.pdf'
        return response
    else:
        return "No resume found to download."



# ------------------ Run Server --------------------- #
if __name__ == '__main__':
    app.run(debug=True)
