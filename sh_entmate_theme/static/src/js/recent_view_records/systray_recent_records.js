/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { Dropdown } from '@web/core/dropdown/dropdown';
import { user } from "@web/core/user";


export class RecentRecordsSystray extends Component {
    static template = "sh_entmate_theme.RecentRecordsSystray";


    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.sh_enable_recent_record_view = session.sh_enable_recent_record_view;

        this.state = useState({
            activeTab: 'records',
            searchQuery: '',
            show_dropdown: false,
        });
        this.records = [];
        this.bookmarks = []
        this.total_record_count = [];

        this.handleDocumentClick = this.handleDocumentClick.bind(this);
        this.switchTab = this.switchTab.bind(this);
        this.markAsBookmark = this.markAsBookmark.bind(this);
        this.removeRecord = this.removeRecord.bind(this);
        this.searchRecords = this.searchRecords.bind(this);
        useBus(this.env.bus, 'close_recent_record', (ev) => this.closeRecentRecord());

    }

    closeRecentRecord(){
        this.state.show_dropdown = false;
    }

    handleDocumentClick() {
        this.state.show_dropdown = !this.state.show_dropdown;
    }

    switchTab(tabName) {
        this.state.activeTab = tabName;
    }

    async toggleDropdown() {
        this.state.show_dropdown = !this.state.show_dropdown;

        if (this.state.show_dropdown) {
            await this.get_records();
            this.render(true);
        }

        // Close Other Pop-up
        this.env.bus.trigger('close_quick_create', {});
        this.env.bus.trigger('close_quick_menu', {});
        this.env.bus.trigger('close_calculator', {});
        this.env.bus.trigger('close_todo_list', {});
        this.env.bus.trigger('close_bookmark', {});

    }

    async get_records(query = '') {
        // const userId = session.uid;
        const recordFields = ['sh_user_id', 'sh_model', 'sh_record_id', 'name', 'sh_action_name', 'sh_module_name'];
        const order = { order: 'id desc' };
        const domain = [["sh_is_bookmark", "=", false], ["sh_user_id", "=", user.userId]];

        if (query) {
            domain.push(['name', 'ilike', query]);
        }

        const [records, bookmarks] = await Promise.all([
            this.orm.searchRead('sh.recent.records', domain, recordFields, order),
            this.orm.searchRead('sh.recent.records', [["sh_is_bookmark", "=", true], ["sh_user_id", "=", user.userId]], recordFields, order)
        ]);

        var total_record_count = await this.orm.searchRead('sh.recent.records', [["sh_is_bookmark", "=", false], ["sh_user_id", "=", user.userId]], recordFields, order);

        this.total_record_count = total_record_count
        this.records = records;
        this.bookmarks = bookmarks;
    }

    async searchRecords() {
        await this.get_records(this.state.searchQuery);
        this.render(true);
    }

    openRecord(record) {
        this.do_action(record)
    }

    openBookmark(record) {
        this.do_action(record)
    }

    do_action(record) {
        var action = {
            type: 'ir.actions.act_window',
            res_model: record.sh_model,
            res_id: record.sh_record_id,
            views: [[false, 'form']],
            name: record.sh_action_name,
            target: 'current',
        };

        if (record.sh_module_name) {
            action['context'] = { 'module': record.sh_module_name }
        }
        this.actionService.doAction(action);
        this.render(true)
    }

    async markAsBookmark(record) {
        await this.orm.write("sh.recent.records", [record.id], { sh_is_bookmark: true });
        await this.get_records()

        this.render(true)
    }

    async removeRecord(record) {
        await this.orm.unlink("sh.recent.records", [record.id]);
        await this.get_records()
        this.render(true)
    }

    async clearRecords(records) {
        await this.orm.unlink("sh.recent.records", records.map((rec) => rec.id));
        await this.get_records()
        this.render(true)
    }
}

registry.category("systray").add("sh_entmate_theme.RecentRecordsSystray", { Component: RecentRecordsSystray }, { sequence: 25 });