# EDafk_combat.py

## Purpose
Automated AFK (away from keyboard) combat assistant for Rez site combat. Monitors shield status and fighter deployment, executes evasion sequences when shields fail, and redeploys fighters when destroyed.

## Key Classes/Functions
- AFK_Combat: Implements autonomous combat management with shield monitoring

## Key Methods
- check_shields_up(): Reads shield status from journal
- check_fighter_destroyed(): Checks if deployed fighter is destroyed, resets flag after reading
- evade(): Executes full evasion sequence - boost, supercruise, retreat, return to normal space, configure power
- launch_fighter(): Deploys fighter with pilot selection and attack command configuration

## Dependencies
- EDJournal: Ship state monitoring (shields, fighter status)
- EDKeys: Keyboard input control
- Voice: Voice notification system
- time.sleep: Timing for game response

## Notes
- Monitors journal for shield loss and fighter destroyed events
- Toggle between two fighter bays during deployment (rebuilding management)
- Supercruise retreat provides time to escape combat zone
- Configurable AttackAtWill behavior for deployed fighter
- Original author: sumzer0@yahoo.com
- Includes commented hotkey example for standalone testing
