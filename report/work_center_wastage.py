from odoo import api, fields, models, tools

class WorkCentreWastage(models.Model):
    _name = 'work.centre.wastage'
    _description = 'Work Centre Wastage'
    _auto = False

    id = fields.Integer()
    operation_name = fields.Char(string="Operation Name")
    line_id = fields.Many2one('mrp.line', string='Line')
    time_from = fields.Float(string="Time From")
    time_to = fields.Float(string="Time To")
    product_id = fields.Many2one('product.product', string="Product")
    planned_qty = fields.Float(string="Planned Qty")
    wastage_qty = fields.Float(string="Wastage")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'work_centre_wastage')
        self._cr.execute("""
            CREATE OR REPLACE VIEW work_centre_wastage AS
            SELECT
                ROW_NUMBER() OVER () AS id,
                pdo.name AS operation_name,
                wd.line_id,
                wd.time_from,
                wd.time_to,
                wd.product_id,
                wd.planned_qty,
                wd.wastage_qty
            FROM wastage_details wd
            JOIN production_daily_operation_wastage pdow
                ON pdow.id = wd.production_daily_operation_wastage_id
            JOIN production_daily_operation pdo
                ON pdo.id = pdow.production_daily_operation_id
                                                join mrp_planning mp on mp.id = pdo.production_plan_id where mp.planning_date = current_date
        """)

