import hashlib
import os
import pymysql
from flask import Flask, render_template, jsonify, session, request, redirect, url_for
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.secret_key = 'toko'

# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name='aqilfikri20',
    api_key='912145415255432',
    api_secret='C2XDAVLNiYqV82fmgyIqHS-5gUY'
)

# Konfigurasi Database (PyMySQL)
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "12345678",
    "database": "kuliner_db",
    "cursorclass": pymysql.cursors.DictCursor
}


# 🔐 Hash & Verify Password
def hash_password(password):
    salt = os.urandom(16)
    hashed_password = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
    return salt.hex() + ':' + hashed_password


def verify_password(stored_password, input_password):
    try:
        salt_hex, expected_hash = stored_password.split(':', 1)
        salt = bytes.fromhex(salt_hex)
    except (AttributeError, ValueError):
        return False
    actual_hash = hashlib.sha256(salt + input_password.encode('utf-8')).hexdigest()
    return actual_hash == expected_hash


def get_connection():
    """Utility untuk membuka koneksi ke database"""
    return pymysql.connect(**db_config)


# ==============================
# ROUTES
# ==============================

@app.route("/tambah_toko")
def tambah_toko():
    return render_template("tambah_toko.html")


@app.route('/tambah_menu/<int:toko_id>', methods=['GET', 'POST'])
def tambah_menu(toko_id):
    if request.method == 'POST':
        nama_menu = request.form['nama_menu']
        harga = request.form['harga']
        deskripsi = request.form['deskripsi']

        if 'img_menu' not in request.files or request.files['img_menu'].filename == '':
            return 'Gambar menu belum dipilih', 400

        file = request.files['img_menu']
        upload_result = cloudinary.uploader.upload(file)
        img_url = upload_result['secure_url']

        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """INSERT INTO table_menu (nama_menu, harga, deskripsi, img_menu, toko_id)
                     VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(sql, (nama_menu, harga, deskripsi, img_url, toko_id))
            conn.commit()
        conn.close()

        return redirect(url_for('detail_toko', id=toko_id))
    
    return render_template('tambah_menu.html', toko_id=toko_id)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/input_filter")
def input_filter():
    return redirect(url_for("home"))


@app.route("/page_login", methods=["GET", "POST"])
def page_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM table_admin WHERE email = %s", (email,))
            admin = cursor.fetchone()
        conn.close()
        
        if admin and verify_password(admin['password'], password):
            session['logged_in'] = True
            session['user'] = admin['email']
            return redirect(url_for('home'))
        else:
            return render_template('page_login.html', error="Email atau Password salah!")

    return render_template("page_login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route("/admin")
def admin():
    return redirect(url_for("page_login"))


@app.route("/")
def home():
    search_query = request.args.get('search', '')

    conn = get_connection()
    with conn.cursor() as cursor:
        if search_query:
            query = "SELECT * FROM table_toko WHERE nama_toko LIKE %s"
            cursor.execute(query, ('%' + search_query + '%',))
        else:
            cursor.execute("SELECT * FROM table_toko")
        data = cursor.fetchall()
    conn.close()

    return render_template("index.html", data=data, search_query=search_query)


@app.route('/toko', methods=['GET', 'POST'])
def toko():
    if request.method == 'GET':
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM table_toko")
            toko_list = cursor.fetchall()

            for toko in toko_list:
                cursor.execute("SELECT id, nama_menu, harga, deskripsi, img_menu FROM table_menu WHERE toko_id = %s", (toko['id'],))
                toko['menu'] = cursor.fetchall()
        conn.close()
        return jsonify(toko_list)

    elif request.method == 'POST':
        nama_toko = request.form['nama_toko']
        lokasi = request.form['lokasi']
        
        if 'img' not in request.files:
            return 'No image uploaded', 400
        file = request.files['img']

        if file.filename == '':
            return 'No selected file', 400

        upload_result = cloudinary.uploader.upload(file)
        img_url = upload_result['secure_url']

        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """INSERT INTO table_toko (nama_toko, lokasi, img) VALUES (%s, %s, %s)"""
            cursor.execute(sql, (nama_toko, lokasi, img_url))
            conn.commit()
        conn.close()

        return redirect(url_for('home'))


@app.route('/edit_toko/<int:id>', methods=['GET', 'POST'])
def edit_toko(id):
    conn = get_connection()
    with conn.cursor() as cursor:
        if request.method == 'GET':
            cursor.execute("SELECT * FROM table_toko WHERE id = %s", (id,))
            toko = cursor.fetchone()
            conn.close()
            return render_template('edit_toko.html', toko=toko)

        elif request.method == 'POST':
            nama_toko = request.form['nama_toko']
            lokasi = request.form['lokasi']

            if 'img' in request.files and request.files['img'].filename != '':
                file = request.files['img']
                upload_result = cloudinary.uploader.upload(file)
                img_url = upload_result['secure_url']
            else:
                img_url = request.form['existing_img']

            cursor.execute("""UPDATE table_toko
                              SET nama_toko=%s, lokasi=%s, img=%s
                              WHERE id=%s""",
                           (nama_toko, lokasi, img_url, id))
            conn.commit()
    conn.close()
    return redirect(url_for('home'))


@app.route('/edit_menu/<int:id>', methods=['GET', 'POST'])
def edit_menu(id):
    conn = get_connection()
    with conn.cursor() as cursor:
        if request.method == 'GET':
            cursor.execute("SELECT * FROM table_menu WHERE id = %s", (id,))
            menu = cursor.fetchone()
            conn.close()
            return render_template('edit_menu.html', menu=menu)

        elif request.method == 'POST':
            nama_menu = request.form['nama_menu']
            harga = request.form['harga']
            deskripsi = request.form['deskripsi']

            img_url = request.form.get('existing_img', '')
            if 'img_menu' in request.files and request.files['img_menu'].filename != '':
                file = request.files['img_menu']
                upload_result = cloudinary.uploader.upload(file)
                img_url = upload_result['secure_url']

            cursor.execute("""UPDATE table_menu
                              SET nama_menu=%s, harga=%s, deskripsi=%s, img_menu=%s
                              WHERE id=%s""",
                           (nama_menu, harga, deskripsi, img_url, id))
            conn.commit()

            cursor.execute("SELECT toko_id FROM table_menu WHERE id = %s", (id,))
            toko_id = cursor.fetchone()['toko_id']
    conn.close()
    return redirect(url_for('detail_toko', id=toko_id))


@app.route('/delete_toko/<int:id>', methods=['POST'])
def delete_toko(id):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM table_toko WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('home'))


@app.route('/detail_toko/<int:id>', methods=['GET'])
def detail_toko(id):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM table_toko WHERE id = %s", (id,))
        toko = cursor.fetchone()

        if not toko:
            conn.close()
            return redirect(url_for('home'))

        cursor.execute("SELECT * FROM table_menu WHERE toko_id = %s", (id,))
        menu = cursor.fetchall()
    conn.close()

    return render_template('detail_toko.html', toko=toko, menu=menu, toko_id=id)


@app.route('/delete_menu/<int:id>', methods=['POST'])
def delete_menu(id):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT toko_id FROM table_menu WHERE id = %s", (id,))
        menu = cursor.fetchone()
        if not menu:
            conn.close()
            return redirect(url_for('home'))
        toko_id = menu['toko_id']

        cursor.execute("DELETE FROM table_menu WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('detail_toko', id=toko_id))


@app.template_filter('rupiah')
def rupiah_format(value):
    try:
        value = int(value)
        return f"Rp{value:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@app.route("/register_admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM table_admin WHERE email = %s", (email,))
            admin = cursor.fetchone()

            if admin:
                conn.close()
                return render_template("register_admin.html", error="Email sudah terdaftar!")

            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO table_admin (email, password) VALUES (%s, %s)", 
                           (email, hashed_password))
            conn.commit()
        conn.close()
        return redirect(url_for("page_login"))
    
    return render_template("register_admin.html")


if __name__ == "__main__":
    app.run(debug=True)
