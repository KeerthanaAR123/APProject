import os
import random
import pandas as pd
from flask import Flask, render_template, request, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt

# --------- GOOGLE SHEET INIT ---------- #
def init_google_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "day11-467403-d292e19fd8ca.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("day1").sheet1

    if not sheet.row_values(1):
        sheet.insert_row(["Name", "Question", "User Answer", "Correct Answer", "Status", "Timestamp"], 1)
    return sheet

sheet = init_google_sheets()

# --------- FLASK APP ---------- #
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed to use Flask session

# --------- UTIL FUNCTIONS ---------- #
def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(n % 10, 'th')}"

def generate_question():
    a = random.randint(1, 20)
    d = random.randint(1, 10)
    n = random.randint(3, 10)
    ord_n = ordinal(n)
    question = f"Find the {ord_n} term of the AP: {a}, {a + d}, {a + 2*d}, ..."
    correct_answer = a + (n - 1) * d
    return question, correct_answer

def check_answer(user_input, correct):
    try:
        return int(user_input) == correct
    except:
        return False

def get_google_sheet_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = [col.lower() for col in df.columns]
    return df

# --------- ROUTES ---------- #
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form')
def formapi():
    questions = [generate_question() for _ in range(5)]
    session['quiz_questions'] = questions
    only_questions = [q for q, a in questions]
    return render_template('form.html', questions=only_questions)

@app.route('/anyname', methods=['POST'])
def insertdata():
    try:
        name = request.form.get('name', 'Anonymous')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stored = session.get('quiz_questions', [])

        for i in range(1, 6):
            ques = request.form.get(f'question{i}')
            ans = request.form.get(f'answer{i}')

            correct = None
            for q, a in stored:
                if q == ques:
                    correct = a
                    break

            if correct is None:
                return f"Could not match question: {ques}"

            status = "Correct" if check_answer(ans, correct) else "Incorrect"
            sheet.append_row([name, ques, ans, correct, status, timestamp])

        return render_template("success.html")
    except Exception as e:
        return f"Error: {e}"

@app.route('/results')
def show_results():
    df = get_google_sheet_data()
    correct_count = df['status'].str.lower().eq('correct').sum() if 'status' in df.columns else 0
    incorrect_count = df['status'].str.lower().eq('incorrect').sum() if 'status' in df.columns else 0

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(x=["Correct", "Incorrect"], y=[correct_count, incorrect_count], palette="pastel", ax=ax)
    ax.set_ylabel("Count")
    ax.set_title("Quiz Result Summary")
    plt.tight_layout()

    img_path = "static/barplot.png"
    plt.savefig(img_path)
    plt.close()

    table_html = df.to_html(classes='table table-bordered', index=False)

    return render_template("result.html",
                           table_html=table_html,
                           correct_count=correct_count,
                           incorrect_count=incorrect_count,
                           graph_url=img_path)

@app.route('/worksheet')
def create_worksheet():
    content = "Arithmetic Progression Worksheet:\n\n"
    questions = session.get('quiz_questions', [])

    if not questions:
        content += "No quiz questions available. Please take the quiz first."
    else:
        for i, (question, _) in enumerate(questions, 1):
            content += f"{i}. {question} = \n"

    filename = f"AP_worksheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w") as f:
        f.write(content)

    return render_template("worksheet_success.html", filename=filename)

# --------- RUN FLASK APP ---------- #
if __name__ == '__main__':
    app.run(debug=True, port=8001)
