#!/usr/bin/env python3
"""Background provisioning script - runs as a separate process."""
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
_logger = logging.getLogger('bg_provision')

def main(db_name, sub_id):
    sys.path.insert(0, '/opt/odoo/server')
    import odoo
    odoo.tools.config.parse_config(['--config=/etc/odoo/odoo.conf', '-d', db_name, '--stop-after-init'])
    from odoo.modules.registry import Registry
    from odoo import api, SUPERUSER_ID

    _logger.info('Starting provisioning for subscription %s in db %s', sub_id, db_name)
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        sub = env['ms.subscription'].browse(int(sub_id))
        if not sub.exists():
            _logger.error('Subscription %s not found', sub_id)
            return
        _logger.info('Provisioning DB for %s (subdomain: %s)', sub.name, sub.subdomain)
        sub.action_provision_and_notify()
        cr.commit()
        _logger.info('Provisioning complete for %s - DB: %s', sub.name, sub.db_name)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: bg_provision.py <master_db_name> <subscription_id>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
