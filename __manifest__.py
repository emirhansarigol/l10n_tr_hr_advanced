{
    'name': 'Türkiye İnsan Kaynakları Yerelleştirme Paketi (Gelişmiş)',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Localization',
    'summary': 'SGK, Teşvik, KVKK, Kıdem/İhbar ve İzin süreçlerinin Türkiye mevzuatına uyarlanması.',
    'description': """
        Türkiye mevzuatına uygun gelişmiş İK modülü.
        - KVKK süreçleri ve yetkilendirmeleri
        - İŞKUR çıkış kodları ve yasal parametreler
        - Türkiye'ye özgü bordrolama ve teşvik motoru altyapısı
    """,
    'author': 'Yazılım Firması / Stajyer',
    'website': 'https://www.firmawebresmi.com',
    'depends': [
        'base',
        'hr',
        'hr_payroll',
        'l10n_tr_hr_payroll',
        'hr_payroll_account', # Bordro-Muhasebe köprüsü
        'l10n_tr',            # Türkiye Tek Düzen Hesap Planı
        'account',
        'hr_holidays',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'data/iskur_rec_data.xml',
        'data/hr_payroll_rules.xml',
        'data/hr_default_data.xml',
        'wizards/hr_termination_wizard_views.xml',
        'reports/report_payslip_tr.xml',
        'reports/report_payslip_run_tr.xml',
        'reports/report_actions.xml',
        'views/hr_employee_views.xml',
        'views/res_company_views.xml',
        'views/hr_version_views.xml',
    ],
    'post_init_hook': 'account_settings',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}