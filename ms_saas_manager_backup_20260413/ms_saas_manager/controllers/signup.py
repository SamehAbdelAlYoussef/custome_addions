# -*- coding: utf-8 -*-
import re
import logging
import threading
import secrets
import requests as py_requests
from odoo import http, _
from odoo.http import request
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)

# ── Cloudflare Turnstile keys ──
CF_TURNSTILE_SITEKEY = '0x4AAAAAAC8mGbakPPbuXAKi'
CF_TURNSTILE_SECRET  = '0x4AAAAAAC8mGU6Ik5NhOQDjJXFw15470ng'


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
            'turnstile_sitekey': CF_TURNSTILE_SITEKEY,
        })

    @http.route('/signup/submit', type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def signup_submit(self, **post):
        Plan      = request.env['ms.plan.template'].sudo()
        Partner   = request.env['res.partner'].sudo()
        Sub       = request.env['ms.subscription'].sudo()
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

        # ── Validate subdomain ──
        if not subdomain:
            errors['subdomain'] = 'Subdomain is required'
        elif not re.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
            errors['subdomain'] = 'Subdomain must be 3-32 characters: lowercase letters, numbers, hyphens.'
        elif subdomain in ('www', 'app', 'mail', 'admin', 'api', 'test', 'demo', 'ms', 'ftp', 'smtp', 'pop', 'imap'):
            errors['subdomain'] = 'This subdomain is reserved. Please choose another.'
        else:
            existing = ManagedDb.search([('subdomain', '=', subdomain)], limit=1)
            if existing:
                errors['subdomain'] = 'This subdomain is already taken.'

        # ── Validate Cloudflare Turnstile ──
        turnstile_token = post.get('cf-turnstile-response', '')
        if not turnstile_token:
            errors['turnstile'] = 'Please complete the human verification.'
        elif not errors:
            try:
                cf_resp = py_requests.post(
                    'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                    data={'secret': CF_TURNSTILE_SECRET, 'response': turnstile_token},
                    timeout=10,
                )
                cf_result = cf_resp.json()
                if not cf_result.get('success'):
                    errors['turnstile'] = 'Human verification failed. Please try again.'
            except Exception:
                errors['turnstile'] = 'Verification service unavailable. Please try again.'

        plan = Plan.search([('code', '=', plan_code)], limit=1)
        if not plan:
            errors['plan'] = 'Invalid plan selected'

        if errors:
            return request.render('ms_saas_manager.page_signup', {
                'plan': plan, 'billing': billing, 'errors': errors, 'post': post,
                'turnstile_sitekey': CF_TURNSTILE_SITEKEY,
            })

        # ── Check for existing unverified signup with same email ──
        existing_sub = Sub.search([
            ('email', '=', email),
            ('email_verified', '=', False),
            ('state', '=', 'draft'),
        ], limit=1)
        if existing_sub:
            existing_sub.unlink()

        # ── Create or find partner ──
        partner = Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': name, 'email': email, 'phone': phone,
                'company_name': company, 'customer_rank': 1,
            })

        # ── Generate verification token ──
        verify_token = secrets.token_urlsafe(32)

        # ── Create subscription in draft (NOT trial yet) ──
        sub = Sub.create({
            'partner_id':    partner.id,
            'template_id':   plan.id,
            'billing_cycle': billing,
            'company_name':  company,
            'subdomain':     subdomain,
            'verify_token':  verify_token,
            'email_verified': False,
        })

        # ── Send verification email ──
        try:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            verify_url = '%s/signup/verify/%s' % (base_url, verify_token)

            mail_values = {
                'subject': 'Verify your email — Manager Solutions',
                'email_from': request.env.company.email or 'noreply@msolutions-eg.com',
                'email_to': email,
                'body_html': '''
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:#1A6B3A;padding:30px;text-align:center;">
    <h1 style="color:#fff;margin:0;">Manager Solutions</h1>
    <p style="color:#a3d9b1;margin:5px 0;">Cloud Accounting Platform</p>
  </div>
  <div style="padding:30px;background:#fff;">
    <h2 style="color:#333;">Verify Your Email Address</h2>
    <p>Hi <strong>%s</strong>,</p>
    <p>Thank you for signing up for the <strong>%s</strong> plan!
       Please verify your email to activate your 7-day free trial.</p>
    <div style="text-align:center;margin:30px 0;">
      <a href="%s"
         style="background:#1A6B3A;color:#fff;padding:16px 36px;
                border-radius:8px;text-decoration:none;font-size:16px;
                font-weight:bold;display:inline-block;">
        ✅ Verify My Email
      </a>
    </div>
    <p style="color:#888;font-size:13px;">
      If the button doesn't work, copy and paste this link:<br/>
      <a href="%s" style="color:#1A6B3A;">%s</a>
    </p>
    <p style="color:#888;font-size:13px;">
      This link expires in 24 hours. If you didn't sign up, please ignore this email.
    </p>
  </div>
  <div style="background:#f2f3f4;padding:20px;text-align:center;color:#888;font-size:12px;">
    Manager Solutions · <a href="https://msolutions-eg.com">msolutions-eg.com</a>
  </div>
</div>''' % (name, plan.name, verify_url, verify_url, verify_url),
            }
            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        except Exception as e:
            _logger.error('Verification email failed for %s: %s', email, e)

        # ── Show "Check your email" page ──
        return request.render('ms_saas_manager.page_verify_email', {
            'email': email,
            'name': name,
        })

    @http.route('/signup/verify/<string:token>', type='http', auth='public', website=True)
    def verify_email(self, token, **kw):
        """User clicks verification link → start trial + provision DB."""
        Sub = request.env['ms.subscription'].sudo()
        sub = Sub.search([
            ('verify_token', '=', token),
            ('email_verified', '=', False),
            ('state', '=', 'draft'),
        ], limit=1)

        if not sub:
            return request.render('ms_saas_manager.page_verify_expired', {})

        # ── Mark as verified ──
        sub.write({
            'email_verified': True,
            'verify_token': False,
        })

        # ── Start trial ──
        sub.action_start_trial()

        # ── Provision database in background thread ──
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
        subdomain = subdomain.strip().lower()
        reserved = ('www', 'app', 'mail', 'admin', 'api', 'test', 'demo', 'ms', 'ftp', 'smtp', 'pop', 'imap')

        if len(subdomain) < 3:
            return request.make_response(
                jsonlib.dumps({'available': False, 'reason': 'Minimum 3 characters'}),
                headers=[('Content-Type', 'application/json')])

        if not re.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
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
        if not request.env.user.has_group('base.group_system'):
            return request.redirect('/web')
        db = request.env['ms.managed.db'].sudo().search([('subdomain', '=', subdomain)], limit=1)
        if not db or not db.admin_email or not db.admin_password:
            return request.redirect('/web')
        domain = 'msolutions-eg.com'
        token = secrets.token_urlsafe(32)
        db.sudo().write({'login_token': token})
        target = 'https://%s.%s/ms/autologin?token=%s' % (subdomain, domain, token)
        return request.redirect(target)

    @http.route('/ms/autologin', type='http', auth='none', csrf=False)
    def token_autologin(self, token='', **kw):
        if not token:
            return request.redirect('/web/login')
        host = request.httprequest.host
        subdomain = host.split('.')[0] if '.' in host else ''
        try:
            import psycopg2
            conn = psycopg2.connect(dbname='ms_master', user='odoo', host='localhost', password='MsDb@2025!')
            cur = conn.cursor()
            cur.execute(
                "SELECT name, admin_email, admin_password, login_token FROM ms_managed_db WHERE subdomain = %s",
                [subdomain])
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row or row[3] != token:
                return request.redirect('/web/login')
            db_name, admin_email, admin_password, _ = row
            conn2 = psycopg2.connect(dbname='ms_master', user='odoo', host='localhost', password='MsDb@2025!')
            cur2 = conn2.cursor()
            cur2.execute("UPDATE ms_managed_db SET login_token = NULL WHERE subdomain = %s", [subdomain])
            conn2.commit()
            cur2.close()
            conn2.close()
            uid = request.session.authenticate(db_name, admin_email, admin_password)
            if uid:
                return request.redirect('/web')
        except Exception as e:
            _logger.error('Token autologin error: %s', e)
        return request.redirect('/web/login')
