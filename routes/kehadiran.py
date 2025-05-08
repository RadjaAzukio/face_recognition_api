from flask import Blueprint, jsonify
from sqlalchemy.orm import Session
from models.mahasiswa_model import get_db, Kehadiran

kehadiran_bp = Blueprint('kehadiran', __name__, url_prefix='/kehadiran')

@kehadiran_bp.route('', methods=['GET'])
def lihat_kehadiran():
    db: Session = next(get_db())
    data_kehadiran = db.query(Kehadiran).all()
    hasil = []
    for kehadiran in data_kehadiran:
        hasil.append({
            'id': kehadiran.id,
            'mahasiswa_id': kehadiran.mahasiswa_id,
            'waktu_hadir': kehadiran.waktu_hadir.isoformat()
        })
    return jsonify(hasil)