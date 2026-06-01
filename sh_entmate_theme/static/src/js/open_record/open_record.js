/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { ActionMenus } from "@web/search/action_menus/action_menus";

patch(ListRenderer.prototype, {
  /**
   * @override
   */
  setup() {
    this.show_open_record_new_tab_button_listrenderer =
    session.sh_enable_open_record_in_new_tab;
    this.is_list_view = true;
    var Many2one_protect = this["env"]["config"]["actionType"];
    var view_type = this["props"]["activeActions"]["type"];
    if (view_type != "view" || Many2one_protect == false) {
      this.is_list_view = false;
    }
    onMounted(this.onMounted);
    super.setup();
  },

  onMounted() {
      if (this.show_open_record_new_tab_button_listrenderer) {
        if (this.is_list_view) {
          // Find the table rows
          var table = document.querySelector(".o_list_table");
          var trElements = table.querySelectorAll("tr:not([class])");
          
          if (trElements.length > 0) {
            var header = trElements[0];
            var table_header = document.createElement("th");
            table_header.textContent = "Open";
            header.children[0].insertAdjacentElement('afterend', table_header);
            
            var footer = trElements[trElements.length - 1];
            var table_footer = document.createElement("td");
            footer.children[0].insertAdjacentElement('afterend', table_footer);
            
            var trsWithColspan6 = table.querySelectorAll("tr:has(td[colspan])");
            
            trsWithColspan6.forEach(function(tr) {
              var newTd = document.createElement("td");
              tr.appendChild(newTd);
            });
          }
        }
      }
  },

  OpenRecord(res_id) {
    var url = window.location.href;
    // var latest_url = url + "&id=" + res_id;
    var latest_url = url + "/" + res_id;
    // let result = latest_url.replace("view_type=list", "view_type=form");
    var result = latest_url
    window.open(result, "_blank");
  },

  setDefaultColumnWidths() {
      if (this.show_open_record_new_tab_button_listrenderer) {
        var trsWithGroupheader = document.querySelectorAll("tr:has(th.o_group_name)");
    
        if (trsWithGroupheader.length > 0) {
          trsWithGroupheader.forEach(function(tr) {
            var hasCustomClass = false;
    
            // Check if any <td> inside the <tr> contains the custom class
            var tds = tr.querySelectorAll("td");
            tds.forEach(function(td) {
              if (td.classList.contains("sh_custom_class")) {
                hasCustomClass = true;
                return; // Exit the loop if the custom class is found in a <td>
              }
            });
    
            // If the custom class is not found, add a new <td> with the custom class
            if (!hasCustomClass) {
              var newTd = document.createElement("td");
              newTd.classList.add("sh_custom_class");
              tr.children[0].insertAdjacentElement("afterend", newTd);
            }
          });
        }
        super.setDefaultColumnWidths();
      } else {
        super.setDefaultColumnWidths();
      }
    
    
  },
});


// Action Menu

patch(ActionMenus.prototype, {
  /**
   * @override
   */

  setup(){
    this.show_open_record_new_tab_button_action = session.sh_enable_open_record_in_new_tab;
    super.setup();
  },

  onOpenRecord() {
    let record_activeIds = this.props.getActiveIds();
    for (var j in record_activeIds) {
      var url = window.location.href;
      var latest_url = url + "/" + record_activeIds[j];
      // let result = latest_url.replace("view_type=list", "view_type=form");
      let result = latest_url;
      window.open(result, "_blank");
    }
  },
});