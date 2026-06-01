/** @odoo-module **/


import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";


patch(ListController.prototype, {

    setup(...args) {
        super.setup(...args)
        this.orm = useService("orm");
        this.show_expand_collapse = false;
        this.search_enable_expand_collapse();

    },

    async search_enable_expand_collapse() {
        const data = await this.orm.searchRead(
            "res.users",
            [['id', '=', user.userId]],
            ["sh_enable_expand_collapse"]
        );
        
        if (data) {
            this.show_expand_collapse = data[0].sh_enable_expand_collapse
        }
    },

    _onClickRefreshView (ev) {
        this.actionService.switchView('list');
    },

    shExpandGroups () {
        document.querySelectorAll('.o_group_header').forEach(function(header) {
        if (!header.classList.contains('o_group_open')) {
            const groupName = header.querySelector('.o_group_name');
            if (groupName) {
                groupName.click();
            }
            }
        });
    },

    shCollapseGroups () {
        document.querySelectorAll('.o_group_header').forEach(function(header) {
        if (header.classList.contains('o_group_open')) {
            const groupName = header.querySelector('.o_group_name');
            if (groupName) {
                groupName.click();
            }
        }
        });
    },

});