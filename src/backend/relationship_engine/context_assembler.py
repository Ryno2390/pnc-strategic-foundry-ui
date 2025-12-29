"""
PNC Strategic Foundry - Context Assembler
==========================================
The "Bridge" between S1 Reasoning Model and the Relationship Store.

This module provides tool-use functions that S1 can call to retrieve
comprehensive Customer 360 views from the resolved relationship graph.

Functions Available to S1:
    - get_customer_360(entity_id_or_name): Full relationship view for a person
    - get_household_summary(household_name): Aggregated household financials
    - search_entities(query): Find entities by name search
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import re

# ============================================================================
# DATA PATHS
# ============================================================================
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "relationship_store"
RAW_DIR = DATA_DIR / "raw"
RESOLVED_DIR = DATA_DIR / "resolved"

# ============================================================================
# DATA CLASSES FOR TOOL RESPONSES
# ============================================================================

@dataclass
class Account:
    """Represents a financial account."""
    account_type: str
    account_number_masked: str
    balance: float
    source_system: str
    additional_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Portfolio:
    """Represents a wealth management portfolio."""
    name: str
    portfolio_type: str
    value: float
    beneficiaries: List[str] = field(default_factory=list)

@dataclass
class BusinessConnection:
    """Represents a business relationship."""
    business_name: str
    business_id: str
    role: str
    ownership_pct: Optional[float]
    accounts: List[Account] = field(default_factory=list)

@dataclass
class HouseholdMember:
    """Represents a household member."""
    name: str
    relationship: str
    entity_id: str
    personal_aum: float = 0.0

@dataclass
class Customer360:
    """Complete 360-degree view of a customer relationship."""
    entity_id: str
    canonical_name: str
    entity_type: str

    # Core demographics
    tax_id_last4: Optional[str] = None
    date_of_birth: Optional[str] = None
    primary_address: Optional[str] = None
    primary_phone: Optional[str] = None
    primary_email: Optional[str] = None

    # Financial holdings
    personal_accounts: List[Account] = field(default_factory=list)
    wealth_portfolios: List[Portfolio] = field(default_factory=list)

    # Relationships
    household_members: List[HouseholdMember] = field(default_factory=list)
    business_connections: List[BusinessConnection] = field(default_factory=list)

    # Aggregations
    total_personal_aum: float = 0.0
    total_business_exposure: float = 0.0
    total_household_aum: float = 0.0
    total_relationship_value: float = 0.0

    # Source systems
    source_systems: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

class Entitlement(Enum):
    RETAIL = "CONSUMER_CORE"
    COMMERCIAL = "COMMERCIAL_CORE"
    WEALTH = "WEALTH_ADVISORY"
    ADMIN = "ALL"

# ============================================================================
# CONTEXT ASSEMBLER CLASS
# ============================================================================

class ContextAssembler:
    """
    Entitlement-Aware Context Assembler.
    Ensures advisors only see data they are licensed to access.
    """

    def __init__(self):
        self.unified_entities = self._load_json(RESOLVED_DIR / "unified_entities.json")
        self.relationships = self._load_json(RESOLVED_DIR / "relationships.json")
        self.match_scores = self._load_json(RESOLVED_DIR / "match_scores.json")

    def _load_json(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        with open(path, "r") as f:
            return json.load(f)

    def get_customer_360(self, entity_id_or_name: str, entitlements: List[Entitlement] = None) -> Optional[Dict]:
        """
        Retrieves full Customer 360 view, filtered by entitlements.
        """
        # Default to ADMIN (all access) if not specified for backward compatibility
        if entitlements is None:
            entitlements = [Entitlement.ADMIN]

        # Find entity
        entity = None
        for e in self.unified_entities:
            if e["unified_id"] == entity_id_or_name or e["canonical_name"].upper() == entity_id_or_name.upper():
                entity = e
                break
        
        if not entity:
            return None

        # Filter sources based on entitlements
        is_admin = Entitlement.ADMIN in entitlements
        allowed_sources = [ent.value for ent in entitlements] if not is_admin else None
        
        filtered_records = []
        for rec in entity.get("source_records", []):
            if is_admin or rec["source"] in allowed_sources:
                filtered_records.append(rec)
        
        if not filtered_records:
            return {"status": "RESTRICTED", "message": "Advisor not entitled to view this entity's data."}

        # Build response
        # In a real implementation, we would reconstruct the Customer360 object
        # using only the entitled source records.
        res = entity.copy()
        res["source_records"] = filtered_records
        res["entitlements_applied"] = [e.name for e in entitlements]
        return res

    def get_household_summary(self, household_name: str) -> Dict[str, Any]:
        """
        TOOL: get_household_summary

        Retrieves aggregated financial summary for an entire household.

        Args:
            household_name: Last name of the household (e.g., "Smith")

        Returns:
            Dictionary with household members and combined financials

        Example S1 Usage:
            result = get_household_summary("Smith")
        """
        household_name_upper = household_name.upper().strip()

        # Find all entities with this last name
        household_members = []
        for entity in self.unified_entities:
            if entity['entity_type'] == 'PERSON':
                name_parts = entity['canonical_name'].split()
                if name_parts and name_parts[-1].upper() == household_name_upper:
                    c360 = self.get_customer_360(entity['unified_id'])
                    if c360:
                        household_members.append(c360)

        # Also find entities connected by SPOUSE relationship
        for member in list(household_members):
            source_ids = [src['id'] for src in self._get_entity_by_id(member.entity_id).get('source_records', [])]
            for src_id in source_ids:
                for rel in self.relationships_by_entity.get(src_id, []):
                    if rel['relationship_type'] == 'SPOUSE':
                        # Add the other party
                        other_id = rel['entity2_id'] if rel['entity1_id'] == src_id else rel['entity1_id']
                        # Find unified entity for this source ID
                        for entity in self.unified_entities:
                            for src in entity.get('source_records', []):
                                if src['id'] == other_id:
                                    if not any(m.entity_id == entity['unified_id'] for m in household_members):
                                        c360 = self.get_customer_360(entity['unified_id'])
                                        if c360:
                                            household_members.append(c360)

        # Aggregate financials
        total_personal_aum = sum(m.total_personal_aum for m in household_members)
        total_business_exposure = sum(m.total_business_exposure for m in household_members)

        # Find unique businesses connected to household
        connected_businesses = {}
        for member in household_members:
            for biz in member.business_connections:
                if biz.business_id not in connected_businesses:
                    connected_businesses[biz.business_id] = biz

        return {
            "household_name": household_name,
            "members": [
                {
                    "name": m.canonical_name,
                    "entity_id": m.entity_id,
                    "personal_aum": m.total_personal_aum,
                    "accounts_count": len(m.personal_accounts) + len(m.wealth_portfolios)
                }
                for m in household_members
            ],
            "connected_businesses": [
                {
                    "name": b.business_name,
                    "role": b.role,
                    "ownership_pct": b.ownership_pct
                }
                for b in connected_businesses.values()
            ],
            "totals": {
                "personal_aum": total_personal_aum,
                "business_exposure": total_business_exposure,
                "total_relationship_value": total_personal_aum + total_business_exposure,
                "member_count": len(household_members),
                "business_count": len(connected_businesses)
            }
        }

    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        TOOL: search_entities

        Searches for entities by name (fuzzy matching).

        Args:
            query: Search string (e.g., "Smith", "Johnson Properties")

        Returns:
            List of matching entities with basic info

        Example S1 Usage:
            results = search_entities("Smith")
        """
        query_upper = query.upper().strip()
        results = []

        for entity in self.unified_entities:
            name = entity['canonical_name']
            # Simple contains match
            if query_upper in name.upper():
                results.append({
                    "entity_id": entity['unified_id'],
                    "name": name,
                    "type": entity['entity_type'],
                    "sources": [src['source'] for src in entity.get('source_records', [])]
                })

        return results

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _find_entity(self, entity_id_or_name: str) -> Optional[Dict]:
        """Find entity by ID or name."""
        # Try direct ID lookup
        if entity_id_or_name.startswith('UNI-'):
            return self.entity_by_id.get(entity_id_or_name)

        # Try name lookup (exact match first)
        name_key = entity_id_or_name.upper().strip()
        if name_key in self.entity_by_name:
            return self.entity_by_name[name_key][0]

        # Fuzzy name search
        for name, entities in self.entity_by_name.items():
            if name_key in name or name in name_key:
                return entities[0]
            # Also check for partial matches
            name_parts = name_key.split()
            if any(part in name for part in name_parts):
                return entities[0]

        return None

    def _get_entity_by_id(self, unified_id: str) -> Dict:
        """Get entity by unified ID."""
        return self.entity_by_id.get(unified_id, {})

    def _add_consumer_accounts(self, c360: Customer360, consumer_id: str):
        """Add consumer banking accounts to Customer360."""
        record = self.consumer_by_id.get(consumer_id)
        if not record:
            return

        for acct in record.get('accounts', []):
            c360.personal_accounts.append(Account(
                account_type=acct['type'],
                account_number_masked=acct['number'],
                balance=acct['balance'],
                source_system='CONSUMER_CORE',
                additional_info={'opened': acct.get('opened'), 'rate': acct.get('rate'), 'limit': acct.get('limit')}
            ))

    def _add_wealth_portfolios(self, c360: Customer360, wealth_id: str):
        """Add wealth management portfolios to Customer360."""
        record = self.wealth_by_id.get(wealth_id)
        if not record:
            return

        for port in record.get('portfolios', []):
            c360.wealth_portfolios.append(Portfolio(
                name=port['name'],
                portfolio_type=port['type'],
                value=port['value'],
                beneficiaries=port.get('beneficiaries', [])
            ))

    def _add_relationships(self, c360: Customer360, entity: Dict):
        """Add household and business relationships."""
        # Get source IDs for this entity
        source_ids = [src['id'] for src in entity.get('source_records', [])]

        for src_id in source_ids:
            for rel in self.relationships_by_entity.get(src_id, []):
                other_id = rel['entity2_id'] if rel['entity1_id'] == src_id else rel['entity1_id']
                other_name = rel['entity2_name'] if rel['entity1_id'] == src_id else rel['entity1_name']

                if rel['relationship_type'] == 'SPOUSE':
                    # Add as household member
                    if not any(h.name == other_name for h in c360.household_members):
                        c360.household_members.append(HouseholdMember(
                            name=other_name,
                            relationship='Spouse',
                            entity_id=other_id
                        ))

                elif rel['relationship_type'] == 'BUSINESS_OWNER':
                    # Add business connection
                    biz_record = self.commercial_by_id.get(other_id)
                    if biz_record and not any(b.business_id == other_id for b in c360.business_connections):
                        # Find ownership info
                        ownership_pct = None
                        role = "Owner"
                        for signer in biz_record.get('authorized_signers', []):
                            name_parts = entity['canonical_name'].split()
                            if any(part.upper() in signer['name'].upper() for part in name_parts):
                                ownership_pct = signer.get('ownership_pct')
                                role = signer.get('title', 'Owner')
                                break

                        # Get business accounts
                        biz_accounts = []
                        for acct in biz_record.get('accounts', []):
                            biz_accounts.append(Account(
                                account_type=acct['type'],
                                account_number_masked=acct['number'],
                                balance=acct.get('balance', 0),
                                source_system='COMMERCIAL_CORE',
                                additional_info={
                                    'limit': acct.get('limit'),
                                    'rate': acct.get('rate')
                                }
                            ))

                        c360.business_connections.append(BusinessConnection(
                            business_name=biz_record['legal_name'],
                            business_id=other_id,
                            role=role,
                            ownership_pct=ownership_pct,
                            accounts=biz_accounts
                        ))

        # Also check for household members from wealth data
        for src in entity.get('source_records', []):
            if src['source'] == 'WEALTH_ADVISORY':
                record = self.wealth_by_id.get(src['id'])
                if record:
                    for member_str in record.get('household_members', []):
                        # Parse "Jane M. Smith (Spouse)" format
                        match = re.match(r'(.+?)\s*\((.+?)\)', member_str)
                        if match:
                            member_name, relationship = match.groups()
                            if not any(h.name.upper() == member_name.upper().strip() for h in c360.household_members):
                                c360.household_members.append(HouseholdMember(
                                    name=member_name.strip(),
                                    relationship=relationship.strip(),
                                    entity_id=""  # Unknown without resolution
                                ))

    def _calculate_totals(self, c360: Customer360):
        """Calculate aggregated totals."""
        # Personal accounts (positive balances only for AUM)
        c360.total_personal_aum = sum(
            max(0, acct.balance) for acct in c360.personal_accounts
        )

        # Add wealth portfolios
        c360.total_personal_aum += sum(p.value for p in c360.wealth_portfolios)

        # Business exposure (their ownership share)
        for biz in c360.business_connections:
            biz_value = sum(max(0, acct.balance) for acct in biz.accounts)
            ownership_factor = (biz.ownership_pct or 100) / 100
            c360.total_business_exposure += biz_value * ownership_factor

        # Total relationship value
        c360.total_relationship_value = c360.total_personal_aum + c360.total_business_exposure

