# W-2 Validation Reference

Box-by-box review guidance for validating W-2 Wage and Tax Statements.

## The Reconciliation Identity

For every W-2, these relationships should hold (with known exceptions):

```
Box 3 (SS wages) = Box 1 (Fed wages) 
    + pretax 401(k) / 403(b) / 457 contributions (Box 12 D/E/G)
    + HSA pretax contributions through cafeteria plan (Box 12 W, employee portion)
    + section 125 cafeteria plan pretax (health, dental, dep care)
    + dependent care benefits (Box 10)
    - GTL imputed income over $50k (Box 12 C) if applicable
```

```
Box 5 (Medicare wages) = Box 3 (SS wages) + [any wages above SS wage base]
```

**Sanity checks (for 2025):**
- `Box 4 = 6.2% × Box 3` (Social Security tax)
- `Box 6 ≥ 1.45% × Box 5` (Medicare tax; add 0.9% on wages over $200k individually)
- `Box 3 ≤ $176,100` (2025 Social Security wage base)
- `Box 4 ≤ $10,918.20` (2025 max SS tax)

If the above don't reconcile, something is misread or missing. Most common cause: failure to account for pretax deductions (cafeteria plan, dependent care, 401(k)).

## Box-by-Box Review

### Box 1: Wages, Tips, Other Compensation
Federally taxable wages. Goes on Form 1040 Line 1a. Excludes most pretax contributions.

### Box 2: Federal Income Tax Withheld
Credit on Form 1040 Line 25a. Verify against last pay stub of the year to catch missing payments.

### Box 3: Social Security Wages
Capped at the SS wage base ($176,100 for 2025). Includes 401(k) contributions (pretax) but excludes HSA employee portion (Code W). **Usually differs from Box 1** because pretax retirement is excluded from Box 1 but not Box 3.

### Box 4: Social Security Tax Withheld
Must equal exactly `6.2% × Box 3`. If off by more than a penny, the W-2 is wrong.

### Box 5: Medicare Wages
No cap. Usually ≥ Box 3 (same up to SS base, greater above).

### Box 6: Medicare Tax Withheld
At least `1.45% × Box 5`. For individual wages over $200,000, add 0.9% Additional Medicare Tax on the excess. Reconcile against Form 8959 if MFJ combined exceeds $250k.

### Box 7: Social Security Tips
Usually zero for salaried employees. For tipped workers, check that Box 3 + Box 7 ≤ SS wage base.

### Box 8: Allocated Tips
NOT included in Box 1. Must be reported on Form 4137 unless employee has records proving actual tips received.

### Box 10: Dependent Care Benefits
Amount employer provided through a cafeteria plan (DCAP / FSA for dependent care).
- **2025 exclusion limit: $5,000 MFJ** ($2,500 MFS)
- **Requires qualifying person UNDER AGE 13** (or spouse/dependent unable to self-care)
- Excess over $5,000 OR any amount with no qualifying person is taxable
- Report on Form 2441 — Part III calculates the taxable portion
- Taxable portion flows to 1040 Line 1e

**Gotcha:** If employer provides dependent care benefits but the employee has no qualifying person under 13, the ENTIRE Box 10 is taxable. This is easy to miss because Box 1 already excludes it — you have to add it back on Form 2441.

### Box 11: Nonqualified Plans
Distributions from NQDC plans. Usually in Box 1 already.

### Box 12: Coded Amounts
| Code | Description | Notes |
|---|---|---|
| A | Uncollected SS on tips | |
| B | Uncollected Medicare on tips | |
| C | Taxable cost of group-term life > $50,000 | Already in Box 1, 3, 5 |
| **D** | **401(k) elective deferral** | Pretax. 2025 limit $23,500 + $7,500/$11,250 catch-up |
| E | 403(b) elective deferral | |
| F | 408(k)(6) SEP | |
| G | 457(b) elective deferral | |
| H | 501(c)(18)(D) elective deferral | |
| J | Nontaxable sick pay | Not in Box 1 |
| K | 20% excise on golden parachute | |
| L | Substantiated employee expense reimbursement | |
| M/N | Uncollected FICA on GTL > $50k (former employees) | |
| P | Excludable moving (armed forces only) | |
| Q | Nontaxable combat pay | |
| R | Employer Archer MSA | |
| S | SIMPLE plan | |
| T | Adoption benefits | Form 8839 |
| V | Nonstatutory stock option exercise | Already in Box 1, 3, 5 |
| **W** | **HSA contributions (employer + employee pretax)** | File Form 8889. 2025 limit $4,300 self / $8,550 family |
| Y | 409A deferrals | |
| Z | 409A failure (taxable + 20% penalty + interest) | |
| AA | Roth 401(k) | Post-tax; NOT deductible |
| BB | Roth 403(b) | Post-tax |
| **DD** | **Employer health coverage cost** | Informational only, NOT taxable |
| EE | Roth 457(b) | Post-tax |
| FF | QSEHRA benefits | |
| GG | Section 83(i) qualified equity grants | |
| HH | Section 83(i) aggregate deferrals | |
| II | Medicaid waiver payments | |

