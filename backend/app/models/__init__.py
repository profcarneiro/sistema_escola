from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.lgpd import LGPDConsent, TermoTipo
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, FaixaEtaria, DiaSemana, Turno

__all__ = [
    "User",
    "UserRole",
    "AuditLog",
    "LGPDConsent",
    "TermoTipo",
    "Room",
    "Course",
    "Teacher",
    "ClassGroup",
    "FaixaEtaria",
    "DiaSemana",
    "Turno",
]

