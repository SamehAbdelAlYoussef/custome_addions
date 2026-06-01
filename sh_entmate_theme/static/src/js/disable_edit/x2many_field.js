/** @odoo-module **/

import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

import { patch } from "@web/core/utils/patch";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain } from "@web/model/relational_model/utils";
import {
    useActiveActions,
    useAddInlineRecord,
    useOpenX2ManyRecord,
    useSelectCreate,
    useX2ManyCrud,
} from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { computeViewClassName } from "@web/views/utils";
import { ViewButton } from "@web/views/view_button/view_button";

import { Component } from "@odoo/owl";


patch(X2ManyField.prototype, {
      setup() {
        this.field = this.props.record.fields[this.props.name];
        const { saveRecord, updateRecord, removeRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        this.archInfo = this.props.views?.[this.props.viewMode] || {};
        const classes = this.props.viewMode
            ? ["o_field_x2many", `o_field_x2many_${this.props.viewMode}`]
            : ["o_field_x2many"];
        this.className = computeViewClassName(this.props.viewMode, this.archInfo.xmlDoc, classes);

        const { activeActions, creates } = this.archInfo;
        if (this.props.viewMode === "kanban") {
            this.creates = creates.length
                ? creates
                : [
                      {
                          type: "create",
                          string: this.props.addLabel || _t("Add"),
                          class: "o-kanban-button-new",
                      },
                  ];
        }
        const subViewActiveActions = activeActions;
        this.activeActions = useActiveActions({
            crudOptions: Object.assign({}, this.props.crudOptions, {
                onDelete: removeRecord,
                /*edit: this.props.record.isInEdition,*/
                edit: () => this.props.record.isInEdition,
            }),
            fieldType: this.isMany2Many ? "many2many" : "one2many",
            subViewActiveActions,
            getEvalParams: (props) => {
                return {
                    evalContext: props.record.evalContext,
                    readonly: props.readonly,
                };
            },
        });

        this.addInLine = useAddInlineRecord({
            addNew: (...args) => this.list.addNewRecord(...args),
        });

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord,
            updateRecord,
            isMany2Many: this.isMany2Many,
        });
        this._openRecord = (params) => {
            const activeElement = document.activeElement;
            openRecord({
                ...params,
                onClose: () => {
                    if (activeElement) {
                        activeElement.focus();
                    }
                },
            });
        };
        this.canOpenRecord =
            this.props.viewMode === "list"
                ? !(this.archInfo.editable || this.props.editable)
                : true;

        const selectCreate = useSelectCreate({
            resModel: this.props.record.data[this.props.name].resModel,
            activeActions: this.activeActions,
            onSelected: (resIds) => saveRecord(resIds),
            onCreateEdit: ({ context }) => this._openRecord({ context }),
            onUnselect: this.isMany2Many ? undefined : () => saveRecord(),
        });

        this.selectCreate = (params) => {
            const p = Object.assign({}, params);
            const currentIds = this.props.record.data[this.props.name].currentIds.filter(
                (id) => typeof id === "number"
            );
            p.domain = [...(p.domain || []), "!", ["id", "in", currentIds]];
            return selectCreate(p);
        };
        this.action = useService("action");
    }


});

