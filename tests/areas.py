"""Las áreas de la suite: qué módulo de tests pertenece a qué parte de WorkDesk.

Cada test recibe automáticamente el marcador de su área (`conftest.py`), de modo que se
puede ejecutar solo lo que corresponde a lo que se está tocando:

    python -m pytest -m sla
    python -m pytest -m "tickets or notifications"
    python -m pytest -m unit          # los que no usan la base de datos: segundos

Un módulo de tests nuevo **debe** añadirse aquí: si no pertenece a ningún área, la
recolección de pytest falla con un mensaje que lo dice (así ninguno queda fuera de las
ejecuciones por área). `tests/test_suite_infrastructure.py` comprueba además que esta
lista no apunta a módulos que ya no existen.
"""

AREAS: dict[str, tuple[str, ...]] = {
    # Aplicación, rutas, layout, formato, comandos y auditoría.
    "platform": (
        "test_app",
        "test_logging",
        "test_system",
        "test_layout",
        "test_formatting",
        "test_cli",
        "test_audit",
        "test_audit_screen",
        "test_route_protection",
        "test_route_authorization",
        "test_security_headers",
        "test_error_pages",
        "test_startup_safety",
        "test_data_integrity",
        "test_pages_smoke",
        "test_request_cost",
        "test_settings",
        "test_configuration",
        "test_settings_screens",
        "test_migrations",
        "test_docs_coherence",
        "test_frontend_conventions",
        "test_suite_infrastructure",
        "test_database_limits",
    ),
    # Autenticación, sesiones, contraseñas, roles y «Mi cuenta».
    "auth": (
        "test_auth",
        "test_authorization",
        "test_session_limits",
        "test_login_hardening",
        "test_auth_events",
        "test_passwords",
        "test_password_policy",
        "test_credentials",
        "test_account_password",
        "test_account_profile",
    ),
    "users": (
        "test_users_routes",
        "test_users_service",
        "test_users_manage_routes",
        "test_users_manage_service",
    ),
    # La base de conocimiento (v0.7.0).
    "knowledge": (
        "test_knowledge_model",
        "test_knowledge_screens",
        "test_ticket_knowledge",
        "test_duplicate_warning",
    ),
    "groups": ("test_groups",),
    # Los dashboards por rol y la carga de trabajo (v0.6.0).
    "dashboards": (
        "test_dashboard_requester",
        "test_workload_queries",
        "test_workload_screen",
        "test_dashboard_staff",
        "test_inactive_tickets",
    ),
    # Los reportes operativos y la exportación a CSV y XLSX (v0.8.0).
    "reports": ("test_report_queries", "test_report_screen", "test_exports"),
    # Los respaldos, la restauración, el estado del sistema y la retención (v0.8.0).
    "backups": ("test_backups", "test_restore", "test_system_status", "test_retention"),
    # Catálogos de tickets, motivos de espera, estados y transiciones.
    "catalogs": (
        "test_catalogs",
        "test_catalogs_routes",
        "test_catalogs_service",
        "test_wait_reasons",
        "test_states_admin",
        "test_state_actions",
    ),
    # El núcleo de tickets y todo su ciclo de vida.
    "tickets": (
        "test_ticket_assignment",
        "test_ticket_attachments",
        "test_ticket_comments",
        "test_ticket_edit_lock",
        "test_ticket_create_uploads",
        "test_ticket_lock_revoke",
        "test_ticket_location_required",
        "test_ticket_history",
        "test_ticket_history_visibility",
        "test_ticket_model",
        "test_ticket_policies",
        "test_ticket_relations",
        "test_ticket_reassignment",
        "test_reassignment_screen",
        "test_ticket_requesters",
        "test_ticket_resolution",
        "test_ticket_state_transitions",
        "test_tickets_edit_routes",
        "test_tickets_edit_service",
        "test_tickets_list_routes",
        "test_tickets_list_service",
        "test_tickets_assignment_filters",
        "test_tickets_routes",
        "test_tickets_service",
    ),
    # Tiempo laboral, calendario, políticas y períodos de SLA, y el planificador.
    "sla": (
        "test_worktime",
        "test_work_calendar",
        "test_work_calendar_routes",
        "test_sla_periods",
        "test_sla_indicators",
        "test_sla_business_rules",
        "test_sla_indicators_ui",
        "test_sla_switch",
        "test_sla_policies",
        "test_sla_policies_routes",
        "test_sla_policy_forms",
        "test_scheduler",
    ),
    "notifications": (
        "test_notification_settings",
        "test_notifications",
        "test_notifications_routes",
        "test_notification_events",
    ),
    # Los comandos que cargan datos de demostración.
    "seeds": (
        "test_seed_demo",
        "test_seed_demo_tickets_data",
        "test_seed_demo_tickets_load",
        "test_seed_demo_tickets_dates",
        "test_seed_demo_tickets_steps",
        "test_seed_demo_tickets_people",
        "test_seed_demo_tickets_lifecycle",
        "test_seed_demo_notifications",
    ),
}

AREA_BY_MODULE: dict[str, str] = {
    module: area for area, modules in AREAS.items() for module in modules
}
