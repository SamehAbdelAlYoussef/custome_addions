# -*- coding: utf-8 -*-
import re
import logging
import threading
import requests as py_requests
from odoo import http, _
from odoo.http import request
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)


class MsWebsiteHome(Website):
    """Override the website homepage to show our landing page."""
    @http.route('/', type='http', auth='public', website=True)
    def index(self, **kw):
        return request.render('ms_saas_manager.page_home', {})


class MsSignupController(http.Controller):

    @http.route('/home', type='http', auth='public', website=True)
    def home_page(self, **kw):
        return request.render('ms_saas_manager.page_home', {})

    @http.route('/pricing', type='http', auth='public', website=True)
    def pricing_page(self, **kw):
        plans = request.env['ms.plan.template'].sudo().search(
            [('active', '=', True)], order='sequence')
        return request.render('ms_saas_manager.page_pricing', {'plans': plans})

    @http.route('/signup/<string:plan_code>', type='http', auth='public', website=True)
    def signup_page(self, plan_code, billing='monthly', **kw):
        plan = request.env['ms.plan.template'].sudo().search(
            [('code', '=', plan_code), ('active', '=', True)], limit=1)
        if not plan:
            return request.redirect('/pricing')
        return request.render('ms_saas_manager.page_signup', {
            'plan': plan, 'billing': billing,
        })

    @http.route('/signup/submit', type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def signup_submit(self, **post):
        Plan    = request.env['ms.plan.template'].sudo()
        Partner = request.env['res.partner'].sudo()
        Sub     = request.env['ms.subscription'].sudo()
        ManagedDb = request.env['ms.managed.db'].sudo()

        plan_code = post.get('plan_code', '')
        billing   = post.get('billing', 'monthly')
        name      = post.get('name', '').strip()
        email     = post.get('email', '').strip()
        phone     = post.get('phone', '').strip()
        company   = post.get('company', '').strip()
        subdomain = post.get('subdomain', '').strip().lower()

        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        if not email or '@' not in email:
            errors['email'] = 'Valid email is required'
        if not phone:
            errors['phone'] = 'Phone is required'
        if not company:
            errors['company'] = 'Company name is required'

        # Validate subdomain
        if not subdomain:
            errors['subdomain'] = 'Subdomain is required'
        elif not re.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
            errors['subdomain'] = 'Subdomain must be 3-32 characters: lowercase letters, numbers, hyphens. Cannot start/end with hyphen.'
        elif subdomain in ('www', 'app', 'mail', 'admin', 'api', 'test', 'demo', 'ms', 'ftp', 'smtp', 'pop', 'imap'):
            errors['subdomain'] = 'This subdomain is reserved. Please choose another.'
        else:
            # Check if subdomain already taken
            existing = ManagedDb.search([('subdomain', '=', subdomain)], limit=1)
            if existing:
                errors['subdomain'] = 'This subdomain is already taken. Please choose another.'

        plan = Plan.search([('code', '=', plan_code)], limit=1)
        if not plan:
            errors['plan'] = 'Invalid plan selected'

        if errors:
            return request.render('ms_saas_manager.page_signup', {
                'plan': plan, 'billing': billing, 'errors': errors, 'post': post,
            })

        # Create or find partner
        partner = Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': name, 'email': email, 'phone': phone,
                'company_name': company, 'customer_rank': 1,
            })

        # Create subscription with subdomain
        sub = Sub.create({
            'partner_id':    partner.id,
            'template_id':   plan.id,
            'billing_cycle': billing,
            'company_name':  company,
            'subdomain':     subdomain,
        })

        # Start trial (sets state, notifies admin)
        sub.action_start_trial()

        # Provision database in background thread
        db_name = request.env.registry.db_name
        sub_id = sub.id
        def _bg_provision():
            import odoo
            with odoo.api.Environment.manage():
                with odoo.registry(db_name).cursor() as cr:
                    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                    bg_sub = env['ms.subscription'].browse(sub_id)
                    bg_sub.action_provision_and_notify()

        t = threading.Thread(target=_bg_provision, daemon=True)
        t.start()

        return request.redirect('/signup/thankyou/%s' % sub.name)

    @http.route('/signup/thankyou/<path:ref>', type='http', auth='public', website=True)
    def thank_you(self, ref, **kw):
        sub = request.env['ms.subscription'].sudo().search([('name', '=', ref)], limit=1)
        return request.render('ms_saas_manager.page_thank_you', {'subscription': sub})

    @http.route('/signup/check-subdomain', type='http', auth='public', website=True, csrf=False)
    def check_subdomain(self, subdomain='', **kw):
        import json as jsonlib
        import re as re2
        subdomain = subdomain.strip().lower()
        reserved = ('www', 'app', 'mail', 'admin', 'api', 'test', 'demo', 'ms', 'ftp', 'smtp', 'pop', 'imap')

        if len(subdomain) < 3:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Minimum 3 characters'}),
                headers=[('Content-Type', 'application/json')])

        if not re2.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Invalid format'}),
                headers=[('Content-Type', 'application/json')])

        if subdomain in reserved:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Reserved name'}),
                headers=[('Content-Type', 'application/json')])

        existing = request.env['ms.managed.db'].sudo().search([('subdomain', '=', subdomain)], limit=1)
        if existing:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Already taken'}),
                headers=[('Content-Type', 'application/json')])

        return request.make_response(
            jsonlib.dumps({'available': True}),
            headers=[('Content-Type', 'application/json')])

    @http.route('/signup/check-subdomain', type='http', auth='public', website=True, csrf=False)
    def check_subdomain(self, subdomain='', **kw):
        import json as jsonlib
        import re as re2
        subdomain = subdomain.strip().lower()
        reserved = ('www', 'app', 'mail', 'admin', 'api', 'test', 'demo', 'ms', 'ftp', 'smtp', 'pop', 'imap')

        if len(subdomain) < 3:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Minimum 3 characters'}),
                headers=[('Content-Type', 'application/json')])

        if not re2.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Invalid format'}),
                headers=[('Content-Type', 'application/json')])

        if subdomain in reserved:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Reserved name'}),
                headers=[('Content-Type', 'application/json')])

        existing = request.env['ms.managed.db'].sudo().search([('subdomain', '=', subdomain)], limit=1)
        if existing:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Already taken'}),
                headers=[('Content-Type', 'application/json')])

        return request.make_response(
            jsonlib.dumps({'available': True}),
            headers=[('Content-Type', 'application/json')])

    @http.route('/admin/autologin/<string:subdomain>', type='http', auth='user', website=False)
    def admin_autologin(self, subdomain, **kw):
        """Generate one-time token and redirect to customer subdomain for login."""
        if not request.env.user.has_group('base.group_system'):
            return request.redirect('/web')

        db = request.env['ms.managed.db'].sudo().search([('subdomain', '=', subdomain)], limit=1)
        if not db or not db.admin_email or not db.admin_password:
            return request.redirect('/web')

        domain = 'msolutions-eg.com'

        # Store token temporarily in the DB record
        import secrets
        token = secrets.token_urlsafe(32)
        db.sudo().write({'login_token': token})

        # Redirect to customer subdomain with token
        target = 'https://%s.%s/ms/autologin?token=%s' % (subdomain, domain, token)
        return request.redirect(target)

    @http.route('/ms/autologin', type='http', auth='none', csrf=False)
    def token_autologin(self, token='', **kw):
        """Runs on customer subdomain - validates token and creates session."""
        if not token:
            return request.redirect('/web/login')

        # Determine which DB we are on from the host
        host = request.httprequest.host
        subdomain = host.split('.')[0] if '.' in host else ''

        # Find the DB record in master
        try:
            import psycopg2
            conn = psycopg2.connect(dbname='ms_master', user='odoo', host='localhost', password='MsDb@2025!')
            cur = conn.cursor()
            cur.execute(
                "SELECT name, admin_email, admin_password, login_token FROM ms_managed_db WHERE subdomain = %s",
                [subdomain]
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row or row[3] != token:
                return request.redirect('/web/login')

            db_name, admin_email, admin_password, _ = row

            # Clear the token (one-time use)
            conn2 = psycopg2.connect(dbname='ms_master', user='odoo', host='localhost', password='MsDb@2025!')
            cur2 = conn2.cursor()
            cur2.execute("UPDATE ms_managed_db SET login_token = NULL WHERE subdomain = %s", [subdomain])
            conn2.commit()
            cur2.close()
            conn2.close()

            # Authenticate on this DB
            uid = request.session.authenticate(db_name, admin_email, admin_password)
            if uid:
                return request.redirect('/web')

        except Exception as e:
            _logger.error('Token autologin error: %s', e)

        return request.redirect('/web/login')
