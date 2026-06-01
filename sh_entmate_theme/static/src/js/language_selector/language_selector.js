/* @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { user } from "@web/core/user";

export class LanguageTemplate extends Component {
       static components = { Dropdown };
       static template = "sh_entmate_theme.LanguageTemplate";

       setup() {
            this.actionService = useService("action");
            this.orm = useService("orm");
            this.languages_list = useState([]);
            this.state = useState({enable_languages : true})
            this.onWillStart()
            this.fetch_sh_get_installed_lang()
        }

       async onWillStart() {
            const data = await this.orm.searchRead(
            "res.users",
            [['id', '=', user.userId]],
            ["sh_enable_language_selection"]
            );

            if (data) {
                if (! data[0].sh_enable_language_selection) {
                    this.state.enable_languages = false;
                    }
            }
       }

       async fetch_sh_get_installed_lang() {
            var self = this;
            rpc("/web/dataset/call_kw/res.lang/sh_get_installed_lang", {
                    model: 'res.lang',
                    method: 'sh_get_installed_lang',
                    args: [],
                    kwargs: {},
                }).then(function (languages) {
                    self.languages_list = languages
                    self.selected_lang = user.lang
                    });
       }

       onBeforeOpen() {
            // Close Other Pop-up
            this.env.bus.trigger('close_calculator', {});
            this.env.bus.trigger('close_quick_menu', {});
            this.env.bus.trigger('close_recent_record', {});
            this.env.bus.trigger('close_todo_list', {});
            this.env.bus.trigger('close_quick_create', {});
            this.env.bus.trigger('close_bookmark', {});

            this.fetch_sh_get_installed_lang();
        }

       change_sh_user_lang(e){
        
        var self = this;
        var lang = e[0]
        var self = this;

        this.orm.write("res.users", [parseInt(user.userId)], { 'lang': lang }).then(function () {
        self.actionService.doAction({
                    name: 'Reload Context',
                    type: 'ir.actions.client',
                    tag: 'reload_context',
                });
        });
        }
}

registry.category("systray").add("sh_entmate_theme.LanguageTemplate", { Component: LanguageTemplate });