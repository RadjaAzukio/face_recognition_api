from flask import Blueprint, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from flask_login import login_user
from models.mahasiswa_model import User, get_db  # Import User dari models.py

login_bp = Blueprint('login', __name__, url_prefix='/login')

@login_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db_session = get_db()  # Mendapatkan sesi database
        try:
            user = db_session.query(User).filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return jsonify({'success': True, 'message': 'Login berhasil'}), 200
            else:
                return jsonify({'success': False, 'message': 'Login gagal. Periksa username dan password Anda.'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': f'Terjadi kesalahan: {e}'}), 500
        finally:
            db_session.close()
    return render_template('login.html')  # Jika metode GET, render halaman login
