{
    'name': 'Manufacturing Dashboard',
    'version': '15.0.1.0.0',
    'summary': 'Dashboard for manufacturing planning, operations monitoring, and performance analysis.',
    'description': """
                    The Manufacturing Dashboard module provides a clear and interactive interface to 
                    plan, monitor, and analyze manufacturing operations.  
                    
                    Key Features:
                    - Visualize ongoing and upcoming production orders.  
                    - Monitor work center and machine utilization.  
                    - Track planned vs. actual production performance.  
                    - Analyze production efficiency and bottlenecks.  
                    - Support decision-making with real-time insights.  
                    
                    This module is designed to give production managers and teams an overview of 
                    manufacturing activities, helping improve planning accuracy, resource allocation, 
                    and overall operational efficiency.
                    """,
    'author': 'Avishka Deshan',
    'company': 'Optimized Technologies',
    'website': "https:www.optimized.lk",
    'maintainer': 'Avishka Deshan',
    'category': 'Inventory',
    'depends': ['mrp', 'manufacturing_extend', 'dynamic_manufacturing_extend'],

    'data': [
        'security/ir.model.access.csv',
        # 'views/manufacturing_dashboard_views.xml',
        # 'views/menu_action.xml',
        'views/widget_configuration_views.xml',
        # 'wizard/widget_data_views.xml',
        'report/upcoming_production_schedule_views.xml',
        'report/raw_material_readiness_views.xml',
        'report/demand_forecast_views.xml',
        'report/order_priority_queue_Views.xml',
        'report/current_production_status_views.xml',
        'report/work_center_production_views.xml',
        'report/stepwise_production_flow_tracker_views.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'manufacturing_dashboard/static/src/js/manufacturing_dashboard.js',
    #         'manufacturing_dashboard/static/src/js/d3.min.js',
    #         'manufacturing_dashboard/static/src/css/manufacturing_dashboard.css',
    #     ],
    #     'web.assets_qweb': [
    #         'manufacturing_dashboard/static/src/xml/manufacturing_dashboard.xml',
    #     ],
    # },
    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
