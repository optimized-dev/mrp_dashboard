from odoo import fields, models, tools

class CostResourceConsumption(models.Model):
    _name = 'cost.resource.consumption'
    _description = 'Cost Resource Consumption'
    _auto = False

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product')
    product_name = fields.Char(string='Product Name')
    mrp_planning_id = fields.Many2one('mrp.planning', string='MRP Planning')
    planned_qty = fields.Float(string='Planned Qty')
    actual_qty = fields.Float(string='Actual Qty')
    total_production_cost = fields.Float(string='Total Production Cost')
    cost_per_unit = fields.Float(string='Cost per Unit')
    material_planned_usage = fields.Float(string='Material Planned Usage')
    material_actual_usage = fields.Float(string='Material Actual Usage')
    variance = fields.Float(string='Material Variance %')
    utility_name = fields.Char(string='Utility Name')
    energy_per_unit_output = fields.Float(string='Energy per Unit Output')
    material_cost = fields.Float(string='Material Cost')
    labour_cost = fields.Float(string='Labour Cost')
    overhead_cost = fields.Float(string='Overhead Cost')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'cost_resource_consumption')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW cost_resource_consumption AS (
                SELECT
                    row_number() OVER(ORDER BY ppc.date) AS id,   
                    ppc.date AS date,
                    ppc.product_id,
                    pt.name AS product_name,
                    mp.id AS mrp_planning_id,
                    coalesce(mp.product_uom_qty, 0) AS planned_qty,
                    coalesce(mp.actual_qty, 0) AS actual_qty,
                    sum(mdml.actual_value) + sum(dll.actual_value) + sum(poll.actual_value) AS total_production_cost,
                    CASE 
                        WHEN coalesce(mp.actual_qty, 0) = 0 THEN 0
                        ELSE (sum(mdml.actual_value) + sum(dll.actual_value) + sum(poll.actual_value)) / mp.actual_qty
                    END AS cost_per_unit,
                    coalesce(mp.product_uom_qty, 0) * bom.total_bom_cost AS material_planned_usage,
                    coalesce(mp.actual_qty, 0) * bom.total_bom_cost AS material_actual_usage,
                    CASE 
                        WHEN coalesce(mp.product_uom_qty, 0) = 0 THEN 0
                        ELSE ((coalesce(mp.actual_qty, 0) * bom.total_bom_cost) 
                             - (coalesce(mp.product_uom_qty, 0) * bom.total_bom_cost)) 
                             / (coalesce(mp.product_uom_qty, 0) * bom.total_bom_cost) * 100
                    END AS variance,
                    ut.name AS utility_name,
                    CASE 
                        WHEN mp.actual_qty = 0 THEN 0
                        ELSE coalesce(pol.actual_value, 0) / mp.actual_qty 
                    END AS energy_per_unit_output,
                    sum(mdml.actual_value) as material_cost,
                    sum(dll.actual_value) as labour_cost,
                    sum(poll.actual_value) as overhead_cost
                FROM pcc_production_costing ppc
                JOIN pcc_direct_material_line mdml ON mdml.costing_id = ppc.id
                JOIN pcc_direct_labour_line dll ON dll.costing_id = ppc.id
                JOIN pcc_production_overhead_line pol ON pol.costing_id = ppc.id
                JOIN pcc_production_overhead_line poll ON poll.costing_id = ppc.id
                JOIN mrp_planning mp ON mp.id = ppc.production_plan_id
                JOIN product_template pt ON pt.id = ppc.product_id
                JOIN utility_types ut ON ut.id = pol.utility_type_id
                JOIN (
                    SELECT 
                        mpbl.mrp_planning_line_id,
                        SUM(mpbl.product_qty * pp.stored_standard_price) AS total_bom_cost
                    FROM mrp_planning_bom_line mpbl
                    JOIN product_product pp ON pp.id = mpbl.product_id
                    GROUP BY mpbl.mrp_planning_line_id
                ) bom ON bom.mrp_planning_line_id = ppc.production_plan_id
                WHERE ppc.date BETWEEN current_date - INTERVAL '365 days' AND current_date
                GROUP BY ut.name, ppc.date, ppc.product_id, pt.name, mp.id, pol.actual_value, 
                         bom.total_bom_cost, mp.actual_qty, mp.product_uom_qty
            )
        """)
