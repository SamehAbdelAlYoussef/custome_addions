/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
var sh_disable_auto_edit_model = false
import { session } from "@web/session";


patch(FormController.prototype, {
    async setup() {
        super.setup();
        
        if (this.footerArchInfo) {
            // If dialogue box then need to give edit permission
            this.props.preventEdit = false
        }
        else if (session.sh_disable_auto_edit_model) {
            
            this.model.config.mode = 'readonly';
        }

    },


    disableEditButton() {
        if (session.sh_disable_auto_edit_model) {
            return true
        } else {
            return false
        }
    },

    _onClickEditView(ev) {
        ev.currentTarget.style.display = 'none'
        this.model.root.switchMode("edit");
        this.shDisplayButtons()
        this.hideEdit = true
    },

    async saveButtonClicked(params = {}) {
        if(document.querySelector('.sh_form_button_edit'))
        {
            document.querySelector('.sh_form_button_edit').style.display = 'block'
        }

        super.saveButtonClicked();
        if (session.sh_disable_auto_edit_model) {
            this.hideEdit = false
            this.model.root.switchMode("readonly");
        }
    },

    async discard() {
        if(document.querySelector('.sh_form_button_edit')){
            document.querySelector('.sh_form_button_edit').style.display = 'block'
        }
        super.discard();
        if (session.sh_disable_auto_edit_model) {
            this.hideEdit = false
        }
        this.model.root.switchMode("readonly");
    },

    async shDisplayButtons() {
        const dirty = await this.model.root.isDirty();

        if (dirty) {
            return false
        }
        else {
            return true
        }
    },

});

