"""Los datos que ya existen en la base y que el seed necesita encontrar."""



from ...extensions import db
from ...models import (
    Categoria,
    Estado,
    Grupo,
    MotivoEspera,
    Prioridad,
    TipoRelacionTicket,
    TransicionEstado,
    Ubicacion,
    User,
)
from ...models.categoria import FALLBACK_CATEGORY_CODE
from ...tickets.service import (
    INITIAL_STATE_CODE,
)
from ..demo_tickets_data import (
    FALLBACK_CATEGORY,
    PRIORITY_CODES,
)
from .common import (
    DemoTicketsError,
)


class Catalogs:
    """Usuarios, prioridades, categorías y ubicaciones ya existentes."""

    def __init__(
        self,
        users,
        priorities,
        categories,
        fallback,
        locations,
        wait_reasons,
        groups,
    ):
        self.users: dict[str, User] = users
        self.groups: dict[str, Grupo] = groups
        self.wait_reasons: dict[str, MotivoEspera] = wait_reasons
        self.priorities: dict[str, Prioridad] = priorities
        self.categories: dict[str, Categoria] = categories
        self.fallback: Categoria = fallback
        self.locations: dict[str, Ubicacion] = locations
        self.warnings: list[str] = []

    @classmethod
    def load(cls, tickets) -> "Catalogs":
        initial_state = db.session.scalar(
            db.select(Estado.id).where(Estado.codigo == INITIAL_STATE_CODE)
        )
        if initial_state is None:
            raise DemoTicketsError(
                "Faltan los catálogos iniciales. Ejecuta primero seed-catalogs."
            )

        needed = {demo_ticket.creado_por for demo_ticket in tickets}
        for demo_ticket in tickets:
            needed.update(demo_ticket.solicitantes)
            needed.update(step.actor for step in demo_ticket.ajustes)
            needed.update(
                step.asignar for step in demo_ticket.ajustes if step.asignar
            )
            needed.update(
                step.agregar_solicitante
                for step in demo_ticket.ajustes
                if step.agregar_solicitante
            )
            needed.update(
                step.retirar_solicitante
                for step in demo_ticket.ajustes
                if step.retirar_solicitante
            )

        users = {
            user.username: user
            for user in db.session.scalars(
                db.select(User).where(User.username.in_(needed))
            )
        }
        missing = sorted(needed - set(users))
        if missing:
            raise DemoTicketsError(
                "Faltan usuarios de demostración "
                f"({', '.join(missing[:4])}{'...' if len(missing) > 4 else ''}). "
                "Ejecuta primero seed-demo."
            )

        priorities = {
            priority.codigo: priority
            for priority in db.session.scalars(
                db.select(Prioridad).where(Prioridad.activo.is_(True))
            )
        }
        missing_priorities = [code for code in PRIORITY_CODES if code not in priorities]
        if missing_priorities:
            raise DemoTicketsError(
                "Faltan prioridades activas "
                f"({', '.join(missing_priorities)}). Ejecuta primero seed-catalogs."
            )

        active_categories = list(
            db.session.scalars(db.select(Categoria).where(Categoria.activo.is_(True)))
        )
        fallback = next(
            (c for c in active_categories if c.codigo == FALLBACK_CATEGORY_CODE),
            None,
        )
        if fallback is None:
            raise DemoTicketsError(
                "Falta la categoría de respaldo. Ejecuta primero seed-catalogs."
            )

        categories = {c.nombre.casefold(): c for c in active_categories}
        locations = {
            location.nombre.casefold(): location
            for location in db.session.scalars(
                db.select(Ubicacion).where(Ubicacion.activo.is_(True))
            )
        }

        wait_reasons = {
            reason.codigo: reason
            for reason in db.session.scalars(
                db.select(MotivoEspera).where(
                    MotivoEspera.activo.is_(True),
                    MotivoEspera.codigo.is_not(None),
                )
            )
        }

        uses_states = any(step.estado for demo in tickets for step in demo.ajustes)
        has_transitions = (
            db.session.scalar(db.select(db.func.count(TransicionEstado.id))) > 0
        )

        if uses_states and not has_transitions:
            raise DemoTicketsError(
                "Faltan las transiciones de estado. Ejecuta primero seed-catalogs."
            )

        # La demostración recorre todo el flujo: si el Administrador deshabilitó
        # alguna transición, el ticket que la necesita fallaría a mitad de la
        # carga. Mejor avisar antes, y con las transiciones a la vista.
        disabled = disabled_transitions() if uses_states else []

        if disabled:
            raise DemoTicketsError(
                "Hay transiciones deshabilitadas que la demostración necesita: "
                + "; ".join(disabled)
                + ". Habilítalas en Administración → Estados y transiciones y "
                "vuelve a ejecutar el comando."
            )

        uses_relations = any(
            step.relacionar or step.duplicado_de
            for demo in tickets
            for step in demo.ajustes
        )
        has_relation_types = (
            db.session.scalar(db.select(db.func.count(TipoRelacionTicket.id))) >= 2
        )

        if uses_relations and not has_relation_types:
            raise DemoTicketsError(
                "Faltan los tipos de relación entre tickets. Ejecuta primero "
                "seed-catalogs."
            )

        groups = {
            group.nombre.casefold(): group
            for group in db.session.scalars(
                db.select(Grupo).where(Grupo.activo.is_(True))
            )
        }

        return cls(
            users,
            priorities,
            categories,
            fallback,
            locations,
            wait_reasons,
            groups,
        )

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def category(self, name: str, *, fallback_ok: bool) -> Categoria | None:
        """Categoría por nombre. Si falta: la de respaldo (al crear) o None."""
        if name == FALLBACK_CATEGORY:
            return self.fallback

        found = self.categories.get(name.casefold())
        if found is not None:
            return found

        if fallback_ok:
            self.warn(
                f"Categoría «{name}» no encontrada: los tickets que la usan "
                f"quedaron en «{self.fallback.nombre}»."
            )
            return self.fallback

        self.warn(
            f"Categoría «{name}» no encontrada: se omitió la reclasificación "
            "de algunos tickets."
        )
        return None

    def group(self, name: str) -> Grupo | None:
        """Grupo por nombre. Es opcional: si falta o está desactivado el
        ticket queda sin grupo y se avisa (los crea `seed-demo`)."""
        found = self.groups.get(name.casefold())
        if found is None:
            self.warn(
                f"Grupo «{name}» no encontrado o desactivado: algunos tickets "
                "quedaron sin grupo. Ejecuta seed-demo para cargar los grupos."
            )
        return found

    def wait_reason(self, code: str | None) -> MotivoEspera | None:
        """Motivo de espera por código. Es opcional: si falta o está
        desactivado, la espera se registra sin motivo y se avisa."""
        if code is None:
            return None

        found = self.wait_reasons.get(code)
        if found is None:
            self.warn(
                f"Motivo de espera «{code}» no encontrado o desactivado: algunas "
                "esperas quedaron sin motivo."
            )
        return found

    def location(self, name: str | None) -> Ubicacion | None:
        if name is None:
            return None

        found = self.locations.get(name.casefold())
        if found is None:
            self.warn(
                f"Ubicación «{name}» no encontrada: los tickets que la usan "
                "quedaron sin ubicación."
            )
        return found


def disabled_transitions() -> list[str]:
    """Las transiciones que el Administrador deshabilitó, escritas como
    «Origen → Destino (Acción)» con los nombres visibles actuales."""
    disabled = db.session.scalars(
        db.select(TransicionEstado)
        .where(TransicionEstado.activa.is_(False))
        .order_by(TransicionEstado.id)
    )

    return [
        f"{t.estado_origen.nombre_visible} → {t.estado_destino.nombre_visible} "
        f"({t.accion_nombre})"
        for t in disabled
    ]
