from flask import Blueprint, flash, redirect, render_template, request, jsonify, url_for
from flask_login import login_required
from models.mahasiswa_model import Mahasiswa, get_db
from sqlalchemy.orm import Session
from services.add_mahasiswa import add_new_mahasiswa
import os
import traceback
from services.face_recognition_service import encode_face
import threading
import io
import queue
import pickle

mahasiswa_bp = Blueprint('mahasiswa', __name__, url_prefix='/mahasiswa') # Membuat Blueprint untuk mahasiswa
add_new_mahasiswa = add_new_mahasiswa  # Import fungsi untuk menambahkan mahasiswa
# Buat queue untuk komunikasi antar-thread
result_queue = queue.Queue()

def add_new_mahasiswa(db_session, nim, nama, wajah_encoding):
    """Menambahkan mahasiswa baru ke database."""
    try:
        # Gunakan pickle.dumps untuk mengubah array NumPy menjadi binary data
        wajah_encoding_bytes = pickle.dumps(wajah_encoding)
        mahasiswa_baru = Mahasiswa(nim=nim, nama=nama, wajah_encoding=wajah_encoding_bytes)
        db_session.add(mahasiswa_baru)
        return mahasiswa_baru
    except Exception as e:
        print(f"Error in add_new_mahasiswa: {e}")
        return None

def process_and_add(nim, nama, image_data):
    """
    Fungsi ini dijalankan dalam thread terpisah untuk mengkodekan wajah dan menambahkan
    mahasiswa ke database.
    """
    db = next(get_db())
    try:
        # Gunakan BytesIO untuk mengubah data gambar menjadi objek seperti file
        image_file_like = io.BytesIO(image_data)
        wajah_encoding = encode_face(image_file_like)
        print(f"Hasil encode_face: {wajah_encoding}")
        if wajah_encoding is None:
            print("Wajah tidak terdeteksi atau gagal dienkode")
            result_queue.put({"success": False, "message": "Wajah tidak terdeteksi atau gagal dienkode"})  # Masukkan hasil ke queue
            return

        mahasiswa_baru = add_new_mahasiswa(db, nim, nama, wajah_encoding)
        if mahasiswa_baru:
            db.commit()
            pesan = f"Mahasiswa {mahasiswa_baru.nama} berhasil ditambahkan ke database (dalam thread)"
            print(pesan)
            result_queue.put({"success": True, "message": pesan})  # Masukkan hasil ke queue
        else:
            db.rollback()
            pesan = "Gagal menambahkan mahasiswa ke database (dalam thread)"
            print(pesan)
            result_queue.put({"success": False, "message": pesan})  # Masukkan hasil ke queue
    except Exception as e:
        error_message = f"Error dalam process_and_add (thread): {e}"
        print(f"Error dalam process_and_add (thread): {e}")
        print(traceback.format_exc())
        result_queue.put({"success": False, "message": error_message})  # Masukkan hasil ke queue
    finally:
        db.close() # Perbaikan: Gunakan db.close() untuk menutup sesi

@mahasiswa_bp.route('', methods=['POST']) # Gunakan mahasiswa_bp
def tambah_mahasiswa():
    try:
        if 'nim' not in request.form or 'nama' not in request.form:
            return jsonify({"error": "NIM dan Nama harus diisi"}), 400

        nim = request.form['nim']
        nama = request.form['nama']

        if 'image' not in request.files:
            return jsonify({"error": "Tidak ada file gambar yang diunggah"}), 400

        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"error": "Tidak ada nama file gambar"}), 400

        # Baca data gambar ke dalam memori
        image_data = image_file.read()

        # Mulai pengkodean wajah dan penyisipan database dalam thread terpisah.
        thread = threading.Thread(target=process_and_add, args=(nim, nama, image_data))
        thread.start()
        thread.join()  # Tunggu thread selesai

        # Dapatkan hasil dari queue
        result = result_queue.get()
        if result["success"]:
            return jsonify({"message": result["message"]}), 201  # 201 Created
        else:
            return jsonify({"error": result["message"]}), 500 # 500 Internal Server Error

    except Exception as e:
        error_message = f"Terjadi kesalahan: {str(e)}"
        print(traceback.format_exc())
        return jsonify({"error": error_message}), 500

@mahasiswa_bp.route('/retake_wajah/<int:mahasiswa_id>', methods=['GET', 'POST'])
@login_required
def retake_wajah(mahasiswa_id):
    """
    Rute untuk mengambil ulang foto wajah mahasiswa.
    """
    db_session = get_db()
    mahasiswa = db_session.query(Mahasiswa).filter_by(id=mahasiswa_id).first()

    if not mahasiswa:
        flash('Mahasiswa tidak ditemukan.', 'danger')
        return redirect(url_for('mahasiswa.daftar_mahasiswa'))

    if request.method == 'POST':
        if 'image' not in request.files:
            flash('Tidak ada file gambar yang diunggah.', 'danger')
            return redirect(request.url)

        image = request.files['image']
        if image.filename == '':
            flash('Tidak ada gambar yang dipilih.', 'danger')
            return redirect(request.url)

        # Validasi tipe file (opsional, tapi disarankan)
        if not allowed_file(image.filename):
            flash('Tipe file tidak valid. Hanya gambar yang diizinkan.', 'danger')
            return redirect(request.url)

        # Panggil fungsi untuk menyimpan foto dan update data wajah
        success, message = update_mahasiswa_face(mahasiswa, image)  # Gunakan fungsi yang baru dibuat
        if success:
            flash(message, 'success')
            return redirect(url_for('mahasiswa.daftar_mahasiswa'))  # Redirect ke halaman yang sesuai
        else:
            flash(message, 'danger')
            return redirect(request.url) # Tetap di halaman yang sama untuk mencoba lagi

    return render_template('retake_wajah.html', mahasiswa=mahasiswa)

def update_mahasiswa_face(mahasiswa, image):
        """
        Fungsi untuk memperbarui data wajah mahasiswa.
        """
        try:
            # Baca data gambar ke dalam memori
            image_data = image.read()
            image_file_like = io.BytesIO(image_data)
        
            # Encode wajah menggunakan layanan pengenalan wajah
            wajah_encoding = encode_face(image_file_like)
            if wajah_encoding is None:
                    return False, "Wajah tidak terdeteksi atau gagal dienkode."
        
            # Update encoding wajah mahasiswa
            mahasiswa.wajah_encoding = pickle.dumps(wajah_encoding)
            db = next(get_db())
            db.add(mahasiswa)
            db.commit()
            return True, "Data wajah mahasiswa berhasil diperbarui."
        except Exception as e:
            print(f"Error dalam update_mahasiswa_face: {e}")
            print(traceback.format_exc())
            return False, f"Terjadi kesalahan: {str(e)}"

def allowed_file(filename):
    """
    Fungsi untuk memeriksa apakah tipe file yang diunggah diizinkan.
    """
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Sesuaikan dengan tipe yang Anda inginkan
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
