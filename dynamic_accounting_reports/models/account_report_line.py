from odoo import models, fields, api, _
from odoo.tools import float_is_zero


class AccountReportLine(models.Model):
    _name = 'dynamic.account.report.line'
    _description = 'Dynamic Account Report Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('dynamic.account.report', string='Report', required=True, ondelete='cascade')
    name = fields.Char(string='Label', required=True, translate=True)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('dynamic.account.report.line', string='Parent Line', ondelete='cascade')
    children_ids = fields.One2many('dynamic.account.report.line', 'parent_id', string='Child Lines')
    level = fields.Integer(default=2)

    # What this line computes
    line_type = fields.Selection([
        ('account_type', 'Account Type Sum'),
        ('account_codes', 'Account Code Range'),
        ('formula', 'Formula (sum of other lines)'),
        ('title', 'Title / Section Header'),
        ('total', 'Total Line'),
    ], string='Line Type', default='account_type', required=True)

    # For account_type
    account_type_ids = fields.Char(
        string='Account Types',
        help='Comma-separated account types, e.g.: asset_current,asset_cash'
    )

    # For account_codes
    code_from = fields.Char(string='Code From')
    code_to = fields.Char(string='Code To')

    # For formula
    formula = fields.Char(
        string='Formula',
        help='Reference other lines by code, e.g.: line_1 + line_2 - line_3'
    )
    code = fields.Char(string='Line Code', help='Unique code for formula references')

    # Display options
    sign = fields.Selection([
        ('+', 'Positive'),
        ('-', 'Negative / Reverse Sign'),
    ], default='+')
    hide_if_zero = fields.Boolean(default=False)
    is_bold = fields.Boolean(default=False)

    # Domain filters
    domain_filter = fields.Char(
        string='Additional Domain',
        help='Python domain expression to add as filter, e.g. [(\'partner_id.is_company\', \'=\', True)]'
    )

    def _compute_line_values(self, options, date_from, date_to, comparison_periods):
        """Compute the values for this report line."""
        self.ensure_one()
        report = self.report_id

        if self.line_type == 'title':
            return report._format_title_line(
                f'line_{self.id}', self.name, level=self.level
            )

        values = []

        if self.line_type == 'account_type':
            values = self._compute_account_type_values(report, options, date_from, date_to, comparison_periods)
        elif self.line_type == 'account_codes':
            values = self._compute_account_code_values(report, options, date_from, date_to, comparison_periods)
        elif self.line_type == 'formula':
            values = self._compute_formula_values(options, date_from, date_to, comparison_periods)
        elif self.line_type == 'total':
            # Sum all child lines
            values = self._compute_children_total(options, date_from, date_to, comparison_periods)

        # Apply sign
        if self.sign == '-':
            values = [-v for v in values]

        # Hide if zero
        if self.hide_if_zero and all(float_is_zero(v, precision_digits=2) for v in values):
            return None

        if self.line_type == 'total':
            return report._format_total_line(
                f'line_{self.id}', self.name, values, level=self.level
            )

        return report._format_detail_line(
            f'line_{self.id}', self.name, values, level=self.level,
            parent_id=f'line_{self.parent_id.id}' if self.parent_id else None
        )

    def _compute_account_type_values(self, report, options, date_from, date_to, comparison_periods):
        """Compute values from account types."""
        if not self.account_type_ids:
            return [0.0] * (1 + len(comparison_periods))

        account_types = [t.strip() for t in self.account_type_ids.split(',')]

        # Main period
        if report.use_date_to_only:
            domain = report._build_domain(options, date_to=date_to)
        else:
            domain = report._build_domain(options, date_from, date_to)

        if self.domain_filter:
            try:
                extra_domain = eval(self.domain_filter)
                domain += extra_domain
            except Exception:
                pass

        values = [report._sum_account_types(domain, account_types)]

        # Comparison periods
        for period in comparison_periods:
            if report.use_date_to_only:
                comp_domain = report._build_domain(options, date_to=period['date_to'])
            else:
                comp_domain = report._build_domain(options, period['date_from'], period['date_to'])
            if self.domain_filter:
                try:
                    comp_domain += eval(self.domain_filter)
                except Exception:
                    pass
            values.append(report._sum_account_types(comp_domain, account_types))

        return values

    def _compute_account_code_values(self, report, options, date_from, date_to, comparison_periods):
        """Compute values from account code ranges."""
        if report.use_date_to_only:
            domain = report._build_domain(options, date_to=date_to)
        else:
            domain = report._build_domain(options, date_from, date_to)

        if self.code_from:
            domain.append(('account_id.code', '>=', self.code_from))
        if self.code_to:
            domain.append(('account_id.code', '<=', self.code_to))

        results = self.env['account.move.line'].read_group(domain, ['balance'], [])
        values = [results[0]['balance'] if results else 0.0]

        for period in comparison_periods:
            if report.use_date_to_only:
                comp_domain = report._build_domain(options, date_to=period['date_to'])
            else:
                comp_domain = report._build_domain(options, period['date_from'], period['date_to'])
            if self.code_from:
                comp_domain.append(('account_id.code', '>=', self.code_from))
            if self.code_to:
                comp_domain.append(('account_id.code', '<=', self.code_to))
            comp_results = self.env['account.move.line'].read_group(comp_domain, ['balance'], [])
            values.append(comp_results[0]['balance'] if comp_results else 0.0)

        return values

    def _compute_formula_values(self, options, date_from, date_to, comparison_periods):
        """Compute values using formula referencing other lines."""
        if not self.formula:
            return [0.0] * (1 + len(comparison_periods))

        # Build context from sibling lines
        sibling_lines = self.report_id.line_ids.filtered(lambda l: l.code and l.id != self.id)
        line_values = {}
        for sibling in sibling_lines:
            vals = sibling._compute_line_values(options, date_from, date_to, comparison_periods)
            if vals and 'columns' in vals:
                line_values[sibling.code] = [
                    col.get('no_format', 0.0) for col in vals['columns']
                ]
            else:
                line_values[sibling.code] = [0.0] * (1 + len(comparison_periods))

        num_periods = 1 + len(comparison_periods)
        result = []
        for i in range(num_periods):
            # Build eval context for this period
            eval_ctx = {}
            for code, vals in line_values.items():
                eval_ctx[code] = vals[i] if i < len(vals) else 0.0
            try:
                result.append(float(eval(self.formula, {"__builtins__": {}}, eval_ctx)))
            except Exception:
                result.append(0.0)

        return result

    def _compute_children_total(self, options, date_from, date_to, comparison_periods):
        """Sum all children lines."""
        num_periods = 1 + len(comparison_periods)
        totals = [0.0] * num_periods

        for child in self.children_ids.sorted(key=lambda l: l.sequence):
            vals = child._compute_line_values(options, date_from, date_to, comparison_periods)
            if vals and 'columns' in vals:
                for i, col in enumerate(vals['columns']):
                    if i < num_periods:
                        totals[i] += col.get('no_format', 0.0)

        return totals

