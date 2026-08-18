from odoo import models, fields, api

class HrSgkSigortaTuru(models.Model):
    _name = 'hr.sgk.sigorta.turu'
    _description = 'SGK Sigorta Türleri'

    name = fields.Char(string="Sigorta Türü Adı", required=True)
    code = fields.Char(string="Kodu", size=2, required=True)

    def name_get(self):
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]


class HrSgkGorevKodu(models.Model):
    _name = 'hr.sgk.gorev.kodu'
    _description = 'SGK Görev Kodları'

    name = fields.Char(string="Görev Adı", required=True)
    code = fields.Char(string="Kodu", size=2, required=True)

    def name_get(self):
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]


class HrSgkBelgeTuru(models.Model):
    _name = 'hr.sgk.belge.turu'
    _description = 'SGK Belge Türleri'

    name = fields.Char(string="Belge Türü Adı", required=True)
    code = fields.Char(string="Kodu", size=2, required=True)

    def name_get(self):
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]


class HrMissingDayReason(models.Model):
    _name = 'hr.missing.day.reason'
    _description = 'SGK Missing Day Reasons'

    name = fields.Char(string="Reason", required=True)
    code = fields.Char(string="Code", size=2, required=True)

    def name_get(self):
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]


class HrOccupationCode(models.Model):
    _name = 'hr.occupation.code'
    _description = 'ISKUR Occupation Codes'

    name = fields.Char(string="Occupation Name", required=True)
    code = fields.Char(string="Code", required=True, help="Format: 9999.99")

    def name_get(self):
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]


class HrIskurReason(models.Model):
    _name = 'hr.iskur.reason'
    _description = 'ISKUR Termination Reasons'

    name = fields.Char(string="Description", required=True)
    code = fields.Char(string="ISKUR Code", size=2, required=True)


class HrBusinessLine(models.Model):
    _name = 'hr.business.line'
    _description = 'CSGB Business Lines'

    name = fields.Char(string="Business Line Name", required=True)
    code = fields.Char(string="Code", size=2, required=True)





