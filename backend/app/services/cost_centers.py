from typing import Optional
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.financial import CostCenter, TipoCentroCusto


CENTROS_CUSTO_GERAIS = [
    ("ESTRUTURA", "Estrutura"),
    ("ADMINISTRATIVO", "Administrativo"),
    ("EVENTOS_WORKSHOPS", "Eventos/Workshops"),
    ("CORPORATIVO", "Corporativo"),
    ("MARKETING_CAPTACAO", "Marketing e captação"),
    ("ATELIE_PARCERIA", "Ateliê - Parceria"),
    ("SEM_CENTRO", "Sem centro (classificar)"),
]


def get_or_create_course_cost_center(db: Session, curso: Course) -> CostCenter:
    """Garante que um curso possua seu centro de custo dedicado e sincronizado."""
    cc = db.query(CostCenter).filter(CostCenter.curso_id == curso.id).first()
    if cc:
        changed = False
        if cc.nome != curso.nome:
            cc.nome = curso.nome
            changed = True
        if cc.ativo != bool(curso.ativo):
            cc.ativo = bool(curso.ativo)
            changed = True
        if changed:
            db.flush()
        return cc

    codigo = f"CURSO_{curso.id}"
    cc = db.query(CostCenter).filter(CostCenter.codigo == codigo).first()
    if cc:
        cc.curso_id = curso.id
        cc.nome = curso.nome
        cc.tipo = TipoCentroCusto.CURSO.value
        cc.ativo = bool(curso.ativo)
        db.flush()
        return cc

    cc = CostCenter(
        codigo=codigo,
        nome=curso.nome,
        tipo=TipoCentroCusto.CURSO.value,
        curso_id=curso.id,
        ativo=bool(curso.ativo),
    )
    db.add(cc)
    db.flush()
    return cc


def ensure_default_cost_centers(db: Session) -> None:
    """Cria os centros de custo gerais padrão e garante um centro por curso."""
    for codigo, nome in CENTROS_CUSTO_GERAIS:
        cc = db.query(CostCenter).filter(CostCenter.codigo == codigo).first()
        if not cc:
            db.add(CostCenter(
                codigo=codigo,
                nome=nome,
                tipo=TipoCentroCusto.GERAL.value,
                ativo=True,
            ))
    db.flush()

    cursos = db.query(Course).all()
    for curso in cursos:
        get_or_create_course_cost_center(db, curso)
    db.commit()


def get_general_cost_center_id(db: Session, codigo: str) -> Optional[int]:
    """Retorna o ID de um centro de custo geral pelo código, garantindo sua existência."""
    cc = db.query(CostCenter).filter(CostCenter.codigo == codigo).first()
    if cc:
        return cc.id
    for c_code, c_nome in CENTROS_CUSTO_GERAIS:
        if c_code == codigo:
            cc = CostCenter(
                codigo=c_code,
                nome=c_nome,
                tipo=TipoCentroCusto.GERAL.value,
                ativo=True,
            )
            db.add(cc)
            db.flush()
            return cc.id
    return None
