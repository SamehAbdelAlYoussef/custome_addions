/** @odoo-module **/
import { MenuDropdown, MenuItem, NavBar } from '@web/webclient/navbar/navbar';
import { isMobileOS } from "@web/core/browser/feature_detection";
import { patch } from "@web/core/utils/patch";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { onMounted } from "@odoo/owl";
import { Component, onWillStart, useState } from "@odoo/owl";
import { renderToString } from "@web/core/utils/render";


var app_icon_style = 'style_1';
var backend_all_icon_style = 'backend_fontawesome_icon';
var enable_multi_tab = false

export class ShAppsMenu extends Component {
    static template = 'web_responsive.AppsMenu'
    setup() {
        super.setup();
        this.state = useState({ isOpen: false });
        this.menuManager = useService("menu");
        this.apps = this.menuManager.getApps();
        // this.action = useService("action");
        this.initializeKeyHandlers();
        onMounted(() => {
            window.addEventListener("SH_TRIGGER_MENU_STATE", (e) => {
                const { isOpen, triggeredByMenuClick } = e.detail;
                this.updateMenuState(isOpen, triggeredByMenuClick);
            });
        });
    }
    currentApp() {
        let app = this.menuManager.getCurrentApp();
        if (app){
            if (app_icon_style && (app_icon_style == 'style_2' || app_icon_style == 'style_4' || app_icon_style == 'style_6')){
                var app_name = app.xmlid
                return {
                    iconStyle: app_icon_style,
                    webIconData: app_name.replaceAll('.', '_'),
                };
            }
            else{
                if(app_icon_style && app_icon_style == 'style_1'){
                    return {
                        iconStyle: app_icon_style,
                        webIconData: app.webIconData,
                    };
                }
                if(app_icon_style && (app_icon_style == 'style_3' || app_icon_style == 'style_5')){
                    var app_name = app.xmlid
                    var xml = app_name.replaceAll('.', '_')
                    var url  =  ""
                    if(app_icon_style == 'style_3'){
                        url = "/sh_entmate_theme/static/src/app_icon/3d_icons/" + xml + ".png"
                    }
                    else{
                        url = "/sh_entmate_theme/static/src/app_icon/glass_icons/" + xml + ".png"
                    }
                    return {
                        iconStyle: app_icon_style,
                        webIconData: url,
                    };
                }
            }
        }
        return;
     }

    updateMenuState(isOpen, triggeredByMenuClick) {
        this.state.isOpen = isOpen;

        // Toggle a CSS class on the body for background overlay or effects
        document.body.classList.toggle("sh_sidebar_background_enterprise", isOpen);

        // Hide search-related elements if open
        const searchResults = document.querySelector('.sh_search_results');
        const globalSearch = document.querySelector('.sh_global_search');
        const globalSearchInput = document.querySelector('#global_search_input');

        if (searchResults) {
            searchResults.style.display = 'none';
        }
        if (globalSearch) {
            globalSearch.style.display = 'none';
        }
        if (globalSearchInput) {
            globalSearchInput.value = '';
        }

        // Handle special case when triggered by clicking the menu button
        if (triggeredByMenuClick) {
            const currentApp = this.menuManager.getCurrentApp();

            if (currentApp?.name === "Website") {
                const isNotInWeb = !window.location.pathname.startsWith("/web");

                // Add spinner icon if not already in /web
                if (isNotInWeb) {
                    const appIcon = document.querySelector(".o_navbar_apps_menu button > i");
                    if (appIcon) {
                        appIcon.className = "fa fa-spin fa-spinner";
                    }
                }

                // Redirect to home menu
                window.location.assign("/web#home");
                return;  // prevent duplicate trigger
            }
        }

        // Trigger custom logic (event, bus, or rerender)
        this.triggerMenuStateChange(isOpen);
    }


    triggerMenuStateChange(isOpen) {
        const event = new CustomEvent("SH_MENU_STATE:UPDATED", {
            detail: { isOpen },
        });
        window.dispatchEvent(event);
    }

