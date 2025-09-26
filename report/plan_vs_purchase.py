from odoo import models, fields, tools

class PlanVsPurchase(models.Model):
    _name = 'plan.vs.purchase'
    _description = 'Production Plan vs Import Purchase Plan'
    _auto = False

    planning_date = fields.Date(string='Planning Date')
    product_id = fields.Many2one('product.product', string='Product')
    product_name = fields.Char(string='Product Name')
    required_qty = fields.Float(string='Required Qty')
    purchased_qty = fields.Float(string='Purchased Qty')
    remaining_stock = fields.Float(string='Remaining Stock')
    gap_qty = fields.Float(string='Gap Qty')
    alert_status = fields.Selection([
        ('OK', '✅ OK'),
        ('Shortfall', '❌ Shortfall')
    ], string='Alert Status')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'plan_vs_purchase')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW plan_vs_purchase AS
            WITH RECURSIVE product_data AS (
                SELECT 
                    mp.planning_date,
                    mp.id AS planning_id,
                    pp.id AS product_id,
                    pt.name AS product_name,
                    SUM(mpbl.product_qty) AS required_qty,
                    COALESCE(SUM(pol.quantity),0) AS purchased_qty
                FROM mrp_planning mp
                JOIN (
                    SELECT mrp_planning_line_id, product_id, SUM(product_qty) AS product_qty
                    FROM mrp_planning_bom_line
                    GROUP BY mrp_planning_line_id, product_id
                ) mpbl ON mpbl.mrp_planning_line_id = mp.id
                JOIN product_product pp ON pp.id = mp.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN planning_order_lines pol ON pol.product_id = mpbl.product_id
                LEFT JOIN import_purchase_planning ipp ON ipp.id = pol.import_purchase_planning_id
                WHERE mp.planning_date >= current_date
                GROUP BY mp.planning_date, mp.id, pp.id, pt.name
            ),
            current_stock AS (
                SELECT sq.product_id, SUM(sq.quantity) AS stock_qty
                FROM stock_quant sq
                JOIN stock_location sl ON sl.id = sq.location_id
                WHERE sl.usage='internal'
                GROUP BY sq.product_id
            ),
            dates_product AS (
                SELECT 
                    pd.planning_date,
                    pd.product_id,
                    pd.product_name,
                    pd.required_qty,
                    pd.purchased_qty,
                    COALESCE(SUM(cs.stock_qty),0)::numeric AS initial_stock
                FROM product_data pd
                LEFT JOIN mrp_planning_bom_line mpbl ON mpbl.mrp_planning_line_id = pd.planning_id
                LEFT JOIN current_stock cs ON cs.product_id = mpbl.product_id
                GROUP BY pd.planning_date, pd.product_id, pd.product_name, pd.required_qty, pd.purchased_qty
            ),
            recursive_calc AS (
                SELECT 
                    planning_date,
                    product_id,
                    product_name,
                    required_qty,
                    purchased_qty,
                    initial_stock AS remaining_stock,
                    (required_qty - (purchased_qty + initial_stock))::numeric AS gap_qty,
                    CASE 
                        WHEN initial_stock + purchased_qty - required_qty < 0 THEN 'Shortfall' 
                        ELSE 'OK' 
                    END AS alert_status
                FROM dates_product
                WHERE planning_date = current_date

                UNION ALL

                SELECT 
                    dp.planning_date,
                    dp.product_id,
                    dp.product_name,
                    dp.required_qty,
                    dp.purchased_qty,
                    (rc.remaining_stock + dp.purchased_qty - dp.required_qty)::numeric AS remaining_stock,
                    (dp.required_qty - (dp.purchased_qty + rc.remaining_stock))::numeric AS gap_qty,
                    CASE 
                        WHEN (rc.remaining_stock + dp.purchased_qty - dp.required_qty) < 0 THEN 'Shortfall' 
                        ELSE 'OK' 
                    END AS alert_status
                FROM dates_product dp
                JOIN recursive_calc rc 
                  ON dp.product_id = rc.product_id 
                 AND dp.planning_date = rc.planning_date + INTERVAL '1 day'
            )
            SELECT 
                row_number() OVER() AS id,   -- unique ID for Odoo
                *
            FROM recursive_calc
            ORDER BY product_id, planning_date;
        """)
