from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import generate_password_hash
from models.mahasiswa_model import User, get_db  # Import User dari models.py

registrasi_bp = Blueprint('registrasi', __name__, url_prefix='/registrasi')

@registrasi_bp.route('/', methods=['GET', 'POST'])
def registrasi():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256') # gunakan metode yang lebih aman
        db_session = get_db() # Mendapatkan sesi dari fungsi get_db
        try:
            # Periksa apakah username sudah ada
            if db_session.query(User).filter_by(username=username).first():
                return jsonify({'success': False, 'message': 'Username sudah terdaftar.'}), 400

            new_user = User(username=username, password=hashed_password)
            db_session.add(new_user)
            db_session.commit()
            return jsonify({'success': True, 'message': 'Registrasi berhasil. Silakan login.'}), 201
        except Exception as e:
            db_session.rollback()
            return jsonify({'success': False, 'message': f'Terjadi kesalahan: {e}'}), 500
        finally:
            db_session.close()
    return render_template('registrasi.html') # Tampilkan halaman registrasi jika GET
