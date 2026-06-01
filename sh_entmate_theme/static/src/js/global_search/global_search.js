/* @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { onWillStart, onMounted, onWillUnmount} from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
var show_company = false;


export class GlobalSearchSh extends Component {
    static template = "sh_entmate_theme.GlobalSearch";

    setup() {
        super.setup()
        this.orm = useService("orm");
        this.show_company = show_company
        this.sh_enable_gloabl_search_mode = session.sh_enable_gloabl_search_mode
        this.sidebar_collapse_style = ""

        this.state = useState({
            query: "",
            results: [],
            hasResults: false,
            isExpanded: false,
        });

        this.onWillStart();

        this.keydownHandler = this.handleKeydown.bind(this);
        onMounted(() => {
            document.body.addEventListener("keydown", this.keydownHandler);
        });

        onWillUnmount(() => {
            document.body.removeEventListener("keydown", this.keydownHandler);
        });
       
    }

    handleKeydown(e) {
        const body = document.body;

        if (body.classList.contains("sh_sidebar_background_enterprise")) {
            const searchContainer = document.querySelector(".sh_global_search");
            const searchInput = document.querySelector(".usermenu_search_input");
            const appMenuDiv = document.querySelector(".dropdown-menu-custom");

            if (searchContainer) searchContainer.style.display = "block";
            if (searchInput) searchInput.focus();
            if (appMenuDiv) appMenuDiv.style.opacity = "0";
        }
    }

    onWillStart(){
        let doc = document.body;
        let search_input = document.getElementById("global_search_input");
        var val = "";
        doc.addEventListener("keypress",function(e){
            val = val  + e.key;
        });
    }

    onKeyUp(){
        if(!this.state.query){
             const body = document.body;
             if (body.classList.contains("sh_sidebar_background_enterprise")) {
                const searchContainer = document.querySelector(".sh_global_search");
                const searchInput = document.querySelector(".usermenu_search_input");
                const appMenuDiv = document.querySelector(".dropdown-menu-custom");

                if (searchContainer) searchContainer.style.display = "none";
                if (searchInput) searchInput.focus();
                if (appMenuDiv) appMenuDiv.style.opacity = "1";
            }
        }
    }

   

    async _searchData() {
        if(document.querySelector('.sh_search_results')){
            document.querySelector('.sh_search_results').style.display = "block";
        }

        const config = await this.orm.searchRead(
            "sh.ent.theme.config.settings",
            [['id', '=', 1]],
            ["theme_style"]
        );

        const searchStyle = config[0]?.theme_style || "collapsed";
        this.state.isExpanded = searchStyle === "expanded";

        const inputSelector = this.state.isExpanded
            ? ".sh_search_input input.usermenu_search_input2"
            : ".sh_search_input input.usermenu_search_input";
        const searchInput = document.querySelector(inputSelector);

        if (!searchInput) return;

        const query = searchInput.value.trim();
        this.state.query = query;
        if (!query) {
            this.state.results = [];
            this.state.hasResults = false;
            return;
        }

        try {
            const data = await rpc("/web/dataset/call_kw/global.search/get_search_result", {
                model: 'global.search',
                method: 'get_search_result',
                args: [[query]],
                kwargs: {},
            });
            
        // Handle different data structures
        if (Array.isArray(data)) {
            this.state.results = data;
        } else if (typeof data === "object") {
            this.state.results = Object.values(data || {});
        } else {
            this.state.results = [];
        }
           this.state.hasResults = this.state.results.length > 0;
        } catch (error) {
        }
    }
}

registry.category("systray").add("sh_entmate_theme.GlobalSearch", { Component: GlobalSearchSh }, { sequence: 25 });