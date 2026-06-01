# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MsPaymobWebhook(http.Controller):

    @http.route('/paymob/callback', type='http', auth='public', methods=['POST'], csrf=False)
    def callback(self, **post):
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))
            paymob = request.env['ms.paymob'].sudo()

            if not paymob.verify_hmac(data):
                _logger.warning('Paymob HMAC failed')
                return request.make_response('HMAC_FAILED', status=403)

            obj     = data.get('obj', {})
            success = obj.get('success', False)
            order_id = str(obj.get('order', {}).get('id', ''))
            txn_id   = str(obj.get('id', ''))

            if not success:
                return request.make_response('NOT_SUCCESS', status=200)

            invoice = request.env['ms.invoice'].sudo().search(
                [('paymob_order_id', '=', order_id)], limit=1)
            if not invoice:
                merchant_id = obj.get('order', {}).get('merchant_order_id', '')
                invoice = request.env['ms.invoice'].sudo().search(
                    [('name', '=', merchant_id)], limit=1)

            if invoice:
                invoice.paymob_transaction_id = txn_id
                invoice.action_mark_paid()
                _logger.info('Invoice %s paid via Paymob', invoice.name)

            return request.make_response('OK', status=200)
        except Exception as e:
            _logger.error('Paymob webhook error: %s', e)
            return request.make_response('ERROR', status=500)

    @http.route('/paymob/return', type='http', auth='public', website=True)
    def paymob_return(self, **kw):
        success  = kw.get('success', 'false').lower() == 'true'
        order_id = kw.get('order', '')
        if success and order_id:
            inv = request.env['ms.invoice'].sudo().search(
                [('paymob_order_id', '=', order_id)], limit=1)
            if inv and inv.subscription_id:
                return request.redirect(
                    f'/my/subscription/{inv.subscription_id.name}?payment=success')
        return request.redirect('/my/subscription?payment=failed')
