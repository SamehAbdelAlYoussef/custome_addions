/* @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { Dropdown } from "@web/core/dropdown/dropdown";


export class CalculatorTemplate extends Component {
    static components = { Dropdown };
    static template = "sh_entmate_theme.CalculatorTemplate";

    setup() {
        this.orm = useService("orm");
        this.state = useState({ enable_calc: true, show_calc: false, input_expression: "" });
        useBus(this.env.bus, 'close_calculator', (ev) => this.closeCalculator());
        this.onWillStart()
    }

    async onWillStart() {
        const data = await this.orm.searchRead("res.users", [['id', '=', user.userId]], ["sh_enable_calculator_mode"]
        );
        if (data) {
            if (!data[0].sh_enable_calculator_mode) {
                this.state.enable_calc = false;

            }
        }
    }


    showCalculator() {
        this.state.show_calc = !this.state.show_calc;

        // Close Other Pop-up
        this.env.bus.trigger('close_quick_create', {});
        this.env.bus.trigger('close_quick_menu', {});
        this.env.bus.trigger('close_recent_record', {});
        this.env.bus.trigger('close_todo_list', {});
        this.env.bus.trigger('close_bookmark', {});
    }

    closeCalculator(){
        this.state.show_calc = false;
    }

    // Keyboard press 

    onKeypress(ev) {
        if (ev.key == "Enter") {
            this.answerButton();
        }

    }

    // Buttons Events 

    cancelButton() {
        this.state.input_expression = "";

    }

    rootButton() {
        this.state.input_expression = "√"
    }

    squareButton() {
        let number = Number(this.state.input_expression);

        if (isNaN(number)) {
            alert("Enter Valid Value for square result");
            this.state.input_expression = ""
        }
        else if (typeof number == "number") {
            this.state.input_expression = number * number;
        }
    }

    divisionButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "/"
        } else {
            this.state.input_expression = "/"
        }
    }

    sevenButton() {

        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "7"
        } else {
            this.state.input_expression = "7"
        }
    }

    eightButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "8"
        } else {
            this.state.input_expression = "8"
        }
    }

    nineButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "9"
        } else {
            this.state.input_expression = "9"
        }
    }

    multiplyButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "*"
        } else {
            this.state.input_expression = "*"
        }
    }


    fourButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "4"
        } else {
            this.state.input_expression = "4"
        }
    }

    fiveButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "5"
        } else {
            this.state.input_expression = "5"
        }
    }

    sixButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "6"
        } else {
            this.state.input_expression = "6"
        }
    }

    minusButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "-"
        } else {
            this.state.input_expression = "-"
        }
    }

    oneButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "1"
        } else {
            this.state.input_expression = "1"
        }
    }

    twoButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "2"
        } else {
            this.state.input_expression = "2"
        }
    }

    threeButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "3"
        } else {
            this.state.input_expression = "3"
        }
    }

    plusButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "+"
        } else {
            this.state.input_expression = "+"
        }
    }


    plusMinusButton() {

        if (this.state.input_expression != "0") {
            this.state.input_expression = "-" + this.state.input_expression
        } 
        // else {
        //     this.state.input_expression = "±"
        // }
    }

    zeroButton() {
        this.state.input_expression = this.state.input_expression + "0"
    }

    decimalButton() {
        if (this.state.input_expression != "0") {
            this.state.input_expression = this.state.input_expression + "."
        } else {
            this.state.input_expression = "0."
        }
    }


    answerButton() {
        var expression = this.state.input_expression;
        var hasAlphabets = /[a-zA-Z]/.test(expression);
        var hasSpecialChars = /[^a-zA-Z0-9\s+\-*/%=]/.test(expression);

        if (!hasAlphabets && !hasSpecialChars) {
            if (expression.includes("√")) {
            let number = expression.split("√")[1];
            this.state.input_expression = Math.sqrt(number);
            } else {
                this.state.input_expression = eval(this.state.input_expression);
            }
        }
        else{
            this.state.input_expression = '';
        }
    }

}

registry.category("systray").add("sh_entmate_theme.CalculatorTemplate", { Component: CalculatorTemplate });