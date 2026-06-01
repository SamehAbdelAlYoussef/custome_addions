/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

class DynamicAccountReport extends Component {
    static template = "dynamic_accounting_reports.MainReport";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            reportData: null,
            loading: true,
            reportId: null,
            reportName: "",
            lines: [],
            columns: [],
            filters: {},
            unfoldedLines: new Set(),
            dateRange: "this_year",
            dateFrom: "",
            dateTo: "",
            showComparison: false,
            comparisonType: "previous_period",
            comparisonNumber: 1,
            selectedJournals: [],
            selectedAccounts: [],
            selectedPartners: [],
            selectedAccountType: "all",
            selectedCompanies: [],
            selectedAnalyticAccounts: [],
            selectedAnalyticPlans: [],
            allEntries: false,
            unfoldAll: false,
            journalOptions: [],
            accountOptions: [],
            partnerOptions: [],
            companyOptions: [],
            analyticAccountOptions: [],
            analyticPlanOptions: [],
            searchText: "",
            journalSearch: "",
            accountSearch: "",
            partnerSearch: "",
            companySearch: "",
            analyticAccountSearch: "",
            analyticPlanSearch: "",
            activeDropdown: null,
        });

        onWillStart(async () => {
            const params = this.props.action?.params || this.props.action?.context || {};
            this.state.reportId = params.report_id || this.props.action?.context?.report_id;
            if (this.state.reportId) {
                await this._loadReport();
            }
        });

        onMounted(() => {
            const el = this.__owl__.bdom?.el || document.querySelector('.o_ent_report');
            if (el) {
                let parent = el.parentElement;
                while (parent && parent !== document.body) {
                    const style = window.getComputedStyle(parent);
                    const overflow = style.overflow + style.overflowY;
                    if (overflow.includes('hidden') || overflow.includes('clip')) {
                        parent.style.overflow = 'auto';
                    }
                    if (style.display === 'flex' || style.display === 'inline-flex') {
                        if (parent.classList.contains('o_action_manager') ||
                            parent.classList.contains('o_action') ||
                            parent.classList.contains('o_content')) {
                            parent.style.overflow = 'auto';
                        }
                    }
                    parent = parent.parentElement;
                }
            }
        });
    }

    // ====================================================================
    // DATA
    // ====================================================================

    async _loadReport() {
        this.state.loading = true;
        try {
            const options = this._buildOptions();
            const data = await rpc("/dynamic_reports/get_report_data", {
                report_id: this.state.reportId,
                options: options,
            });
            if (data.error) {
                this.notification.add(data.error, { type: "danger" });
                return;
            }
            this.state.reportData = data;
            this.state.reportName = data.report_name;
            this.state.lines = data.lines || [];
            this.state.columns = data.columns || [];
            this.state.filters = data.filters || {};
            if (!this.state.dateFrom && data.date_from) this.state.dateFrom = data.date_from;
            if (!this.state.dateTo && data.date_to) this.state.dateTo = data.date_to;
            await this._loadFilterOptions();
        } catch (error) {
            console.error("Error loading report:", error);
            this.notification.add(_t("Error loading report"), { type: "danger" });
        }
        this.state.loading = false;
    }

    async _loadFilterOptions() {
        const f = this.state.filters;
        const cids = this.state.selectedCompanies.length ? this.state.selectedCompanies : null;
        try {
            if (f.journals && !this.state.journalOptions.length) {
                this.state.journalOptions = await rpc("/dynamic_reports/get_filter_data", {
                    report_id: this.state.reportId, filter_type: "journals", company_ids: cids,
                });
            }
            if (f.accounts && !this.state.accountOptions.length) {
                this.state.accountOptions = await rpc("/dynamic_reports/get_filter_data", {
                    report_id: this.state.reportId, filter_type: "accounts", company_ids: cids,
                });
            }
            if (f.partners && !this.state.partnerOptions.length) {
                this.state.partnerOptions = await rpc("/dynamic_reports/get_filter_data", {
                    report_id: this.state.reportId, filter_type: "partners", company_ids: cids,
                });
            }
            if (f.multi_company && !this.state.companyOptions.length) {
                this.state.companyOptions = await rpc("/dynamic_reports/get_filter_data", {
                    report_id: this.state.reportId, filter_type: "companies",
                });
            }
            if (f.analytic && !this.state.analyticAccountOptions.length) {
                this.state.analyticAccountOptions = await rpc("/dynamic_reports/get_filter_data", {
                    report_id: this.state.reportId, filter_type: "analytic_accounts", company_ids: cids,
                });
            }
            if (f.analytic && !this.state.analyticPlanOptions.length) {
                this.state.analyticPlanOptions = await rpc("/dynamic_reports/get_filter_data", {
                    report_id: this.state.reportId, filter_type: "analytic_plans", company_ids: cids,
                });
            }
        } catch (e) { console.warn("Filter load error", e); }
    }

    _buildOptions() {
        const o = {
            date_range: this.state.dateRange,
            date_from: this.state.dateFrom || false,
            date_to: this.state.dateTo || false,
            all_entries: this.state.allEntries,
            unfold_all: this.state.unfoldAll,
            unfolded_lines: Array.from(this.state.unfoldedLines),
        };
        if (this.state.showComparison) {
            o.comparison = { enabled: true, type: this.state.comparisonType, number: this.state.comparisonNumber };
        }
        if (this.state.selectedJournals.length) o.journal_ids = this.state.selectedJournals;
        if (this.state.selectedAccounts.length) o.account_ids = this.state.selectedAccounts;
        if (this.state.selectedPartners.length) o.partner_ids = this.state.selectedPartners;
        if (this.state.selectedAccountType !== 'all') o.account_type = this.state.selectedAccountType;
        if (this.state.selectedCompanies.length) o.company_ids = this.state.selectedCompanies;
        if (this.state.selectedAnalyticAccounts.length) o.analytic_account_ids = this.state.selectedAnalyticAccounts;
        if (this.state.selectedAnalyticPlans.length) o.analytic_plan_ids = this.state.selectedAnalyticPlans;
        return o;
    }

    // ====================================================================
    // LINE INTERACTIONS
    // ====================================================================

    async onToggleLine(lineId) {
        if (this.state.unfoldedLines.has(lineId)) {
            this.state.unfoldedLines.delete(lineId);
            const collectChildren = (parentId) => {
                for (const l of this.state.lines) {
                    if (l.parent_id === parentId) {
                        this.state.unfoldedLines.delete(l.id);
                        collectChildren(l.id);
                    }
                }
            };
            collectChildren(lineId);
            this.state.lines = this.state.lines.filter(l => {
                if (l.parent_id !== lineId) return true;
                if (l.id && (l.id.startsWith('move_line_') || l.id.startsWith('initial_'))) return false;
                return true;
            });
        } else {
            this.state.unfoldedLines.add(lineId);
            const hasPreloadedChildren = this.state.lines.some(l => l.parent_id === lineId);
            if (!hasPreloadedChildren) {
                try {
                    const childLines = await rpc("/dynamic_reports/get_unfolded_lines", {
                        report_id: this.state.reportId, line_id: lineId, options: this._buildOptions(),
                    });
                    const idx = this.state.lines.findIndex(l => l.id === lineId);
                    if (idx >= 0 && childLines.length) {
                        const newLines = [...this.state.lines];
                        newLines.splice(idx + 1, 0, ...childLines);
                        this.state.lines = newLines;
                    }
                } catch (e) { console.error("Unfold error:", e); }
            }
        }
    }

    onClickMoveLine(moveId) {
        if (moveId) {
            this.action.doAction({
                type: "ir.actions.act_window", res_model: "account.move",
                res_id: moveId, views: [[false, "form"]], target: "current",
            });
        }
    }

    // ====================================================================
    // DROPDOWNS
    // ====================================================================

    toggleDropdown(name) {
        if (this.state.activeDropdown === name) {
            this.state.activeDropdown = null;
        } else {
            this.state.activeDropdown = name;
            this.state.journalSearch = "";
            this.state.accountSearch = "";
            this.state.partnerSearch = "";
            this.state.companySearch = "";
        }
    }

    closeDropdowns() { this.state.activeDropdown = null; }

    // ====================================================================
    // FILTER ACTIONS
    // ====================================================================

    async setDateRange(range) {
        this.state.dateRange = range; this.state.dateFrom = ""; this.state.dateTo = "";
        this.state.activeDropdown = null; await this._loadReport();
    }
    async onChangeDateFrom(ev) {
        this.state.dateFrom = ev.target.value; this.state.dateRange = "custom";
        if (this.state.dateFrom && this.state.dateTo) await this._loadReport();
    }
    async onChangeDateTo(ev) {
        this.state.dateTo = ev.target.value; this.state.dateRange = "custom";
        if (this.state.dateTo) await this._loadReport();
    }
    async toggleComparison() { this.state.showComparison = !this.state.showComparison; await this._loadReport(); }
    async setComparisonType(type) { this.state.comparisonType = type; await this._loadReport(); }
    async setComparisonNumber(ev) { this.state.comparisonNumber = parseInt(ev.target.value) || 1; await this._loadReport(); }
    async toggleAllEntries() { this.state.allEntries = !this.state.allEntries; this.state.activeDropdown = null; await this._loadReport(); }
    async toggleUnfoldAll() { this.state.unfoldAll = !this.state.unfoldAll; this.state.unfoldedLines.clear(); this.state.activeDropdown = null; await this._loadReport(); }

    async toggleJournal(journalId) {
        const idx = this.state.selectedJournals.indexOf(journalId);
        if (idx >= 0) this.state.selectedJournals.splice(idx, 1);
        else this.state.selectedJournals.push(journalId);
        await this._loadReport();
    }
    async togglePartner(partnerId) {
        const idx = this.state.selectedPartners.indexOf(partnerId);
        if (idx >= 0) this.state.selectedPartners.splice(idx, 1);
        else this.state.selectedPartners.push(partnerId);
        await this._loadReport();
    }
    async toggleAccount(accountId) {
        const idx = this.state.selectedAccounts.indexOf(accountId);
        if (idx >= 0) this.state.selectedAccounts.splice(idx, 1);
        else this.state.selectedAccounts.push(accountId);
        await this._loadReport();
    }
    async toggleCompany(companyId) {
        const idx = this.state.selectedCompanies.indexOf(companyId);
        if (idx >= 0) this.state.selectedCompanies.splice(idx, 1);
        else this.state.selectedCompanies.push(companyId);
        // Reset dependent filters since they depend on selected companies
        this.state.journalOptions = [];
        this.state.partnerOptions = [];
        this.state.selectedJournals = [];
        this.state.selectedPartners = [];
        this.state.selectedAccountType = "all";
        await this._loadReport();
    }
    async toggleAnalyticAccount(aaId) {
        const idx = this.state.selectedAnalyticAccounts.indexOf(aaId);
        if (idx >= 0) this.state.selectedAnalyticAccounts.splice(idx, 1);
        else this.state.selectedAnalyticAccounts.push(aaId);
        await this._loadReport();
    }
    async toggleAnalyticPlan(planId) {
        const idx = this.state.selectedAnalyticPlans.indexOf(planId);
        if (idx >= 0) this.state.selectedAnalyticPlans.splice(idx, 1);
        else this.state.selectedAnalyticPlans.push(planId);
        await this._loadReport();
    }

    // Search handlers
    onJournalSearch(ev) { this.state.journalSearch = ev.target.value.toLowerCase(); }
    onAccountSearch(ev) { this.state.accountSearch = ev.target.value.toLowerCase(); }
    onPartnerSearch(ev) { this.state.partnerSearch = ev.target.value.toLowerCase(); }
    onCompanySearch(ev) { this.state.companySearch = ev.target.value.toLowerCase(); }
    onAnalyticAccountSearch(ev) { this.state.analyticAccountSearch = ev.target.value.toLowerCase(); }
    onAnalyticPlanSearch(ev) { this.state.analyticPlanSearch = ev.target.value.toLowerCase(); }
    onSearchChange(ev) { this.state.searchText = ev.target.value.toLowerCase(); }
    async onAccountTypeChange(ev) { this.state.selectedAccountType = ev.target.value; await this._loadReport(); }

    // Clear handlers
    async clearJournalFilter() { this.state.selectedJournals = []; await this._loadReport(); }
    async clearAccountFilter() { this.state.selectedAccounts = []; await this._loadReport(); }
    async clearPartnerFilter() { this.state.selectedPartners = []; await this._loadReport(); }
    async clearCompanyFilter() { this.state.selectedCompanies = []; this.state.journalOptions = []; await this._loadReport(); }
    async clearAnalyticAccountFilter() { this.state.selectedAnalyticAccounts = []; await this._loadReport(); }
    async clearAnalyticPlanFilter() { this.state.selectedAnalyticPlans = []; await this._loadReport(); }

    // ====================================================================
    // EXPORTS
    // ====================================================================

    onExportXlsx() {
        const options = JSON.stringify(this._buildOptions());
        window.open(`/dynamic_reports/export_xlsx?report_id=${this.state.reportId}&options=${encodeURIComponent(options)}`, "_blank");
    }
    onExportPdf() {
        const options = JSON.stringify(this._buildOptions());
        window.open(`/dynamic_reports/export_pdf?report_id=${this.state.reportId}&options=${encodeURIComponent(options)}`, "_blank");
    }

    // ====================================================================
    // COMPUTED — Filtered dropdown lists with search
    // ====================================================================

    get filteredLines() {
        if (!this.state.searchText) return this.state.lines;
        return this.state.lines.filter(l => !l.name || l.name.toLowerCase().includes(this.state.searchText));
    }

    get filteredJournals() {
        if (!this.state.journalSearch) return this.state.journalOptions;
        return this.state.journalOptions.filter(j =>
            (j.name || '').toLowerCase().includes(this.state.journalSearch) ||
            (j.code || '').toLowerCase().includes(this.state.journalSearch)
        );
    }

    get filteredAccounts() {
        if (!this.state.accountSearch) return this.state.accountOptions;
        return this.state.accountOptions.filter(a =>
            (a.name || '').toLowerCase().includes(this.state.accountSearch) ||
            (a.code || '').toLowerCase().includes(this.state.accountSearch)
        );
    }

    get filteredPartners() {
        if (!this.state.partnerSearch) return this.state.partnerOptions;
        return this.state.partnerOptions.filter(p =>
            (p.name || '').toLowerCase().includes(this.state.partnerSearch)
        );
    }

    get filteredCompanies() {
        if (!this.state.companySearch) return this.state.companyOptions;
        return this.state.companyOptions.filter(c =>
            (c.name || '').toLowerCase().includes(this.state.companySearch)
        );
    }

    get filteredAnalyticAccounts() {
        if (!this.state.analyticAccountSearch) return this.state.analyticAccountOptions;
        return this.state.analyticAccountOptions.filter(a =>
            (a.name || '').toLowerCase().includes(this.state.analyticAccountSearch)
        );
    }

    get filteredAnalyticPlans() {
        if (!this.state.analyticPlanSearch) return this.state.analyticPlanOptions;
        return this.state.analyticPlanOptions.filter(p =>
            (p.name || '').toLowerCase().includes(this.state.analyticPlanSearch)
        );
    }

    get displayColumns() {
        const rt = this.state.reportData?.report_type;
        if (rt === "trial_balance") return [
            {name: _t("Initial Debit")}, {name: _t("Initial Credit")},
            {name: _t("Debit")}, {name: _t("Credit")},
            {name: _t("End Debit")}, {name: _t("End Credit")},
        ];
        if (rt === "aged_receivable" || rt === "aged_payable") return [
            {name: _t("Not Due")}, {name: _t("1-30")}, {name: _t("31-60")},
            {name: _t("61-90")}, {name: _t("91-120")}, {name: _t("Older")}, {name: _t("Total")},
        ];
        if (rt === "partner_ledger") return [
            {name: _t("Initial Balance")}, {name: _t("Debit")}, {name: _t("Credit")}, {name: _t("Balance")},
        ];
        if (rt === "general_ledger") return [
            {name: _t("Debit")}, {name: _t("Credit")}, {name: _t("Balance")},
        ];
        if (rt === "analytic_account" || rt === "analytic_plan") return [
            {name: _t("Debit")}, {name: _t("Credit")}, {name: _t("Balance")},
        ];
        return this.state.columns;
    }

    get dateLabel() {
        if (this.state.filters.use_date_to_only) return _t("As of ") + (this.state.dateTo || '');
        return (this.state.dateFrom || '') + " - " + (this.state.dateTo || '');
    }

    get dateRangeLabel() {
        const labels = {
            this_month: _t("This Month"), this_quarter: _t("This Quarter"),
            this_year: _t("This Financial Year"), last_month: _t("Last Month"),
            last_quarter: _t("Last Quarter"), last_year: _t("Last Financial Year"),
            custom: _t("Custom"),
        };
        return labels[this.state.dateRange] || _t("This Financial Year");
    }

    get companyLabel() {
        if (!this.state.selectedCompanies.length) return _t("All Companies");
        if (this.state.selectedCompanies.length === 1) {
            const c = this.state.companyOptions.find(x => x.id === this.state.selectedCompanies[0]);
            return c ? c.name : "1 " + _t("Company");
        }
        return this.state.selectedCompanies.length + " " + _t("Companies");
    }

    getLineClasses(line) {
        let cls = ["o_ent_line"];
        if (line.class) cls.push(line.class);
        if (line.level !== undefined) cls.push(`o_ent_level_${line.level}`);
        if (line.is_title) cls.push("o_ent_title");
        if (line.is_total) cls.push("o_ent_total");
        if (line.parent_id) cls.push("o_ent_child");
        return cls.join(" ");
    }

    isLineVisible(line) {
        if (line.parent_id) return this.state.unfoldedLines.has(line.parent_id) || this.state.unfoldAll;
        return true;
    }

    isJournalSelected(id) { return this.state.selectedJournals.includes(id); }
    isPartnerSelected(id) { return this.state.selectedPartners.includes(id); }
    isAccountSelected(id) { return this.state.selectedAccounts.includes(id); }
    isCompanySelected(id) { return this.state.selectedCompanies.includes(id); }
    isAnalyticAccountSelected(id) { return this.state.selectedAnalyticAccounts.includes(id); }
    isAnalyticPlanSelected(id) { return this.state.selectedAnalyticPlans.includes(id); }

    formatVal(val) {
        if (val === undefined || val === null) return '0.00';
        return parseFloat(val).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
}

registry.category("actions").add("dynamic_account_report", DynamicAccountReport);
