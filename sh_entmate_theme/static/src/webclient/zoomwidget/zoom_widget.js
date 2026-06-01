/** @odoo-module **/
import { user } from "@web/core/user";
import {Component} from "@odoo/owl";
import { useState ,onWillStart} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";


export class ZoomWidget extends Component {
    static template = 'sh_entmate_theme.ZoomWidget';
    static components = { Dropdown ,DropdownItem};
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({show_zoom_mode : true,show_zoom_functions : false, zoom_value : 100});
        this.onWillStart();
    }

    async onWillStart(){
        const data = await this.orm.searchRead("res.users",[['id', '=', user.userId]],["sh_enable_zoom"]
        );
        console.log(data[0]);
        
        if (data) {
          if (!data[0].sh_enable_zoom) {
              this.state.show_zoom_mode = false;
          }
      }
        var page = document.querySelector(".o_web_client");
        page.classList.forEach(function(className) {
            if (className.startsWith('sh_zoom_')) {
              page.classList.remove(className);
            }
          });
        
        if (this.state.zoom_value!=100) {
        var zoom_value_class = "sh_zoom_"+this.state.zoom_value;
        page.classList.add(zoom_value_class);
        }

    }
    setResetZoom(){
        this.state.zoom_value = 100;
        this.onWillStart();
    }

    zoomDropdown(ev){
          this.state.show_zoom_functions = !this.state.show_zoom_functions;
    }
    setDecZoom(){
        if (this.state.zoom_value>10) {
            this.state.zoom_value = this.state.zoom_value - 10;
        }
        this.onWillStart();

    }

    setIncZoom(){
        
        if (this.state.zoom_value<200) {
            this.state.zoom_value = this.state.zoom_value + 10
        }
        this.onWillStart();
    }

}
    

