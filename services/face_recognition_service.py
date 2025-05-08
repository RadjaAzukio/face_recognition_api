import os
import face_recognition
import io
from PIL import Image
import numpy as np
import logging
import pickle
from flask import current_app

logger = logging.getLogger(__name__)

def encode_face(image_file_like):
    """
    Fungsi untuk mengenkode wajah dari file gambar.

    Args:
        image_file_like: File gambar seperti yang diterima dari Flask (misalnya, request.files['image']).

    Returns:
        bytes: Encoding wajah dalam bentuk bytes, atau None jika wajah tidak terdeteksi atau terjadi kesalahan.
    """
    try:
        # Load gambar menggunakan PIL
        img = Image.open(image_file_like)
        img_array = np.array(img)

        # Deteksi lokasi wajah
        face_locations = face_recognition.face_locations(img_array)
        if not face_locations:
            logger.warning("Wajah tidak terdeteksi dalam gambar.")
            return None

        # Encode wajah
        face_encoding = face_recognition.face_encodings(img_array, known_face_locations=face_locations)
        if not face_encoding:
            logger.warning("Gagal mengenkode wajah.")
            return None

        # Convert the face encoding to bytes
        face_encoding_bytes = pickle.dumps(face_encoding[0])  # Encode only the first face found
        return face_encoding_bytes
    except Exception as e:
        logger.error(f"Error saat mengenkode wajah: {e}")
        return None

def update_mahasiswa_face(mahasiswa, image):
    """
    Fungsi untuk menyimpan foto wajah mahasiswa dan memperbarui data wajah di database.

    Args:
        mahasiswa: Objek Mahasiswa yang akan diupdate.
        image: File gambar yang diunggah.

    Returns:
        Tuple: (success, message)
            success: True jika berhasil, False jika gagal.
            message: Pesan yang menjelaskan hasil operasi.
    """
    db_session = current_app.extensions['sqlalchemy'].db.session
    try:
        img = Image.open(io.BytesIO(image.read()))
        img_array = np.array(img)
        face_locations = face_recognition.face_locations(img_array)

        if not face_locations:
            return False, 'Wajah tidak terdeteksi dalam gambar.'

        wajah_encoding = face_recognition.face_encodings(img_array, known_face_locations=face_locations)[0]
        mahasiswa.wajah_encoding = pickle.dumps(wajah_encoding)

        # Simpan foto mahasiswa
        filename = f"mahasiswa_{mahasiswa.id}.jpg"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        filepath = os.path.join(upload_folder, filename)
        img.save(filepath)

        mahasiswa.foto_wajah = filename
        db_session.commit()
        return True, 'Foto wajah mahasiswa berhasil diperbarui.'
    except Exception as e:
        db_session.rollback()
        return False, f'Terjadi kesalahan: {e}'
    finally:
        db_session.close()
