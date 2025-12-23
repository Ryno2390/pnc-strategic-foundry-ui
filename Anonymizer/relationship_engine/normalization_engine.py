#!/usr/bin/env python3
"""
PNC Strategic Foundry - Relationship Engine
Normalization Engine
============================================

Ingests siloed data from Consumer, Commercial, and Wealth systems
and normalizes it into a unified format for identity resolution.

Confidence Thresholds:
- HIGH (0.95+): Auto-merge records
- MEDIUM (0.70-0.94): Human-in-the-loop - AI asks advisor
- LOW (<0.70): Keep separate
"""

from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Normalization")


# =============================================================================
# Constants
# =============================================================================

# State abbreviations
STATE_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY"
}

# Address abbreviations
ADDRESS_ABBREV = {
    "street": "ST", "st": "ST", "str": "ST",
    "avenue": "AVE", "ave": "AVE", "av": "AVE",
    "road": "RD", "rd": "RD",
    "drive": "DR", "dr": "DR",
    "lane": "LN", "ln": "LN",
    "boulevard": "BLVD", "blvd": "BLVD",
    "court": "CT", "ct": "CT",
    "circle": "CIR", "cir": "CIR",
    "place": "PL", "pl": "PL",
    "apartment": "APT", "apt": "APT", "apt.": "APT",
    "suite": "STE", "ste": "STE", "ste.": "STE",
    "unit": "UNIT", "un": "UNIT",
    "floor": "FL", "fl": "FL",
    "building": "BLDG", "bldg": "BLDG",
}

# Name prefixes/suffixes to normalize
NAME_PREFIXES = {"dr", "dr.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "prof", "prof."}
NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "esq", "esq.", "phd", "md"}


# =============================================================================
# Confidence Levels
# =============================================================================

class ConfidenceLevel(Enum):
    HIGH = "HIGH"       # 0.95+ : Auto-merge
    MEDIUM = "MEDIUM"   # 0.70-0.94 : Human-in-the-loop
    LOW = "LOW"         # <0.70 : Keep separate


def get_confidence_level(score: float) -> ConfidenceLevel:
    """Determine confidence level from score."""
    if score >= 0.95:
        return ConfidenceLevel.HIGH
    elif score >= 0.70:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NormalizedName:
    """Normalized person name."""
    full_name: str           # "JOHN ROBERT SMITH"
    first_name: str          # "JOHN"
    middle_name: str         # "ROBERT"
    last_name: str           # "SMITH"
    suffix: str              # "JR"
    original: str            # Original input

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedAddress:
    """Normalized address."""
    street_line1: str        # "123 MAIN ST"
    street_line2: str        # "APT 4B"
    city: str                # "PITTSBURGH"
    state: str               # "PA"
    zip5: str                # "15213"
    zip4: str                # "4521"
    full_address: str        # Combined for matching
    original: str            # Original input

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedPhone:
    """Normalized phone number."""
    number: str              # "4125551234"
    formatted: str           # "(412) 555-1234"
    area_code: str           # "412"
    original: str            # Original input

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedEntity:
    """A normalized entity (person or business) ready for identity resolution."""

    # Source information
    source_system: str
    source_id: str
    entity_type: str         # "PERSON" or "BUSINESS"

    # Identity fields (for matching)
    name: NormalizedName
    tax_id_last4: str        # SSN or EIN last 4
    date_of_birth: Optional[str]  # ISO format

    # Contact fields
    address: NormalizedAddress
    phone_primary: Optional[NormalizedPhone]
    phone_mobile: Optional[NormalizedPhone]
    email: str               # Lowercase, trimmed

    # Relationships (for linking)
    related_entities: list[str] = field(default_factory=list)  # Names of related people
    business_affiliations: list[str] = field(default_factory=list)  # Business names

    # Original data
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_system": self.source_system,
            "source_id": self.source_id,
            "entity_type": self.entity_type,
            "name": self.name.to_dict(),
            "tax_id_last4": self.tax_id_last4,
            "date_of_birth": self.date_of_birth,
            "address": self.address.to_dict(),
            "phone_primary": self.phone_primary.to_dict() if self.phone_primary else None,
            "phone_mobile": self.phone_mobile.to_dict() if self.phone_mobile else None,
            "email": self.email,
            "related_entities": self.related_entities,
            "business_affiliations": self.business_affiliations,
        }


