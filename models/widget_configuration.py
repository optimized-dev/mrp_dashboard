from odoo import api, fields, models , _
from datetime import timedelta

class WidgetConfiguration(models.Model):
    _name = 'widget.configuration'
    _description = 'Widget Configuration'

    name = fields.Char('Name')
    no_of_days = fields.Integer(string='No of Days')
    widget = fields.Selection(
        [
            ('production_plan', 'Upcoming Production Schedule'),
            ('raw_materials', 'Raw Materials Forecast'),
            ('finished_goods', 'Finished Goods Forecast'),
            ('future_delivery', 'Future Delivery Planning'),
        ],
        string="Widget",
        required=True,
        default='raw_materials',
    )

    @api.model
    def get_upcoming_production_schedule(self):
        current_date = fields.Date.context_today(self)
        products = self.env['product.template'].search([('sale_ok', '=', True)])
        forecast_data = []
        for record in self:
            if record.no_of_days > 0:
                sum_planned_qty = 0
                for product in products:
                    product_id = self.env['product.template'].browse(product.id)
                    current_stock = product_id.qty_available

                    for day in range(record.no_of_days):
                        date = current_date + timedelta(days=day)

                        production_plans = self.env['mrp.planning'].search([
                            ('product_id', '=', product_id.id),
                            ('planning_date', '=', date)
                        ])
                        planned_qty = sum(production_plans.mapped('product_uom_qty'))
                        sum_planned_qty += planned_qty

                        sale_orders = self.env['sale.order.line'].search([
                            ('product_id', '=', product_id.id),
                            ('order_id.state', 'in', ['approve']),
                            ('order_id.commitment_date', '=', date)
                        ])
                        sale_qty = sum(sale_orders.mapped('product_uom_qty'))

                        delivery_orders = self.env['stock.move'].search([
                            ('product_id', '=', product_id.id),
                            ('date', '=', date)
                        ])
                        delivery_qty = sum(delivery_orders.mapped('product_uom_qty'))

                        current_stock = current_stock + planned_qty - sale_qty - delivery_qty

                # Add only summary for the table
                forecast_data.append({
                    'horizon': record.name,  # This will be the first column
                    'planned_qty': sum_planned_qty  # This will be the second column
                })
        print(forecast_data)

        return forecast_data

    def get_data(self):
        current_date = fields.Date.context_today(self)
        products = self.env['product.template'].search([('sale_ok', '=', True)])
        for product in products:
            product_id = self.env['product.template'].browse(product.id)
            day_wise_forecast = []
            for day in range(7):
                current_stock = product_id.qty_available
                date = current_date + timedelta(days=day)
                production_plans = self.env['mrp.planning'].search([
                    ('product_id', '=', product_id.id),
                    ('planning_date', '=', date)
                ])
                planned_qty = sum(production_plans.mapped('product_uom_qty'))

                # Daily Sales Orders
                sale_orders = self.env['sale.order.line'].search([
                    ('product_id', '=', product_id.id),
                    ('order_id.state', 'in', ['approve']),
                    ('order_id.commitment_date', '=', date)
                ])
                sale_qty = sum(sale_orders.mapped('product_uom_qty'))

                # Daily Delivery Orders
                delivery_orders = self.env['stock.move'].search([
                    ('product_id', '=', product_id.id),
                    ('date', '=', date)
                ])
                delivery_qty = sum(delivery_orders.mapped('product_uom_qty'))

                # Daily forecast stock update
                current_stock = current_stock + planned_qty - sale_qty - delivery_qty
                if current_stock < sale_qty:
                    priority = "High"
                elif current_stock < (sale_qty * 2):
                    priority = "Medium"
                else:
                    priority = "Low"
                day_wise_forecast.append({
                    'date': date,
                    'product': product.name,
                    'forecast_qty': current_stock,
                    'production': planned_qty,
                    'sales': sale_qty,
                    'delivery': delivery_qty,
                    'priority': priority
                })
            print(day_wise_forecast)








