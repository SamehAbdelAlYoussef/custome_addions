# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import re
import logging

_logger = logging.getLogger(__name__)


class MsSubscription(models.Model):
    _name = 'ms.subscription'
    _description = 'SaaS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name         = fields.Char(string='Reference', readonly=True, default='New', copy=False)

    # ── Customer ────────────────────────────────────────────────────
    partner_id   = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    email        = fields.Char(related='partner_id.email', store=True)
    phone        = fields.Char(related='partner_id.phone', store=True)
    company_name = fields.Char(string='Company Name')

    # ── Plan ────────────────────────────────────────────────────────
    template_id    = fields.Many2one('ms.plan.template', string='Plan', required=True, tracking=True)
    billing_cycle  = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly',  'Yearly'),
    ], default='monthly', required=True, tracking=True)
    extra_user_packs = fields.Integer(string='Extra User Packs (×5)', default=0)
    total_users      = fields.Integer(compute='_compute_totals', store=True, string='Total Users')
    total_amount     = fields.Float(compute='_compute_totals',  store=True, string='Amount (EGP)')

    # ── Database ────────────────────────────────────────────────────
    db_name      = fields.Char(string='Database Name', readonly=True, copy=False)
    db_id        = fields.Many2one('ms.managed.db', string='Managed DB', readonly=True)
    subdomain    = fields.Char(string='Subdomain', readonly=True,
                               help='e.g. acme → acme.msolutions-eg.com')
    url          = fields.Char(string='Customer URL', compute='_compute_url')

    # ── Dates ───────────────────────────────────────────────────────
    date_start       = fields.Date(default=fields.Date.context_today, tracking=True)
    trial_end        = fields.Date(compute='_compute_trial_end', store=True)
    date_next_invoice = fields.Date(string='Next Invoice Date', tracking=True)
    date_end         = fields.Date(string='End Date', tracking=True)

    # ── State ───────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',     'Draft'),
        ('trial',     'Free Trial'),
        ('active',    'Active'),
        ('paused',    'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired',   'Expired'),
    ], default='draft', tracking=True, copy=False)

    # ── Invoices ────────────────────────────────────────────────────
    invoice_ids    = fields.One2many('ms.invoice', 'subscription_id', string='Invoices')
    invoice_count  = fields.Integer(compute='_compute_invoice_count')
    total_paid     = fields.Float(compute='_compute_invoice_count', string='Total Paid')

    notes = fields.Text()

    # ── Email Verification ────────────────────────────────────────
    verify_token    = fields.Char(string='Verification Token', copy=False, index=True)
    email_verified  = fields.Boolean(string='Email Verified', default=False, copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # ── Compute ─────────────────────────────────────────────────────

    @api.depends('template_id', 'billing_cycle', 'extra_user_packs')
    def _compute_totals(self):
        for s in self:
            if not s.template_id:
                s.total_users = s.total_amount = 0
                continue
            s.total_users = s.template_id.max_users + (s.extra_user_packs * 5)
            if s.billing_cycle == 'monthly':
                base = s.template_id.monthly_price
                extra = s.template_id.extra_users_price * s.extra_user_packs
            else:
                base = s.template_id.yearly_price
                extra = s.template_id.extra_users_price * s.extra_user_packs * 12
            s.total_amount = base + extra

    @api.depends('template_id', 'date_start')
    def _compute_trial_end(self):
        for s in self:
            if s.template_id and s.date_start:
                s.trial_end = s.date_start + timedelta(days=s.template_id.trial_days)
            else:
                s.trial_end = False

    def _compute_url(self):
        domain = 'msolutions-eg.com'
        for s in self:
            if s.subdomain:
                s.url = f'https://{s.subdomain}.{domain}'
            else:
                s.url = False

    def _compute_invoice_count(self):
        for s in self:
            paid = s.invoice_ids.filtered(lambda i: i.state == 'paid')
            s.invoice_count = len(s.invoice_ids)
            s.total_paid = sum(paid.mapped('amount'))

    # ── Sequence ────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ms.subscription') or 'New'
        return super().create(vals_list)

    # ── Actions ─────────────────────────────────────────────────────

    def action_start_trial(self):
        for s in self:
            s.state = 'trial'
            s.date_start = date.today()
            s.message_post(body=_('Free trial started. Ends: %s') % s.trial_end)
            s._notify_admin()

    def action_provision_and_notify(self):
        """Called async after signup - provisions DB then sends welcome email."""
        for s in self:
            try:
                s._provision_database()
                s._send_mail('ms_saas_manager.email_template_welcome')
                s.message_post(body=_('Database provisioned. Welcome email sent.'))
            except Exception as e:
                _logger.error('Provision failed for %s: %s', s.name, e)
                s.message_post(body=_('Provisioning error: %s') % e)

    def action_activate(self):
        for s in self:
            s.state = 'active'
            s._set_next_invoice_date()
            s.message_post(body=_('Subscription activated.'))

    def action_cancel(self):
        for s in self:
            s.state = 'cancelled'
            s.date_end = date.today()
            s._send_mail('ms_saas_manager.email_template_cancelled')
            s.message_post(body=_('Subscription cancelled.'))

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_reactivate(self):
        for s in self:
            s.state = 'active'
            s._set_next_invoice_date()

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'ms.invoice',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
        }

    def action_open_database(self):
        """Owner clicks → opens customer Odoo as admin (auto-login)."""
        self.ensure_one()
        if not self.db_id:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'No Database', 'message': 'Database not provisioned yet.',
                               'type': 'warning'}}
        return self.db_id.action_open_as_admin()

    def action_change_plan(self):
        return {
            'name': _('Change Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'ms.change.plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id,
                        'default_current_template_id': self.template_id.id},
        }

    def action_create_invoice(self):
        self.ensure_one()
        inv = self.env['ms.invoice'].create({
            'subscription_id': self.id,
            'partner_id': self.partner_id.id,
            'template_id': self.template_id.id,
            'billing_cycle': self.billing_cycle,
            'amount': self.total_amount,
            'due_date': date.today() + timedelta(days=7),
        })
        self._set_next_invoice_date()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ms.invoice',
            'res_id': inv.id,
            'view_mode': 'form',
        }

    # ── DB Provisioning ─────────────────────────────────────────────

    def _provision_database(self):
        """Create a new Odoo database for this customer."""
        self.ensure_one()
        if self.db_id:
            return  # already provisioned

        # Use subdomain from signup form, or auto-generate
        subdomain = self.subdomain
        if not subdomain:
            base = self.company_name or self.partner_id.name or 'client'
            subdomain = re.sub(r'[^a-z0-9]', '', base.lower())[:20] or 'client'
            self.subdomain = subdomain

        db_name = 'ms_' + re.sub(r'[^a-z0-9]', '_', subdomain.lower())

        wizard = self.env['ms.provision.wizard'].create({
            'subscription_id': self.id,
            'template_id': self.template_id.id,
            'db_name': db_name,
            'subdomain': subdomain,
            'admin_email': self.email or f'admin@{subdomain}.msolutions-eg.com',
        })
        wizard.action_provision()

    # ── Invoice scheduling ──────────────────────────────────────────

    def _set_next_invoice_date(self):
        today = date.today()
        if self.billing_cycle == 'monthly':
            self.date_next_invoice = today + relativedelta(months=1)
        else:
            self.date_next_invoice = today + relativedelta(years=1)

    # ── Cron jobs ───────────────────────────────────────────────────

    @api.model
    def _cron_check_trials(self):
        today = date.today()

        # ── 3-day reminder ──
        reminder_subs = self.search([
            ('state', '=', 'trial'),
            ('trial_end', '=', today + timedelta(days=3)),
        ])
        for s in reminder_subs:
            s._send_mail('ms_saas_manager.email_template_trial_ending')
            s.message_post(body=_('Trial ending reminder sent (3 days left).'))

        # ── Trial expired → generate invoice + suspend DB ──
        expired_subs = self.search([
            ('state', '=', 'trial'),
            ('trial_end', '<=', today),
        ])
        for s in expired_subs:
            s.state = 'expired'
            s.date_end = today

            # Auto-generate invoice
            try:
                inv = self.env['ms.invoice'].create({
                    'subscription_id': s.id,
                    'partner_id': s.partner_id.id,
                    'template_id': s.template_id.id,
                    'billing_cycle': s.billing_cycle,
                    'amount': s.total_amount,
                    'due_date': today + timedelta(days=7),
                })
                inv.action_send()
                s.message_post(body=_(
                    'Trial expired. Invoice %s auto-generated and sent.'
                ) % inv.name)
            except Exception as e:
                _logger.error('Invoice creation failed for %s: %s', s.name, e)
                s.message_post(body=_('Trial expired. Invoice creation failed: %s') % e)

            # Suspend the database
            if s.db_id and s.db_id.state == 'ready':
                s.db_id.action_suspend()
                s.message_post(body=_('Database suspended — awaiting payment.'))

            # Send trial ended email
            s._send_mail('ms_saas_manager.email_template_trial_ended')

    @api.model
    def _cron_auto_renew(self):
        today = date.today()
        for s in self.search([('state', '=', 'active'),
                               ('date_next_invoice', '<=', today)]):
            s.action_create_invoice()

    @api.model
    def _cron_cleanup_expired(self):
        """Delete databases 30 days after expiry with no payment."""
        today = date.today()
        cutoff = today - timedelta(days=30)
        expired_subs = self.search([
            ('state', '=', 'expired'),
            ('date_end', '<=', cutoff),
        ])
        for s in expired_subs:
            if s.db_id and s.db_id.state in ('suspended', 'error'):
                db_name = s.db_name
                try:
                    s.db_id.action_delete_database()
                    s.state = 'cancelled'
                    s.message_post(body=_(
                        'Database %s deleted after 30 days without payment.'
                    ) % db_name)
                except Exception as e:
                    _logger.error('DB cleanup failed for %s: %s', s.name, e)

    # ── Mail helpers ────────────────────────────────────────────────

    def _send_mail(self, xml_id):
        tmpl = self.env.ref(xml_id, raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)

    def _notify_admin(self):
        tmpl = self.env.ref('ms_saas_manager.email_template_admin_signup',
                            raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)