    getMenuItemHref(payload) {
        return `/odoo/${payload.actionPath || "action-" + payload.actionID}${window.location.search}`;
    }
    initializeKeyHandlers() {
        const keyOptions = { allowRepeat: true };

        useHotkey("ArrowRight", () => this.navigate("next"), keyOptions);
        useHotkey("ArrowLeft", () => this.navigate("previous"), keyOptions);
        useHotkey("ArrowDown", () => this.navigate("next"), keyOptions);
        useHotkey("ArrowUp", () => this.navigate("previous"), keyOptions);
        useHotkey("Escape", () => this.updateMenuState(false, false));
    }

    navigate(direction) {
        const focusableApps = Array.from(document.querySelectorAll(".o_app"));
        if (focusableApps.length > 0) {
            const activeElementIndex = focusableApps.indexOf(document.activeElement);
            let nextIndex;

            if (direction === "previous") {
                nextIndex = activeElementIndex > 0 ? activeElementIndex - 1 : focusableApps.length - 1;
            } else {
                nextIndex = activeElementIndex + 1 < focusableApps.length ? activeElementIndex + 1 : 0;
            }

            focusableApps[nextIndex]?.focus();
        }
    }
}

patch(NavBar.prototype, {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.searchTheme()
        this.state = useState({
            show_global_search: false,
        })
        this.state.isAllAppsMenuOpened = false;
        this.state.isAppMenuSidebarOpened = false;
        enable_multi_tab = session.sh_enable_multi_tab
        this.enable_global_search = session.sh_enable_gloabl_search_mode
        onMounted(() => {
            if (enable_multi_tab){
               this.addmultitabtags()
            }
        });
    },

     loadMobileMenu() {
        this.state.isAllAppsMenuOpened = false;
        this.state.isAppMenuSidebarOpened = false;

        const event = new CustomEvent("SH_TRIGGER_MENU_STATE", {
            detail: { isOpen: true, triggeredByMenuClick: true },
        });
        window.dispatchEvent(event);

        const overlayContainer = document.querySelector('.o-overlay-container');
        const nextDiv = overlayContainer?.nextElementSibling;
        if (!nextDiv) return;

        nextDiv.innerHTML = '';

        const apps = this.menuService.getApps();
        const iconStyle = this.getIconStyle();

        const homeMenu = this.renderHomeMenu(apps, iconStyle);
        nextDiv.appendChild(homeMenu);
    },

    getMenuItemHref(payload) {
        return `/odoo/${payload.actionPath || "action-" + payload.actionID}${window.location.search}`;
    },


    renderHomeMenu(apps, iconStyle) {
        const container = document.createElement("div");
        container.className = "o_home_menu";
        container.style.height = "100vh";
        container.style.overflowY = "auto";

        const wrapper = document.createElement("div");
        wrapper.className = "container";

        const appGrid = document.createElement("div");
        appGrid.className = "o_apps row user-select-none mt-5 mx-0";
        appGrid.setAttribute("role", "listbox");

        apps.forEach((app, index) => {
            const col = document.createElement("div");
            col.className = "col-4 col-md-3 col-lg-2 mb-4 d-flex justify-content-center";

            const link = document.createElement("a");
            link.href = app.href || `/web#menu_id=${app.id}`;
            link.setAttribute("role", "option");
            link.setAttribute("id", `result_app_${index}`);
            link.dataset.menuXmlid = app.xmlid || "";

            link.className = "o_menuitem d-flex flex-column rounded-3 justify-content-start align-items-center w-100 p-1 p-md-2";

            link.addEventListener("click", async (ev) => {
                ev.preventDefault();

                // Remove the overlay
                const existingOverlay = document.querySelector('.o_home_menu');
                if (existingOverlay) existingOverlay.remove();

                // Also clean background class if any
                document.body.classList.remove("sh_sidebar_background_enterprise");

                // Route to actual app
                if (this.menuService && app.id) {
                    try {
                        await this.menuService.selectMenu(app.id);
                    } catch (err) {
                        console.error("Failed to select menu:", err);
                    }
                }
            });
            if (iconStyle === "style_1") {
                const img = document.createElement("img");
                img.className = "img o_app_icon o_app_icon_1 rounded-3";
                img.src = `/web/image?model=ir.ui.menu&field=web_icon_data&id=${app.id}`;
                link.appendChild(img);
            } else if (iconStyle === "style_2") {
                const span = document.createElement("span");
                span.className = `sh-${this.getAppClassName(app)} sh_fa_icon`;
                link.appendChild(span);
            } else if (iconStyle === "style_3") {
                const img = document.createElement("img");
                img.className = "img threed_icon icon_solid_new";
                img.src = `/sh_entmate_theme/static/src/app_icon/3d_icons/${this.getAppClassName(app)}.png`;
                img.title = app.name;
                img.alt = app.name;
                link.appendChild(img);
            } else if (iconStyle === "style_4") {
                const span = document.createElement("span");
                span.className = `sh-${this.getAppClassName(app)}-dt sh_fa_icon`;

                const path1 = document.createElement("span");
                path1.className = "path1";
                span.appendChild(path1);

                const path2 = document.createElement("span");
                path2.className = "path2";
                span.appendChild(path2);

                link.appendChild(span);

            } else if (iconStyle === "style_5") {
                const img = document.createElement("img");
                img.className = "img glass_icon icon_solid_new";
                img.src = `/sh_entmate_theme/static/src/app_icon/glass_icons/${this.getAppClassName(app)}.png`;
                img.title = app.name;
                img.alt = app.name;
                link.appendChild(img);

            } else if (iconStyle === "style_6") {
                const span = document.createElement("span");
                span.style.fontSize = "35px";
                span.className = `sh-${this.getAppClassName(app)}-l sh_fa_icon`;
                link.appendChild(span);

            }else {
                const fallback = document.createElement("div");
                img.style.maxWidth = "70px";
                fallback.className = "o_app_icon position-relative d-flex justify-content-center align-items-center p-2 rounded-3 ratio ratio-1x1";
                fallback.style.backgroundColor = app.webIcon?.backgroundColor || "#ccc";

                const icon = document.createElement("i");
                icon.className = app.webIcon?.iconClass || "fa fa-cube";
                icon.style.color = app.webIcon?.color || "#fff";
                fallback.appendChild(icon);
                link.appendChild(fallback);
            }

            // --- App label ---
            const caption = document.createElement("div");
            caption.className = "o_caption w-100 text-center text-truncate mt-2";
            caption.textContent = app.label || app.name || "App";
            link.appendChild(caption);

            col.appendChild(link);
            appGrid.appendChild(col);
        });

        wrapper.appendChild(appGrid);
        container.appendChild(wrapper);
        return container;
    },


    async searchTheme() {
        const data = await this.orm.searchRead(
            "sh.ent.theme.config.settings",
            [],
            ["app_icon_style", "backend_all_icon_style"]
        );
        if (data) {
            if (data[0]['app_icon_style']) {
                app_icon_style = data[0]['app_icon_style'];
            }
            if (data[0]['backend_all_icon_style']) {
                backend_all_icon_style = data[0]['backend_all_icon_style'];
            }
        }
    },

    onNavBarDropdownItemSelection(menu) {
        if (enable_multi_tab) {
            if (window.event.shiftKey) {
                this._createMultiTab(menu)
                //                localStorage.setItem("sh_add_tab",1)
            } else {
                //                localStorage.setItem("sh_add_tab",0)
            }
        }
        if (this.websiteCustomMenus) {
            const websiteMenu = this.websiteCustomMenus.get(menu.xmlid);
            if (websiteMenu) {
                return this.websiteCustomMenus.open(menu);
            }
        }

        if (menu) {
            this.menuService.selectMenu(menu);
        }
    },

    ShowGlobalSearch() {
        if (this.enable_global_search) {
            this.state.show_global_search = !this.state.show_global_search;
            let elm = document.querySelector(".sh_global_search");
            document.addEventListener("keypress",(e)=>{
                console.log(e.key);
                elm.style.display = "block";
                document.querySelector("input").focus()
            })
        }
        document.body.classList.toggle('sh_sidebar_background_enterprise')

        /*const appMenuDiv = document.querySelector(".sh_entmate_theme_appmenu_div");
        const body = document.body;
        const searchContainer = document.querySelector(".sh_search_container");
        const actionManager = document.querySelector(".o_action_manager");
        const menuBrand = document.querySelector(".o_menu_brand");
        const full = document.querySelector(".full");
        const menuSections = document.querySelector(".o_menu_sections");

        if (appMenuDiv?.classList.contains("sh_first_load")) {
            appMenuDiv.classList.remove("show", "sh_first_load");
        }
        if (appMenuDiv?.classList.contains("show")) {
            body.classList.remove("sh_sidebar_background_enterprise");
            if (searchContainer) searchContainer.style.display = "none";
            appMenuDiv.classList.remove("show");
            if (actionManager) actionManager.classList.remove("d-none");
            if (menuBrand) menuBrand.style.display = "block";
            if (full) full.classList.remove("sidebar_arrow");
            if (menuSections) menuSections.style.display = "flex";
        } else {
            appMenuDiv?.classList.add("show");
            body.classList.add("sh_sidebar_background_enterprise");
//            appMenuDiv.style.opacity = "1";
            if (full) full.classList.add("sidebar_arrow");
            if (menuBrand) menuBrand.style.display = "none";
            if (menuSections) menuSections.style.display = "none";
        }*/

    },
    // NEW 28TH MARCH MULTITAB CODE 
    _createMultiTab: function (ev) {
        var tab_name = ev.name
        /*var url = '#menu_id='+ev.id + '&action='+ ev.actionID*/
        var url = '/odoo/action-' + ev.actionID
        var actionId = ev.actionID
        var menuId = ev.id
        var menu_xmlid = ev.xmlid
        var self = this
        localStorage.setItem('LastCreatedTab', actionId)

        rpc('/add/mutli/tab', {
            'name': tab_name,
            'url': url,
            'actionId': actionId,
            'menuId': menuId,
            'menu_xmlid': menu_xmlid,
        }).then((rec) => {
            self.addmultitabtags(ev)
        });
    },

    addmultitabtags: async function (ev) {
        var self = this
        var rec = await rpc('/get/mutli/tab', {});
        if (rec) {
            /*if (theme_style == 'theme_style'){ debugge document.querySelector('body > header')?.style.height = "48px"; }*/
            const multiTabSection = document.querySelector('.multi_tab_section');
            // Clear the multi_tab_section content
            if (multiTabSection) {
                multiTabSection.innerHTML = '';

                // Iterate over the `rec` object or array
                rec.forEach(value => {
                    const tabTag = `
                            <div class="d-flex justify-content-between multi_tab_div align-items-center">
                                <a href="${value.url}" class="flex-fill" data-xml-id="${value.menu_xmlid}" data-menu="${value.menuId}"
                                    data-action-id="${value.actionId}" multi_tab_id="${value.id}" multi_tab_name="${value.name}">
                                    <span>${value.name}</span>
                                </a>
                                <span class="remove_tab ml-4">X</span>
                            </div>`;
                    multiTabSection.insertAdjacentHTML('beforeend', tabTag);
                });
            }

            /*$('.multi_tab_section').empty()
            $.each(rec, function( key, value ) {
                var tab_tag = '<div class="d-flex justify-content-between multi_tab_div align-items-center"><a href="'+ value.url +'"'+' class="flex-fill" data-xml-id="'+ value.menu_xmlid +'" data-menu="'+ value.menuId +'" data-action-id="'+ value.actionId +'" multi_tab_id="'+value.id+'" multi_tab_name="'+value.name+'"><span>'+value.name+'</span></a><span class="remove_tab ml-4">X</span></div>'
                $('.multi_tab_section').append(tab_tag)
            })*/
            var ShstoredActionId = sessionStorage.getItem("sh_current_action_id");
            var ShstoredAction = sessionStorage.getItem("sh_current_action");
            if (ShstoredActionId) {
                var TabDiv = document.querySelector('.multi_tab_section .multi_tab_div');
                var ActiveMenu = TabDiv.find('a[data-action-id="' + ShstoredActionId + '"]');
                ActiveMenu.parent().addClass('tab_active')
            }

            if (ev) {
                var actionId = ev.actionID
                var menu_xmlid = ev.xmlid
                if (localStorage.getItem('LastCreatedTab')) {
                    var target = '.multi_tab_section .multi_tab_div a[data-action-id="' + localStorage.getItem('LastCreatedTab') + '"]'
                    target.parentElement?.classList.add('tab_active');
                    localStorage.removeItem('LastCreatedTab')
                } else {
                    var target = '.multi_tab_section .multi_tab_div a[data-xml-id="' + menu_xmlid + '"]'
                    target.parentElement?.classList.add('tab_active');
                }
            }
            document.body.classList.add("multi_tab_enabled");

        } else {
            document.body.classList.remove("multi_tab_enabled");
        }
        /*$('.multi_tab_section .remove_tab').on('click', function (ev) {
                    self._RemoveTab(ev)
                });
        $('.multi_tab_section .multi_tab_div a').on('click', function (ev) {
                    self._TabClicked(ev)
                });*/
        document.querySelectorAll('.multi_tab_section .remove_tab').forEach(element => {
            element.addEventListener('click', ev => {
                self._RemoveTab(ev);
            });
        });

        document.querySelectorAll('.multi_tab_section .multi_tab_div a').forEach(element => {
            element.addEventListener('click', ev => {
                self._TabClicked(ev);
            });
        });

    },

    _RemoveTab: function (ev) {
        var self = this
        var multi_tab_id = ev.target.closest('.multi_tab_div')?.querySelector('a')?.getAttribute('multi_tab_id');
        rpc('/remove/multi/tab', {
            'multi_tab_id': multi_tab_id,
        }).then(function (rec) {
            if (rec) {
                if (rec['removeTab']) {
                    /*$(ev.target).parent().remove()
                    var FirstTab = $('.multi_tab_section').find('.multi_tab_div:first-child')*/
                    ev.target.closest('.multi_tab_div')?.remove();
                    var FirstTab = document.querySelector('.multi_tab_section .multi_tab_div');
                    if (FirstTab?.length) {
                        FirstTab.querySelector('a')?.click();
                        FirstTab.classList.add('tab_active');
                        /*$(FirstTab).find('a')[0].click()
                        $(FirstTab).addClass('tab_active')*/
                    }
                }
                if (rec['multi_tab_count'] == 0) {
                    document.body.classList.remove("multi_tab_enabled");
                }
            }
        });
    },

    _TabClicked: function (ev) {
        localStorage.setItem("TabClick", true);
        localStorage.setItem("TabClickTilteUpdate", true);
        if (ev.target.dataset.actionId) {
            document.querySelector('.multi_tab_section .tab_active')?.classList.remove('tab_active');
            ev.target.closest('.multi_tab_div')?.classList.add('tab_active');
        }
        else {
            if (ev.currentTarget.dataset.actionId) {
                document.querySelector('.multi_tab_section .tab_active')?.classList.remove('tab_active');
                ev.currentTarget.closest('.multi_tab_div')?.classList.add('tab_active');
            }
        }
    },

    // NEW 28TH MARCH MULTITAB CODE 

    onNavBarDropdownItemClick(ev) {
        if (ev.shiftKey) {
            localStorage.setItem("sh_add_tab", 1)
        } else {
            localStorage.setItem("sh_add_tab", 0)
        }
    },
    getAppClassName(app) {
        var app_name = app.xmlid
        return app_name.replaceAll('.', '_')
    },
    getIconStyle() {
        return app_icon_style;
    },
    currentAppData() {
        return this.menuService.getCurrentApp();
    },
    getBackend_icon() {
        return backend_all_icon_style;
    },
    isMobile(ev) {
        return isMobileOS;
    },

});

ShAppsMenu.template = "web_responsive.AppsMenu";
Object.assign(NavBar.components, {ShAppsMenu});


