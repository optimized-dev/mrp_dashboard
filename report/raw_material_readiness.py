from odoo import fields, models, tools, api
from collections import defaultdict


class RawMaterialReadiness(models.Model):
    _name = 'raw.material.readiness'
    _auto = False
    _description = 'Raw Material Readiness'

    date = fields.Date(string="Date", readonly=True)
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    required_qty = fields.Float(string="Required Qty", readonly=True)
    setting_name = fields.Char(string="Horizon", readonly=True)
    product_code = fields.Char(string="Product Code", readonly=True)
    forecast_stock = fields.Float(
        string="Forecast Stock",
        compute="_compute_forecast",
        store=False,
        readonly=True
    )
    priority = fields.Selection(
        [
            ('high', '🔴 High'),
            ('medium', '🟠 Medium'),
            ('low', '🟢 Low')
        ],
        string="Priority",
        compute="_compute_forecast",
        store=False,
        readonly=True
    )

    @api.depends('date', 'product_id', 'required_qty')
    def _compute_forecast(self):
        if not self:
            return

        products = self.mapped('product_id')
        if not products:
            return

        min_date = min(self.mapped('date'))
        max_date = max(self.mapped('date'))

        # Plans (Production requirements)
        all_plans = self.env['mrp.planning'].search([
            ('planning_date', '>=', min_date),
            ('planning_date', '<=', max_date)
        ])
        plans_map = defaultdict(list)
        for plan in all_plans:
            for line in plan.mrp_planning_bom_line_ids:
                plans_map[(line.product_id.id, plan.planning_date)].append(line.product_qty)

        # Purchases (Incoming stock)
        all_purchase_orders = self.env['purchase.order.line'].search([
            ('order_id.state', 'not in', ['done', 'cancel', 'draft']),
            ('order_id.date_approve', '>=', min_date),
            ('order_id.date_approve', '<=', max_date)
        ])
        purchase_map = defaultdict(list)
        for line in all_purchase_orders:
            line_date = line.order_id.date_approve.date()
            purchase_map[(line.product_id.id, line_date)].append(line)

        # Forecast calculation per product
        for product in products:
            product_records = self.filtered(lambda r: r.product_id == product).sorted('date')
            current_stock = product.qty_available

            for rec in product_records:
                # Requirements from production plan
                required_qty = sum(plans_map.get((product.id, rec.date), []))

                # Incoming PO qty
                lines = purchase_map.get((product.id, rec.date), [])
                total_po_qty = sum(l.product_qty - l.qty_received for l in lines)

                # Forecast calculation
                current_stock = current_stock + total_po_qty - required_qty
                rec.forecast_stock = current_stock

                # --- Priority assignment ---
                if current_stock < 0:
                    rec.priority = 'high'
                else:
                    rec.priority = 'low'

    def init(self):
        tools.drop_view_if_exists(self._cr, 'raw_material_readiness')
        self._cr.execute("""
                         CREATE
                         OR REPLACE VIEW raw_material_readiness AS (
                WITH settings AS (
                    SELECT
                        COALESCE(no_of_days, 0) AS no_of_days,
                        name AS setting_name
                    FROM widget_configuration WHERE widget = 'production_plan'
                ),
                date_range AS (
                    SELECT
                        CURRENT_DATE AS start_date,
                        CURRENT_DATE + s.no_of_days AS end_date,
                        s.setting_name
                    FROM settings s
                ),
                product_required AS (
                    SELECT
                        ml.product_id,
                        mp.id AS mrp_id,
                        ml.product_qty AS required_qty,
                        mp.planning_date,
                        dr.setting_name
                    FROM mrp_planning mp
                    JOIN mrp_planning_bom_line ml 
                        ON ml.mrp_planning_line_id = mp.id
                    JOIN date_range dr 
                        ON mp.planning_date BETWEEN dr.start_date AND dr.end_date
                )
                SELECT
                    ROW_NUMBER() OVER() AS id,  -- primary key for Odoo
                    pr.planning_date AS date,
                    pp.id AS product_id,  -- now using product.product
                    SUM(pr.required_qty) AS required_qty,
                    pr.setting_name,
                    pt.default_code AS product_code
                FROM product_required pr
                JOIN product_product pp ON pp.id = pr.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                GROUP BY pr.planning_date, pp.id, pr.setting_name, pt.default_code
            )
                         """)
