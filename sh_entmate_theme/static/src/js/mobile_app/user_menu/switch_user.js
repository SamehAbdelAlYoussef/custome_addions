/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

export function sh_backmate_theme_mobile_switch_user_PreferencesItem(env) {
    const switch_user_url = "/sh_backmate_theme_mobile/session/logout";
    return {
        type: "item",
        id: "sh_backmate_theme_mobile_switch_user",
        description: env._t("Log out"),
        href: switch_user_url,
        callback: () => {
            browser.open(switch_user_url, "_self");
        },
        sequence: 10000,
    };
}
