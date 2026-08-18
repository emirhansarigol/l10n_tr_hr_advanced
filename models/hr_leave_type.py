from odoo import models, fields

class HrLeaveType(models.Model):
    """ Odoo İzin Türlerini SGK Eksik Gün Kodları İle Eşleştirme """
    _inherit = 'hr.leave.type'

    sgk_missing_day_reason_id = fields.Many2one(
        'hr.missing.day.reason',
        string="SGK Eksik Gün Nedeni",
        help="Bu izin türü kullanıldığında SGK'ya bildirilecek eksik gün nedeni. Yıllık izin gibi eksik gün sayılmayacaklar için '00' kodunu seçin."
    )