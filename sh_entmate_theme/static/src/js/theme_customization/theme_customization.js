import { Component, useState, xml, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { isIOS } from "@web/core/browser/feature_detection";

export class ThemeCustomization extends Component{
    static template = "sh_entmate_theme.ThemeCustomization";
    static components = { Dropdown };

    setup(){
        super.setup();        
        let userAgent = navigator.userAgent;
		var is_iPad = navigator.userAgent.match(/iPad/i) != null;
		var is_safari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
		if(is_safari){
			document.querySelector('.o_web_client').classList.add('backmate_safari')
		}
		if(isIOS && !is_iPad){
			if(userAgent.match(/chrome|chromium|crios/i)){
				document.querySelector('.o_web_client').classList.add("sh_iphone_chrome")
			}else{
				document.querySelector('.o_web_client').classList.add("sh_iphone_safari")
			}
		}

        this.checked = useState({
            theme_color : "style_1",
            sidebar_style : "style_1",
            separator_style : "style_1",
            button_style : "style_1",
            kanban_style : "style_1",
            app_icon_style : "style_1",
            font_icon_style : "backend_fontawesome_icon",
            tab_style : "style_1",
            predefined_list_view_boolean : false,
            login_style_box : "style_3",
            form_element_style : "style_1",
            breadcrumbs_style : "style_1",
            checkbox_style : "default",
            radio_button_style : "default",
            scrollbar_style : "style_1",
            listview_style : "style_1",
            header_background_type : "bg_color",
            is_type_color : true,
            login_page_background_type : "bg_color",
            is_type_color_login_bg : true,
            body_background_type : "bg_color",
            is_body_background_type_color : true,
            is_custom_google_font : false,
            body_font_family : "",
            list_view_is_hover_row : false,
            progress_style : ""

            });
        this.saved_colors = useState({
            
            sidebar_background_color          : "#e7e9ed",
            sidebar_font_color                : "#000000",
            primary_color                     : "#00A09D",
            secondary_color                   : "#E6E6E6",
            extra_color                       : "#017e84",
            google_font                       : "",
            chatter_position                  : "bottom",
            separator_color                   : "#5D1049",
            is_sticky_form                    : false,
            is_sticky_list_inside_form        : false,
            is_sticky_list                    : false,
            is_sticky_pivot                   : false,
            list_view_border                  : "",
            list_view_odd_row_color           : "#FFFFFF",
            list_view_even_row_color          : "#FFFFFF",
            header_background_color           : "#875A7B",
            list_view_hover_bg_color : "#f5f5f5",
            progress_height : "4px",
            progress_color : "#000000"


        });

        this.orm = useService("orm");

        this.onWillStart();

        
    }


    async onWillStart(){
        self = this;
        rpc('/get_theme_style',{}).then(function (data) {
            console.log(data);
            
            self.checked.theme_color = data.theme_style;
            self.checked.sidebar_style = data.sidebar_img;
            self.checked.separator_style = data.separator_style;
            self.checked.button_style = data.button_style;
            self.checked.kanban_style = data.kanban_box_style;
            self.checked.app_icon_style = data.app_icon_style;
            self.checked.font_icon_style = data.backend_all_icon_style;
            self.checked.tab_style = data.tab_style;
            self.checked.form_element_style = data.form_element_style;
            self.checked.breadcrumbs_style = data.breadcrumb_style;
            self.checked.checkbox_style = data.checkbox_style;
            self.checked.radio_button_style = data.radio_style;
            self.checked.scrollbar_style = data.scrollbar_style;


            // using save.

            self.checked.predefined_list_view_boolean = data.predefined_list_view_boolean;
            self.checked.list_view_is_hover_row = data.list_view_is_hover_row;
            self.checked.login_style_box = data.login_page_style;
            self.checked.listview_style = data.predefined_list_view_style;
            self.checked.header_background_type = data.header_background_type;
            self.saved_colors.header_background_color = data.header_background_color;
            self.checked.login_page_background_type = data.login_page_background_type;
            self.checked.body_background_type = data.body_background_type;
            self.checked.is_custom_google_font = data.is_used_google_font;
            console.log(data.body_background_type);
            
            self.checked.body_font_family = data.body_font_family;

            self.saved_colors.sidebar_background_color = data.sidebar_color;
            self.saved_colors.sidebar_font_color = data.sidebar_font_color;
            self.saved_colors.primary_color = data.primary_color;
            self.saved_colors.secondary_color = data.secondary_color;
            self.saved_colors.extra_color = data.extra_color;
            self.saved_colors.google_font = data.google_font;
            self.saved_colors.chatter_position = data.chatter_type;
            self.saved_colors.separator_color = data.separator_color;
            self.saved_colors.is_sticky_form = data.is_sticky_form;
            self.saved_colors.is_sticky_list_inside_form = data.is_sticky_list_inside_form;
            self.saved_colors.is_sticky_list = data.is_sticky_list;
            self.saved_colors.is_sticky_pivot = data.is_sticky_pivot;
            self.saved_colors.list_view_border = data.list_view_border;
            self.saved_colors.list_view_odd_row_color = data.list_view_odd_row_color;
            self.saved_colors.list_view_even_row_color = data.list_view_even_row_color;
            self.saved_colors.header_background_color = data.header_background_color;
            self.saved_colors.list_view_hover_bg_color = data.list_view_hover_bg_color;

            self.checked.progress_style = data.progress_style;
            self.saved_colors.progress_height = data.progress_height;
            self.saved_colors.progress_color = data.progress_color;

            self.saved_colors.login_page_background_color = data.login_page_background_color;
            self.saved_colors.login_page_box_color = data.login_page_box_color;
            self.saved_colors.login_page_background_color = data.login_page_background_color;

            self.updateBodyClass()
        })


    }

    updateBodyClass() {
        // Remove existing chatter style classes
        document.body.classList.remove("chatter_style_bottom", "chatter_style_sided");

        // Add the selected chatter style class
        const className = this.saved_colors.chatter_position === "bottom" ? "chatter_style_bottom" : "chatter_style_sided";
        document.body.classList.add(className);
    }

    async  _click_theme_color_box(ev){
        var self = this;
        
        var color_id = (ev.target.parentElement).getAttribute('id');
        this.checked.theme_color = color_id

        rpc("/web/dataset/call_kw/res.lang/onchange_theme_style_js", {
                    model: 'sh.ent.theme.config.settings',
                    method: 'onchange_theme_style_js',
                    args: [color_id],
                    kwargs: {},
                }).then(async function (rec) {
                    var result = await self.orm.write("sh.ent.theme.config.settings", [1], { theme_style : color_id });
                    if (result){
                        location.reload();
                    }
                });
    }

    async _click_sidebar_style_box(ev){
        var target = ev.target.parentElement.parentElement.parentElement;
        var sidebar_style = target.getAttribute('id');
        let self = this;
        this.checked.sidebar_style = sidebar_style;

        var result = await self.orm.write("sh.ent.theme.config.settings", [1], {
         sidebar_img : sidebar_style});
         if (result){
            location.reload();
         }
    }

    _click_sh_theme_design(ev){
        let elm = ev.target.parentElement;

        var collapseElements = ev.currentTarget.parentElement.getElementsByClassName('collapse');
        console.log("hi");
        
        console.log(collapseElement);
        
        var collapseElement = collapseElements[0]; 
        console.log("ss");
        
        console.log(collapseElement);
        console.log(collapseElement.style.display);
        
        

        if (collapseElement.style.display == 'none' || collapseElement.style.display == "") {
            collapseElement.style.transition = 'height 0.6s ease'; 
            collapseElement.style.height = 'auto';  
            setTimeout(function() {
                collapseElement.style.height = collapseElement.scrollHeight + 'px'; 
            }, 0);
        } else {
            collapseElement.style.transition = 'height 0.6s ease';  
            collapseElement.style.height = collapseElement.scrollHeight + 'px';  
            setTimeout(function() {
                collapseElement.style.height = '0';
            }, 0);

            collapseElement.addEventListener('transitionend', function() {
                collapseElement.style.display = 'none';
            });
        }

        collapseElement.style.display = collapseElement.style.height === '0' ? 'none' : 'block';

    }

    
    // click header style.
    _click_header_background_type(ev) {

        var header_background_type = ev.currentTarget.value;
        console.log("clicke hereader",header_background_type);
        
        this.checked.header_background_type = header_background_type;

        if (header_background_type == "bg_color") {
            this.checked.is_type_color = true;
        }else{
            this.checked.is_type_color = false;
        }

    }

    
    // body background type.

    _click_body_background_type(ev) {

        var body_background_type = ev.currentTarget.value;
        this.checked.body_background_type = body_background_type;
        console.log(body_background_type);

        if (body_background_type == "bg_img") {
            this.checked.is_body_background_type_color = false;
        } else {
            this.checked.is_body_background_type_color = true;
        }
        
    }

    // body change font family.

    _on_change_body_font_family(ev) {
        console.log(ev.currentTarget.value);
        var bodyFontFamily = ev.currentTarget.value;
        this.checked.body_font_family = bodyFontFamily;
        // Check if the value is 'custom_google_font' and toggle display styles
        if (bodyFontFamily == 'custom_google_font') {
            this.checked.is_custom_google_font = true;
            this.saved_colors.google_font
        }else{
            this.checked.is_custom_google_font = false;
        }
    }

    // click seperator style box.

    async _click_separator_style_box(ev){

        var separator_style = ev.currentTarget.id;
        this.checked.separator_style = separator_style;

        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
         separator_style : separator_style});
         if (result){
            location.reload();
         }
    }

    // button style box.

    async _click_button_style_box(ev){
        var button_style = ev.currentTarget.id;
        this.checked.button_style = button_style;

        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
         button_style : button_style});
         if (result){
            location.reload();
         }

    }

    // kanban style box

    async _click_kanban_style_box(ev){
        var kanban_style = ev.currentTarget.id;
        this.checked.kanban_style = kanban_style;
        
        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
         kanban_box_style : kanban_style});
         if (result){
            location.reload();
         }
   }

   // app icon style.

   async _click_app_icon_style_box(ev){
        var app_icon_style = ev.currentTarget.id;
        this.checked.app_icon_style = app_icon_style;

        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
        app_icon_style : app_icon_style});
        if (result){
            location.reload();
        }

    }


    async _click_font_icon_style_box(ev){
        var font_icon_style = ev.currentTarget.id;
        this.checked.font_icon_style = font_icon_style;

        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
         backend_all_icon_style : font_icon_style});
         if (result){
            location.reload();
         }
   }


   async _click_tab_style_box(ev){
        var tab_style = ev.currentTarget.id;
        console.log("click tab");
        
        console.log(tab_style);
        
        this.checked.tab_style = tab_style;

        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
        horizontal_tab_style : tab_style});
        if (result){
            location.reload();
        }

    }

    async _click_predefined_list_view_boolean(ev) {

        this.checked.predefined_list_view_boolean = !this.checked.predefined_list_view_boolean;

    }

    async _click_login_style_box(ev){
        var login_style_box = ev.currentTarget.id;
        this.checked.login_style_box = login_style_box;

    }

    async _click_listview_style_box(ev) {
        var listview_style = ev.currentTarget.id;
        console.log(listview_style);
        this.checked.listview_style = listview_style;
        
        console.log(listview_style);
        
    
    }

    // click list view is hover.

    /*async _click_list_view_is_hover_row(ev){

        this.checked.list_view_is_hover_row = !this.checked.list_view_is_hover_row;

        *//*if (this.checked.list_view_is_hover_row) {
            var rowColorHoverElements = document.querySelectorAll(".is_row_color_hover");
            rowColorHoverElements.forEach(function(element) {
                element.style.display = "table-row";
            });
        } else {
            var rowColorHoverElements = document.querySelectorAll(".is_row_color_hover");
            rowColorHoverElements.forEach(function(element) {
                element.style.display = "none";
            });
        }*//*

    }*/

    // login page background type.

    _click_login_page_background_type(ev) {
        var login_page_background_type = ev.currentTarget.value;
        this.checked.login_page_background_type = login_page_background_type;

        if (login_page_background_type == "bg_color") {
            this.checked.is_type_color_login_bg = true;
        }else{
            this.checked.is_type_color_login_bg = false;
        }
    }
    
    

    // progressbar style.

    async _click_progressbar_style_box(ev) {
        
        var progress_style = ev.currentTarget.value
        if (progress_style === 'style_1') {
            document.getElementById("progress_color_height").style.display = "table-row";
        } else {
            document.getElementById("progress_color_height").style.display = "none";
        }
    }


    async _click_form_element_style_box(ev){
        var form_element_style = ev.currentTarget.id;
        this.checked.form_element_style = form_element_style;
   
        
        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
         form_element_style : form_element_style});
         if (result){
            location.reload();
         }
   }

   // click bread crumbs style box.

   async _click_breadcrumbs_style_box(ev){
        var breadcrumbs_style = ev.currentTarget.id;
        this.checked.breadcrumbs_style = breadcrumbs_style;
        
        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
        breadcrumb_style : breadcrumbs_style});
        if (result){
            location.reload();
        }
    }
    
    

   async _click_checkbox_style_box(ev){
    var checkbox_style = ev.currentTarget.id;
    this.checked.checkbox_style = checkbox_style;
    console.log(checkbox_style);
    
    var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
     checkbox_style : checkbox_style});
     if (result){
        location.reload();
     }

}


    // click radio button style.

        async _click_radio_button_style_box(ev){
            var radio_button_style = ev.currentTarget.id;
            this.checked.radio_button_style = radio_button_style;
            
            var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
            radio_style : radio_button_style});
            if (result){
                location.reload();
            }
   }

   // click scrollbar style box.

   async _click_scrollbar_style_box(ev){
        var scrollbar_style = ev.currentTarget.id;
        this.checked.scrollbar_style = scrollbar_style;
        
        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
        scrollbar_style : scrollbar_style});
        if (result){
            location.reload();
        }
    }

    // close model.

    async _click_close_setting(ev){
        var themeLayout = document.querySelector('.backmate_theme_layout');
        if (themeLayout) {
            themeLayout.setAttribute('style', 'opacity:0');
        }
        setTimeout(() => {
            document.querySelector('.sh_entmate_theme_config_template').click();
        }, 400);
    }

    async chatter_position_type(ev){
        this.saved_colors.chatter_position = ev.currentTarget.value;
    }

    async select_list_border_style(ev){
        this.saved_colors.list_view_border = ev.currentTarget.value;
    }

    async image_upload_change(event){
        const file = event.currentTarget?.files[0];
        if (file) {
            const formData = new FormData();
            formData.append(event.currentTarget.id, file);

            window.fetch('/api/upload/multi', {
                method: 'POST',
                body: formData,
            })
           
        }
        
    }

   
    
    // save button here

    async _click_save_color(ev){
        var self = this
        var sidebar_background_color = this.saved_colors.sidebar_background_color;

        var sidebar_font_color = this.saved_colors.sidebar_font_color;

        var primary_color = this.saved_colors.primary_color;
        
        var secondary_color = this.saved_colors.secondary_color;
        
        var extra_color = this.saved_colors.extra_color;
        
        var body_background_type = this.checked.body_background_type;
        var header_background_type = this.checked.header_background_type;
        console.log("header",header_background_color);
        
        
        var body_font_family = this.checked.body_font_family;
        var is_used_google_font = this.checked.is_custom_google_font;
        var body_google_font_family = false;
        
        var chatter_type = this.saved_colors.chatter_position;
        if (body_font_family === 'custom_google_font') {
            is_used_google_font = true;
            body_google_font_family = this.saved_colors.google_font;
        }
        
        var separator_color = "3px solid " + this.saved_colors.separator_color;
        
        // For checkboxes, use .checked to get the boolean value
        var is_sticky_form = this.saved_colors.is_sticky_form;
        var is_sticky_list = this.saved_colors.is_sticky_list;
        var is_sticky_list_inside_form = this.saved_colors.is_sticky_list_inside_form;
        var is_sticky_pivot = this.saved_colors.is_sticky_pivot;
        
        var predefined_list_view_boolean = self.checked.predefined_list_view_boolean;
        var predefined_list_view_style = self.checked.listview_style;
        var list_view_border = this.saved_colors.list_view_border;
        var list_view_even_row_color = this.saved_colors.list_view_even_row_color;
        var list_view_odd_row_color = this.saved_colors.list_view_odd_row_color;
        var list_view_is_hover_row = this.checked.list_view_is_hover_row;
        var list_view_hover_bg_color = this.saved_colors.list_view_hover_bg_color;
        
        var login_page_style = this.checked.login_style_box;
        var login_page_background_type = this.checked.login_page_background_type;
        var login_page_box_color = this.saved_colors.login_page_box_color;
        var login_page_background_color = this.saved_colors.login_page_background_color;
        
        var progress_style = this.checked.progress_style;
        var progress_height = this.saved_colors.progress_height;
        var progress_color = this.saved_colors.progress_color;
        
        var header_background_color = this.saved_colors.header_background_color;
        
        var result = await this.orm.write("sh.ent.theme.config.settings", [1], {
            header_background_color : header_background_color,
            sidebar_color : sidebar_background_color,
            sidebar_font_color : sidebar_font_color,
            primary_color : primary_color,
            secondary_color : secondary_color,
            extra_color : extra_color,
            body_background_type : body_background_type,
            header_background_type : header_background_type,
            body_font_family: body_font_family,
            is_used_google_font : is_used_google_font,
            body_google_font_family : body_google_font_family,
            separator_color : separator_color,
            is_sticky_form : is_sticky_form,
            is_sticky_list : is_sticky_list,
            is_sticky_list_inside_form : is_sticky_list_inside_form,
            is_sticky_pivot : is_sticky_pivot,
            predefined_list_view_boolean : predefined_list_view_boolean,
            predefined_list_view_style : predefined_list_view_style,
            list_view_border : list_view_border,
            list_view_even_row_color : list_view_even_row_color,
            list_view_odd_row_color : list_view_odd_row_color,
            list_view_is_hover_row : list_view_is_hover_row,
            list_view_hover_bg_color : list_view_hover_bg_color,
            login_page_style : login_page_style,
            login_page_background_type : login_page_background_type,
            login_page_background_color : login_page_background_color,
            login_page_box_color : login_page_box_color,
            progress_style : progress_style,
            progress_height : progress_height,
            progress_color : progress_color,
            chatter_type : chatter_type,

        });


        if (result){
            location.reload();
        }

   }

}

registry.category("systray").add("sh_entmate_theme.ThemeCustomization", { Component: ThemeCustomization }, { sequence: 100 });
