/* @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { user } from "@web/core/user";

// import { TodoCard } from "@sh_entmate_theme/js/todo_widget/todo_card";

export class ToDoTemplate extends Component {
	static template = "sh_entmate_theme.ToDoTemplate";

	setup() {
		super.setup();
		this.orm = useService("orm");
		this.sh_enable_todo_mode = session.sh_enable_todo_mode;
		this.state = useState({ show_todo: false, input_value: null, todo_datas : [], edit_id : undefined, show_label: true });
		useBus(this.env.bus, 'close_todo_list', (ev) => this.closeTodoList());
		this.onWillStart()
	}

	closeTodoList(){
	    this.state.show_todo = false;
	}

	async onWillStart(){
		const data = await this.orm.searchRead(
            "sh.todo",
            [['user_id', '=', user.userId]],
            ['name','is_done']
            );

		this.state.todo_datas = data;
	}

	// show todo model
	_click_todo() {
		this.state.show_todo = true;
		// Close Other Pop-up
        this.env.bus.trigger('close_quick_create', {});
        this.env.bus.trigger('close_quick_menu', {});
        this.env.bus.trigger('close_calculator', {});
        this.env.bus.trigger('close_recent_record', {});
        this.env.bus.trigger('close_bookmark', {});
	}

	// hide todo model
	_close_todo() {
		this.state.show_todo = false;
	}

	// onkeydown method
	async add_todo() {
	}

	// save todo text
	async _click_add_todo() {
		var todo_txt = this.state.input_value;

		if (todo_txt == null || todo_txt == "" || todo_txt == " ") {
			alert("please enter titlte")
		} else {
			var data = await this.orm.create("sh.todo", [{
				'name': todo_txt,
			}]);
			this.onWillStart();
		}
		this.state.input_value = null;
	}

	// check/uncheck todo task.

	async _click_sh_todo_checklist(ev){
		var todo_id = parseInt(ev.currentTarget.id);
		if(ev.currentTarget.classList.contains('sh_todo_checklist')){
		    var done_todo = ev.currentTarget.checked;
		}
		else{
		    var done_todo = !ev.currentTarget.querySelector('.sh_todo_checklist').checked
		}
		await this.orm.write("sh.todo", [todo_id], { is_done : done_todo });
		this.onWillStart()
	}

	// edit data enable textarea
	async _click_sh_header_pencil(ev){
		var item = ev.currentTarget.id;
		this.state.edit_id = item;
		this.state.show_label = false

		/*TODO*/
		ev.target.parentElement.parentElement.parentElement.parentElement.getElementsByClassName("sh_todo_label")[0].style.display = "none";
		ev.currentTarget.parentElement.parentElement.querySelector('.sh_header_save').style.display = 'block'
		ev.currentTarget.style.display = 'none'
		
	}

	// on blue element auto save and write.
	async onBlurTextArea(ev){
		var todo_id = parseInt(ev.currentTarget.id);
		var todo_value = ev.currentTarget.value;

		await this.orm.write("sh.todo", [todo_id], { name : todo_value });

		this.state.edit_id = undefined;
		this.state.show_label = true
		/*TODO*/
		ev.target.parentElement.parentElement.parentElement.parentElement.querySelector('.sh_header_pencil').style.display = 'block'
		ev.target.parentElement.parentElement.parentElement.parentElement.querySelector('.sh_header_save').style.display = 'none'
		this.onWillStart();

		/*TODO*/
		ev.target.parentElement.parentElement.parentElement.parentElement.getElementsByClassName("sh_todo_label")[0].style.display = "block";
	}

	// delete item 
	async _remove_todo(ev){
		var todo_id = parseInt(ev.currentTarget.id);
		await this.orm.unlink("sh.todo", [todo_id]);
		this.onWillStart();
	}

}

registry.category("systray").add("sh_entmate_theme.ToDoTemplate", { Component: ToDoTemplate }, { sequence: 25 });
