/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { onMounted } from "@odoo/owl";
import { usePager } from "@web/search/pager_hook";
import { user } from "@web/core/user";

patch(FormController.prototype, {

    async setup() {

        const orm = useService("orm");
        onMounted(async () => {
            if (session.sh_enable_recent_record_view && this.props.resId) {
                const record = this.model.root;
                const model = this.props.resModel;
                const record_id = this.props.resId;
                const record_name = JSON.parse(sessionStorage.current_action).name + ' / ' + (model === 'res.config.settings' ? 'settings' : (record.data.display_name || record.data.name));
                const action_name = JSON.parse(sessionStorage.current_action).name
                const module_name = this.props.context.module;
                await orm.call("sh.recent.records", "create_or_update", [
                    user.userId,
                    model,
                    record_id,
                    record_name,
                    action_name,
                    module_name,
                ])
            }

        });

        usePager(async () => {
            if (!this.model.root.isNew) {
                const resIds = this.model.root.resIds;
                if (session.sh_enable_recent_record_view  && this.model.root) {
                    var record = this.model.root;
                    var model = this.props.resModel;
                    var record_name = JSON.parse(sessionStorage.current_action).name + ' / ' + (record.data.display_name || record.data.name);
                    var action_name = JSON.parse(sessionStorage.current_action).name
                    const module_name = this.props.context.module
                    var index_of_current_record = resIds.indexOf(this.model.root.resId)
                    var record_id = resIds[index_of_current_record]
                    await orm.call("sh.recent.records", "create_or_update", [
                        user.user_id,
                        model,
                        record_id,
                        record_name,
                        action_name,
                        module_name,
                    ])
                }

                return {
                    offset: resIds.indexOf(this.model.root.resId),
                    limit: 1,
                    total: resIds.length,
                    onUpdate: ({ offset }) => this.onPagerUpdate({ offset, resIds }),
                };
            }
        });
        super.setup();
    },
});
