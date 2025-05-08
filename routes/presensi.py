from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from models.mahasiswa_model import get_db, Mahasiswa, Kehadiran
from services.face_recognition_service import compare_faces, encode_face
import os
from datetime import datetime

presensi_bp = Blueprint('presensi', __name__, url_prefix='/presensi')

@presensi_bp.route('', methods=['POST'])
def proses_presensi():
    if 'image' not in request.files:
        return jsonify({"error": "Tidak ada file gambar yang diunggah"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "Tidak ada nama file gambar"}), 400

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
    kehadiran = Kehadiran(mahasiswa_id=mahasiswa_id, waktu_hadir=datetime.now())
    db.add(kehadiran)
    db.commit()