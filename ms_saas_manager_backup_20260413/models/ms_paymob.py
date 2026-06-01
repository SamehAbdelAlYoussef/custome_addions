# -*- coding: utf-8 -*-
import requests
import hashlib
import hmac
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MsPaymob(models.AbstractModel):
    _name = 'ms.paymob'
    _description = 'Paymob Gateway'

    def _cfg(self):
        P = self.env['ir.config_parameter'].sudo()
        return {
            'api_key':        P.get_param('ms_saas.paymob_api_key', ''),
            'integration_id': P.get_param('ms_saas.paymob_integration_id', ''),
            'iframe_id':      P.get_param('ms_saas.paymob_iframe_id', ''),
            'hmac_secret':    P.get_param('ms_saas.paymob_hmac_secret', ''),
            'base':           'https://accept.paymob.com/api',
        }

    def _auth_token(self, cfg):
        r = requests.post(f"{cfg['base']}/auth/tokens",
                          json={'api_key': cfg['api_key']}, timeout=30)
        r.raise_for_status()
        return r.json()['token']

    def _create_order(self, token, invoice, cfg):
        cents = int(invoice.amount * 100)
        r = requests.post(f"{cfg['base']}/ecommerce/orders", json={
            'auth_token': token,
            'delivery_needed': False,
            'amount_cents': cents,
            'currency': 'EGP',
            'merchant_order_id': invoice.name,
            'items': [{'name': f'{invoice.template_id.name}',
                       'amount_cents': cents, 'quantity': 1}],
        }, timeout=30)
        r.raise_for_status()
        return r.json()['id']

    def _payment_key(self, token, order_id, invoice, cfg):
        p = invoice.partner_id
        r = requests.post(f"{cfg['base']}/acceptance/payment_keys", json={
            'auth_token': token,
            'amount_cents': int(invoice.amount * 100),
            'expiration': 3600,
            'order_id': order_id,
            'currency': 'EGP',
            'integration_id': int(cfg['integration_id']),
            'billing_data': {
                'first_name': (p.name or 'Customer').split()[0],
                'last_name':  (p.name or 'Name').split()[-1],
                'email':      p.email or 'N/A',
                'phone_number': p.phone or 'N/A',
                'apartment': 'N/A', 'floor': 'N/A', 'street': 'N/A',
                'building': 'N/A', 'shipping_method': 'NA',
                'postal_code': 'N/A', 'city': p.city or 'Cairo',
                'country': 'EG', 'state': 'N/A',
            },
        }, timeout=30)
        r.raise_for_status()
        return r.json()['token']

    def create_payment_link(self, invoice):
        try:
            cfg = self._cfg()
            if not cfg['api_key']:
                raise UserError(_('Paymob API Key not set. Go to Settings → Technical → System Parameters → ms_saas.paymob_api_key'))
            token    = self._auth_token(cfg)
            order_id = self._create_order(token, invoice, cfg)
            pkey     = self._payment_key(token, order_id, invoice, cfg)
            invoice.paymob_order_id = str(order_id)
            url = f"https://accept.paymob.com/api/acceptance/iframes/{cfg['iframe_id']}?payment_token={pkey}"
            _logger.info('Paymob link for %s: %s', invoice.name, url)
            return url
        except Exception as e:
            _logger.error('Paymob error: %s', e)
            raise UserError(_('Paymob Error: %s') % e)

    def verify_hmac(self, data):
        cfg = self._cfg()
        secret = cfg['hmac_secret']
        if not secret:
            return True
        obj = data.get('obj', {})
        fields_order = [
            'amount_cents', 'created_at', 'currency', 'error_occured',
            'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure',
            'is_auth', 'is_capture', 'is_refunded', 'is_standalone_payment',
            'is_voided', 'order.id', 'owner', 'pending',
            'source_data.pan', 'source_data.sub_type', 'source_data.type', 'success',
        ]
        def get_val(key):
            parts = key.split('.')
            v = obj
            for p in parts:
                v = v.get(p, '') if isinstance(v, dict) else ''
            return str(v)
        concat = ''.join(get_val(f) for f in fields_order)
        computed = hmac.new(secret.encode(), concat.encode(), hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, data.get('hmac', ''))
