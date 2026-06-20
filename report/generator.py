import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

class ReportGenerator:
    """
    Takes the mathematical verdicts from APEX and generates a beautiful, 
    human-readable HTML/PDF dashboard to review every evening.
    """
    def __init__(self):
        # Setup Jinja environment for rendering HTML
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Ensure the output directory exists in the root workspace
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_html_report(self, regime_state: int, regime_mult: float, verdicts: list) -> str:
        """
        Renders the final processed verdicts into the HTML template.
        Returns the absolute filepath of the generated report.
        """
        template = self.env.get_template('report.html')
        
        # Sort verdicts: BUYs first, then HOLDs, then REJECTs. Sort by highest score within those blocks.
        def get_sort_key(v):
            order = {"BUY": 0, "HOLD": 1, "REJECT": 2}
            return (order.get(v['decision'], 3), -v['final_score'])
            
        sorted_verdicts = sorted(verdicts, key=get_sort_key)
        
        # Inject data into the HTML template
        html_content = template.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M IST"),
            regime_state=regime_state,
            regime_mult=f"{regime_mult:.2f}",
            stocks=sorted_verdicts
        )
        
        # Save to output folder
        filename = f"apex_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"[APEX] Report successfully generated at: {filepath}")
        return filepath
