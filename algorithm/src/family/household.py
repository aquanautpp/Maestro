"""Household management for families with multiple children and caregivers.

Supports tracking interactions per child and aggregating household-level stats.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

# Import age adaptation if available
try:
    from ..age_adaptation import calculate_age_months, get_age_group, get_pitch_threshold_for_age
    HAS_AGE_ADAPTATION = True
except ImportError:
    HAS_AGE_ADAPTATION = False


@dataclass
class Child:
    """Represents a child in the household."""
    id: str
    name: str
    birth_date: str  # ISO format: YYYY-MM-DD
    pitch_profile: dict = field(default_factory=dict)  # Learned pitch characteristics
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat() + "Z")

    @property
    def age_months(self) -> int:
        """Calculate current age in months."""
        if HAS_AGE_ADAPTATION:
            return calculate_age_months(self.birth_date)
        else:
            birth = datetime.fromisoformat(self.birth_date.replace("Z", "")).date()
            today = date.today()
            months = (today.year - birth.year) * 12 + (today.month - birth.month)
            return max(0, months)

    @property
    def age_group(self) -> Optional[str]:
        """Get age group string (e.g., '2-3')."""
        if HAS_AGE_ADAPTATION:
            return get_age_group(self.age_months)
        return None

    @property
    def pitch_threshold(self) -> int:
        """Get recommended pitch threshold for this child's age."""
        if HAS_AGE_ADAPTATION:
            return get_pitch_threshold_for_age(self.age_months)
        return 280  # Default

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["age_months"] = self.age_months
        data["age_group"] = self.age_group
        data["pitch_threshold"] = self.pitch_threshold
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Child":
        """Create Child from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            birth_date=data["birth_date"],
            pitch_profile=data.get("pitch_profile", {}),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", datetime.now().isoformat() + "Z"),
        )


@dataclass
class Caregiver:
    """Represents a caregiver (parent, grandparent, nanny, etc.)."""
    id: str
    name: str
    relationship: str = "parent"  # parent, grandparent, nanny, other
    voice_profile: dict = field(default_factory=dict)  # Optional voice characteristics
    is_primary: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat() + "Z")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Caregiver":
        """Create Caregiver from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            relationship=data.get("relationship", "parent"),
            voice_profile=data.get("voice_profile", {}),
            is_primary=data.get("is_primary", False),
            created_at=data.get("created_at", datetime.now().isoformat() + "Z"),
        )


