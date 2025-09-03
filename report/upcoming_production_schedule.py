from odoo import fields, models, tools, api
from collections import defaultdict

class UpcomingProductionSchedule(models.Model):
    _name = 'upcoming.production.schedule'
    _auto = False
    _description = 'Upcoming Production Schedule'
    _order = 'date asc'

    date = fields.Date(string="Date", readonly=True)
    product_id = fields.Many2one('product.template', string="Product", readonly=True)
    planned_qty = fields.Float(string="Planned Qty", readonly=True)
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


    @api.depends('date', 'product_id', 'planned_qty')
    def _compute_forecast(self):
        if not self:
            return

        products = self.mapped('product_id')
        min_date = min(self.mapped('date'))
        max_date = max(self.mapped('date'))

        all_plans = self.env['mrp.planning'].search([
            ('product_id', 'in', products.ids),
            ('planning_date', '>=', min_date),
            ('planning_date', '<=', max_date)
        ])
        plans_map = defaultdict(list)
        for plan in all_plans:
            plans_map[(plan.product_id.id, plan.planning_date)].append(plan.product_uom_qty)

        all_sale_orders = self.env['sale.order.line'].search([
            ('product_id.product_tmpl_id', 'in', products.ids),
            ('order_id.state', 'not in', ['draft', 'cancel']),
            ('order_id.commitment_date', '>=', min_date),
            ('order_id.commitment_date', '<=', max_date)
        ])
        sale_map = defaultdict(list)
        for line in all_sale_orders:
            line_date = line.order_id.commitment_date.date()
            sale_map[(line.product_id.product_tmpl_id.id, line_date)].append(line)

        for product in products:
            product_records = self.filtered(lambda r: r.product_id == product).sorted('date')
            current_stock = product.qty_available

            day_wise_forecast = []

            for rec in product_records:
                planned_qty = sum(plans_map.get((product.id, rec.date), []))

                lines = sale_map.get((product.id, rec.date), [])
                total_demand_qty = sum(l.product_uom_qty for l in lines)
                total_delivered = sum(l.qty_delivered for l in lines)
                sale_qty = total_demand_qty - total_delivered

                current_stock = current_stock + planned_qty - sale_qty
                rec.forecast_stock = current_stock

                shortfall = current_stock  # since stock already reduced by sales
                no_of_days = (rec.date - min_date).days

                day_wise_forecast.append({
                    'rec': rec,
                    'shortfall': shortfall,
                    'no_of_days': no_of_days
                })

            # Assign priority
            negative_shortfall_forecast = [f for f in day_wise_forecast if f['shortfall'] < 0]
            sorted_negative = sorted(
                negative_shortfall_forecast,
                key=lambda f: (f['no_of_days'], f['shortfall'])
            )
            for idx, f in enumerate(sorted_negative):
                f['rec'].priority = 'high' if idx == 0 else 'medium' if idx == 1 else 'low'

            for f in day_wise_forecast:
                if f['shortfall'] >= 0:
                    f['rec'].priority = 'low'

    def init(self):
        tools.drop_view_if_exists(self._cr, 'upcoming_production_schedule')
        self._cr.execute("""
                         CREATE
                         OR REPLACE VIEW upcoming_production_schedule AS (
                WITH settings AS (
                    SELECT 
                        COALESCE(no_of_days, 0) AS no_of_days,
                        name AS setting_name
                    FROM widget_configuration
                    WHERE widget = 'production_plan'
                ),
                -- Generate all days for each setting
                date_series AS (
                    SELECT 
                        s.setting_name,
                        gs::date AS date
                    FROM settings s
                    CROSS JOIN generate_series(CURRENT_DATE + 1, CURRENT_DATE + s.no_of_days, interval '1 day') AS gs
                ),
                products AS (
                    SELECT DISTINCT product_id FROM mrp_planning
                ),
                date_product_series AS (
                    SELECT
                        ds.setting_name,
                        ds.date,
                        p.product_id
                    FROM date_series ds
                    CROSS JOIN products p
                )
                SELECT
                    ROW_NUMBER() OVER() AS id,
                    dps.date AS date,
                    dps.product_id,
                    pt.default_code AS product_code,  -- Added product_code
                    SUM(mp.product_uom_qty) AS planned_qty,
                    dps.setting_name
                FROM date_product_series dps
                LEFT JOIN mrp_planning mp
                    ON mp.product_id = dps.product_id
                    AND mp.planning_date::date = dps.date
                LEFT JOIN product_product pp
                    ON pp.id = dps.product_id
                LEFT JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
                GROUP BY dps.setting_name, dps.date, dps.product_id, pt.default_code
                HAVING SUM(mp.product_uom_qty) > 0
                ORDER BY dps.setting_name, dps.date, dps.product_id
            )
                         """)



