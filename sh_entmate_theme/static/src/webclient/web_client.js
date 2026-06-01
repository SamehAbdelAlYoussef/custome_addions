/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { ActionContainer } from "@web/webclient/actions/action_container";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ZoomWidget } from "@sh_entmate_theme/webclient/zoomwidget/zoom_widget";
import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";


patch(WebClient.prototype, {
   


});
	WebClient.components = {
		ActionContainer,
        ZoomWidget,
        NavBar,
        // NotUpdatable,
        MainComponentsContainer,
	};

WebClient.template = "web.WebClient";

