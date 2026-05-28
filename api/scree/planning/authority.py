class PlanningAuthority:
    """Authority over GitLab planning objects: a principal may see an epic iff
    they are a member of its GitLab group (permission-enforcement-map: "membership
    of the item's Space in the resolved set"). Spike stub keyed on a readable-group
    map; the real impl resolves GitLab group membership (cf. GitLabAuthority)."""

    def __init__(self, readable_groups: dict[str, set[str]]) -> None:
        self._readable = readable_groups

    def readable_groups(self, principal: str) -> set[str]:
        # AR-08: the Gateway resolves this ONCE per request, not per epic.
        return self._readable.get(principal, set())
