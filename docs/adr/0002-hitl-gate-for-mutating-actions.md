# Human-in-the-Loop (HITL) Gate for High-Stakes Mutating Actions

Automated execution of mutating cloud commands (such as pod restarts, rollback deployments, and firewall reconfigurations) carries high availability and security risks. We decided that all mutating tools must be intercepted by a mandatory code-level `ConfirmationRequiredInterrupt` gate that captures execution parameters, intent, and impact, halting automated execution until an authorized human operator grants explicit approval.
