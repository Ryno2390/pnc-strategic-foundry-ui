"PNC Strategic Foundry - Synthetic Data Factory (Teacher -> Student Distillation)
================================================================================
This script uses the Large "Teacher" Model (via API) to generate a high-quality
fine-tuning dataset for the Small "Student" Model.

Process:
1. Load Policy.
2. Generate diverse scenarios (Approvals, Denials, Edge Cases).
3. Generate the "Perfect Reasoning Trace" (System 2 Checklist).
4. Export to JSONL format for MLX/Qwen fine-tuning.
"

import os
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("PNC.SyntheticFactory")

class SyntheticDataFactory:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.teacher_model = None
        self.policy_text = ""
        self._load_policy()

    def _load_policy(self):
        # Load the Green Energy Policy
        policy_path = Path("data/policies/pnc_green_energy_transition_policy.md")
        if policy_path.exists():
            with open(policy_path, "r") as f:
                self.policy_text = f.read()
        else:
            raise FileNotFoundError(f"Policy not found at {policy_path}")

    def create_dataset(self, count: int = 100):
        # We'll create specialized datasets for each system
        consumer_records = []
        commercial_records = []
        wealth_records = []
        
        # Create base identities
        for i in range(count):
            first = random.choice(self.FIRST_NAMES)
            last = random.choice(self.LAST_NAMES)
            ssn = str(random.randint(1000, 9999))
            dob = f"{random.randint(1950, 2005)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            addr = f"{random.randint(100,9999)} {random.choice(self.STREETS)}"
            city = random.choice(self.CITIES)
            zip5 = str(random.randint(15000, 19999))
            phone = f"({random.randint(200,999)}) 555-{random.randint(1000,9999)}"

            # 1. Consumer Core Record
            if random.random() < 0.8:
                consumer_records.append({
                    "customer_id": f"CON-{random.randint(10000, 99999)}",
                    "first_name": first,
                    "last_name": last,
                    "ssn_last4": ssn,
                    "date_of_birth": dob,
                    "address_line1": addr,
                    "city": city,
                    "state": "PA",
                    "zip": zip5,
                    "phone_primary": phone,
                    "email": f"{first.lower()}.{last.lower()}@pnc-test.com"
                })

            # 2. Commercial Core Record
            if random.random() < 0.4:
                biz_name = f"{last} {random.choice(['Consulting', 'Properties', 'Ventures', 'Group'])} LLC"
                commercial_records.append({
                    "business_id": f"BIZ-{random.randint(10000, 99999)}",
                    "legal_name": biz_name,
                    "ein": f"99-{random.randint(1000000, 9999999)}",
                    "business_address": addr,
                    "business_city": city,
                    "business_state": "PA",
                    "business_zip": zip5,
                    "primary_contact": f"{first} {last}",
                    "contact_phone": phone,
                    "contact_email": f"{first.lower()}@{last.lower()}biz.com",
                    "contact_ssn_last4": ssn,
                    "authorized_signers": [{"name": f"{first} {last}", "role": "OWNER"}]
                })

            # 3. Wealth Advisory Record
            if random.random() < 0.3:
                wealth_records.append({
                    "client_id": f"WM-{random.randint(10000, 99999)}",
                    "client_name": f"{first} {random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')} {last}",
                    "tax_id_last4": ssn,
                    "birth_date": dob,
                    "residence": {"street": addr, "city": city, "state": "PA", "postal": zip5},
                    "phone": phone,
                    "email": f"{first.lower()}@wealth-pnc.com",
                    "household_members": [f"{first} {last} (Head)"]
                })

        # Save with wrappers expected by normalization_engine
        datasets = [
            ("CONSUMER_CORE", "consumer_banking.json", consumer_records),
            ("COMMERCIAL_CORE", "commercial_banking.json", commercial_records),
            ("WEALTH_ADVISORY", "wealth_management.json", wealth_records)
        ]
        
        for source, filename, records in datasets:
            path = self.output_dir / filename
            output = {
                "source_system": source,
                "extraction_date": datetime.now().isoformat(),
                "records": records
            }
            with open(path, "w") as f:
                json.dump(output, f, indent=2)
            print(f"Generated {len(records)} records for {source} in {filename}")

if __name__ == "__main__":
    factory = SyntheticEntityFactory()
    factory.create_dataset(count=50)