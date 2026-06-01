# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class MsInvoice(models.Model):
    _name = 'ms.invoice'
    _description = 'SaaS Invoice'
    _inherit = ['mail.thread']
    _order = 'date_invoice desc'

    name           = fields.Char(readonly=True, default='New', copy=False)
    subscription_id = fields.Many2one('ms.subscription', required=True, ondelete='cascade')
    partner_id     = fields.Many2one('res.partner', string='Customer', required=True)
    template_id    = fields.Many2one('ms.plan.template', string='Plan')
    billing_cycle  = fields.Selection([('monthly', 'Monthly'), ('yearly', 'Yearly')])

    date_invoice   = fields.Date(default=fields.Date.context_today)
    due_date       = fields.Date()
    date_paid      = fields.Date()

    amount         = fields.Float(required=True, string='Amount (EGP)')
    state          = fields.Selection([
        ('draft',     'Draft'),
        ('sent',      'Sent'),
        ('paid',      'Paid'),
        ('overdue',   'Overdue'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    paymob_order_id       = fields.Char(copy=False)
    paymob_transaction_id = fields.Char(copy=False)
    paymob_payment_url    = fields.Char(string='Payment URL', copy=False)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ms.invoice') or 'New'
        return super().create(vals_list)

    def action_send(self):
        for inv in self:
            inv.state = 'sent'
            tmpl = self.env.ref('ms_saas_manager.email_template_invoice', raise_if_not_found=False)
            if tmpl:
                tmpl.send_mail(inv.id, force_send=True)

    def action_mark_paid(self):
        for inv in self:
            inv.write({'state': 'paid', 'date_paid': date.today()})
            sub = inv.subscription_id
            if sub.state not in ('active',):
                sub.action_activate()
            # Unsuspend DB if it was suspended
            if sub.db_id and sub.db_id.state == 'suspended':
                sub.db_id.action_unsuspend()
                sub.message_post(body=_('Database reactivated after payment confirmed.'))
            inv.message_post(body=_('Payment confirmed — subscription activated.'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_generate_paymob_link(self):
        self.ensure_one()
        paymob = self.env['ms.paymob']
        url = paymob.create_payment_link(self)
        if url:
            self.write({'paymob_payment_url': url, 'state': 'sent'})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Payment Link Ready'),
                    'message': _('Link sent to customer: %s') % url,
                    'type': 'success',
                    'sticky': True,
                },
            }

    @api.model
    def _cron_mark_overdue(self):
        today = date.today()
        self.search([
            ('state', 'in', ('draft', 'sent')),
            ('due_date', '<', today),
        ]).write({'state': 'overdue'})
