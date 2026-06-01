/* @odoo-module */

import { Component, onWillStart, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { useState } from "@odoo/owl";



export class NightMode extends Component {
    static template = "sh_entmate_theme.NightMode";

    setup() {
        this.orm = useService("orm");
        this.state = useState({ show_theme_mode: false, is_night_mode: false })
        this.onWillStart();
    }

    async onWillStart() {
        if (session.sh_enable_night_mode && localStorage.getItem("is_night_mode") == 't') {
            this.state.is_night_mode = true;
            document.querySelector('.o_web_client').classList.add('sh_night_mode');            
            }
            else{
                this.state.is_night_mode = false;
                document.querySelector('.o_web_client').classList.remove('sh_night_mode');                
            }

        const data = await this.orm.searchRead(
            "res.users",
            [['id', '=', user.userId]],
            ["sh_enable_night_mode"]
        );
        if (data[0].sh_enable_night_mode) {
            this.state.show_theme_mode = true
        }

    }

    _click_moon_button() {
        localStorage.setItem("is_night_mode", "t");
        document.querySelector('.o_web_client').classList.add('sh_night_mode');
        this.state.is_night_mode = true
    }

    _click_sun_button() {
        localStorage.setItem("is_night_mode", "f");
        this.state.is_night_mode = false;
        document.querySelector('.o_web_client').classList.remove('sh_night_mode');
    }

}

registry.category("systray").add("sh_entmate_theme.NightMode", { Component: NightMode }, { sequence: 100 });