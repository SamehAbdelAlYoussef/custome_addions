/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { patch } from "@web/core/utils/patch";
import { PivotGroupByMenu } from "@web/views/pivot/pivot_group_by_menu";


const components = { Dropdown, PivotGroupByMenu };

patch(components.PivotGroupByMenu.prototype, {
    onGroupBySelected({ itemId, optionId }) {
        var pivotElement = document.querySelector('.o_pivot');
        if (pivotElement && pivotElement.classList.contains('sh_pivot')) {
            pivotElement.classList.remove('sh_pivot');
        }
        

        const item = this.items.find(({ id }) => id === itemId);
        this.props.onItemSelected({
            itemId,
            optionId,
            fieldName: item.fieldName,
            interval: optionId,
            groupId: this.props.cell.groupId,
        });
    }

});
patch(components.Dropdown.prototype, {

    toggle() {
        const toggled = !this.state.open;
        
        var pivotElement = document.querySelector('.o_pivot');
        if (pivotElement) {
            if (toggled) {
                pivotElement.classList.add('sh_pivot');
            } else {
                pivotElement.classList.remove('sh_pivot');
            }
        }
        
        return this.changeStateAndNotify({ open: toggled, groupIsOpen: toggled });

    },
   
});