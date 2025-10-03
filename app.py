from flask import Flask, render_template, request, redirect, session
from database import get_db_connection  # Eğer veritabanı bağlantısı ayrı dosyadaysa
import sqlite3 
from datetime import datetime
import locale
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Oturumlar için gizli anahtar

# Türkçe ay ismi için locale ayarla
locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
current_month = datetime.now().strftime('%B')  # Örn: "Eylül"

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return redirect('/dashboard')

@app.route('/members')
def show_members():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    if session['role'] == 'trainer':
        members = conn.execute('SELECT * FROM members WHERE trainer_id = ?', (session['user_id'],)).fetchall()
    else:
        members = conn.execute('SELECT * FROM members').fetchall()

    conn.close()
    return render_template('index.html', members=members)

@app.route('/add', methods=['POST'])
def add_member():
    if 'user_id' not in session:
        return redirect('/login')

    trainer_id = request.form.get('trainer_id') or session['user_id']
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    join_date = request.form.get('join_date') or datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    conn.execute('INSERT INTO members (trainer_id, name, email, phone, join_date) VALUES (?, ?, ?, ?, ?)',
                 (trainer_id, name, email, phone, join_date))
    conn.commit()
    conn.close()

    return redirect('/members')

@app.route('/trainers')
def show_trainers():
    conn = get_db_connection()
    trainers = conn.execute('SELECT * FROM trainers').fetchall()
    conn.close()
    return render_template('trainers.html', trainers=trainers)

@app.route('/classes')
def show_classes():
    conn = get_db_connection()
    classes = conn.execute('''
        SELECT classes.*, trainers.name AS trainer_name
        FROM classes
        LEFT JOIN trainers ON classes.trainer_id = trainers.id
    ''').fetchall()

    trainers = conn.execute('SELECT * FROM trainers').fetchall()
    conn.close()
    return render_template('classes.html', classes=classes, trainers=trainers)

@app.route('/add_class', methods=['POST'])
def add_class():
    name = request.form['name']
    description = request.form['description']
    day = request.form['day']
    time = request.form['time']
    trainer_id = request.form['trainer_id']

    conn = get_db_connection()
    conn.execute('INSERT INTO classes (name, description, day, time, trainer_id) VALUES (?, ?, ?, ?, ?)',
                 (name, description, day, time, trainer_id))
    conn.commit()
    conn.close()
    return redirect('/classes')

