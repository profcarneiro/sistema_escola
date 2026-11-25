from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.lgpd import LGPDConsent, TermoTipo
from app.models.room import Room
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.class_group import ClassGroup, class_group_courses, FaixaEtaria, DiaSemana, Turno
from app.models.student import Aluno, TipoLiberacao
from app.models.guardian import Responsavel
from app.models.enrollment import Matricula, StatusMatricula, TipoCortesia
from app.models.discount_policy import (
    PaymentPlan,
    CourseDiscountRule,
    DiscountSettings,
    TipoPoliticaDesconto,
    CondicaoPagamento,
)
from app.models.waitlist import ListaEspera
from app.models.attendance import (
    Lesson,
    Attendance,
    ClassMakeUp,
    Evaluation,
    StatusPresenca,
    StatusReposicao,
    ConceitoAvaliacao,
)
from app.models.financial import (
    Invoice,
    Payment,
    Expense,
    FormaPagamento,
    StatusTitulo,
)

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
    "class_group_courses",
    "FaixaEtaria",
    "DiaSemana",
    "Turno",
    "Aluno",
    "TipoLiberacao",
    "Responsavel",
    "Matricula",
    "StatusMatricula",
    "TipoCortesia",
    "PaymentPlan",
    "CourseDiscountRule",
    "DiscountSettings",
    "TipoPoliticaDesconto",
    "CondicaoPagamento",
    "ListaEspera",
    "Lesson",
    "Attendance",
    "ClassMakeUp",
    "Evaluation",
    "StatusPresenca",
    "StatusReposicao",
    "ConceitoAvaliacao",
    "Invoice",
    "Payment",
    "Expense",
    "FormaPagamento",
    "StatusTitulo",
]



