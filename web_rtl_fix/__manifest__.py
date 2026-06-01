{
    "name": "Web RTL Fix (Odoo 18)",
    "version": "18.0.1.0.0",
    "category": "Web",
    "summary": "Fix RTL layout issues caused by themes",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_rtl_fix/static/src/scss/rtl_fix.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
