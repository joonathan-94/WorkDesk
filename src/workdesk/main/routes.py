from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from ..dashboard import requester_dashboard
from ..security import RoleCode, current_actor, has_any_role
from . import bp


@bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    return redirect(url_for("auth.login"))


@bp.get("/dashboard")
@login_required
def dashboard():
    """El dashboard de cada rol. El del personal sigue siendo provisional."""
    user = current_actor()

    if has_any_role(user, RoleCode.SOLICITANTE):
        return render_template(
            "main/dashboard_requester.html", data=requester_dashboard(user)
        )

    return render_template("main/dashboard.html")