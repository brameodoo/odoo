{
    'name': "Convenio de Adeudo",
    'version': "1.1", # Subí la versión
    'category': "Human Resources",
    'summary': "PMONTOS PAGOS, Gestión de convenios de adeudo para empleados",
    'author': "Grupo Brame",
    'license': 'LGPL-3', # Buena práctica
    
    # --- ¡CORRECCIÓN CRÍTICA! ---
    # Añadimos 'l10n_mx_edi' (para la conversión a letras) y 'mail' (para el chatter).
    'depends': ['base', 'hr', 'mail', 'l10n_mx_edi'],
    
    'data': [
        'security/ir.model.access.csv',
        'data/adeudo_convenio_sequence.xml',
        'report/adeudo_report.xml', # Correcto
        'views/adeudo_convenio_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
