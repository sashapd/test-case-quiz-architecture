from flask import Flask, render_template, redirect, session, url_for, request, g
import random
import sqlite3


def populate_db(c):
    c.execute('''CREATE TABLE user
                (id integer primary key, username text, password text)''')
    c.execute('''CREATE TABLE test_case
                (id integer primary key, description text, category_key integer key)''')
    c.execute('''CREATE TABLE category
                (id integer primary key, name text)''')
    c.execute('''CREATE TABLE test_step
                (id integer primary key, name text, test_case_id integer key, number integer)''')

    users = [('sasha', '1234'), ('admin', '1234')]
    c.executemany('insert into user(username, password) values (?, ?)', users)

    data_by_category = {'Login module':
                        {'Enter right login': ['Enter "sasha" login', 'Enter "1234" as password', 'Press "Login" button'],
                         'Test register': ['Press register button', 'Enter any credentials', 'Press "finish register"']}, "Register module": {}, "Test test module": {}, "lalal": {}, "yoyo": {}}

    for category, test_cases in data_by_category.items():
        c.execute('insert into category(name) values (?)', (category,))
        category_indx = c.lastrowid
        for test_case, steps in test_cases.items():
            c.execute('insert into test_case(description, category_key) values (?, ?)',
                      (test_case, category_indx))
            test_case_indx = c.lastrowid
            for i, step in enumerate(steps):
                c.execute(
                    'insert into test_step(name, test_case_id, number) values (?, ?, ?)', (step, test_case_indx, i + 1))


app = Flask(__name__, static_url_path='/static')

app.secret_key = b'hellowosdjorisjgjsdfhgsdfds23432234324324324hsafcxmzncvvz,mcvczxmn'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(':memory:')
        c = db.cursor()
        populate_db(c)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    c = get_db().cursor()
    c.execute("SELECT * FROM test_step")
    if 'user_type' in session:
        return render_template('index.html', username=session['username'])
    return render_template('login.html')


@app.route('/start_tests')
def start_tests():
    if 'user_type' in session:
        c = get_db().cursor()
        session['quiz'] = {}
        session['quiz']['category_id'] = request.args.get('id')
        session['quiz']['total'] = 3
        session['quiz']['questions'] = []
        session['quiz']['results'] = []
        test_case_id = get_random_test_case(
            c, [str(i) for i in session['quiz']['questions']], str(session['quiz']['category_id']))
        if test_case_id is not None:
            session['quiz']['questions'].append(test_case_id)
            return redirect(url_for('tests'))
        else:
            return redirect(url_for('categories'))
    return render_template('login.html')


def get_random_test_case(c, seen, category_id):
    c.execute('select id from test_case where category_key=? and id not in ({}) order by RANDOM() limit 1'.format(
        ', '.join(seen)), (category_id,))
    res = c.fetchone()
    if res is None:
        c.execute('select id from test_case where category_key=? order by RANDOM() limit 1'.format(
            ', '.join(seen)), (category_id,))
        res = c.fetchone()
    return res[0]


def get_steps_for_test_case(c, test_case_id):
    c.execute('select name, id from test_step where test_case_id=?',
              (str(test_case_id),))
    steps = c.fetchall()
    c.execute('select name, id from test_step where test_case_id !=? order by RANDOM() limit 4',
              (str(test_case_id),))
    steps += c.fetchall()
    random.shuffle(steps)
    return steps


def get_test_case_name(c, test_case_id):
    c.execute('select description from test_case where id=?',
              (str(test_case_id),))
    res = c.fetchall()
    return res[0][0]


def get_test_step_name(c, test_case_id):
    c.execute('select name from test_step where id=?', (str(test_case_id),))
    res = c.fetchall()
    return res[0][0]


@app.route('/tests')
def tests():
    if 'user_type' in session and 'quiz' in session and 'results' in session['quiz']:
        if len(session['quiz']['questions']) > session['quiz']['total']:
            return redirect(url_for('results'))
        print(len(session['quiz']['questions']))
        c = get_db().cursor()
        test_case_id = session['quiz']['questions'][-1]
        steps = get_steps_for_test_case(c, test_case_id)
        print(test_case_id)
        test_case_name = get_test_case_name(c, test_case_id)
        index = len(session['quiz']['questions'])
        total = session['quiz']['total']
        return render_template('tests.html', username=session['username'], test_case_name=test_case_name, steps=steps, index=index, total=total)
    return render_template('login.html')


