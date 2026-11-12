from flask import render_template

from ..security import RoleCode, roles_required
from . import bp
from .hub import HUB_SECTIONS


@bp.get("")
@roles_required(RoleCode.ADMINISTRADOR)
def index():
    return render_template("admin/index.html", sections=HUB_SECTIONS)
