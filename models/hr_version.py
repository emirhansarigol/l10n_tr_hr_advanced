from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    yol_yardim_ucreti = fields.Float(string='Yol Yardım Ücreti', default=150)
    yemek_yardim_ucreti = fields.Float(string="Günlük Yemek Yardım Ücreti")

    # YENİ ALAN: SGK Teşvik Kanun Numarası
    sgk_kanun_no = fields.Selection([
        ('00000', 'Teşviksiz / Emekli (00000)'),
        ('05510', '5510 Sayılı Kanun (%5 İndirim)'),
        ('06111', '6111 Sayılı Kanun (Genç ve Kadın İstihdamı)'),
        ('05746', '5746 Sayılı Kanun (Ar-Ge ve Teknokent)'),
        ('27103', '27103 Sayılı Kanun (İlave İstihdam)'),
    ], string="SGK Kanun No (Teşvik Türü)", default='05510', tracking=True)


class HrVersionWizard(models.TransientModel):
    _inherit = 'hr.version.wizard'

    def action_load_template(self):
        # Sihirbazın içindeki şablon seçtiğim o alanı otomatik buldum.
        sablon = False
        for field_name, field_def in self._fields.items():
            if field_def.type == 'many2one' and field_def.comodel_name == 'hr.version':
                sablon = getattr(self, field_name)
                break

        # Odoo'nun orijinal kopyalama işlemini çalıştır
        res = super(HrVersionWizard, self).action_load_template()

        # Oluşturulan yeni sözleşmeyi (versiyonu) yakaladım
        hedef_versiyon_id = False

        if isinstance(res, dict) and res.get('res_model') == 'hr.version' and res.get('res_id'):
            hedef_versiyon_id = res.get('res_id')

        if not hedef_versiyon_id:
            # Eğer fonksiyon ID döndürmediyse, bu çalışana ait "En Son Oluşturulan" versiyonu bul!
            if self.env.context.get('active_model') == 'hr.employee':
                employee_id = self.env.context.get('active_id')
                son_versiyon = self.env['hr.version'].search([('employee_id', '=', employee_id)], limit=1,
                                                             order='id desc')
                if son_versiyon:
                    hedef_versiyon_id = son_versiyon.id

        # Şablonu ve Yeni Versiyonu bulduysak, Yan Hakları VE TEŞVİK KODUNU KOPYALA!
        if sablon and hedef_versiyon_id:
            hedef_versiyon = self.env['hr.version'].browse(hedef_versiyon_id)
            hedef_versiyon.write({
                'yol_yardim_ucreti': sablon.yol_yardim_ucreti,
                'yemek_yardim_ucreti': sablon.yemek_yardim_ucreti,
                'sgk_kanun_no': sablon.sgk_kanun_no,  # Teşvik türü de yeni çalışana geçsin!
            })

        return res