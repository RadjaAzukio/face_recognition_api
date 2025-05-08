import logging
import os
import io
import traceback
from datetime import datetime
from PIL import Image
import face_recognition
import numpy as np
from flask import Flask, flash, render_template, request, jsonify, redirect, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, or_
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import scoped_session, sessionmaker
import pickle

# Konfigurasi Aplikasi
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mahasiswa.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Ganti dengan kunci rahasia yang kuat
app.config['UPLOAD_FOLDER'] = 'uploads' # Tambahkan konfigurasi upload folder

# Inisialisasi SQLAlchemy
db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'

# Fungsi untuk Manajemen Sesi Database
def get_db():
    """Mengembalikan sesi database yang terlingkup."""
    return scoped_session(sessionmaker(bind=db.engine))

@app.teardown_appcontext
def remove_session(*args, **kwargs):
    """Menghapus sesi database setelah konteks aplikasi berakhir."""
    db_session = get_db()
    db_session.remove()

@login_manager.user_loader
def load_user(user_id):
    """
    Fungsi ini diperlukan oleh Flask-Login untuk memuat objek User dari ID.
    """
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        logger.error(f"Error in load_user: {e}")
        traceback.print_exc()
        return None

# Import Modul Model
from models.mahasiswa_model import Kehadiran, Mahasiswa, User

# Import Modul Service
from services.add_mahasiswa import add_new_mahasiswa
from services.face_recognition_service import encode_face, update_mahasiswa_face # Import all functions

# Fungsi untuk memeriksa apakah tipe file yang diizinkan
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route untuk Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Rute untuk halaman login.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db_session = get_db()
        try:
            user = db_session.query(User).filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return jsonify({'success': True, 'message': 'Login berhasil'})
            else:
                return jsonify({'success': False, 'message': 'Login gagal. Periksa username dan password Anda.'}), 401
        except Exception as e:
            logger.error(f"Error in login: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Terjadi kesalahan: {e}'}), 500
        finally:
            db_session.close()
    return render_template('login.html')

# Route untuk Logout
@app.route('/logout')
@login_required
def logout():
    """
    Rute untuk logout.
    """
    logout_user()
    return redirect(url_for('login'))

@app.route('/registrasi_wajah_mahasiswa', methods=['POST'])
@login_required
def registrasi_wajah_mahasiswa():
    """
    Rute untuk registrasi wajah mahasiswa yang sudah terdaftar.
    Menerima NIM dan gambar wajah, kemudian menyimpan encoding wajah ke database.
    """
    db_session = get_db()
    try:
        nim = request.form.get('nim')
        image_data = request.files.get('image')

        if not nim or not image_data:
            return jsonify({'success': False, 'message': 'NIM dan Gambar harus diisi'}), 400

        # Baca data gambar dari file yang diupload
        image_file_like = io.BytesIO(image_data.read())

        # Encode wajah menggunakan fungsi dari face_recognition_service.py
        wajah_encoding_bytes = encode_face(image_file_like)
        if wajah_encoding_bytes is None:
            return jsonify({
                'success': False,
                'message': 'Wajah tidak terdeteksi atau gagal dienkode'
            }), 400

        # Cari mahasiswa berdasarkan NIM
        mahasiswa = db_session.query(Mahasiswa).filter_by(nim=nim).first()
        if not mahasiswa:
            return jsonify({'success': False, 'message': 'Mahasiswa dengan NIM tersebut tidak ditemukan'}), 404

        # Simpan encoding wajah ke database
        mahasiswa.wajah_encoding = wajah_encoding_bytes
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Registrasi wajah mahasiswa berhasil!'
        }), 200
    except Exception as e:
        logger.error(f"Error in registrasi_wajah_mahasiswa: {e}")
        traceback.print_exc()
        db_session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {e}'
        }), 500
    finally:
        db_session.close()

