# -*- coding: utf-8 -*-
import re
import logging
import secrets
import subprocess
import requests as py_requests
from odoo import http, _
from odoo.http import request
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)

CF_TURNSTILE_SITEKEY = '0x4AAAAAAC8mGbakPPbuXAKi'
CF_TURNSTILE_SECRET  = '0x4AAAAAAC8mGU6Ik5NhOQDjJXFw15470ng'


class MsWebsiteHome(Website):
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

        if not subdomain:
            errors['subdomain'] = 'Subdomain is required'
        elif not re.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
            errors['subdomain'] = 'Subdomain: 3-32 chars, lowercase, numbers, hyphens only.'
        elif subdomain in ('www','app','mail','admin','api','test','demo','ms','ftp','smtp','pop','imap'):
            errors['subdomain'] = 'This subdomain is reserved.'
        else:
            existing = ManagedDb.search([('subdomain', '=', subdomain)], limit=1)
            if existing:
                errors['subdomain'] = 'This subdomain is already taken.'

        # ── Cloudflare Turnstile verification ──
        turnstile_token = post.get('cf-turnstile-response', '')
        if not turnstile_token:
            errors['turnstile'] = 'Please complete the human verification.'
        elif not errors:
            try:
                cf_resp = py_requests.post(
                    'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                    data={'secret': CF_TURNSTILE_SECRET, 'response': turnstile_token},
                    timeout=10)
                if not cf_resp.json().get('success'):
                    errors['turnstile'] = 'Verification failed. Please try again.'
            except Exception:
                errors['turnstile'] = 'Verification unavailable. Please try again.'

        plan = Plan.search([('code', '=', plan_code)], limit=1)
        if not plan:
            errors['plan'] = 'Invalid plan selected'

        if errors:
            return request.render('ms_saas_manager.page_signup', {
                'plan': plan, 'billing': billing, 'errors': errors, 'post': post,
                'turnstile_sitekey': CF_TURNSTILE_SITEKEY,
            })

        # ── Remove any previous unverified signup for same email ──
        old_drafts = Sub.search([
            ('email', '=', email), ('email_verified', '=', False), ('state', '=', 'draft')])
        if old_drafts:
            old_drafts.unlink()

        # ── Create or find partner ──
        partner = Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': name, 'email': email, 'phone': phone,
                'company_name': company, 'customer_rank': 1,
            })

        # ── Generate verification token ──
        verify_token = secrets.token_urlsafe(32)

        # ── Create subscription in draft (NOT active yet) ──
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

            mail = request.env['mail.mail'].sudo().create({
                'subject': 'Verify your email - Manager Solutions',
                'email_from': request.env.company.email or 'noreply@msolutions-eg.com',
                'email_to': email,
                'body_html': """
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:#1A6B3A;padding:30px;text-align:center;">
    <h1 style="color:#fff;margin:0;">Manager Solutions</h1>
    <p style="color:#a3d9b1;margin:5px 0 0;">Cloud Accounting Platform</p>
  </div>
  <div style="padding:30px;background:#fff;">
    <h2 style="color:#333;">Verify Your Email Address</h2>
    <p>Hi <strong>%s</strong>,</p>
    <p>Thank you for signing up for the <strong>%s</strong> plan.
       Click the button below to verify your email and start your 7-day free trial.</p>
    <div style="text-align:center;margin:30px 0;">
      <a href="%s"
         style="background:#1A6B3A;color:#fff;padding:16px 36px;
                border-radius:8px;text-decoration:none;font-size:16px;
                font-weight:bold;display:inline-block;">
        Verify My Email
      </a>
    </div>
    <p style="color:#888;font-size:13px;">
      Or copy this link: <a href="%s" style="color:#1A6B3A;">%s</a>
    </p>
    <p style="color:#888;font-size:13px;">
      This link expires in 24 hours. If you did not sign up, ignore this email.
    </p>
  </div>
  <div style="background:#f2f3f4;padding:20px;text-align:center;color:#888;font-size:12px;">
    Manager Solutions &middot; <a href="https://msolutions-eg.com">msolutions-eg.com</a>
  </div>
</div>""" % (name, plan.name, verify_url, verify_url, verify_url),
            })
            mail.send()
        except Exception as e:
            _logger.error('Verification email failed for %s: %s', email, e)

        return request.render('ms_saas_manager.page_verify_email', {
            'email': email, 'name': name,
        })

    @http.route('/signup/verify/<string:token>', type='http', auth='public', website=True)
    def verify_email(self, token, **kw):
        Sub = request.env['ms.subscription'].sudo()
        sub = Sub.search([
            ('verify_token', '=', token),
            ('email_verified', '=', False),
            ('state', '=', 'draft'),
        ], limit=1)

        if not sub:
            return request.render('ms_saas_manager.page_verify_expired', {})

        # Mark verified
        sub.write({'email_verified': True, 'verify_token': False})

        # Start trial (fully automatic)
        sub.action_start_trial()

        # Provision database in background subprocess
        db_name = request.env.registry.db_name
        sub_id = sub.id
        script = '/opt/odoo/custom_addons/ms_saas_manager/scripts/bg_provision.py'
        log_file = open('/var/log/odoo/provision.log', 'a')
        try:
            subprocess.Popen(
                ['/opt/odoo/venv/bin/python3', script, db_name, str(sub_id)],
                stdout=log_file, stderr=subprocess.STDOUT, close_fds=True
            )
            _logger.info('Background provisioning started for sub %s', sub_id)
        except Exception as e:
            _logger.error('Failed to start provisioning process: %s', e)

        return request.redirect('/signup/thankyou/%s' % sub.name)

    @http.route('/signup/resend-verify', type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def resend_verification(self, **post):
        email = post.get('email', '').strip()
        Sub = request.env['ms.subscription'].sudo()
        sub = Sub.search([
            ('email', '=', email), ('email_verified', '=', False), ('state', '=', 'draft'),
        ], limit=1)

        if sub and sub.verify_token:
            try:
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                verify_url = '%s/signup/verify/%s' % (base_url, sub.verify_token)
                mail = request.env['mail.mail'].sudo().create({
                    'subject': 'Verify your email - Manager Solutions',
                    'email_from': request.env.company.email or 'noreply@msolutions-eg.com',
                    'email_to': email,
                    'body_html': """
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:#1A6B3A;padding:30px;text-align:center;">
    <h1 style="color:#fff;margin:0;">Manager Solutions</h1>
  </div>
  <div style="padding:30px;background:#fff;">
    <h2>Verify Your Email</h2>
    <p>Hi <strong>%s</strong>, click below to verify:</p>
    <div style="text-align:center;margin:30px 0;">
      <a href="%s" style="background:#1A6B3A;color:#fff;padding:16px 36px;
         border-radius:8px;text-decoration:none;font-size:16px;font-weight:bold;
         display:inline-block;">Verify My Email</a>
    </div>
  </div>
</div>""" % (sub.partner_id.name, verify_url),
                })
                mail.send()
            except Exception as e:
                _logger.error('Resend verify failed: %s', e)

        return request.render('ms_saas_manager.page_verify_email', {
            'email': email, 'name': sub.partner_id.name if sub else '',
            'resent': True,
        })

    @http.route('/signup/thankyou/<path:ref>', type='http', auth='public', website=True)
    def thank_you(self, ref, **kw):
        sub = request.env['ms.subscription'].sudo().search([('name', '=', ref)], limit=1)
        return request.render('ms_saas_manager.page_thank_you', {'subscription': sub})

    @http.route('/signup/check-subdomain', type='http', auth='public', website=True, csrf=False)
    def check_subdomain(self, subdomain='', **kw):
        import json as jsonlib
        subdomain = subdomain.strip().lower()
        reserved = ('www','app','mail','admin','api','test','demo','ms','ftp','smtp','pop','imap')

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
        token = secrets.token_urlsafe(32)
        db.sudo().write({'login_token': token})
        target = 'https://%s.msolutions-eg.com/ms/autologin?token=%s' % (subdomain, token)
        return request.redirect(target)

    @http.route('/ms/autologin', type='http', auth='none', csrf=False)
    def token_autologin(self, token='', **kw):
        if not token:
            return request.redirect('/web/login')
        host = request.httprequest.host
        subdomain = host.split('.')[0] if '.' in host else ''
        try:
            import psycopg2
            conn = psycopg2.connect(dbname='ms_app', user='odoo',
                                     host='localhost', password='MsDb@2025!')
            cur = conn.cursor()
            cur.execute("SELECT name, admin_email, admin_password, login_token "
                        "FROM ms_managed_db WHERE subdomain = %s", [subdomain])
            row = cur.fetchone()
            cur.close(); conn.close()
            if not row or row[3] != token:
                return request.redirect('/web/login')
            db_name, admin_email, admin_password, _ = row
            conn2 = psycopg2.connect(dbname='ms_app', user='odoo',
                                      host='localhost', password='MsDb@2025!')
            cur2 = conn2.cursor()
            cur2.execute("UPDATE ms_managed_db SET login_token = NULL WHERE subdomain = %s",
                         [subdomain])
            conn2.commit(); cur2.close(); conn2.close()
            uid = request.session.authenticate(db_name, admin_email, admin_password)
            if uid:
                return request.redirect('/web')
        except Exception as e:
            _logger.error('Token autologin error: %s', e)
        return request.redirect('/web/login')
