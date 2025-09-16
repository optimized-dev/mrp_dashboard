from odoo import models, fields, tools

class OrderPriorityQueue(models.Model):
    _name = 'order.priority.queue'
    _auto = False
    _description = 'Order Priority Queue (Product Wise)'

    order_no = fields.Char("Order No")
    product_name = fields.Char("Product Name")
    order_qty = fields.Float("Order Qty")
    delivery_due_date = fields.Datetime("Delivery Due Date")
    priority = fields.Selection([
        ('high', '🔴 High'),
        ('medium', '🟠 Medium'),
        ('low', '🟢 Low')
    ], string="Priority", readonly=True)
    customer = fields.Char("Customer")
    profitability_score = fields.Float("Profitability Score")

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    sol.id AS id,
                    so.name AS order_no,
                    pt.name AS product_name,
                    sol.product_uom_qty AS order_qty,
                    so.commitment_date AS delivery_due_date,
                    CASE
                        WHEN so.commitment_date <= CURRENT_DATE + INTERVAL '2 day' THEN 'high'
                        WHEN so.commitment_date <= CURRENT_DATE + INTERVAL '7 day' THEN 'medium'
                        ELSE 'low'
                    END AS priority,
                    rp.name AS customer,
                    (sol.price_total - (sol.price_unit * sol.product_uom_qty)) AS profitability_score
                FROM sale_order so
                JOIN sale_order_line sol ON sol.order_id = so.id
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN res_partner rp ON rp.id = so.partner_id
                WHERE so.state NOT IN ('cancel')
            )
        """)
