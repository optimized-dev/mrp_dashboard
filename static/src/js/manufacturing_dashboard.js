odoo.define('manufacturing_dashboard.manufacturing_dashboard', function (require) {
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const rpc = require('web.rpc');
    const core = require('web.core');

    const ManufacturingDashboardTag = AbstractAction.extend({
        template: 'manufacturing_dashboard',

        start: async function () {
            let self = this;

            // Default select Planning tab
            this.$('.mrp-nav-item').removeClass('active');
            this.$('.mrp-nav-item:contains("Planning")').addClass('active');

            // Show Planning widget container
            this.$('#widgets_container').closest('.mrp-dashboard-widget-section').show();

            // Setup tabs
            this._setup_tabs();

            // Setup search button
            this._setup_search();

            // Initial render
            await this._render_widgets();
        },

        _setup_tabs: function () {
            let self = this;
            this.$('.mrp-nav-item').on('click', function (ev) {
                ev.preventDefault();
                let $clicked = $(this);
                self.$('.mrp-nav-item').removeClass('active');
                $clicked.addClass('active');
                self.$('#widgets_container').closest('.mrp-dashboard-widget-section')
                    .toggle($clicked.text().trim() === "Planning");
            });
        },

        _setup_search: function () {
            let self = this;
            this.$('#global_search_btn').on('click', async function () {
                let from_date = self.$('#global_from_date').val();
                let to_date = self.$('#global_to_date').val();
                if (!from_date || !to_date) return;

                // 1️⃣ Fetch Production Schedule Data
                let production_data = await self._rpc({
                    route: '/manufacturing/dashboard/forecast/date_range',
                    params: { from_date, to_date }
                });

                // 2️⃣ Fetch Material Readiness Data
                let material_data = await self._rpc({
                    route: '/manufacturing/dashboard/raw_forecast/date_range',
                    params: { from_date, to_date }
                });

                self._render_widgets(production_data, material_data);
            });
        },

        _render_widgets: async function (production_data = null, material_data = null) {
            let self = this;

            // Fetch data if not provided
            if (!production_data) {
                production_data = await self._rpc({ route: '/manufacturing/dashboard/forecast' });
            }
            if (!material_data) {
                material_data = await self._rpc({ route: '/manufacturing/dashboard/raw_material_forecast' });
            }

            let table_html = `<div class="widget-area">`;

            // 1️⃣ Production Schedule Widget
            table_html += `
                <div id="widget_production_schedule" class="mrp-widget-card">
                    <h3 class="mrp-widget-title">Upcoming Production Schedule</h3>
                    <table class="mrp-dashboard-table">
                        <thead>
                            <tr>
                                <th>Horizon</th>
                                <th>Planned Qty</th>
                            </tr>
                        </thead>
                        <tbody>`;
            production_data.forEach(item => {
                table_html += `
                    <tr class="forecast-row" data-horizon='${JSON.stringify(item)}'>
                        <td>${item.horizon || '-'}</td>
                        <td>${item.planned_qty || 0}</td>
                    </tr>`;
            });
            table_html += `</tbody></table></div>`;

            // 2️⃣ Material Readiness Overview Widget
            table_html += `
                <div id="widget_material_readiness" class="mrp-widget-card">
                    <h3 class="mrp-widget-title">Material Readiness Overview</h3>
                    <table class="mrp-dashboard-table">
                        <thead>
                            <tr>
                                <th>Horizon</th>
                                <th>Required Qty</th>
                            </tr>
                        </thead>
                        <tbody>`;
            material_data.forEach(item => {
                table_html += `
                    <tr class="raw-material-row" data-horizon='${JSON.stringify(item)}'>
                        <td>${item.horizon || '-'}</td>
                        <td>${item.planned_qty || 0}</td>
                    </tr>`;
            });
            table_html += `</tbody></table></div></div>`;

            self.$('#widgets_container').html(table_html);

            // Row click handlers
            self.$('.forecast-row').on('click', function () {
                let horizon_data = $(this).data('horizon');
                self._show_horizon_popup(horizon_data, false);
            });
            self.$('.raw-material-row').on('click', function () {
                let horizon_data = $(this).data('horizon');
                self._show_horizon_popup(horizon_data, true);
            });
        },

        _show_horizon_popup: function(horizon_data, is_material = false) {
            let header_html = `<h3>${horizon_data.horizon}</h3>`;
            if (horizon_data.start_date && horizon_data.end_date) {
                header_html += `<p>Start Date: ${horizon_data.start_date} | End Date: ${horizon_data.end_date}</p>`;
            }

            let table_header = is_material ? `
                <tr>
                    <th>Material Code</th>
                    <th>Material Name</th>
                    <th>Required Qty</th>
                    <th>Available Qty</th>
                </tr>` : `
                <tr>
                    <th>Product Name</th>
                    <th>Product Code</th>
                    <th>Planned Qty</th>
                    <th>Priority</th>
                </tr>`;

            let table_rows = '';
            if (is_material) {
                horizon_data.raw_material_forecast.forEach(item => {
                    table_rows += `
                        <tr>
                            <td>${item.product_code}</td>
                            <td>${item.product_id}</td>
                            <td>${item.required_qty}</td>
                            <td>${item.available_qty}</td>
                        </tr>`;
                });
            } else {
                horizon_data.day_wise_forecast.forEach(item => {
                    let priority_style = '';
                    if (item.priority?.toLowerCase() === 'high') priority_style = 'color: red; font-weight: bold;';
                    else if (item.priority?.toLowerCase() === 'medium') priority_style = 'color: orange; font-weight: bold;';
                    else if (item.priority?.toLowerCase() === 'low') priority_style = 'color: green; font-weight: bold;';

                    table_rows += `
                        <tr>
                            <td>${item.product_id}</td>
                            <td>${item.product_code}</td>
                            <td>${item.planned_qty}</td>
                            <td style="${priority_style}">${item.priority || ''}</td>
                        </tr>`;
                });
            }

            let popup_html = `
                <div class="forecast-popup">
                    <div class="popup-content">
                        <div class="popup-header">
                            ${header_html}
                            <button class="popup-close">✖</button>
                        </div>
                        <div class="popup-table-wrapper">
                            <table class="mrp-dashboard-table">
                                <thead>${table_header}</thead>
                                <tbody>${table_rows}</tbody>
                            </table>
                        </div>
                    </div>
                </div>`;

            $('.forecast-popup').remove();
            $('body').append(popup_html);

            $('.popup-close').on('click', function() { $('.forecast-popup').remove(); });
        }
    });

    core.action_registry.add('manufacturing_dashboard_tag', ManufacturingDashboardTag);
    return ManufacturingDashboardTag;
});
