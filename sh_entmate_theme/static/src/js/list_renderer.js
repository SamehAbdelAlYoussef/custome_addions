/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
const { Component, useState, useRef, useExternalListener, onWillUpdateProps, onWillStart, onPatched } = owl;
import { renderToFragment } from "@web/core/utils/render";
import {DocumentViewer} from "./document_viewer_component"


patch(ListRenderer.prototype,{

    setup(){

        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.notificationService = useService("notification");

        onWillStart(async () => {
            
            const data = await this.orm.call('res.users', 'get_attachment_data', [this.props.list.resModel, this.props.list.records.map((rec)=>rec.resId)], {});

            this.sh_attachments = data[0]
            this.sh_show_attachment_in_list_view = data[1]

        });
        super.setup()

    },

    _shloadattachmentviewer: async function (ev) {
        
        let attachment_id = parseInt($(ev.currentTarget).data("id"));
        let record_id = parseInt($(ev.currentTarget).data("record_id"));
        let attachment_mimetype = $(ev.currentTarget).data("mimetype");
        let mimetype_match = attachment_mimetype.match("(image|application/pdf|text|video)");
        let attachment_name = $(ev.currentTarget).data("data-name");
        var attachment_data = this.sh_attachments[0];

      if (mimetype_match) {

        var sh_attachment_id = attachment_id;
        var sh_attachment_list = [];
          attachment_data[record_id].forEach((attachment) => {
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

        /*var sh_attachmentViewer = new shDocumentViewer(self,sh_attachment_list,sh_attachment_id);
        sh_attachmentViewer.appendTo($(".o_DialogManager"));*/

        var self = this
        var list_html = await renderToFragment(
                                        'shDocumentViewer', {
                                         modelName:'ssssssssss',
                                         sh_attachment_list: sh_attachment_list,
                                         sh_attachment_id:sh_attachment_id,
                                        });
                                        $(".modal-dialog").html(list_html)

      }
      else{

        this.notificationService.add(this.env._t("Preview for this file type can not be shown"), {
            title: this.env._t("File Format Not Supported"),
            type: 'danger',
            sticky: false
        });
      }

    }
})

ListRenderer.components = { DocumentViewer };