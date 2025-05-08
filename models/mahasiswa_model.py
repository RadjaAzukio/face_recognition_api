from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, relationship, scoped_session  # Import scoped_session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import pickle

# Base = declarative_base() # Jangan gunakan declarative_base() secara langsung dengan Flask-SQLAlchemy
db = SQLAlchemy()  # Inisialisasi SQLAlchemy tanpa argumen, akan di-bind ke app nanti


class Mahasiswa(db.Model):
    __tablename__ = 'mahasiswa'

    id = Column(Integer, primary_key=True)
    nim = Column(String(20), unique=True, nullable=False)
    nama = Column(String(100), nullable=False)
    # Menyimpan encoding sebagai binary data menggunakan pickle
    wajah_encoding = Column(LargeBinary, nullable=True)
    kehadiran = relationship('Kehadiran', backref='mahasiswa_rel',
                            lazy=True)  # Mengubah backref menjadi 'mahasiswa_rel'

    def __repr__(self):
        return f"<Mahasiswa(nim='{self.nim}', nama='{self.nama}')>"


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    is_registered = Column(Boolean, default=False)
    nim = Column(String(20), unique=True, nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Kehadiran(db.Model):
    __tablename__ = 'kehadiran'
    id = Column(Integer, primary_key=True)
    mahasiswa_id = Column(Integer, ForeignKey('mahasiswa.id'))
    waktu_hadir = Column(DateTime, default=datetime.now)
    mahasiswa = relationship(
        "Mahasiswa", back_populates="kehadiran")  #kehadiran sudah didefinisikan di Mahasiswa, jadi tidak perlu back_populates


# Konfigurasi Database SQLite (untuk contoh)
engine = create_engine('sqlite:///mahasiswa.db')

# Gunakan scoped_session
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        SessionLocal.remove()
