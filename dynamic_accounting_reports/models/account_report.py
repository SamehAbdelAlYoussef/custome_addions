import json
import io
import logging
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.tools import float_is_zero, format_date
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.warning('xlsxwriter not installed. Excel export will not work.')
    xlsxwriter = None


class AccountReport(models.Model):
    _name = 'dynamic.account.report'
    _description = 'Dynamic Accounting Report'
    _order = 'sequence, id'

    name = fields.Char(string='Report Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    report_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('profit_loss', 'Profit & Loss'),
        ('trial_balance', 'Trial Balance'),
        ('general_ledger', 'General Ledger'),
        ('aged_receivable', 'Aged Receivable'),
        ('aged_payable', 'Aged Payable'),
        ('partner_ledger', 'Partner Ledger'),
        ('cash_flow', 'Cash Flow Statement'),
        ('custom', 'Custom Report'),
        ('tax_report', 'Tax Report'),
        ('analytic_account', 'Analytic Account Report'),
        ('analytic_plan', 'Analytic Plan Report'),
        ('petty_cash', 'Petty Cash Report'),
        ('bank_book', 'Bank Book'),
        ('day_book', 'Day Book'),
        ('budget_vs_actual', 'Budget vs Actual'),
    ], string='Report Type', required=True, default='custom')
    line_ids = fields.One2many('dynamic.account.report.line', 'report_id', string='Report Lines')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Filter configuration
    filter_date_range = fields.Boolean(default=True)
    filter_comparison = fields.Boolean(default=True)
    filter_journals = fields.Boolean(default=False)
    filter_accounts = fields.Boolean(default=False)
    filter_partners = fields.Boolean(default=False)
    filter_analytic = fields.Boolean(default=False)
    filter_unfold_all = fields.Boolean(default=False)
    filter_hierarchy = fields.Boolean(default=False)
    filter_multi_company = fields.Boolean(default=False)
    filter_account_type = fields.Boolean(default=False, help='Show Account Type filter (Receivable/Payable)')

    # Date defaults
    date_range = fields.Selection([
        ('this_month', 'This Month'),
        ('this_quarter', 'This Quarter'),
        ('this_year', 'This Financial Year'),
        ('last_month', 'Last Month'),
        ('last_quarter', 'Last Quarter'),
        ('last_year', 'Last Financial Year'),
        ('custom', 'Custom'),
    ], default='this_year')

    # For balance sheet type reports
    use_date_to_only = fields.Boolean(
        default=False,
        help='If True, report uses single date (As of) instead of date range'
    )

    def action_open_report(self):
        """Open the dynamic report view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'dynamic_account_report',
            'name': self.name,
            'params': {
                'report_id': self.id,
            },
            'context': dict(self.env.context, report_id=self.id),
        }

    # ========================================================================
    # DATE HELPERS
    # ========================================================================

    def _get_dates(self, options):
        """Get date_from and date_to from options."""
        if options.get('date_from') and options.get('date_to'):
            return fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])
        return self._get_default_dates(options.get('date_range', self.date_range))

    def _get_default_dates(self, date_range=None):
        """Get default dates based on the date range selection."""
        today = fields.Date.context_today(self)
        company = self.env.company
        fiscal_year_last_month = company.fiscalyear_last_month or 12
        fiscal_year_last_day = company.fiscalyear_last_day or 31

        if date_range == 'this_month':
            date_from = today.replace(day=1)
            date_to = (date_from + relativedelta(months=1)) - timedelta(days=1)
        elif date_range == 'this_quarter':
            quarter = (today.month - 1) // 3
            date_from = today.replace(month=quarter * 3 + 1, day=1)
            date_to = (date_from + relativedelta(months=3)) - timedelta(days=1)
        elif date_range == 'last_month':
            date_from = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            date_to = today.replace(day=1) - timedelta(days=1)
        elif date_range == 'last_quarter':
            quarter = (today.month - 1) // 3
            date_to = today.replace(month=quarter * 3 + 1, day=1) - timedelta(days=1)
            date_from = (date_to.replace(day=1) - relativedelta(months=2))
        elif date_range == 'last_year':
            fy_date_to = today.replace(month=int(fiscal_year_last_month), day=int(fiscal_year_last_day))
            if fy_date_to >= today:
                fy_date_to = fy_date_to - relativedelta(years=1)
            date_to = fy_date_to - relativedelta(years=1)
            date_from = date_to - relativedelta(years=1) + timedelta(days=1)
        else:  # this_year (default)
            fy_date_to = today.replace(month=int(fiscal_year_last_month), day=int(fiscal_year_last_day))
            if fy_date_to < today:
                fy_date_to = fy_date_to + relativedelta(years=1)
            date_to = fy_date_to
            date_from = fy_date_to - relativedelta(years=1) + timedelta(days=1)

        return date_from, date_to

    def _get_comparison_dates(self, options, date_from, date_to):
        """Get comparison period dates."""
        comparison = options.get('comparison', {})
        if not comparison.get('enabled'):
            return []

        periods = []
        comp_type = comparison.get('type', 'previous_period')
        number = comparison.get('number', 1)

        for i in range(1, number + 1):
            if comp_type == 'previous_period':
                delta = relativedelta(months=i * self._get_period_months(date_from, date_to))
                periods.append({
                    'date_from': date_from - delta,
                    'date_to': date_to - delta,
                    'string': self._get_period_string(date_from - delta, date_to - delta),
                })
            elif comp_type == 'previous_year':
                delta = relativedelta(years=i)
                periods.append({
                    'date_from': date_from - delta,
                    'date_to': date_to - delta,
                    'string': self._get_period_string(date_from - delta, date_to - delta),
                })
            elif comp_type == 'custom' and comparison.get('date_from') and comparison.get('date_to'):
                periods.append({
                    'date_from': fields.Date.from_string(comparison['date_from']),
                    'date_to': fields.Date.from_string(comparison['date_to']),
                    'string': self._get_period_string(
                        fields.Date.from_string(comparison['date_from']),
                        fields.Date.from_string(comparison['date_to'])
                    ),
                })
        return periods

    def _get_period_months(self, date_from, date_to):
        """Calculate number of months in a period."""
        return (date_to.year - date_from.year) * 12 + date_to.month - date_from.month + 1

    def _get_period_string(self, date_from, date_to):
        """Get display string for a period."""
        return f"{format_date(self.env, date_from)} - {format_date(self.env, date_to)}"

    # ========================================================================
    # DOMAIN / FILTER BUILDING
    # ========================================================================

    def _build_domain(self, options, date_from=None, date_to=None):
        """Build the base domain for account.move.line queries."""
        domain = [('display_type', 'not in', ('line_section', 'line_note'))]

        company_ids = options.get('company_ids', [self.env.company.id])
        domain.append(('company_id', 'in', company_ids))

        # Posted entries only unless draft is explicitly requested
        if options.get('all_entries'):
            domain.append(('parent_state', '!=', 'cancel'))
        else:
            domain.append(('parent_state', '=', 'posted'))

        # Date filter
        if date_from and date_to:
            domain.append(('date', '>=', date_from))
            domain.append(('date', '<=', date_to))
        elif date_to:
            domain.append(('date', '<=', date_to))

        # Journal filter
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))

        # Account filter
        if options.get('account_ids'):
            domain.append(('account_id', 'in', options['account_ids']))

        # Partner filter
        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', options['partner_ids']))

        # Analytic filter
        if options.get('analytic_account_ids'):
            domain.append(('analytic_distribution', '!=', False))

        return domain

    # ========================================================================
    # MAIN REPORT DATA GETTERS
    # ========================================================================

    def get_report_data(self, options):
        """Main method to get report data for the frontend."""
        self.ensure_one()
        date_from, date_to = self._get_dates(options)

        # Build comparison periods
        comparison_periods = self._get_comparison_dates(options, date_from, date_to)

        # Get report lines based on report type
        handler = getattr(self, f'_get_{self.report_type}_lines', None)
        if handler:
            lines = handler(options, date_from, date_to, comparison_periods)
        else:
            lines = self._get_custom_report_lines(options, date_from, date_to, comparison_periods)

        # Build column headers — per report type
        col_handler = getattr(self, f'_get_{self.report_type}_columns', None)
        if col_handler:
            columns = col_handler(date_from, date_to, comparison_periods, options)
        else:
            columns = self._get_column_headers(date_from, date_to, comparison_periods, options)

        return {
            'report_name': self.name,
            'report_type': self.report_type,
            'lines': lines,
            'columns': columns,
            'date_from': str(date_from),
            'date_to': str(date_to),
            'comparison_periods': comparison_periods,
            'filters': self._get_filter_config(options),
            'company_name': self.env.company.name,
            'currency_id': self.env.company.currency_id.id,
            'currency_symbol': self.env.company.currency_id.symbol,
        }

    def _get_column_headers(self, date_from, date_to, comparison_periods, options):
        """Get column headers for the report."""
        if self.use_date_to_only:
            col_name = _('Balance')
        else:
            col_name = self._get_period_string(date_from, date_to)
        columns = [{
            'name': col_name,
            'class': 'number',
        }]
        for period in comparison_periods:
            columns.append({
                'name': period['string'],
                'class': 'number',
            })
        if comparison_periods and options.get('comparison', {}).get('show_percent'):
            columns.append({
                'name': '%',
                'class': 'number',
            })
        return columns

    def _get_filter_config(self, options):
        """Return filter configuration for the frontend."""
        return {
            'date_range': self.filter_date_range,
            'comparison': self.filter_comparison,
            'journals': self.filter_journals,
            'accounts': self.filter_accounts,
            'partners': self.filter_partners,
            'analytic': self.filter_analytic,
            'unfold_all': self.filter_unfold_all,
            'hierarchy': self.filter_hierarchy,
            'multi_company': self.filter_multi_company,
            'use_date_to_only': self.use_date_to_only,
            'account_type': self.filter_account_type,
        }

    # ========================================================================
    # BALANCE SHEET
    # ========================================================================

    def _get_balance_sheet_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Balance Sheet report lines matching Enterprise layout."""
        lines = []
        domain = self._build_domain(options, date_to=date_to)
        num_cols = 1 + len(comparison_periods)

        # =========================================================
        # ASSETS
        # =========================================================

        # -- Current Assets sub-section --
        current_asset_types = [
            ('asset_cash', _('Bank and Cash Accounts')),
            ('asset_receivable', _('Receivables')),
            ('asset_current', _('Current Assets')),
            ('asset_prepayments', _('Prepayments')),
        ]
        current_asset_total = [0.0] * num_cols
        current_asset_detail = []
        for acc_type, label in current_asset_types:
            vals = self._get_single_type_balance(domain, acc_type, options, date_to, comparison_periods)
            has_value = any(not float_is_zero(v, precision_digits=2) for v in vals)
            current_asset_detail.append(self._format_detail_line(
                f'bs_{acc_type}', label, vals, level=2, parent_id='current_assets',
                unfoldable_flag=has_value,
            ))
            for i in range(num_cols):
                current_asset_total[i] += vals[i]

        # -- Plus Fixed Assets --
        fixed_vals = self._get_single_type_balance(domain, 'asset_fixed', options, date_to, comparison_periods)

        # -- Plus Non-current Assets --
        noncurrent_vals = self._get_single_type_balance(domain, 'asset_non_current', options, date_to, comparison_periods)

        # -- Total Assets --
        total_assets = [
            current_asset_total[i] + fixed_vals[i] + noncurrent_vals[i]
            for i in range(num_cols)
        ]

        # ASSETS grey band
        lines.append(self._format_group_header('assets_header', _('ASSETS'), total_assets))

        # Current Assets section header (bold, with total)
        lines.append(self._format_section_header(
            'current_assets', _('Current Assets'), current_asset_total, level=1
        ))
        lines.extend(current_asset_detail)

        # Plus Fixed Assets
        lines.append(self._format_detail_line(
            'bs_asset_fixed', _('Plus Fixed Assets'), fixed_vals, level=1,
            unfoldable_flag=any(not float_is_zero(v, precision_digits=2) for v in fixed_vals),
        ))

        # Plus Non-current Assets
        lines.append(self._format_detail_line(
            'bs_asset_noncurrent', _('Plus Non-current Assets'), noncurrent_vals, level=1,
            unfoldable_flag=any(not float_is_zero(v, precision_digits=2) for v in noncurrent_vals),
        ))

        # Total Assets
        # (Total shown in ASSETS grey band above — no separate line needed, matching Enterprise)

        # =========================================================
        # LIABILITIES (show as positive — multiply by -1)
        # =========================================================

        # Grey band header
        current_liab_types = [
            ('liability_current', _('Current Liabilities')),
            ('liability_payable', _('Payables')),
            ('liability_credit_card', _('Credit Card')),
        ]
        current_liab_total = [0.0] * num_cols
        current_liab_detail = []
        for acc_type, label in current_liab_types:
            vals = self._get_single_type_balance(domain, acc_type, options, date_to, comparison_periods, sign=-1)
            has_value = any(not float_is_zero(v, precision_digits=2) for v in vals)
            current_liab_detail.append(self._format_detail_line(
                f'bs_{acc_type}', label, vals, level=2, parent_id='current_liabilities',
                unfoldable_flag=has_value,
            ))
            for i in range(num_cols):
                current_liab_total[i] += vals[i]

        # Non-current liabilities
        noncurrent_liab_vals = self._get_single_type_balance(
            domain, 'liability_non_current', options, date_to, comparison_periods, sign=-1
        )
        total_liabilities = [
            current_liab_total[i] + noncurrent_liab_vals[i]
            for i in range(num_cols)
        ]

        # LIABILITIES grey band
        lines.append(self._format_group_header('liabilities_header', _('LIABILITIES'), total_liabilities))

        # Current Liabilities section header
        lines.append(self._format_section_header(
            'current_liabilities', _('Current Liabilities'), current_liab_total, level=1
        ))
        lines.extend(current_liab_detail)

        # Plus Non-current Liabilities
        lines.append(self._format_detail_line(
            'bs_liab_noncurrent', _('Plus Non-current Liabilities'), noncurrent_liab_vals, level=1,
            unfoldable_flag=any(not float_is_zero(v, precision_digits=2) for v in noncurrent_liab_vals),
        ))

        # =========================================================
        # EQUITY (IAS 1 — show as positive — multiply by -1)
        # =========================================================

        # Get fiscal year start date
        company = self.env.company
        fy_last_month = int(company.fiscalyear_last_month or 12)
        fy_last_day = int(company.fiscalyear_last_day or 31)
        fy_date_to = date_to.replace(month=fy_last_month, day=fy_last_day)
        if fy_date_to < date_to:
            fy_start = fy_date_to + timedelta(days=1)
        else:
            fy_start = (fy_date_to - relativedelta(years=1)) + timedelta(days=1)

        AML = self.env['account.move.line']

        # --- Share Capital (accounts 301xxx) ---
        share_capital_vals = self._get_bs_account_balance(
            domain, ['301'], options, date_to, comparison_periods, sign=-1
        )

        # --- Statutory Reserve (accounts 302002) ---
        reserve_vals = self._get_bs_account_balance(
            domain, ['302002'], options, date_to, comparison_periods, sign=-1
        )

        # --- Retained Earnings (accounts 302001) ---
        retained_vals = self._get_bs_account_balance(
            domain, ['302001'], options, date_to, comparison_periods, sign=-1
        )

        # --- Previous Years Unallocated (equity_unaffected) ---
        eq_unaff_domain = self._build_domain(options, date_to=date_to)
        eq_unaff_domain += [('account_id.account_type', '=', 'equity_unaffected')]
        eq_unaff_results = AML.read_group(eq_unaff_domain, ['balance'], [])
        eq_unaff_balance = eq_unaff_results[0]['balance'] if eq_unaff_results and eq_unaff_results[0].get('balance') else 0.0
        prev_years_unalloc = [-eq_unaff_balance]

        # --- Current Year P&L ---
        income_types = ['income', 'income_other']
        expense_types = ['expense', 'expense_depreciation', 'expense_direct_cost']

        curr_domain = self._build_domain(options, fy_start, date_to)
        curr_year_income = self._sum_account_types(curr_domain, income_types)
        curr_year_expense = self._sum_account_types(curr_domain, expense_types)
        curr_year_pl = [-(curr_year_income + curr_year_expense)]

        # Comparison periods
        for period in comparison_periods:
            p_fy_date_to = period['date_to'].replace(month=fy_last_month, day=fy_last_day)
            if p_fy_date_to < period['date_to']:
                p_fy_start = p_fy_date_to + timedelta(days=1)
            else:
                p_fy_start = (p_fy_date_to - relativedelta(years=1)) + timedelta(days=1)

            c_domain = self._build_domain(options, p_fy_start, period['date_to'])
            c_inc = self._sum_account_types(c_domain, income_types)
            c_exp = self._sum_account_types(c_domain, expense_types)
            curr_year_pl.append(-(c_inc + c_exp))

            c_eq_unaff_domain = self._build_domain(options, date_to=period['date_to'])
            c_eq_unaff_domain += [('account_id.account_type', '=', 'equity_unaffected')]
            c_eq_unaff_r = AML.read_group(c_eq_unaff_domain, ['balance'], [])
            c_eq_unaff_bal = c_eq_unaff_r[0]['balance'] if c_eq_unaff_r and c_eq_unaff_r[0].get('balance') else 0.0
            prev_years_unalloc.append(-c_eq_unaff_bal)

        # Total Equity
        total_equity = [
            share_capital_vals[i] + reserve_vals[i] + retained_vals[i] +
            prev_years_unalloc[i] + curr_year_pl[i]
            for i in range(num_cols)
        ]

        # EQUITY grey band
        lines.append(self._format_group_header('equity_header', _('EQUITY / حقوق الملكية'), total_equity))

        # Share Capital
        has_sc = any(not float_is_zero(v, precision_digits=2) for v in share_capital_vals)
        lines.append(self._format_detail_line(
            'bs_share_capital', _('Share Capital / رأس المال'), share_capital_vals, level=1,
            unfoldable_flag=has_sc,
        ))

        # Statutory Reserve
        has_res = any(not float_is_zero(v, precision_digits=2) for v in reserve_vals)
        lines.append(self._format_detail_line(
            'bs_reserve', _('Statutory Reserve / احتياطي نظامي'), reserve_vals, level=1,
            unfoldable_flag=has_res,
        ))

        # Retained Earnings
        has_ret = any(not float_is_zero(v, precision_digits=2) for v in retained_vals)
        lines.append(self._format_detail_line(
            'bs_retained', _('Retained Earnings / أرباح مبقاة'), retained_vals, level=1,
            unfoldable_flag=has_ret,
        ))

        # Previous Years Unallocated Earnings
        has_prev = any(not float_is_zero(v, precision_digits=2) for v in prev_years_unalloc)
        lines.append(self._format_detail_line(
            'bs_prev_years_unalloc', _('Previous Years Unallocated / أرباح سنوات سابقة غير موزعة'),
            prev_years_unalloc, level=1,
            unfoldable_flag=has_prev,
        ))

        # Current Year Profit/Loss
        has_curr = any(not float_is_zero(v, precision_digits=2) for v in curr_year_pl)
        lines.append(self._format_detail_line(
            'bs_curr_year_pl', _('Current Year Profit (Loss) / ربح (خسارة) العام الحالي'),
            curr_year_pl, level=1,
            unfoldable_flag=has_curr,
        ))

        # =========================================================
        # LIABILITIES + EQUITY (grey band at bottom)
        # =========================================================
        total_le = [
            total_liabilities[i] + total_equity[i]
            for i in range(num_cols)
        ]
        lines.append(self._format_group_header(
            'total_liab_equity', _('LIABILITIES + EQUITY'), total_le
        ))

        return lines

    def _get_single_type_balance(self, domain, account_type, options, date_to, comparison_periods, sign=1):
        """Get balance for a single account type with comparison periods."""
        AML = self.env['account.move.line']
        type_domain = domain + [('account_id.account_type', '=', account_type)]
        results = AML.read_group(type_domain, ['balance'], [])
        balance = (results[0]['balance'] if results else 0.0) * sign
        values = [balance]

        for period in comparison_periods:
            comp_domain = self._build_domain(options, date_to=period['date_to'])
            comp_domain += [('account_id.account_type', '=', account_type)]
            comp_results = AML.read_group(comp_domain, ['balance'], [])
            comp_balance = (comp_results[0]['balance'] if comp_results else 0.0) * sign
            values.append(comp_balance)

        return values

    def _get_bs_account_balance(self, domain, account_code_prefixes, options, date_to, comparison_periods, sign=1):
        """Get balance for accounts matching code prefixes (e.g. ['301'] for share capital)."""
        AML = self.env['account.move.line']
        code_domain = ['|'] * (len(account_code_prefixes) - 1) if len(account_code_prefixes) > 1 else []
        for prefix in account_code_prefixes:
            code_domain.append(('account_id.code', '=like', prefix + '%'))

        type_domain = domain + code_domain
        results = AML.read_group(type_domain, ['balance'], [])
        balance = (results[0]['balance'] if results else 0.0) * sign
        values = [balance]

        for period in comparison_periods:
            comp_domain = self._build_domain(options, date_to=period['date_to'])
            comp_domain += code_domain
            comp_results = AML.read_group(comp_domain, ['balance'], [])
            comp_balance = (comp_results[0]['balance'] if comp_results else 0.0) * sign
            values.append(comp_balance)

        return values

    def _compute_unallocated_earnings(self, options, date_to, comparison_periods):
        """Compute P&L result (unallocated earnings) for balance sheet."""
        income_types = ['income', 'income_other']
        expense_types = ['expense', 'expense_depreciation', 'expense_direct_cost']

        # Current period
        domain = self._build_domain(options, date_to=date_to)
        income = self._sum_account_types(domain, income_types)
        expense = self._sum_account_types(domain, expense_types)
        values = [income - expense]

        # Comparison periods
        for period in comparison_periods:
            comp_domain = self._build_domain(options, date_to=period['date_to'])
            comp_income = self._sum_account_types(comp_domain, income_types)
            comp_expense = self._sum_account_types(comp_domain, expense_types)
            values.append(comp_income - comp_expense)

        return values

    # ========================================================================
    # PROFIT & LOSS
    # ========================================================================

    def _get_profit_loss_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Profit & Loss report lines — IFRS compliant."""
        lines = []
        domain = self._build_domain(options, date_from, date_to)
        num_cols = 1 + len(comparison_periods)

        # ─────────────────────────────────────────────────
        # Revenue (IFRS 15)
        # ─────────────────────────────────────────────────
        revenue_vals = self._get_pl_type_balance(
            domain, 'income', options, date_from, date_to, comparison_periods, sign=-1
        )
        has_revenue = any(not self._is_zero(v) for v in revenue_vals)
        lines.append(self._format_pl_line(
            'pl_revenue', 'Revenue / الإيرادات', revenue_vals, level=1,
            unfoldable=has_revenue,
        ))

        # Less Costs of Revenue (Cost of Sales)
        cogs_vals = self._get_pl_type_balance(
            domain, 'expense_direct_cost', options, date_from, date_to, comparison_periods, sign=1
        )
        has_cogs = any(not self._is_zero(v) for v in cogs_vals)
        lines.append(self._format_pl_line(
            'pl_cogs', 'Less Cost of Revenue / تكلفة الإيرادات', cogs_vals, level=1,
            unfoldable=has_cogs,
        ))

        # ── Gross Profit ──────────────────────────────────
        gross_profit = [revenue_vals[i] - cogs_vals[i] for i in range(num_cols)]
        lines.append(self._format_group_header('gross_profit', _('Gross Profit / مجمل الربح'), gross_profit))

        # Less Operating Expenses (exclude finance costs and zakat — shown separately below)
        opex_vals = self._get_pl_type_balance(
            domain, 'expense', options, date_from, date_to, comparison_periods, sign=1
        )
        deprec_vals = self._get_pl_type_balance(
            domain, 'expense_depreciation', options, date_from, date_to, comparison_periods, sign=1
        )

        # Finance costs and zakat are part of 'expense' type but shown separately
        finance_cost_vals = self._get_pl_account_balance(
            domain, ['400051', '400311'], options, date_from, date_to, comparison_periods, sign=1
        )
        zakat_vals = self._get_pl_account_balance(
            domain, ['400070', '400071', '400072'], options, date_from, date_to, comparison_periods, sign=1
        )

        # Net operating expenses = total expense - finance costs - zakat
        total_opex = [opex_vals[i] + deprec_vals[i] - finance_cost_vals[i] - zakat_vals[i] for i in range(num_cols)]
        has_opex = any(not self._is_zero(v) for v in total_opex)
        lines.append(self._format_pl_line(
            'pl_opex', 'Less Operating Expenses / المصروفات التشغيلية', total_opex, level=1,
            unfoldable=has_opex,
        ))

        # ── Operating Profit ────────────────────────────
        operating_income = [gross_profit[i] - total_opex[i] for i in range(num_cols)]
        lines.append(self._format_group_header('operating_income', _('Operating Profit / الربح التشغيلي'), operating_income))

        # Plus Other Income
        other_income_vals = self._get_pl_type_balance(
            domain, 'income_other', options, date_from, date_to, comparison_periods, sign=-1
        )
        has_other_income = any(not self._is_zero(v) for v in other_income_vals)
        lines.append(self._format_pl_line(
            'pl_other_income', 'Plus Other Income / إيرادات أخرى', other_income_vals, level=1,
            unfoldable=has_other_income,
        ))

        # Less Finance Costs (already computed above)
        has_finance = any(not self._is_zero(v) for v in finance_cost_vals)
        lines.append(self._format_pl_line(
            'pl_finance_cost', 'Less Finance Costs / تكاليف التمويل', finance_cost_vals, level=1,
            unfoldable=has_finance,
        ))

        # ── Profit Before Zakat ─────────────────────────
        profit_before_zakat = [
            operating_income[i] + other_income_vals[i] - finance_cost_vals[i]
            for i in range(num_cols)
        ]
        lines.append(self._format_group_header('profit_before_zakat', _('Profit Before Zakat / الربح قبل الزكاة'), profit_before_zakat))

        # Less Zakat & Tax Expense (accounts with code starting with 400070 or in zakat journal)
        zakat_vals = self._get_pl_account_balance(
            domain, ['400070', '400071', '400072'], options, date_from, date_to, comparison_periods, sign=1
        )
        has_zakat = any(not self._is_zero(v) for v in zakat_vals)
        lines.append(self._format_pl_line(
            'pl_zakat', 'Less Zakat & Tax / الزكاة والضريبة', zakat_vals, level=1,
            unfoldable=has_zakat,
        ))

        # ── Net Profit ────────────────────────────────────
        net_profit = [
            profit_before_zakat[i] - zakat_vals[i]
            for i in range(num_cols)
        ]
        lines.append(self._format_group_header('net_profit', _('Net Profit / صافي الربح'), net_profit))

        return lines

    def _get_pl_account_balance(self, domain, account_codes, options, date_from, date_to, comparison_periods, sign=1):
        """Get balance for specific account codes (for finance costs, zakat, etc.)."""
        AML = self.env['account.move.line']
        code_domain = ['|'] * (len(account_codes) - 1) if len(account_codes) > 1 else []
        for code in account_codes:
            code_domain.append(('account_id.code', '=like', code + '%'))

        type_domain = domain + code_domain
        results = AML.read_group(type_domain, ['balance'], [])
        balance = (results[0]['balance'] if results else 0.0) * sign
        values = [balance]

        for period in comparison_periods:
            comp_domain = self._build_domain(options, period['date_from'], period['date_to'])
            comp_domain += code_domain
            comp_results = AML.read_group(comp_domain, ['balance'], [])
            comp_balance = (comp_results[0]['balance'] if comp_results else 0.0) * sign
            values.append(comp_balance)

        return values

    def _format_pl_line(self, line_id, name, values, level=1, unfoldable=False):
        """Format a P&L detail line (non-grey-band)."""
        columns = []
        for v in values:
            columns.append({
                'name': self._format_value(v),
                'no_format': v,
                'class': 'number',
            })
        return {
            'id': line_id,
            'name': name,
            'level': level,
            'columns': columns,
            'unfoldable': unfoldable,
            'unfolded': False,
            'parent_id': None,
        }

    def _is_zero(self, value, precision=2):
        """Check if value is effectively zero."""
        from odoo.tools import float_is_zero
        return float_is_zero(value, precision_digits=precision)

    def _get_pl_type_balance(self, domain, account_type, options, date_from, date_to, comparison_periods, sign=1):
        """Get P&L balance for a single account type with comparison periods."""
        AML = self.env['account.move.line']
        type_domain = domain + [('account_id.account_type', '=', account_type)]
        results = AML.read_group(type_domain, ['balance'], [])
        balance = (results[0]['balance'] if results else 0.0) * sign
        values = [balance]

        for period in comparison_periods:
            comp_domain = self._build_domain(options, period['date_from'], period['date_to'])
            comp_domain += [('account_id.account_type', '=', account_type)]
            comp_results = AML.read_group(comp_domain, ['balance'], [])
            comp_balance = (comp_results[0]['balance'] if comp_results else 0.0) * sign
            values.append(comp_balance)

        return values

    # ========================================================================
    # TRIAL BALANCE
    # ========================================================================

    def _get_trial_balance_columns(self, date_from, date_to, comparison_periods, options):
        """Trial Balance has 6 columns: Initial Debit/Credit, Period Debit/Credit, End Debit/Credit."""
        return [
            {'name': _('Initial Balance Debit'), 'class': 'number'},
            {'name': _('Initial Balance Credit'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('End Balance Debit'), 'class': 'number'},
            {'name': _('End Balance Credit'), 'class': 'number'},
        ]

    def _get_trial_balance_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Trial Balance report lines."""
        lines = []
        domain = self._build_domain(options, date_from, date_to)

        # Get all accounts with moves in period
        AccountMoveLine = self.env['account.move.line']
        results = AccountMoveLine.read_group(
            domain,
            ['account_id', 'debit', 'credit', 'balance'],
            ['account_id'],
        )

        # Initial balances
        init_domain = self._build_domain(options, date_to=date_from - timedelta(days=1))
        init_results = AccountMoveLine.read_group(
            init_domain,
            ['account_id', 'debit', 'credit', 'balance'],
            ['account_id'],
        )
        init_balance_map = {}
        for r in init_results:
            if r['account_id']:
                init_balance_map[r['account_id'][0]] = r['balance']

        total_init_debit = 0.0
        total_init_credit = 0.0
        total_debit = 0.0
        total_credit = 0.0
        total_end_debit = 0.0
        total_end_credit = 0.0

        account_ids = set()
        balance_map = {}
        for r in results:
            if r['account_id']:
                acc_id = r['account_id'][0]
                account_ids.add(acc_id)
                balance_map[acc_id] = {
                    'debit': r['debit'],
                    'credit': r['credit'],
                    'balance': r['balance'],
                }

        for acc_id in init_balance_map:
            account_ids.add(acc_id)

        accounts = self.env['account.account'].browse(list(account_ids)).sorted(key=lambda a: getattr(a, 'code', '') or '')

        for account in accounts:
            init_bal = init_balance_map.get(account.id, 0.0)
            period_data = balance_map.get(account.id, {'debit': 0.0, 'credit': 0.0, 'balance': 0.0})

            init_debit = init_bal if init_bal > 0 else 0.0
            init_credit = -init_bal if init_bal < 0 else 0.0
            period_debit = period_data['debit']
            period_credit = period_data['credit']
            end_balance = init_bal + period_data['balance']
            end_debit = end_balance if end_balance > 0 else 0.0
            end_credit = -end_balance if end_balance < 0 else 0.0

            total_init_debit += init_debit
            total_init_credit += init_credit
            total_debit += period_debit
            total_credit += period_credit
            total_end_debit += end_debit
            total_end_credit += end_credit

            if float_is_zero(init_bal, precision_digits=2) and \
               float_is_zero(period_data['debit'], precision_digits=2) and \
               float_is_zero(period_data['credit'], precision_digits=2):
                continue

            lines.append({
                'id': f'account_{account.id}',
                'name': f'{getattr(account, "code", "") + " " if getattr(account, "code", "") else ""}{account.name}',
                'level': 2,
                'columns': [
                    {'name': self._format_value(init_debit), 'no_format': init_debit, 'class': 'number'},
                    {'name': self._format_value(init_credit), 'no_format': init_credit, 'class': 'number'},
                    {'name': self._format_value(period_debit), 'no_format': period_debit, 'class': 'number'},
                    {'name': self._format_value(period_credit), 'no_format': period_credit, 'class': 'number'},
                    {'name': self._format_value(end_debit), 'no_format': end_debit, 'class': 'number'},
                    {'name': self._format_value(end_credit), 'no_format': end_credit, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'account_id': account.id,
                'parent_id': None,
            })

        # Total line — grey band
        lines.append({
            'id': 'trial_balance_total',
            'name': _('TOTAL'),
            'level': 0,
            'class': 'o_ent_group_header',
            'columns': [
                {'name': self._format_value(total_init_debit), 'no_format': total_init_debit, 'class': 'number'},
                {'name': self._format_value(total_init_credit), 'no_format': total_init_credit, 'class': 'number'},
                {'name': self._format_value(total_debit), 'no_format': total_debit, 'class': 'number'},
                {'name': self._format_value(total_credit), 'no_format': total_credit, 'class': 'number'},
                {'name': self._format_value(total_end_debit), 'no_format': total_end_debit, 'class': 'number'},
                {'name': self._format_value(total_end_credit), 'no_format': total_end_credit, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'is_title': True,
        })

        return lines

    # ========================================================================
    # GENERAL LEDGER
    # ========================================================================

    def _get_general_ledger_columns(self, date_from, date_to, comparison_periods, options):
        """General Ledger columns: Debit, Credit, Balance."""
        return [
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'},
        ]

    def _get_general_ledger_lines(self, options, date_from, date_to, comparison_periods):
        """Generate General Ledger report lines."""
        lines = []
        domain = self._build_domain(options, date_from, date_to)

        # Get all accounts with moves
        AccountMoveLine = self.env['account.move.line']
        results = AccountMoveLine.read_group(
            domain,
            ['account_id', 'debit', 'credit', 'balance'],
            ['account_id'],
        )

        # Initial balances
        init_domain = self._build_domain(options, date_to=date_from - timedelta(days=1))

        account_ids = [r['account_id'][0] for r in results if r['account_id']]
        if options.get('account_ids'):
            account_ids = options['account_ids']

        accounts = self.env['account.account'].browse(account_ids).sorted(key=lambda a: getattr(a, 'code', '') or '')

        for account in accounts:
            # Initial balance
            init_results = AccountMoveLine.read_group(
                init_domain + [('account_id', '=', account.id)],
                ['debit', 'credit', 'balance'],
                [],
            )
            init_balance = init_results[0]['balance'] if init_results else 0.0

            # Period totals
            period_results = AccountMoveLine.read_group(
                domain + [('account_id', '=', account.id)],
                ['debit', 'credit', 'balance'],
                [],
            )
            period_debit = period_results[0]['debit'] if period_results else 0.0
            period_credit = period_results[0]['credit'] if period_results else 0.0
            end_balance = init_balance + (period_results[0]['balance'] if period_results else 0.0)

            # Account header line
            lines.append({
                'id': f'account_{account.id}',
                'name': f'{getattr(account, "code", "") + " " if getattr(account, "code", "") else ""}{account.name}',
                'level': 1,
                'columns': [
                    {'name': self._format_value(period_debit), 'no_format': period_debit, 'class': 'number'},
                    {'name': self._format_value(period_credit), 'no_format': period_credit, 'class': 'number'},
                    {'name': self._format_value(end_balance), 'no_format': end_balance, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'account_id': account.id,
                'parent_id': None,
            })

            # Initial balance line
            if not float_is_zero(init_balance, precision_digits=2):
                lines.append({
                    'id': f'initial_{account.id}',
                    'name': _('Initial Balance'),
                    'level': 3,
                    'columns': [
                        {'name': '', 'class': 'number'},
                        {'name': '', 'class': 'number'},
                        {'name': self._format_value(init_balance), 'no_format': init_balance, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': f'account_{account.id}',
                    'class': 'o_account_report_initial_balance',
                })

            # Individual move lines if unfolded
            if options.get('unfold_all') or f'account_{account.id}' in options.get('unfolded_lines', []):
                move_lines = AccountMoveLine.search(
                    domain + [('account_id', '=', account.id)],
                    order='date, id',
                    limit=80,
                )
                cumulative_balance = init_balance
                for ml in move_lines:
                    cumulative_balance += ml.balance
                    lines.append({
                        'id': f'move_line_{ml.id}',
                        'name': ml.move_id.name or '',
                        'level': 3,
                        'columns': [
                            {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                            {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                            {'name': self._format_value(cumulative_balance), 'no_format': cumulative_balance, 'class': 'number'},
                        ],
                        'unfoldable': False,
                        'parent_id': f'account_{account.id}',
                        'caret_options': 'account.move',
                        'move_id': ml.move_id.id,
                        'date': str(ml.date),
                        'partner_name': ml.partner_id.name or '',
                        'ref': ml.ref or '',
                    })

        # Grand total line
        total_debit = sum(
            float(l['columns'][0].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns')
        )
        total_credit = sum(
            float(l['columns'][1].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns')
        )
        total_balance = sum(
            float(l['columns'][2].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns')
        )
        lines.append({
            'id': 'gl_total',
            'name': _('TOTAL'),
            'level': 0,
            'class': 'o_ent_group_header',
            'columns': [
                {'name': self._format_value(total_debit), 'no_format': total_debit, 'class': 'number'},
                {'name': self._format_value(total_credit), 'no_format': total_credit, 'class': 'number'},
                {'name': self._format_value(total_balance), 'no_format': total_balance, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'is_title': True,
        })

        return lines

    # ========================================================================
    # AGED RECEIVABLE / PAYABLE
    # ========================================================================

    def _get_aged_receivable_columns(self, date_from, date_to, comparison_periods, options):
        return self._get_aged_columns()

    def _get_aged_payable_columns(self, date_from, date_to, comparison_periods, options):
        return self._get_aged_columns()

    def _get_aged_columns(self):
        """Aged report columns: Not due, 0-30, 31-60, 61-90, 91-120, Older, Total."""
        return [
            {'name': _('Not due'), 'class': 'number'},
            {'name': _('0 - 30'), 'class': 'number'},
            {'name': _('31 - 60'), 'class': 'number'},
            {'name': _('61 - 90'), 'class': 'number'},
            {'name': _('91 - 120'), 'class': 'number'},
            {'name': _('Older'), 'class': 'number'},
            {'name': _('Total'), 'class': 'number'},
        ]

    def _get_aged_receivable_lines(self, options, date_from, date_to, comparison_periods):
        return self._get_aged_report_lines(options, date_to, 'asset_receivable')

    def _get_aged_payable_lines(self, options, date_from, date_to, comparison_periods):
        return self._get_aged_report_lines(options, date_to, 'liability_payable')

    def _get_aged_report_lines(self, options, date_to, account_type):
        """Generate Aged Receivable/Payable report lines."""
        lines = []
        periods = [
            {'name': _('Not due'), 'start': 0, 'stop': 0},
            {'name': _('0 - 30'), 'start': 1, 'stop': 30},
            {'name': _('31 - 60'), 'start': 31, 'stop': 60},
            {'name': _('61 - 90'), 'start': 61, 'stop': 90},
            {'name': _('91 - 120'), 'start': 91, 'stop': 120},
            {'name': _('Older'), 'start': 121, 'stop': False},
        ]

        domain = [
            ('account_id.account_type', '=', account_type),
            ('parent_state', '=', 'posted'),
            ('company_id', 'in', options.get('company_ids', [self.env.company.id])),
            ('reconciled', '=', False),
            ('date', '<=', date_to),
        ]

        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', options['partner_ids']))

        move_lines = self.env['account.move.line'].search(domain, order='partner_id, date')

        partner_data = {}
        totals = [0.0] * (len(periods) + 1)  # +1 for total column

        for ml in move_lines:
            partner = ml.partner_id
            partner_key = partner.id or 0
            if partner_key not in partner_data:
                partner_data[partner_key] = {
                    'partner': partner,
                    'values': [0.0] * (len(periods) + 1),
                }

            amount = ml.amount_residual
            date_maturity = ml.date_maturity or ml.date
            days = (date_to - date_maturity).days if isinstance(date_to, date) else 0

            # Determine which period bucket
            placed = False
            for idx, period in enumerate(periods):
                if period['stop'] is False:
                    if days >= period['start']:
                        partner_data[partner_key]['values'][idx] += amount
                        totals[idx] += amount
                        placed = True
                        break
                elif period['start'] == 0 and period['stop'] == 0:
                    if days <= 0:
                        partner_data[partner_key]['values'][idx] += amount
                        totals[idx] += amount
                        placed = True
                        break
                else:
                    if period['start'] <= days <= period['stop']:
                        partner_data[partner_key]['values'][idx] += amount
                        totals[idx] += amount
                        placed = True
                        break

            if not placed:
                partner_data[partner_key]['values'][-2] += amount
                totals[-2] += amount

            # Total column
            partner_data[partner_key]['values'][-1] += amount
            totals[-1] += amount

        # Build lines
        for partner_key, data in sorted(partner_data.items(), key=lambda x: x[1]['partner'].name or ''):
            partner = data['partner']
            values = data['values']
            columns = []
            for v in values:
                columns.append({
                    'name': self._format_value(v),
                    'no_format': v,
                    'class': 'number',
                })

            lines.append({
                'id': f'partner_{partner.id or 0}',
                'name': partner.name or _('Unknown Partner'),
                'level': 2,
                'columns': columns,
                'unfoldable': True,
                'unfolded': False,
                'partner_id': partner.id,
                'parent_id': None,
            })

        # Total line — grey band
        total_columns = [{'name': self._format_value(v), 'no_format': v, 'class': 'number'} for v in totals]
        lines.append({
            'id': 'aged_total',
            'name': _('TOTAL'),
            'level': 0,
            'class': 'o_ent_group_header',
            'columns': total_columns,
            'unfoldable': False,
            'parent_id': None,
            'is_title': True,
        })

        return lines

    # ========================================================================
    # PARTNER LEDGER
    # ========================================================================

    def _get_partner_ledger_columns(self, date_from, date_to, comparison_periods, options):
        """Partner Ledger columns: Initial Balance, Debit, Credit, End Balance."""
        return [
            {'name': _('Initial Balance'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('End Balance'), 'class': 'number'},
        ]

    def _get_partner_ledger_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Partner Ledger report lines — shows only receivable/payable movements."""
        lines = []
        domain = self._build_domain(options, date_from, date_to)
        # Account type filter: receivable, payable, or both
        acct_type = options.get('account_type', 'all')
        if acct_type == 'receivable':
            rp_filter = [('account_id.account_type', '=', 'asset_receivable')]
        elif acct_type == 'payable':
            rp_filter = [('account_id.account_type', '=', 'liability_payable')]
        else:
            rp_filter = [('account_id.account_type', 'in', ['asset_receivable', 'liability_payable'])]

        # Get all partners with moves on receivable/payable accounts
        AccountMoveLine = self.env['account.move.line']
        results = AccountMoveLine.read_group(
            domain + [('partner_id', '!=', False)] + rp_filter,
            ['partner_id', 'debit', 'credit', 'balance'],
            ['partner_id'],
        )

        # Initial balances (only receivable/payable)
        init_domain = self._build_domain(options, date_to=date_from - timedelta(days=1))

        for result in sorted(results, key=lambda r: r['partner_id'][1] if r['partner_id'] else ''):
            if not result['partner_id']:
                continue
            partner_id = result['partner_id'][0]
            partner_name = result['partner_id'][1]

            # Initial balance (only receivable/payable)
            init_results = AccountMoveLine.read_group(
                init_domain + [('partner_id', '=', partner_id)] + rp_filter,
                ['balance'],
                [],
            )
            init_balance = init_results[0]['balance'] if init_results else 0.0
            end_balance = init_balance + result['balance']

            lines.append({
                'id': f'partner_{partner_id}',
                'name': partner_name,
                'level': 1,
                'columns': [
                    {'name': self._format_value(init_balance), 'no_format': init_balance, 'class': 'number'},
                    {'name': self._format_value(result['debit']), 'no_format': result['debit'], 'class': 'number'},
                    {'name': self._format_value(result['credit']), 'no_format': result['credit'], 'class': 'number'},
                    {'name': self._format_value(end_balance), 'no_format': end_balance, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'partner_id': partner_id,
                'parent_id': None,
            })

        # Grand total line
        total_init = sum(
            float(l['columns'][0].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns') and len(l['columns']) >= 4
        )
        total_debit = sum(
            float(l['columns'][1].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns') and len(l['columns']) >= 4
        )
        total_credit = sum(
            float(l['columns'][2].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns') and len(l['columns']) >= 4
        )
        total_end = sum(
            float(l['columns'][3].get('no_format', 0))
            for l in lines if l.get('level') == 1 and l.get('columns') and len(l['columns']) >= 4
        )
        lines.append({
            'id': 'partner_ledger_total',
            'name': _('TOTAL'),
            'level': 0,
            'class': 'o_ent_group_header',
            'columns': [
                {'name': self._format_value(total_init), 'no_format': total_init, 'class': 'number'},
                {'name': self._format_value(total_debit), 'no_format': total_debit, 'class': 'number'},
                {'name': self._format_value(total_credit), 'no_format': total_credit, 'class': 'number'},
                {'name': self._format_value(total_end), 'no_format': total_end, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'is_title': True,
        })

        return lines

    # ========================================================================
    # CASH FLOW STATEMENT
    # ========================================================================

    def _get_cash_flow_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Cash Flow Statement report lines — Enterprise style."""
        lines = []
        num_cols = 1 + len(comparison_periods)

        # =========================================================
        # OPERATING ACTIVITIES
        # =========================================================
        net_profit = self._compute_net_profit(options, date_from, date_to, comparison_periods)

        receivable_change = self._compute_balance_change(
            options, date_from, date_to, ['asset_receivable'], comparison_periods
        )
        payable_change = self._compute_balance_change(
            options, date_from, date_to, ['liability_payable'], comparison_periods
        )

        operating_total = [
            net_profit[i] - receivable_change[i] + payable_change[i]
            for i in range(len(net_profit))
        ] if net_profit else [0.0] * num_cols

        lines.append(self._format_group_header(
            'operating', _('CASH FLOWS FROM OPERATING ACTIVITIES'), operating_total
        ))
        lines.append(self._format_detail_line(
            'net_profit', _('Net Profit'), net_profit, level=2, parent_id='operating'
        ))
        lines.append(self._format_detail_line(
            'receivable_change', _('Decrease/(Increase) in Receivables'),
            [-v for v in receivable_change], level=2, parent_id='operating'
        ))
        lines.append(self._format_detail_line(
            'payable_change', _('Increase/(Decrease) in Payables'),
            payable_change, level=2, parent_id='operating'
        ))

        # =========================================================
        # INVESTING ACTIVITIES
        # =========================================================
        investing_change = self._compute_balance_change(
            options, date_from, date_to, ['asset_fixed', 'asset_non_current'], comparison_periods
        )
        investing_total = [-v for v in investing_change]

        lines.append(self._format_group_header(
            'investing', _('CASH FLOWS FROM INVESTING ACTIVITIES'), investing_total
        ))
        lines.append(self._format_detail_line(
            'investing_assets', _('Purchase/Sale of Fixed Assets'),
            investing_total, level=2, parent_id='investing'
        ))

        # =========================================================
        # FINANCING ACTIVITIES
        # =========================================================
        financing_change = self._compute_balance_change(
            options, date_from, date_to,
            ['liability_non_current', 'equity', 'equity_unaffected'],
            comparison_periods
        )

        lines.append(self._format_group_header(
            'financing', _('CASH FLOWS FROM FINANCING ACTIVITIES'), financing_change
        ))
        lines.append(self._format_detail_line(
            'financing_equity', _('Equity/Long-term Debt Changes'),
            financing_change, level=2, parent_id='financing'
        ))

        # =========================================================
        # NET CHANGE + CASH POSITIONS
        # =========================================================
        net_cash = [
            operating_total[i] + investing_total[i] + financing_change[i]
            for i in range(num_cols)
        ]
        lines.append(self._format_group_header(
            'net_cash_change', _('NET INCREASE IN CASH'), net_cash
        ))

        cash_begin = self._compute_cash_balance(options, date_from - timedelta(days=1))
        cash_end = self._compute_cash_balance(options, date_to)
        lines.append(self._format_detail_line(
            'cash_begin', _('Cash at Beginning of Period'), [cash_begin], level=2
        ))
        lines.append(self._format_section_header(
            'cash_end', _('Cash at End of Period'), [cash_end], level=1, unfoldable=False
        ))

        return lines

    def _compute_net_profit(self, options, date_from, date_to, comparison_periods):
        """Compute net profit for a period."""
        domain = self._build_domain(options, date_from, date_to)
        income = self._sum_account_types(domain, ['income', 'income_other'])
        expense = self._sum_account_types(domain, ['expense', 'expense_depreciation', 'expense_direct_cost'])
        values = [income - expense]

        for period in comparison_periods:
            comp_domain = self._build_domain(options, period['date_from'], period['date_to'])
            comp_income = self._sum_account_types(comp_domain, ['income', 'income_other'])
            comp_expense = self._sum_account_types(comp_domain, ['expense', 'expense_depreciation', 'expense_direct_cost'])
            values.append(comp_income - comp_expense)

        return values

    def _compute_balance_change(self, options, date_from, date_to, account_types, comparison_periods):
        """Compute the change in balance for given account types."""
        domain_start = self._build_domain(options, date_to=date_from - timedelta(days=1))
        domain_end = self._build_domain(options, date_to=date_to)

        balance_start = self._sum_account_types(domain_start, account_types)
        balance_end = self._sum_account_types(domain_end, account_types)
        values = [balance_end - balance_start]

        for period in comparison_periods:
            comp_domain_start = self._build_domain(options, date_to=period['date_from'] - timedelta(days=1))
            comp_domain_end = self._build_domain(options, date_to=period['date_to'])
            comp_start = self._sum_account_types(comp_domain_start, account_types)
            comp_end = self._sum_account_types(comp_domain_end, account_types)
            values.append(comp_end - comp_start)

        return values

    def _compute_cash_flow_section(self, options, date_from, date_to, account_types, comparison_periods):
        """Compute values for a cash flow section."""
        domain = self._build_domain(options, date_from, date_to)
        val = self._sum_account_types(domain, account_types)
        values = [val]
        for period in comparison_periods:
            comp_domain = self._build_domain(options, period['date_from'], period['date_to'])
            values.append(self._sum_account_types(comp_domain, account_types))
        return values

    def _compute_cash_balance(self, options, as_of_date):
        """Compute cash balance as of a date."""
        domain = self._build_domain(options, date_to=as_of_date)
        return self._sum_account_types(domain, ['asset_cash'])


    # ========================================================================
    # TAX REPORT (VAT RETURN)
    # ========================================================================

    def _get_tax_report_columns(self, date_from, date_to, comparison_periods, options):
        """Tax Report columns: Amount and VAT Amount."""
        return [
            {'name': _('Amount'), 'class': 'number'},
            {'name': _('VAT Amount'), 'class': 'number'},
        ]

    def _get_tax_report_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Tax Report (VAT Return) lines — Saudi style."""
        lines = []
        AML = self.env['account.move.line']

        # Base domain
        base_domain = [
            ('parent_state', '=', 'posted'),
            ('company_id', 'in', options.get('company_ids', [self.env.company.id])),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if not options.get('all_entries', False):
            base_domain.append(('parent_state', '=', 'posted'))

        # ── Helper: get tax amounts by tax type ──
        def get_tax_data(tax_type_use, tax_scope=None):
            """Get base amount and tax amount for a tax type."""
            tax_domain = [('type_tax_use', '=', tax_type_use)]
            if tax_scope:
                tax_domain.append(('amount', '=', tax_scope))
            taxes = self.env['account.tax'].search(tax_domain)
            if not taxes:
                return 0.0, 0.0

            # Find move lines with these taxes
            domain = base_domain + [('tax_ids', 'in', taxes.ids)]
            base_results = AML.read_group(domain, ['balance'], [])
            base_amount = abs(base_results[0]['balance']) if base_results else 0.0

            # Tax amount lines (generated by taxes)
            tax_line_domain = base_domain + [('tax_line_id', 'in', taxes.ids)]
            tax_results = AML.read_group(tax_line_domain, ['balance'], [])
            tax_amount = abs(tax_results[0]['balance']) if tax_results else 0.0

            return base_amount, tax_amount

        def get_sale_tax_data_by_rate(rate):
            """Get sale tax data for a specific rate."""
            taxes = self.env['account.tax'].search([
                ('type_tax_use', '=', 'sale'),
                ('amount', '=', rate),
            ])
            if not taxes:
                return 0.0, 0.0
            domain = base_domain + [('tax_ids', 'in', taxes.ids)]
            base_results = AML.read_group(domain, ['balance'], [])
            base_amount = abs(base_results[0]['balance']) if base_results else 0.0
            tax_line_domain = base_domain + [('tax_line_id', 'in', taxes.ids)]
            tax_results = AML.read_group(tax_line_domain, ['balance'], [])
            tax_amount = abs(tax_results[0]['balance']) if tax_results else 0.0
            return base_amount, tax_amount

        def get_purchase_tax_data_by_rate(rate):
            """Get purchase tax data for a specific rate."""
            taxes = self.env['account.tax'].search([
                ('type_tax_use', '=', 'purchase'),
                ('amount', '=', rate),
            ])
            if not taxes:
                return 0.0, 0.0
            domain = base_domain + [('tax_ids', 'in', taxes.ids)]
            base_results = AML.read_group(domain, ['balance'], [])
            base_amount = abs(base_results[0]['balance']) if base_results else 0.0
            tax_line_domain = base_domain + [('tax_line_id', 'in', taxes.ids)]
            tax_results = AML.read_group(tax_line_domain, ['balance'], [])
            tax_amount = abs(tax_results[0]['balance']) if tax_results else 0.0
            return base_amount, tax_amount

        # Get all sale taxes to calculate totals
        all_sale_taxes = self.env['account.tax'].search([('type_tax_use', '=', 'sale')])
        all_purchase_taxes = self.env['account.tax'].search([('type_tax_use', '=', 'purchase')])

        # Standard rate (15% in Saudi)
        std_sale_base, std_sale_vat = get_sale_tax_data_by_rate(15.0)
        # Zero-rated sales
        zero_sale_base, zero_sale_vat = get_sale_tax_data_by_rate(0.0)
        # Exempt sales (no tax lines)
        exempt_sale_taxes = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 0),
            ('name', 'ilike', 'exempt'),
        ])
        exempt_sale_base = 0.0
        if exempt_sale_taxes:
            domain = base_domain + [('tax_ids', 'in', exempt_sale_taxes.ids)]
            results = AML.read_group(domain, ['balance'], [])
            exempt_sale_base = abs(results[0]['balance']) if results else 0.0

        # Total sales
        total_sale_base = 0.0
        total_sale_vat = 0.0
        if all_sale_taxes:
            domain = base_domain + [('tax_ids', 'in', all_sale_taxes.ids)]
            results = AML.read_group(domain, ['balance'], [])
            total_sale_base = abs(results[0]['balance']) if results else 0.0
            tax_domain = base_domain + [('tax_line_id', 'in', all_sale_taxes.ids)]
            results = AML.read_group(tax_domain, ['balance'], [])
            total_sale_vat = abs(results[0]['balance']) if results else 0.0

        # Purchase taxes
        std_purch_base, std_purch_vat = get_purchase_tax_data_by_rate(15.0)
        zero_purch_base, zero_purch_vat = get_purchase_tax_data_by_rate(0.0)

        total_purch_base = 0.0
        total_purch_vat = 0.0
        if all_purchase_taxes:
            domain = base_domain + [('tax_ids', 'in', all_purchase_taxes.ids)]
            results = AML.read_group(domain, ['balance'], [])
            total_purch_base = abs(results[0]['balance']) if results else 0.0
            tax_domain = base_domain + [('tax_line_id', 'in', all_purchase_taxes.ids)]
            results = AML.read_group(tax_domain, ['balance'], [])
            total_purch_vat = abs(results[0]['balance']) if results else 0.0

        # ═══════════════════════════════════════
        # VAT ON SALES section
        # ═══════════════════════════════════════
        lines.append(self._format_group_header('vat_sales', _('VAT on Sales:'), [total_sale_base, total_sale_vat]))

        lines.append(self._format_tax_line('tax_1', '1. Standard rated sales', std_sale_base, std_sale_vat))
        lines.append(self._format_tax_line('tax_2', '2. Private Healthcare / Private Education / First house sales to citizens', 0.0, 0.0))
        lines.append(self._format_tax_line('tax_3', '3. Zero rated domestic sales', zero_sale_base, None))
        lines.append(self._format_tax_line('tax_4', '4. Exports', 0.0, None))
        lines.append(self._format_tax_line('tax_5', '5. Exempt sales', exempt_sale_base, None))
        lines.append(self._format_tax_line('tax_6', '6. Total Sales', total_sale_base, total_sale_vat))

        # ═══════════════════════════════════════
        # VAT ON PURCHASES section
        # ═══════════════════════════════════════
        lines.append(self._format_group_header('vat_purchases', _('VAT on Purchases:'), [total_purch_base, total_purch_vat]))

        lines.append(self._format_tax_line('tax_7', '7. Standard rated domestic purchases', std_purch_base, std_purch_vat))
        lines.append(self._format_tax_line('tax_8', '8. Imports subject to VAT paid at customs', 0.0, 0.0))
        lines.append(self._format_tax_line('tax_9', '9. Imports subject to VAT accounted for through reverse charge mechanism', 0.0, 0.0))
        lines.append(self._format_tax_line('tax_10', '10. Zero rated purchases', zero_purch_base, None))
        lines.append(self._format_tax_line('tax_11', '11. Exempt purchases', 0.0, None))
        lines.append(self._format_tax_line('tax_12', '12. Total Purchases', total_purch_base, total_purch_vat))

        # ═══════════════════════════════════════
        # VAT CALCULATION lines
        # ═══════════════════════════════════════
        vat_due = total_sale_vat - total_purch_vat
        lines.append(self._format_tax_line('tax_13', '13. Total VAT due for current period', None, vat_due))
        lines.append(self._format_tax_line('tax_14', '14. Corrections from previous period (between +- SAR 5000)', None, 0.0))
        lines.append(self._format_tax_line('tax_15', '15. VAT credit carried forward from previous period', None, 0.0))

        # Net VAT — grey band
        net_vat = vat_due
        lines.append(self._format_group_header('net_vat', _('16. Net VAT due (or claim)'), [net_vat]))

        return lines

    def _format_tax_line(self, line_id, name, amount, vat_amount):
        """Format a single tax report line with Amount and VAT Amount columns."""
        columns = []
        if amount is not None:
            columns.append({
                'name': self._format_value(amount),
                'no_format': amount,
                'class': 'number',
            })
        else:
            columns.append({'name': '', 'no_format': 0, 'class': 'number'})

        if vat_amount is not None:
            columns.append({
                'name': self._format_value(vat_amount),
                'no_format': vat_amount,
                'class': 'number',
            })
        else:
            columns.append({'name': '', 'no_format': 0, 'class': 'number'})

        return {
            'id': line_id,
            'name': name,
            'level': 2,
            'columns': columns,
            'unfoldable': False,
            'unfolded': False,
            'parent_id': None,
        }


    # ========================================================================
    # ANALYTIC ACCOUNT REPORT
    # ========================================================================

    def _get_analytic_account_columns(self, date_from, date_to, comparison_periods, options):
        """Analytic Account columns."""
        cols = [
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'},
        ]
        for period in comparison_periods:
            cols.append({'name': period['string'], 'class': 'number'})
        return cols

    def _get_analytic_account_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Analytic Account report lines — grouped by plan."""
        lines = []
        AML = self.env['account.move.line']
        company_ids = options.get('company_ids', [self.env.company.id])

        base_domain = [
            ('parent_state', '=', 'posted'),
            ('analytic_distribution', '!=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', 'in', company_ids),
        ]
        if not options.get('all_entries', False):
            base_domain.append(('parent_state', '=', 'posted'))
        if options.get('journal_ids'):
            base_domain.append(('journal_id', 'in', options['journal_ids']))
        if options.get('partner_ids'):
            base_domain.append(('partner_id', 'in', options['partner_ids']))

        # Get all move lines with analytic distribution
        move_lines = AML.sudo().search(base_domain)

        # Build data: plan -> account -> {debit, credit, balance}
        plans = self.env['account.analytic.plan'].sudo().search([])
        accounts = self.env['account.analytic.account'].sudo().search([])
        plan_map = {p.id: p for p in plans}
        acc_map = {a.id: a for a in accounts}
        acc_plan = {a.id: a.plan_id.id for a in accounts if a.plan_id}

        # Apply analytic filters from options
        selected_acc_ids = options.get('analytic_account_ids', [])
        selected_plan_ids = options.get('analytic_plan_ids', [])

        data = {}  # plan_id -> acc_id -> {debit, credit}
        for ml in move_lines:
            dist = ml.analytic_distribution or {}
            for acc_id_str, pct in dist.items():
                try:
                    acc_id = int(acc_id_str)
                except (ValueError, TypeError):
                    continue
                # Filter by selected analytic accounts
                if selected_acc_ids and acc_id not in selected_acc_ids:
                    continue
                pid = acc_plan.get(acc_id)
                if not pid:
                    continue
                # Filter by selected analytic plans
                if selected_plan_ids and pid not in selected_plan_ids:
                    continue
                factor = pct / 100.0
                data.setdefault(pid, {}).setdefault(acc_id, {'debit': 0.0, 'credit': 0.0})
                data[pid][acc_id]['debit'] += ml.debit * factor
                data[pid][acc_id]['credit'] += ml.credit * factor

        # Comparison periods
        comp_data = []
        for period in comparison_periods:
            comp_domain = [
                ('parent_state', '=', 'posted'),
                ('analytic_distribution', '!=', False),
                ('date', '>=', period['date_from']),
                ('date', '<=', period['date_to']),
                ('company_id', 'in', company_ids),
            ]
            if options.get('journal_ids'):
                comp_domain.append(('journal_id', 'in', options['journal_ids']))
            if options.get('partner_ids'):
                comp_domain.append(('partner_id', 'in', options['partner_ids']))
            comp_lines = AML.sudo().search(comp_domain)
            cd = {}
            for ml in comp_lines:
                dist = ml.analytic_distribution or {}
                for acc_id_str, pct in dist.items():
                    try:
                        acc_id = int(acc_id_str)
                    except (ValueError, TypeError):
                        continue
                    if selected_acc_ids and acc_id not in selected_acc_ids:
                        continue
                    pid = acc_plan.get(acc_id)
                    if not pid:
                        continue
                    if selected_plan_ids and pid not in selected_plan_ids:
                        continue
                    factor = pct / 100.0
                    cd.setdefault(pid, {}).setdefault(acc_id, 0.0)
                    cd[pid][acc_id] += (ml.credit - ml.debit) * factor
            comp_data.append(cd)

        grand_debit = 0.0
        grand_credit = 0.0
        grand_balance = 0.0
        grand_comp = [0.0] * len(comparison_periods)

        for pid in sorted(data.keys(), key=lambda x: plan_map[x].name if x in plan_map else ''):
            plan = plan_map.get(pid)
            if not plan:
                continue
            plan_debit = 0.0
            plan_credit = 0.0
            plan_balance = 0.0
            plan_comp = [0.0] * len(comparison_periods)
            children = []

            for acc_id in sorted(data[pid].keys(), key=lambda x: acc_map[x].name if x in acc_map else ''):
                acc = acc_map.get(acc_id)
                if not acc:
                    continue
                d = data[pid][acc_id]['debit']
                c = data[pid][acc_id]['credit']
                b = c - d
                plan_debit += d
                plan_credit += c
                plan_balance += b

                cols = [
                    {'name': self._format_value(d), 'no_format': d, 'class': 'number'},
                    {'name': self._format_value(c), 'no_format': c, 'class': 'number'},
                    {'name': self._format_value(b), 'no_format': b, 'class': 'number'},
                ]
                for i, period in enumerate(comparison_periods):
                    cv = comp_data[i].get(pid, {}).get(acc_id, 0.0)
                    plan_comp[i] += cv
                    cols.append({'name': self._format_value(cv), 'no_format': cv, 'class': 'number'})

                children.append({
                    'id': f'analytic_acc_{acc_id}',
                    'name': f'{getattr(acc, "code", "") + " " if getattr(acc, "code", "") else ""}{acc.name}'.strip(),
                    'level': 2,
                    'columns': cols,
                    'unfoldable': True,
                    'unfolded': options.get('unfold_all', False),
                    'parent_id': f'analytic_plan_{pid}',
                    'analytic_account_id': acc_id,
                })

            # Plan header (grey band)
            plan_cols = [plan_debit, plan_credit, plan_balance] + plan_comp
            lines.append(self._format_section_header(f'analytic_plan_{pid}', plan.name, plan_cols, level=0, unfoldable=True))
            lines.extend(children)

            grand_debit += plan_debit
            grand_credit += plan_credit
            grand_balance += plan_balance
            for i in range(len(comparison_periods)):
                grand_comp[i] += plan_comp[i]

        # Grand total
        total_vals = [grand_debit, grand_credit, grand_balance] + grand_comp
        lines.append(self._format_group_header('analytic_grand_total', _('TOTAL'), total_vals))

        return lines

    # ========================================================================
    # ANALYTIC PLAN REPORT
    # ========================================================================

    def _get_analytic_plan_columns(self, date_from, date_to, comparison_periods, options):
        """Analytic Plan report columns."""
        cols = [
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'},
        ]
        for period in comparison_periods:
            cols.append({'name': period['string'], 'class': 'number'})
        return cols

    def _get_analytic_plan_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Analytic Plan summary report."""
        lines = []
        AML = self.env['account.move.line']
        company_ids = options.get('company_ids', [self.env.company.id])

        base_domain = [
            ('parent_state', '=', 'posted'),
            ('analytic_distribution', '!=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', 'in', company_ids),
        ]
        if options.get('journal_ids'):
            base_domain.append(('journal_id', 'in', options['journal_ids']))
        if options.get('partner_ids'):
            base_domain.append(('partner_id', 'in', options['partner_ids']))

        move_lines = AML.sudo().search(base_domain)

        plans = self.env['account.analytic.plan'].sudo().search([])
        accounts = self.env['account.analytic.account'].sudo().search([])
        plan_map = {p.id: p for p in plans}
        acc_plan = {a.id: a.plan_id.id for a in accounts if a.plan_id}

        # Apply analytic filters from options
        selected_acc_ids = options.get('analytic_account_ids', [])
        selected_plan_ids = options.get('analytic_plan_ids', [])

        data = {}  # plan_id -> {debit, credit}
        for ml in move_lines:
            dist = ml.analytic_distribution or {}
            for acc_id_str, pct in dist.items():
                try:
                    acc_id = int(acc_id_str)
                except (ValueError, TypeError):
                    continue
                if selected_acc_ids and acc_id not in selected_acc_ids:
                    continue
                pid = acc_plan.get(acc_id)
                if not pid:
                    continue
                if selected_plan_ids and pid not in selected_plan_ids:
                    continue
                factor = pct / 100.0
                data.setdefault(pid, {'debit': 0.0, 'credit': 0.0})
                data[pid]['debit'] += ml.debit * factor
                data[pid]['credit'] += ml.credit * factor

        # Comparison periods
        comp_data = []
        for period in comparison_periods:
            comp_domain = [
                ('parent_state', '=', 'posted'),
                ('analytic_distribution', '!=', False),
                ('date', '>=', period['date_from']),
                ('date', '<=', period['date_to']),
                ('company_id', 'in', company_ids),
            ]
            if options.get('journal_ids'):
                comp_domain.append(('journal_id', 'in', options['journal_ids']))
            if options.get('partner_ids'):
                comp_domain.append(('partner_id', 'in', options['partner_ids']))
            comp_lines = AML.sudo().search(comp_domain)
            cd = {}
            for ml in comp_lines:
                dist = ml.analytic_distribution or {}
                for acc_id_str, pct in dist.items():
                    try:
                        acc_id = int(acc_id_str)
                    except (ValueError, TypeError):
                        continue
                    if selected_acc_ids and acc_id not in selected_acc_ids:
                        continue
                    pid = acc_plan.get(acc_id)
                    if not pid:
                        continue
                    if selected_plan_ids and pid not in selected_plan_ids:
                        continue
                    factor = pct / 100.0
                    cd.setdefault(pid, 0.0)
                    cd[pid] += (ml.credit - ml.debit) * factor
            comp_data.append(cd)

        grand_debit = 0.0
        grand_credit = 0.0
        grand_balance = 0.0
        grand_comp = [0.0] * len(comparison_periods)

        for pid in sorted(data.keys(), key=lambda x: plan_map[x].name if x in plan_map else ''):
            plan = plan_map.get(pid)
            if not plan:
                continue
            d = data[pid]['debit']
            c = data[pid]['credit']
            b = c - d
            grand_debit += d
            grand_credit += c
            grand_balance += b

            cols = [
                {'name': self._format_value(d), 'no_format': d, 'class': 'number'},
                {'name': self._format_value(c), 'no_format': c, 'class': 'number'},
                {'name': self._format_value(b), 'no_format': b, 'class': 'number'},
            ]
            for i, period in enumerate(comparison_periods):
                cv = comp_data[i].get(pid, 0.0)
                grand_comp[i] += cv
                cols.append({'name': self._format_value(cv), 'no_format': cv, 'class': 'number'})

            lines.append({
                'id': f'plan_{pid}',
                'name': plan.name,
                'level': 1,
                'columns': cols,
                'unfoldable': False,
                'parent_id': None,
            })

        # Grand total
        total_vals = [grand_debit, grand_credit, grand_balance] + grand_comp
        lines.append(self._format_group_header('plan_total', _('TOTAL'), total_vals))

        return lines

    # ========================================================================
    # PETTY CASH REPORT
    # ========================================================================

    def _get_petty_cash_columns(self, date_from, date_to, comparison_periods, options):
        """Petty Cash report columns."""
        return [
            {'name': _('Date'), 'class': ''},
            {'name': _('Reference'), 'class': ''},
            {'name': _('Partner'), 'class': ''},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'},
        ]

    def _get_petty_cash_lines(self, options, date_from, date_to, comparison_periods):
        """Generate Petty Cash report lines — one section per cash account.
        
        The journal filter selects WHICH petty cash accounts to display,
        but ALL transactions hitting those accounts are shown (including
        internal transfers from bank journals).
        """
        lines = []
        company_ids = options.get('company_ids', [self.env.company.id])

        # Find petty cash accounts: accounts linked to cash-type journals
        cash_journals = self.env['account.journal'].sudo().search([
            ('type', '=', 'cash'),
            ('company_id', 'in', company_ids),
        ])

        # If journal filter is active, use it to select which cash accounts to show
        if options.get('journal_ids'):
            selected_journals = cash_journals.filtered(lambda j: j.id in options['journal_ids'])
        else:
            selected_journals = cash_journals

        cash_account_ids = set()
        for j in selected_journals:
            for acc in j.default_account_id:
                cash_account_ids.add(acc.id)

        # If account filter is active, intersect with it
        if options.get('account_ids'):
            cash_account_ids = cash_account_ids & set(options['account_ids'])

        if not cash_account_ids:
            return lines

        cash_accounts = self.env['account.account'].sudo().browse(list(cash_account_ids)).sorted(key=lambda a: getattr(a, 'code', '') or '')

        grand_init_balance = 0.0
        grand_debit = 0.0
        grand_credit = 0.0

        for account in cash_accounts:
            # Build domain for this account — NO journal filter here,
            # we want ALL transactions hitting this petty cash account
            domain = [
                ('account_id', '=', account.id),
                ('company_id', 'in', company_ids),
                ('parent_state', '=', 'posted'),
            ]

            # Initial balance (before date_from)
            init_domain = domain + [('date', '<', date_from)]
            if options.get('partner_ids'):
                init_domain.append(('partner_id', 'in', options['partner_ids']))
            init_results = self.env['account.move.line'].sudo().read_group(
                init_domain, ['debit', 'credit'], []
            )
            init_debit = init_results[0]['debit'] if init_results and init_results[0]['debit'] else 0.0
            init_credit = init_results[0]['credit'] if init_results and init_results[0]['credit'] else 0.0
            init_balance = init_debit - init_credit

            # Period entries — show ALL journals, not filtered by journal_ids
            period_domain = domain + [('date', '>=', date_from), ('date', '<=', date_to)]
            if options.get('partner_ids'):
                period_domain.append(('partner_id', 'in', options['partner_ids']))

            move_lines = self.env['account.move.line'].sudo().search(period_domain, order='date, id')

            if not move_lines and float_is_zero(init_balance, precision_digits=2):
                continue

            acc_debit = sum(ml.debit for ml in move_lines)
            acc_credit = sum(ml.credit for ml in move_lines)
            acc_balance = init_balance + acc_debit - acc_credit

            # Account header
            lines.append({
                'id': f'petty_cash_{account.id}',
                'name': f'{getattr(account, "code", "") + " " if getattr(account, "code", "") else ""}{account.name}',
                'level': 1,
                'columns': [
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': self._format_value(init_debit + acc_debit), 'no_format': init_debit + acc_debit, 'class': 'number'},
                    {'name': self._format_value(init_credit + acc_credit), 'no_format': init_credit + acc_credit, 'class': 'number'},
                    {'name': self._format_value(acc_balance), 'no_format': acc_balance, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': True,
                'parent_id': None,
            })

            # Always show initial balance as a separate line at the top
            lines.append({
                'id': f'petty_init_{account.id}',
                'name': _('Initial Balance'),
                'level': 2,
                'columns': [
                    {'name': '', 'class': ''},
                    {'name': _('Opening Balance'), 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': self._format_value(init_debit), 'no_format': init_debit, 'class': 'number'},
                    {'name': self._format_value(init_credit), 'no_format': init_credit, 'class': 'number'},
                    {'name': self._format_value(init_balance), 'no_format': init_balance, 'class': 'number'},
                ],
                'unfoldable': False,
                'parent_id': f'petty_cash_{account.id}',
                'class': 'o_account_reports_initial_balance',
            })

            # Detail transaction lines — always visible
            running = init_balance
            for ml in move_lines:
                running += ml.debit - ml.credit
                lines.append({
                    'id': f'petty_ml_{ml.id}',
                    'name': ml.move_id.name or '',
                    'level': 3,
                    'columns': [
                        {'name': str(ml.date), 'class': ''},
                        {'name': ml.ref or ml.name or '', 'class': ''},
                        {'name': ml.partner_id.name or '', 'class': ''},
                        {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                        {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                        {'name': self._format_value(running), 'no_format': running, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': f'petty_cash_{account.id}',
                    'caret_options': 'account.move',
                    'move_id': ml.move_id.id,
                })

            grand_init_balance += init_balance
            grand_debit += init_debit + acc_debit
            grand_credit += init_credit + acc_credit

        # Grand total (debit and credit already include initial balances)
        grand_balance = grand_debit - grand_credit
        lines.append({
            'id': 'petty_cash_total',
            'name': _('TOTAL'),
            'level': 0,
            'columns': [
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': self._format_value(grand_debit), 'no_format': grand_debit, 'class': 'number'},
                {'name': self._format_value(grand_credit), 'no_format': grand_credit, 'class': 'number'},
                {'name': self._format_value(grand_balance), 'no_format': grand_balance, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'class': 'total',
        })

        return lines

    # ========================================================================
    # BANK BOOK REPORT
    # ========================================================================

    def _get_bank_book_columns(self, date_from, date_to, comparison_periods, options):
        return [
            {'name': _('Date'), 'class': ''},
            {'name': _('Reference'), 'class': ''},
            {'name': _('Partner'), 'class': ''},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'},
        ]

    def _get_bank_book_lines(self, options, date_from, date_to, comparison_periods):
        lines = []
        company_ids = options.get('company_ids', [self.env.company.id])

        bank_journals = self.env['account.journal'].sudo().search([
            ('type', '=', 'bank'),
            ('company_id', 'in', company_ids),
        ])
        bank_account_ids = set()
        for j in bank_journals:
            if j.default_account_id:
                bank_account_ids.add(j.default_account_id.id)

        if not bank_account_ids:
            return lines

        if options.get('account_ids'):
            bank_account_ids = bank_account_ids & set(options['account_ids'])
            if not bank_account_ids:
                return lines

        bank_accounts = self.env['account.account'].sudo().browse(list(bank_account_ids)).sorted(key=lambda a: a.name or '')

        grand_debit = 0.0
        grand_credit = 0.0
        grand_init_balance = 0.0

        for account in bank_accounts:
            domain = [
                ('account_id', '=', account.id),
                ('company_id', 'in', company_ids),
                ('parent_state', '=', 'posted'),
            ]

            init_domain = domain + [('date', '<', date_from)]
            if options.get('partner_ids'):
                init_domain.append(('partner_id', 'in', options['partner_ids']))
            init_results = self.env['account.move.line'].sudo().read_group(init_domain, ['debit', 'credit'], [])
            init_debit = init_results[0]['debit'] if init_results and init_results[0]['debit'] else 0.0
            init_credit = init_results[0]['credit'] if init_results and init_results[0]['credit'] else 0.0
            init_balance = init_debit - init_credit

            period_domain = domain + [('date', '>=', date_from), ('date', '<=', date_to)]
            if options.get('partner_ids'):
                period_domain.append(('partner_id', 'in', options['partner_ids']))
            if options.get('journal_ids'):
                period_domain.append(('journal_id', 'in', options['journal_ids']))

            move_lines = self.env['account.move.line'].sudo().search(period_domain, order='date, id')

            if not move_lines and float_is_zero(init_balance, precision_digits=2):
                continue

            acc_debit = sum(ml.debit for ml in move_lines)
            acc_credit = sum(ml.credit for ml in move_lines)
            acc_balance = init_balance + acc_debit - acc_credit
            acc_code = getattr(account, 'code', '') or ''
            acc_display = f'{acc_code} {account.name}'.strip() if acc_code else account.name

            lines.append({
                'id': f'bank_book_{account.id}',
                'name': acc_display,
                'level': 1,
                'columns': [
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': self._format_value(acc_debit), 'no_format': acc_debit, 'class': 'number'},
                    {'name': self._format_value(acc_credit), 'no_format': acc_credit, 'class': 'number'},
                    {'name': self._format_value(acc_balance), 'no_format': acc_balance, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'parent_id': None,
            })

            if options.get('unfold_all', False):
                if not float_is_zero(init_balance, precision_digits=2):
                    lines.append({
                        'id': f'bank_init_{account.id}',
                        'name': _('Initial Balance'),
                        'level': 3,
                        'columns': [
                            {'name': '', 'class': ''},
                            {'name': '', 'class': ''},
                            {'name': '', 'class': ''},
                            {'name': self._format_value(init_debit), 'no_format': init_debit, 'class': 'number'},
                            {'name': self._format_value(init_credit), 'no_format': init_credit, 'class': 'number'},
                            {'name': self._format_value(init_balance), 'no_format': init_balance, 'class': 'number'},
                        ],
                        'unfoldable': False,
                        'parent_id': f'bank_book_{account.id}',
                        'class': 'o_account_reports_initial_balance',
                    })

                running = init_balance
                for ml in move_lines:
                    running += ml.debit - ml.credit
                    lines.append({
                        'id': f'bank_ml_{ml.id}',
                        'name': ml.move_id.name or '',
                        'level': 3,
                        'columns': [
                            {'name': str(ml.date), 'class': ''},
                            {'name': ml.ref or ml.name or '', 'class': ''},
                            {'name': ml.partner_id.name or '', 'class': ''},
                            {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                            {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                            {'name': self._format_value(running), 'no_format': running, 'class': 'number'},
                        ],
                        'unfoldable': False,
                        'parent_id': f'bank_book_{account.id}',
                        'caret_options': 'account.move',
                        'move_id': ml.move_id.id,
                    })

            grand_debit += acc_debit
            grand_credit += acc_credit
            grand_init_balance += init_balance

        grand_balance = grand_init_balance + grand_debit - grand_credit
        lines.append({
            'id': 'bank_book_total',
            'name': _('TOTAL'),
            'level': 0,
            'columns': [
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': self._format_value(grand_debit), 'no_format': grand_debit, 'class': 'number'},
                {'name': self._format_value(grand_credit), 'no_format': grand_credit, 'class': 'number'},
                {'name': self._format_value(grand_balance), 'no_format': grand_balance, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'class': 'total',
        })
        return lines

    # ========================================================================
    # DAY BOOK REPORT
    # ========================================================================

    def _get_day_book_columns(self, date_from, date_to, comparison_periods, options):
        return [
            {'name': _('Entry'), 'class': ''},
            {'name': _('Account'), 'class': ''},
            {'name': _('Partner'), 'class': ''},
            {'name': _('Label'), 'class': ''},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
        ]

    def _get_day_book_lines(self, options, date_from, date_to, comparison_periods):
        from itertools import groupby as igroupby
        lines = []
        company_ids = options.get('company_ids', [self.env.company.id])

        domain = [
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', 'in', company_ids),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))
        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', options['partner_ids']))
        if options.get('account_ids'):
            domain.append(('account_id', 'in', options['account_ids']))

        move_lines = self.env['account.move.line'].sudo().search(domain, order='date, move_id, id')

        grand_debit = 0.0
        grand_credit = 0.0

        for dt, date_group in igroupby(move_lines, key=lambda ml: ml.date):
            date_lines = list(date_group)
            day_debit = sum(ml.debit for ml in date_lines)
            day_credit = sum(ml.credit for ml in date_lines)

            lines.append({
                'id': f'day_{dt}',
                'name': str(dt),
                'level': 1,
                'columns': [
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': self._format_value(day_debit), 'no_format': day_debit, 'class': 'number'},
                    {'name': self._format_value(day_credit), 'no_format': day_credit, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'parent_id': None,
            })

            if options.get('unfold_all', False):
                for move, move_group in igroupby(date_lines, key=lambda ml: ml.move_id):
                    mls = list(move_group)
                    for ml in mls:
                        acc_code = getattr(ml.account_id, 'code', '') or ''
                        acc_name = f'{acc_code} {ml.account_id.name}'.strip() if acc_code else (ml.account_id.name or '')
                        lines.append({
                            'id': f'daybook_ml_{ml.id}',
                            'name': '',
                            'level': 3,
                            'columns': [
                                {'name': move.name or '', 'class': ''},
                                {'name': acc_name, 'class': ''},
                                {'name': ml.partner_id.name or '', 'class': ''},
                                {'name': ml.name or ml.ref or '', 'class': ''},
                                {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                                {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                            ],
                            'unfoldable': False,
                            'parent_id': f'day_{dt}',
                            'caret_options': 'account.move',
                            'move_id': move.id,
                        })

            grand_debit += day_debit
            grand_credit += day_credit

        lines.append({
            'id': 'day_book_total',
            'name': _('TOTAL'),
            'level': 0,
            'columns': [
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': '', 'class': ''},
                {'name': self._format_value(grand_debit), 'no_format': grand_debit, 'class': 'number'},
                {'name': self._format_value(grand_credit), 'no_format': grand_credit, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'class': 'total',
        })
        return lines

    # ========================================================================
    # BUDGET VS ACTUAL REPORT
    # ========================================================================

    def _get_budget_vs_actual_columns(self, date_from, date_to, comparison_periods, options):
        return [
            {'name': _('Budget'), 'class': 'number'},
            {'name': _('Actual'), 'class': 'number'},
            {'name': _('Variance'), 'class': 'number'},
            {'name': _('Variance %'), 'class': 'number'},
        ]

    def _get_budget_vs_actual_lines(self, options, date_from, date_to, comparison_periods):
        lines = []
        company_ids = options.get('company_ids', [self.env.company.id])

        domain = [
            ('parent_state', '=', 'posted'),
            ('analytic_distribution', '!=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', 'in', company_ids),
        ]
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))
        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', options['partner_ids']))

        move_lines = self.env['account.move.line'].sudo().search(domain)

        plans = self.env['account.analytic.plan'].sudo().search([])
        accounts = self.env['account.analytic.account'].sudo().search([])
        plan_map = {p.id: p for p in plans}
        acc_map = {a.id: a for a in accounts}
        acc_plan = {a.id: a.plan_id.id for a in accounts if a.plan_id}

        actual_data = {}
        for ml in move_lines:
            dist = ml.analytic_distribution or {}
            for acc_id_str, pct in dist.items():
                try:
                    acc_id = int(acc_id_str)
                except (ValueError, TypeError):
                    continue
                pid = acc_plan.get(acc_id)
                if not pid:
                    continue
                factor = pct / 100.0
                actual_data.setdefault(pid, {}).setdefault(acc_id, 0.0)
                actual_data[pid][acc_id] += (ml.debit - ml.credit) * factor

        budget_data = {}
        # Use simple.budget.line from our module
        if 'simple.budget.line' in self.env:
            try:
                budget_lines = self.env['simple.budget.line'].sudo().search([
                    ('date_from', '<=', date_to),
                    ('date_to', '>=', date_from),
                    ('budget_id.state', 'in', ['confirmed', 'done']),
                    ('company_id', 'in', company_ids),
                ])
                for bl in budget_lines:
                    if bl.analytic_account_id:
                        acc_id = bl.analytic_account_id.id
                        pid = acc_plan.get(acc_id)
                        if pid:
                            budget_data.setdefault(pid, {}).setdefault(acc_id, 0.0)
                            bl_days = (bl.date_to - bl.date_from).days + 1
                            period_start = max(bl.date_from, date_from)
                            period_end = min(bl.date_to, date_to)
                            overlap_days = (period_end - period_start).days + 1
                            if bl_days > 0 and overlap_days > 0:
                                budget_data[pid][acc_id] += bl.planned_amount * overlap_days / bl_days
            except Exception:
                pass

        all_pids = set(list(actual_data.keys()) + list(budget_data.keys()))
        grand_budget = 0.0
        grand_actual = 0.0

        for pid in sorted(all_pids, key=lambda x: plan_map[x].name if x in plan_map else ''):
            plan = plan_map.get(pid)
            if not plan:
                continue

            plan_budget = 0.0
            plan_actual = 0.0
            children = []

            all_acc_ids = set(list(actual_data.get(pid, {}).keys()) + list(budget_data.get(pid, {}).keys()))

            for acc_id in sorted(all_acc_ids, key=lambda x: acc_map[x].name if x in acc_map else ''):
                acc = acc_map.get(acc_id)
                if not acc:
                    continue

                budget_amt = budget_data.get(pid, {}).get(acc_id, 0.0)
                actual_amt = actual_data.get(pid, {}).get(acc_id, 0.0)
                variance = budget_amt - actual_amt
                variance_pct = (variance / budget_amt * 100) if budget_amt else 0.0

                plan_budget += budget_amt
                plan_actual += actual_amt
                acc_code = getattr(acc, 'code', '') or ''

                children.append({
                    'id': f'bva_acc_{acc_id}',
                    'name': f'{acc_code} {acc.name}'.strip() if acc_code else acc.name,
                    'level': 2,
                    'columns': [
                        {'name': self._format_value(budget_amt), 'no_format': budget_amt, 'class': 'number'},
                        {'name': self._format_value(actual_amt), 'no_format': actual_amt, 'class': 'number'},
                        {'name': self._format_value(variance), 'no_format': variance, 'class': 'number'},
                        {'name': f'{variance_pct:.1f}%', 'no_format': variance_pct, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': f'bva_plan_{pid}',
                })

            if not children:
                continue

            plan_variance = plan_budget - plan_actual
            plan_pct = (plan_variance / plan_budget * 100) if plan_budget else 0.0

            lines.append({
                'id': f'bva_plan_{pid}',
                'name': plan.name,
                'level': 0,
                'columns': [
                    {'name': self._format_value(plan_budget), 'no_format': plan_budget, 'class': 'number'},
                    {'name': self._format_value(plan_actual), 'no_format': plan_actual, 'class': 'number'},
                    {'name': self._format_value(plan_variance), 'no_format': plan_variance, 'class': 'number'},
                    {'name': f'{plan_pct:.1f}%', 'no_format': plan_pct, 'class': 'number'},
                ],
                'unfoldable': True,
                'unfolded': options.get('unfold_all', False),
                'parent_id': None,
            })
            if options.get('unfold_all', False):
                lines.extend(children)

            grand_budget += plan_budget
            grand_actual += plan_actual

        grand_variance = grand_budget - grand_actual
        grand_pct = (grand_variance / grand_budget * 100) if grand_budget else 0.0

        lines.append({
            'id': 'bva_total',
            'name': _('TOTAL'),
            'level': 0,
            'columns': [
                {'name': self._format_value(grand_budget), 'no_format': grand_budget, 'class': 'number'},
                {'name': self._format_value(grand_actual), 'no_format': grand_actual, 'class': 'number'},
                {'name': self._format_value(grand_variance), 'no_format': grand_variance, 'class': 'number'},
                {'name': f'{grand_pct:.1f}%', 'no_format': grand_pct, 'class': 'number'},
            ],
            'unfoldable': False,
            'parent_id': None,
            'class': 'total',
        })
        return lines

    # ========================================================================
    # CUSTOM REPORT (using report lines)
    # ========================================================================

    def _get_custom_report_lines(self, options, date_from, date_to, comparison_periods):
        """Generate lines for custom defined reports."""
        lines = []
        for line in self.line_ids.sorted(key=lambda l: l.sequence):
            line_vals = line._compute_line_values(options, date_from, date_to, comparison_periods)
            lines.append(line_vals)
        return lines

    # ========================================================================
    # SHARED HELPERS
    # ========================================================================

    def _get_account_type_lines(self, domain, account_types, options, date_to,
                                 comparison_periods, parent_id=None, date_from=None):
        """Get report lines grouped by account for given account types."""
        lines = []
        type_domain = domain + [('account_id.account_type', 'in', account_types)]

        AccountMoveLine = self.env['account.move.line']
        results = AccountMoveLine.read_group(
            type_domain,
            ['account_id', 'debit', 'credit', 'balance'],
            ['account_id'],
        )

        total_values = [0.0] * (1 + len(comparison_periods))

        for result in sorted(results, key=lambda r: r['account_id'][1] if r['account_id'] else ''):
            if not result['account_id']:
                continue

            account_id = result['account_id'][0]
            account_name = result['account_id'][1]
            balance = result['balance']
            values = [balance]
            total_values[0] += balance

            # Comparison periods
            for idx, period in enumerate(comparison_periods):
                if date_from:
                    comp_domain = self._build_domain(options, period['date_from'], period['date_to'])
                else:
                    comp_domain = self._build_domain(options, date_to=period['date_to'])
                comp_domain += [('account_id', '=', account_id)]

                comp_result = AccountMoveLine.read_group(
                    comp_domain,
                    ['balance'],
                    [],
                )
                comp_balance = comp_result[0]['balance'] if comp_result else 0.0
                values.append(comp_balance)
                total_values[idx + 1] += comp_balance

            lines.append(self._format_detail_line(
                f'account_{account_id}', account_name,
                values, level=2, parent_id=parent_id, account_id=account_id
            ))

        return lines, total_values

    def _sum_account_types(self, domain, account_types):
        """Sum balances for given account types."""
        results = self.env['account.move.line'].read_group(
            domain + [('account_id.account_type', 'in', account_types)],
            ['balance'],
            [],
        )
        return results[0]['balance'] if results else 0.0

    # ========================================================================
    # LINE FORMATTING
    # ========================================================================

    def _format_title_line(self, line_id, name, level=0):
        """Create a title/header line."""
        return {
            'id': line_id,
            'name': name,
            'level': level,
            'class': 'o_account_report_title',
            'columns': [],
            'unfoldable': False,
            'parent_id': None,
            'is_title': True,
        }

    def _format_group_header(self, line_id, name, values, level=0):
        """Create a grey-band group header line (LIABILITIES, EQUITY)."""
        columns = []
        for v in values:
            columns.append({
                'name': self._format_value(v),
                'no_format': v,
                'class': 'number',
            })
        return {
            'id': line_id,
            'name': name,
            'level': level,
            'class': 'o_ent_group_header',
            'columns': columns,
            'unfoldable': False,
            'parent_id': None,
            'is_title': True,
        }

    def _format_section_header(self, line_id, name, values, level=1, unfoldable=True):
        """Create a bold sub-section header with total (Current Assets, Current Liabilities)."""
        columns = []
        for v in values:
            columns.append({
                'name': self._format_value(v),
                'no_format': v,
                'class': 'number',
            })
        return {
            'id': line_id,
            'name': name,
            'level': level,
            'class': 'o_ent_section_header',
            'columns': columns,
            'unfoldable': unfoldable,
            'unfolded': False,
            'parent_id': None,
        }

    def _format_detail_line(self, line_id, name, values, level=2, parent_id=None,
                             account_id=None, partner_id=None, unfoldable_flag=False):
        """Create a detail data line."""
        columns = []
        for v in values:
            columns.append({
                'name': self._format_value(v),
                'no_format': v,
                'class': 'number',
            })
        return {
            'id': line_id,
            'name': name,
            'level': level,
            'columns': columns,
            'unfoldable': bool(account_id) or unfoldable_flag,
            'unfolded': False,
            'account_id': account_id,
            'partner_id': partner_id,
            'parent_id': parent_id,
        }

    def _format_total_line(self, line_id, name, values, level=0, is_grand_total=False):
        """Create a total line."""
        columns = []
        for v in values:
            columns.append({
                'name': self._format_value(v),
                'no_format': v,
                'class': 'number',
            })
        return {
            'id': line_id,
            'name': name,
            'level': level,
            'class': 'total' + (' o_account_report_grand_total' if is_grand_total else ''),
            'columns': columns,
            'unfoldable': False,
            'parent_id': None,
            'is_total': True,
        }

    def _format_value(self, value, figure_type='float'):
        """Format a numeric value for display."""
        if value is None:
            value = 0.0
        currency = self.env.company.currency_id
        if float_is_zero(value, precision_digits=2):
            return '0.00'
        return f'{value:,.2f}'

    # ========================================================================
    # UNFOLD / DRILL-DOWN
    # ========================================================================

    def get_unfolded_lines(self, line_id, options):
        """Get child lines when a line is unfolded (expanded)."""
        self.ensure_one()
        date_from, date_to = self._get_dates(options)
        lines = []

        if line_id.startswith('account_'):
            account_id = int(line_id.replace('account_', ''))
            domain = self._build_domain(options, date_from, date_to)
            domain += [('account_id', '=', account_id)]

            # Get initial balance
            init_domain = self._build_domain(options, date_to=date_from - timedelta(days=1))
            init_domain += [('account_id', '=', account_id)]
            init_results = self.env['account.move.line'].read_group(
                init_domain, ['balance'], []
            )
            cumulative_balance = init_results[0]['balance'] if init_results else 0.0

            move_lines = self.env['account.move.line'].search(
                domain, order='date, id', limit=80
            )

            for ml in move_lines:
                cumulative_balance += ml.balance
                lines.append({
                    'id': f'move_line_{ml.id}',
                    'name': ml.move_id.name or '',
                    'level': 3,
                    'columns': self._get_move_line_columns(ml, cumulative_balance),
                    'unfoldable': False,
                    'parent_id': line_id,
                    'caret_options': 'account.move',
                    'move_id': ml.move_id.id,
                    'date': str(ml.date),
                    'partner_name': ml.partner_id.name or '',
                    'ref': ml.ref or '',
                })

        elif line_id.startswith('partner_'):
            partner_id = int(line_id.replace('partner_', ''))
            domain = self._build_domain(options, date_from, date_to)
            # Account type filter for unfold
            acct_type = options.get('account_type', 'all')
            if acct_type == 'receivable':
                rp_unfold = [('account_id.account_type', '=', 'asset_receivable')]
            elif acct_type == 'payable':
                rp_unfold = [('account_id.account_type', '=', 'liability_payable')]
            else:
                rp_unfold = [('account_id.account_type', 'in', ['asset_receivable', 'liability_payable'])]

            domain += [('partner_id', '=', partner_id)] + rp_unfold

            move_lines = self.env['account.move.line'].search(
                domain, order='date, move_id, id'
            )

            # Group by move_id to show one line per invoice/bill
            from collections import OrderedDict
            moves = OrderedDict()
            for ml in move_lines:
                mid = ml.move_id.id
                if mid not in moves:
                    moves[mid] = {
                        'move': ml.move_id,
                        'date': ml.date,
                        'name': ml.move_id.name or '',
                        'ref': ml.ref or ml.move_id.ref or '',
                        'debit': 0.0,
                        'credit': 0.0,
                    }
                moves[mid]['debit'] += ml.debit
                moves[mid]['credit'] += ml.credit

            # Initial balance for running total
            init_domain = self._build_domain(options, date_to=date_from - timedelta(days=1))
            init_domain += [('partner_id', '=', partner_id)] + rp_unfold
            init_results = self.env['account.move.line'].read_group(
                init_domain, ['balance'], []
            )
            cumulative = init_results[0]['balance'] if init_results else 0.0

            if not float_is_zero(cumulative, precision_digits=2):
                lines.append({
                    'id': f'partner_init_{partner_id}',
                    'name': _('Initial Balance'),
                    'level': 3,
                    'columns': [
                        {'name': '', 'class': ''},
                        {'name': '', 'class': ''},
                        {'name': '', 'class': ''},
                        {'name': self._format_value(cumulative), 'no_format': cumulative, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                    'class': 'o_account_reports_initial_balance',
                })

            for mid, mdata in moves.items():
                cumulative += mdata['debit'] - mdata['credit']
                ref_text = mdata['ref']
                if ref_text and mdata['name'] != ref_text:
                    display = '%s — %s' % (mdata['name'], ref_text)
                else:
                    display = mdata['name']

                lines.append({
                    'id': f'move_line_{mid}',
                    'name': display,
                    'level': 3,
                    'columns': [
                        {'name': str(mdata['date']), 'class': ''},
                        {'name': self._format_value(mdata['debit']), 'no_format': mdata['debit'], 'class': 'number'},
                        {'name': self._format_value(mdata['credit']), 'no_format': mdata['credit'], 'class': 'number'},
                        {'name': self._format_value(cumulative), 'no_format': cumulative, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                    'caret_options': 'account.move',
                    'move_id': mid,
                })
        elif line_id.startswith('bank_book_'):
            account_id = int(line_id.replace('bank_book_', ''))
            company_ids = options.get('company_ids', [self.env.company.id])
            domain = [
                ('account_id', '=', account_id),
                ('company_id', 'in', company_ids),
                ('parent_state', '=', 'posted'),
            ]
            init_domain = domain + [('date', '<', date_from)]
            if options.get('partner_ids'):
                init_domain.append(('partner_id', 'in', options['partner_ids']))
            init_results = self.env['account.move.line'].sudo().read_group(
                init_domain, ['debit', 'credit'], []
            )
            init_debit = init_results[0]['debit'] if init_results and init_results[0]['debit'] else 0.0
            init_credit = init_results[0]['credit'] if init_results and init_results[0]['credit'] else 0.0
            init_balance = init_debit - init_credit

            if not float_is_zero(init_balance, precision_digits=2):
                lines.append({
                    'id': f'bank_init_{account_id}',
                    'name': _('Initial Balance'),
                    'level': 3,
                    'columns': [
                        {'name': '', 'class': ''},
                        {'name': '', 'class': ''},
                        {'name': '', 'class': ''},
                        {'name': self._format_value(init_debit), 'no_format': init_debit, 'class': 'number'},
                        {'name': self._format_value(init_credit), 'no_format': init_credit, 'class': 'number'},
                        {'name': self._format_value(init_balance), 'no_format': init_balance, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                    'class': 'o_account_reports_initial_balance',
                })

            period_domain = domain + [('date', '>=', date_from), ('date', '<=', date_to)]
            if options.get('partner_ids'):
                period_domain.append(('partner_id', 'in', options['partner_ids']))
            if options.get('journal_ids'):
                period_domain.append(('journal_id', 'in', options['journal_ids']))
            move_lines = self.env['account.move.line'].sudo().search(period_domain, order='date, id')
            running = init_balance
            for ml in move_lines:
                running += ml.debit - ml.credit
                lines.append({
                    'id': f'bank_ml_{ml.id}',
                    'name': ml.move_id.name or '',
                    'level': 3,
                    'columns': [
                        {'name': str(ml.date), 'class': ''},
                        {'name': ml.ref or ml.name or '', 'class': ''},
                        {'name': ml.partner_id.name or '', 'class': ''},
                        {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                        {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                        {'name': self._format_value(running), 'no_format': running, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                    'caret_options': 'account.move',
                    'move_id': ml.move_id.id,
                })
        elif line_id.startswith('day_'):
            day_str = line_id.replace('day_', '')
            company_ids = options.get('company_ids', [self.env.company.id])
            domain = [
                ('parent_state', '=', 'posted'),
                ('date', '=', day_str),
                ('company_id', 'in', company_ids),
                ('display_type', 'not in', ('line_section', 'line_note')),
            ]
            if options.get('journal_ids'):
                domain.append(('journal_id', 'in', options['journal_ids']))
            if options.get('partner_ids'):
                domain.append(('partner_id', 'in', options['partner_ids']))
            if options.get('account_ids'):
                domain.append(('account_id', 'in', options['account_ids']))
            move_lines = self.env['account.move.line'].sudo().search(domain, order='move_id, id')
            for ml in move_lines:
                acc_name = f'{getattr(ml.account_id, "code", "") + " " if getattr(ml.account_id, "code", "") else ""}{ml.account_id.name}' if ml.account_id else ''
                lines.append({
                    'id': f'daybook_ml_{ml.id}',
                    'name': '',
                    'level': 3,
                    'columns': [
                        {'name': ml.move_id.name or '', 'class': ''},
                        {'name': acc_name, 'class': ''},
                        {'name': ml.partner_id.name or '', 'class': ''},
                        {'name': ml.name or ml.ref or '', 'class': ''},
                        {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                        {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                    'caret_options': 'account.move',
                    'move_id': ml.move_id.id,
                })
        elif line_id.startswith('bva_plan_'):
            plan_id = int(line_id.replace('bva_plan_', ''))
            company_ids = options.get('company_ids', [self.env.company.id])
            accounts = self.env['account.analytic.account'].sudo().search([('plan_id', '=', plan_id)])
            acc_map = {a.id: a for a in accounts}

            domain = [
                ('parent_state', '=', 'posted'),
                ('analytic_distribution', '!=', False),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', 'in', company_ids),
            ]
            if options.get('journal_ids'):
                domain.append(('journal_id', 'in', options['journal_ids']))
            if options.get('partner_ids'):
                domain.append(('partner_id', 'in', options['partner_ids']))

            move_lines_all = self.env['account.move.line'].sudo().search(domain)
            actual = {}
            for ml in move_lines_all:
                dist = ml.analytic_distribution or {}
                for acc_id_str, pct in dist.items():
                    try:
                        acc_id = int(acc_id_str)
                    except (ValueError, TypeError):
                        continue
                    if acc_id in acc_map:
                        factor = pct / 100.0
                        actual.setdefault(acc_id, 0.0)
                        actual[acc_id] += (ml.debit - ml.credit) * factor

            budget = {}
            if 'simple.budget.line' in self.env:
                try:
                    budget_lines = self.env['simple.budget.line'].sudo().search([
                        ('date_from', '<=', date_to),
                        ('date_to', '>=', date_from),
                        ('analytic_account_id', 'in', list(acc_map.keys())),
                        ('budget_id.state', 'in', ['confirmed', 'done']),
                    ])
                    for bl in budget_lines:
                        acc_id = bl.analytic_account_id.id
                        bl_days = (bl.date_to - bl.date_from).days + 1
                        period_start = max(bl.date_from, date_from)
                        period_end = min(bl.date_to, date_to)
                        overlap_days = (period_end - period_start).days + 1
                        if bl_days > 0 and overlap_days > 0:
                            budget.setdefault(acc_id, 0.0)
                            budget[acc_id] += bl.planned_amount * overlap_days / bl_days
                except Exception:
                    pass

            all_acc_ids = set(list(actual.keys()) + list(budget.keys()))
            for acc_id in sorted(all_acc_ids, key=lambda x: acc_map[x].name if x in acc_map else ''):
                acc = acc_map.get(acc_id)
                if not acc:
                    continue
                b = budget.get(acc_id, 0.0)
                a = actual.get(acc_id, 0.0)
                v = b - a
                vp = (v / b * 100) if b else 0.0
                lines.append({
                    'id': f'bva_acc_{acc_id}',
                    'name': f'{getattr(acc, "code", "") + " " if getattr(acc, "code", "") else ""}{acc.name}'.strip(),
                    'level': 2,
                    'columns': [
                        {'name': self._format_value(b), 'no_format': b, 'class': 'number'},
                        {'name': self._format_value(a), 'no_format': a, 'class': 'number'},
                        {'name': self._format_value(v), 'no_format': v, 'class': 'number'},
                        {'name': f'{vp:.1f}%', 'no_format': vp, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                })
        elif line_id.startswith('petty_cash_'):
            account_id = int(line_id.replace('petty_cash_', ''))
            company_ids = options.get('company_ids', [self.env.company.id])
            domain = [
                ('account_id', '=', account_id),
                ('company_id', 'in', company_ids),
                ('parent_state', '=', 'posted'),
            ]
            # Initial balance
            init_domain = domain + [('date', '<', date_from)]
            if options.get('partner_ids'):
                init_domain.append(('partner_id', 'in', options['partner_ids']))
            init_results = self.env['account.move.line'].sudo().read_group(
                init_domain, ['debit', 'credit'], []
            )
            init_debit = init_results[0]['debit'] if init_results and init_results[0]['debit'] else 0.0
            init_credit = init_results[0]['credit'] if init_results and init_results[0]['credit'] else 0.0
            init_balance = init_debit - init_credit

            lines.append({
                'id': f'petty_init_{account_id}',
                'name': _('Initial Balance'),
                'level': 2,
                'columns': [
                    {'name': '', 'class': ''},
                    {'name': _('Opening Balance'), 'class': ''},
                    {'name': '', 'class': ''},
                    {'name': self._format_value(init_debit), 'no_format': init_debit, 'class': 'number'},
                    {'name': self._format_value(init_credit), 'no_format': init_credit, 'class': 'number'},
                    {'name': self._format_value(init_balance), 'no_format': init_balance, 'class': 'number'},
                ],
                'unfoldable': False,
                'parent_id': line_id,
                'class': 'o_account_reports_initial_balance',
            })

            # Period entries — show ALL journals (no journal_ids filter)
            period_domain = domain + [('date', '>=', date_from), ('date', '<=', date_to)]
            if options.get('partner_ids'):
                period_domain.append(('partner_id', 'in', options['partner_ids']))
            move_lines = self.env['account.move.line'].sudo().search(period_domain, order='date, id')
            running = init_balance
            for ml in move_lines:
                running += ml.debit - ml.credit
                lines.append({
                    'id': f'petty_ml_{ml.id}',
                    'name': ml.move_id.name or '',
                    'level': 3,
                    'columns': [
                        {'name': str(ml.date), 'class': ''},
                        {'name': ml.ref or ml.name or '', 'class': ''},
                        {'name': ml.partner_id.name or '', 'class': ''},
                        {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                        {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                        {'name': self._format_value(running), 'no_format': running, 'class': 'number'},
                    ],
                    'unfoldable': False,
                    'parent_id': line_id,
                    'caret_options': 'account.move',
                    'move_id': ml.move_id.id,
                })
        elif line_id.startswith('analytic_acc_'):
            analytic_acc_id = int(line_id.replace('analytic_acc_', ''))
            acc_id_str = str(analytic_acc_id)
            domain = [
                ('parent_state', '=', 'posted'),
                ('analytic_distribution', '!=', False),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', 'in', options.get('company_ids', [self.env.company.id])),
            ]
            if options.get('journal_ids'):
                domain.append(('journal_id', 'in', options['journal_ids']))
            if options.get('partner_ids'):
                domain.append(('partner_id', 'in', options['partner_ids']))
            all_lines = self.env['account.move.line'].sudo().search(domain, order='date, id')
            for ml in all_lines:
                dist = ml.analytic_distribution or {}
                if acc_id_str not in dist:
                    continue
                pct = dist[acc_id_str]
                factor = pct / 100.0
                d = ml.debit * factor
                c = ml.credit * factor
                b = c - d
                cols = [
                    {'name': self._format_value(d), 'no_format': d, 'class': 'number'},
                    {'name': self._format_value(c), 'no_format': c, 'class': 'number'},
                    {'name': self._format_value(b), 'no_format': b, 'class': 'number'},
                ]
                lines.append({
                    'id': f'analytic_ml_{ml.id}_{analytic_acc_id}',
                    'name': ml.move_id.name or '',
                    'level': 4,
                    'columns': cols,
                    'unfoldable': False,
                    'parent_id': line_id,
                    'caret_options': 'account.move',
                    'move_id': ml.move_id.id,
                    'date': str(ml.date),
                    'partner_name': ml.partner_id.name or '',
                    'ref': ml.ref or ml.name or '',
                })

        elif line_id.startswith('bs_') or line_id.startswith('pl_'):
            # ── Balance Sheet & P&L unfold: show individual accounts ──
            company_ids = options.get('company_ids', [self.env.company.id])

            # Map line IDs to account types and sign
            type_map = {
                'bs_asset_cash': (['asset_cash'], 1),
                'bs_asset_receivable': (['asset_receivable'], 1),
                'bs_asset_current': (['asset_current'], 1),
                'bs_asset_prepayments': (['asset_prepayments'], 1),
                'bs_asset_fixed': (['asset_fixed'], 1),
                'bs_asset_noncurrent': (['asset_non_current'], 1),
                'bs_liability_current': (['liability_current'], -1),
                'bs_liability_payable': (['liability_payable'], -1),
                'bs_liability_credit_card': (['liability_credit_card'], -1),
                'bs_liab_noncurrent': (['liability_non_current'], -1),
                'bs_prev_years_unalloc': (['equity_unaffected'], -1),
                'bs_curr_year_pl': (['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost'], -1),
                'pl_revenue': (['income'], -1),
                'pl_cogs': (['expense_direct_cost'], 1),
                'pl_other_income': (['income_other'], -1),
            }

            # Accounts excluded from Operating Expenses (shown in Finance Costs / Zakat instead)
            opex_exclude_codes = ['400051', '400311', '400070', '400071', '400072']

            # Code-based unfold (for accounts matched by code prefix)
            code_map = {
                'bs_share_capital': (['301'], -1),
                'bs_reserve': (['302002'], -1),
                'bs_retained': (['302001'], -1),
                'pl_finance_cost': (['400051', '400311'], 1),
                'pl_zakat': (['400070', '400071', '400072'], 1),
            }

            if line_id in code_map:
                prefixes, sign = code_map[line_id]
                is_bs = line_id.startswith('bs_')

                code_domain = ['|'] * (len(prefixes) - 1) if len(prefixes) > 1 else []
                for prefix in prefixes:
                    code_domain.append(('account_id.code', '=like', prefix + '%'))

                if is_bs:
                    ml_domain = [
                        ('parent_state', '=', 'posted'),
                        ('date', '<=', date_to),
                        ('company_id', 'in', company_ids),
                    ] + code_domain
                else:
                    ml_domain = [
                        ('parent_state', '=', 'posted'),
                        ('date', '>=', date_from),
                        ('date', '<=', date_to),
                        ('company_id', 'in', company_ids),
                    ] + code_domain

                results = self.env['account.move.line'].sudo().read_group(
                    ml_domain, ['account_id', 'debit', 'credit'], ['account_id']
                )
                seen_ids = set()
                for r in sorted(results, key=lambda x: x['account_id'][1] if x.get('account_id') else ''):
                    if not r.get('account_id'):
                        continue
                    acc_id = r['account_id'][0]
                    if acc_id in seen_ids:
                        continue
                    seen_ids.add(acc_id)
                    acc_name = r['account_id'][1]
                    bal = ((r.get('debit') or 0) - (r.get('credit') or 0)) * sign
                    if float_is_zero(bal, precision_digits=2):
                        continue
                    lines.append({
                        'id': f'{line_id}_acc_{acc_id}',
                        'name': acc_name,
                        'level': 3,
                        'columns': [{'name': self._format_value(bal), 'no_format': bal, 'class': 'number'}],
                        'unfoldable': False,
                        'parent_id': line_id,
                    })

            elif line_id == 'pl_opex':
                # Operating Expenses unfold — exclude finance costs and zakat accounts
                ml_domain = [
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('company_id', 'in', company_ids),
                    ('account_id.account_type', 'in', ['expense', 'expense_depreciation']),
                ]

                results = self.env['account.move.line'].sudo().read_group(
                    ml_domain, ['account_id', 'debit', 'credit'], ['account_id']
                )
                # Get account codes for exclusion check
                result_acc_ids = [r['account_id'][0] for r in results if r.get('account_id')]
                if result_acc_ids:
                    acc_codes = {a['id']: a['code'] for a in self.env['account.account'].sudo().search_read(
                        [('id', 'in', result_acc_ids)], ['code']
                    )}
                else:
                    acc_codes = {}

                seen_ids = set()
                for r in sorted(results, key=lambda x: x['account_id'][1] if x.get('account_id') else ''):
                    if not r.get('account_id'):
                        continue
                    acc_id = r['account_id'][0]
                    # Skip finance cost and zakat accounts
                    acc_code = acc_codes.get(acc_id, '')
                    if any(acc_code.startswith(exc) for exc in opex_exclude_codes):
                        continue
                    if acc_id in seen_ids:
                        continue
                    seen_ids.add(acc_id)
                    acc_name = r['account_id'][1]
                    bal = (r.get('debit') or 0) - (r.get('credit') or 0)
                    if float_is_zero(bal, precision_digits=2):
                        continue
                    lines.append({
                        'id': f'{line_id}_acc_{acc_id}',
                        'name': acc_name,
                        'level': 3,
                        'columns': [{'name': self._format_value(bal), 'no_format': bal, 'class': 'number'}],
                        'unfoldable': False,
                        'parent_id': line_id,
                    })

            elif line_id in type_map:
                account_types, sign = type_map[line_id]
                is_bs = line_id.startswith('bs_')

                if is_bs:
                    ml_domain = [
                        ('parent_state', '=', 'posted'),
                        ('date', '<=', date_to),
                        ('company_id', 'in', company_ids),
                        ('account_id.account_type', 'in', account_types),
                    ]
                else:
                    ml_domain = [
                        ('parent_state', '=', 'posted'),
                        ('date', '>=', date_from),
                        ('date', '<=', date_to),
                        ('company_id', 'in', company_ids),
                        ('account_id.account_type', 'in', account_types),
                    ]

                results = self.env['account.move.line'].sudo().read_group(
                    ml_domain, ['account_id', 'debit', 'credit'], ['account_id']
                )
                seen_ids = set()
                for r in sorted(results, key=lambda x: x['account_id'][1] if x.get('account_id') else ''):
                    if not r.get('account_id'):
                        continue
                    acc_id = r['account_id'][0]
                    if acc_id in seen_ids:
                        continue
                    seen_ids.add(acc_id)
                    acc_name = r['account_id'][1]
                    bal = ((r.get('debit') or 0) - (r.get('credit') or 0)) * sign
                    if float_is_zero(bal, precision_digits=2):
                        continue
                    lines.append({
                        'id': f'{line_id}_acc_{acc_id}',
                        'name': acc_name,
                        'level': 3,
                        'columns': [{'name': self._format_value(bal), 'no_format': bal, 'class': 'number'}],
                        'unfoldable': False,
                        'parent_id': line_id,
                    })

        return lines

    def _get_move_line_columns(self, ml, cumulative_balance):
        """Get column values for a move line."""
        if self.report_type == 'trial_balance':
            return [
                {'name': '', 'class': 'number'},
                {'name': '', 'class': 'number'},
                {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                {'name': '', 'class': 'number'},
                {'name': '', 'class': 'number'},
            ]
        elif self.report_type == 'partner_ledger':
            return [
                {'name': '', 'class': 'number'},
                {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                {'name': self._format_value(cumulative_balance), 'no_format': cumulative_balance, 'class': 'number'},
            ]
        else:
            return [
                {'name': self._format_value(ml.debit), 'no_format': ml.debit, 'class': 'number'},
                {'name': self._format_value(ml.credit), 'no_format': ml.credit, 'class': 'number'},
                {'name': self._format_value(cumulative_balance), 'no_format': cumulative_balance, 'class': 'number'},
            ]

    # ========================================================================
    # EXCEL EXPORT
    # ========================================================================

    def get_xlsx(self, options):
        """Export report to Excel."""
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self.name[:31])

        # Styles
        title_style = workbook.add_format({
            'bold': True, 'font_size': 14, 'bottom': 2,
        })
        header_style = workbook.add_format({
            'bold': True, 'font_size': 10, 'bg_color': '#D5E8F0',
            'border': 1, 'text_wrap': True, 'align': 'center',
        })
        text_style = workbook.add_format({'font_size': 10})
        number_style = workbook.add_format({
            'font_size': 10, 'num_format': '#,##0.00',
        })
        total_style = workbook.add_format({
            'bold': True, 'font_size': 10, 'top': 1, 'bottom': 2,
        })
        total_number_style = workbook.add_format({
            'bold': True, 'font_size': 10, 'num_format': '#,##0.00',
            'top': 1, 'bottom': 2,
        })

        # Get report data
        data = self.get_report_data(options)

        # Title
        sheet.write(0, 0, self.name, title_style)
        sheet.write(1, 0, f"{data['date_from']} to {data['date_to']}", text_style)

        # Column headers
        row = 3
        sheet.write(row, 0, 'Name', header_style)
        sheet.set_column(0, 0, 40)
        for idx, col in enumerate(data.get('columns', [])):
            sheet.write(row, idx + 1, col['name'], header_style)
            sheet.set_column(idx + 1, idx + 1, 18)

        # Data rows
        row += 1
        for line in data.get('lines', []):
            indent = line.get('level', 0)
            is_total = line.get('is_total', False) or 'total' in line.get('class', '')

            style = total_style if is_total else text_style
            num_st = total_number_style if is_total else number_style

            name = ('  ' * indent) + (line.get('name', '') or '')
            sheet.write(row, 0, name, style)

            for idx, col in enumerate(line.get('columns', [])):
                value = col.get('no_format', 0)
                if isinstance(value, (int, float)):
                    sheet.write_number(row, idx + 1, value, num_st)
                else:
                    sheet.write(row, idx + 1, col.get('name', ''), style)
            row += 1

        workbook.close()
        output.seek(0)
        return output.read()

    # ========================================================================
    # PDF EXPORT
    # ========================================================================

    def get_pdf(self, options):
        """Export report to PDF using direct wkhtmltopdf."""
        self.ensure_one()
        report_data = self.get_report_data(options)
        html = self._build_pdf_html(report_data)

        # Convert HTML to PDF via wkhtmltopdf
        from odoo.tools.misc import find_in_path
        import subprocess
        import tempfile
        import os

        try:
            wkhtmltopdf = find_in_path('wkhtmltopdf')
        except IOError:
            raise UserError(_('wkhtmltopdf not found. Install it to export PDF.'))

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as fh:
            fh.write(html)
            html_path = fh.name

        pdf_path = html_path.replace('.html', '.pdf')
        try:
            cmd = [
                wkhtmltopdf, '--quiet',
                '--page-size', 'A4',
                '--margin-top', '20mm', '--margin-bottom', '20mm',
                '--margin-left', '15mm', '--margin-right', '15mm',
                '--encoding', 'UTF-8',
                html_path, pdf_path,
            ]
            subprocess.run(cmd, check=True, timeout=60)
            with open(pdf_path, 'rb') as fp:
                return fp.read()
        finally:
            for p in (html_path, pdf_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _build_pdf_html(self, report_data):
        """Build standalone HTML for PDF export."""
        company = self.env.company
        date_label = report_data.get('date_to', '')
        if report_data.get('date_from') and report_data.get('date_from') != report_data.get('date_to'):
            date_label = f"{report_data['date_from']} - {report_data['date_to']}"
        else:
            date_label = f"As of {report_data.get('date_to', '')}"

        # Build column headers
        col_headers = ''
        for col in report_data.get('columns', []):
            col_headers += f'<th class="num">{col.get("name", "")}</th>'
        num_data_cols = len(report_data.get('columns', []))

        # Build rows
        rows_html = ''
        for line in report_data.get('lines', []):
            level = line.get('level', 2)
            indent = level * 20 + 12
            cls = line.get('class', '') or ''

            row_class = ''
            if 'o_ent_group_header' in cls:
                row_class = 'grp'
            elif 'o_ent_section_header' in cls:
                row_class = 'sec'
            elif line.get('is_title'):
                row_class = 'ttl'
            elif 'o_account_report_grand_total' in cls:
                row_class = 'gt'
            elif line.get('is_total') or 'total' in cls:
                row_class = 'tot'

            name = line.get('name', '') or ''
            rows_html += f'<tr class="{row_class}"><td style="padding-left:{indent}px">{name}</td>'

            columns = line.get('columns', [])
            if columns:
                for col in columns:
                    val = col.get('no_format', 0) or 0
                    text = col.get('name', '0.00')
                    style = ''
                    if isinstance(val, (int, float)):
                        if val < 0:
                            style = 'color:#dc3545;'
                        elif val == 0:
                            style = 'color:#adb5bd;'
                    rows_html += f'<td class="num" style="{style}">{text}</td>'
            else:
                for _ in range(num_data_cols or 1):
                    rows_html += '<td class="num"></td>'
            rows_html += '</tr>\n'

        # Company info
        addr_parts = []
        if company.street:
            addr_parts.append(company.street)
        city_country = ', '.join(filter(None, [company.city, company.country_id.name if company.country_id else '']))
        if city_country:
            addr_parts.append(city_country)
        if company.vat:
            addr_parts.append(f'VAT: {company.vat}')
        company_info = '<br/>'.join(addr_parts)

        return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/>
<style>
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #212529; margin: 0; padding: 0 20px; }}
.hdr {{ display: flex; justify-content: space-between; align-items: flex-start; padding: 10px 0 15px; border-bottom: 2px solid #714B67; margin-bottom: 15px; }}
.co {{ font-size: 14px; font-weight: bold; }}
.ci {{ text-align: right; font-size: 10px; color: #666; line-height: 1.5; }}
h1 {{ text-align: center; font-size: 18px; margin: 15px 0 4px; }}
.dt {{ text-align: center; color: #888; font-size: 10px; margin-bottom: 15px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #f8f9fa; padding: 7px 12px; font-size: 9px; font-weight: 600; text-transform: uppercase; border-bottom: 2px solid #dee2e6; }}
th.num {{ text-align: right; }}
td {{ padding: 5px 12px; border-bottom: 1px solid #eee; font-size: 10px; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.ph th {{ background: #fff; border-bottom: none; text-align: center; font-size: 10px; padding: 6px 12px; }}
tr.grp td {{ background: #e0e0e0; font-weight: 800; text-transform: uppercase; font-size: 11px; padding: 7px 12px; }}
tr.sec td {{ font-weight: 700; font-size: 11px; }}
tr.ttl td {{ background: #f0f2f5; font-weight: 700; border-top: 2px solid #dee2e6; padding: 8px 12px; }}
tr.tot td {{ font-weight: 700; border-top: 1px solid #adb5bd; background: #f8f9fa; }}
tr.gt td {{ font-weight: 800; font-size: 11px; border-top: 2px solid #714B67; border-bottom: 2px solid #714B67; background: #e8e4e7; }}
.ft {{ text-align: center; margin-top: 25px; font-size: 8px; color: #aaa; }}
</style></head>
<body>
<div class="hdr"><div class="co">{company.name or ''}</div><div class="ci">{company_info}</div></div>
<h1>{report_data.get('report_name', self.name)}</h1>
<div class="dt">{date_label}</div>
<table>
<thead>
<tr class="ph"><th></th><th class="num" colspan="{num_data_cols or 1}">{date_label}</th></tr>
<tr><th style="min-width:200px"></th>{col_headers}</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
<div class="ft">Generated on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</body></html>'''

