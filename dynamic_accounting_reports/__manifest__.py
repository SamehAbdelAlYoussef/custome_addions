{
    'name': 'Dynamic Accounting Reports',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Dynamic Financial Reports - Balance Sheet, P&L, Trial Balance, General Ledger, Aged Reports, Partner Ledger, Cash Flow',
    'description': """
        Dynamic Accounting Reports for Odoo 18 Community
        =================================================
        This module provides enterprise-like dynamic accounting reports:
        - Balance Sheet
        - Profit and Loss
        - Trial Balance
        - General Ledger
        - Aged Receivable
        - Aged Payable
        - Partner Ledger
        - Cash Flow Statement

        Features:
        - Dynamic filtering (date, journals, accounts, partners, analytic)
        - Comparison periods (previous period, previous year, custom)
        - Expandable/collapsible report lines
        - Drill-down to journal entries
        - Export to PDF and Excel
        - Multi-company support
    """,
    'author': 'Custom',
    'website': '',
    'depends': [
        'account',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/activate_accounting_features.xml',
        'views/account_report_views.xml',
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/trial_balance.xml',
        'data/general_ledger.xml',
        'data/aged_receivable.xml',
        'data/aged_payable.xml',
        'data/partner_ledger.xml',
        'data/cash_flow_statement.xml',
        'data/tax_report.xml',
        'views/menu_views.xml',
        'views/simple_budget_views.xml',
        'data/analytic_account.xml',
        'data/analytic_plan.xml',
        'data/petty_cash.xml',
        'data/bank_book.xml',
        'data/day_book.xml',
        'data/budget_vs_actual.xml',
        'report/report_financial.xml',
        'report/report_journal_entry.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dynamic_accounting_reports/static/src/css/account_report.css',
            'dynamic_accounting_reports/static/src/js/account_report_widget.js',
            'dynamic_accounting_reports/static/src/xml/account_report_template.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': '_post_init_hook',
}

