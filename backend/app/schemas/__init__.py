from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    TokenPayload,
    UserRoleEnum,
)
from app.schemas.lgpd import (
    LGPDConsentBase,
    LGPDConsentCreate,
    LGPDConsentResponse,
    LGPDConsentRevogar,
    TermoTipoEnum,
)
from app.schemas.room import RoomBase, RoomCreate, RoomUpdate, RoomResponse
from app.schemas.course import CourseBase, CourseCreate, CourseUpdate, CourseResponse
from app.schemas.teacher import TeacherBase, TeacherCreate, TeacherUpdate, TeacherResponse
from app.schemas.class_group import (
    ClassGroupBase,
    ClassGroupCreate,
    ClassGroupUpdate,
    ClassGroupResponse,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenPayload",
    "UserRoleEnum",
    "LGPDConsentBase",
    "LGPDConsentCreate",
    "LGPDConsentResponse",
    "LGPDConsentRevogar",
    "TermoTipoEnum",
    "RoomBase",
    "RoomCreate",
    "RoomUpdate",
    "RoomResponse",
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "TeacherBase",
    "TeacherCreate",
    "TeacherUpdate",
    "TeacherResponse",
    "ClassGroupBase",
    "ClassGroupCreate",
    "ClassGroupUpdate",
    "ClassGroupResponse",
]

