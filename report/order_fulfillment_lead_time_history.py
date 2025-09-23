from odoo import models, fields, tools

class OrderFulfillmentLeadTimeHistory(models.Model):
    _name = 'order.fulfillment.lead.time.history'
    _description = 'Order Fulfillment Lead Time History'
    _auto = False

    order_name = fields.Char(string='Order Name')
    partner_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product', string='Product')
    order_creation = fields.Date(string='Order Creation Date')
    promised_ship_date = fields.Date(string='Promised Ship Date')
    actual_ship_date = fields.Date(string='Actual Ship Date')
    e2e_lt = fields.Integer(string='End-to-End Lead Time')
    delay_days = fields.Integer(string='Delay Days')
    on_time_flag = fields.Boolean(string='On Time Flag')
    backlog_aging = fields.Char(string='Backlog Aging')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'order_fulfillment_lead_time_history')
        self._cr.execute("""
            CREATE OR REPLACE VIEW order_fulfillment_lead_time_history AS (
                SELECT sol.id AS id,
                       so.name AS order_name,
                       so.partner_id AS partner_id,
                       sol.product_id AS product_id,
                       DATE(so.date_order) AS order_creation,
                       so.commitment_date::date AS promised_ship_date,
                       COALESCE(sp.date_done, sp.scheduled_date)::date AS actual_ship_date,
                       (COALESCE(sp.date_done, sp.scheduled_date)::date - so.date_order::date)::int AS e2e_lt,
                       CASE 
                           WHEN COALESCE(sp.date_done, sp.scheduled_date) > so.commitment_date::date
                           THEN (COALESCE(sp.date_done, sp.scheduled_date)::date - so.commitment_date::date)::int
                           ELSE 0
                       END AS delay_days,
                       CASE 
                           WHEN COALESCE(sp.date_done, sp.scheduled_date)::date <= so.commitment_date::date THEN TRUE
                           ELSE FALSE
                       END AS on_time_flag,
                       CASE 
                           WHEN COALESCE(sp.date_done, sp.scheduled_date) IS NULL 
                                OR COALESCE(sp.date_done, sp.scheduled_date) > so.commitment_date::date THEN
                                CASE 
                                    WHEN (COALESCE(sp.date_done, CURRENT_DATE)::date - so.commitment_date::date) BETWEEN 0 AND 7 THEN '0-7'
                                    WHEN (COALESCE(sp.date_done, CURRENT_DATE)::date - so.commitment_date::date) BETWEEN 8 AND 14 THEN '8-14'
                                    WHEN (COALESCE(sp.date_done, CURRENT_DATE)::date - so.commitment_date::date) BETWEEN 15 AND 30 THEN '15-30'
                                    WHEN (COALESCE(sp.date_done, CURRENT_DATE)::date - so.commitment_date::date) BETWEEN 31 AND 60 THEN '31-60'
                                    ELSE '>60'
                                END
                       END AS backlog_aging
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                JOIN res_partner rp ON rp.id = so.partner_id
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN stock_picking sp ON sp.origin = so.name
                WHERE so.date_order BETWEEN current_date - INTERVAL '365 days' AND current_date
                ORDER BY so.date_order DESC
            )
        """)
