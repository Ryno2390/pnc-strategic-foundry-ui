#!/usr/bin/env python3
"""
PNC Strategic Foundry - Relationship Engine
Identity Resolution Engine
============================================

Matches normalized entities across systems using weighted scoring.
Infers relationships (HOUSEHOLD, BUSINESS_OWNER, etc.) from shared attributes.

Confidence Thresholds:
- HIGH (0.95+): Auto-merge records
- MEDIUM (0.70-0.94): Human-in-the-loop - AI asks advisor
- LOW (<0.70): Keep separate

Weighted Scoring Algorithm:
- SSN/TIN Last4 Match: 0.40 (strongest signal)
- DOB Match: 0.20
- Name Similarity: 0.15
- Address Match: 0.15
- Phone Match: 0.05
- Email Match: 0.05
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Optional
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Identity.Resolution")


# =============================================================================
# Constants & Enums
# =============================================================================

class ConfidenceLevel(Enum):
    HIGH = "HIGH"       # 0.95+ : Auto-merge
    MEDIUM = "MEDIUM"   # 0.70-0.94 : Human-in-the-loop
    LOW = "LOW"         # <0.70 : Keep separate


class RelationshipType(Enum):
    SAME_PERSON = "SAME_PERSON"           # Identity match across systems
    HOUSEHOLD = "HOUSEHOLD"               # Family members at same address
    SPOUSE = "SPOUSE"                     # Married couple
    PARENT_CHILD = "PARENT_CHILD"         # Parent-child relationship
    BUSINESS_OWNER = "BUSINESS_OWNER"     # Person owns business
    BUSINESS_CONTACT = "BUSINESS_CONTACT" # Person is business contact
    JOINT_ACCOUNT = "JOINT_ACCOUNT"       # Share a joint account


class MergeAction(Enum):
    AUTO_MERGE = "AUTO_MERGE"             # High confidence - merge automatically
    REVIEW_REQUIRED = "REVIEW_REQUIRED"   # Medium confidence - human review
    KEEP_SEPARATE = "KEEP_SEPARATE"       # Low confidence - don't merge


# =============================================================================
# Scoring Weights
# =============================================================================

@dataclass
class ScoringWeights:
    """Weights for identity matching algorithm."""
    ssn_match: float = 0.40      # Strongest signal
    dob_match: float = 0.20      # Strong signal
    name_similarity: float = 0.15
    address_match: float = 0.15
    phone_match: float = 0.05
    email_match: float = 0.05

    def total(self) -> float:
        return (self.ssn_match + self.dob_match + self.name_similarity +
                self.address_match + self.phone_match + self.email_match)


DEFAULT_WEIGHTS = ScoringWeights()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MatchScore:
    """Detailed breakdown of match score between two entities."""
    entity1_id: str
    entity2_id: str
    entity1_name: str
    entity2_name: str
    entity1_source: str
    entity2_source: str

    # Individual scores (0.0 - 1.0)
    ssn_score: float = 0.0
    dob_score: float = 0.0
    name_score: float = 0.0
    address_score: float = 0.0
    phone_score: float = 0.0
    email_score: float = 0.0

    # Weighted total
    total_score: float = 0.0
    confidence_level: str = "LOW"
    merge_action: str = "KEEP_SEPARATE"

    # Explanation
    match_reasons: list[str] = field(default_factory=list)
    mismatch_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InferredRelationship:
    """A relationship inferred between two entities."""
    entity1_id: str
    entity2_id: str
    entity1_name: str
    entity2_name: str
    relationship_type: str
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UnifiedEntity:
    """A unified entity after merging records from multiple systems."""
    unified_id: str
    canonical_name: str
    entity_type: str  # PERSON or BUSINESS

    # Source records that were merged
    source_records: list[dict] = field(default_factory=list)

    # Merged attributes
    tax_id_last4: str = ""
    date_of_birth: Optional[str] = None
    addresses: list[dict] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)

    # Holdings across all systems
    holdings: dict = field(default_factory=dict)  # {system: [accounts]}

    # Relationships to other entities
    relationships: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Similarity Functions
# =============================================================================

def string_similarity(s1: str, s2: str) -> float:
    """Calculate similarity between two strings (0.0 - 1.0)."""
    if not s1 or not s2:
        return 0.0
    s1 = s1.upper().strip()
    s2 = s2.upper().strip()
    if s1 == s2:
        return 1.0
    return SequenceMatcher(None, s1, s2).ratio()


def name_similarity(name1: dict, name2: dict) -> float:
    """
    Calculate name similarity with fuzzy matching.

    Handles:
    - "John" vs "Jonathan" (partial match)
    - "J" vs "John" (initial match)
    - "Bob" vs "Robert" (nickname)
    """
    # Common nicknames
    nicknames = {
        "ROBERT": ["BOB", "ROB", "BOBBY", "ROBBIE"],
        "WILLIAM": ["WILL", "BILL", "BILLY", "WILLY"],
        "RICHARD": ["RICK", "DICK", "RICH"],
        "MICHAEL": ["MIKE", "MIKEY"],
        "JAMES": ["JIM", "JIMMY", "JAMIE"],
        "JOHN": ["JACK", "JOHNNY", "JON", "JONATHAN"],
        "JONATHAN": ["JOHN", "JON", "JACK"],
        "ELIZABETH": ["LIZ", "BETH", "LIZZY", "BETTY"],
        "MARGARET": ["MAGGIE", "MEG", "PEGGY"],
        "KATHERINE": ["KATE", "KATHY", "KATIE", "KAT"],
        "SARAH": ["SARA"],
        "MARIA": ["MARIE"],
    }

    first1 = name1.get("first_name", "").upper()
    first2 = name2.get("first_name", "").upper()
    last1 = name1.get("last_name", "").upper()
    last2 = name2.get("last_name", "").upper()

    # Last name must match or be very similar
    last_sim = string_similarity(last1, last2)
    if last_sim < 0.8:
        return last_sim * 0.5  # Penalize if last names don't match

    # First name matching
    first_sim = 0.0

    if first1 == first2:
        first_sim = 1.0
    elif len(first1) == 1 or len(first2) == 1:
        # Initial match (J vs John)
        if first1[0] == first2[0]:
            first_sim = 0.8
    else:
        # Check nicknames
        for canonical, nicks in nicknames.items():
            if first1 == canonical and first2 in nicks:
                first_sim = 0.9
                break
            if first2 == canonical and first1 in nicks:
                first_sim = 0.9
                break
            if first1 in nicks and first2 in nicks:
                first_sim = 0.85
                break

        # Fuzzy match if no nickname match
        if first_sim == 0.0:
            first_sim = string_similarity(first1, first2)

    # Middle name bonus
    middle1 = name1.get("middle_name", "").upper()
    middle2 = name2.get("middle_name", "").upper()
    middle_bonus = 0.0
    if middle1 and middle2:
        if middle1 == middle2:
            middle_bonus = 0.1
        elif middle1[0] == middle2[0]:
            middle_bonus = 0.05

    # Weighted combination
    score = (last_sim * 0.5) + (first_sim * 0.4) + middle_bonus
    return min(1.0, score)


def address_similarity(addr1: dict, addr2: dict) -> float:
    """Calculate address similarity."""
    if not addr1 or not addr2:
        return 0.0

    # ZIP code is strongest signal
    zip1 = addr1.get("zip5", "")
    zip2 = addr2.get("zip5", "")

    if not zip1 or not zip2:
        return 0.0

    if zip1 != zip2:
        return 0.0  # Different ZIP = different address

    # Street similarity
    street1 = addr1.get("street_line1", "")
    street2 = addr2.get("street_line1", "")
    street_sim = string_similarity(street1, street2)

    # Unit/Apt similarity
    unit1 = addr1.get("street_line2", "")
    unit2 = addr2.get("street_line2", "")

    if unit1 and unit2:
        unit_sim = string_similarity(unit1, unit2)
    elif not unit1 and not unit2:
        unit_sim = 1.0
    else:
        unit_sim = 0.5  # One has unit, other doesn't

    # City match (should match if ZIP matches, but check anyway)
    city1 = addr1.get("city", "")
    city2 = addr2.get("city", "")
    city_sim = string_similarity(city1, city2)

    return (street_sim * 0.6) + (unit_sim * 0.2) + (city_sim * 0.2)


# =============================================================================
# Identity Resolution Engine
# =============================================================================

class IdentityResolutionEngine:
    """Resolves identities across multiple source systems."""

    def __init__(self, weights: ScoringWeights = DEFAULT_WEIGHTS):
        self.weights = weights
        self.entities: list[dict] = []
        self.match_scores: list[MatchScore] = []
        self.inferred_relationships: list[InferredRelationship] = []
        self.unified_entities: list[UnifiedEntity] = []

    def load_entities(self, path: Path) -> None:
        """Load normalized entities from JSON file."""
        with open(path, "r") as f:
            self.entities = json.load(f)
        logger.info(f"Loaded {len(self.entities)} normalized entities")

    def calculate_match_score(self, e1: dict, e2: dict) -> MatchScore:
        """Calculate detailed match score between two entities."""
        score = MatchScore(
            entity1_id=e1["source_id"],
            entity2_id=e2["source_id"],
            entity1_name=e1["name"]["full_name"],
            entity2_name=e2["name"]["full_name"],
            entity1_source=e1["source_system"],
            entity2_source=e2["source_system"],
        )

        # SSN/TIN Match (0.40 weight)
        ssn1 = e1.get("tax_id_last4", "")
        ssn2 = e2.get("tax_id_last4", "")
        if ssn1 and ssn2 and ssn1 == ssn2:
            score.ssn_score = 1.0
            score.match_reasons.append(f"SSN last4 match: ***-**-{ssn1}")
        elif ssn1 and ssn2:
            score.ssn_score = 0.0
            score.mismatch_reasons.append(f"SSN mismatch: {ssn1} vs {ssn2}")

        # DOB Match (0.20 weight)
        dob1 = e1.get("date_of_birth")
        dob2 = e2.get("date_of_birth")
        if dob1 and dob2 and dob1 == dob2:
            score.dob_score = 1.0
            score.match_reasons.append(f"DOB match: {dob1}")
        elif dob1 and dob2:
            score.dob_score = 0.0
            score.mismatch_reasons.append(f"DOB mismatch: {dob1} vs {dob2}")
        # If one is missing, neutral (0.5)
        elif dob1 or dob2:
            score.dob_score = 0.5

        # Name Similarity (0.15 weight)
        name_sim = name_similarity(e1["name"], e2["name"])
        score.name_score = name_sim
        if name_sim >= 0.8:
            score.match_reasons.append(
                f"Name match ({name_sim:.0%}): {e1['name']['full_name']} ≈ {e2['name']['full_name']}"
            )
        elif name_sim < 0.5:
            score.mismatch_reasons.append(
                f"Name mismatch ({name_sim:.0%}): {e1['name']['full_name']} vs {e2['name']['full_name']}"
            )

        # Address Match (0.15 weight)
        addr_sim = address_similarity(e1.get("address", {}), e2.get("address", {}))
        score.address_score = addr_sim
        if addr_sim >= 0.8:
            score.match_reasons.append(
                f"Address match ({addr_sim:.0%}): {e1['address']['full_address']}"
            )

        # Phone Match (0.05 weight)
        phone1 = e1.get("phone_primary", {})
        phone2 = e2.get("phone_primary", {})
        if phone1 and phone2:
            num1 = phone1.get("number", "") if isinstance(phone1, dict) else ""
            num2 = phone2.get("number", "") if isinstance(phone2, dict) else ""
            if num1 and num2 and num1 == num2:
                score.phone_score = 1.0
                score.match_reasons.append(f"Phone match: {phone1.get('formatted', num1)}")

        # Email Match (0.05 weight)
        email1 = e1.get("email", "")
        email2 = e2.get("email", "")
        if email1 and email2:
            if email1 == email2:
                score.email_score = 1.0
                score.match_reasons.append(f"Email match: {email1}")
            else:
                # Check if same domain (weak signal)
                domain1 = email1.split("@")[-1] if "@" in email1 else ""
                domain2 = email2.split("@")[-1] if "@" in email2 else ""
                if domain1 and domain1 == domain2 and domain1 not in ["gmail.com", "yahoo.com", "outlook.com"]:
                    score.email_score = 0.3
                    score.match_reasons.append(f"Same email domain: {domain1}")

        # Calculate weighted total
        score.total_score = (
            (score.ssn_score * self.weights.ssn_match) +
            (score.dob_score * self.weights.dob_match) +
            (score.name_score * self.weights.name_similarity) +
            (score.address_score * self.weights.address_match) +
            (score.phone_score * self.weights.phone_match) +
            (score.email_score * self.weights.email_match)
        )

        # Determine confidence level and action
        if score.total_score >= 0.95:
            score.confidence_level = ConfidenceLevel.HIGH.value
            score.merge_action = MergeAction.AUTO_MERGE.value
        elif score.total_score >= 0.70:
            score.confidence_level = ConfidenceLevel.MEDIUM.value
            score.merge_action = MergeAction.REVIEW_REQUIRED.value
        else:
            score.confidence_level = ConfidenceLevel.LOW.value
            score.merge_action = MergeAction.KEEP_SEPARATE.value

        return score

    def find_all_matches(self) -> list[MatchScore]:
        """
        Find potential matches using a scalable Blocking Strategy.
        
        Instead of O(n^2) comparisons, we index entities by 'Blocking Keys'
        and only compare records within the same block.
        """
        persons = [e for e in self.entities if e["entity_type"] == "PERSON"]
        logger.info(f"Indexing {len(persons)} person entities for scalable matching...")

        # 1. Build Blocks (Inverted Index)
        # We use Zip Code and Last Name Prefix as primary blocking keys
        blocks = defaultdict(list)
        for p in persons:
            addr = p.get("address", {})
            zip_code = addr.get("zip5", "UNKNOWN")
            last_name = p["name"].get("last_name", "UNKNOWN").upper()
            last_prefix = last_name[:3] if len(last_name) >= 3 else last_name

            # Key format: ZIP|PREFIX (e.g., 15213|SMI)
            block_key = f"{zip_code}|{last_prefix}"
            blocks[block_key].append(p)

        # 2. Compare within blocks
        matches = []
        compared_pairs = set()
        comparison_count = 0

        logger.info(f"Processing {len(blocks)} candidate blocks...")

        for block_key, members in blocks.items():
            if len(members) < 2:
                continue

            for i, e1 in enumerate(members):
                for j, e2 in enumerate(members):
                    if i >= j:
                        continue
                    
                    # Skip same-system comparisons
                    if e1["source_system"] == e2["source_system"]:
                        continue

                    # Unique pair key (bidirectional)
                    pair_key = tuple(sorted([e1["source_id"], e2["source_id"]]))
                    if pair_key in compared_pairs:
                        continue
                    
                    compared_pairs.add(pair_key)
                    comparison_count += 1
                    
                    score = self.calculate_match_score(e1, e2)
                    if score.total_score >= 0.3:
                        matches.append(score)

        # Sort by score descending
        matches.sort(key=lambda x: x.total_score, reverse=True)
        self.match_scores = matches

        logger.info(f"Scalable matching complete. Comparisons: {comparison_count} (vs {len(persons)**2} brute force)")
        logger.info(f"Found {len(matches)} potential matches")
        return matches

    def infer_relationships(self) -> list[InferredRelationship]:
        """Infer HOUSEHOLD and other relationships from shared attributes."""
        persons = [e for e in self.entities if e["entity_type"] == "PERSON"]
        relationships = []

        # Group by address (ZIP + street)
        by_address = defaultdict(list)
        for p in persons:
            addr = p.get("address", {})
            key = f"{addr.get('zip5', '')}|{addr.get('street_line1', '')}"
            if key != "|":
                by_address[key].append(p)

        # Find households (same address, different people)
        for addr_key, residents in by_address.items():
            if len(residents) < 2:
                continue

            # Group by last name at this address
            by_last_name = defaultdict(list)
            for r in residents:
                last_name = r["name"]["last_name"]
                by_last_name[last_name].append(r)

            # People with same last name at same address = HOUSEHOLD
            for last_name, family in by_last_name.items():
                if len(family) < 2:
                    continue

                # Check for duplicates (same person across systems)
                unique_people = []
                seen_ssns = set()
                for p in family:
                    ssn = p.get("tax_id_last4", "")
                    if ssn and ssn in seen_ssns:
                        continue
                    seen_ssns.add(ssn)
                    unique_people.append(p)

                # Create household relationships
                for i, p1 in enumerate(unique_people):
                    for p2 in unique_people[i+1:]:
                        # Check if already identified as same person
                        is_same = any(
                            m.total_score >= 0.95 and
                            {m.entity1_id, m.entity2_id} == {p1["source_id"], p2["source_id"]}
                            for m in self.match_scores
                        )
                        if is_same:
                            continue

                        evidence = [
                            f"Same address: {p1['address']['full_address']}",
                            f"Same last name: {last_name}"
                        ]

                        # Check for SPOUSE indicators
                        rel_type = RelationshipType.HOUSEHOLD

                        # Check if mentioned in each other's related_entities
                        p1_related = " ".join(p1.get("related_entities", [])).upper()
                        p2_related = " ".join(p2.get("related_entities", [])).upper()

                        p1_full = p1["name"]["full_name"]
                        p2_full = p2["name"]["full_name"]

                        if p1["name"]["first_name"] in p2_related or p1_full in p2_related:
                            if "SPOUSE" in p2_related or p1["name"]["first_name"] in p2_related:
                                rel_type = RelationshipType.SPOUSE
                                evidence.append(f"Referenced as spouse/related in {p2['source_system']}")

                        if p2["name"]["first_name"] in p1_related or p2_full in p1_related:
                            if "SPOUSE" in p1_related or p2["name"]["first_name"] in p1_related:
                                rel_type = RelationshipType.SPOUSE
                                evidence.append(f"Referenced as spouse/related in {p1['source_system']}")

                        rel = InferredRelationship(
                            entity1_id=p1["source_id"],
                            entity2_id=p2["source_id"],
                            entity1_name=p1_full,
                            entity2_name=p2_full,
                            relationship_type=rel_type.value,
                            confidence=0.85,
                            evidence=evidence
                        )
                        relationships.append(rel)

        # Find BUSINESS_OWNER relationships
        businesses = [e for e in self.entities if e["entity_type"] == "BUSINESS"]

        for biz in businesses:
            biz_name = biz["name"]["full_name"]
            related_names = biz.get("related_entities", [])

            for rel_name in related_names:
                # Find matching person
                rel_normalized = rel_name.upper()
                for person in persons:
                    person_name = person["name"]["full_name"]
                    # Check similarity
                    if string_similarity(person_name, rel_normalized) >= 0.8:
                        evidence = [
                            f"Listed as authorized signer for {biz_name}",
                            f"Name match: {rel_name}"
                        ]

                        # Check if SSN matches contact
                        if person.get("tax_id_last4") and person["tax_id_last4"] in str(biz.get("raw_data", {})):
                            evidence.append("SSN matches business contact")

                        rel = InferredRelationship(
                            entity1_id=person["source_id"],
                            entity2_id=biz["source_id"],
                            entity1_name=person_name,
                            entity2_name=biz_name,
                            relationship_type=RelationshipType.BUSINESS_OWNER.value,
                            confidence=0.90,
                            evidence=evidence
                        )
                        relationships.append(rel)
                        break

        self.inferred_relationships = relationships
        logger.info(f"Inferred {len(relationships)} relationships")
        return relationships

    def build_unified_entities(self) -> list[UnifiedEntity]:
        """Build unified entities by merging high-confidence matches."""
        # Start with auto-merge matches
        auto_merges = [m for m in self.match_scores if m.merge_action == MergeAction.AUTO_MERGE.value]

        # Build clusters of entities to merge
        clusters = []
        entity_to_cluster = {}

        for match in auto_merges:
            id1, id2 = match.entity1_id, match.entity2_id

            cluster1 = entity_to_cluster.get(id1)
            cluster2 = entity_to_cluster.get(id2)

            if cluster1 is None and cluster2 is None:
                # New cluster
                new_cluster = {id1, id2}
                clusters.append(new_cluster)
                entity_to_cluster[id1] = new_cluster
                entity_to_cluster[id2] = new_cluster
            elif cluster1 is not None and cluster2 is None:
                # Add to existing cluster
                cluster1.add(id2)
                entity_to_cluster[id2] = cluster1
            elif cluster1 is None and cluster2 is not None:
                cluster2.add(id1)
                entity_to_cluster[id1] = cluster2
            elif cluster1 is not cluster2:
                # Merge clusters
                cluster1.update(cluster2)
                for eid in cluster2:
                    entity_to_cluster[eid] = cluster1
                clusters.remove(cluster2)

        # Create unified entities from clusters
        unified = []
        entity_lookup = {e["source_id"]: e for e in self.entities}
        used_ids = set()

        for i, cluster in enumerate(clusters, 1):
            source_records = [entity_lookup[eid] for eid in cluster if eid in entity_lookup]
            if not source_records:
                continue

            # Use the most complete record as canonical
            canonical = max(source_records, key=lambda x: (
                bool(x.get("date_of_birth")),
                len(x.get("email", "")),
                len(x["name"]["full_name"])
            ))

            unified_entity = UnifiedEntity(
                unified_id=f"UNI-{i:04d}",
                canonical_name=canonical["name"]["full_name"],
                entity_type=canonical["entity_type"],
                source_records=[{"source": r["source_system"], "id": r["source_id"]} for r in source_records],
                tax_id_last4=canonical.get("tax_id_last4", ""),
                date_of_birth=canonical.get("date_of_birth"),
                addresses=[r["address"] for r in source_records if r.get("address")],
                phones=list(set(
                    r["phone_primary"]["formatted"]
                    for r in source_records
                    if r.get("phone_primary") and r["phone_primary"].get("formatted")
                )),
                emails=list(set(r.get("email", "") for r in source_records if r.get("email"))),
            )

            unified.append(unified_entity)
            used_ids.update(cluster)

        # Add remaining entities that weren't merged
        for entity in self.entities:
            if entity["source_id"] not in used_ids:
                # Check if it's a duplicate within same system (skip contacts if main exists)
                if "-CONTACT" in entity["source_id"]:
                    main_id = entity["source_id"].replace("-CONTACT", "")
                    if main_id in used_ids or any(e["source_id"] == main_id for e in self.entities):
                        continue

                unified_entity = UnifiedEntity(
                    unified_id=f"UNI-{len(unified)+1:04d}",
                    canonical_name=entity["name"]["full_name"],
                    entity_type=entity["entity_type"],
                    source_records=[{"source": entity["source_system"], "id": entity["source_id"]}],
                    tax_id_last4=entity.get("tax_id_last4", ""),
                    date_of_birth=entity.get("date_of_birth"),
                    addresses=[entity["address"]] if entity.get("address") else [],
                    phones=[entity["phone_primary"]["formatted"]] if entity.get("phone_primary") else [],
                    emails=[entity.get("email")] if entity.get("email") else [],
                )
                unified.append(unified_entity)

        self.unified_entities = unified
        logger.info(f"Built {len(unified)} unified entities from {len(self.entities)} source records")
        return unified

    def print_results(self) -> None:
        """Print comprehensive results."""

        print("\n" + "=" * 80)
        print("PNC RELATIONSHIP ENGINE - IDENTITY RESOLUTION RESULTS")
        print("=" * 80)

        # Match scores
        print("\n" + "-" * 80)
        print("IDENTITY MATCH SCORES")
        print("-" * 80)
        print(f"{'Confidence':<12} {'Score':<8} {'Entity 1':<25} {'Entity 2':<25}")
        print("-" * 80)

        for match in self.match_scores:
            if match.total_score >= 0.50:  # Only show meaningful matches
                conf_icon = {
                    "HIGH": "🟢 AUTO",
                    "MEDIUM": "🟡 REVIEW",
                    "LOW": "🔴 KEEP"
                }.get(match.confidence_level, "")

                print(f"{conf_icon:<12} {match.total_score:.2f}    "
                      f"{match.entity1_name[:23]:<25} {match.entity2_name[:23]:<25}")

                # Show sources
                print(f"{'':12} {'':8} ({match.entity1_source}) → ({match.entity2_source})")

                # Show reasons
                if match.match_reasons:
                    for reason in match.match_reasons[:3]:
                        print(f"{'':12} {'':8} ✓ {reason}")
                print()

        # Summary by action
        auto_merge = [m for m in self.match_scores if m.merge_action == "AUTO_MERGE"]
        review = [m for m in self.match_scores if m.merge_action == "REVIEW_REQUIRED"]
        separate = [m for m in self.match_scores if m.merge_action == "KEEP_SEPARATE"]

        print("-" * 80)
        print("MERGE DECISION SUMMARY")
        print("-" * 80)
        print(f"  🟢 AUTO-MERGE (≥0.95):     {len(auto_merge)} pairs")
        print(f"  🟡 REVIEW REQUIRED (0.70-0.94): {len(review)} pairs")
        print(f"  🔴 KEEP SEPARATE (<0.70):  {len(separate)} pairs")

        # Inferred relationships
        print("\n" + "-" * 80)
        print("INFERRED RELATIONSHIPS")
        print("-" * 80)

        for rel in self.inferred_relationships:
            rel_icon = {
                "HOUSEHOLD": "🏠",
                "SPOUSE": "💑",
                "BUSINESS_OWNER": "🏢",
                "PARENT_CHILD": "👨‍👧",
            }.get(rel.relationship_type, "🔗")

            print(f"\n  {rel_icon} {rel.relationship_type}")
            print(f"     {rel.entity1_name} ←→ {rel.entity2_name}")
            print(f"     Confidence: {rel.confidence:.0%}")
            for ev in rel.evidence:
                print(f"     • {ev}")

        # Unified entities
        print("\n" + "-" * 80)
        print("UNIFIED RELATIONSHIP GRAPH")
        print("-" * 80)

        for entity in self.unified_entities:
            if entity.entity_type == "PERSON":
                icon = "👤"
            else:
                icon = "🏢"

            print(f"\n  {icon} {entity.unified_id}: {entity.canonical_name}")
            print(f"     Type: {entity.entity_type}")

            if len(entity.source_records) > 1:
                print(f"     🔗 MERGED FROM {len(entity.source_records)} SYSTEMS:")
                for src in entity.source_records:
                    print(f"        - {src['source']}: {src['id']}")
            else:
                print(f"     Source: {entity.source_records[0]['source']}")

            if entity.tax_id_last4:
                print(f"     Tax ID: ***-**-{entity.tax_id_last4}")
            if entity.date_of_birth:
                print(f"     DOB: {entity.date_of_birth}")
            if entity.phones:
                print(f"     Phone(s): {', '.join(entity.phones)}")
            if entity.emails:
                print(f"     Email(s): {', '.join(entity.emails[:2])}")

        # Final summary
        persons = [e for e in self.unified_entities if e.entity_type == "PERSON"]
        businesses = [e for e in self.unified_entities if e.entity_type == "BUSINESS"]
        merged_persons = [e for e in persons if len(e.source_records) > 1]

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"  Source records ingested:     {len(self.entities)}")
        print(f"  Unified entities created:    {len(self.unified_entities)}")
        print(f"    - Persons:                 {len(persons)}")
        print(f"    - Businesses:              {len(businesses)}")
        print(f"  Cross-system merges:         {len(merged_persons)}")
        print(f"  Relationships inferred:      {len(self.inferred_relationships)}")
        print("=" * 80)

        # Example advisor query
        print("\n" + "-" * 80)
        print("EXAMPLE: What the AI Advisor Can Now See")
        print("-" * 80)

        # Find John Smith
        john = next((e for e in self.unified_entities if "JOHN" in e.canonical_name and "SMITH" in e.canonical_name), None)
        if john:
            print(f"\n  Query: \"Tell me about {john.canonical_name}\"")
            print(f"\n  AI Response:")
            print(f"  \"I have a complete view of {john.canonical_name}'s relationship with PNC:")
            print(f"")
            if len(john.source_records) > 1:
                print(f"   📊 UNIFIED PROFILE (merged from {len(john.source_records)} systems)")
            for src in john.source_records:
                system = src['source']
                if system == "CONSUMER_CORE":
                    print(f"   💳 Personal Banking: Checking, Savings, Credit Card")
                elif system == "COMMERCIAL_CORE":
                    print(f"   🏢 Business: Smith Consulting LLC - Line of Credit")
                elif system == "WEALTH_ADVISORY":
                    print(f"   💰 Wealth: Family Trust ($1.25M), IRAs, 529 Plans")

            # Find spouse
            spouse_rel = next((r for r in self.inferred_relationships
                              if r.relationship_type in ["SPOUSE", "HOUSEHOLD"]
                              and john.canonical_name in [r.entity1_name, r.entity2_name]), None)
            if spouse_rel:
                spouse_name = spouse_rel.entity2_name if spouse_rel.entity1_name == john.canonical_name else spouse_rel.entity1_name
                print(f"   👨‍👩‍👧‍👦 Household: {spouse_name} (spouse)")

            print(f"")
            print(f"   Would you like me to analyze his business cash flow and suggest")
            print(f"   optimizations for the 529 contributions?\"")

        print("\n" + "=" * 80)


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Run identity resolution on normalized entities."""

    backend_dir = Path(__file__).parent.parent
    project_root = backend_dir.parent.parent
    data_dir = project_root / "data" / "relationship_store"
    normalized_path = data_dir / "normalized" / "all_entities.json"

    if not normalized_path.exists():
        logger.error(f"Normalized data not found: {normalized_path}")
        logger.error("Run normalization_engine.py first")
        return

    engine = IdentityResolutionEngine()
    engine.load_entities(normalized_path)
    engine.find_all_matches()
    engine.infer_relationships()
    engine.build_unified_entities()
    engine.print_results()

    # Save results
    output_dir = data_dir / "resolved"
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "match_scores.json", "w") as f:
        json.dump([m.to_dict() for m in engine.match_scores], f, indent=2)

    with open(output_dir / "relationships.json", "w") as f:
        json.dump([r.to_dict() for r in engine.inferred_relationships], f, indent=2)

    with open(output_dir / "unified_entities.json", "w") as f:
        json.dump([e.to_dict() for e in engine.unified_entities], f, indent=2)

    logger.info(f"Results saved to {output_dir}")


if __name__ == "__main__":
    main()
