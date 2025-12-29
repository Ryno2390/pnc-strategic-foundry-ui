import json
from pathlib import Path
from src.backend.cross_sell_engine import CrossSellOptimizer

def test_business_intelligence():
    print("=== Testing Business Intelligence Engines ===")
    project_root = Path(__file__).parent.parent.parent.parent
    data_dir = project_root / "data" / "relationship_store" / "resolved"
    
    # 1. Cross-Sell Optimizer
    print("\n1. Touching Cross-Sell Optimizer...")
    optimizer = CrossSellOptimizer(data_dir=str(data_dir))
    opps = optimizer.analyze_opportunities()
    print(f"   Found {len(opps)} Cross-Sell Opportunities")
    
    if opps:
        # Show the highest priority one
        high_pri = [o for o in opps if o['priority'] == 'HIGH']
        print(f"   High Priority Opportunities: {len(high_pri)}")
        if high_pri:
            print(f"   Example: {high_pri[0]['name']} -> {high_pri[0]['opportunity']}")
    
    assert len(opps) > 0

if __name__ == "__main__":
    test_business_intelligence()
