"""Predefined process templates.

Each template is a named list of stages so a manager can spin up a common
workflow without retyping every stage. Stages are (name, suggested_assignee)
tuples; the assignee is just a hint and can be edited or cleared in the dialog.

Kept as plain Python data (no DB table) on purpose: templates are part of the
app's configuration, not user data, so they version with the code.
"""

# Sentinel for "start from scratch" — no stages prefilled.
BLANK = 'Personalizado (en blanco)'

PROCESS_TEMPLATES = {
    'Manufactura estándar': [
        ('Recepción de materiales', 'Almacén'),
        ('En producción', 'Producción'),
        ('Control de calidad', 'Calidad'),
        ('Empaque', 'Logística'),
        ('Finalizado', ''),
    ],
    'Orden de servicio': [
        ('Solicitud recibida', 'Atención al cliente'),
        ('Diagnóstico', 'Técnico'),
        ('En reparación', 'Técnico'),
        ('Prueba final', 'Calidad'),
        ('Entrega', 'Logística'),
    ],
    'Desarrollo de producto': [
        ('Diseño', 'Ingeniería'),
        ('Prototipo', 'Ingeniería'),
        ('Validación', 'Calidad'),
        ('Producción piloto', 'Producción'),
        ('Lanzamiento', ''),
    ],
    'Logística / Envío': [
        ('Preparación de pedido', 'Almacén'),
        ('En tránsito', 'Transporte'),
        ('En aduana', 'Despacho'),
        ('Entregado', ''),
    ],
}


def template_names():
    """Names to show in the selector, with the blank option first."""
    return [BLANK] + list(PROCESS_TEMPLATES.keys())


def stages_for(template_name):
    """Return the (name, assignee) stage list for a template, or [] for blank
    / unknown names."""
    return list(PROCESS_TEMPLATES.get(template_name, []))
