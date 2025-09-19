from odoo import models, fields

class OrderFulfillmentProgress(models.Model):
    _name = 'order.fulfillment.progress'
    _description = 'Order Fulfillment Progress'
    _auto = False

    id = fields.Integer()
    sale_order = fields.Char(string='Sale Order')
    customer = fields.Char(string='Customer')
    product = fields.Char(string='Product')
    ordered_qty = fields.Float(string='Ordered Quantity')
    delivery_due_date = fields.Date(string='Delivery Due Date')
    order_start = fields.Datetime(string='Order Start')
    order_finish = fields.Datetime(string='Order Finish')
    forecast_qty_on_due_date = fields.Float(string='Forecast Qty')
    shortage_or_balance = fields.Float(string='Shortage/Balance')
    qty_to_produce = fields.Float(string='Qty to Produce')
    progress_percent = fields.Float(string='Progress %')
    status = fields.Char(string='Status')
    remaining_days = fields.Integer(string='Remaining Days')  # NEW FIELD

    def init(self):
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW order_fulfillment_progress AS
        WITH stock AS (
            SELECT
                pp.product_tmpl_id,
                SUM(sq.quantity) AS current_stock
            FROM stock_quant sq
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN stock_location sl ON sl.id = sq.location_id
            WHERE sl.usage = 'internal'
            GROUP BY pp.product_tmpl_id
        ),
        sales AS (
            SELECT
                pp.product_tmpl_id,
                DATE(so.commitment_date) AS due_date,
                SUM(sol.product_uom_qty) AS demand
            FROM sale_order_line sol
            JOIN sale_order so ON sol.order_id = so.id
            JOIN product_product pp ON sol.product_id = pp.id
            GROUP BY pp.product_tmpl_id, DATE(so.commitment_date)
        ),
        planning AS (
            SELECT
                mp.product_id AS product_tmpl_id,
                mp.planning_date::date AS plan_date,
                SUM(mp.product_uom_qty) AS supply
            FROM mrp_planning mp
            GROUP BY mp.product_id, mp.planning_date::date
        )
        SELECT
            sol.id AS id,
            so.name AS sale_order,
            rp.name AS customer,
            COALESCE(pp.default_code,'') || ' - ' || pt.name AS product,
            sol.product_uom_qty AS ordered_qty,
            DATE(so.commitment_date) AS delivery_due_date,
            so.date_order AS order_start,
            so.validity_date AS order_finish,
            (st.current_stock
               + COALESCE((SELECT SUM(p.supply)
                           FROM planning p
                           WHERE p.product_tmpl_id = pt.id
                             AND p.plan_date <= so.commitment_date),0)
               - COALESCE((SELECT SUM(s.demand)
                           FROM sales s
                           WHERE s.product_tmpl_id = pt.id
                             AND s.due_date <= so.commitment_date),0)
            ) AS forecast_qty_on_due_date,
            ((st.current_stock
               + COALESCE((SELECT SUM(p.supply)
                           FROM planning p
                           WHERE p.product_tmpl_id = pt.id
                             AND p.plan_date <= so.commitment_date),0)
               - COALESCE((SELECT SUM(s.demand)
                           FROM sales s
                           WHERE s.product_tmpl_id = pt.id
                             AND s.due_date <= so.commitment_date),0)
            ) - sol.product_uom_qty) AS shortage_or_balance,
            GREATEST(0, (sol.product_uom_qty - (
               (st.current_stock
                  + COALESCE((SELECT SUM(p.supply)
                              FROM planning p
                              WHERE p.product_tmpl_id = pt.id
                                AND p.plan_date <= so.commitment_date),0)
                  - COALESCE((SELECT SUM(s.demand)
                              FROM sales s
                              WHERE s.product_tmpl_id = pt.id
                                AND s.due_date <= so.commitment_date),0)
               )
            ))) AS qty_to_produce,
            ROUND(
              (
                (sol.product_uom_qty - GREATEST(0, sol.product_uom_qty - (
                  (st.current_stock
                    + COALESCE((SELECT SUM(p.supply)
                                FROM planning p
                                WHERE p.product_tmpl_id = pt.id
                                  AND p.plan_date <= so.commitment_date),0)
                    - COALESCE((SELECT SUM(s.demand)
                                FROM sales s
                                WHERE s.product_tmpl_id = pt.id
                                  AND s.due_date <= so.commitment_date),0)
                  )
                )))::numeric / NULLIF(sol.product_uom_qty,0)
              ) * 100,2
            ) AS progress_percent,
            CASE
              WHEN (
                (sol.product_uom_qty - GREATEST(0, sol.product_uom_qty - (
                  (st.current_stock
                    + COALESCE((SELECT SUM(p.supply)
                                FROM planning p
                                WHERE p.product_tmpl_id = pt.id
                                  AND p.plan_date <= so.commitment_date),0)
                    - COALESCE((SELECT SUM(s.demand)
                                FROM sales s
                                WHERE s.product_tmpl_id = pt.id
                                  AND s.due_date <= so.commitment_date),0)
                  )
                )))::numeric / NULLIF(sol.product_uom_qty,0)
              ) * 100 >= 95 THEN '✅ On Track'
              WHEN (
                (sol.product_uom_qty - GREATEST(0, sol.product_uom_qty - (
                  (st.current_stock
                    + COALESCE((SELECT SUM(p.supply)
                                FROM planning p
                                WHERE p.product_tmpl_id = pt.id
                                  AND p.plan_date <= so.commitment_date),0)
                    - COALESCE((SELECT SUM(s.demand)
                                FROM sales s
                                WHERE s.product_tmpl_id = pt.id
                                  AND s.due_date <= so.commitment_date),0)
                  )
                )))::numeric / NULLIF(sol.product_uom_qty,0)
              ) * 100 BETWEEN 90 AND 95 THEN '⚠️ At Risk'
              ELSE '❌ Delayed'
            END AS status,
            (so.commitment_date::date - CURRENT_DATE) AS remaining_days
        FROM sale_order_line sol
        JOIN sale_order so ON so.id = sol.order_id
        JOIN res_partner rp ON so.partner_id = rp.id
        JOIN product_product pp ON sol.product_id = pp.id
        JOIN product_template pt ON pp.product_tmpl_id = pt.id
        LEFT JOIN stock st ON st.product_tmpl_id = pt.id
        WHERE DATE(so.commitment_date) >= CURRENT_DATE
        ORDER BY so.commitment_date, so.name;
        """)
