#!/usr/bin/env python3
"""Install missing modules on a customer database."""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
_logger = logging.getLogger('sync_modules')

def main(master_db, sub_id):
    sys.path.insert(0, '/opt/odoo/server')
    import odoo
    odoo.tools.config.parse_config(['--config=/etc/odoo/odoo.conf', '-d', master_db, '--stop-after-init'])
    from odoo.modules.registry import Registry
    from odoo import api, SUPERUSER_ID
    import subprocess

    # Get plan modules and customer db name from master
    _logger.info('Reading subscription %s from %s', sub_id, master_db)
    registry = Registry(master_db)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        sub = env['ms.subscription'].browse(int(sub_id))
        if not sub.exists() or not sub.db_id:
            _logger.error('Subscription or DB not found')
            return
        plan_modules = sub.template_id.get_module_names()
        db_name = sub.db_id.name
        _logger.info('Plan modules: %s', plan_modules)
        _logger.info('Customer DB: %s', db_name)

    # Get installed modules from customer DB
    import psycopg2
    conn = psycopg2.connect(dbname=db_name, user='odoo', host='localhost', password='MsDb@2025!')
    cur = conn.cursor()
    cur.execute("SELECT name FROM ir_module_module WHERE state = 'installed'")
    installed = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()

    # Find missing modules
    missing = [m for m in plan_modules if m not in installed]
    _logger.info('Installed: %s', len(installed))
    _logger.info('Missing: %s', missing)

    if not missing:
        _logger.info('All modules already installed. Nothing to do.')
        # Update master record
        registry2 = Registry(master_db)
        with registry2.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            sub = env['ms.subscription'].browse(int(sub_id))
            sub.message_post(body='Module sync: all modules already installed.')
            cr.commit()
        return

    # Install missing modules
    modules_str = ','.join(missing)
    _logger.info('Installing: %s', modules_str)
    cmd = (
        f'/opt/odoo/venv/bin/python3 /opt/odoo/server/odoo-bin '
        f'-c /etc/odoo/odoo.conf -d {db_name} '
        f'--init={modules_str} --without-demo=all '
        f'--stop-after-init --no-http'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)

    if result.returncode == 0:
        _logger.info('Modules installed successfully on %s', db_name)
        status = 'success'
        msg = 'Module sync completed. Installed: ' + modules_str
    else:
        error = result.stderr[-500:] if result.stderr else 'Unknown error'
        _logger.error('Install failed: %s', error)
        status = 'error'
        msg = 'Module sync failed: ' + error[:200]

    # Rename Invoicing → Accounting + hide Apps
    try:
        conn = psycopg2.connect(dbname=db_name, user='odoo', host='localhost', password='MsDb@2025!')
        cur = conn.cursor()
        cur.execute("UPDATE ir_ui_menu SET name = jsonb_set(name, '{en_US}', '\"Accounting\"') WHERE name::text LIKE '%%Invoicing%%' AND parent_id IS NULL")
        cur.execute("UPDATE ir_module_module SET shortdesc = jsonb_set(shortdesc, '{en_US}', '\"Accounting\"') WHERE name = 'account'")
        cur.execute("DELETE FROM ir_ui_menu WHERE name::text LIKE '%%Apps%%' AND parent_id IS NULL")
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

    # Update master record
    registry3 = Registry(master_db)
    with registry3.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        sub = env['ms.subscription'].browse(int(sub_id))
        sub.message_post(body=msg)
        cr.commit()

    _logger.info('Sync complete for %s: %s', db_name, status)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: sync_modules.py <master_db> <subscription_id>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
