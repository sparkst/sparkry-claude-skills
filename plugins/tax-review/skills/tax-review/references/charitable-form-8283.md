# Charitable Contributions & Form 8283 Reference

Guidance for validating charitable contributions, acknowledgment letters, and Form 8283 requirements. Based on IRS Pub 1771, Pub 526, Pub 561, and Reg § 1.170A-13.

## Contemporaneous Written Acknowledgment (CWA) Thresholds

Per IRC § 170(f)(8), the donor must obtain a CWA for any single contribution of $250 or more. Below $250, a bank record or basic receipt is sufficient.

| Amount | Requirement |
|---|---|
| Cash under $250 | Bank record OR donee written communication showing name, date, amount |
| Cash $250+ | Full CWA required (see elements below) |
| Quid pro quo $75+ | Donee must disclose goods/services value and that deduction is limited to excess |
| Non-cash under $250 | Receipt with name, date, location, description |
| Non-cash $250–$500 | CWA + written records of acquisition details |
| Non-cash $500–$5,000 | Above + **Form 8283 Section A** |
| Non-cash over $5,000 | Above + **qualified appraisal** + **Form 8283 Section B** with donee signature |
| Non-cash over $500,000 | Above + appraisal physically attached to return |

**Exception for publicly-traded securities:** Always Section A only, regardless of value. No qualified appraisal required.

## What the CWA MUST Contain

Per IRC § 170(f)(8)(B):

1. **Name of the charity**
2. **Amount of cash** contribution (cash only)
3. **Description (NOT value) of non-cash** contribution (stock, property)
4. **Statement** that no goods or services were provided in return, IF that was the case
5. **Description and good-faith estimate** of goods/services provided in return, IF any
6. **Statement** that goods/services consisted entirely of intangible religious benefits, IF applicable (used by churches)

If ANY of these elements is missing for a $250+ donation, the CWA is deficient and the deduction is technically not IRS-compliant.

**What is NOT required** (common misconception):
- Charity's address — not required but useful
- Charity's EIN — not required but useful
- Signature — not required but common
- Letter date — not required but "contemporaneous" timing matters

## "Contemporaneous" Timing Rule

Per IRC § 170(f)(8)(C), the donor must receive the CWA by the EARLIER of:
- The date the return is filed, OR
- The due date including extensions

**Strict compliance.** A CWA received one day late = deduction denied. There is no way to cure this retroactively.

Practical implication: if you're reviewing a return in April and a CWA letter is dated January of the filing year, it's fine. If it's dated the day after filing, it's too late.

## Quid Pro Quo Rules (IRC § 6115)

When a donor receives something of value in exchange for a gift over $75 (e.g., a gala ticket, a tote bag, a book), the charity MUST:
- Inform the donor in writing that the deduction is limited to the amount in excess of the goods/services value
- Provide a good-faith estimate of that value

**Common situations to watch for:**
- Gala/dinner tickets (FMV = cost of meal + entertainment)
- Auction purchases (FMV = market value of item; deduction = amount paid above FMV)
- Charity runs/walks (registration fees often NOT deductible; separate donations are)
- Membership benefits (subscriptions, parking, preferred seating reduce deduction)
- Raffle tickets — NEVER deductible as charitable (it's gambling)

**Token exception:** De minimis items (pens, mugs, calendars) under specific IRS thresholds can be ignored. For 2025, the low-cost article threshold is around $13.60.

## Form 8283 — Section A vs Section B

### Section A (Part I) — Publicly Traded Securities
Always Section A, regardless of value. Includes:
- Stocks traded on an established securities market (NYSE, Nasdaq, OTC with quotations)
- Mutual funds with readily-available quotations
- ETFs

**Donee signature NOT required.** No qualified appraisal required.

### Section A (Part I) — Other Items ≤ $5,000
For each non-cash item or group of similar items ≤ $5,000:
- Name/address of donee
- Description of property
- Date contributed
- Date acquired by donor ("Various" OK)
- How acquired (purchase, gift, inheritance)
- Donor's cost/basis
- Fair market value
- Method used to determine FMV (thrift shop value, appraisal, catalog, comparable sales)

### Section B — Items > $5,000 (NOT publicly traded)
Required for:
- Art, collectibles
- Real estate
- Vehicles, boats, aircraft (unless 1098-C applies)
- Closely-held stock
- Partnership/LLC interests
- Intellectual property

Requires:
- **Qualified appraisal** (signed/dated within 60 days before contribution, obtained before return filing deadline)
- **Donee acknowledgment signature in Part V** — the charity signs to confirm receipt
- **Appraiser signature in Part IV**
- For gifts over $500,000, the appraisal itself must be physically attached

## Qualified Appraiser (Reg § 1.170A-17)

A qualified appraiser is an individual who:
1. Has a recognized appraiser designation from a professional org OR meets minimum education + 2 years experience
2. Regularly prepares appraisals for compensation
3. Makes the qualification declaration in the appraisal itself
4. Is not the donor, donee, or related party to either, or a party to the acquisition transaction

## FMV for Publicly-Traded Stock

Per IRS Pub 561 and Reg § 20.2031-2(b):

**FMV = (Highest quoted selling price + Lowest quoted selling price) / 2** on the valuation date.

**NOT:** closing price, opening price, VWAP, or the charity's stated value if different.

### Valuation Date = Delivery Date, NOT Submission Date

The donation is "complete" for tax purposes when the charity has **unconditional control** of the stock. Per Pub 561:

| Transfer Method | Date of Gift |
|---|---|
| Stock certificate delivered in person, endorsed | Delivery date |
| Stock certificate mailed, endorsed | Postmark date (if received in regular course) |
| DTC / electronic transfer to charity's broker | **Date shares arrive in charity's account** |
| Delivered to bank/broker/issuer for transfer to charity's name | Date transferred on the books of the corporation |

**Common error:** Using the submission date (when donor signed the transfer authorization at their own broker) instead of the delivery date. Typical settlement takes 1–5 business days. The donor must use the DELIVERY DATE for FMV.

### Stock That Doesn't Trade on Delivery Date

When delivery falls on a weekend, holiday, or date with no trading:

**Weighted inverse average:** Take the H+L mean on the nearest trading day BEFORE and the nearest trading day AFTER, weighted inversely by the number of trading days to each.

**Example:** Delivered Saturday. Prior Friday H+L mean = $100. Following Monday H+L mean = $110. Weight by inverse trading-day distance (1 day before, 2 days after):
```
((2 × $100) + (1 × $110)) / (1 + 2) = $310 / 3 = $103.33
```

The weights are SWAPPED from what you'd expect: the 2-days-after price gets the 1-day-before weight, and vice versa.

### What If the Charity States a Value That Doesn't Match?

The charity's stated value is NOT binding. If the charity says "we valued this at $X using the closing price" and the IRS rule gives a different number using H+L/2, the donor should use the IRS-correct number on their return.

**Donor is responsible for FMV determination, not the charity.** Per Pub 526.

## AGI Limitations on Charitable Deductions

For 2025 (unchanged by OBBBA):

| Gift Type | Recipient | AGI Limit |
|---|---|---|
| Cash | Public charity (50% org) | 60% |
| Appreciated LTCG property (held > 1yr) | Public charity, FMV basis | **30%** |
| Appreciated property | Public charity, cost-basis election | 50% |
| Cash | Private non-operating foundation | 30% |
| Appreciated property | Private foundation | 20% |

**Carryforward:** Excess over AGI limit carries forward up to 5 years. Each year, current-year contributions are used first, then oldest carryforward.

**5-year carryforward retains its character:** A carryforward of appreciated stock remains 30%-limited; a carryforward of cash remains 60%-limited.

## OBBBA 2026+ Changes (Not 2025)

Starting 2026:
- **0.5% AGI floor**: Itemizers can only deduct giving above 0.5% of AGI
- **35% benefit cap**: Top-bracket (37%) itemizers get capped at 35% tax benefit
- **Above-the-line for non-itemizers**: $1,000 single / $2,000 MFJ (cash to public charity only; excludes DAF)

**2025 is the optimal year for large charitable gifts.** Donor-advised fund bunching before 12/31/2025 locks in the favorable pre-OBBBA rules.

## Common Validation Checks

When reviewing charitable donations:

1. **Does each $250+ gift have a CWA?** Missing CWA = deduction denied.
2. **Does the CWA have all required elements?** No-goods-or-services statement is the most commonly missing one.
3. **Is the "contemporaneous" timing met?** Received before the earlier of filing or due date.
4. **Is every $500+ non-cash gift on Form 8283?** And every $5,000+ in Section B (except publicly-traded)?
5. **For stock gifts: was FMV computed correctly?**
   - Delivery date (not submission date)
   - H+L/2 (not close price)
   - Match the donor-side math, not the charity's stated value
6. **Does the charity name match across documents?** Use the legal name (e.g., "Faith Foundation Northwest" not "Faith United Methodist Church" if the foundation is the recipient).
7. **Are any gifts actually quid pro quo?** Check for galas, auctions, charity runs, membership benefits.
8. **Was the donor ever credited for someone else's gift?** (A third party submits a gift but asks the charity to credit the donor — not deductible by the donor since they didn't pay it.)
9. **AGI limit exceeded?** If cash > 60% AGI or stock > 30% AGI, excess carries forward.
10. **Same donor name on all docs?** "Amy & Travis" vs "Travis" matters if not MFJ.

## Stock Donation Red Flags

- **Charity-stated value ≠ IRS H+L/2:** Charity used close price or wrong date. Compute correct value.
- **Gift date mismatch:** Submission vs delivery. Always use delivery.
- **Missing "no goods or services" language on stock receipt:** Receipt is deficient. Request a supplemental letter.
- **Share count on receipt ≠ share count on broker transfer:** Reconcile against broker 1099-B and outgoing DTC confirmation.
- **Receipt from fiscal sponsor vs ultimate beneficiary:** List the actual 501(c)(3) that received the shares.
- **Cross-year gifts:** A gift initiated 12/31/2025 but delivered 1/2/2026 is a **2026 deduction**, not 2025. Delivery date controls.

## Sources

- IRS Pub 1771: https://www.irs.gov/pub/irs-pdf/p1771.pdf
- IRS Pub 526 (2025): https://www.irs.gov/publications/p526
- IRS Pub 561 (12/2025): https://www.irs.gov/publications/p561
- Instructions for Form 8283 (12/2025): https://www.irs.gov/instructions/i8283
- IRS — Written Acknowledgments: https://www.irs.gov/charities-non-profits/charitable-organizations/charitable-contributions-written-acknowledgments
- Reg § 20.2031-2(b): https://www.law.cornell.edu/cfr/text/26/20.2031-2
- Reg § 1.170A-13: https://www.law.cornell.edu/cfr/text/26/1.170A-13
- IRC § 170(f)(8): https://www.law.cornell.edu/uscode/text/26/170
