from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class HrEmployee(models.Model):
    """ Personel Modelinin Alanları ve Odoo İçi Kuralları """
    _inherit = 'hr.employee'

    # ================= TR YERELLEŞTİRME VE KVKK =================
    iskur_reason_id = fields.Many2one('hr.iskur.reason', string="ISKUR Termination Reason")
    kvkk_approved = fields.Boolean(string="KVKK Explicit Consent Signed", default=False, tracking=True)
    kvkk_approval_date = fields.Date(string="KVKK Approval Date")

    # ================= SGK İŞE GİRİŞ BİLDİRGE ALANLARI =================
    sgk_sigorta_turu_id = fields.Many2one('hr.sgk.sigorta.turu', string="SGK Sigorta Türü")
    sgk_gorev_kodu_id = fields.Many2one('hr.sgk.gorev.kodu', string="SGK Görev Kodu")
    sgk_meslek_kodu_id = fields.Many2one('hr.occupation.code', string="ISKUR Occupation Code")
    csgb_iskolu_id = fields.Many2one('hr.business.line', string="CSGB Business Line")
    sgk_eski_hukumlu = fields.Boolean(string="Ex-Convict", default=False)
    sgk_engelli = fields.Boolean(string="Disabled", default=False)
    sgk_ogrenim_kodu = fields.Selection([
        ('0', '0 - Bilinmeyen'),
        ('1', '1 - Okur yazar değil'),
        ('2', '2 - İlkokul'),
        ('4', '4 - Lise veya dengi'),
        ('5', '5 - Yüksek okul veya fakülte')
    ], string="Education Level Code", default='5')
    sgk_mezuniyet_bolumu = fields.Char(string="Graduation Department", size=100)
    sgk_mezuniyet_yili = fields.Integer(string="Graduation Year")
    sgk_kismi_sureli = fields.Boolean(string="Part-Time?", default=False)
    sgk_kismi_sureli_gun = fields.Integer(string="Part-Time Days")

    ssnid=fields.Char(string="SGK Sicil No")

    # ================= ÇIKIŞ BORDROSU VE EKSİK GÜN ALANLARI =================
    sgk_hakedilen_ucret = fields.Float(string="Son Ay Hak Edilen Ücret")
    sgk_prim_ikramiye = fields.Float(string="Prim ve İkramiyeler")
    sgk_eksik_gun_sayisi = fields.Integer(string="Çıkış Ayı Eksik Gün Sayısı")
    sgk_eksik_gun_nedeni_id = fields.Many2one('hr.missing.day.reason', string="Eksik Gün Nedeni")
    is_sgk_exit_generated = fields.Boolean(string="SGK Exit Generated", default=False, tracking=True)

    # ================= İŞE GİRİŞ EVRAKLARI =================
    doc_id_copy_fname = fields.Char(string="ID Copy Filename")
    doc_residence_cert = fields.Binary(string="Residence Certificate", attachment=True)
    doc_residence_cert_fname = fields.Char(string="Residence Certificate Filename")
    doc_criminal_record = fields.Binary(string="Criminal Record", attachment=True)
    doc_criminal_record_fname = fields.Char(string="Criminal Record Filename")
    doc_health_report = fields.Binary(string="Health Report", attachment=True)
    doc_health_report_fname = fields.Char(string="Health Report Filename")
    doc_diploma = fields.Binary(string="Diploma / Graduation Certificate", attachment=True)
    doc_diploma_fname = fields.Char(string="Diploma Filename")
    doc_sgk_entry = fields.Binary(string="SGK Entry Declaration", attachment=True)
    doc_sgk_entry_fname = fields.Char(string="SGK Entry Filename")
    doc_military_cert = fields.Binary(string="Military Status Certificate", attachment=True)
    doc_military_cert_fname = fields.Char(string="Military Cert Filename")
    doc_blood_group = fields.Binary(string="Blood Group Card", attachment=True)
    doc_blood_group_fname = fields.Char(string="Blood Group Filename")
    doc_photo = fields.Binary(string="Passport Photo", attachment=True)
    doc_photo_fname = fields.Char(string="Photo Filename")
    doc_sgk_exit = fields.Binary(string="SGK Exit Declaration", attachment=True)
    doc_sgk_exit_fname = fields.Char(string="SGK Exit Filename")

    # ================= SGK BELGE TÜRÜ & ÖNCEKİ DÖNEM =================
    sgk_belge_turu_id = fields.Many2one('hr.sgk.belge.turu', string="Belge Türü (Bulunduğumuz Dönem)")
    sgk_onceki_belge_turu_id = fields.Many2one('hr.sgk.belge.turu', string="Önceki Dönem Belge Türü")
    sgk_onceki_hakedilen_ucret = fields.Float(string="Önceki Dönem Hak Edilen Ücret")
    sgk_onceki_prim_ikramiye = fields.Float(string="Önceki Dönem Prim/İkramiye")
    sgk_onceki_eksik_gun_sayisi = fields.Integer(string="Önceki Dönem Eksik Gün Sayısı")
    sgk_onceki_eksik_gun_nedeni_id = fields.Many2one('hr.missing.day.reason', string="Önceki Dönem Eksik Gün Nedeni")

    # ================= ODOO BUTON KONTROLLERİ VE REFERANSLAR =================
    is_sgk_entry_generated = fields.Boolean(string="SGK Entry Generated", default=False, tracking=True)
    show_sgk_entry_btn = fields.Boolean(compute='_compute_button_visibilities')
    show_sgk_exit_btn = fields.Boolean(compute='_compute_button_visibilities')
    show_termination_btn = fields.Boolean(compute='_compute_button_visibilities')
    sgk_giris_referans = fields.Char(string="İşe Giriş Referans Kodu", readonly=True, copy=False)
    sgk_cikis_referans = fields.Char(string="İşten Çıkış Referans Kodu", readonly=True, copy=False)

    # ================= NAKİL (TRANSFER) İŞLEMLERİ =================
    sgk_nakil_gelis = fields.Boolean(string="Aynı İşverenden Nakil Geldi?", default=False)
    sgk_nakil_geldigi_sicil = fields.Char(string="Nakil Geldiği İşyeri Sicil", size=26)
    sgk_nakil_gidis_sicil = fields.Char(string="Nakil Gideceği İşyeri Sicil", size=26)

    @api.depends('is_sgk_entry_generated', 'version_id', 'version_id.date_end', 'departure_date', 'active',
                 'is_sgk_exit_generated')
    def _compute_button_visibilities(self):
        today = fields.Date.today()
        for emp in self:
            emp.show_sgk_entry_btn = bool(emp.version_id) and not emp.is_sgk_entry_generated

            end_date = emp.departure_date or (emp.version_id and emp.version_id.date_end)
            show_exit = False
            if emp.is_sgk_entry_generated and end_date and not emp.is_sgk_exit_generated:
                deadline_date = end_date + timedelta(days=10)
                if today <= deadline_date:
                    show_exit = True

            emp.show_sgk_exit_btn = show_exit
            emp.show_termination_btn = emp.is_sgk_entry_generated and emp.active

    @api.constrains('identification_id')
    def _check_tc_identity_number(self):
        for employee in self:
            if employee.identification_id:
                if len(employee.identification_id) != 11 or not employee.identification_id.isdigit():
                    raise ValidationError(
                        _("Geçersiz T.C. Kimlik Numarası. Tam olarak 11 haneli olmalı ve sadece rakam içermelidir."))

    @api.constrains('sgk_kismi_sureli', 'sgk_kismi_sureli_gun')
    def _check_part_time_days(self):
        for emp in self:
            if emp.sgk_kismi_sureli and (emp.sgk_kismi_sureli_gun < 1 or emp.sgk_kismi_sureli_gun > 29):
                raise ValidationError(_("Kısmi süreli (Part-time) gün sayısı 1 ile 29 arasında olmalıdır!"))

    @api.onchange('sgk_eksik_gun_sayisi', 'departure_date')
    def _onchange_eksik_gun_hesapla(self):
        for emp in self:
            aylik_maas = getattr(emp, 'wage', 0.0)
            if not aylik_maas and hasattr(emp, 'version_id') and emp.version_id:
                aylik_maas = getattr(emp.version_id, 'wage', 0.0)

            if not aylik_maas or aylik_maas <= 0:
                emp.sgk_hakedilen_ucret = 0.0
                if emp.sgk_eksik_gun_sayisi and emp.sgk_eksik_gun_sayisi > 0:
                    return {
                        'warning': {
                            'title': _("Maaş Bilgisi Bulunamadı!"),
                            'message': _("Odoo 19 Sözleşmeler/Bordro sekmesinde tanımlı bir maaş bulunamadı.")
                        }
                    }
                continue

            gunluk_ucret = aylik_maas / 30.0
            if emp.departure_date:
                sgk_prim_gunu = emp.departure_date.day
                calisilan_gun = max(0, sgk_prim_gunu - (emp.sgk_eksik_gun_sayisi or 0))
                emp.sgk_hakedilen_ucret = calisilan_gun * gunluk_ucret
            else:
                calisilan_gun = max(0, 30 - (emp.sgk_eksik_gun_sayisi or 0))
                emp.sgk_hakedilen_ucret = calisilan_gun * gunluk_ucret

    def action_fetch_missing_days_from_leaves(self):
        for emp in self:
            if not emp.departure_date:
                raise UserError(_("Önce personelin 'Çıkış Tarihi'ni (departure_date) girmelisiniz"))

            cikis_tarihi = emp.departure_date
            bulundugumuz_donem_ay = cikis_tarihi.month
            bulundugumuz_donem_yil = cikis_tarihi.year
            onceki_donem_tarihi = cikis_tarihi - relativedelta(months=1)
            onceki_donem_ay = onceki_donem_tarihi.month
            onceki_donem_yil = onceki_donem_tarihi.year
            baslangic_tarihi = onceki_donem_tarihi.replace(day=1)

            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', cikis_tarihi),
                ('request_date_to', '>=', baslangic_tarihi)
            ])

            bulundugumuz_ay_eksik_gun = 0
            bulundugumuz_ay_nedenler = set()
            onceki_ay_eksik_gun = 0
            onceki_ay_nedenler = set()

            for leave in leaves:
                sgk_neden = leave.holiday_status_id.sgk_missing_day_reason_id
                if not sgk_neden or sgk_neden.code == '00':
                    continue

                current_date = leave.request_date_from
                while current_date <= leave.request_date_to:
                    if current_date > cikis_tarihi:
                        break
                    if current_date.month == bulundugumuz_donem_ay and current_date.year == bulundugumuz_donem_yil:
                        bulundugumuz_ay_eksik_gun += 1
                        bulundugumuz_ay_nedenler.add(sgk_neden)
                    elif current_date.month == onceki_donem_ay and current_date.year == onceki_donem_yil:
                        onceki_ay_eksik_gun += 1
                        onceki_ay_nedenler.add(sgk_neden)
                    current_date += timedelta(days=1)

            birden_fazla_kodu = self.env['hr.missing.day.reason'].search([('code', '=', '12')], limit=1)

            emp.sgk_eksik_gun_sayisi = bulundugumuz_ay_eksik_gun
            emp.sgk_eksik_gun_nedeni_id = birden_fazla_kodu.id if len(bulundugumuz_ay_nedenler) > 1 else (
                list(bulundugumuz_ay_nedenler)[0].id if len(bulundugumuz_ay_nedenler) == 1 else False)

            emp.sgk_onceki_eksik_gun_sayisi = onceki_ay_eksik_gun
            emp.sgk_onceki_eksik_gun_nedeni_id = birden_fazla_kodu.id if len(onceki_ay_nedenler) > 1 else (
                list(onceki_ay_nedenler)[0].id if len(onceki_ay_nedenler) == 1 else False)

            emp._onchange_eksik_gun_hesapla()

            onceki_ay_bitis = cikis_tarihi.replace(day=1) - relativedelta(days=1)
            onceki_ay_baslangic = onceki_ay_bitis.replace(day=1)
            onceki_bordro = self.env['hr.payslip'].search([
                ('employee_id', '=', emp.id),
                ('state', 'in', ['done', 'paid']),
                ('date_to', '>=', onceki_ay_baslangic),
                ('date_to', '<=', onceki_ay_bitis)
            ], limit=1, order='date_to desc')

            if onceki_bordro:
                brut_satir = onceki_bordro.line_ids.filtered(lambda l: l.code == 'GROSS')
                emp.sgk_onceki_hakedilen_ucret = brut_satir.total if brut_satir else onceki_bordro.basic_wage
                emp.sgk_onceki_prim_ikramiye = 0.0
            else:
                emp.sgk_onceki_hakedilen_ucret = 0.0
                emp.sgk_onceki_prim_ikramiye = 0.0

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Başarılı!'),
                    'message': _(
                        'Eksik günler İzinler modülünden çekildi ve önceki dönem bordro ücretleri hesaplandı.'),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

    def action_terminate_contract(self):
        for employee in self:
            if not employee.contract_date_start:
                raise UserError(_("Bu personelin sözleşme başlangıç tarihi yok. Tazminat hesaplanamaz!"))
            return {
                'name': _('Sözleşmeyi Feshet ve Tazminat Hesapla'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.termination.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_employee_id': employee.id}
            }