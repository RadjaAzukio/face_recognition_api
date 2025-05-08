from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from models.mahasiswa_model import get_db, Mahasiswa, Kehadiran
from services.face_recognition_service import compare_faces, encode_face, decode_image
import os
from datetime import datetime
import json

presensi_kamera_bp = Blueprint('presensi_kamera', __name__, url_prefix='/presensi_kamera')

@presensi_kamera_bp.route('', methods=['POST'])
def proses_presensi_kamera():
    if request.content_type == 'application/json':
        data = request.get_json()
        if 'image_base64' not in data:
            return jsonify({"error": "Tidak ada data gambar base64"}), 400
        image_data = decode_image(data['image_base64'])
        if image_data is None:
            return jsonify({"error": "Gagal mendekode gambar"}), 400
        image_file = image_data # Sekarang kita punya objek gambar PIL
    elif 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"error": "Tidak ada nama file gambar"}), 400
    else:
        return jsonify({"error": "Tidak ada gambar yang diterima"}), 400

    db: Session = next(get_db())
    all_mahasiswa = db.query(Mahasiswa).all()
    known_face_encodings_bytes = [m.wajah_encoding for m in all_mahasiswa if m.wajah_encoding]

    face_to_check_encoding_bytes = encode_face(image_file)

    if face_to_check_encoding_bytes:
        match, index = compare_faces(known_face_encodings_bytes, face_to_check_encoding_bytes)
        if match and index is not None:
            mahasiswa_terdeteksi = all_mahasiswa[index]
            catat_kehadiran(db, mahasiswa_terdeteksi.id)
            return jsonify({"message": f"Kehadiran {mahasiswa_terdeteksi.nama} tercatat pada {datetime.now()}"}), 200
        else:
            return jsonify({"message": "Wajah tidak dikenali"}), 404
    else:
        return jsonify({"error": "Tidak ada wajah terdeteksi dalam gambar"}), 400

def catat_kehadiran(db: Session, mahasiswa_id: int):
    """Fungsi untuk mencatat kehadiran mahasiswa ke dalam tabel kehadiran."""
    from models.mahasiswa_model import Kehadiran
    kehadiran = Kehadiran(mahasiswa_id=mahasiswa_id, waktu_hadir=datetime.now())
    db.add(kehadiran)
    db.commit()