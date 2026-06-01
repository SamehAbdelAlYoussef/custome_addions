/** @odoo-module **/
import { ShDocumentViewer } from "@sh_entmate_theme/js/attachment_in_listview/sh_document_viewer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { registry } from "@web/core/registry";
import { session } from '@web/session';
import { FileViewer } from "@web/core/file_viewer/file_viewer";
import { AttachmentList } from "@mail/core/common/attachment_list";
const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";
import { onMounted, useState, useChildSubEnv, whenReady } from "@odoo/owl";

patch(ListRenderer.prototype, {

    setup() {
        super.setup();
        var self = this
        this.fileViewer = useFileViewer();
        self.showattachment = session.show_attachment_in_list_view
        var rec_ids = []
        this.notificationService = useService("notification");
        var records = this.props.list.records
        var model = this.props.list.resModel
        records.map(record => rec_ids.push(record.resId))
        rpc("/get/attachment/data", {
            model: model,
            rec_ids: rec_ids,
        }).then(function (data) {
            if (data) {
                self.sh_attachment_data = data;
            }
        });

        onMounted(() => {
            const reloadViewButton = document.querySelector('.o_action_manager > .o_view_controller.o_list_view > .o_control_panel .reload_view');
            if (reloadViewButton) {
                reloadViewButton.click();
            }
        });
    },

    close: function(){
        registry.category("main_components").remove('sh_document');
    },

    _loadattachmentviewer(ev) {
        var attachment_id = parseInt(ev.currentTarget.dataset.id, 10);
        var rec_id = parseInt(ev.currentTarget.dataset.rec_id, 10);
        var attachment_mimetype = ev.currentTarget.dataset.mimetype;
        var mimetype_match = attachment_mimetype.match("(image|application/pdf|text|video)");
        var attachment_data = this.sh_attachment_data[0];


        if (mimetype_match) {
            var sh_attachment_id = attachment_id;
            var sh_attachment_list = [];
            attachment_data[rec_id].forEach((attachment) => {
                if (attachment.attachment_mimetype.match("(image|application/pdf|text|video)")) {
                    sh_attachment_list.push({
                        id: attachment.attachment_id,
                        filename: attachment.attachment_name,
                        name: attachment.attachment_name,
                        url: "/web/content/" + attachment.attachment_id + "?download=true",
                        type: attachment.attachment_mimetype,
                        mimetype: attachment.attachment_mimetype,
                        is_main: false,
                    });
                }
            });
            
            registry.category("main_components").add('sh_document', {
                Component: ShDocumentViewer,
                props: { attachments: sh_attachment_list, activeAttachmentID: sh_attachment_id},
            });

        } else {
            this.notificationService.add(_t("Preview for this file type can not be shown"), {
                title: _t("File Format Not Supported"),
                type: 'danger',
                sticky: false
            });
        }
    },

});

const getAttachmentNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

patch(AttachmentUploadService.prototype, {
    get uploadURL() {
        if (session.bg_color){
            return "/app/attachment/upload";
        }
        else{
            return "/mail/attachment/upload";
        }
    },
});

patch(AttachmentList.prototype, {
    /**
     * @param {import("models").Attachment} attachment
     */
    onClickDownload(attachment) {
        if (session.bg_color) {
            var attach_id = attachment.id
            rpc("/attach/get_data", {
                id: attach_id
            }).then(function (data) {
                if (data) {
                    window.flutter_inappwebview.callHandler('blobToBase64Handler', btoa(data['pdf_data']), data['attach_type'], data['attach_name']);
                }
            });
        } else {
            super.onClickDownload(attachment);
        }
    }
});

ListRenderer.components = {
    ...ListRenderer.components,
};
