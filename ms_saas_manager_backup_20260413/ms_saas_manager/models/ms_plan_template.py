# -*- coding: utf-8 -*-
import os
import zipfile
import shutil
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ADDONS_PATH = '/opt/odoo/custom_addons'


class MsPlanTemplateModule(models.Model):
    """One module line inside a plan template."""
    _name = 'ms.plan.template.module'
    _description = 'Plan Template Module Line'
    _order = 'sequence'

    template_id = fields.Many2one('ms.plan.template', ondelete='cascade')
    sequence    = fields.Integer(default=10)

    # Link to ir.module.module for auto-detection
    module_id   = fields.Many2one('ir.module.module', string='Module',
                                   help='Select from available modules on this server')
    name        = fields.Char(string='Technical Name', required=True,
                              help='Odoo module technical name, e.g. account, hr')
    label       = fields.Char(string='Display Name', required=True,
                              help='Human-readable name shown in backend')
    description = fields.Char(string='Description')
    category    = fields.Selection([
        ('standard', 'Odoo Standard'),
        ('custom',   'Custom Module'),
        ('hr',       'HR Module'),
        ('account',  'Accounting Module'),
        ('website',  'Website Module'),
    ], string='Category', default='standard')
    is_required = fields.Boolean(string='Required', default=True,
                                 help='Always installed; cannot be removed by user')
    module_state = fields.Selection(related='module_id.state', string='Install Status',
                                     readonly=True)

    @api.onchange('module_id')
    def _onchange_module_id(self):
        """Auto-fill name, label, description from ir.module.module."""
        if self.module_id:
            self.name = self.module_id.name
            # shortdesc is JSON in Odoo 18, get English value
            shortdesc = self.module_id.shortdesc or self.module_id.name
            self.label = shortdesc
            self.description = self.module_id.summary or ''
            # Auto-detect category
            cat_name = (self.module_id.category_id.name or '').lower()
            if 'account' in cat_name or 'invoic' in cat_name:
                self.category = 'account'
            elif 'human' in cat_name or 'hr' in cat_name or 'employee' in cat_name:
                self.category = 'hr'
            elif 'website' in cat_name:
                self.category = 'website'
            else:
                self.category = 'standard'

    def unlink(self):
        """Prevent deleting required modules."""
        for rec in self:
            if rec.is_required:
                raise UserError(_(
                    'Cannot delete required module "%s". '
                    'Uncheck "Required" first if you want to remove it.'
                ) % rec.label)
        return super().unlink()