# ============================================================================
# TOOL REGISTRY (For S1 Integration)
# ============================================================================

# Global instance for tool calls
_assembler = None

def get_assembler() -> ContextAssembler:
    """Get or create the global ContextAssembler instance."""
    global _assembler
    if _assembler is None:
        _assembler = ContextAssembler()
    return _assembler

# Tool definitions for S1
AVAILABLE_TOOLS = {
    "get_customer_360": {
        "description": "Retrieves complete 360-degree view of a customer including all accounts, portfolios, household members, and business connections.",
        "parameters": {
            "entity_id_or_name": {
                "type": "string",
                "description": "Customer name (e.g., 'John Smith') or entity ID (e.g., 'UNI-0003')"
            }
        },
        "returns": "Customer360 object with all financial and relationship data"
    },
    "get_household_summary": {
        "description": "Retrieves aggregated financial summary for an entire household by last name.",
        "parameters": {
            "household_name": {
                "type": "string",
                "description": "Last name of the household (e.g., 'Smith')"
            }
        },
        "returns": "Dictionary with all household members and combined financials"
    },
    "search_entities": {
        "description": "Searches for customers and businesses by name.",
        "parameters": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'Smith', 'Johnson Properties')"
            }
        },
        "returns": "List of matching entities with basic info"
    }
}

