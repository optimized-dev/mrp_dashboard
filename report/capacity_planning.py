from odoo import fields, models, tools

class CapacityPlanning(models.Model):
    _name = 'capacity.planning'
    _description = 'Capacity Planning'
    _auto = False  # SQL view, not a table

    id = fields.Integer(string='ID', readonly=True)
    resources = fields.Char(string='Resource')
    allocated_time_hours = fields.Char(string='Allocated Time')
    total_capacity = fields.Char(string='Total Capacity')
    used_percent = fields.Char(string='Used %')
    buffer = fields.Char(string='Buffer')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'capacity_planning')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW capacity_planning AS
            SELECT 
                ROW_NUMBER() OVER () AS id,
                resources,
                allocated_time_hours,
                total_capacity,
                used_percent,
                buffer
            FROM (
                SELECT 
                    'Machines' AS resources,
                    ROUND(CAST(COALESCE(SUM(pdps.machine_rate), 0) / 60.0 AS numeric)) || ' Hour' AS allocated_time_hours,
                    ROUND(CAST(COALESCE(SUM(csl.machine_rate), 0) / 60.0 AS numeric)) || ' Hour' AS total_capacity,
                    ROUND(
                        (CAST(COALESCE(SUM(pdps.machine_rate), 0) / 60.0 AS numeric) /
                         NULLIF(CAST(COALESCE(SUM(csl.machine_rate), 0) / 60.0 AS numeric), 0)) * 100
                    ) || ' %' AS used_percent,
                    ROUND(
                        (CAST(COALESCE(SUM(csl.machine_rate), 0) / 60.0 AS numeric) - 
                         CAST(COALESCE(SUM(pdps.machine_rate), 0) / 60.0 AS numeric))
                    ) || ' Hour' AS buffer
                FROM production_daily_plan_process_stages pdps
                JOIN mrp_planning mp 
                    ON pdps.daily_production_plan_id = mp.id
                JOIN capacity_stage_line csl 
                    ON csl.stage_id = pdps.production_stage_id 
                WHERE mp.planning_date = CURRENT_DATE

                UNION ALL

                SELECT 
                    'Labor' AS resources,
                    ROUND(CAST(COALESCE(SUM(bpsldp.labour_rate), 0) / 60.0 AS numeric)) || ' Hour' AS allocated_time_hours,
                    ROUND(CAST(COALESCE(SUM(csl.labor_rate), 0) / 60.0 AS numeric)) || ' Hour' AS total_capacity,
                    ROUND(
                        (CAST(COALESCE(SUM(bpsldp.labour_rate), 0) / 60.0 AS numeric) /
                         NULLIF(CAST(COALESCE(SUM(csl.labor_rate), 0) / 60.0 AS numeric), 0)) * 100
                    ) || ' %' AS used_percent,
                    ROUND(
                        (CAST(COALESCE(SUM(csl.labor_rate), 0) / 60.0 AS numeric) - 
                         CAST(COALESCE(SUM(bpsldp.labour_rate), 0) / 60.0 AS numeric))
                    ) || ' Hour' AS buffer
                FROM bom_production_stage_labour_daily_plan bpsldp
                JOIN production_daily_plan_process_stages pdps 
                    ON pdps.id = bpsldp.production_daily_plan_process_stages_id
                JOIN mrp_planning mp 
                    ON pdps.daily_production_plan_id = mp.id
                JOIN capacity_stage_line csl 
                    ON csl.stage_id = pdps.production_stage_id 
                WHERE mp.planning_date = CURRENT_DATE
            ) AS subquery;
        """)
