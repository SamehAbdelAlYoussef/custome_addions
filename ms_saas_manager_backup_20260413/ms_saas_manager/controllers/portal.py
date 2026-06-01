# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class MsPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'subscription_count' in counters:
            values['subscription_count'] = request.env['ms.subscription'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', 'not in', ('draft',)),
            ])
        return values

    @http.route('/my/subscription', type='http', auth='user', website=True)
    def portal_subscriptions(self, **kw):
        partner = request.env.user.partner_id
        subs = request.env['ms.subscription'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', 'not in', ('draft',)),
        ], order='date_start desc')
        return request.render('ms_saas_manager.portal_my_subscriptions', {
            'subscriptions': subs,
            'payment_success': kw.get('payment') == 'success',
            'payment_failed':  kw.get('payment') == 'failed',
        })

    @http.route('/my/subscription/<string:ref>', type='http', auth='user', website=True)
    def portal_subscription_detail(self, ref, **kw):
        partner = request.env.user.partner_id
        sub = request.env['ms.subscription'].sudo().search([
            ('name', '=', ref), ('partner_id', '=', partner.id)
        ], limit=1)
        if not sub:
            return request.redirect('/my/subscription')
        invoices = request.env['ms.invoice'].sudo().search([
            ('subscription_id', '=', sub.id)
        ], order='date_invoice desc')
        return request.render('ms_saas_manager.portal_subscription_detail', {
            'subscription': sub,
            'invoices': invoices,
            'payment_success': kw.get('payment') == 'success',
            'payment_failed':  kw.get('payment') == 'failed',
        })

    @http.route('/my/subscription/<string:ref>/pay/<int:invoice_id>',
                type='http', auth='user', website=True)
    def pay_invoice(self, ref, invoice_id, **kw):
        partner = request.env.user.partner_id
        inv = request.env['ms.invoice'].sudo().search([
            ('id', '=', invoice_id),
            ('subscription_id.partner_id', '=', partner.id),
            ('state', 'in', ('draft', 'sent', 'overdue')),
        ], limit=1)
        if not inv:
            return request.redirect(f'/my/subscription/{ref}')
        try:
            url = request.env['ms.paymob'].sudo().create_payment_link(inv)
            inv.write({'paymob_payment_url': url, 'state': 'sent'})
            return request.redirect(url)
        except Exception as e:
            return request.redirect(f'/my/subscription/{ref}?error=1')