def execute_tool(tool_name: str, **kwargs) -> Any:
    """Execute a tool by name with given parameters."""
    assembler = get_assembler()

    if tool_name == "get_customer_360":
        result = assembler.get_customer_360(kwargs.get('entity_id_or_name', ''))
        return result.to_dict() if result else {"error": "Customer not found"}

    elif tool_name == "get_household_summary":
        return assembler.get_household_summary(kwargs.get('household_name', ''))

    elif tool_name == "search_entities":
        return assembler.search_entities(kwargs.get('query', ''))

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ============================================================================
# DEMO / TEST
# ============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("PNC CONTEXT ASSEMBLER - TOOL-USE DEMONSTRATION")
    print("=" * 80)

    assembler = ContextAssembler()

    # Demo 1: Get Customer 360 for John Smith
    print("\n" + "─" * 80)
    print("TOOL CALL: get_customer_360('John Smith')")
    print("─" * 80)

    john = assembler.get_customer_360("John Smith")
    if john:
        print(f"\n📋 CUSTOMER 360: {john.canonical_name}")
        print(f"   Entity ID: {john.entity_id}")
        print(f"   DOB: {john.date_of_birth}")
        print(f"   Address: {john.primary_address}")
        print(f"   Phone: {john.primary_phone}")
        print(f"   Source Systems: {', '.join(john.source_systems)}")

        print(f"\n💳 PERSONAL ACCOUNTS ({len(john.personal_accounts)}):")
        for acct in john.personal_accounts:
            print(f"   • {acct.account_type}: {acct.account_number_masked} = ${acct.balance:,.2f}")

        print(f"\n📈 WEALTH PORTFOLIOS ({len(john.wealth_portfolios)}):")
        for port in john.wealth_portfolios:
            print(f"   • {port.name} ({port.portfolio_type}): ${port.value:,.2f}")
            if port.beneficiaries:
                print(f"     Beneficiaries: {', '.join(port.beneficiaries)}")

        print(f"\n👨‍👩‍👧‍👦 HOUSEHOLD ({len(john.household_members)}):")
        for member in john.household_members:
            print(f"   • {member.name} ({member.relationship})")

        print(f"\n🏢 BUSINESS CONNECTIONS ({len(john.business_connections)}):")
        for biz in john.business_connections:
            print(f"   • {biz.business_name}")
            print(f"     Role: {biz.role} ({biz.ownership_pct}% ownership)")
            for acct in biz.accounts:
                print(f"     → {acct.account_type}: ${acct.balance:,.2f}")

        print(f"\n💰 FINANCIAL SUMMARY:")
        print(f"   Personal AUM:        ${john.total_personal_aum:>15,.2f}")
        print(f"   Business Exposure:   ${john.total_business_exposure:>15,.2f}")
        print(f"   ─────────────────────────────────────")
        print(f"   TOTAL RELATIONSHIP:  ${john.total_relationship_value:>15,.2f}")

    # Demo 2: Household Summary
    print("\n" + "─" * 80)
    print("TOOL CALL: get_household_summary('Smith')")
    print("─" * 80)

    household = assembler.get_household_summary("Smith")
    print(f"\n🏠 SMITH HOUSEHOLD SUMMARY")
    print(f"\n   Members ({household['totals']['member_count']}):")
    for member in household['members']:
        print(f"   • {member['name']}: ${member['personal_aum']:,.2f} ({member['accounts_count']} accounts)")

    print(f"\n   Connected Businesses ({household['totals']['business_count']}):")
    for biz in household['connected_businesses']:
        print(f"   • {biz['name']} - {biz['role']} ({biz['ownership_pct']}%)")

    print(f"\n   💰 HOUSEHOLD TOTALS:")
    print(f"   Personal AUM:           ${household['totals']['personal_aum']:>15,.2f}")
    print(f"   Business Exposure:      ${household['totals']['business_exposure']:>15,.2f}")
    print(f"   ─────────────────────────────────────────")
    print(f"   TOTAL RELATIONSHIP:     ${household['totals']['total_relationship_value']:>15,.2f}")

    print("\n" + "=" * 80)
