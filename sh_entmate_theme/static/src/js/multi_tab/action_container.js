/** @odoo-module **/


import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { ActionContainer } from '@web/webclient/actions/action_container';
const { Component, tags } = owl;
import { NavBar } from '@web/webclient/navbar/navbar';
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillStart, onWillDestroy, xml } from "@odoo/owl";
import { markup } from "@odoo/owl";
const components = { ActionContainer };
import { session } from "@web/session";
import { renderToElement } from "@web/core/utils/render";
import { NavTab } from "@sh_entmate_theme/js/multi_tab/navtab";
import { user } from "@web/core/user";

var display_notice = false;
var font_color = '#ffffff';
var background_color = '#212121';
var font_size = 12;
var font_family = 'Roboto';
var padding = 5;
var content = ''
var is_animation = false;
var direction = 'right';
var simple_text = false;
var is_popup_notification = false;
var close_notification = false;
var notification_template = '';

patch(components.ActionContainer.prototype, {
    setup() {
       super.setup()
       this.orm = useService("orm");
       this.render_action_template()
    },

    async render_notification_template(){
        const output = await this.orm.searchRead(
                        "sh.announcement",
                        [['is_popup_notification', '=', false], ['user_ids.id', 'in', [user.userId]]],
                        ['is_popup_notification', 'font_size', 'font_family', 'padding', 'name', 'description', 'is_animation', 'direction', 'user_ids', 'simple_text', 'background_color', 'font_color', 'description_text']
                        );

                        
        if (output.length>0){
            var display_notice = true
            
            
            if (display_notice && !is_popup_notification) {
                var style = "position:relative;background:" + output[0].background_color + ";color:" + output[0].font_color + ";font-size:" + output[0].font_size + "px;font-family:" + output[0].font_family + ";padding:" + output[0].padding + "px;"
                var notification_html =   renderToElement(
                                    'sh_entmate_theme.notification', {
                                    // display_notice: output[0].display_notice,
                                    // background_color: output[0].background_color,
                                    font_size: output[0].font_size,
                                    font_family: output[0].font_family,
                                    padding: output[0].padding,
                                    font_color: output[0].font_color,
                                    is_animation: output[0].is_animation,
                                    direction: output[0].direction,
                                    simple_text: output[0].simple_text,
                                    is_popup_notification: output[0].is_popup_notification,
                                    content: output[0].simple_text ?output[0]['description_text'] : output[0]['description'] ,
                                    style: style,
                                    close_notification: function (ev){
                                  ev.currentTarget.parentElement.style.display = "none";
                                  
                                    }
                                });
                                
                document.querySelector(".o_web_client").append(notification_html);
            }

        }

    },
    async render_action_template(){
        var self = this
        await self.render_notification_template().then(function (data){
            self.info = {};
            self.notification_template = notification_template;
            self.onActionManagerUpdate = ({ detail: info }) => {
                self.info = info;
                self.render();
            };
            self.env.bus.addEventListener("ACTION_MANAGER:UPDATE", self.onActionManagerUpdate);
        });
    },

    close_backmate_theme_layout(){
        this.env.bus.trigger('close_quick_create', {});
        this.env.bus.trigger('close_todo_list', {});
        this.env.bus.trigger('close_calculator', {});
        this.env.bus.trigger('close_recent_record', {});
        this.env.bus.trigger('close_quick_menu', {});
        this.env.bus.trigger('close_bookmark', {});

        if(document.querySelector('.sh_search_results')){
            document.querySelector('.sh_search_results').style.display = "none";
        }

    },

});

ActionContainer.components = { ActionDialog, NavTab };
ActionContainer.template = xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager" t-on-click="close_backmate_theme_layout" >
       <NavTab/>
        <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`;
ActionContainer.props = {};


