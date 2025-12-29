"""
PNC Strategic Foundry - Flash Card Generator
============================================
Generates HTML "Flash Reports" for the Analysis Cards UI.
Inspired by Gemini's Flash UI, these cards provide immediate, 
visually rich summaries of complex reasoning.

The frontend 'ArtifactCard' component renders these via iframe.
"""

import json
from typing import Dict, List, Any

class FlashCardGenerator:
    
    STYLE_CSS = """
    <style>
        :root {
            --pnc-orange: #F47920;
            --pnc-blue: #004C89;
            --pnc-grey: #5A5A5A;
            --bg-dark: #1E1E1E;
            --text-light: #FFFFFF;
        }
        body {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 16px;
            background-color: transparent;
            color: var(--text-light);
        }
        .card-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 8px;
        }
        .title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--pnc-orange);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge {
            font-size: 0.75rem;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 700;
        }
        .badge.approved { background-color: rgba(40, 167, 69, 0.2); color: #28a745; border: 1px solid #28a745; }
        .badge.denied { background-color: rgba(220, 53, 69, 0.2); color: #dc3545; border: 1px solid #dc3545; }
        .badge.flagged { background-color: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid #ffc107; }
        
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 12px;
        }
        .section-title {
            font-size: 0.8rem;
            color: #AAAAAA;
            margin-bottom: 4px;
            text-transform: uppercase;
        }
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        .metric-label { font-size: 0.9rem; color: #DDDDDD; }
        .metric-value { font-size: 0.9rem; font-weight: 600; }
        
        .reasoning-text {
            font-size: 0.9rem;
            line-height: 1.4;
            color: #CCCCCC;
        }
        ul { margin: 8px 0; padding-left: 20px; }
        li { margin-bottom: 4px; }
        
        .chart-placeholder {
            height: 100px;
            background: linear-gradient(90deg, rgba(244,121,32,0.1) 0%, rgba(0,76,137,0.1) 100%);
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            color: var(--pnc-orange);
            border: 1px dashed var(--pnc-orange);
        }
    </style>
    """

    @staticmethod
    def _generate_svg_bar_chart(metrics: Dict[str, Any]) -> str:
        """
        Generates a simple SVG Bar Chart comparing values.
        Specific use case: LTV vs Max LTV.
        """
        # Parse LTVs (remove % and convert to int)
        try:
            val_str = metrics.get("LTV Requested", "0%").replace("%", "")
            limit_str = metrics.get("Policy Limit", "0%").split("%")[0].split("(")[0].strip() # Handle "50% (Tier 2)"
            
            val = float(val_str)
            limit = float(limit_str)
            
            max_scale = max(val, limit, 100)
            val_pct = (val / max_scale) * 100
            limit_pct = (limit / max_scale) * 100
            
            bar_color = "#28a745" if val <= limit else "#dc3545" # Green if safe, Red if breach
            
            svg = f"""
            <svg width="100%" height="60" style="margin-top: 10px;">
                <!-- Background lines -->
                <line x1="0" y1="0" x2="0" y2="50" stroke="#555" stroke-width="1"/>
                <line x1="100%" y1="0" x2="100%" y2="50" stroke="#555" stroke-width="1"/>
                
                <!-- Limit Bar (Ghost) -->
                <rect x="0" y="10" width="{limit_pct}%" height="15" fill="none" stroke="#AAAAAA" stroke-width="1" stroke-dasharray="4"/>
                <text x="{limit_pct}%" y="40" fill="#AAAAAA" font-size="10" text-anchor="middle">Max {int(limit)}%</text>
                
                <!-- Value Bar -->
                <rect x="0" y="12" width="{val_pct}%" height="11" fill="{bar_color}" opacity="0.9"/>
                <text x="{val_pct}%" y="40" fill="{bar_color}" font-size="10" text-anchor="middle" font-weight="bold">{int(val)}%</text>
                
                <!-- Label -->
                <text x="0" y="40" fill="#DDD" font-size="10" text-anchor="start">0%</text>
                <text x="100%" y="40" fill="#DDD" font-size="10" text-anchor="end">{int(max_scale)}%</text>
            </svg>
            """
            return svg
        except Exception:
            return "<div class='chart-error'>Visualization unavailable for these metrics</div>"

    @staticmethod
    def generate_decision_card(title: str, decision: str, metrics: Dict[str, Any], reasoning_bullets: List[str]) -> Dict[str, Any]:
        """
        Generates a Decision Card (HTML) with Embedded Visualization.
        """
        badge_class = decision.lower()
        
        # Generate Chart
        chart_html = FlashCardGenerator._generate_svg_bar_chart(metrics)
        
        metrics_html = ""
        for k, v in metrics.items():
            metrics_html += f"""
            <div class="metric-row">
                <span class="metric-label">{k}</span>
                <span class="metric-value">{v}</span>
            </div>
            """
            
        bullets_html = "".join([f"<li>{r}</li>" for r in reasoning_bullets])
        
        html = f"""
        <html>
        <head>{FlashCardGenerator.STYLE_CSS}</head>
        <body>
            <div class="card-container">
                <div class="header">
                    <span class="title">{title}</span>
                    <span class="badge {badge_class}">{decision}</span>
                </div>
                
                <div class="section">
                    <div class="section-title">Key Financials</div>
                    {metrics_html}
                </div>
                
                <div class="section">
                    <div class="section-title">Compliance Visualization</div>
                    {chart_html}
                </div>
                
                <div class="section">
                    <div class="section-title">Reasoning Trace</div>
                    <div class="reasoning-text">
                        <ul>{bullets_html}</ul>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return {
            "id": f"card-{hash(title)}",
            "type": "decision_card",
            "styleName": "Flash Report",
            "status": "complete",
            "html": html
        }

if __name__ == "__main__":
    # Test
    card = FlashCardGenerator.generate_decision_card(
        "Project NeonFuture", 
        "FLAGGED", 
        {"LTV": "75%", "Max Allowed": "50%", "Tech": "Sodium-Ion"},
        ["LTV exceeds Tier 2 limit (50%)", "Missing Warranty Insurance"]
    )
    print(card["html"])
