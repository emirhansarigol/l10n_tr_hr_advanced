from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    sgk_kullanici_adi = fields.Char(string="SGK Kullanıcı Adı (İşveren TC)", size=11)
    sgk_isyeri_kodu = fields.Char(string="SGK İşyeri Kodu")
    sgk_sistem_sifre = fields.Char(string="SGK Sistem Şifresi")
    sgk_isyeri_sifre = fields.Char(string="SGK İşyeri Şifresi")
    sgk_vergi_no = fields.Char(string="SGK Vergi No")
    sgk_isyeri_sicil = fields.Char(string="SGK İşyeri Sicil No", size=26)