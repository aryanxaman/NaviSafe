export function checkInPhase(deadline: number, now: number) {
  const remaining = deadline - now;
  return remaining > 5 * 60_000 ? 'active'
    : remaining > 0 ? 'near_eta'
    : remaining > -15 * 60_000 ? 'overdue' : 'manual_escalation';
}
