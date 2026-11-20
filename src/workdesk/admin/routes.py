from flask import render_template

from ..security import admin_only
from . import bp
from .hub import HUB_SECTIONS


@bp.get("")
@admin_only
def index():
    return render_template("admin/index.html", sections=HUB_SECTIONS)