def get_step_numbers_by_id(form):
    res = {}
    for step_id, step_num in form.items():
        if "step-" in step_id:
            res[step_id[len("step-"):]] = step_num
    return res


def is_in_test_case(c, id, test_case_id):
    c.execute('select test_case_id from test_step where id=? and test_case_id=?',
              (id, test_case_id,))
    return len(c.fetchall()) > 0


def get_step_num_by_id(c, id):
    c.execute('select number from test_step where id=?', (id,))
    return c.fetchall()[0][0]


def get_steps_with_colors(c, steps_by_id, test_case_id):
    res = []
    session['quiz']['results'].append({'correct': 0, 'wrong': 0, 'wrong_order': 0, 'all_correct': 0})
    for id, num in steps_by_id.items():
        color = "black"
        in_test_case = is_in_test_case(c, id, test_case_id)
        num_in_db = str(get_step_num_by_id(c, id))
        if in_test_case and num_in_db == num:
            color = "green"
            session['quiz']['results'][-1]['correct'] += 1
        elif (in_test_case and num == '') or (not in_test_case and num != ''):
            color = "red"
            session['quiz']['results'][-1]['wrong'] += 1
        elif in_test_case:
            color = "#FF8C00"
            session['quiz']['results'][-1]['wrong_order'] += 1
        name = get_test_step_name(c, id)
        res.append([in_test_case, num_in_db, color, num, name])
    if session['quiz']['results'][-1]['wrong'] == 0 and session['quiz']['results'][-1]['wrong_order'] == 0:
        session['quiz']['results'][-1]['all_correct'] += 1
    res.sort(key=lambda k: (not k[0], k[1]))
    return res


@app.route('/check_tests', methods=['POST'])
def check_tests():
    if 'user_type' in session:
        c = get_db().cursor()
        res = get_steps_with_colors(c, get_step_numbers_by_id(
            request.form), session['quiz']['questions'][-1])
        test_case_id = session['quiz']['questions'][-1]
        test_case_name = get_test_case_name(c, test_case_id)
        index = len(session['quiz']['questions'])
        total = session['quiz']['total']
        test_case_id = get_random_test_case(
            c, [str(i) for i in session['quiz']['questions']], str(session['quiz']['category_id']))
        session['quiz']['questions'].append(test_case_id)
        print(len(session['quiz']['questions']))
        session['quiz'] = session['quiz']
        return render_template('check_tests.html', username=session['username'], test_case_name=test_case_name, test_results=res, index=index, total=total)
    return render_template('login.html')


@app.route('/results')
def results():
    if 'user_type' in session:
        result_by_test_case = session['quiz']['results']
        results_combined = {}
        results_combined['correct'] = sum(r['correct'] for r in result_by_test_case)
        results_combined['wrong'] = sum(r['wrong'] for r in result_by_test_case)
        results_combined['wrong_order'] = sum(r['wrong_order'] for r in result_by_test_case)
        results_combined['all_correct'] = sum(r['all_correct'] for r in result_by_test_case)
        return render_template('results.html', results=enumerate(result_by_test_case), results_combined=results_combined)
    return render_template('login.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if is_in_users(username, password):
            session['username'] = username
            session['user_type'] = get_user_type(username)
        else:
            return render_template('login.html', error='AUTH')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_type', None)
    return redirect(url_for('index'))


def get_categories():
    c = get_db().cursor()
    c.execute('SELECT id, name from category')
    res = c.fetchall()
    return res


@app.route('/categories')
def categories():
    if 'user_type' in session:
        return render_template('categories.html', username=session['username'], categories=get_categories())
    return render_template('login.html')


def is_in_users(username, password):
    c = get_db().cursor()
    c.execute("select * from user where username=? and password=?",
              (username, password))
    return len(c.fetchall()) > 0


def get_user_type(username):
    return 'user'


if __name__ == '__main__':
    app.run()

# garnishe +
# contacts +
# registration
# dovidka +
# one test case per screen +
# wrong answer - red, right answer - green, yellow - incorrect sequence +
# sequence of test cases +
# end - total results, percentage by test case
