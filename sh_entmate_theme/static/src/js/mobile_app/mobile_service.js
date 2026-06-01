/** @odoo-module **/

import { registry } from "@web/core/registry";
import { sh_backmate_theme_mobile_switch_user_PreferencesItem } from "./user_menu/switch_user";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { cookie } from "@web/core/browser/cookie";


const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

const sh_backmate_theme_mobile_service = {
    start() {
        if (cookie.get("sh_backmate_theme_mobile_login_web_view")) {
            userMenuRegistry.remove("log_out");
            userMenuRegistry.add("sh_backmate_theme_mobile_switch_user", sh_backmate_theme_mobile_switch_user_PreferencesItem, { force: true });
        }
    },
};
serviceRegistry.add("sh_backmate_theme_mobile_service", sh_backmate_theme_mobile_service);
