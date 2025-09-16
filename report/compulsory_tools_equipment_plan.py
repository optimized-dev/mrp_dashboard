from odoo import models, fields, tools

class CompulsoryToolsEquipmentPlan(models.Model):
    _name = 'compulsory.tools.equipment.plan'
    _description = 'Compulsory Tools & Equipment Plan'
    _auto = False  # SQL view, not a regular table

    id = fields.Integer(string='ID', readonly=True)
    planning_date = fields.Date(string='Planning Date')
    tool = fields.Many2one('product.product', string='Tool')
    production_stage_id = fields.Many2one('mrp.routing.workcenter', string='Production Stage')
    product_id = fields.Many2one('product.product', string='Product')
    product_name = fields.Char(string='Product Name')
    current_stock = fields.Float(string='Current Stock')
    total_required_qty = fields.Float(string='Required Quantity')
    gap = fields.Float(string='Gap')
    availability = fields.Char(string='Availability')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'compulsory_tools_equipment_plan')
        self._cr.execute("""
            CREATE OR REPLACE VIEW compulsory_tools_equipment_plan AS
WITH dates AS (
    SELECT generate_series(
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '7 day',
        INTERVAL '1 day'
    )::date AS planning_date
),
current_stock AS (
    SELECT
        pp.id AS product_id,
        SUM(sq.quantity) AS current_stock
    FROM stock_quant sq
    JOIN product_product pp ON pp.id = sq.product_id
    JOIN stock_location sl ON sl.id = sq.location_id
    WHERE sl.usage = 'internal'
    GROUP BY pp.id
)
SELECT
    ROW_NUMBER() OVER (ORDER BY d.planning_date, bom_tool.product_id, p_stages.production_stage_id) AS id,
    d.planning_date,
    bom_tool.product_id AS tool,
    p_stages.production_stage_id AS production_stage_id,
    pp.id AS product_id,
    pt.name AS product_name,
    COALESCE(cs.current_stock, 0) AS current_stock,
    SUM(COALESCE(bom_tool.qty, 0)) AS total_required_qty,
    (COALESCE(cs.current_stock, 0) - SUM(COALESCE(bom_tool.qty, 0))) AS gap,
    CASE
        WHEN COALESCE(cs.current_stock, 0) = 0 THEN '❌ Not Available'
        WHEN COALESCE(cs.current_stock, 0) >= SUM(COALESCE(bom_tool.qty, 0)) THEN '✅ Available'
        WHEN COALESCE(cs.current_stock, 0) < SUM(COALESCE(bom_tool.qty, 0)) AND COALESCE(cs.current_stock, 0) > 0 THEN '⚠️ Partial'
    END AS availability
FROM dates d
LEFT JOIN mrp_planning mp_plan 
    ON mp_plan.planning_date = d.planning_date
LEFT JOIN production_daily_plan_process_stages p_stages 
    ON p_stages.daily_production_plan_id = mp_plan.id
LEFT JOIN bom_tool_standard_daily_plan bom_tool 
    ON bom_tool.production_daily_plan_process_stages_id = p_stages.id
LEFT JOIN product_product pp 
    ON pp.id = mp_plan.product_id
LEFT JOIN product_template pt 
    ON pt.id = pp.product_tmpl_id
LEFT JOIN current_stock cs
    ON cs.product_id = pp.id
GROUP BY 
    d.planning_date,
    bom_tool.product_id,
    p_stages.production_stage_id,
    pp.id,
    pt.name,
    cs.current_stock
ORDER BY d.planning_date, tool;
        """)
