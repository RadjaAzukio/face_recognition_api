from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Konfigurasi Database SQLite
DATABASE_URL = "sqlite:///mahasiswa.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    # Contoh penggunaan (opsional)
    db = next(get_db())
    print("Koneksi ke database berhasil!")
    db.close()