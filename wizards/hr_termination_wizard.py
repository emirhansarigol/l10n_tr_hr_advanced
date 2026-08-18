from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrTerminationWizard(models.TransientModel):
    _name = 'hr.termination.wizard'
    _description = 'Contract Termination Wizard'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True)
    iskur_reason_id = fields.Many2one('hr.iskur.reason', string="Termination Reason", required=True)
    termination_date = fields.Date(string="Termination Date", default=fields.Date.context_today, required=True)

    has_notice_period_used = fields.Boolean(string="Notice Period Used?", default=False)

    severance_pay = fields.Float(string="Severance Pay", compute='_compute_compensations', store=True)
    notice_pay = fields.Float(string="Notice Pay", compute='_compute_compensations', store=True)

    # ================= MUHASEBE (ACCOUNTING) ALANLARI =================
    journal_id = fields.Many2one('account.journal', string="Journal", domain=[('type', '=', 'general')])
    expense_account_id = fields.Many2one('account.account', string="Expense Account (Debit)")
    payable_account_id = fields.Many2one('account.account', string="Payable Account (Credit)")

    @api.depends('employee_id', 'iskur_reason_id', 'termination_date', 'has_notice_period_used')
    def _compute_compensations(self):
        for wizard in self:
            sev_pay = 0.0
            not_pay = 0.0

            start_date = wizard.employee_id.contract_date_start

            if start_date and wizard.termination_date:
                worked_days = (wizard.termination_date - start_date).days

                # 365 Days Legal Rule
                if worked_days >= 365:
                    if wizard.iskur_reason_id and wizard.iskur_reason_id.code != '03':
                        worked_years = worked_days / 365.0
                        gross_wage_placeholder = 30000.0
                        sev_pay = worked_years * gross_wage_placeholder

                # Notice Pay
                if not wizard.has_notice_period_used and wizard.iskur_reason_id and wizard.iskur_reason_id.code != '03':
                    not_pay = 5000.0

            wizard.severance_pay = sev_pay
            wizard.notice_pay = not_pay

    def action_confirm_termination(self):
        """ çalışanı arşivler ve muhasebe kaydı oluşturur """

        total_compensation = self.severance_pay + self.notice_pay

        # Eğer tazminat çıkıyorsa Muhasebe Fişi (Journal Entry) oluştur
        if total_compensation > 0:
            if not self.journal_id or not self.expense_account_id or not self.payable_account_id:
                raise UserError(_("Please select Journal and Accounts to generate the compensation journal entry!"))

            # BÜYÜK DÜZELTME: Odoo 19 için address_home_id yerine work_contact_id kullanıyoruz!
            partner_id = self.employee_id.work_contact_id.id if self.employee_id.work_contact_id else False

            move_vals = {
                'journal_id': self.journal_id.id,
                'date': self.termination_date,
                'ref': _('Severance & Notice Pay - %s') % self.employee_id.name,
                'line_ids': [
                    # BORÇ (Gider) Satırı
                    (0, 0, {
                        'name': _('Severance and Notice Expense'),
                        'account_id': self.expense_account_id.id,
                        'debit': total_compensation,
                        'credit': 0.0,
                        'partner_id': partner_id,
                    }),
                    # ALACAK (Ödenecek) Satırı
                    (0, 0, {
                        'name': _('Severance and Notice Payable'),
                        'account_id': self.payable_account_id.id,
                        'debit': 0.0,
                        'credit': total_compensation,
                        'partner_id': partner_id,
                    }),
                ]
            }
            # Yevmiye kaydını (Taslak olarak) oluştur
            self.env['account.move'].create(move_vals)

        # Standart Fesih İşlemleri
        self.employee_id.departure_date = self.termination_date
        if self.employee_id.version_id:
            self.employee_id.version_id.date_end = self.termination_date

        self.employee_id.active = False

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Termination Complete'),
                'message': _('Employee terminated and Journal Entry created successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }