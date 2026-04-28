# 1099 Series Reconciliation Reference

Validation guidance for the major 1099 forms. Focus: what to extract, what to cross-check, and where errors commonly occur.

## 1099-INT (Interest Income)

**Key boxes:**
- Box 1: Taxable interest (goes on Schedule B Line 1)
- Box 2: Early withdrawal penalty (above-the-line deduction)
- Box 3: US Savings Bonds / Treasury interest (state-tax-exempt; reported separately on Schedule B)
- Box 4: Federal tax withheld (credit on 1040 Line 25b)
- Box 6: Foreign tax paid (claim on Schedule 3 or Form 1116)
- Box 8: Tax-exempt interest (1040 Line 2a; not in Box 1)
- Box 9: Specified private activity bond interest (AMT add-back, Form 6251)

**Validation checks:**
- Treasury interest in Box 3 is exempt from state income tax — track separately
- If Box 1 + Box 3 combined > $1,500, Schedule B is required (list payers)
- Watch for distinct 1099-INTs from the same bank (checking, savings, bonds) — each must be entered
- Joint accounts: both filers own 50/50 typically; if reported to only one SSN, the other spouse's share is still reportable

## 1099-DIV (Dividends)

**Key boxes:**
- Box 1a: Total ordinary dividends (Schedule B, flows to 1040 Line 3b)
- Box 1b: Qualified dividends (subset of 1a; 1040 Line 3a, taxed at LTCG rates)
- Box 2a: Total capital gain distributions (mutual fund LTCG passed through; Schedule D)
- Box 2b: Unrecap. Sec 1250 gain (real estate depreciation recapture, 25% rate)
- Box 2c: Section 1202 gain (QSBS 28%)
- Box 2d: Collectibles gain (28%)
- Box 3: Nondividend distributions (return of capital; reduces basis)
- Box 5: Section 199A dividends (REIT dividends eligible for QBI 20% deduction)
- Box 7: Foreign tax paid
- Box 11: FATCA filing indicator
- Box 12: Exempt-interest dividends (from muni bond mutual funds; 1040 Line 2a)
- Box 13: Specified private activity bond interest dividends (AMT add-back)

**Validation checks:**
- 1b (qualified) ≤ 1a (ordinary) always
- 2a (total cap gain) includes 2b + 2c + 2d
- Section 199A dividends (Box 5) get a 20% deduction even if you don't own a business — don't miss this
- Box 12 exempt-interest dividends go on 1040 Line 2a (NOT Schedule B Part I)
- Box 13 is part of Box 12 but creates an AMT preference

## 1099-B (Broker Proceeds)

**Key fields:**
- Box 1a: Description of property
- Box 1b: Date acquired
- Box 1c: Date sold
- Box 1d: Proceeds
- Box 1e: Cost basis
- Box 1f: Accrued market discount
- Box 1g: Wash sale loss disallowed
- Box 2: Type of gain/loss (short/long)
- Box 3: Covered security indicator (basis reported to IRS?)
- Box 4: Federal tax withheld
- Box 12: Basis reported to IRS checkbox (Box A/D vs B/E)

**Validation checks:**
- Each lot gets a Form 8949 entry
- Short-term vs long-term determined by holding period (>1 year = LT)
- Form 8949 Box letter:
  - **A**: Short-term, basis reported to IRS
  - **B**: Short-term, basis NOT reported
  - **C**: Short-term, no 1099-B received
  - **D**: Long-term, basis reported
  - **E**: Long-term, basis NOT reported
  - **F**: Long-term, no 1099-B
- **Box 1e is often WRONG for ESPP/ISO/NQSO/RSU** — requires Code B adjustment (see [form-8949-espp.md](form-8949-espp.md))
- Wash sale disallowed losses increase the basis of the replacement shares (tracked in software)

## 1099-R (Retirement Distributions)

**Key boxes:**
- Box 1: Gross distribution
- Box 2a: Taxable amount
- Box 2b: Taxable amount not determined / Total distribution checkboxes
- Box 4: Federal tax withheld
- Box 5: Employee contributions / designated Roth / insurance premiums (recovery of basis)
- Box 7: Distribution code(s)

**Distribution Code 7 values (most common):**
- **1**: Early distribution, no known exception (under 59½, typically 10% penalty)
- **2**: Early distribution, exception applies (under 59½ but no penalty — SEPP, disability exception, etc.)
- **3**: Disability
- **4**: Death
- **7**: Normal distribution (age 59½ or older)
- **8**: Excess contributions + earnings (taxable in year paid)
- **B**: Designated Roth account distribution
- **G**: **Direct rollover** and direct payment (trustee-to-trustee, non-taxable)
- **H**: Direct rollover of designated Roth to Roth IRA
- **J**: Early distribution from Roth IRA
- **Q**: Qualified Roth IRA distribution
- **R**: Recharacterized IRA contribution (prior year)
- **T**: Roth IRA distribution, exception applies

**Form 1040 reporting (IMPORTANT distinction):**
- **Line 4a/4b** = IRA distributions (Traditional, Roth, SEP, SIMPLE, inherited IRA)
- **Line 5a/5b** = Pensions & annuities (401(k), 403(b), 457(b), defined benefit, TSP)
- **Source controls the line** — not the destination

**Common scenarios:**
| Source | Destination | Reporting | Taxable? |
|---|---|---|---|
| 401(k) | IRA | Line 5a gross, 5b = $0 | No (direct rollover, Code G) |
| 401(k) | Roth IRA | Line 5a gross, 5b = full amount | Yes (Roth conversion) |
| IRA | Roth IRA | Line 4a gross, 4b = taxable (pro-rata) | Yes |
| IRA | IRA (trustee-to-trustee) | Usually NOT reported | No |
| Traditional IRA | Distribution to you | Line 4a gross, 4b = taxable | Yes |

**When line 4b/5b < 4a/5a due to rollover, write "Rollover" next to the amount on the paper form.** Tax software does this automatically.

**Pro-rata trap (IRC § 408(d)(2)):** All traditional/SEP/SIMPLE IRAs are aggregated for computing the taxable portion of a distribution or conversion. A large pre-tax IRA balance poisons backdoor Roth conversions. Fix: reverse-roll pre-tax IRA into an employer 401(k) (401(k)s are NOT aggregated), then execute backdoor Roth. See Form 8606 for basis tracking.

## 1099-G (Government Payments)

**Key boxes:**
- Box 1: Unemployment compensation (Schedule 1 Line 7, taxable)
- Box 2: State/local income tax refund (taxable only if itemized last year and got benefit — Tax Benefit Rule)
- Box 3: Year of refund
- Box 4: Federal tax withheld
- Box 5: RTAA payments
- Box 6: Taxable grants
- Box 7: Agriculture payments
- Box 11: State tax withheld

**Validation checks:**
- **Unemployment is always federally taxable** (even if you live in a no-income-tax state)
- **State refund** (Box 2) is ONLY taxable if:
  - You itemized deductions in the prior year, AND
  - You deducted state income tax (not sales tax), AND
  - The deduction gave you a tax benefit (not limited out by AMT or SALT cap)
- WA residents: no state income tax, so Box 2 is never a taxable refund issue (Box 2 usually empty)
- If you have Fed withholding on unemployment (Box 4), add to 1040 Line 25b

## 1099-Q (529 Plan Distributions)

**Key boxes:**
- Box 1: Gross distribution
- Box 2: Earnings portion
- Box 3: Basis portion (contributions)
- Box 5: Private vs State QTP checkbox
- Box 6: Trustee-to-trustee transfer checkbox
- Recipient: whoever the money went to (account owner or beneficiary)

**Validation checks:**
- **Box 1 = Box 2 + Box 3** (always, by identity)
- **Fully qualified education expenses → no taxable income**, NO reporting on return
- If distributions exceed qualified expenses, earnings portion is taxable + 10% penalty on the taxable earnings
- **Recipient matters:** If the check went to the account owner (parent), the parent reports any taxable portion. If it went to the beneficiary (student), the student reports. Each gets a separate 1099-Q.
- Qualified expenses include: tuition, fees, books, required supplies, room & board (if enrolled at least half-time), computers/software
- NON-qualified: transportation, insurance, student loan payments (with a $10k lifetime exception)
- Can't double-dip: expenses used for 529 qualification cannot also be used for AOTC/LLC
- Scholarship adjustment: non-taxable portion of scholarships reduces qualified expenses, but the taxpayer can elect to include scholarship in income to preserve 529 qualification

## 1099-NEC (Nonemployee Compensation)

**Key boxes:**
- Box 1: Nonemployee compensation (self-employment income → Schedule C)
- Box 4: Federal tax withheld (rare for 1099-NEC)

**Validation checks:**
- If the taxpayer received this but the work was really employee work, it may be misclassified — Form 8919 can reclassify
- Triggers Schedule C + Schedule SE (self-employment tax)
- $400+ total SE income = SE tax required
- Flows to QBI calculation

## 1099-K (Payment Card / Third Party Network)

**Key boxes:**
- Box 1a: Gross amount of payment card/third-party transactions
- Box 1b: Card not present transactions

**Validation checks:**
- 2025 reporting threshold was scheduled to drop to $600 but is phased: $2,500 in 2025, $600 in 2026+
- Gross amount — does NOT net refunds, chargebacks, fees
- For resellers/hobby sellers, may need to separately report cost basis on Schedule 1 or Schedule C
- Personal reimbursements via Venmo/PayPal (splitting dinner, gifts) are NOT taxable — don't include

## 1099-MISC (Miscellaneous Information)

**Key boxes:**
- Box 1: Rents
- Box 2: Royalties
- Box 3: Other income
- Box 4: Federal tax withheld
- Box 5: Fishing boat proceeds
- Box 6: Medical & health care payments
- Box 7: Nonemployee compensation (MOVED to 1099-NEC starting 2020; rarely used on MISC now)
- Box 8: Substitute payments in lieu of dividends/interest
- Box 10: Gross proceeds to attorneys
- Box 14: Nonqualified deferred compensation

**Validation checks:**
- Box 3 "Other income" needs a story — where on the return? Usually Schedule 1 Line 8
- Rents: Schedule E
- Royalties: Schedule E (non-working interest) or Schedule C (working interest)
- Attorney fees on Box 10 ≠ attorney's income (it's a notification to the IRS)

## 1098 (Mortgage Interest)

**Key boxes:**
- Box 1: Mortgage interest received
- Box 2: Outstanding mortgage principal (as of 1/1 or origination date)
- Box 3: Mortgage origination date
- Box 4: Refund of overpaid interest
- Box 5: Mortgage insurance premiums (deductible status depends on year)
- Box 6: Points paid on purchase of principal residence
- Box 7: Address of property (if different from payer)
- Box 8: Address of property
- Box 10: Often shows real estate taxes paid through escrow
- Box 11: Mortgage acquisition date

**Validation checks:**
- Mortgage interest deductibility depends on:
  - Is it acquisition indebtedness or home equity used for home improvement? ✓
  - Home equity NOT used for home improvement? ✗ (since TCJA)
  - Over $750k loan origination post-12/15/2017? Partial phaseout
  - Over $1M loan origination pre-12/15/2017? Grandfathered under old rules
- Property tax (Box 10) goes to Schedule A Line 5b, capped under SALT
- Points are amortized over the loan life on refinances; deductible in year paid for purchases

## K-1 (Partnership/S-Corp/Trust)

Not technically a 1099 but often grouped. Each line corresponds to specific 1040/Schedule locations. See Schedule K-1 instructions.

**Common K-1 items:**
- Box 1 (partnership): Ordinary business income → Schedule E Part II
- Box 2: Rental real estate income
- Box 5: Interest → Schedule B
- Box 6a/6b: Dividends → Schedule B
- Box 8: Net short-term cap gain → Schedule D
- Box 9a: Net long-term cap gain → Schedule D
- Box 13: Other deductions
- Box 20: QBI info (code Z)

## Form 5498 (IRA Contribution Information)

**Key boxes:**
- Box 1: IRA contributions (Traditional)
- Box 2: Rollover contributions
- Box 3: Roth conversion amount
- Box 4: Recharacterized contributions
- Box 5: FMV of account
- Box 10: Roth contributions
- Box 11: RMD required indicator

**Validation checks:**
- 5498 is NOT filed with the return — informational only
- Cross-check Box 1/10 (contributions) against deduction claimed
- Cross-check Box 2 (rollover) against corresponding 1099-R (should match if direct rollover)
- Box 3 (Roth conversion) triggers Form 8606 Part II

## Cross-Reference Checks

When reviewing an entire tax document bundle:

1. **1099-R Box 1 rollover amount ↔ 5498 Box 2 rollover contribution** — should match exactly for a direct rollover
2. **W-2 Box 2 + 1099-R Box 4 + 1099-G Box 4 + other withholding** = Total federal withholding on 1040 Line 25
3. **Brokerage 1099 DIV + INT + B all on one consolidated form** — extract each section separately
4. **1098 property tax** — may also appear on annual property tax statement; check not double-counting
5. **1099-Q totals per beneficiary** — one 529 can have multiple recipients (parent + student = 2 forms)
6. **K-1 ordinary income + guaranteed payments** — may trigger SE tax if general partner
7. **Charitable CWAs ↔ stock donation FMV calculations ↔ Form 8283 entries** — ensure all three match
