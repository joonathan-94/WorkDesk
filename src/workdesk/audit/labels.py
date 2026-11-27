"""Los nombres que ve el Administrador en la pantalla de auditoría.

Una prueba exige que toda acción de `AuditAction` tenga el suyo: una acción nueva sin nombre
haría fallar la suite antes de llegar a la pantalla como un código en mayúsculas.
"""

from .service import AuditAction

AUDIT_ACTION_LABELS: dict[AuditAction, str] = {
    AuditAction.USUARIO_CREADO: "Usuario creado",
    AuditAction.USUARIO_MODIFICADO: "Datos de usuario modificados",
    AuditAction.USUARIO_ACTIVADO: "Usuario reactivado",
    AuditAction.USUARIO_DESACTIVADO: "Usuario desactivado",
    AuditAction.CAMBIO_ROL: "Cambio de rol",
    AuditAction.PASSWORD_RESTABLECIDA: "Contraseña restablecida",
    AuditAction.PASSWORD_CAMBIADA: "Contraseña cambiada por su titular",
    AuditAction.CATALOGO_CREADO: "Elemento de catálogo creado",
    AuditAction.CATALOGO_MODIFICADO: "Elemento de catálogo modificado",
    AuditAction.CATALOGO_ACTIVADO: "Elemento de catálogo reactivado",
    AuditAction.CATALOGO_DESACTIVADO: "Elemento de catálogo desactivado",
    AuditAction.GRUPO_CREADO: "Grupo creado",
    AuditAction.GRUPO_MODIFICADO: "Grupo modificado",
    AuditAction.GRUPO_ACTIVADO: "Grupo reactivado",
    AuditAction.GRUPO_DESACTIVADO: "Grupo desactivado",
    AuditAction.GRUPO_MIEMBRO_AGREGADO: "Técnico agregado a un grupo",
    AuditAction.GRUPO_MIEMBRO_RETIRADO: "Técnico retirado de un grupo",
    AuditAction.GRUPO_SUPERVISOR_DESIGNADO: "Supervisor designado en un grupo",
    AuditAction.GRUPO_SUPERVISOR_RETIRADO: "Supervisor retirado de un grupo",
    AuditAction.ESTADO_MODIFICADO: "Estado de ticket modificado",
    AuditAction.TRANSICION_ACTIVADA: "Transición habilitada",
    AuditAction.TRANSICION_DESACTIVADA: "Transición deshabilitada",
    AuditAction.CALENDARIO_LABORAL_GUARDADO: "Calendario laboral guardado",
    AuditAction.POLITICA_SLA_CREADA: "Política de SLA definida",
    AuditAction.POLITICA_SLA_MODIFICADA: "Política de SLA modificada",
    AuditAction.POLITICA_SLA_ACTIVADA: "Política de SLA reactivada",
    AuditAction.POLITICA_SLA_DESACTIVADA: "Política de SLA desactivada",
    AuditAction.CONFIGURACION_MODIFICADA: "Configuración modificada",
    AuditAction.CONFIGURACION_RESTABLECIDA: "Configuración restablecida",
    AuditAction.ARTICULO_CREADO: "Artículo creado",
    AuditAction.ARTICULO_MODIFICADO: "Artículo modificado",
    AuditAction.ARTICULO_PUBLICADO: "Artículo publicado",
    AuditAction.ARTICULO_DESPUBLICADO: "Artículo retirado de publicación",
    AuditAction.ARTICULO_DESTACADO: "Artículo destacado o sin destacar",
    AuditAction.ARTICULO_ACTIVADO: "Artículo reactivado",
    AuditAction.ARTICULO_DESACTIVADO: "Artículo desactivado",
    AuditAction.BLOQUEO_EDICION_LIBERADO: "Bloqueo de edición liberado",
    AuditAction.REASIGNACION_MASIVA: "Reasignación masiva",
    AuditAction.SLA_RECALCULADO: "SLA recalculado desde la consola",
    AuditAction.DATOS_EXPORTADOS: "Datos exportados",
}

# Los tipos de entidad que aparecen en `entidad_tipo`. Uno desconocido se muestra tal cual.
ENTITY_LABELS: dict[str, str] = {
    "usuario": "Usuario",
    "grupo": "Grupo",
    "categoria": "Categoría",
    "prioridad": "Prioridad",
    "ubicacion": "Ubicación",
    "motivo_espera": "Motivo de espera",
    "estado": "Estado",
    "transicion": "Transición",
    "calendario_laboral": "Calendario laboral",
    "politica_sla": "Política de SLA",
    "configuracion": "Configuración",
    "articulo_conocimiento": "Artículo",
    "ticket": "Ticket",
    "tecnico": "Técnico",
    "exportacion": "Exportación",
}


def action_label(code: str) -> str:
    try:
        return AUDIT_ACTION_LABELS[AuditAction(code)]
    except ValueError:
        return code


def entity_label(code: str | None) -> str:
    if code is None:
        return "—"

    return ENTITY_LABELS.get(code, code)
