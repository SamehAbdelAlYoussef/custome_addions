import json
import base64
import logging
from datetime import datetime

from odoo import http
from odoo.http import request, content_disposition

_logger = logging.getLogger(__name__)


class DynamicAccountReportController(http.Controller):

    @http.route('/dynamic_reports/get_report_data', type='json', auth='user')
    def get_report_data(self, report_id, options=None):
        """Get report data for rendering."""
        report = request.env['dynamic.account.report'].browse(int(report_id))
        if not report.exists():
            return {'error': 'Report not found'}
        options = options or {}
        options['company_ids'] = options.get('company_ids', [request.env.company.id])
        return report.get_report_data(options)

    @http.route('/dynamic_reports/get_unfolded_lines', type='json', auth='user')
    def get_unfolded_lines(self, report_id, line_id, options=None):
        """Get unfolded (expanded) lines for a specific line."""
        report = request.env['dynamic.account.report'].browse(int(report_id))
        if not report.exists():
            return {'error': 'Report not found'}
        options = options or {}
        options['company_ids'] = options.get('company_ids', [request.env.company.id])
        return report.get_unfolded_lines(line_id, options)

    @http.route('/dynamic_reports/export_xlsx', type='http', auth='user')
    def export_xlsx(self, report_id, options=None, **kw):
        """Export report as Excel file."""
        report = request.env['dynamic.account.report'].browse(int(report_id))
        if not report.exists():
            return request.not_found()

        try:
            options = json.loads(options) if options else {}
        except (json.JSONDecodeError, TypeError):
            options = {}

        options['company_ids'] = options.get('company_ids', [request.env.company.id])
        xlsx_data = report.get_xlsx(options)

        filename = f'{report.name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        return request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

    @http.route('/dynamic_reports/export_pdf', type='http', auth='user')
    def export_pdf(self, report_id, options=None, **kw):
        """Export report as PDF."""
        report = request.env['dynamic.account.report'].browse(int(report_id))
        if not report.exists():
            return request.not_found()

        try:
            options = json.loads(options) if options else {}
        except (json.JSONDecodeError, TypeError):
            options = {}

        options['company_ids'] = options.get('company_ids', [request.env.company.id])
        try:
            pdf_data = report.get_pdf(options)
            filename = f'{report.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', content_disposition(filename)),
                ]
            )
        except Exception as e:
            _logger.error('PDF export error: %s', str(e))
            return request.not_found()

    @http.route('/dynamic_reports/get_filter_data', type='json', auth='user')
    def get_filter_data(self, report_id, filter_type, company_ids=None):
        """Get available filter options (journals, accounts, partners, etc.)."""
        result = []
        # Use selected companies or fall back to current company
        cids = company_ids or [request.env.company.id]

        if filter_type == 'journals':
            journals = request.env['account.journal'].search([
                ('company_id', 'in', cids),
            ])
            result = [{'id': j.id, 'name': j.name, 'code': j.code, 'type': j.type} for j in journals]

        elif filter_type == 'accounts':
            accounts = request.env['account.account'].search([], order='code')
            result = [{'id': a.id, 'name': f'{a.code} {a.name}', 'code': a.code} for a in accounts]

        elif filter_type == 'partners':
            # Get all partners that have posted journal entries
            request.env.cr.execute("""
                SELECT DISTINCT aml.partner_id
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.partner_id IS NOT NULL
                  AND am.state = 'posted'
                  AND aml.company_id IN %s
            """, [tuple(cids)])
            partner_ids = [r[0] for r in request.env.cr.fetchall()]
            partners = request.env['res.partner'].browse(partner_ids).sorted('name')
            result = [{'id': p.id, 'name': p.name} for p in partners]

        elif filter_type == 'analytic_accounts':
            try:
                analytics = request.env['account.analytic.account'].search(
                    [],
                    order='name'
                )
                result = [{'id': a.id, 'name': f"[{a.plan_id.name}] {a.name}" if a.plan_id else a.name} for a in analytics]
            except Exception:
                result = []

        elif filter_type == 'analytic_plans':
            try:
                plans = request.env['account.analytic.plan'].search(
                    [],
                    order='name'
                )
                result = [{'id': p.id, 'name': p.name} for p in plans]
            except Exception:
                result = []

        elif filter_type == 'companies':
            # Return all companies accessible to the user
            companies = request.env['res.company'].search([])
            result = [{'id': c.id, 'name': c.name} for c in companies]

        return result