**Most common misread:** confusing codes D (401k) and DD (health coverage). D is a 401(k) deferral — pretax, reduces Box 1. DD is informational — does not affect Box 1.

### Box 13: Checkboxes
- **Statutory employee:** Income reported on Schedule C, not 1040 Line 1
- **Retirement plan:** Affects Traditional IRA deduction phaseout. If checked, the IRA deduction may be limited based on MAGI.
- **Third-party sick pay:** Disability or medical leave paid by insurance company.

### Box 14: Other
Employer-specific. Common items:
- **DQDIS** or similar — Disqualifying disposition of ISO/ESPP. **Already in Box 1 wages.** See [form-8949-espp.md](form-8949-espp.md) for basis adjustment rules.
- **WAPFL / WAFML** — Washington Paid Family/Medical Leave contributions. Not federally deductible but may be state-deductible (N/A in WA since no income tax).
- **CASDI** — CA State Disability Insurance. State-deductible.
- **NYPFL** — NY Paid Family Leave.
- **RRTA compensation** — Railroad retirement tax info.
- Various union dues, health insurance premium after-tax, charitable auto-deductions, etc.

### Box 15-20: State/Local
Employer's state ID, state wages, state tax, local wages, local tax, locality name. For WA residents: no state income tax, so most of these are blank.

## Common Errors to Catch

1. **Rotated/photographed W-2s** — Box 2 and Box 4 are adjacent; easy to misread one for the other. Always verify `Box 4 = 6.2% × Box 3` to detect.

2. **Missing Box 12 codes** — If Box 1 seems "too low" vs Box 3, the pretax deductions must total the difference. Check all Box 12 codes to make sure you captured them.

3. **DQDIS already in Box 1** — Never add this separately. It's an employer-generated FYI that the bargain element of a disqualifying ESPP/ISO disposition was ALREADY included in wages.

4. **Multi-state W-2s** — W-2 may have multiple rows in Boxes 15-17. Add them up for total state income.

5. **DD (Health coverage) is NOT income** — It's informational. Never add to wages.

6. **Box 12 W (HSA) — who contributed?** W includes BOTH the employer portion AND the employee's pretax contribution through the cafeteria plan. Form 8889 separates these. If the employee contributed outside the cafeteria plan (by writing a check to the HSA directly), that's NOT in Box 12 W and IS deductible above-the-line.

7. **Dependent care trap** — Box 10 with no qualifying child under 13 means the whole amount must be added back to income via Form 2441.

8. **Retirement plan box affects IRA deduction** — If checked for either spouse on a joint return, the Traditional IRA deduction phases out at much lower MAGI than if neither spouse is covered.

## Reconciling Against Pay Stubs

When the W-2 looks wrong, compare to the final pay stub of the year:
- Year-to-date gross pay ≈ Box 1 + pretax contributions
- YTD federal withholding = Box 2
- YTD FICA/Medicare = Box 4 + Box 6
- YTD 401(k) should match Box 12 D/E/G

Material differences between the W-2 and the YTD pay stub usually indicate:
- Post-year-end correction (check for W-2c)
- Imputed income added (GTL > $50k, personal use of company car, relocation, etc.)
- Third-party sick pay adjustments
- DQDIS amounts added at year-end

## Form 8959 (Additional Medicare Tax) Reconciliation

When any employee's wages exceed $200,000 individually, OR MFJ couple's combined wages exceed $250,000:

1. Employer withholds 0.9% on individual wages over $200k (regardless of filing status)
2. Total tax = 0.9% × (combined wages — $250,000 MFJ threshold)
3. Withheld ≠ owed for MFJ couples where neither spouse individually exceeds $200k but combined does
4. Reconcile on Form 8959 — may owe additional, may get refund

**Example (MFJ):**
- Spouse A wages: $300,000 → employer withheld 0.9% × $100,000 = $900
- Spouse B wages: $150,000 → employer withheld $0
- Combined: $450,000 → true tax = 0.9% × $200,000 = $1,800
- Shortfall owed via Form 8959: $900

## Multi-W-2 Watch-Outs

If an employee has multiple W-2s (job change, multiple employers):
- Each employer withheld SS tax on up to $176,100 of wages
- Combined SS withholding may exceed $10,918.20 (the 2025 max)
- Excess SS withholding is refundable on Form 1040 Line 25c
- Check: `Σ(Box 4 across all W-2s) vs $10,918.20`
- Similarly for Medicare, though there's no cap on Medicare wages