class Household:
    """
    Manages a household with multiple children and caregivers.

    Stores data locally in JSON for offline-first operation.
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize household manager.

        Args:
            data_path: Path to household data file. If None, uses default location.
        """
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data" / "household.json"

        self.data_path = data_path
        self._children: List[Child] = []
        self._caregivers: List[Caregiver] = []
        self._active_child_id: Optional[str] = None
        self._active_caregiver_id: Optional[str] = None

        self._load()

    def _load(self):
        """Load household data from JSON file."""
        if not self.data_path.exists():
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._children = [
                Child.from_dict(c) for c in data.get("children", [])
            ]
            self._caregivers = [
                Caregiver.from_dict(c) for c in data.get("caregivers", [])
            ]
            self._active_child_id = data.get("active_child_id")
            self._active_caregiver_id = data.get("active_caregiver_id")

        except Exception:
            pass

    def _save(self):
        """Save household data to JSON file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "children": [c.to_dict() for c in self._children],
            "caregivers": [c.to_dict() for c in self._caregivers],
            "active_child_id": self._active_child_id,
            "active_caregiver_id": self._active_caregiver_id,
            "updated_at": datetime.now().isoformat() + "Z",
        }

        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ============ CHILDREN MANAGEMENT ============

    @property
    def children(self) -> List[Child]:
        """Get all children (active and inactive)."""
        return self._children

    @property
    def active_children(self) -> List[Child]:
        """Get only active children."""
        return [c for c in self._children if c.is_active]

    def get_child(self, child_id: str) -> Optional[Child]:
        """Get child by ID."""
        for child in self._children:
            if child.id == child_id:
                return child
        return None

    def add_child(self, name: str, birth_date: str) -> Child:
        """
        Add a new child to the household.

        Args:
            name: Child's name
            birth_date: Birth date in ISO format (YYYY-MM-DD)

        Returns:
            Created Child object
        """
        child = Child(
            id=str(uuid.uuid4())[:8],
            name=name,
            birth_date=birth_date,
        )
        self._children.append(child)

        # Set as active if first child
        if len(self.active_children) == 1:
            self._active_child_id = child.id

        self._save()
        return child

    def update_child(self, child_id: str, **updates) -> Optional[Child]:
        """
        Update a child's information.

        Args:
            child_id: Child's ID
            **updates: Fields to update (name, birth_date, is_active, pitch_profile)

        Returns:
            Updated Child or None if not found
        """
        child = self.get_child(child_id)
        if not child:
            return None

        for key, value in updates.items():
            if hasattr(child, key):
                setattr(child, key, value)

        self._save()
        return child

    def remove_child(self, child_id: str, hard_delete: bool = False) -> bool:
        """
        Remove a child from the household.

        Args:
            child_id: Child's ID
            hard_delete: If True, permanently remove. If False, mark as inactive.

        Returns:
            True if removed, False if not found
        """
        child = self.get_child(child_id)
        if not child:
            return False

        if hard_delete:
            self._children = [c for c in self._children if c.id != child_id]
        else:
            child.is_active = False

        # Clear active if this was active child
        if self._active_child_id == child_id:
            active = self.active_children
            self._active_child_id = active[0].id if active else None

        self._save()
        return True

    # ============ ACTIVE CHILD ============

    @property
    def active_child(self) -> Optional[Child]:
        """Get the currently active child for detection."""
        if self._active_child_id:
            return self.get_child(self._active_child_id)
        # Return first active child if none explicitly set
        active = self.active_children
        return active[0] if active else None

    def set_active_child(self, child_id: str) -> bool:
        """
        Set the active child for detection.

        Args:
            child_id: Child's ID

        Returns:
            True if set successfully, False if child not found
        """
        child = self.get_child(child_id)
        if not child or not child.is_active:
            return False

        self._active_child_id = child_id
        self._save()
        return True

    # ============ CAREGIVERS MANAGEMENT ============

    @property
    def caregivers(self) -> List[Caregiver]:
        """Get all caregivers."""
        return self._caregivers

    def get_caregiver(self, caregiver_id: str) -> Optional[Caregiver]:
        """Get caregiver by ID."""
        for cg in self._caregivers:
            if cg.id == caregiver_id:
                return cg
        return None

    def add_caregiver(
        self,
        name: str,
        relationship: str = "parent",
        is_primary: bool = False
    ) -> Caregiver:
        """
        Add a new caregiver to the household.

        Args:
            name: Caregiver's name
            relationship: Relationship type (parent, grandparent, nanny, other)
            is_primary: Whether this is the primary caregiver

        Returns:
            Created Caregiver object
        """
        caregiver = Caregiver(
            id=str(uuid.uuid4())[:8],
            name=name,
            relationship=relationship,
            is_primary=is_primary,
        )
        self._caregivers.append(caregiver)

        # Set as active if first caregiver
        if len(self._caregivers) == 1:
            self._active_caregiver_id = caregiver.id

        self._save()
        return caregiver

    def update_caregiver(self, caregiver_id: str, **updates) -> Optional[Caregiver]:
        """Update a caregiver's information."""
        caregiver = self.get_caregiver(caregiver_id)
        if not caregiver:
            return None

        for key, value in updates.items():
            if hasattr(caregiver, key):
                setattr(caregiver, key, value)

        self._save()
        return caregiver

    def remove_caregiver(self, caregiver_id: str) -> bool:
        """Remove a caregiver from the household."""
        if not self.get_caregiver(caregiver_id):
            return False

        self._caregivers = [c for c in self._caregivers if c.id != caregiver_id]

        if self._active_caregiver_id == caregiver_id:
            self._active_caregiver_id = self._caregivers[0].id if self._caregivers else None

        self._save()
        return True

    # ============ ACTIVE CAREGIVER ============

    @property
    def active_caregiver(self) -> Optional[Caregiver]:
        """Get the currently active caregiver."""
        if self._active_caregiver_id:
            return self.get_caregiver(self._active_caregiver_id)
        return self._caregivers[0] if self._caregivers else None

    def set_active_caregiver(self, caregiver_id: str) -> bool:
        """Set the active caregiver."""
        if not self.get_caregiver(caregiver_id):
            return False

        self._active_caregiver_id = caregiver_id
        self._save()
        return True

    # ============ PITCH PROFILE CALIBRATION ============

    def update_child_pitch_profile(
        self,
        child_id: str,
        detected_pitches: List[float]
    ) -> Optional[dict]:
        """
        Update a child's pitch profile based on detected speech.

        This helps improve child identification when there are multiple children.

        Args:
            child_id: Child's ID
            detected_pitches: List of pitch values (Hz) from detected speech

        Returns:
            Updated pitch profile or None if child not found
        """
        child = self.get_child(child_id)
        if not child or not detected_pitches:
            return None

        import numpy as np

        # Calculate statistics
        pitches = np.array(detected_pitches)
        profile = {
            "mean_pitch": float(np.mean(pitches)),
            "median_pitch": float(np.median(pitches)),
            "std_pitch": float(np.std(pitches)),
            "min_pitch": float(np.min(pitches)),
            "max_pitch": float(np.max(pitches)),
            "sample_count": len(detected_pitches),
            "updated_at": datetime.now().isoformat() + "Z",
        }

        # Merge with existing profile
        existing = child.pitch_profile.get("sample_count", 0)
        if existing > 0:
            # Weighted average for running statistics
            total = existing + len(detected_pitches)
            old_weight = existing / total
            new_weight = len(detected_pitches) / total

            old_profile = child.pitch_profile
            profile["mean_pitch"] = (
                old_profile.get("mean_pitch", profile["mean_pitch"]) * old_weight +
                profile["mean_pitch"] * new_weight
            )
            profile["sample_count"] = total

        child.pitch_profile = profile
        self._save()
        return profile

    # ============ SUMMARY ============

    def get_summary(self) -> dict:
        """Get household summary with all children and caregivers."""
        return {
            "children": [c.to_dict() for c in self.active_children],
            "caregivers": [c.to_dict() for c in self._caregivers],
            "active_child_id": self._active_child_id,
            "active_caregiver_id": self._active_caregiver_id,
            "total_children": len(self.active_children),
            "total_caregivers": len(self._caregivers),
        }
