# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MsCopyModulesWizard(models.TransientModel):
    _name = 'ms.copy.modules.wizard'
    _description = 'Copy Modules From Another Plan'

    target_template_id = fields.Many2one('ms.plan.template', string='To Plan', required=True, readonly=True)
    source_template_id = fields.Many2one('ms.plan.template', string='From Plan', required=True,
                                          domain="[('id', '!=', target_template_id)]")
    replace_existing = fields.Boolean(string='Replace existing modules', default=False,
                                       help='If checked, removes current modules before copying. '
                                            'If unchecked, only adds missing modules.')

    def action_copy(self):
        self.ensure_one()
        target = self.target_template_id
        source = self.source_template_id

        if not source.module_ids:
            raise UserError(_('Source plan "%s" has no modules.') % source.name)

        if self.replace_existing:
            # Delete non-required modules from target
            target.module_ids.filtered(lambda m: not m.is_required).unlink()

        existing_names = target.module_ids.mapped('name')
        copied = 0

        for mod in source.module_ids:
            if mod.name not in existing_names:
                self.env['ms.plan.template.module'].create({
                    'template_id': target.id,
                    'sequence': mod.sequence,
                    'module_id': mod.module_id.id if mod.module_id else False,
                    'name': mod.name,
                    'label': mod.label,
                    'description': mod.description,
                    'category': mod.category,
                    'is_required': mod.is_required,
                })
                copied += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Modules Copied'),
                'message': _('%d modules copied from "%s" to "%s".') % (copied, source.name, target.name),
                'type': 'success',
            },
        }