# Route untuk Registrasi Wajah (dan data mahasiswa)
@app.route('/registrasi', methods=['GET', 'POST'])
def registrasi_wajah():
    """
    Rute untuk registrasi wajah dan data mahasiswa.
    """
    if request.method == 'POST':
        nim = request.form['nim']
        nama = request.form['nama']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        image_data = request.files['image'].read()
        db_session = get_db()
        try:
            if db_session.query(User).filter_by(username=nim).first():
                return jsonify({'success': False, 'message': 'NIM sudah terdaftar.'}), 400
            image_file_like = io.BytesIO(image_data)
            wajah_encoding = encode_face(image_file_like)
            if wajah_encoding is None:
                return jsonify({"success": False, "message": "Wajah tidak terdeteksi atau gagal dienkode"}), 400
            new_user = User(username=nim, password=hashed_password, nim=nim, is_registered=True)
            db_session.add(new_user)
            db_session.commit()
            mahasiswa_baru = add_new_mahasiswa(db_session, nim, nama, wajah_encoding)
            if not mahasiswa_baru:
                db_session.rollback()
                return jsonify({'success': False, 'message': 'Gagal menambahkan data mahasiswa'}), 500
            db_session.commit()
            return jsonify({'success': True, 'message': 'Registrasi wajah dan data mahasiswa berhasil!'}), 201
        except Exception as e:
            logger.error(f"Error in registrasi_wajah: {e}")
            traceback.print_exc()
            db_session.rollback()
            return jsonify({'success': False, 'message': f'Terjadi kesalahan: {e}'}), 500
        finally:
            db_session.close()
    elif request.method == 'GET':
        return render_template('registrasi_wajah.html') # Render formulir registrasi
    return None # Sebagai fallback, meskipun seharusnya tidak tercapai

# Route untuk Memeriksa Login
@app.route('/check_login')
def check_login():
    """
    Rute untuk memeriksa apakah pengguna sudah login.
    """
    if current_user.is_authenticated:
        return jsonify({'logged_in': True}), 200
    else:
        return jsonify({'logged_in': False}), 401

# Route untuk Memeriksa Registrasi Wajah
@app.route('/check_registered')
@login_required
def check_registered():
    """
    Rute untuk memeriksa apakah wajah pengguna sudah terdaftar.
    """
    db_session = get_db()
    try:
        user = db_session.query(User).filter_by(id=current_user.id).first()
        if user:
            return jsonify({'registered': user.is_registered}), 200
        else:
            return jsonify({'registered': False}), 403
    finally:
        db_session.close()

# Route untuk Presensi
@app.route('/presensi', methods=['GET', 'POST'])
@login_required
def presensi():
    """
    Rute untuk proses presensi.
    """
    db_session = get_db()
    try:
        if request.method == 'POST':
            image_data = request.files['image'].read()
            try:
                image_file_like = io.BytesIO(image_data)
                img = Image.open(image_file_like)
                img_array = np.array(img)
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                return jsonify({'success': False, 'message': 'Gagal memproses gambar'}), 400

            face_locations = face_recognition.face_locations(img_array)
            if not face_locations:
                return jsonify({'success': False, 'message': 'Wajah tidak terdeteksi'}), 400

            try:
                wajah_encoding = face_recognition.face_encodings(img_array, known_face_locations=face_locations)[0]
            except Exception as e:
                logger.error(f"Error encoding face: {e}")
                return jsonify({'success': False, 'message': 'Gagal mengenkode wajah'}), 500

            user = db_session.query(User).filter_by(id=current_user.id).first()
            mahasiswa = db_session.query(Mahasiswa).filter_by(nim=user.nim).first()

            if mahasiswa:
                if mahasiswa.wajah_encoding:
                    try:
                        known_face_encoding = pickle.loads(mahasiswa.wajah_encoding)
                        results = face_recognition.compare_faces([known_face_encoding], wajah_encoding)
                        if results[0]:
                            kehadiran = Kehadiran(mahasiswa_id=mahasiswa.id)
                            db_session.add(kehadiran)
                            db_session.commit()
                            return jsonify({'success': True, 'message': 'Presensi berhasil'}), 200
                        else:
                            return jsonify({'success': False, 'message': 'Wajah tidak cocok'}), 400
                    except pickle.UnpicklingError as e:
                        logger.error(f"Error unpickling wajah_encoding: {e}")
                        mahasiswa.wajah_encoding = None
                        db_session.commit()
                        return jsonify({'success': False, 'message': f'Data wajah rusak, silahkan registrasi ulang untuk mahasiswa dengan NIM {mahasiswa.nim}'}), 500
                    except Exception as e:
                        logger.error(f"Error comparing faces: {e}")
                        return jsonify({'success': False, 'message': f'Terjadi kesalahan saat membandingkan wajah: {e}'}), 500
                else:
                    # Jika wajah belum terdaftar, simpan encoding wajah
                    try:
                        mahasiswa.wajah_encoding = pickle.dumps(wajah_encoding)
                        db_session.commit()
                        return jsonify({'success': True, 'message': 'Wajah berhasil didaftarkan dan presensi berhasil'}), 200
                    except Exception as e:
                        logger.error(f"Error saving wajah_encoding: {e}")
                        return jsonify({'success': False, 'message': f'Terjadi kesalahan saat menyimpan data wajah: {e}'}), 500
            else:
                return jsonify({'success': False, 'message': 'Mahasiswa tidak ditemukan'}), 400
        else:
            return render_template('presensi_kamera.html')
    except Exception as e:
        logger.error(f"Error in presensi: {e}")
        traceback.print_exc()
        db_session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {e}'}), 500
    finally:
        db_session.close()

