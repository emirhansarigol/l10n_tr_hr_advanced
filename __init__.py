from . import models
from . import wizards
from odoo import api, SUPERUSER_ID


def account_settings(env):
    company_id = env.company.id

    # 1. HESAPLARI BUL
    hesap_335 = env['account.account'].search([('code', '=like', '335%'), ('company_id', '=', company_id)], limit=1)
    hesap_770 = env['account.account'].search([('code', '=like', '770%'), ('company_id', '=', company_id)], limit=1)
    hesap_360 = env['account.account'].search([('code', '=like', '360%'), ('company_id', '=', company_id)], limit=1)
    hesap_361 = env['account.account'].search([('code', '=like', '361%'), ('company_id', '=', company_id)], limit=1)

    hesap_602 = env['account.account'].search([('code', '=like', '602%'), ('company_id', '=', company_id)], limit=1)
    if not hesap_602:
        hesap_602 = env['account.account'].search([('code', '=like', '649%'), ('company_id', '=', company_id)], limit=1)

    if not hesap_335:
        return

    hesap_335.write({'reconcile': True})

    maas_yevmiyesi = env['account.journal'].search([('name', 'ilike', 'Maaş'), ('company_id', '=', company_id)],
                                                   limit=1)
    if not maas_yevmiyesi:
        maas_yevmiyesi = env['account.journal'].search(
            [('code', 'in', ['SLR', 'PAY']), ('company_id', '=', company_id)], limit=1)
    if maas_yevmiyesi:
        maas_yevmiyesi.write({'default_account_id': hesap_335.id})

    # =======================================================================
    # 2. ODOO NATIVE SGK KURALLARINI EZME (Yol/Yemek İstisnası & Mesai)
    # =======================================================================
    basic_rule = env['hr.salary.rule'].search([('code', '=', 'BASIC')], limit=1)
    if basic_rule:
        basic_rule.write({'sequence': 7})

    yol_rule = env['hr.salary.rule'].search([('code', '=', 'YOL_YARDIM')], limit=1)
    if yol_rule:
        yol_rule.write({'sequence': 8})

    yemek_rule = env['hr.salary.rule'].search([('code', '=', 'YEMEK_YARDIM')], limit=1)
    if yemek_rule:
        yemek_rule.write({'sequence': 9})

    ot_rule = env['hr.salary.rule'].search([('code', '=', 'OVERTIME')], limit=1)
    if ot_rule:
        ot_rule.write({'sequence': 9})

    basic_cat = basic_rule.category_id.code if basic_rule and basic_rule.category_id else 'BASIC'
    ot_cat = ot_rule.category_id.code if ot_rule and ot_rule.category_id else 'ALW'

    # SGK Matrahı (Tüm Zeka Burada Toplandı)
    # SGK Matrahı (Hiçbir kurala muhtaç olmayan, TANK GİBİ blok)
    sgk_ortak_blok = f"""
    try:
        sgk_matrahi = categories['{basic_cat}']

        # 1. YOL YARDIMI (Doğrudan puantajdan hesapla)
        yol_parasi = 0.0
        try:
            if 'WORK100' in worked_days and payslip.version_id:
                yol_parasi = worked_days['WORK100'].number_of_days * payslip.version_id.yol_yardim_ucreti
        except:
            pass

        # 2. FAZLA MESAİ (Doğrudan puantajdan hesapla)
        mesai_parasi = 0.0
        try:
            if 'OVERTIME' in worked_days:
                mesai_saati = worked_days['OVERTIME'].number_of_hours
                if mesai_saati > 0:
                    maas = payslip.version_id.wage if payslip.version_id else (payslip.contract_id.wage if payslip.contract_id else 0.0)
                    if maas > 0:
                        saatlik_ucret = (maas / 30.0) / 7.5
                        mesai_parasi = mesai_saati * saatlik_ucret * 1.5
        except:
            pass

        # 3. YEMEK YARDIMI İSTİSNASI (Doğrudan puantajdan hesapla)
        istisna_asan_yemek = 0.0
        try:
            if 'WORK100' in worked_days and payslip.version_id:
                yemek_parasi = worked_days['WORK100'].number_of_days * payslip.version_id.yemek_yardim_ucreti
                if yemek_parasi > 0:
                    try:
                        aylik_asgari_brut = payslip._rule_parameter('l10n_tr_gross_min_wage')
                    except:
                        aylik_asgari_brut = 20002.50
                    gunluk_istisna = (aylik_asgari_brut / 30.0) * 0.2365
                    toplam_istisna = gunluk_istisna * worked_days['WORK100'].number_of_days
                    if yemek_parasi > toplam_istisna:
                        istisna_asan_yemek = yemek_parasi - toplam_istisna
        except:
            pass

        # HEPSİNİ TOPLA
        sgk_matrahi += mesai_parasi + yol_parasi + istisna_asan_yemek
    except:
        sgk_matrahi = 0.0

    result_base = min(sgk_matrahi, payslip._rule_parameter('l10n_tr_ssi_base_ceiling'))
    """

    env['hr.salary.rule'].search([('code', '=', 'SSIEDED')]).write({
        'sequence': 10,
        'amount_python_compute': sgk_ortak_blok + "\nresult = -result_base\nresult_rate = 14"
    })
    env['hr.salary.rule'].search([('code', '=', 'SSIDED')]).write({
        'sequence': 11,
        'amount_python_compute': sgk_ortak_blok + "\nresult = -result_base\nresult_rate = 1"
    })
    env['hr.salary.rule'].search([('code', '=', 'SSICDED')]).write({
        'sequence': 12,
        'amount_python_compute': sgk_ortak_blok + "\nresult = result_base\nresult_rate = 20.5"
    })
    env['hr.salary.rule'].search([('code', '=', 'SSIUCDED')]).write({
        'sequence': 13,
        'amount_python_compute': sgk_ortak_blok + "\nresult = result_base\nresult_rate = 2"
    })
    env['hr.salary.rule'].search([('code', '=', 'GROSS')]).write({
        'sequence': 40,
        'amount_python_compute': f"result = categories['{basic_cat}'] + categories.get('{ot_cat}', 0.0) + categories.get('SSID', 0.0) + YTDGROSS"
    })

    # =======================================================================
    # 3. KUSURSUZ MUHASEBE EŞLEŞTİRME HARİTASI (Limitler Kaldırıldı!)
    # =======================================================================
    eslesmeler = {
        'BASIC': {'debit': hesap_770},
        'OVERTIME': {'debit': hesap_770},
        'YOL_YARDIM': {'debit': hesap_770},
        'YEMEK_YARDIM': {'debit': hesap_770},
        'SSICDED': {'debit': hesap_770, 'credit': hesap_361},
        'SSIUCDED': {'debit': hesap_770, 'credit': hesap_361},
        'TESVIK_5510': {'debit': hesap_361, 'credit': hesap_602},
        'SSIEDED': {'debit': hesap_361},
        'SSIDED': {'debit': hesap_361},
        'STAX': {'debit': hesap_360},
        'BTNET': {'credit': hesap_360},
        'NET': {'credit': hesap_335},
    }

    for kural_kodu, hesaplar in eslesmeler.items():
        kurallar = env['hr.salary.rule'].search([
            ('code', '=', kural_kodu),
            '|', ('struct_id.company_id', '=', False), ('struct_id.company_id', '=', company_id)
        ])
        for kural in kurallar:
            update_vals = {}
            if hesaplar.get('debit'): update_vals['account_debit'] = hesaplar['debit'].id
            if hesaplar.get('credit'): update_vals['account_credit'] = hesaplar['credit'].id
            kural.write(update_vals)