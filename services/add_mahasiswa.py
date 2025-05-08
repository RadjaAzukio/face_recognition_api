from models.mahasiswa_model import Mahasiswa
from sqlalchemy.orm import Session
import traceback  # Import traceback

def add_new_mahasiswa(db: Session, nim: str, nama: str, wajah_encoding):
    """Menambahkan mahasiswa baru ke database."""
    try:  # Tambahkan try-except block
        if wajah_encoding:
            db_mahasiswa = Mahasiswa(nim=nim, nama=nama, wajah_encoding=wajah_encoding)
            db.add(db_mahasiswa)
            db.flush() #tambahan
            return db_mahasiswa
        else:
            return None  # Gagal mengenali wajah
    except Exception as e:
        print(traceback.format_exc())
        return None
