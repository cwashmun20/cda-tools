import dance
import dancer
import entry

class Partnership:
    """Representation of a partnership."""

    names = ""
    lead = None
    follow = None
    newcomers = None
    nc_beginners = None
    entries = []

    def __init__(self, leader: dancer.Dancer, follower: dancer.Dancer):
        """Create a partnership from two dancers."""
        
        self.names = leader.name + " & " + follower.name
        self.lead = leader
        self.follow = follower
        self.newcomers = leader.newcomer() and follower.newcomer()
        self.nc_beginners = leader.nc_beginner() and follower.nc_beginner()
        self.entries = []

    def __repr__(self) -> str:
        """String representation of a partnership with registration-relevant 
        information.
        """
        string = f"""\
        Names (Lead & Follow): {self.names}
        Newcomers?             {self.newcomers}
        NC Beginners?          {self.nc_beginners}
        Entries:               {self.entries}
        """
        # TODO (CWA): Future feature: add recommended levels for each syllabus style,
        #             AKA the lowest common level where neither dancer has pointed
        #             out of any dances, plus the level above that. Will need to
        #             ignore Newcomer if dancers are ineligible. 

    # TODO (CWA): Change or remove default value of rv_ruleset depending on convention in Fall 2024.
    # TODO (CWA): Implement a way to pass on the reason why eligibility was denied.
    def eligible(self, dance_obj: dance.Dance, rv_ruleset: str = "newcomer") -> bool:
        """Returns a boolean corresponding to whether a couple is eligible for
        a certain dance at a certain level.

        Args:
            dance_obj: a Dance object used to determine eligibility for that dance.
            rv_ruleset: a string, either "newcomer" or "level", based on which
                        ruleset a competition uses for rookie-vet eligibility:
                        "newcomer": rookies == newcomers; vets == non-newcomers;
                        "level": rookies == newcomer/bronze dancer; vets == silver+ dancers.
        Returns:
            True if a couple is eligible for the dance; otherwise False.
        Raises:
            NotImplementedError: if the "level" ruleset is used (not yet implemented).
            ValueError: if the ruleset is not recognized. 
        """
        # Check eligibility for Newcomer
        if not self.newcomers and dance_obj.level == dance.SYLLABUS_LEVELS[0]:
            return False

        # Check eligibility for Beginner Nightclub
        if not self.nc_beginners and dance_obj.level == dance.NC_LEVELS[0]:
            return False
        
        # Check eligibility for Rookie/Vet
        if rv_ruleset == "newcomer":
            # Check Rookie Lead
            if dance_obj.level == dance.ALL_LEVELS[-2]:
                return self.lead.newcomer() and not self.follow.newcomer()
            # Check Rookie Follow
            elif dance_obj.level == dance.ALL_LEVELS[-1]:
                return self.follow.newcomer() and not self.lead.newcomer()     
        elif rv_ruleset == "level":
            # Check Rookie Lead
            if dance_obj.level == dance.ALL_LEVELS[-2]:
                rookie_lead = not self.lead.has_vet_entries(dance_obj.style)
                vet_follow = not self.follow.has_rookie_entries(dance_obj.style)
                return rookie_lead and vet_follow
            # Check Rookie Follow
            elif dance_obj.level == dance.ALL_LEVELS[-1]:
                rookie_follow = not self.follow.has_vet_entries(dance_obj.style)
                vet_lead = not self.lead.has_rookie_entries(dance_obj.style)
                return rookie_follow and vet_lead
        elif rv_ruleset not in ["newcomer", "level"]:
            raise ValueError("Invalid Rookie/Vet ruleset.")

        lead_level = self.lead.points.proficiency_level(dance_obj)
        follow_level = self.follow.points.proficiency_level(dance_obj)
        event_level = dance.FLC_LEVELS.index(dance_obj.level)

        # Check for Split-Level Exception and Pointing Out
        if abs(lead_level - follow_level) >= 2:
            combined_level = max(lead_level, follow_level) - 1
            # TODO (CWA): If this is how combined_level is assigned, sync this
            #             with the couple's entries and awarded points to award 
            #             3x points, if applicable.
        else:
            combined_level = max(lead_level, follow_level)

        return combined_level <= event_level
    
    def add(self, comp_entry: entry.Entry):
        """Adds a competition entry for a couple. Should only be called within the Entry constructor."""
        if comp_entry not in self.entries:
            self.entries.append(comp_entry)
            self.lead.add(comp_entry)
            self.follow.add(comp_entry)

    def drop(self, comp_entry: entry.Entry):
        """Drops a competition entry for a couple."""
        self.entries.remove(comp_entry)
        self.lead.drop(comp_entry)
        self.follow.drop(comp_entry)