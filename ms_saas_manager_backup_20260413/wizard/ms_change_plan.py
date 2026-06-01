# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MsChangePlan(models.TransientModel):
    _name = 'ms.change.plan'
    _description = 'Change Subscription Plan'

    subscription_id      = fields.Many2one('ms.subscription', required=True)
    current_template_id  = fields.Many2one('ms.plan.template', string='Current Plan', readonly=True)
    new_template_id      = fields.Many2one('ms.plan.template', string='New Plan', required=True)
    new_billing_cycle    = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly',  'Yearly'),
    ], string='Billing Cycle', required=True, default='monthly')
    install_new_modules  = fields.Boolean(
        string='Install new plan modules on customer DB',
        default=True,
    )
    notes = fields.Text(string='Reason / Notes')

    def action_confirm_change(self):
        self.ensure_one()
        sub = self.subscription_id
        old_plan = sub.template_id.name
        new_plan = self.new_template_id.name

        sub.write({
            'template_id':   self.new_template_id.id,
            'billing_cycle': self.new_billing_cycle,
        })

        if self.install_new_modules and sub.db_id and sub.db_name:
            # Install additional modules on existing DB
            new_modules = self.new_template_id.get_module_names()
            if new_modules:
                import subprocess
                modules_str = ','.join(new_modules)
                cmd = (
                    f'sudo -u odoo /opt/odoo/venv/bin/python3 '
                    f'/opt/odoo/server/odoo-bin '
                    f'-c /etc/odoo/odoo.conf '
                    f'-d {sub.db_name} '
                    f'--init={modules_str} '
                    f'--without-demo=all '
                    f'--stop-after-init --no-http'
                )
                subprocess.Popen(cmd, shell=True)

        sub.message_post(
            body=_(
                'Plan changed from <b>%s</b> → <b>%s</b> (%s).<br/>%s'
            ) % (old_plan, new_plan, self.new_billing_cycle,
                 self.notes or '')
        )

        return {'type': 'ir.actions.act_window_close'}