# =============================================================================
# Normalization Functions
# =============================================================================

class Normalizer:
    """Normalizes various data formats."""

    @staticmethod
    def normalize_name(name_input: str | dict) -> NormalizedName:
        """
        Normalize a person's name.

        Handles:
        - "John Smith"
        - "J. Smith"
        - "John R. Smith"
        - "Dr. John Smith Jr."
        - {"first_name": "John", "last_name": "Smith"}
        """
        if isinstance(name_input, dict):
            first = name_input.get("first_name", "")
            middle = name_input.get("middle_initial", "") or name_input.get("middle_name", "")
            last = name_input.get("last_name", "")
            name_str = f"{first} {middle} {last}".strip()
        else:
            name_str = str(name_input)

        original = name_str

        # Uppercase and clean
        name_str = name_str.upper().strip()
        name_str = re.sub(r'\s+', ' ', name_str)  # Multiple spaces to single

        # Remove prefixes
        parts = name_str.split()
        while parts and parts[0].lower().rstrip('.') in NAME_PREFIXES:
            parts.pop(0)

        # Extract suffix
        suffix = ""
        if parts and parts[-1].lower().rstrip('.') in NAME_SUFFIXES:
            suffix = parts.pop().rstrip('.')

        # Parse remaining parts
        if len(parts) == 0:
            first_name, middle_name, last_name = "", "", ""
        elif len(parts) == 1:
            first_name, middle_name, last_name = parts[0], "", ""
        elif len(parts) == 2:
            first_name, last_name = parts[0], parts[1]
            middle_name = ""
        else:
            first_name = parts[0]
            last_name = parts[-1]
            middle_name = " ".join(parts[1:-1])

        # Clean initials (remove periods)
        first_name = first_name.rstrip('.')
        middle_name = middle_name.rstrip('.')

        # Full name for matching
        full_parts = [first_name]
        if middle_name:
            full_parts.append(middle_name)
        full_parts.append(last_name)
        full_name = " ".join(full_parts)

        return NormalizedName(
            full_name=full_name,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            suffix=suffix,
            original=original
        )

    @staticmethod
    def normalize_address(
        line1: str = "",
        line2: str = "",
        city: str = "",
        state: str = "",
        zip_code: str = ""
    ) -> NormalizedAddress:
        """
        Normalize an address to standard format.

        Handles:
        - "123 Main St" vs "123 Main Street"
        - "Apt 4B" vs "Apt. 4B" vs "Apartment 4B"
        - "PA" vs "Pennsylvania"
        - "15213" vs "15213-4521"
        """
        original = f"{line1}, {line2}, {city}, {state} {zip_code}".strip(", ")

        # Combine line1 and line2 if line2 is embedded
        if "," in line1 and not line2:
            parts = line1.split(",", 1)
            line1 = parts[0].strip()
            line2 = parts[1].strip() if len(parts) > 1 else ""

        # Uppercase
        line1 = line1.upper().strip()
        line2 = line2.upper().strip()
        city = city.upper().strip()
        state = state.upper().strip()

        # Normalize street abbreviations
        def normalize_street(s: str) -> str:
            words = s.split()
            result = []
            for word in words:
                clean_word = word.rstrip('.,')
                if clean_word.lower() in ADDRESS_ABBREV:
                    result.append(ADDRESS_ABBREV[clean_word.lower()])
                else:
                    result.append(word.rstrip('.'))
            return " ".join(result)

        line1 = normalize_street(line1)
        line2 = normalize_street(line2)

        # Handle "#" notation -> "APT"
        line1 = re.sub(r'#\s*(\w+)', r'APT \1', line1)
        line2 = re.sub(r'#\s*(\w+)', r'APT \1', line2)

        # Normalize state
        state_lower = state.lower()
        if state_lower in STATE_ABBREV:
            state = STATE_ABBREV[state_lower]
        elif len(state) == 2:
            state = state.upper()

        # Normalize ZIP
        zip_clean = re.sub(r'[^\d]', '', zip_code)
        zip5 = zip_clean[:5] if len(zip_clean) >= 5 else zip_clean
        zip4 = zip_clean[5:9] if len(zip_clean) > 5 else ""

        # Full address for matching
        full_parts = [line1]
        if line2:
            full_parts.append(line2)
        full_parts.append(city)
        full_parts.append(state)
        full_parts.append(zip5)
        full_address = " ".join(full_parts)

        return NormalizedAddress(
            street_line1=line1,
            street_line2=line2,
            city=city,
            state=state,
            zip5=zip5,
            zip4=zip4,
            full_address=full_address,
            original=original
        )

    @staticmethod
    def normalize_phone(phone: str | None) -> Optional[NormalizedPhone]:
        """
        Normalize phone number to standard format.

        Handles:
        - "(412) 555-1234"
        - "412-555-1234"
        - "412.555.1234"
        - "4125551234"
        - "+1 (412) 555-1234"
        """
        if not phone:
            return None

        original = str(phone)

        # Extract digits only
        digits = re.sub(r'[^\d]', '', phone)

        # Remove country code if present
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]

        if len(digits) != 10:
            return None  # Invalid phone

        area_code = digits[:3]
        formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

        return NormalizedPhone(
            number=digits,
            formatted=formatted,
            area_code=area_code,
            original=original
        )

    @staticmethod
    def normalize_date(date_str: str | None) -> Optional[str]:
        """
        Normalize date to ISO format (YYYY-MM-DD).

        Handles:
        - "03/15/1975"
        - "1975-03-15"
        - "03-15-1975"
        - "1975/03/15"
        - "11-03-1968"
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Try various formats
        formats = [
            "%Y-%m-%d",      # 1975-03-15
            "%m/%d/%Y",      # 03/15/1975
            "%m-%d-%Y",      # 03-15-1975
            "%Y/%m/%d",      # 1975/03/15
            "%d-%m-%Y",      # 15-03-1975 (European)
            "%m/%d/%y",      # 03/15/75
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None  # Could not parse

    @staticmethod
    def normalize_email(email: str | None) -> str:
        """Normalize email to lowercase, trimmed."""
        if not email:
            return ""
        return str(email).lower().strip()


# =============================================================================
# Data Loaders
# =============================================================================

class DataLoader:
    """Loads and normalizes data from source systems."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.normalizer = Normalizer()

    def load_consumer(self) -> list[NormalizedEntity]:
        """Load and normalize Consumer Banking data."""
        path = self.data_dir / "raw" / "consumer_banking.json"

        with open(path, "r") as f:
            data = json.load(f)

        entities = []
        source_system = data["source_system"]

        for record in data["records"]:
            # Normalize name
            name = self.normalizer.normalize_name({
                "first_name": record.get("first_name", ""),
                "middle_initial": record.get("middle_initial", ""),
                "last_name": record.get("last_name", "")
            })

            # Normalize address
            address = self.normalizer.normalize_address(
                line1=record.get("address_line1", ""),
                line2=record.get("address_line2", ""),
                city=record.get("city", ""),
                state=record.get("state", ""),
                zip_code=record.get("zip", "")
            )

            # Normalize phones
            phone_primary = self.normalizer.normalize_phone(record.get("phone_primary"))
            phone_mobile = self.normalizer.normalize_phone(record.get("phone_mobile"))

            # Normalize date
            dob = self.normalizer.normalize_date(record.get("date_of_birth"))

            # Extract relationships
            related = []
            if record.get("joint_owner"):
                related.append(record["joint_owner"])

            entity = NormalizedEntity(
                source_system=source_system,
                source_id=record["customer_id"],
                entity_type="PERSON",
                name=name,
                tax_id_last4=record.get("ssn_last4", ""),
                date_of_birth=dob,
                address=address,
                phone_primary=phone_primary,
                phone_mobile=phone_mobile,
                email=self.normalizer.normalize_email(record.get("email")),
                related_entities=related,
                business_affiliations=[],
                raw_data=record
            )

            entities.append(entity)

        logger.info(f"Loaded {len(entities)} entities from {source_system}")
        return entities

    def load_commercial(self) -> list[NormalizedEntity]:
        """Load and normalize Commercial Banking data."""
        path = self.data_dir / "raw" / "commercial_banking.json"

        with open(path, "r") as f:
            data = json.load(f)

        entities = []
        source_system = data["source_system"]

        for record in data["records"]:
            # Create business entity
            business_name = self.normalizer.normalize_name(record.get("legal_name", ""))

            business_address = self.normalizer.normalize_address(
                line1=record.get("business_address", ""),
                city=record.get("business_city", ""),
                state=record.get("business_state", ""),
                zip_code=record.get("business_zip", "")
            )

            business_entity = NormalizedEntity(
                source_system=source_system,
                source_id=record["business_id"],
                entity_type="BUSINESS",
                name=business_name,
                tax_id_last4=record.get("ein", "")[-4:] if record.get("ein") else "",
                date_of_birth=None,
                address=business_address,
                phone_primary=self.normalizer.normalize_phone(record.get("contact_phone")),
                phone_mobile=None,
                email=self.normalizer.normalize_email(record.get("contact_email")),
                related_entities=[s["name"] for s in record.get("authorized_signers", [])],
                business_affiliations=[],
                raw_data=record
            )
            entities.append(business_entity)

            # Create person entity for primary contact
            contact_name = self.normalizer.normalize_name(record.get("primary_contact", ""))

            # Use mailing address for contact if different
            mailing = record.get("mailing_address", "")
            if mailing and mailing.lower() != "same":
                contact_address = self.normalizer.normalize_address(
                    line1=mailing,
                    city=record.get("mailing_city", ""),
                    state=record.get("mailing_state", ""),
                    zip_code=record.get("mailing_zip", "")
                )
            else:
                contact_address = business_address

            contact_entity = NormalizedEntity(
                source_system=source_system,
                source_id=f"{record['business_id']}-CONTACT",
                entity_type="PERSON",
                name=contact_name,
                tax_id_last4=record.get("contact_ssn_last4", ""),
                date_of_birth=None,
                address=contact_address,
                phone_primary=self.normalizer.normalize_phone(record.get("contact_phone")),
                phone_mobile=None,
                email=self.normalizer.normalize_email(record.get("contact_email")),
                related_entities=[],
                business_affiliations=[record.get("legal_name", "")],
                raw_data=record
            )
            entities.append(contact_entity)

        logger.info(f"Loaded {len(entities)} entities from {source_system}")
        return entities

    def load_wealth(self) -> list[NormalizedEntity]:
        """Load and normalize Wealth Management data."""
        path = self.data_dir / "raw" / "wealth_management.json"

        with open(path, "r") as f:
            data = json.load(f)

        entities = []
        source_system = data["source_system"]

        for record in data["records"]:
            # Normalize name
            name = self.normalizer.normalize_name(record.get("client_name", ""))

            # Normalize address
            residence = record.get("residence", {})
            address = self.normalizer.normalize_address(
                line1=residence.get("street", ""),
                city=residence.get("city", ""),
                state=residence.get("state", ""),
                zip_code=residence.get("postal", "")
            )

            # Normalize phones
            phone_primary = self.normalizer.normalize_phone(record.get("phone"))
            phone_mobile = self.normalizer.normalize_phone(record.get("mobile"))

            # Normalize date
            dob = self.normalizer.normalize_date(record.get("birth_date"))

            # Extract relationships from household
            related = []
            for member in record.get("household_members", []):
                # Extract name part (before parenthetical)
                member_name = re.sub(r'\s*\([^)]*\)', '', member).strip()
                related.append(member_name)

            entity = NormalizedEntity(
                source_system=source_system,
                source_id=record["client_id"],
                entity_type="PERSON",
                name=name,
                tax_id_last4=record.get("tax_id_last4", ""),
                date_of_birth=dob,
                address=address,
                phone_primary=phone_primary,
                phone_mobile=phone_mobile,
                email=self.normalizer.normalize_email(record.get("email")),
                related_entities=related,
                business_affiliations=[],
                raw_data=record
            )

            entities.append(entity)

        logger.info(f"Loaded {len(entities)} entities from {source_system}")
        return entities

    def load_all(self) -> list[NormalizedEntity]:
        """Load all data sources."""
        entities = []
        entities.extend(self.load_consumer())
        entities.extend(self.load_commercial())
        entities.extend(self.load_wealth())
        logger.info(f"Total entities loaded: {len(entities)}")
        return entities


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Demonstrate normalization engine."""

    data_dir = Path(__file__).parent / "data"
    loader = DataLoader(data_dir)

    print("\n" + "=" * 70)
    print("PNC RELATIONSHIP ENGINE - NORMALIZATION DEMO")
    print("=" * 70)

    # Load all data
    entities = loader.load_all()

    print("\n" + "-" * 70)
    print("NORMALIZED ENTITIES")
    print("-" * 70)

    # Group by source
    by_source = {}
    for e in entities:
        by_source.setdefault(e.source_system, []).append(e)

    for source, source_entities in by_source.items():
        print(f"\n{source}:")
        print("-" * 40)

        for entity in source_entities:
            entity_type = "PERSON" if entity.entity_type == "PERSON" else "BIZ"
            print(f"\n  [{entity_type}] {entity.name.full_name}")
            print(f"    Source ID:    {entity.source_id}")
            print(f"    Tax ID Last4: {entity.tax_id_last4}")
            if entity.date_of_birth:
                print(f"    DOB:          {entity.date_of_birth}")
            print(f"    Address:      {entity.address.street_line1}")
            if entity.address.street_line2:
                print(f"                  {entity.address.street_line2}")
            print(f"                  {entity.address.city}, {entity.address.state} {entity.address.zip5}")
            if entity.phone_primary:
                print(f"    Phone:        {entity.phone_primary.formatted}")
            if entity.email:
                print(f"    Email:        {entity.email}")
            if entity.related_entities:
                print(f"    Related:      {', '.join(entity.related_entities)}")
            if entity.business_affiliations:
                print(f"    Business:     {', '.join(entity.business_affiliations)}")

    # Save normalized data
    output_path = data_dir / "normalized" / "all_entities.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        json.dump([e.to_dict() for e in entities], f, indent=2)

    print("\n" + "=" * 70)
    print(f"Normalized data saved to: {output_path}")
    print("=" * 70)

    # Show potential matches preview
    print("\n" + "-" * 70)
    print("POTENTIAL MATCHES (Preview)")
    print("-" * 70)

    # Find people with same last4 SSN across systems
    persons = [e for e in entities if e.entity_type == "PERSON" and e.tax_id_last4]
    by_ssn = {}
    for p in persons:
        by_ssn.setdefault(p.tax_id_last4, []).append(p)

    for ssn4, matches in by_ssn.items():
        if len(matches) > 1:
            sources = set(m.source_system for m in matches)
            if len(sources) > 1:  # Cross-system match
                print(f"\n  Tax ID ***-**-{ssn4}:")
                for m in matches:
                    print(f"    - {m.name.full_name} ({m.source_system})")

    print("\n" + "=" * 70)
    print("Next: Run Identity Resolution to calculate match confidence scores")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
