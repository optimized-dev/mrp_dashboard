from odoo import models, fields, tools

class MachineUtilizationReport(models.Model):
    _name = 'machine.utilization.report'
    _description = 'Machine Utilization Report'
    _auto = False  # SQL view
    _order = 'work_centre, machine_id'

    work_centre = fields.Char(string="Work Centre")
    machine_id = fields.Many2one('machine.master', string="Machine")
    product_id = fields.Many2one('product.template', string="Product")
    planned_runtime_hrs = fields.Float(string="Planned Runtime (Hrs)")
    actual_runtime_hrs = fields.Float(string="Actual Runtime (Hrs)")
    downtime_hrs = fields.Float(string="Downtime (Hrs)")
    downtime_reason = fields.Char(string="Downtime Reason")
    utilization_percent = fields.Float(string="Utilization (%)")
    downtime_percent = fields.Float(string="Downtime (%)")
    mtbf_hrs = fields.Float(string="MTBF (Hrs)")
    mttr_hrs = fields.Float(string="MTTR (Hrs)")
    status = fields.Char(string="Status")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'machine_utilization_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW machine_utilization_report AS
                SELECT 
                    row_number() OVER() AS id,
                    mw.name AS work_centre,
                    mm.id AS machine_id,
                    mp.product_id AS product_id,
                    ROUND((pdpps.machine_rate / 60.0)::numeric, 2) AS planned_runtime_hrs,
                    ROUND(((pdpps.machine_rate / 60.0 - COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0))::numeric), 2) AS actual_runtime_hrs,
                    ROUND(COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0)::numeric, 2) AS downtime_hrs,
                    COALESCE(mr.remark, 'No Downtime') AS downtime_reason,
                    ROUND(
                        CAST(
                            CASE 
                                WHEN pdpps.machine_rate > 0 
                                THEN (((pdpps.machine_rate / 60.0 - COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0)) / (pdpps.machine_rate / 60.0)) * 100) 
                                ELSE 0 
                            END 
                        AS numeric), 2
                    ) AS utilization_percent,
                    ROUND(
                        CAST(
                            CASE 
                                WHEN pdpps.machine_rate > 0 
                                THEN ((COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0) / (pdpps.machine_rate / 60.0)) * 100) 
                                ELSE 0 
                            END 
                        AS numeric), 2
                    ) AS downtime_percent,
                    NULL AS mtbf_hrs,
                    ROUND(COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0)::numeric, 2) AS mttr_hrs,
                    CASE 
                        WHEN ((pdpps.machine_rate / 60.0) > 0 
                              AND (((pdpps.machine_rate / 60.0 - COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0)) / (pdpps.machine_rate / 60.0)) * 100) >= 85 
                              AND ((COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0) / (pdpps.machine_rate / 60.0)) * 100) < 5) 
                            THEN '✅ High Utilization'
                        WHEN ((pdpps.machine_rate / 60.0) > 0 
                              AND (((pdpps.machine_rate / 60.0 - COALESCE(EXTRACT(EPOCH FROM (mr.engineering_end_last_time - mr.request_date_time)) / 3600, 0)) / (pdpps.machine_rate / 60.0)) * 100) BETWEEN 60 AND 85) 
                            THEN '⚠️ Moderate Utilization'
                        ELSE '❌ Low Utilization'
                    END AS status
                FROM mrp_planning mp
                JOIN production_daily_plan_process_stages pdpps 
                    ON pdpps.daily_production_plan_id = mp.id
                JOIN mrp_workcenter mw 
                    ON mw.production_stage_id = pdpps.production_stage_id
                JOIN used_location ul 
                    ON ul.work_center_id = mw.id
                JOIN machine_master mm 
                    ON mm.location_id = ul.id
                LEFT JOIN maintenance_request mr 
                    ON mr.machine_id = mm.id 
                    AND mr.maintenance_request_type = 'machine' 
                    AND mr.maintenance_type = 'corrective' 
                    AND DATE(mr.request_date_time) = mp.planning_date
                WHERE mp.planning_date = CURRENT_DATE;
        """)
