from odoo import models, fields, api

class WidgetData(models.TransientModel):
    _name = 'widget.data'
    _description = 'Widget Data'

    name = fields.Char('Name')
    product_id = fields.Many2one('product.template', string='Product')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    planned_qty = fields.Float('Planned Quantity')
    sale_order_qty = fields.Float('Sale Order Quantity')
    delivery_order_qty = fields.Float('Delivery Order Quantity')
    current_stock = fields.Float('Current Stock')

    @api.model
    def default_get(self, fields_list):
        res = super(WidgetData, self).default_get(fields_list)
        forecast_data = self.env.context.get('default_forecast_data')
        if forecast_data:
            # Take the first record from forecast_data to fill fields (example)
            record = forecast_data[0]
            res.update({
                'name': self.env.context.get('default_horizon'),
                'product_id': record.get('product_id'),
                'start_date': record.get('start_date'),
                'end_date': record.get('end_date'),
                'planned_qty': record.get('planned_qty'),
                'sale_order_qty': record.get('sale_qty'),
                'delivery_order_qty': record.get('delivery_qty'),
                'current_stock': record.get('current_stock'),
            })
        return res