@app.route('/add_trainer', methods=['POST'])
def add_trainer():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    share_percent = request.form['share_percent']

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO trainers (name, email, phone, share_percent)
        VALUES (?, ?, ?, ?)
    ''', (name, email, phone, share_percent))
    conn.commit()
    conn.close()
    return redirect('/trainers')

@app.route('/enroll', methods=['POST'])
def enroll_member():
    member_id = request.form['member_id']
    class_id = request.form['class_id']

    conn = get_db_connection()
    conn.execute('INSERT INTO enrollments (member_id, class_id) VALUES (?, ?)',
                 (member_id, class_id))
    conn.commit()
    conn.close()
    return redirect('/enrollments')

@app.route('/enrollments')
def show_enrollments():
    conn = get_db_connection()
    enrollments = conn.execute('''
        SELECT enrollments.id, members.name AS member_name, classes.name AS class_name
        FROM enrollments
        JOIN members ON enrollments.member_id = members.id
        JOIN classes ON enrollments.class_id = classes.id
    ''').fetchall()
    members = conn.execute('SELECT * FROM members').fetchall()
    classes = conn.execute('SELECT * FROM classes').fetchall()
    conn.close()
    return render_template('enrollments.html', enrollments=enrollments, members=members, classes=classes)

@app.route('/search_members', methods=['GET'])
def search_members():
    query = request.args.get('q', '')
    conn = get_db_connection()
    members = conn.execute('SELECT * FROM members WHERE name LIKE ?', ('%' + query + '%',)).fetchall()
    conn.close()
    return render_template('search_members.html', members=members, query=query)

@app.route('/payments')
def show_payments():
    conn = get_db_connection()
    payments = conn.execute('''
        SELECT payments.*, members.name AS member_name
        FROM payments
        JOIN members ON payments.member_id = members.id
    ''').fetchall()
    members = conn.execute('SELECT * FROM members').fetchall()
    conn.close()
    return render_template('payments.html', payments=payments, members=members)

@app.route('/add_payment', methods=['POST'])
def add_payment():
    member_id = request.form['member_id']
    amount = request.form['amount']
    date = request.form['date']
    note = request.form['note']

    conn = get_db_connection()
    conn.execute('INSERT INTO payments (member_id, amount, date, note) VALUES (?, ?, ?, ?)',
                 (member_id, amount, date, note))
    conn.commit()
    conn.close()
    return redirect('/payments')

@app.route('/member/<int:member_id>')
def member_detail(member_id):
    from datetime import datetime

    conn = get_db_connection()
    member = conn.execute('SELECT * FROM members WHERE id = ?', (member_id,)).fetchone()
    payments = conn.execute('SELECT * FROM payments WHERE member_id = ? ORDER BY end_date DESC', (member_id,)).fetchall()
    enrollments = conn.execute('''
        SELECT classes.name FROM enrollments
        JOIN classes ON enrollments.class_id = classes.id
        WHERE enrollments.member_id = ?
    ''', (member_id,)).fetchall()

    # 🔔 Otomatik yenileme önerisi
    renew_suggestion = None
    if payments and payments[0]['end_date']:
        try:
            end_date = datetime.strptime(payments[0]['end_date'], '%Y-%m-%d')
            days_left = (end_date - datetime.today()).days
            if days_left <= 7:
                renew_suggestion = f"Bu öğrencinin aboneliği {days_left} gün içinde bitiyor. Yenileme önerin!"
        except:
            pass

    conn.close()
    return render_template('member_detail.html',
        member=member,
        payments=payments,
        enrollments=enrollments,
        renew_suggestion=renew_suggestion
    )

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()
    return redirect('/members')

@app.route('/edit_member/<int:member_id>')
def edit_member(member_id):
    conn = get_db_connection()
    member = conn.execute('SELECT * FROM members WHERE id = ?', (member_id,)).fetchone()
    conn.close()
    return render_template('edit_member.html', member=member)

@app.route('/update_member/<int:member_id>', methods=['POST'])
def update_member(member_id):
    data = {key: request.form[key] for key in request.form}
    conn = get_db_connection()
    conn.execute('''
        UPDATE members SET
            name = ?, email = ?, phone = ?, birth_date = ?, height = ?, weight = ?,
            belt_level = ?, weight_category = ?, parent_name = ?, parent_phone = ?,
            parent_email = ?, registration_date = ?
        WHERE id = ?
    ''', (
        data['name'], data['email'], data['phone'], data['birth_date'], data['height'], data['weight'],
        data['belt_level'], data['weight_category'], data['parent_name'], data['parent_phone'],
        data['parent_email'], data['registration_date'], member_id
    ))
    conn.commit()
    conn.close()
    return redirect('/members')

@app.route('/trainer/<int:trainer_id>')
def trainer_detail(trainer_id):
    conn = get_db_connection()
    trainer = conn.execute('SELECT * FROM trainers WHERE id = ?', (trainer_id,)).fetchone()

    classes = conn.execute('SELECT * FROM classes WHERE trainer_id = ?', (trainer_id,)).fetchall()

    # Her sınıftaki öğrenci sayısını hesapla
    class_stats = []
    for cls in classes:
        count = conn.execute('SELECT COUNT(*) FROM enrollments WHERE class_id = ?', (cls['id'],)).fetchone()[0]
        class_stats.append({
            'class_name': cls['name'],
            'student_count': count
        })

    conn.close()
    return render_template('trainer_detail.html', trainer=trainer, class_stats=class_stats)

@app.route('/class/<int:class_id>')
def class_detail(class_id):
    from datetime import datetime
    current_month = datetime.today().strftime('%Y-%m')
    conn = get_db_connection()
    cls = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    trainer = conn.execute('SELECT * FROM trainers WHERE id = ?', (cls['trainer_id'],)).fetchone()

    # Katılımcı listesi
    members = conn.execute('''
        SELECT members.* FROM enrollments
        JOIN members ON enrollments.member_id = members.id
        WHERE enrollments.class_id = ?
    ''', (class_id,)).fetchall()

    # Toplam ödeme (bu sınıfa kayıtlı öğrencilerin yaptığı tüm ödemeler)
    member_ids = [m['id'] for m in members]
    if member_ids:
        placeholders = ','.join(['?'] * len(member_ids))
        total_payment = conn.execute(f'''
    SELECT SUM(amount) FROM payments
    WHERE member_id IN ({placeholders})
    AND payment_date LIKE ?
