# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "EnterpriseMate Backend Theme [For Community Edition]",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "license": "OPL-1",
    "category": "Themes/Backend",
    "version": "0.0.12",
    "summary": "Enterprise Backend Theme, Enterprise Theme, Backend Enterprise Theme, Flexible Enterprise Theme, Enter prise Theme Odoo",
    "description": """Do you want odoo enterpise look in your community version? Are You looking for modern, creative, clean, clear, materialise odoo enterpise look theme for your backend? So you are at the right place, We have made sure that this theme is highly clean, modern, fully customizable enterprise look theme. Cheers!""",
    "depends":
    [
        "web",
        "mail"
    ],
    'external_dependencies': {
        'python': ['firebase_admin'],
    },
    "data":
    [
        "data/theme_config_data.xml",
        "security/base_security.xml",
        "security/ir.model.access.csv",
        "views/views.xml",
        "views/assets.xml",
        "views/login_layout.xml",
        "views/notifications_view.xml",
        "views/send_notifications.xml",
        "views/web_push_notification.xml",
        "views/ent_theme_config_view.xml",
        "views/global_search_view.xml",
        "wizard/theme_preview_wizard.xml",        
        "views/res_users_views.xml",
        "views/firebase_res_config_settings_views.xml",

        # Mobile App
        'views/mobile_app/witch_user_template.xml',
        'views/mobile_app/res_company_views.xml',
        'views/mobile_app/res_users_views.xml'
    ],

    'assets': {

        'web.assets_backend': [
            # mixin           
            "sh_entmate_theme/static/src/scss/mixin/mixin.scss",

            #app_drawer
            "sh_entmate_theme/static/src/scss/app_drawer/app_drawer.scss",


            "/sh_entmate_theme/static/src/enterprise_menu_style/apps_menu/apps_menu.scss",
            "/sh_entmate_theme/static/src/enterprise_menu_style/search_panel/search_panel.scss",

            # Calculator
            'sh_entmate_theme/static/src/js/calculator_widget/calculator_widget.js',
            'sh_entmate_theme/static/src/js/calculator_widget/calculator_widget.xml',
            'sh_entmate_theme/static/src/scss/calculator/calculator.scss',

            # Todo feature
            "sh_entmate_theme/static/src/js/todo_widget/todo_widget.js",
            "sh_entmate_theme/static/src/js/todo_widget/todo_widget.xml",
            'sh_entmate_theme/static/src/scss/todo/todo.scss',

            # Language Selector
            "sh_entmate_theme/static/src/js/language_selector/language_selector.js",
            "sh_entmate_theme/static/src/js/language_selector/language_selector.xml",
            'sh_entmate_theme/static/src/scss/language_selector/language_selector.scss',


            # Night Mode
            'sh_entmate_theme/static/src/js/night_mode/night_mode.js',
            'sh_entmate_theme/static/src/js/night_mode/night_mode.xml',
            'sh_entmate_theme/static/src/scss/night_mode/night_mode.scss',

            # Theme Customization
            "sh_entmate_theme/static/src/js/theme_customization/theme_customization.js",
            "sh_entmate_theme/static/src/js/theme_customization/theme_customization.xml",

            #Zoom Widget
            "sh_entmate_theme/static/src/webclient/web_client.js",
            "sh_entmate_theme/static/src/webclient/zoomwidget/zoom_widget.js",
            "sh_entmate_theme/static/src/webclient/zoomwidget/zoom_widget.xml",
            'sh_entmate_theme/static/src/scss/zoom_in_out/zoom_in_out.scss',

            # Disable Auto edit feature
            "sh_entmate_theme/static/src/js/disable_edit/form_controller.js",
            "sh_entmate_theme/static/src/js/disable_edit/x2many_field.js",
            "sh_entmate_theme/static/src/js/disable_edit/form_controller.xml",
            "sh_entmate_theme/static/src/scss/form_controller/form_controller.scss",

            # Expand Collapse
            "sh_entmate_theme/static/src/js/expand_collapse/list_controller.js",
            'sh_entmate_theme/static/src/js/expand_collapse/refresh.xml',

            "sh_entmate_theme/static/src/js/expand_collapse/kanban_controller.js",
            'sh_entmate_theme/static/src/js/expand_collapse/calendar_controller.js',
            'sh_entmate_theme/static/src/scss/refresh_page/refresh_page.scss',

            # recent viewed records
            "sh_entmate_theme/static/src/js/recent_view_records/form_controller.js",
            "sh_entmate_theme/static/src/js/recent_view_records/systray_recent_records.js",
            "sh_entmate_theme/static/src/js/recent_view_records/systray_recent_records.xml",
            "sh_entmate_theme/static/src/scss/recently_viewed_records/recent_records_systray.scss",

            # Global Search
            "sh_entmate_theme/static/src/js/global_search/global_search.js",
            "sh_entmate_theme/static/src/js/global_search/global_search.xml",
            'sh_entmate_theme/static/src/scss/global_search/global_search.scss',


            # quick create
            "sh_entmate_theme/static/src/js/quick_create/quick_create.js",
            "sh_entmate_theme/static/src/js/quick_create/quick_create.xml",
            'sh_entmate_theme/static/src/scss/quick_create/quick_create.scss',
            

            # open record in new tab feature
            'sh_entmate_theme/static/src/js/open_record/open_record.js',
            'sh_entmate_theme/static/src/js/open_record/action_menus.xml',
            'sh_entmate_theme/static/src/js/open_record/list_rendered.xml',

            # Mobile App
            'sh_entmate_theme/static/src/js/mobile_app/user_menu/switch_user.js',
            'sh_entmate_theme/static/src/js/mobile_app/mobile_service.js',
            'sh_entmate_theme/static/src/js/mobile_app/download.js',


            # Quick Menu Feature
            'sh_entmate_theme/static/src/js/bookmark_menu/route.js',
            'sh_entmate_theme/static/src/js/bookmark_menu/quick_menu_custom.js',
            'sh_entmate_theme/static/src/js/bookmark_menu/web_quick_menu.xml',
            'sh_entmate_theme/static/src/scss/quick_menu/quick_menu.scss',


            # attachments in listview
            'sh_entmate_theme/static/src/scss/attachment/attachment.scss',
            "sh_entmate_theme/static/src/js/attachment_in_listview/sh_document_viewer.js",
            "sh_entmate_theme/static/src/js/attachment_in_listview/sh_document_viewer.xml",
            "sh_entmate_theme/static/src/js/attachment_in_listview/list_view_renderer.js",
            "sh_entmate_theme/static/src/js/attachment_in_listview/list_view_renderer.xml",
            # 'web/static/lib/pdfjs/build/pdf.js',
            # 'web/static/lib/pdfjs/build/pdf.worker.js',
            # 'web/static/lib/pdfjs/web/viewer.js',
            # 'sh_entmate_theme/static/src/js/menu_service.js',
            

            # chatter_position
            # 'sh_entmate_theme/static/src/xml/FormView.xml',
            "sh_entmate_theme/static/src/scss/chatter_position/chatter_position.scss",

            # header
            "sh_entmate_theme/static/src/scss/header/header.scss",

            # sidebar styles
            "sh_entmate_theme/static/src/scss/sidebar/sidebar.scss",

            'sh_entmate_theme/static/src/scss/font_family/fonts.scss',

            #common style
            'sh_entmate_theme/static/src/scss/common/common.scss',

            #button_style
            'sh_entmate_theme/static/src/scss/buttons/buttons.scss',

            # background type color/image
            'sh_entmate_theme/static/src/scss/background_style/background_style.scss',

            # separator
            'sh_entmate_theme/static/src/scss/separator/separator.scss',

            # responsive
            # 'sh_entmate_theme/static/src/scss/responsive.scss',

            # form element style
            'sh_entmate_theme/static/src/scss/form_element_style/form_element_style.scss',

            # notification style
            'sh_entmate_theme/static/src/scss/notification/notification.scss',

            # breadcrumb style
            'sh_entmate_theme/static/src/scss/breadcrumb/breadcrumb.scss',

            # checkbox style
            'sh_entmate_theme/static/src/scss/checkbox_style/checkbox_style.scss',

            # radio button style
            'sh_entmate_theme/static/src/scss/radio_btn_style/radio_btn_style.scss',

            # scrollbar style
            'sh_entmate_theme/static/src/scss/scrollbar/scrollbar_style.scss',

            # predefined list view style
            'sh_entmate_theme/static/src/scss/list_view/list_view.scss',

            # icon_style
            'sh_entmate_theme/static/src/scss/fontawesome_icon/font_awesome_light_icon.scss',
            'sh_entmate_theme/static/src/scss/fontawesome_icon/font_awesome_regular_icon.scss',
            'sh_entmate_theme/static/src/scss/fontawesome_icon/font_awesome_std_icon.scss',
            'sh_entmate_theme/static/src/scss/fontawesome_icon/font_awesome_thin_icon.scss',
            "sh_entmate_theme/static/src/scss/odoo_oi_icon/oi_light_icon.scss",
            "sh_entmate_theme/static/src/scss/odoo_oi_icon/oi_regular_icon.scss",
            "sh_entmate_theme/static/src/scss/odoo_oi_icon/oi_thin_icon.scss",

            # App icon styles
            'sh_entmate_theme/static/src/scss/app_icon_style/app_icon_style.scss',

            # progressbar
            'sh_entmate_theme/static/src/scss/nprogress.scss',


            "sh_entmate_theme/static/src/scss/theme_config.scss",
            
            # Menu Structure
            "sh_entmate_theme/static/src/xml/menu.xml",

            # # Odoo standard js
            'sh_entmate_theme/static/src/js/route_service.js',
            # 'sh_entmate_theme/static/src/js/action_service.js',
            # 'sh_entmate_theme/static/src/js/dropdown.js',

            # # On refresh custom js
            # "sh_entmate_theme/static/src/js/On_refresh.js",

            # Sticky
            'sh_entmate_theme/static/src/scss/sticky/sticky_form.scss',
            'sh_entmate_theme/static/src/scss/sticky/sticky_list_inside_form.scss',
            'sh_entmate_theme/static/src/scss/sticky/sticky_list.scss',
            'sh_entmate_theme/static/src/scss/sticky/sticky_pivot.scss',
            # 'sh_entmate_theme/static/src/js/pivot_view_sticky/pivot_sticky_dropdown.js',

            # # Firebase  and bus Notification
            "https://www.gstatic.com/firebasejs/8.4.3/firebase-app.js",
            "https://www.gstatic.com/firebasejs/8.4.3/firebase-messaging.js",
            "sh_entmate_theme/static/src/js/firebase.js",
            # "sh_entmate_theme/static/src/xml/notification.xml",

            #
            # Horizontal/vertical Tab
            'sh_entmate_theme/static/src/scss/tab/tab.scss',
            #
            # # Discuss Chatter
            'sh_entmate_theme/static/src/components/message/message.js',
            "sh_entmate_theme/static/src/xml/message.xml",

            # Multi Tab
            "sh_entmate_theme/static/src/js/multi_tab/navbar.js",
            "sh_entmate_theme/static/src/js/multi_tab/notification.xml",
            "sh_entmate_theme/static/src/js/multi_tab/navtab.js",
            "sh_entmate_theme/static/src/js/multi_tab/navbar.xml",
            "sh_entmate_theme/static/src/js/multi_tab/action_container.js",
            'sh_entmate_theme/static/src/scss/multi_tab_at_control_panel/multi_tab.scss',

            # kanban view style 

            'sh_entmate_theme/static/src/scss/kanban_view_style/kanban_view_style.scss',



        ],

        'web.assets_frontend': [
            'sh_entmate_theme/static/src/scss/login_page_style.scss',
            'sh_entmate_theme/static/src/scss/font_family/fonts.scss',
        ],
        'web._assets_primary_variables': [
          ('after', 'web/static/src/scss/primary_variables.scss', '/sh_entmate_theme/static/src/scss/back_theme_config_main_scss.scss'),
        ],

    },


    'images': [
        'static/description/banner.png',
        'static/description/splash-screen_screenshot.gif'
    ],
    "live_test_url": "https://softhealer.com/support?ticket_type=demo_request",
    "installable": True,
    "application": True,
    "price": 98,
    "currency": "EUR",
    "bootstrap": True
}
