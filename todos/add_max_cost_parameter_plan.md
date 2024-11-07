# Plan: Add Max Cost Parameter to CLI Tool

## Overview
Implement a maximum cost parameter in the main CLI tool by leveraging the existing SessionUsageTracking system.

## Implementation Steps

### 1. Add Max Cost Parameter to CLI
```python
@click.option(
    '--max-cost',
    type=float,
    default=0.05,
    help='Maximum cost limit in dollars (default: $0.05)'
)
```
Add to existing click decorators in main.py (around line 24-30)

### 2. Modify Cost Tracking Logic
Currently, cost is only calculated at the end (lines 123-130). We need to:

1. Add cost checking in the main loop where tool usage is processed (around line 96)
2. Use existing `session_tracker.compute_cost_per_model()` to get current cost
3. Add check before `run_agent_with_status` call (line 102)

### 3. Implementation Details
```python
def check_cost_limit(session_tracker: SessionUsageTracking, max_cost: float) -> bool:
    current_cost = sum(session_tracker.compute_cost_per_model().values())
    return current_cost < max_cost

# In main() function:
    while confirm_next_loop or approve_tools or click.confirm("Approve", default=True):
        # Add cost check here
        if not check_cost_limit(session_tracker, max_cost):
            current_cost = sum(session_tracker.compute_cost_per_model().values())
            click.echo(f"Cost limit reached: ${current_cost:.4f} / ${max_cost:.4f}")
            if click.confirm("Would you like to extend the cost limit?", default=False):
                extension = click.prompt(
                    "Enter additional amount in dollars",
                    type=float,
                    default=0.05
                )
                max_cost += extension
            else:
                break
```

### 4. Testing Considerations
- Test with small max_cost to ensure prompt triggers
- Verify cost calculation matches final output
- Test with different models (they have different costs)
- Test continuation after limit extension

### 5. Documentation Updates
- Add max_cost parameter to help output
- Update README.md with new parameter details
- Document cost control feature

## Dependencies
- Uses existing SessionUsageTracking
- Relies on Click for CLI handling
- Uses existing cost calculation methods

## Notes
- Consider adding a warning at 80% of max cost
- Could add configuration file support for default max cost
- May want to persist cost limits across sessions