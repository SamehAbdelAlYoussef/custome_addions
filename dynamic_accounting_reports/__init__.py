from . import models
from . import controllers
from . import wizard


def _post_init_hook(env):
    """
    Activate full accounting features for Community Edition on install.

    In CE, several groups are hidden and must be manually enabled via
    developer mode. This hook automatically activates them for all
    internal users so the full Reporting menu and accounting features
    are available immediately after installing this module.
    """
    internal_users = env['res.users'].search([
        ('share', '=', False),
        ('active', '=', True),
    ])
    if not internal_users:
        return

    user_ids = [(4, u.id) for u in internal_users]

    # 1. Show Full Accounting Features
    # XML ID: account.group_account_readonly
    # This is the main gate - enables Accounting menu, Reporting, etc.
    _activate_group(env, 'account.group_account_readonly', user_ids)

    # 2. Accounting User (full access)
    _activate_group(env, 'account.group_account_user', user_ids)

    # 3. Show Inalterability Features
    # This group is under "Extra Rights" and may have different XML IDs
    inalterability_activated = _activate_group(
        env, 'account.group_account_inalterability', user_ids
    )
    if not inalterability_activated:
        # Fallback: search by name
        group = env['res.groups'].search([
            ('name', 'ilike', 'Inalterability'),
        ], limit=1)
        if group:
            group.write({'users': user_ids})

    # 4. Invoice group (implied by readonly, but just in case)
    _activate_group(env, 'account.group_account_invoice', user_ids)


def _activate_group(env, xml_id, user_ids):
    """Safely activate a group by XML ID. Returns True if successful."""
    try:
        group = env.ref(xml_id, raise_if_not_found=False)
        if group:
            group.write({'users': user_ids})
            return True
    except Exception:
        pass
    return False