def hapus_data_wajah_rusak():
    """
    Menghapus data wajah yang rusak dari tabel Mahasiswa.
    """
    with app.app_context():
        db_session = get_db() # Get the database session
        try:
            mahasiswa_rusak = db_session.query(Mahasiswa).filter(Mahasiswa.wajah_encoding.like(b'\x00%')).all()
            jumlah_rusak = len(mahasiswa_rusak)
            if jumlah_rusak > 0:
                logger.warning(f"Ditemukan {jumlah_rusak} data wajah yang rusak.")
                for mahasiswa in mahasiswa_rusak:
                    mahasiswa.wajah_encoding = None
                    db_session.commit()
                logger.info("Data wajah yang rusak telah dihapus.")
            else:
                logger.info("Tidak ditemukan data wajah yang rusak.")
        except Exception as e:
            logger.error(f"Error in hapus_data_wajah_rusak: {e}")
            db_session.rollback()
        finally:
            db_session.close()

@app.route('/retake_wajah/<int:mahasiswa_id>', methods=['GET', 'POST'])
@login_required
def retake_wajah(mahasiswa_id):
    """
    Rute untuk mengambil ulang foto wajah mahasiswa.
    """
    db_session = get_db()
    mahasiswa = db_session.query(Mahasiswa).filter_by(id=mahasiswa_id).first()

    if not mahasiswa:
        flash('Mahasiswa tidak ditemukan.', 'danger')
        return redirect(url_for('mahasiswa.daftar_mahasiswa')) # Asumsi ada route ini

    if request.method == 'POST':
        if 'image' not in request.files:
            flash('Tidak ada file gambar yang diunggah.', 'danger')
            return redirect(request.url)

        image = request.files['image']
        if image.filename == '':
            flash('Tidak ada gambar yang dipilih.', 'danger')
            return redirect(request.url)

        if not allowed_file(image.filename):
            flash('Tipe file tidak valid. Hanya gambar yang diizinkan.', 'danger')
            return redirect(request.url)

        success, message = update_mahasiswa_face(mahasiswa, image)
        if success:
            flash(message, 'success')
            return redirect(url_for('mahasiswa.daftar_mahasiswa'))
        else:
            flash(message, 'danger')
            return redirect(request.url) # stay on the same page

    return render_template('retake_wajah.html', mahasiswa=mahasiswa)

# Inisialisasi Database dan Jalankan Aplikasi
if __name__ == '__main__':
    # Pastikan direktori upload ada
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
        hapus_data_wajah_rusak()
    app.run(debug=True, host='0.0.0.0')