class MsPlanTemplate(models.Model):
    _name = 'ms.plan.template'
    _description = 'SaaS Plan Template'
    _order = 'sequence'

    name         = fields.Char(string='Plan Name', required=True)
    name_ar      = fields.Char(string='Plan Name (Arabic)')
    code         = fields.Char(string='Code', required=True,
                               help='Unique code: basic / pro / advanced / executive')
    sequence     = fields.Integer(default=10)
    active       = fields.Boolean(default=True)
    color        = fields.Integer(string='Color', default=0)
    description  = fields.Text(string='Short Description')
    badge        = fields.Char(string='Badge', help='e.g. Most Popular')
    is_featured  = fields.Boolean(string='Featured / Highlighted')

    # ── Pricing ─────────────────────────────────────────────────────
    monthly_price      = fields.Float(string='Monthly Price (EGP)', required=True)
    yearly_price       = fields.Float(string='Yearly Price (EGP)',  required=True)
    extra_users_price  = fields.Float(string='Extra 5 Users / Month (EGP)', default=999.0)
    yearly_saving_pct  = fields.Float(string='Yearly Saving %',
                                       compute='_compute_saving', store=True)

    # ── Limits ──────────────────────────────────────────────────────
    max_users    = fields.Integer(string='Included Users', default=5)
    trial_days   = fields.Integer(string='Free Trial Days', default=7)

    # ── Modules ─────────────────────────────────────────────────────
    module_ids   = fields.One2many('ms.plan.template.module', 'template_id',
                                    string='Modules to Install')
    module_count = fields.Integer(compute='_compute_module_count', string='Modules')

    # ── Features list (for website display) ─────────────────────────
    features     = fields.Text(string='Features (one per line)',
                               help='Displayed as bullet points on pricing page')

    # ── Upload Module ───────────────────────────────────────────────
    upload_module_file = fields.Binary(string='Upload Module (.zip)', attachment=False)
    upload_module_name = fields.Char(string='Module Filename')

    # ── Stats ───────────────────────────────────────────────────────
    subscription_count = fields.Integer(compute='_compute_stats', string='Active Subscriptions')
    revenue_month      = fields.Float(compute='_compute_stats',   string='Monthly Revenue (EGP)')
    currency_id        = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # ── Compute ─────────────────────────────────────────────────────

    @api.depends('monthly_price', 'yearly_price')
    def _compute_saving(self):
        for t in self:
            if t.monthly_price:
                annual = t.monthly_price * 12
                t.yearly_saving_pct = round(
                    ((annual - t.yearly_price) / annual) * 100, 1)
            else:
                t.yearly_saving_pct = 0.0

    def _compute_module_count(self):
        for t in self:
            t.module_count = len(t.module_ids)

    def _compute_stats(self):
        for t in self:
            subs = self.env['ms.subscription'].search([
                ('template_id', '=', t.id),
                ('state', 'in', ('trial', 'active')),
            ])
            t.subscription_count = len(subs)
            active = subs.filtered(lambda s: s.state == 'active')
            monthly = sum(
                s.template_id.monthly_price if s.billing_cycle == 'monthly'
                else s.template_id.yearly_price / 12
                for s in active
            )
            t.revenue_month = round(monthly, 2)

    # ── Helpers ─────────────────────────────────────────────────────

    def get_features_list(self):
        self.ensure_one()
        if not self.features:
            return []
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def get_module_names(self):
        self.ensure_one()
        return self.module_ids.mapped('name')

    def get_yearly_saving_amount(self):
        self.ensure_one()
        return round((self.monthly_price * 12) - self.yearly_price, 0)

    def action_view_subscriptions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} — Subscriptions',
            'res_model': 'ms.subscription',
            'view_mode': 'list,form',
            'domain': [('template_id', '=', self.id)],
        }

    # ── Copy Modules From Another Plan ──────────────────────────────

    def action_copy_modules_from(self):
        """Open wizard to copy modules from another plan."""
        self.ensure_one()
        return {
            'name': _('Copy Modules From'),
            'type': 'ir.actions.act_window',
            'res_model': 'ms.copy.modules.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_target_template_id': self.id,
            },
        }

    # ── Upload Custom Module ────────────────────────────────────────

    def action_upload_module(self):
        """Extract uploaded zip to custom addons directory."""
        self.ensure_one()
        if not self.upload_module_file:
            raise UserError(_('Please select a .zip file to upload.'))

        import base64
        import tempfile

        filename = self.upload_module_name or 'module.zip'
        if not filename.endswith('.zip'):
            raise UserError(_('Only .zip files are allowed.'))

        # Save to temp file
        zip_data = base64.b64decode(self.upload_module_file)
        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        with open(tmp_path, 'wb') as f:
            f.write(zip_data)

        # Extract to addons path
        try:
            with zipfile.ZipFile(tmp_path, 'r') as zf:
                # Get the top-level folder name (module name)
                top_dirs = set()
                for name in zf.namelist():
                    parts = name.split('/')
                    if parts[0]:
                        top_dirs.add(parts[0])

                if len(top_dirs) != 1:
                    raise UserError(_(
                        'The zip file should contain exactly one module folder. '
                        'Found: %s') % ', '.join(top_dirs))

                module_name = top_dirs.pop()
                target_path = os.path.join(ADDONS_PATH, module_name)

                # Remove existing if present
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)

                zf.extractall(ADDONS_PATH)
                _logger.info('Module %s extracted to %s', module_name, target_path)

            # Clear the upload field
            self.write({
                'upload_module_file': False,
                'upload_module_name': False,
            })

            # Add to module list if not already there
            existing = self.module_ids.filtered(lambda m: m.name == module_name)
            if not existing:
                self.env['ms.plan.template.module'].create({
                    'template_id': self.id,
                    'name': module_name,
                    'label': module_name.replace('_', ' ').title(),
                    'category': 'custom',
                    'is_required': False,
                })

            # Schedule Odoo restart in background (3 sec delay)
            import subprocess as _sp
            _sp.Popen(
                'sleep 3 && systemctl restart odoo',
                shell=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Module Uploaded'),
                    'message': _(
                        'Module "%s" uploaded successfully. '
                        'Odoo is restarting now — page will reload in a few seconds.'
                    ) % module_name,
                    'type': 'success',
                    'sticky': True,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                },
            }
        except zipfile.BadZipFile:
            raise UserError(_('Invalid zip file.'))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
