from __future__ import annotations
from strix.types import ExecutionPlan, ApprovalResult, RiskLevel
from strix.config import StrixConfig

class ApprovalGate:
    """Checks execution plans against risk thresholds and prompts for approval if needed."""
    
    RISK_MAP = {
        'open_app': RiskLevel.SAFE,
        'open_url': RiskLevel.SAFE,
        'get_weather': RiskLevel.SAFE,
        'get_news': RiskLevel.SAFE,
        'get_system_status': RiskLevel.SAFE,
        'get_joke': RiskLevel.SAFE,
        'get_nasa': RiskLevel.SAFE,
        'get_ip_info': RiskLevel.SAFE,
        'get_crypto': RiskLevel.SAFE,
        'get_top_crypto': RiskLevel.SAFE,
        'get_exchange': RiskLevel.SAFE,
        'wiki_search': RiskLevel.SAFE,
        'get_github': RiskLevel.SAFE,
        'list_desktop': RiskLevel.SAFE,
        'search_files': RiskLevel.SAFE,
        'read_file': RiskLevel.SAFE,
        'directory_tree': RiskLevel.SAFE,
        'play_spotify': RiskLevel.SAFE,
        'play_playlist': RiskLevel.SAFE,
        'play_random_song': RiskLevel.SAFE,
        'music_pause': RiskLevel.SAFE,
        'music_next': RiskLevel.SAFE,
        'music_prev': RiskLevel.SAFE,
        'music_stop': RiskLevel.SAFE,
        'create_desktop_file': RiskLevel.LOW,
        'create_desktop_folder': RiskLevel.LOW,
        'create_java_project': RiskLevel.LOW,
        'create_c_project': RiskLevel.LOW,
        'create_cpp_project': RiskLevel.LOW,
        'create_python_project': RiskLevel.LOW,
        'git_status': RiskLevel.SAFE,
        'git_log': RiskLevel.SAFE,
        'git_diff': RiskLevel.SAFE,
        'delete_desktop_file': RiskLevel.HIGH,
        'run_terminal': RiskLevel.MEDIUM,
        'list_projects': RiskLevel.SAFE,
    }

    def __init__(self, config: StrixConfig):
        self.config = config
        print("[STRIX ApprovalGate] Initialized")
        
    def assess_risk(self, tool_name: str) -> RiskLevel:
        """Looks up the risk level for a given tool action."""
        return self.RISK_MAP.get(tool_name, RiskLevel.MEDIUM)
        
    def check(self, plan: ExecutionPlan, approval_callback=None) -> ApprovalResult:
        highest_risk = RiskLevel.SAFE
        for step in plan.steps:
            if step.action.name == 'TOOL_CALL':
                risk = self.assess_risk(step.target)
                if risk.value > highest_risk.value:
                    highest_risk = risk
                    
        plan.risk_level = highest_risk
        needs_approval = highest_risk.value >= self.config.approval_threshold
        
        print(f"[STRIX Approval] plan: risk={highest_risk.name}, {'needs approval' if needs_approval else 'auto-approved'}")
        
        if not needs_approval:
            return ApprovalResult(approved=True, reason="Auto-approved based on risk level")
            
        if approval_callback:
            return approval_callback("Plan requires approval")
            
        # CLI Mode
        print(f"\nExecution Plan Requires Approval (Risk: {highest_risk.name})")
        for i, step in enumerate(plan.steps):
            print(f"  {i+1}. {step.action.name} -> {step.target}")
            
        user_input = input('Approve? [y/N]: ')
        if user_input.lower() in ('y', 'yes'):
            return ApprovalResult(approved=True, reason="User approved via CLI")
        else:
            return ApprovalResult(approved=False, reason="User denied via CLI")
