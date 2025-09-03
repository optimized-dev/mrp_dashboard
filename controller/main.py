from odoo import http, fields
from odoo.http import request
from collections import defaultdict
from datetime import datetime, timedelta

class ManufacturingDashboardController(http.Controller):

    @http.route('/manufacturing/dashboard/forecast', type='json', auth='user')
    def get_forecast_data(self):
        current_date = fields.Date.context_today(request.env.user)
        products = request.env['product.template'].search([('sale_ok', '=', True)])
        forecast_data = []
        WidgetConfig = request.env['widget.configuration']
        records = WidgetConfig.search([])

        max_days = max(records.mapped('no_of_days')) if records else 0
        end_date_global = current_date + timedelta(days=max_days)

        all_plans = request.env['mrp.planning'].search([
            ('product_id', 'in', products.ids),
            ('planning_date', '>=', current_date),
            ('planning_date', '<=', end_date_global)
        ])
        plans_map = defaultdict(list)
        for plan in all_plans:
            plans_map[(plan.product_id.id, plan.planning_date)] += [plan.product_uom_qty]

        all_sale_orders = request.env['sale.order.line'].search([
            ('product_id.product_tmpl_id', 'in', products.ids),
            ('order_id.state', 'not in', ['draft', 'cancel']),
            ('order_id.commitment_date', '>=', current_date),
            ('order_id.commitment_date', '<=', end_date_global)
        ])
        sale_map = defaultdict(list)
        for line in all_sale_orders:
            line_date = line.order_id.commitment_date.date()
            sale_map[(line.product_id.product_tmpl_id.id, line_date)].append(line)

        for record in records:
            end_date = current_date + timedelta(days=record.no_of_days)
            sum_planned_qty = 0
            day_wise_forecast = []

            for product in products:
                product_id = product
                current_stock = product.qty_available
                total_planned = 0
                total_sale_order = 0
                total_current_stock = 0

                for day in range(record.no_of_days):
                    date_iter = current_date + timedelta(days=day)

                    planned_qty = sum(plans_map.get((product_id.id, date_iter), []))
                    total_planned += planned_qty
                    sum_planned_qty += planned_qty

                    lines = sale_map.get((product_id.id, date_iter), [])
                    total_demand_qty = sum(l.product_uom_qty for l in lines)
                    total_delivered = sum(l.qty_delivered for l in lines)
                    sale_qty = total_demand_qty - total_delivered
                    total_sale_order += sale_qty

                    current_stock = current_stock + planned_qty - sale_qty
                    total_current_stock += current_stock

                shortfall = total_current_stock - total_sale_order

                day_wise_forecast.append({
                    'product_id': product_id.name,
                    'product_code': product_id.default_code,
                    'planned_qty': "{:,}".format(int(total_planned)),
                    'shortfall': shortfall,
                    'no_of_days': record.no_of_days,
                })

            if day_wise_forecast:
                # Negative shortfall
                negative_shortfall_forecast = [f for f in day_wise_forecast if f['shortfall'] < 0]
                sorted_negative = sorted(
                    negative_shortfall_forecast,
                    key=lambda f: (f['no_of_days'], f['shortfall'])
                )
                for idx, f in enumerate(sorted_negative):
                    f['priority'] = 'High' if idx == 0 else 'Medium' if idx == 1 else 'Low'
                # Non-negative shortfall
                for f in day_wise_forecast:
                    if f['shortfall'] >= 0:
                        f['priority'] = 'Low'
            forecast_data.append({
                'horizon': record.name,
                'planned_qty': "{:,}".format(int(sum_planned_qty)),
                'day_wise_forecast': day_wise_forecast,
                'start_date': current_date,
                'end_date': end_date
            })

        return forecast_data

    @http.route('/manufacturing/dashboard/forecast/date_range', type='json', auth='user')
    def get_forecast_data_with_date_range(self, from_date=None, to_date=None):
        if not from_date or not to_date:
            return []

        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        days_count = (end_date - from_date).days + 1  # Include end_date

        products = request.env['product.template'].search([('sale_ok', '=', True)])
        if not products:
            return []

        all_plans = request.env['mrp.planning'].search([
            ('product_id', 'in', products.ids),
            ('planning_date', '>=', from_date),
            ('planning_date', '<=', end_date)
        ])
        plans_map = defaultdict(list)
        for plan in all_plans:
            plans_map[(plan.product_id.id, plan.planning_date)].append(plan.product_uom_qty)

        all_sale_orders = request.env['sale.order.line'].search([
            ('product_id.product_tmpl_id', 'in', products.ids),
            ('order_id.state', 'not in', ['draft', 'cancel']),
            ('order_id.commitment_date', '>=', from_date),
            ('order_id.commitment_date', '<=', end_date)
        ])
        sale_map = defaultdict(list)
        for line in all_sale_orders:
            line_date = line.order_id.commitment_date.date()
            sale_map[(line.product_id.product_tmpl_id.id, line_date)].append(line)

        horizon_forecast = {
            'horizon': f'{from_date} to {end_date}',
            'start_date': from_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'planned_qty': "0",  # Formatted with commas
            'day_wise_forecast': []
        }

        total_horizon_planned = 0

        for product in products:
            current_stock = product.qty_available
            total_planned = 0
            total_sale_order = 0
            total_current_stock = 0

            for day in range(days_count):
                date_iter = from_date + timedelta(days=day)
                planned_qty = sum(plans_map.get((product.id, date_iter), []))
                total_planned += planned_qty

                lines = sale_map.get((product.id, date_iter), [])
                total_demand_qty = sum(l.product_uom_qty for l in lines)
                total_delivered = sum(l.qty_delivered for l in lines)
                sale_qty = total_demand_qty - total_delivered
                total_sale_order += sale_qty

                current_stock = current_stock + planned_qty - sale_qty
                total_current_stock += current_stock

            shortfall = total_current_stock - total_sale_order

            horizon_forecast['day_wise_forecast'].append({
                'product_id': product.name,
                'product_code': product.default_code,
                'planned_qty': "{:,}".format(int(total_planned)),
                'shortfall': shortfall,
                'no_of_days': days_count,
            })

            total_horizon_planned += total_planned

        # Update horizon total planned with formatted value
        horizon_forecast['planned_qty'] = "{:,}".format(int(total_horizon_planned))

        # Assign priority based on negative shortfall
        day_wise_forecast = horizon_forecast['day_wise_forecast']
        if day_wise_forecast:
            negative_shortfall_forecast = [f for f in day_wise_forecast if f['shortfall'] < 0]
            sorted_negative = sorted(
                negative_shortfall_forecast,
                key=lambda f: (f['no_of_days'], f['shortfall'])
            )
            for idx, f in enumerate(sorted_negative):
                f['priority'] = 'High' if idx == 0 else 'Medium' if idx == 1 else 'Low'

            for f in day_wise_forecast:
                if f.get('priority') is None:
                    f['priority'] = 'Low'

        return [horizon_forecast]

    @http.route('/manufacturing/dashboard/raw_material_forecast', type='json', auth='user')
    def get_raw_material_forecast_data(self):
        WidgetConfig = request.env['widget.configuration']
        records = WidgetConfig.search([])

        current_date = fields.Date.context_today(request.env.user)
        raw_material_forecast_data = []

        # get max date to fetch all relevant plans and purchase orders at once
        max_days = max(records.mapped('no_of_days')) if records else 0
        end_date_global = current_date + timedelta(days=max_days)

        # fetch all relevant production plans
        all_plans = request.env['mrp.planning'].search([
            ('planning_date', '>=', current_date),
            ('planning_date', '<=', end_date_global)
        ])
        # map (product_id, date) -> required qty
        plans_map = defaultdict(list)
        for plan in all_plans:
            for line in plan.mrp_planning_bom_line_ids:
                plans_map[(line.product_id.id, plan.planning_date)].append(line.product_qty)

        # fetch all relevant purchase orders
        all_purchase_orders = request.env['purchase.order.line'].search([
            ('order_id.state', 'not in', ['done', 'cancel', 'draft']),
            ('order_id.date_approve', '>=', current_date),
            ('order_id.date_approve', '<=', end_date_global)
        ])
        purchase_map = defaultdict(list)
        for line in all_purchase_orders:
            line_date = line.order_id.date_approve.date()
            purchase_map[(line.product_id.id, line_date)].append(line)

        for record in records:
            end_date = current_date + timedelta(days=record.no_of_days)
            sum_required_qty = 0
            raw_material_forecast = []

            # get all products in this horizon
            products_in_horizon = set()
            for day in range(record.no_of_days):
                date_iter = current_date + timedelta(days=day)
                for key in plans_map.keys():
                    if key[1] == date_iter:
                        products_in_horizon.add(key[0])

            for product_id in products_in_horizon:
                product = request.env['product.product'].browse(product_id)
                uom_name = product.uom_id.name  # product-specific UOM
                product_current_stock = product.qty_available
                total_required_qty = 0
                total_product_current_stock = 0

                for day in range(record.no_of_days):
                    date_iter = current_date + timedelta(days=day)
                    # required quantity
                    required_qty = sum(plans_map.get((product_id, date_iter), []))
                    total_required_qty += required_qty
                    sum_required_qty += required_qty

                    # purchase order qty
                    lines = purchase_map.get((product_id, date_iter), [])
                    total_po_qty = sum(l.product_qty - l.qty_received for l in lines)

                    # update stock
                    product_current_stock = product_current_stock + total_po_qty - required_qty
                    total_product_current_stock += product_current_stock

                shortfall = total_product_current_stock - total_required_qty

                raw_material_forecast.append({
                    'product_id': product.name,
                    'product_code': product.default_code,
                    'required_qty': "{:,} {}".format(int(total_required_qty), uom_name),
                    'available_qty': "{:,} {}".format(int(total_product_current_stock), uom_name),
                    'shortfall': "{:,} {}".format(int(shortfall), uom_name),
                    'no_of_days': record.no_of_days,
                })

            # calculate priority
            if raw_material_forecast:
                negative_shortfall_raw_forecast = [
                    f for f in raw_material_forecast
                    if int(f['shortfall'].split()[0].replace(',', '')) < 0
                ]
                sorted_negative = sorted(
                    negative_shortfall_raw_forecast,
                    key=lambda f: (f['no_of_days'], int(f['shortfall'].split()[0].replace(',', '')))
                )
                for idx, f in enumerate(sorted_negative):
                    f['priority'] = 'High' if idx == 0 else 'Medium' if idx == 1 else 'Low'
                for f in raw_material_forecast:
                    if 'priority' not in f:
                        f['priority'] = 'Low'

            raw_material_forecast_data.append({
                'horizon': record.name,
                'planned_qty': "{:,}".format(int(sum_required_qty)),
                'raw_material_forecast': raw_material_forecast,
                'start_date': current_date,
                'end_date': end_date
            })

        return raw_material_forecast_data

    @http.route('/manufacturing/dashboard/raw_forecast/date_range', type='json', auth='user')
    def get_raw_forecast_data_with_date_range(self, from_date=None, to_date=None):
        if not from_date or not to_date:
            return []

        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        days_count = (end_date - from_date).days + 1  # Include end_date

        raw_material_forecast_data = []

        # fetch all planning and purchase data in one go
        all_plans = request.env['mrp.planning'].search([
            ('planning_date', '>=', from_date),
            ('planning_date', '<=', end_date)
        ])
        plans_map = defaultdict(list)
        for plan in all_plans:
            for line in plan.mrp_planning_bom_line_ids:
                plans_map[(line.product_id.id, plan.planning_date)].append(line.product_qty)

        all_purchase_orders = request.env['purchase.order.line'].search([
            ('order_id.state', 'not in', ['done', 'cancel', 'draft']),
            ('order_id.date_approve', '>=', from_date),
            ('order_id.date_approve', '<=', end_date)
        ])
        purchase_map = defaultdict(list)
        for line in all_purchase_orders:
            line_date = line.order_id.date_approve.date()
            purchase_map[(line.product_id.id, line_date)].append(line)

        # process products for this horizon
        sum_required_qty = 0
        raw_material_forecast = []

        # get all products appearing in this horizon
        products_in_horizon = set()
        for key in plans_map.keys():
            if from_date <= key[1] <= end_date:
                products_in_horizon.add(key[0])

        for product_id in products_in_horizon:
            product = request.env['product.product'].browse(product_id)
            uom_name = product.uom_id.name
            product_current_stock = product.qty_available
            total_required_qty = 0
            total_product_current_stock = 0

            for day in range(days_count):
                date_iter = from_date + timedelta(days=day)
                # required quantity
                required_qty = sum(plans_map.get((product_id, date_iter), []))
                total_required_qty += required_qty
                sum_required_qty += required_qty

                # purchase order qty
                lines = purchase_map.get((product_id, date_iter), [])
                total_po_qty = sum(l.product_qty - l.qty_received for l in lines)

                # update stock
                product_current_stock = product_current_stock + total_po_qty - required_qty
                total_product_current_stock += product_current_stock

            shortfall = total_product_current_stock - total_required_qty

            raw_material_forecast.append({
                'product_id': product.name,
                'product_code': product.default_code,
                'required_qty': "{:,} {}".format(int(total_required_qty), uom_name),
                'available_qty': "{:,} {}".format(int(total_product_current_stock), uom_name),
                'shortfall': "{:,} {}".format(int(shortfall), uom_name),
                'no_of_days': days_count,
            })

        # calculate priority
        if raw_material_forecast:
            negative_shortfall_raw_forecast = [
                f for f in raw_material_forecast
                if int(f['shortfall'].split()[0].replace(',', '')) < 0
            ]
            sorted_negative = sorted(
                negative_shortfall_raw_forecast,
                key=lambda f: (f['no_of_days'], int(f['shortfall'].split()[0].replace(',', '')))
            )
            for idx, f in enumerate(sorted_negative):
                f['priority'] = 'High' if idx == 0 else 'Medium' if idx == 1 else 'Low'
            for f in raw_material_forecast:
                if 'priority' not in f:
                    f['priority'] = 'Low'

        # append **one record per horizon**
        raw_material_forecast_data.append({
            'horizon': f'{from_date} to {end_date}',
            'planned_qty': "{:,}".format(int(sum_required_qty)),
            'raw_material_forecast': raw_material_forecast,
            'start_date': from_date,
            'end_date': end_date
        })

        return raw_material_forecast_data

