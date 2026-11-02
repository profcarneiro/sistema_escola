from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.lgpd import router as lgpd_router
from app.routers.rooms import router as rooms_router
from app.routers.courses import router as courses_router
from app.routers.teachers import router as teachers_router
from app.routers.class_groups import router as class_groups_router
from app.routers.students import router as students_router
from app.routers.enrollments import router as enrollments_router

__all__ = [
    "auth_router",
    "users_router",
    "lgpd_router",
    "rooms_router",
    "courses_router",
    "teachers_router",
    "class_groups_router",
    "students_router",
    "enrollments_router",
]


