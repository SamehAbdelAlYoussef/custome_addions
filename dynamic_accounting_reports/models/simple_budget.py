from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SimpleBudget(models.Model):
    _name = 'simple.budget'
    _description = 'Simple Budget'
    _order = 'date_from desc, name'

    name = fields.Char(string='Budget Name', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company, required=True)
    line_ids = fields.One2many('simple.budget.line', 'budget_id', string='Budget Lines')
    total_planned = fields.Float(string='Total Planned', compute='_compute_totals', store=True)
    total_actual = fields.Float(string='Total Actual', compute='_compute_totals', store=False)
    notes = fields.Text(string='Notes')

    @api.depends('line_ids.planned_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_planned = sum(rec.line_ids.mapped('planned_amount'))
            rec.total_actual = sum(rec.line_ids.mapped('actual_amount'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_('Start Date must be before End Date.'))

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class SimpleBudgetLine(models.Model):
    _name = 'simple.budget.line'
    _description = 'Simple Budget Line'
    _order = 'analytic_account_id'

    budget_id = fields.Many2one('simple.budget', string='Budget',
                                 required=True, ondelete='cascade')
    analytic_account_id = fields.Many2one('account.analytic.account',
                                           string='Analytic Account', required=True)
    analytic_plan_id = fields.Many2one(related='analytic_account_id.plan_id',
                                       string='Analytic Plan', store=True, readonly=True)
    planned_amount = fields.Float(string='Planned Amount', required=True)
    actual_amount = fields.Float(string='Actual Amount', compute='_compute_actual', store=False)
    variance = fields.Float(string='Variance', compute='_compute_actual', store=False)
    variance_pct = fields.Float(string='Variance %', compute='_compute_actual', store=False)
    date_from = fields.Date(related='budget_id.date_from', store=True, readonly=True)
    date_to = fields.Date(related='budget_id.date_to', store=True, readonly=True)
    company_id = fields.Many2one(related='budget_id.company_id', store=True, readonly=True)

    @api.depends('planned_amount', 'analytic_account_id', 'budget_id.date_from', 'budget_id.date_to', 'budget_id.state')
    def _compute_actual(self):
        for line in self:
            actual = 0.0
            if line.analytic_account_id and line.date_from and line.date_to:
                acc_id_str = str(line.analytic_account_id.id)
                domain = [
                    ('parent_state', '=', 'posted'),
                    ('analytic_distribution', '!=', False),
                    ('date', '>=', line.date_from),
                    ('date', '<=', line.date_to),
                    ('company_id', '=', line.company_id.id or self.env.company.id),
                ]
                move_lines = self.env['account.move.line'].sudo().search(domain)
                for ml in move_lines:
                    dist = ml.analytic_distribution or {}
                    if acc_id_str in dist:
                        pct = dist[acc_id_str]
                        actual += (ml.debit - ml.credit) * pct / 100.0
            line.actual_amount = actual
            line.variance = line.planned_amount - actual
            line.variance_pct = (line.variance / line.planned_amount * 100) if line.planned_amount else 0.0