''', member_ids + [current_month + '%']).fetchone()[0]
    else:
        total_payment = 0

    # Eğitmen payı ve salon payı hesaplama
    trainer_share = 0
    salon_share = 0
    if trainer and trainer['share_percent']:
        trainer_share = round(total_payment * trainer['share_percent'] / 100, 2)
        salon_share = round(total_payment - trainer_share, 2)

    # Bu ay ödeme yapmayan sporcuları bul
    current_month = datetime.today().strftime('%Y-%m')
    paid_ids = conn.execute('''
        SELECT DISTINCT member_id FROM payments
        WHERE date LIKE ?
    ''', (current_month + '%',)).fetchall()
    paid_ids = [row['member_id'] for row in paid_ids]

    unpaid_members = [m for m in members if m['id'] not in paid_ids]

    conn.close()
    return render_template('class_detail.html',
        cls=cls,
        trainer=trainer,
        members=members,
        total_payment=total_payment,
        trainer_share=trainer_share,
        salon_share=salon_share,
        unpaid_members=unpaid_members
    )

@app.route('/delete_class/<int:class_id>', methods=['POST'])
def delete_class(class_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM classes WHERE id = ?', (class_id,))
    conn.commit()
    conn.close()
    return redirect('/classes')

@app.route('/delete_trainer/<int:trainer_id>', methods=['POST'])
def delete_trainer(trainer_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM trainers WHERE id = ?', (trainer_id,))
    conn.commit()
    conn.close()
    return redirect('/trainers')

@app.route('/edit_class/<int:class_id>')
def edit_class(class_id):
    conn = get_db_connection()
    cls = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    trainers = conn.execute('SELECT * FROM trainers').fetchall()
    conn.close()
    return render_template('edit_class.html', cls=cls, trainers=trainers)

@app.route('/update_class/<int:class_id>', methods=['POST'])
def update_class(class_id):
    data = {key: request.form[key] for key in request.form}
    conn = get_db_connection()
    conn.execute('''
        UPDATE classes SET
            name = ?, description = ?, day = ?, time = ?, trainer_id = ?
        WHERE id = ?
    ''', (
        data['name'], data['description'], data['day'], data['time'], data['trainer_id'], class_id
    ))
    conn.commit()
    conn.close()
    return redirect('/classes')

@app.route('/edit_trainer/<int:trainer_id>')
def edit_trainer(trainer_id):
    conn = get_db_connection()
    trainer = conn.execute('SELECT * FROM trainers WHERE id = ?', (trainer_id,)).fetchone()
    conn.close()
    return render_template('edit_trainer.html', trainer=trainer)

@app.route('/update_trainer/<int:trainer_id>', methods=['POST'])
def update_trainer(trainer_id):
    data = {key: request.form[key] for key in request.form}
    conn = get_db_connection()
    conn.execute('''
        UPDATE trainers SET
            name = ?, email = ?, phone = ?, share_percent = ?
        WHERE id = ?
    ''', (
        data['name'], data['email'], data['phone'], data['share_percent'], trainer_id
    ))
    conn.commit()
    conn.close()
    return redirect('/trainers')

@app.route('/add_payment/<int:member_id>')
def add_payment_form(member_id):
    conn = get_db_connection()
    member = conn.execute('SELECT * FROM members WHERE id = ?', (member_id,)).fetchone()

    # Son ödeme ayını bul
    last_payment = conn.execute('''
        SELECT payment_date FROM payments
        WHERE member_id = ?
        ORDER BY payment_date DESC LIMIT 1
    ''', (member_id,)).fetchone()

    from datetime import datetime, timedelta
    if last_payment and last_payment['payment_date']:
        try:
            last_date = datetime.strptime(last_payment['payment_date'], '%Y-%m-%d')
            next_month = (last_date.replace(day=1) + timedelta(days=32)).strftime('%Y-%m-%d')
        except ValueError:
            next_month = datetime.today().strftime('%Y-%m-%d')
    else:
        next_month = datetime.today().strftime('%Y-%m-%d')

    conn.close()
    return render_template('add_payment.html', member=member, suggested_month=next_month)

@app.route('/save_payment/<int:member_id>', methods=['POST'])
def save_payment(member_id):
    amount = request.form['amount']
    payment_date = request.form['payment_date']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    note = request.form['note']

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO payments (member_id, amount, payment_date, start_date, end_date, note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (member_id, amount, payment_date, start_date, end_date, note))
    conn.commit()
    conn.close()
    return redirect(f'/member/{member_id}')

@app.route('/reports')
def reports():
    from datetime import datetime
    current_month = datetime.today().strftime('%Y-%m')

    conn = get_db_connection()

    # Bu ayki tüm ödemeler
    payments = conn.execute('''
        SELECT payments.*, members.name AS member_name, classes.name AS class_name, trainers.name AS trainer_name, trainers.share_percent
        FROM payments
        JOIN members ON payments.member_id = members.id
        LEFT JOIN enrollments ON enrollments.member_id = members.id
        LEFT JOIN classes ON enrollments.class_id = classes.id
        LEFT JOIN trainers ON classes.trainer_id = trainers.id
        WHERE payment_date LIKE ?
    ''', (current_month + '%',)).fetchall()

    total_income = 0
    trainer_totals = {}
    salon_total = 0

    for p in payments:
        amount = p['amount'] or 0
        total_income += amount
        share = p['share_percent'] or 0
        trainer_share = round(amount * share / 100, 2)
        salon_share = round(amount - trainer_share, 2)

        if p['trainer_name']:
            if p['trainer_name'] not in trainer_totals:
                trainer_totals[p['trainer_name']] = 0
            trainer_totals[p['trainer_name']] += trainer_share

        salon_total += salon_share

    conn.close()
    return render_template('reports.html',
        payments=payments,
        total_income=total_income,
        trainer_totals=trainer_totals,
        salon_total=salon_total,
        current_month=current_month
    )

@app.route('/expiring')
def expiring_members():
    from datetime import datetime, timedelta

    today = datetime.today()
    warning_date = today + timedelta(days=7)  # 7 gün içinde bitenler

    conn = get_db_connection()
    members = conn.execute('SELECT * FROM members').fetchall()

    expiring = []

    for m in members:
        latest_payment = conn.execute('''
            SELECT end_date FROM payments
            WHERE member_id = ?
            ORDER BY end_date DESC LIMIT 1
        ''', (m['id'],)).fetchone()

        if latest_payment and latest_payment['end_date']:
            try:
                end_date = datetime.strptime(latest_payment['end_date'], '%Y-%m-%d')
                if today <= end_date <= warning_date:
                    expiring.append({
                        'name': m['name'],
                        'belt': m['belt_level'],
                        'end_date': latest_payment['end_date']
                    })
            except:
                continue

    conn.close()
    return render_template('expiring.html', expiring=expiring)

@app.route('/edit_payment/<int:payment_id>')
def edit_payment(payment_id):
    conn = get_db_connection()
    payment = conn.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
    member = conn.execute('SELECT * FROM members WHERE id = ?', (payment['member_id'],)).fetchone()
    conn.close()
    return render_template('edit_payment.html', payment=payment, member=member)

@app.route('/update_payment/<int:payment_id>', methods=['POST'])
def update_payment(payment_id):
    amount = request.form['amount']
    payment_date = request.form['payment_date']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    note = request.form['note']

    conn = get_db_connection()
    conn.execute('''
        UPDATE payments
        SET amount = ?, payment_date = ?, start_date = ?, end_date = ?, note = ?
        WHERE id = ?
    ''', (amount, payment_date, start_date, end_date, note, payment_id))
    conn.commit()
    conn.close()

    return redirect(f"/member/{request.form['member_id']}")

@app.route('/delete_payment/<int:payment_id>')
def delete_payment(payment_id):
    conn = get_db_connection()
    member_id = conn.execute('SELECT member_id FROM payments WHERE id = ?', (payment_id,)).fetchone()['member_id']
    conn.execute('DELETE FROM payments WHERE id = ?', (payment_id,))
    conn.commit()
    conn.close()
    return redirect(f"/member/{member_id}")

@app.route('/monthly_report')
def monthly_report():
    from datetime import datetime
    conn = get_db_connection()

    # Ay bazlı toplamlar
    monthly_totals = conn.execute('''
        SELECT SUBSTR(payment_date, 1, 7) AS month, SUM(amount) AS total
        FROM payments
        GROUP BY month
        ORDER BY month DESC
    ''').fetchall()

    # Kuşak bazlı toplamlar
    belt_totals = conn.execute('''
        SELECT members.belt_level, SUM(payments.amount) AS total
        FROM payments
        JOIN members ON payments.member_id = members.id
        GROUP BY members.belt_level
        ORDER BY total DESC
    ''').fetchall()

    # Sınıf bazlı toplamlar
    class_totals = conn.execute('''
        SELECT classes.name, SUM(payments.amount) AS total
        FROM payments
        JOIN members ON payments.member_id = members.id
        JOIN enrollments ON enrollments.member_id = members.id
        JOIN classes ON enrollments.class_id = classes.id
        GROUP BY classes.name
        ORDER BY total DESC
    ''').fetchall()

    conn.close()
    return render_template('monthly_report.html',
        monthly_totals=monthly_totals,
        belt_totals=belt_totals,
        class_totals=class_totals
    )

@app.route('/trainer/<int:trainer_id>')
def trainer_panel(trainer_id):
    from datetime import datetime
    current_month = datetime.today().strftime('%Y-%m')

    conn = get_db_connection()

    trainer = conn.execute('SELECT * FROM trainers WHERE id = ?', (trainer_id,)).fetchone()

    # Eğitmenin sınıfları
    classes = conn.execute('SELECT * FROM classes WHERE trainer_id = ?', (trainer_id,)).fetchall()

    # Eğitmenin öğrencileri ve bu ayki ödemeleri
    payments = conn.execute('''
        SELECT payments.*, members.name AS member_name, classes.name AS class_name
        FROM payments
        JOIN members ON payments.member_id = members.id
        JOIN enrollments ON enrollments.member_id = members.id
        JOIN classes ON enrollments.class_id = classes.id
        WHERE classes.trainer_id = ? AND payment_date LIKE ?
    ''', (trainer_id, current_month + '%')).fetchall()

    total_income = sum(p['amount'] or 0 for p in payments)
    share = trainer['share_percent'] or 0
    trainer_income = round(total_income * share / 100, 2)

    conn.close()
    return render_template('trainer_panel.html',
        trainer=trainer,
        classes=classes,
        payments=payments,
        trainer_income=trainer_income,
        current_month=current_month
    )

@app.route('/performance')
def performance_panel():
    conn = get_db_connection()

    # En çok ödeme yapan öğrenciler
    top_members = conn.execute('''
        SELECT members.name, SUM(payments.amount) AS total
        FROM payments
        JOIN members ON payments.member_id = members.id
        GROUP BY members.id
        ORDER BY total DESC
        LIMIT 10
    ''').fetchall()

    # En çok gelir getiren sınıflar
    top_classes = conn.execute('''
        SELECT classes.name, SUM(payments.amount) AS total
        FROM payments
        JOIN members ON payments.member_id = members.id
        JOIN enrollments ON enrollments.member_id = members.id
        JOIN classes ON enrollments.class_id = classes.id
        GROUP BY classes.id
        ORDER BY total DESC
        LIMIT 10
    ''').fetchall()

    # En çok kazanan eğitmenler
    top_trainers = conn.execute('''
        SELECT trainers.name, SUM(payments.amount * trainers.share_percent / 100.0) AS income
        FROM payments
        JOIN members ON payments.member_id = members.id
        JOIN enrollments ON enrollments.member_id = members.id
        JOIN classes ON enrollments.class_id = classes.id
        JOIN trainers ON classes.trainer_id = trainers.id
        GROUP BY trainers.id
        ORDER BY income DESC
        LIMIT 10
    ''').fetchall()

    conn.close()
    return render_template('performance.html',
        top_members=top_members,
        top_classes=top_classes,
        top_trainers=top_trainers
    )

from werkzeug.security import check_password_hash
from flask import flash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect('/dashboard')
            elif user['role'] == 'trainer':
                return redirect('/trainer_dashboard')
        else:
            flash("❌ Giriş başarısız. Lütfen kullanıcı adı veya şifreyi kontrol edin.")
            return redirect('/login')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    if session['role'] == 'trainer':
        return redirect(f"/trainer/{session['user_id']}")

    return render_template('dashboard.html')  # admin için tam panel

from werkzeug.security import generate_password_hash
from flask import flash

@app.route('/trainer_dashboard')
def trainer_dashboard():
    if 'user_id' not in session or session['role'] != 'trainer':
        return redirect('/login')
    return render_template('trainer_dashboard.html')

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        # Minimum şifre uzunluğu kontrolü
        if len(password) < 4:
            flash("Şifre en az 4 karakter olmalı.")
            return redirect('/add_user')

        # Veritabanında aynı kullanıcı adı var mı?
        conn = get_db_connection()
        existing = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            flash("Bu kullanıcı adı zaten mevcut.")
            return redirect('/add_user')

        # Şifreyi güvenli şekilde hash'le
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Kullanıcıyı ekle
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     (username, hashed_password, role))
        conn.commit()
        conn.close()

        flash("Kullanıcı başarıyla eklendi.")
        return redirect('/dashboard')

    return render_template('add_user.html')


@app.route('/trainer/<int:trainer_id>')
def trainer_profile (trainer_id):
    if 'user_id' not in session or session['role'] != 'trainer':
        return redirect('/login')

    if session['user_id'] != trainer_id:
        return "❌ Bu sayfaya erişim yetkiniz yok."

    conn = get_db_connection()

    trainer = conn.execute('SELECT * FROM users WHERE id = ?', (trainer_id,)).fetchone()

    classes = conn.execute('SELECT * FROM classes WHERE trainer_id = ?', (trainer_id,)).fetchall()

    members = conn.execute('''
        SELECT m.* FROM members m
        JOIN enrollments e ON m.id = e.member_id
        JOIN classes c ON e.class_id = c.id
        WHERE c.trainer_id = ?
    ''', (trainer_id,)).fetchall()

    conn.close()

    return render_template('trainer_panel.html',
                           trainer=trainer,
                           classes=classes,
                           members=members)








@app.route('/test_login', methods=['GET', 'POST'])
def test_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user:
            print("Veritabanı şifre:", user['password'])
            print("Girilen şifre:", password)
            print("Karşılaştırma sonucu:", check_password_hash(user['password'], password))

        if user and check_password_hash(user['password'], password):
            return "✅ Giriş başarılı"
        else:
            return "❌ Şifre yanlış veya kullanıcı yok"

    return '''
        <form method="post">
            <input name="username" placeholder="Kullanıcı Adı">
            <input name="password" placeholder="Şifre" type="password">
            <button type="submit">Test Et</button>
        </form>
    '''

@app.route('/hash/<sifre>')
def hash_sifre(sifre):
    from werkzeug.security import generate_password_hash
    hashli = generate_password_hash(sifre, method='pbkdf2:sha256')
    return f"Hashli şifre: {hashli}"


















@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.template_filter('calculate_age')
def calculate_age(birth_date_str):
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return "Bilinmiyor"


if __name__ == '__main__':
    app.run(debug=True, port=5001)